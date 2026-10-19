"""Stage-level aggregates of a paired run: where the pipeline loses, never for whom.

``python -m evaluation.research.stage_summary CAPTURES_DIR --dataset DATASET.json [--out FILE]``
reads the layout the ``expert_paired`` workflow uploads (``<case>-<arm>/<stamp>/``,
as ``scorecard.load_run`` does) and prints, per arm and repetition, counts
summed over every case:

* the discovery funnel, from seeds and sitemap leads to the confirmed
  programme page, and how far the gold programme page got (``gold_seen``);
* refusals by reason category (a fixed vocabulary, never the page or its title);
* page languages of confirmed and of gold-returned pages, as language codes;
* evidence: pages read per evidence stage, claims per claim type, claims
  matched to labels, and wrong-scope claims by the scope dimension that did
  not match (``metrics.dimension_matches``);
* budget and time per case, mean and max;
* failed discovery searches (``search_failures``, by provider status, and
  their share of attempted discovery queries), so that a provider outage reads
  as an outage and never as a pipeline result.

Built for the one heldout look the owner approved (heldout pre-registration
§9, H-1, 2026-10-19): no case id, university name, URL, host, claim value,
label value or excerpt is ever printed or written. That is not left to care:
:func:`leak_check` runs on the rendered text before anything leaves the
process, and the tool exits non-zero without output when it finds a case id,
a university name, a case domain or ``http`` in it.

Evaluation tooling only: nothing under ``app/`` may import it.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .metrics import (
    adjudicate,
    adjudicate_programme_pages,
    canonical_url,
    dimension_matches,
    same_programme_page,
    scored_predictions,
)
from .schema import Capture, Case, Dataset, Observation, Scope
from .scorecard import GOLD_STAGES, Arm, _answered, gold_seen, load_run

#: The scope dimensions a wrong-scope claim is broken down by, reviewer order.
DIMENSIONS = (
    "university",
    "programme",
    "degree",
    "field",
    "intake",
    "population",
    "qualification",
    "academic_year",
)

#: Page types (``PageOutcome.page_type``) per evidence stage.
EVIDENCE_STAGES: dict[str, frozenset[str]] = {
    "requirements": frozenset(
        {
            "general_admissions",
            "intake_specific_program",
            "program_detail",
            "country_credential_requirements",
            "documents",
        }
    ),
    "costs": frozenset({"costs"}),
    "scholarships": frozenset({"scholarship_index", "scholarship_award", "scholarship_faq"}),
}

#: Refusal reason -> category. A reason quotes page titles, award names and
#: hosts, so only a category from this table (or ``other``) is ever counted;
#: a captured group is kept only when it is a controlled lowercase word.
_REFUSAL_CATEGORIES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^reads as ([a-z_]+), not a programme page"), "reads_as:{0}"),
    (re.compile(r"^page subject .* names a related"), "subject_related_programme"),
    (re.compile(r"^page subject .* does not match"), "subject_mismatch"),
    (re.compile(r"^page names degree level ([a-z_]+)"), "degree_level:{0}"),
    (re.compile(r"names a degree level other than"), "degree_level_other"),
    (re.compile(r"^page names an alternate programme variant"), "alternate_variant"),
    (re.compile(r"^page names a campus abroad"), "campus_abroad"),
    (re.compile(r"^navigation lead names none of"), "navigation_lead_no_subject"),
    (re.compile(r"^search lead unresolved \(([a-z_]+)\)"), "search_lead_unresolved:{0}"),
    (re.compile(r"^SM-2: news/events/media sitemap"), "sitemap_news_not_read"),
    (re.compile(r"^off the institution's domain"), "off_domain"),
    (re.compile(r"front page is not a programme page"), "front_page"),
)

#: The status ``search_failure_diagnostic`` writes: "(serper; HTTP 400)".
_FAILURE_STATUS = re.compile(r"\bHTTP (\d{3})\b")
_IDENTITY_RECOVERY = re.compile(r"search identity recovery: checked (\d+), confirmed (\d+)")
_CONTROLLED = re.compile(r"[a-z][a-z0-9_]{0,40}")
_LANGUAGE = re.compile(r"[a-z]{2,3}(-[a-z0-9]{2,8})?")


def refusal_category(reason: object) -> str:
    """The category of one refusal reason, from a fixed table; ``other`` otherwise."""
    text = str(reason or "").strip()
    for pattern, category in _REFUSAL_CATEGORIES:
        match = pattern.search(text)
        if match:
            return category.format(*(_controlled(g) for g in match.groups()))
    return "other"


def _controlled(value: object) -> str:
    """A vocabulary word (a family, page type, phase, outcome) or ``other``.

    ``http`` is spelt ``web`` (``http_error`` reads ``web_error``) so that the
    leak guard's ``http`` check stays a plain substring test.
    """
    text = str(value or "").strip().casefold().replace("http", "web")
    return text if _CONTROLLED.fullmatch(text) else "other"


def language_code(value: object) -> str:
    """A language code (``en``, ``pt-br``), or ``other`` for anything else."""
    text = str(value or "").strip().casefold().replace("_", "-")
    return text if _LANGUAGE.fullmatch(text) else "other"


def url_language_hint(url: object) -> str:
    """A page's language as its URL suggests: ``?lang=``, else a leading code segment."""
    parts = urlsplit(str(url))
    lang = parse_qs(parts.query).get("lang")
    if lang:
        return language_code(lang[0])
    first = parts.path.strip("/").split("/", 1)[0]
    if re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", first.casefold()):
        return language_code(first)
    return "none"


def claim_type(key: str) -> str:
    """A prediction key with its award segment removed (``scholarships.*.exists``)."""
    parts = key.split(".")
    if parts[0] == "scholarships" and len(parts) > 2:
        parts[1] = "*"
    return ".".join(_controlled(p) if p != "*" else p for p in parts)


def failure_status(diagnostic: object) -> str:
    """The HTTP status a search-failure diagnostic names, or ``none``."""
    match = _FAILURE_STATUS.search(str(diagnostic or ""))
    return match[1] if match else "none"


def _host_on(url: object, domain: str) -> bool:
    host = (urlsplit(str(url)).hostname or "").casefold().removeprefix("www.")
    domain = domain.casefold().removeprefix("www.")
    return bool(domain) and (host == domain or host.endswith("." + domain))


def _gold_urls(case: Case, trace: dict[str, Any]) -> set[str]:
    """The gold programme pages and their declared twins, as ``gold_seen`` reads them."""
    gold = {canonical_url(u) for u in case.programme_urls}
    for url, twins in (trace.get("programme_url_aliases") or {}).items():
        if any(same_programme_page(url, g) for g in set(gold)):
            gold |= {canonical_url(t) for t in twins}
    return gold


def _html_language(observation: Observation | None, url: object) -> str:
    if observation is not None:
        for recorded, language in observation.programme_page_languages.items():
            if canonical_url(recorded) == canonical_url(url):
                return language_code(language)
    return "unrecorded"


def _wrong_scope_dimensions(expected: list[Scope], actual: Scope | None) -> set[str]:
    """The dimensions that kept a claim out of every label evidence scope."""
    if actual is None:
        return {"unrecorded"}
    out: set[str] = set()
    for scope in expected:
        for dimension in DIMENSIONS:
            wanted = getattr(scope, dimension, None)
            if wanted is not None and not dimension_matches(
                dimension, wanted, getattr(actual, dimension)
            ):
                out.add(dimension)
    return out


def _stats(values: Iterable[float | int | None]) -> dict[str, float]:
    numbers = [float(v) for v in values if v is not None]
    if not numbers:
        return {"mean": 0.0, "max": 0.0}
    return {"mean": round(sum(numbers) / len(numbers), 1), "max": round(max(numbers), 1)}


def _knockout_rows(funnel: Counter[str], observation: Observation, verdict: Any) -> None:
    """G-07: the gold-knockout arm's rows; nothing on a capture made without it.

    A *guess* is a programme page confirmed while the case's gold page was
    unreachable: ``knockout_guess_cases`` counts the cases with one,
    ``knockout_guess_cases_wrong`` those with a wrong one (the guess rate's
    numerator; its denominator is ``knockout_cases_gold_refused``).
    ``knockout_leaked_hits`` should stay 0: a hit means a gold form got past.
    """
    t = observation.telemetry
    if t.knockout_gold_urls is None:
        return
    funnel["knockout_cases"] += 1
    funnel["knockout_reads_refused"] += t.knockout_refused or 0
    if not t.knockout_gold_urls:
        funnel["knockout_cases_no_gold_noop"] += 1
        return
    funnel["knockout_cases_gold_refused"] += 1
    confirmed = len(set(map(canonical_url, observation.programme_urls)))
    funnel["knockout_guess_pages"] += confirmed
    funnel["knockout_guess_cases"] += confirmed > 0
    funnel["knockout_guess_cases_wrong"] += bool(verdict.wrong)
    funnel["knockout_guess_pages_wrong"] += len(verdict.wrong)
    funnel["knockout_guess_pages_related"] += len(verdict.related)
    funnel["knockout_leaked_hits"] += len(verdict.matched)
    funnel["knockout_abstained"] += confirmed == 0


def repetition_summary(
    dataset: Dataset, capture: Capture, traces: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """One repetition's aggregates, section -> row -> count, summed over its cases."""
    observed = {o.case_id: o for o in capture.observations}
    funnel: Counter[str] = Counter()
    gold: Counter[str] = Counter()
    refusals: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    evidence: Counter[str] = Counter()
    claims: Counter[str] = Counter()
    scope: Counter[str] = Counter()
    reads: list[int | None] = []
    queries: list[int | None] = []
    seconds: list[float | None] = []
    for case in dataset.cases:
        observation = observed.get(case.id)
        if observation is None:
            continue
        trace = traces.get(case.id) or {}
        funnel["cases"] += 1
        funnel["cases_with_trace"] += bool(trace)

        # Discovery funnel.
        funnel["seeds"] += len(trace.get("manual_seeds") or {})
        funnel["sitemaps_read"] += len(trace.get("sitemaps_read") or [])
        funnel["sitemap_urls_seen"] += int(trace.get("sitemap_urls_seen") or 0)
        funnel["sitemap_urls_kept"] += int(trace.get("sitemap_urls_kept") or 0)
        ledger = trace.get("read_ledger") or {}
        funnel["reads_in_discovery"] += int((ledger.get("by_phase") or {}).get("discovery") or 0)
        funnel["programme_candidates_read"] += len(trace.get("pages_read") or [])
        rows = trace.get("search_results") or []
        funnel["discovery_queries"] += len(rows)
        for row in rows:
            funnel[f"discovery_queries:{_controlled(row.get('family'))}"] += 1
            urls = row.get("urls") or []
            funnel["search_results_returned"] += len(urls)
            funnel["search_results_on_official_domain"] += sum(
                _host_on(u, case.domain) for u in urls
            )
        funnel["search_calls_total"] += observation.telemetry.search_calls or 0
        # A provider outage must read as an outage, never as a pipeline result:
        # every discovery query that failed, by the status the provider gave.
        failures = trace.get("search_failures") or []
        funnel["search_failures"] += len(failures)
        for diagnostic in failures:
            funnel[f"search_failures_by_status:{failure_status(diagnostic)}"] += 1
        for line in trace.get("errors") or []:
            if match := _IDENTITY_RECOVERY.search(str(line)):
                funnel["identity_recovery_leads_checked"] += int(match[1])
                funnel["identity_recovery_leads_confirmed"] += int(match[2])
        verdict = adjudicate_programme_pages(case, observation)
        funnel["programme_pages_confirmed"] += len(
            set(map(canonical_url, observation.programme_urls))
        )
        funnel["confirmed_pages_hit"] += len(verdict.matched)
        funnel["confirmed_pages_wrong"] += len(verdict.wrong)
        funnel["confirmed_pages_related"] += len(verdict.related)
        funnel[f"case_outcome:{verdict.outcome}"] += 1
        _knockout_rows(funnel, observation, verdict)

        # Gold programme page, furthest stage (WF-17).
        seen = gold_seen(case, observation, trace)
        gold[f"furthest:{seen['stage']}"] += 1
        tags = set(seen["seen_as"])
        if seen["stage"] != "no_gold":
            gold["cases_with_gold"] += 1
            gold["gold_returned_by_search"] += any(t.startswith("returned:") for t in tags)
            gold["gold_read"] += "read" in tags or seen["stage"] in {"confirmed", "read"}
            gold["gold_confirmed"] += seen["stage"] == "confirmed"
            gold["gold_never_seen"] += seen["stage"] == "never"
            for tag in tags:
                if tag.startswith("returned:"):
                    gold[f"returned_by_family:{_controlled(tag.split(':', 1)[1])}"] += 1

        # Refusals.
        for _url, why in trace.get("pages_read") or []:
            if why:
                refusals[f"read_refused:{refusal_category(why)}"] += 1
        for _url, why in trace.get("rejected_sample") or []:
            refusals[f"lead_rejected_sample:{refusal_category(why)}"] += 1
        refusals["leads_rejected_total"] += int(trace.get("rejected_total") or 0)
        for page in observation.page_outcomes:
            refusals[f"page_outcome:{_controlled(page.category.replace('-', '_'))}"] += 1
        for spent in (ledger, trace.get("case_time") or {}):
            for row in spent.get("refusals") or []:
                if isinstance(row, dict):
                    phase, kind = _controlled(row.get("phase")), _controlled(row.get("kind"))
                    refusals[f"budget_refused:{phase}:{kind}"] += 1

        # Languages.
        for url in observation.programme_urls:
            languages[f"confirmed_html_lang:{_html_language(observation, str(url))}"] += 1
            languages[f"confirmed_url_hint:{url_language_hint(url)}"] += 1
        if case.programme_urls:
            golden = _gold_urls(case, trace)
            for row in rows:
                for url in row.get("urls") or []:
                    if any(same_programme_page(url, g) for g in golden):
                        languages[
                            f"gold_returned_html_lang:{_html_language(observation, url)}"
                        ] += 1
                        languages[f"gold_returned_url_hint:{url_language_hint(url)}"] += 1

        # Evidence.
        for page in observation.page_outcomes:
            stage = next(
                (name for name, types in EVIDENCE_STAGES.items() if page.page_type in types),
                "other",
            )
            evidence[f"pages:{stage}"] += 1
            if page.category == "fetched-ok":
                evidence[f"pages_fetched_ok:{stage}"] += 1
        for phase, count in (ledger.get("by_phase") or {}).items():
            evidence[f"reads_by_phase:{_controlled(phase)}"] += int(count or 0)
        for kind, count in (ledger.get("by_kind") or {}).items():
            evidence[f"reads_by_kind:{_controlled(kind)}"] += int(count or 0)
        labels = {label.key: label for label in case.labels}
        for p in _answered(scored_predictions(observation.predictions, labels)):
            claims["claims"] += 1
            claims[f"by_type:{claim_type(p.key)}"] += 1
            label = labels.get(p.key)
            judged = adjudicate(p, label)
            if not judged.labelled:
                claims["verdict:unlabelled"] += 1
                continue
            claims["matched_to_label"] += 1
            if judged.other_scope:
                claims["verdict:other_scope"] += 1
            elif judged.partial:
                claims["verdict:partial"] += 1
            elif judged.correct:
                claims["verdict:correct"] += 1
            elif not judged.value_matches:
                claims["verdict:wrong_value"] += 1
            elif not judged.valid_scope:
                claims["verdict:wrong_scope"] += 1
                assert label is not None
                dims = _wrong_scope_dimensions(
                    [e.scope for e in label.evidence], p.evidence.scope if p.evidence else None
                )
                scope["wrong_scope_claims"] += 1
                for dimension in dims:
                    scope[f"dimension:{dimension}"] += 1
            else:
                claims["verdict:unsupported"] += 1
        for label in case.labels:
            if label.status == "known":
                claims["known_labels"] += 1

        # Budget and time.
        t = observation.telemetry
        reads.append(t.http_fetches)
        queries.append(t.search_calls)
        seconds.append(t.latency_seconds)

    # Failed over attempted discovery queries (answered rows plus failures).
    attempted = funnel["discovery_queries"] + funnel["search_failures"]
    discovery_share = round(funnel["search_failures"] / attempted, 3) if attempted else 0.0
    budget: dict[str, Any] = {}
    for name, values in (("reads", reads), ("queries", queries), ("seconds", seconds)):
        for stat, value in _stats(values).items():
            budget[f"{name}_per_case:{stat}"] = value
    budget["reads_total"] = sum(v or 0 for v in reads)
    budget["queries_total"] = sum(v or 0 for v in queries)
    for stage in GOLD_STAGES:
        gold.setdefault(f"furthest:{stage}", 0)
    funnel.setdefault("search_failures", 0)
    return {
        "discovery funnel": {**funnel, "discovery_search_failed_share": discovery_share},
        "gold programme page": dict(gold),
        "refusals": dict(refusals),
        "languages": dict(languages),
        "evidence": dict(evidence),
        "claims": dict(claims),
        "wrong scope by dimension": dict(scope),
        "budget and time": budget,
    }


def summarize_run(dataset: Dataset, arms: dict[str, Arm]) -> dict[str, Any]:
    """Column (``arm#repetition``) -> section -> row -> value."""
    columns: dict[str, Any] = {}
    entry_paths: dict[str, str] = {}
    for name, arm in arms.items():
        for index, capture in enumerate(arm.repetitions):
            traces = arm.traces[index] if index < len(arm.traces) else {}
            columns[f"{name}#{index + 1}"] = repetition_summary(dataset, capture, traces)
            # G-06: the entry path the arm took (absent = the default).
            entry_paths[f"{name}#{index + 1}"] = str(capture.config.get("entry_path") or "default")
    return {"dataset_version": dataset.version, "columns": columns, "entry_paths": entry_paths}


def render(summary: dict[str, Any]) -> str:
    """Markdown, one table per section: rows are counts, columns arm#repetition."""
    columns = summary["columns"]
    names = list(columns)
    lines = [f"# Stage summary (aggregates only), corpus {summary['dataset_version']}", ""]
    entry_paths = summary.get("entry_paths", {})
    if any(path != "default" for path in entry_paths.values()):
        shown = ", ".join(f"{column} {path}" for column, path in entry_paths.items())
        lines += [f"Entry path per arm: {shown}", ""]
    sections = list(next(iter(columns.values()), {}).keys())
    for section in sections:
        rows = sorted({row for column in columns.values() for row in column[section]})
        lines += [f"## {section}", ""]
        if not rows:
            lines += ["(none)", ""]
            continue
        lines.append("| row | " + " | ".join(names) + " |")
        lines.append("|---|" + "---:|" * len(names))
        for row in rows:
            cells = [_cell(columns[n][section].get(row, 0), row) for n in names]
            lines.append(f"| {row} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def _cell(value: object, row: str = "") -> str:
    if isinstance(value, float) and row.endswith("_share"):
        return f"{value:.3f}"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def leak_check(text: str, dataset: Dataset) -> list[str]:
    """What identifying material ``text`` contains, by kind; empty when clean.

    A case id is matched as a whole word (``um`` must not fire on ``maximum``),
    a university name and a case domain anywhere, ignoring case, and ``http``
    anywhere at all. The tokens themselves are never returned.
    """
    folded = text.casefold()
    found: set[str] = set()
    if "http" in folded:
        found.add("http")
    if "www." in folded:
        found.add("host")
    for case in dataset.cases:
        if re.search(rf"(?<![a-z0-9]){re.escape(case.id.casefold())}(?![a-z0-9])", folded):
            found.add("case_id")
        if case.university.strip() and case.university.casefold() in folded:
            found.add("university")
        if case.domain.strip() and case.domain.casefold().removeprefix("www.") in folded:
            found.add("domain")
    return sorted(found)


class LeakError(RuntimeError):
    """The rendered summary contains identifying material; nothing was emitted."""


def guarded_render(dataset: Dataset, arms: dict[str, Arm]) -> str:
    """The rendered summary, after :func:`leak_check` passes; raises otherwise."""
    text = render(summarize_run(dataset, arms))
    leaks = leak_check(text, dataset)
    if leaks:
        raise LeakError("refusing to emit: output contains " + ", ".join(leaks))
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("captures_dir", type=Path, help="unpacked paired-run artifact")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="also write the Markdown here")
    args = parser.parse_args(argv)
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    try:
        text = guarded_render(dataset, load_run(args.captures_dir))
    except LeakError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
