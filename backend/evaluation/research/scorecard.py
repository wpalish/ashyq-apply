"""One table for one paired run: what changed, against the signed corpus.

``python -m evaluation.research.scorecard RUN_DIR`` reads the layout the
``expert_paired`` workflow uploads (``<case>-<arm>/<stamp>/capture.json``),
scores every arm and repetition with the official scorer, and adds what the
scorer's totals hide:

* the outcome of every known label (hit, missed, wrong value, wrong scope,
  unsupported), so a miss can be traced to a cause;
* every wrong claim and every unlabelled answer, which the scorer only counts;
* the six core questions an applicant asks first, answered or not;
* the cost of each case against the per-university budget.

A label counts as gained or lost only when every repetition of one arm agrees
and every repetition of the other arm disagrees; anything else is reported as
unstable rather than as a result.

Plan approved by the owner on 2026-10-05 ("Начинай выполнение по плану");
the targets below are its Definition of Done.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .metrics import (
    PROGRAMME_OUTCOMES,
    adjudicate,
    adjudicate_programme_pages,
    canonical_url,
    ratio,
    returned_matching_gold,
    same_programme_page,
    score,
    scored_predictions,
)
from .schema import Capture, Case, Dataset, Label, Observation, Prediction

#: Definition of Done, metric targets (docs/process/SEARCH_DEFINITION_OF_DONE.md).
#: Targets 1 and 2 are the scorer's metrics; targets 3 and 4 are the readable
#: rows ``readable_rows`` adds (wayfinder finish-algorithm ticket 03).
TARGETS: dict[str, tuple[str, float]] = {
    "claim_precision": (">=", 0.95),
    "wrong_scope_claim_rate": ("<=", 0.03),
    "programme_found_on_readable": (">=", 1.0),
    "wrong_programme_pages": ("<=", 0),
    "core_known_rate": (">=", 0.80),
    "core_known_readable_rate": (">=", 0.80),
}
#: The two denominators of target 4: every known core question (``all``), or
#: only those whose evidence the run could read (``readable``, the target's own
#: denominator by owner decision 2026-10-18, finish-algorithm 01-Q2).
CORE_DENOMINATORS: dict[str, str] = {
    "all": "core_known_rate",
    "readable": "core_known_readable_rate",
}
#: Definition of Done, per-university budget.
BUDGET: dict[str, float] = {"search_calls": 6, "http_fetches": 60, "latency_seconds": 120.0}

#: The six questions an applicant asks first (app.pipeline.runner.CORE_QUESTIONS),
#: as the prediction keys that answer each. A key outside the corpus mapping is
#: written ``unmapped.<claim type>`` by map_claims, and still answers a question.
CORE_QUESTIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "english",
        re.compile(
            r"^(ielts\.overall|english_evidence\.[a-z0-9_]+\.minimum"
            r"|unmapped\.(ielts_min_overall|toefl_min_total|duolingo_min))$"
        ),
    ),
    ("gpa", re.compile(r"^(gpa|min_gpa|unmapped\.min_gpa)$")),
    ("deadline", re.compile(r"^(deadline|unmapped\.admission_deadline)$")),
    ("cost", re.compile(r"^(tuition|unmapped\.(tuition|total_cost_of_attendance))$")),
    ("scholarship", re.compile(r"^(scholarships\.[^.]+\.exists|unmapped\.scholarship_exists)$")),
    (
        "scholarship_international",
        re.compile(
            r"^(scholarships\.[^.]+\.applicability\.(international|nationality)"
            r"|unmapped\.scholarship_(international_eligible|citizenship_restriction))$"
        ),
    ),
)

#: The repetition directories the workflow writes, oldest first.
_ARM_DIR = re.compile(r"^(?P<case>[a-z0-9_]+)-(?P<arm>off|on)$")


@dataclass
class Arm:
    """One arm of a paired run: its captures, one list per repetition."""

    name: str
    repetitions: list[Capture] = field(default_factory=list)
    #: case id -> (access, pages checked, pages failed) from the raw trace.
    access: dict[str, tuple[str, int, int]] = field(default_factory=dict)
    #: Per repetition, case id -> the discovery trace (the raw report's, or
    #: the checkpoint copy a killed case left), for "gold seen at stage".
    traces: list[dict[str, dict[str, Any]]] = field(default_factory=list)
    #: Per repetition, case id -> that repetition's (access, checked, failed).
    access_by_rep: list[dict[str, tuple[str, int, int]]] = field(default_factory=list)
    #: Per repetition, case id -> the hosts whose every request failed.
    failed_hosts: list[dict[str, set[str]]] = field(default_factory=list)
    #: Per repetition, case id -> (search calls, failed search calls) its
    #: case log recorded; absent for a case that left no log.
    search_log: list[dict[str, tuple[int, int]]] = field(default_factory=list)


#: WF-17: how far the gold programme page got, furthest first. ``confirmed``:
#: returned and scored a hit (a twin included); ``rejected``: discovery refused
#: it (read, or dropped unread: the reason says which); ``read``: read and not
#: refused, yet not returned; ``listed``: a lead (sitemap pick, link text,
#: walker candidate, unresolved search lead) never read; ``returned``: only in
#: a provider's result list; ``never``: nowhere in the trace.
GOLD_STAGES = ("confirmed", "rejected", "read", "listed", "returned", "never")


def gold_seen(
    case: Case, observation: Observation | None, trace: dict[str, Any] | None
) -> dict[str, Any]:
    """Where the gold programme page was last seen in one case (WF-17).

    ``seen_as`` keeps every way the trace saw it, so "never seen" splits into
    "not returned", "returned, not read" and "seen as a link, dropped". The
    gold's declared twins (``programme_url_aliases``) count as the gold.
    """
    gold = {canonical_url(u) for u in case.programme_urls}
    if not gold:
        return {"stage": "no_gold", "seen_as": [], "reasons": []}
    trace = trace or {}
    labelled = set(gold)
    for url, twins in (trace.get("programme_url_aliases") or {}).items():
        if any(same_programme_page(url, g) for g in labelled):
            gold |= {canonical_url(t) for t in twins}

    def is_gold(url: object) -> bool:
        # v3-M2: a canonical variant of the gold (or of its twin) is the gold.
        return any(same_programme_page(url, g) for g in gold)

    seen: set[str] = set()
    reasons: list[str] = []
    for row in trace.get("search_results") or []:
        if any(is_gold(u) for u in row.get("urls") or []):
            seen.add(f"returned:{row.get('family')}")
    for urls in (trace.get("selected") or {}).values():
        if any(is_gold(u) for u in urls):
            seen.add("selected")
    if any(is_gold(pair[0]) for pair in trace.get("kept_by_link_text") or []):
        seen.add("link_text")
    walker = trace.get("walker") or {}
    if any(is_gold(c.get("url")) for c in walker.get("candidates") or []):
        seen.add("walker_candidate")
    if any(is_gold(u) for u in trace.get("unresolved") or []):
        seen.add("unresolved")
    read = False
    for url, verdict in trace.get("pages_read") or []:
        if is_gold(url):
            read = True
            seen.add("read")
            if verdict and verdict not in reasons:
                reasons.append(str(verdict))
    for row in walker.get("outcomes") or []:
        if is_gold(row.get("url")):
            seen.add(f"walker:{row.get('outcome')}")
    for url, reason in trace.get("rejected_sample") or []:
        if is_gold(url):
            seen.add("rejected")
            if reason not in reasons:
                reasons.append(str(reason))
    expected = {canonical_url(u) for u in case.programme_urls}
    if observation is not None and returned_matching_gold(observation, expected):
        stage = "confirmed"
    elif reasons:
        stage = "rejected"
    elif read:
        stage = "read"
    elif any(not tag.startswith("returned:") for tag in seen):
        stage = "listed"
    elif seen:
        stage = "returned"
    else:
        stage = "never"
    return {"stage": stage, "seen_as": sorted(seen), "reasons": reasons[:3]}


def _answered(predictions: list[Prediction]) -> list[Prediction]:
    """The predictions the scorer counts: a value, and one copy of each."""
    unique: dict[str, Prediction] = {}
    for p in predictions:
        if p.value is not None and p.value != "UNKNOWN":
            unique[p.model_dump_json()] = p
    return list(unique.values())


def label_outcomes(dataset: Dataset, capture: Capture) -> dict[str, Any]:
    """Every known label's outcome, every wrong claim, every unlabelled answer."""
    observed = {o.case_id: o for o in capture.observations}
    labels_out: list[dict[str, Any]] = []
    wrong: list[dict[str, Any]] = []
    unlabelled: list[dict[str, Any]] = []
    other_scope: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    for case in dataset.cases:
        observation = observed.get(case.id)
        labels = {label.key: label for label in case.labels}
        predictions = (
            _answered(scored_predictions(observation.predictions, labels)) if observation else []
        )
        by_key: dict[str, list[Prediction]] = defaultdict(list)
        for p in predictions:
            label = labels.get(p.key)
            verdict = adjudicate(p, label)
            by_key[p.key].append(p)
            if not verdict.labelled:
                unlabelled.append(
                    {
                        "case": case.id,
                        "key": p.key,
                        "value": p.value,
                        "url": str(p.evidence.url) if p.evidence else None,
                        "label_status": label.status if label else None,
                    }
                )
            elif verdict.other_scope or verdict.partial:
                (other_scope if verdict.other_scope else partial).append(
                    {
                        "case": case.id,
                        "key": p.key,
                        "value": p.value,
                        "expected": label.value if label else None,
                        "url": str(p.evidence.url) if p.evidence else None,
                    }
                )
            elif not verdict.correct:
                wrong.append(
                    {
                        "case": case.id,
                        "key": p.key,
                        "value": p.value,
                        "expected": label.value if label else None,
                        "why": _why(verdict),
                        "url": str(p.evidence.url) if p.evidence else None,
                    }
                )
        for label in case.labels:
            if label.status != "known":
                continue
            ours = by_key.get(label.key, [])
            verdicts = [adjudicate(p, label) for p in ours]
            judged = [v for v in verdicts if v.adjudicated]
            if any(v.correct for v in verdicts):
                outcome = "hit"
            elif not verdicts:
                outcome = "missed"
            elif any(v.partial for v in verdicts):
                outcome = "partial"
            elif not judged:
                outcome = "other_scope_only"
            elif any(v.value_matches and v.valid_scope for v in judged):
                outcome = "unsupported"
            elif any(v.value_matches for v in judged):
                outcome = "wrong_scope"
            else:
                outcome = "wrong_value"
            labels_out.append(
                {
                    "case": case.id,
                    "key": label.key,
                    "outcome": outcome,
                    "expected": label.value,
                    "ours": [p.value for p in ours],
                }
            )
    return {
        "labels": labels_out,
        "wrong_claims": wrong,
        "unlabelled": unlabelled,
        "other_scope": other_scope,
        "partial": partial,
    }


def _why(verdict: Any) -> str:
    if not verdict.value_matches:
        return "wrong_value"
    if not verdict.valid_scope:
        return "wrong_scope"
    return "unsupported"


def core_coverage(capture: Capture) -> dict[str, list[str]]:
    """Case id -> the core questions any prediction answers."""
    out: dict[str, list[str]] = {}
    for o in capture.observations:
        keys = {p.key for p in _answered(o.predictions)}
        out[o.case_id] = [
            name for name, pattern in CORE_QUESTIONS if any(pattern.match(k) for k in keys)
        ]
    return out


def core_known(dataset: Dataset, outcomes: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Case id -> core questions answered correctly, out of those the corpus knows.

    Definition of Done target 4 counts a question only where the signed corpus
    holds a ``known`` label for it (``not_applicable`` and ``unknown`` are
    outside the denominator), and credits it only when a matching known label
    is a hit. ``core_coverage`` above counts any answer, labelled or not.
    """
    hits: dict[str, set[str]] = defaultdict(set)
    for x in outcomes["labels"]:
        if x["outcome"] == "hit":
            hits[x["case"]].add(x["key"])
    out: dict[str, dict[str, int]] = {}
    for case in dataset.cases:
        known_keys = {label.key for label in case.labels if label.status == "known"}
        known = {name for name, pattern in CORE_QUESTIONS if any(map(pattern.match, known_keys))}
        answered = {
            name for name, pattern in CORE_QUESTIONS if any(map(pattern.match, hits[case.id]))
        }
        out[case.id] = {"answered": len(answered & known), "known": len(known)}
    return out


#: The errors a capture records when the case's wall clock ended it
#: (``evaluation/research/live.py``: the child's own stop, or the parent's kill).
CLOCK_KILLED_ERRORS = frozenset({"BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"})


def cost(capture: Capture, *, count_timeouts: bool = True) -> dict[str, dict[str, float | None]]:
    """Case id -> queries, reads and seconds, with the budget's verdict.

    The harness ends a case at its wall clock, so ``latency_seconds`` can never
    exceed 120 and a case the clock killed passed the latency limit unfinished
    (read budget analysis 2026-10-18 §1). ``count_timeouts`` (scorecard option
    ``--count-timeouts-over-budget``, on by owner decision 2026-10-18;
    ``--no-count-timeouts-over-budget`` turns it off) counts such
    a case as over the latency budget and marks its row ``killed_by_clock``.
    """
    out: dict[str, dict[str, float | None]] = {}
    for o in capture.observations:
        t = o.telemetry
        row: dict[str, float | None] = {
            "search_calls": t.search_calls,
            "http_fetches": t.http_fetches,
            "latency_seconds": round(t.latency_seconds, 1) if t.latency_seconds else None,
        }
        over = [k for k, limit in BUDGET.items() if (row.get(k) or 0) > limit]
        if count_timeouts and o.error in CLOCK_KILLED_ERRORS:
            row["killed_by_clock"] = 1
            if "latency_seconds" not in over:
                over.append("latency_seconds")
        row["over_budget"] = len(over)
        if t.t_first_query is not None:
            # Only where the capture recorded it: older captures keep their shape.
            row["t_first_query"] = t.t_first_query
        out[o.case_id] = row
    return out


def programme_pages(dataset: Dataset, capture: Capture, report: dict[str, Any]) -> dict[str, str]:
    """Captured case id -> ``hit``, ``miss`` or ``unlabelled`` for the programme page.

    dev4 labels the programme page and nothing else, so its per-case row has
    to say whether the page was found; this is the scorer's own verdict.
    """
    known = {case.id for case in dataset.cases if case.programme_status == "known"}
    captured = {o.case_id for o in capture.observations}
    return {
        row["case_id"]: ("hit" if row["programme_hit"] else "miss")
        if row["case_id"] in known
        else "unlabelled"
        for row in report["cases"]
        if row["case_id"] in captured
    }


def load_run(run_dir: Path) -> dict[str, Arm]:
    """Arms of a paired run, each with its captures merged per repetition."""
    per_arm: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for capture_path in sorted(run_dir.glob("*/*/capture.json")):
        match = _ARM_DIR.match(capture_path.parent.parent.name)
        if match:
            per_arm[match["arm"]][match["case"]].append(capture_path)
    if not per_arm:
        single = run_dir / "capture.json" if run_dir.is_dir() else run_dir
        arm = Arm(name="run", repetitions=[_read(single)])
        return {"run": arm}
    arms: dict[str, Arm] = {}
    for name, cases in sorted(per_arm.items()):
        arm = Arm(name=name)
        depth = max(len(paths) for paths in cases.values())
        for index in range(depth):
            parts = [_read(paths[index]) for paths in cases.values() if index < len(paths)]
            merged = parts[0].model_copy(
                update={"observations": [o for part in parts for o in part.observations]}
            )
            arm.repetitions.append(merged)
        for case_id, paths in cases.items():
            raw = next(paths[0].parent.glob("*.raw.json"), None)
            if raw is not None:
                arm.access[case_id] = _access(raw)
        for index in range(depth):
            traces: dict[str, dict[str, Any]] = {}
            access: dict[str, tuple[str, int, int]] = {}
            failed: dict[str, set[str]] = {}
            searches: dict[str, tuple[int, int]] = {}
            for case_id, paths in cases.items():
                if index < len(paths):
                    rep_dir = paths[index].parent
                    trace = _trace(rep_dir)
                    if trace is not None:
                        traces[case_id] = trace
                    rep_raw = next(rep_dir.glob("*.raw.json"), None)
                    if rep_raw is not None:
                        access[case_id] = _wire_access(rep_raw)
                    failed[case_id] = set()
                    for log in sorted(rep_dir.glob("*.log")):
                        text = log.read_text(encoding="utf-8", errors="replace")
                        failed[case_id] |= failed_hosts(text)
                        calls, errors = logged_searches(text)
                        prior = searches.get(case_id, (0, 0))
                        searches[case_id] = (prior[0] + calls, prior[1] + errors)
            arm.traces.append(traces)
            arm.access_by_rep.append(access)
            arm.failed_hosts.append(failed)
            arm.search_log.append(searches)
        arms[name] = arm
    return arms


def _read(path: Path) -> Capture:
    return Capture.model_validate_json(path.read_text(encoding="utf-8"))


def _trace(rep_dir: Path) -> dict[str, Any] | None:
    """One repetition's discovery trace: the raw report's, else the checkpoint copy."""
    for path in sorted(rep_dir.glob("*.raw.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            trace = (raw["canary"]["institutions"] or [{}])[0].get("discovery_trace")
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            continue
        if isinstance(trace, dict):
            return trace
    for path in sorted(rep_dir.glob("*.trace.json")):
        try:
            trace = json.loads(path.read_text(encoding="utf-8")).get("discovery_trace")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(trace, dict):
            return trace
    return None


def _access(raw_path: Path) -> tuple[str, int, int]:
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        inst = (raw["canary"]["institutions"] or [{}])[0]
        return (
            str(inst.get("access") or "unknown"),
            int(inst.get("pages_checked") or 0),
            int(inst.get("pages_failed") or 0),
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return ("unknown", 0, 0)


def _wire_access(raw_path: Path) -> tuple[str, int, int]:
    """``_access`` counting only what the site did with requests on the wire (01-Q3).

    Taken out of ``pages_checked``: cache hits and our own privacy refusals
    (no request was sent). Taken out of ``pages_failed``: our privacy refusals
    and a 404 on a robots.txt or sitemap probe (an absent sitemap is the site
    answering, not refusing). unibo base2 off#2, 7 timeouts: 8 failed of 17
    checked, 3 cached, is 8 of 14 — unavailable; um off#2: 5 of its 8 failures
    are probe 404s and 1 a privacy refusal — 2 of 13, readable. The per-case
    ``access`` cell keeps the raw counts.
    """
    state, checked, failed = _access(raw_path)
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        inst = (raw["canary"]["institutions"] or [{}])[0]
        cached = int((inst.get("outcomes") or {}).get("cached") or 0)
        ours = probes = 0
        for url, why in inst.get("failures") or []:
            path = urlsplit(str(url)).path.lower()
            if str(why).startswith("refused_privacy"):
                ours += 1
            elif "HTTP 404" in str(why) and (path == "/robots.txt" or "sitemap" in path):
                probes += 1
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        cached = ours = probes = 0
    failed = max(failed - ours - probes, 0)
    return (state, max(checked - cached - ours, failed), failed)


#: One ``get`` line of a repetition's ``.log`` (``evaluation/research/live.py``).
_GET_START = re.compile(r"^get #(?P<n>\d+) start t=\S+ (?P<url>\S+)")
_GET_DONE = re.compile(r"^get #(?P<n>\d+) took \S+ (?P<outcome>[a-z_]+)")


def _host(url: object) -> str:
    host = (urlsplit(str(url)).hostname or "").lower()
    return host.removeprefix("www.")


def failed_hosts(log_text: str) -> set[str]:
    """The hosts whose every request failed in one repetition's ``.log``.

    ``robots.txt`` is left out: a host that serves its robots file and refuses
    every page (toronto's 403s) is a host we could not read. A cache hit is no
    request. Any outcome but ``ok`` is a failure (HTTP error, timeout, block,
    robots refusal). A host with no request in the log is not failed.
    """
    urls: dict[str, str] = {}
    tally: dict[str, list[bool]] = defaultdict(list)
    for line in log_text.splitlines():
        if match := _GET_START.match(line):
            urls[match["n"]] = match["url"]
        elif (match := _GET_DONE.match(line)) and match["n"] in urls:
            url = urls[match["n"]]
            if match["outcome"] == "cached" or urlsplit(url).path == "/robots.txt":
                continue
            tally[_host(url)].append(match["outcome"] != "ok")
    return {host for host, failed in tally.items() if all(failed)}


_SEARCH_DONE = re.compile(r"^search #\d+ took ", re.MULTILINE)
_SEARCH_FAILED = re.compile(r"^search failed after ", re.MULTILINE)
_FAILURE_HTTP_STATUS = re.compile(r"\bHTTP \d{3}\b")

#: Search-provider health (2026-10-19, the Serper outage): a repetition in
#: which more than this share of all search calls failed measured the
#: provider, not the pipeline, and is never a valid measurement.
SEARCH_FAILURE_LIMIT = 0.2


def logged_searches(log_text: str) -> tuple[int, int]:
    """(search calls, failed search calls) one case log recorded."""
    return len(_SEARCH_DONE.findall(log_text)), len(_SEARCH_FAILED.findall(log_text))


def search_health(
    capture: Capture,
    traces: dict[str, dict[str, Any]],
    logged: dict[str, tuple[int, int]],
) -> dict[str, Any]:
    """How many of a repetition's search calls failed, over every case.

    A case's log is the record of every provider call (discovery and topic
    search alike). A case with no log falls back to its discovery trace, and
    there only a failure that names an HTTP status counts: a strict budget's
    own refusal also leaves a diagnostic, but it never reached the provider.

    Free-search ticket 02: a query the run's ``--max-search-queries`` cap
    refused was never sent either, but the case it belonged to ran short of
    search, so a repetition with any such refusal is unhealthy as well
    (``cap_refused``, present only then).
    """
    calls = failed = 0
    cap_refused = sum(o.telemetry.search_cap_refusals or 0 for o in capture.observations)
    for observation in capture.observations:
        case_calls = observation.telemetry.search_calls or 0
        if observation.case_id in logged:
            log_calls, case_failed = logged[observation.case_id]
            case_calls = max(case_calls, log_calls)
        else:
            diagnostics = (traces.get(observation.case_id) or {}).get("search_failures") or []
            case_failed = sum(bool(_FAILURE_HTTP_STATUS.search(str(d))) for d in diagnostics)
        calls += max(case_calls, case_failed)
        failed += case_failed
    share = round(failed / calls, 3) if calls else 0.0
    return {
        "calls": calls,
        "failed": failed,
        "failed_share": share,
        "healthy": share <= SEARCH_FAILURE_LIMIT and not cap_refused,
        **({"cap_refused": cap_refused} if cap_refused else {}),
    }


def search_warning(columns: list[tuple[str, int, dict[str, Any]]]) -> list[str]:
    """The banner for a run whose search provider failed; empty when it held up."""
    sick = [
        f"{name}#{i} {rep['search_health']['failed']}/{rep['search_health']['calls']}"
        for name, i, rep in columns
        if "search_health" in rep and not rep["search_health"]["healthy"]
    ]
    if not sick:
        return []
    capped = [
        f"{name}#{i} {rep['search_health']['cap_refused']}"
        for name, i, rep in columns
        if rep.get("search_health", {}).get("cap_refused")
    ]
    if capped:
        return [
            "> **WARNING: THE RUN'S SEARCH QUERY CAP WAS REACHED. THIS RUN IS NOT A VALID "
            "MEASUREMENT.** Queries refused by --max-search-queries (no request sent) in: "
            f"{', '.join(capped)}. The cases after the cap ran without search.",
            "",
        ]
    return [
        "> **WARNING: SEARCH PROVIDER UNHEALTHY. THIS RUN IS NOT A VALID MEASUREMENT.** "
        f"More than {SEARCH_FAILURE_LIMIT} of all search calls failed in: "
        f"{', '.join(sick)} (failed/calls). Every number below measures the provider "
        "outage, not the pipeline.",
        "",
    ]


#: H-1 (replay plan 2026-10-19 §5.4): the kinds the recorded provider counts
#: misses by, in the telemetry field order ``recorded_search_misses_<kind>``.
RECORDED_KINDS = ("discovery", "topic", "scholarship", "identity")
#: H-1: misses beyond the off arm's worst repetition a column may have before
#: it reads as "the queries changed", counted on discovery's misses. The plan's
#: §1.4 "<= 2 on dev3" was scholarship/topic noise in the total, which the
#: discovery count leaves out, so the expected A/A excess is 0 (§5.4).
RECORDED_DISCOVERY_TOLERANCE = 0


def recorded_search(capture: Capture) -> dict[str, int] | None:
    """A recorded-search replay's answered and unanswered requests, over every case.

    None for a capture that searched live. On a replay a miss is a request the
    store had no answer for: it was answered with nothing, so the case was
    scored on empty search there. A capture made since H-1 also has the misses
    per search kind (``misses_discovery`` ...) and, on the knockout arm, the
    knockout cases with a discovery miss (their second pass was never
    recorded); a capture made before H-1 has the three totals only.
    """
    replay = capture.config.get("search_provider") == "recorded"
    rows = [
        o.telemetry for o in capture.observations if o.telemetry.recorded_search_misses is not None
    ]
    if not replay and not rows:
        return None
    counts = {
        "hits": sum(t.recorded_search_hits or 0 for t in rows),
        "misses": sum(t.recorded_search_misses or 0 for t in rows),
        "cases_with_miss": sum(1 for t in rows if t.recorded_search_misses),
    }
    if rows and all(t.recorded_search_misses_discovery is not None for t in rows):
        for kind in RECORDED_KINDS:
            counts[f"misses_{kind}"] = sum(
                getattr(t, f"recorded_search_misses_{kind}") or 0 for t in rows
            )
        if any(t.knockout_gold_urls for t in rows):
            counts["knockout_cases_discovery_miss"] = sum(
                1 for t in rows if t.knockout_gold_urls and t.recorded_search_misses_discovery
            )
    return counts


def _recorded_reps(arms: dict[str, Any]) -> list[dict[str, int]]:
    return [
        rep["recorded_search"]
        for arm in arms.values()
        for rep in arm["repetitions"]
        if "recorded_search" in rep
    ]


def recorded_judged_on(arms: dict[str, Any]) -> str:
    """``misses_discovery`` when every replayed repetition has it, else ``misses``.

    H-1 judges the replay target on discovery's misses: the store holds
    discovery's requests only, so the topic, scholarship and identity searches
    miss in every arm and their count varies with what a case read. A run with
    any capture made before H-1 is judged on the total in every column, so two
    columns are never compared on different counts.
    """
    reps = _recorded_reps(arms)
    if reps and all("misses_discovery" in rep for rep in reps):
        return "misses_discovery"
    return "misses"


def recorded_baseline(arms: dict[str, Any]) -> int | None:
    """The misses a replay of unchanged queries has: the off arm's worst repetition.

    Counted as :func:`recorded_judged_on` says: on discovery's misses since
    H-1; on the total for older captures, where the scholarship, topic and
    identity searches miss in every arm and a rule is penalised only for
    misses beyond these. Without an off arm, the fewest misses of any
    repetition. The tolerance is added by :func:`recorded_allowed`.
    """
    key = recorded_judged_on(arms)
    counts = {
        name: [
            rep["recorded_search"][key] for rep in arm["repetitions"] if "recorded_search" in rep
        ]
        for name, arm in arms.items()
    }
    if not any(counts.values()):
        return None
    if counts.get("off"):
        return max(counts["off"])
    return min(v for values in counts.values() for v in values)


def recorded_allowed(key: str, baseline: int) -> int:
    """The most misses a column may have on ``key`` and still read as unchanged queries."""
    return baseline + (RECORDED_DISCOVERY_TOLERANCE if key == "misses_discovery" else 0)


def recorded_warning(
    columns: list[tuple[str, int, dict[str, Any]]],
    baseline: int | None,
    key: str = "misses",
) -> list[str]:
    """The replay's banner: always a note on a replay, a warning when a column misses more.

    With per-kind counts (H-1) the note shows each column's total and its
    misses by kind, and the warning is judged on the discovery misses.
    """
    if baseline is None:
        return []
    by_kind = key == "misses_discovery"

    def shown(replayed: dict[str, Any]) -> str:
        if not by_kind:
            return str(replayed["misses"])
        kinds = ", ".join(kind + " " + str(replayed["misses_" + kind]) for kind in RECORDED_KINDS)
        return f"{replayed['misses']} ({kinds})"

    listed = ", ".join(
        f"{name}#{i} {shown(rep['recorded_search'])}"
        for name, i, rep in columns
        if "recorded_search" in rep
    )
    lines = [
        "> Recorded-search replay: every search was answered from recorded result lists "
        f"(no provider was called). Unanswered requests per column: {listed}.",
        "",
    ]
    if by_kind:
        lines += [
            "> Judged on discovery's misses only: the store holds discovery's requests, so "
            "topic, scholarship and identity searches miss in every arm.",
            "",
        ]
        knocked = [
            f"{name}#{i} knockout: second pass unrecorded on "
            f"{rep['recorded_search']['knockout_cases_discovery_miss']} cases"
            for name, i, rep in columns
            if rep.get("recorded_search", {}).get("knockout_cases_discovery_miss")
        ]
        if knocked:
            lines += ["> " + "; ".join(knocked) + ".", ""]
    allowed = recorded_allowed(key, baseline)
    over = [
        f"{name}#{i}"
        for name, i, rep in columns
        if "recorded_search" in rep and rep["recorded_search"][key] > allowed
    ]
    if over:
        counted = "discovery requests" if by_kind else "requests"
        lines += [
            "> **WARNING: THE QUERIES CHANGED.** "
            f"{', '.join(over)} sent {counted} the recorded store has no answer for "
            f"(more than the {allowed} of the unchanged queries). Those searches returned "
            "nothing, so this replay cannot measure the rule; its numbers are not a result.",
            "",
        ]
    return lines


def case_readable(access: tuple[str, int, int] | None) -> bool:
    """Target 3's "a site the run can read": not ``BLOCKED``, under half its requests failed.

    Owner decision 2026-10-18 (01-Q3): judged per repetition, for targets 3 and
    4 only; a case failing it is ``unavailable`` in that repetition. A case with no raw report (``unknown``, 0 requests) stays readable: nothing
    says the site refused us.
    """
    if access is None:
        return True
    state, checked, failed = access
    return state != "BLOCKED" and not (checked and 2 * failed >= checked)


def label_exclusion(label: Label, hosts_failed: set[str]) -> str | None:
    """Why a known label's evidence is unreadable (``pdf``, ``host_failed``), or ``None``.

    A label is readable when any of its evidence pages is HTML on a host that
    answered a request in that repetition (or was never asked).
    """
    reasons = []
    for item in label.evidence:
        url = str(item.url)
        if urlsplit(url).path.lower().endswith(".pdf"):
            reasons.append("pdf")
        elif _host(url) in hosts_failed:
            reasons.append("host_failed")
        else:
            return None
    if not reasons:
        return None
    return "pdf" if all(r == "pdf" for r in reasons) else "host_failed"


def readable_rows(
    dataset: Dataset,
    outcomes: dict[str, Any],
    programme: dict[str, str],
    access: dict[str, tuple[str, int, int]],
    hosts_failed: dict[str, set[str]],
) -> dict[str, Any]:
    """Targets 3 and 4 for one repetition, with each exclusion's reason (ticket 03).

    ``programme_found_on_readable``: programme hits (twins included, related is
    not a hit) over cases whose programme is ``known`` and which are readable.
    ``wrong_programme_pages``: cases whose returned page is a wrong programme.
    ``core_known_rate`` is ``known core answered``; ``core_known_readable_rate``
    keeps a known core question in its denominator only when the case is
    readable and one of its known labels has readable evidence. A non-English
    page and a case with no programme page found stay in both denominators.
    ``excluded``: case id -> ``access`` (the case left both readable
    denominators) and ``<reason>:<question>`` per core question that left.
    """
    hits: dict[str, set[str]] = defaultdict(set)
    for x in outcomes["labels"]:
        if x["outcome"] == "hit":
            hits[x["case"]].add(x["key"])
    found = found_of = wrong = 0
    answered = known = answered_readable = known_readable = 0
    excluded: dict[str, list[str]] = {}
    for case in dataset.cases:
        if case.id not in programme:
            continue
        readable = case_readable(access.get(case.id))
        reasons: list[str] = [] if readable else ["access"]
        if programme[case.id] == "wrong":
            wrong += 1
        if case.programme_status == "known" and readable:
            found_of += 1
            found += programme[case.id] == "hit"
        labels = [label for label in case.labels if label.status == "known"]
        for name, pattern in CORE_QUESTIONS:
            mine = [label for label in labels if pattern.match(label.key)]
            if not mine:
                continue
            answer = any(map(pattern.match, hits[case.id]))
            known += 1
            answered += answer
            if not readable:
                continue
            why = [label_exclusion(label, hosts_failed.get(case.id, set())) for label in mine]
            if all(why):
                reasons.append(f"{why[0]}:{name}")
                continue
            known_readable += 1
            answered_readable += answer
        if reasons:
            excluded[case.id] = reasons
    return {
        "programme_found_on_readable": ratio(found, found_of),
        "wrong_programme_pages": wrong,
        "core_known_rate": ratio(answered, known),
        "core_known_readable_rate": ratio(answered_readable, known_readable),
        "excluded": excluded,
    }


def build(
    dataset: Dataset,
    arms: dict[str, Arm],
    *,
    allow_drafts: bool = False,
    count_timeouts_over_budget: bool = True,
    core_denominator: str = "readable",
) -> dict[str, Any]:
    """The scorecard as data: metrics, label outcomes, changes, core, cost.

    ``core_denominator`` (``readable``, or ``all`` for today's old measure)
    picks the denominator target 4 is judged on.
    """
    card: dict[str, Any] = {"dataset_version": dataset.version, "arms": {}}
    for name, arm in arms.items():
        reps = []
        for index, capture in enumerate(arm.repetitions):
            report = score(dataset, capture, allow_drafts=allow_drafts)
            outcomes = label_outcomes(dataset, capture)
            traces = arm.traces[index] if index < len(arm.traces) else {}
            observed = {o.case_id: o for o in capture.observations}
            programme_outcomes = {
                case.id: adjudicate_programme_pages(case, observed[case.id]).outcome
                for case in dataset.cases
                if case.id in observed
            }
            reps.append(
                {
                    "pipeline_sha": capture.pipeline_sha,
                    "metrics": report["metrics"],
                    "outcomes": outcomes,
                    "core": core_coverage(capture),
                    "core_known": core_known(dataset, outcomes),
                    "cost": cost(capture, count_timeouts=count_timeouts_over_budget),
                    "programme_pages": programme_outcomes,
                    "readable": readable_rows(
                        dataset,
                        outcomes,
                        programme_outcomes,
                        arm.access_by_rep[index] if index < len(arm.access_by_rep) else {},
                        arm.failed_hosts[index] if index < len(arm.failed_hosts) else {},
                    ),
                    # v3-M3: only cases that went through the identity gate.
                    "site_identity": {
                        o.case_id: o.site_identity.established
                        for o in capture.observations
                        if o.site_identity is not None
                    },
                    "gold_seen": {
                        case.id: gold_seen(case, observed[case.id], traces.get(case.id))
                        for case in dataset.cases
                        if case.id in observed
                    },
                    "programme": programme_pages(dataset, capture, report),
                    "search_health": search_health(
                        capture,
                        traces,
                        arm.search_log[index] if index < len(arm.search_log) else {},
                    ),
                    **(
                        {"recorded_search": replayed}
                        if (replayed := recorded_search(capture)) is not None
                        else {}
                    ),
                    # G-06: which entry path the arm took (absent = the default).
                    "entry_path": str(capture.config.get("entry_path") or "default"),
                }
            )
        card["arms"][name] = {
            "repetitions": reps,
            "access": arm.access,
            "traced": bool(arm.traces and any(arm.traces[0].values())),
        }
    if {"off", "on"} <= set(arms):
        card["changes"] = stable_changes(card["arms"]["off"], card["arms"]["on"])
    card["targets"] = check_targets(card, core_denominator=core_denominator)
    return card


def stable_changes(off: dict[str, Any], on: dict[str, Any]) -> dict[str, list[str]]:
    """Labels every ``on`` repetition hits and every ``off`` one misses, or the reverse."""

    def hits(arm: dict[str, Any]) -> list[set[str]]:
        return [
            {f"{x['case']}:{x['key']}" for x in rep["outcomes"]["labels"] if x["outcome"] == "hit"}
            for rep in arm["repetitions"]
        ]

    off_hits, on_hits = hits(off), hits(on)
    always_on = set.intersection(*on_hits) if on_hits else set()
    never_on = set.union(*on_hits) if on_hits else set()
    always_off = set.intersection(*off_hits) if off_hits else set()
    never_off = set.union(*off_hits) if off_hits else set()
    everything = never_on | never_off
    gained = sorted(always_on - never_off)
    lost = sorted(always_off - never_on)
    unstable = sorted(everything - always_on - always_off - set(gained) - set(lost))
    return {"gained": gained, "lost": lost, "unstable": unstable}


def _worst_row(name: str, metric: str, values: list[Any]) -> dict[str, Any] | None:
    op, target = TARGETS[metric]
    known = [v for v in values if v is not None]
    if not known:
        return None
    worst = min(known) if op == ">=" else max(known)
    met = worst >= target if op == ">=" else worst <= target
    return {"arm": name, "metric": metric, "worst": worst, "target": f"{op} {target}", "met": met}


def check_targets(
    card: dict[str, Any], *, core_denominator: str = "readable"
) -> list[dict[str, Any]]:
    """Each Definition-of-Done target, judged on the worst repetition of each arm.

    Targets 3 and 4 follow the scorer's rows and the budget, so the rows that
    were there before ticket 03 keep their place. Targets 3 and 4 leave a case
    out of the repetition in which its site was unavailable (01-Q3).
    """
    core_metric = CORE_DENOMINATORS[core_denominator]
    rows = []
    baseline = recorded_baseline(card["arms"])
    judged_on = recorded_judged_on(card["arms"])
    for name, arm in card["arms"].items():
        for metric, (op, target) in TARGETS.items():
            if metric not in arm["repetitions"][0]["metrics"]:
                continue
            values = [rep["metrics"][metric]["value"] for rep in arm["repetitions"]]
            known = [v for v in values if v is not None]
            if not known:
                continue
            worst = min(known) if op == ">=" else max(known)
            met = worst >= target if op == ">=" else worst <= target
            rows.append(
                {
                    "arm": name,
                    "metric": metric,
                    "worst": worst,
                    "target": f"{op} {target}",
                    "met": met,
                }
            )
        over = sum(
            1 for rep in arm["repetitions"] for row in rep["cost"].values() if row["over_budget"]
        )
        rows.append(
            {
                "arm": name,
                "metric": "cases_over_budget",
                "worst": over,
                "target": "== 0",
                "met": over == 0,
            }
        )
        if all("readable" in rep for rep in arm["repetitions"]):
            for metric in ("programme_found_on_readable", "wrong_programme_pages", core_metric):
                values = [rep["readable"][metric] for rep in arm["repetitions"]]
                row = _worst_row(
                    name, metric, [v["value"] if isinstance(v, dict) else v for v in values]
                )
                if row is not None:
                    rows.append(row)
        # Only on an outage, so a healthy run's targets read as they always did.
        health = [rep["search_health"] for rep in arm["repetitions"] if "search_health" in rep]
        if any(not h["healthy"] for h in health):
            rows.append(
                {
                    "arm": name,
                    "metric": "search_provider_healthy",
                    "worst": max(h["failed_share"] for h in health),
                    "target": f"<= {SEARCH_FAILURE_LIMIT}",
                    "met": all(h["healthy"] for h in health),
                }
            )
        # Recorded-search replay only: misses beyond the unchanged queries',
        # on discovery's misses since H-1 (on the total for older captures).
        misses = [
            rep["recorded_search"][judged_on]
            for rep in arm["repetitions"]
            if "recorded_search" in rep
        ]
        if baseline is not None and misses:
            allowed = recorded_allowed(judged_on, baseline)
            rows.append(
                {
                    "arm": name,
                    "metric": "recorded_search_misses",
                    "worst": max(misses),
                    "target": f"<= {allowed}"
                    + (" discovery" if judged_on == "misses_discovery" else ""),
                    "met": max(misses) <= allowed,
                }
            )
    return rows


_SHOWN = (
    "programme_page_recall",
    "claim_precision",
    "claim_recall",
    "wrong_scope_claim_rate",
    "other_scope_claim_rate",
    "partial_claim_rate",
    "critical_field_coverage",
    "unsupported_claim_rate",
)


def _entry_path_line(lines: list[str], paths: list[str]) -> None:
    """G-06: the arm header's entry-path row, once an arm left the default path."""
    if any(path != "default" for path in paths):
        lines.append("| entry path | " + " | ".join(paths) + " |")


def render(card: dict[str, Any]) -> str:
    """The scorecard as Markdown, short enough to read in a PR."""
    lines = [f"# Scorecard — corpus {card['dataset_version']}", ""]
    columns = [
        (name, i, rep)
        for name, arm in card["arms"].items()
        for i, rep in enumerate(arm["repetitions"], 1)
    ]
    lines += search_warning(columns)
    lines += recorded_warning(
        columns, recorded_baseline(card["arms"]), recorded_judged_on(card["arms"])
    )
    lines.append("| metric | " + " | ".join(f"{n}#{i}" for n, i, _ in columns) + " |")
    lines.append("|---|" + "---|" * len(columns))
    _entry_path_line(lines, [rep.get("entry_path", "default") for _, _, rep in columns])
    for metric in _SHOWN:
        cells = [
            f"{rep['metrics'][metric]['numerator']}/{rep['metrics'][metric]['denominator']}"
            for _, _, rep in columns
        ]
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")
    core = [sum(len(v) for v in rep["core"].values()) for _, _, rep in columns]
    cases = [len(rep["core"]) * len(CORE_QUESTIONS) for _, _, rep in columns]
    lines.append(
        "| core questions answered | "
        + " | ".join(f"{a}/{b}" for a, b in zip(core, cases, strict=True))
        + " |"
    )
    lines.append(
        "| known core answered | "
        + " | ".join(
            f"{sum(v['answered'] for v in rep['core_known'].values())}"
            f"/{sum(v['known'] for v in rep['core_known'].values())}"
            for _, _, rep in columns
        )
        + " |"
    )
    if all("readable" in rep for _, _, rep in columns):
        # Ticket 03: targets 3 and 4 on what the run could read, beside the old rows.
        for label, metric in (
            ("known core answered (readable)", "core_known_readable_rate"),
            ("programme page on readable", "programme_found_on_readable"),
        ):
            lines.append(
                f"| {label} | "
                + " | ".join(
                    f"{rep['readable'][metric]['numerator']}"
                    f"/{rep['readable'][metric]['denominator']}"
                    for _, _, rep in columns
                )
                + " |"
            )
        lines.append(
            "| wrong programme pages | "
            + " | ".join(str(rep["readable"]["wrong_programme_pages"]) for _, _, rep in columns)
            + " |"
        )
    if any("programme_pages" in rep for _, _, rep in columns):
        # v3-M2: a related programme is neither a hit nor a wrong page.
        outcome_names = [o for o in PROGRAMME_OUTCOMES if o != "unadjudicated"]
        lines.append(
            f"| programme pages {'/'.join(outcome_names)} | "
            + " | ".join(
                "/".join(
                    str(sum(1 for v in rep.get("programme_pages", {}).values() if v == o))
                    for o in outcome_names
                )
                for _, _, rep in columns
            )
            + " |"
        )
    if any(rep.get("site_identity") for _, _, rep in columns):
        # v3-M3: shown once a case went through production's identity gate.
        lines.append(
            "| identity established | "
            + " | ".join(
                f"{sum(rep.get('site_identity', {}).values())}/{len(rep.get('site_identity', {}))}"
                for _, _, rep in columns
            )
            + " |"
        )
    reads = [sum(r["http_fetches"] or 0 for r in rep["cost"].values()) for _, _, rep in columns]
    lines.append("| reads (all cases) | " + " | ".join(str(r) for r in reads) + " |")
    if "changes" in card:
        ch = card["changes"]
        lines += [
            "",
            f"**Stable gains** ({len(ch['gained'])}): " + (", ".join(ch["gained"]) or "none"),
        ]
        lines.append(f"**Stable losses** ({len(ch['lost'])}): " + (", ".join(ch["lost"]) or "none"))
        lines.append(f"Unstable ({len(ch['unstable'])}): " + (", ".join(ch["unstable"]) or "none"))
    lines += [
        "",
        "## Targets (worst repetition)",
        "",
        "| arm | metric | worst | target | met |",
        "|---|---|---|---|---|",
    ]
    for row in card["targets"]:
        worst = row["worst"]
        shown = f"{worst:.3f}" if isinstance(worst, float) else str(worst)
        met = "yes" if row["met"] else "NO"
        lines.append(f"| {row['arm']} | {row['metric']} | {shown} | {row['target']} | {met} |")
    last_arm = list(card["arms"])[-1]
    rep = card["arms"][last_arm]["repetitions"][0]
    lines += ["", f"## Wrong claims ({last_arm}, every repetition)", ""]
    # The same fact quoted from several pages, or in several repetitions, is
    # one finding, counted. A wrong value in any repetition is a finding.
    seen: dict[tuple[str, str, str, str, str], int] = defaultdict(int)
    for each in card["arms"][last_arm]["repetitions"]:
        for w in each["outcomes"]["wrong_claims"]:
            ours, expected = json.dumps(w["value"])[:80], json.dumps(w["expected"])[:80]
            seen[(w["case"], w["key"], ours, expected, w["why"])] += 1
    for (case_id, key, ours, expected, why), n in seen.items():
        times = f" ×{n}" if n > 1 else ""
        lines.append(f"- {case_id} `{key}`: ours {ours} vs {expected} ({why}){times}")
    if not seen:
        lines.append("- none")
    counts: dict[str, int] = defaultdict(int)
    for x in rep["outcomes"]["labels"]:
        counts[x["outcome"]] += 1
    lines += ["", f"## Known labels by outcome ({last_arm}#1)", ""]
    lines.append(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    # Seconds before the first query, shown once any case recorded it.
    first_query = any("t_first_query" in row for row in rep["cost"].values())
    # WF-17: where the gold programme page got to, shown once a case of this
    # repetition carried a trace; a run without traces keeps its table shape.
    traced = bool(card["arms"][last_arm].get("traced"))
    gold = rep.get("gold_seen") or {}
    # Ticket 03: why a case or its core labels left a readable denominator, and
    # the programme hit's stability over the arm's repetitions (ticket 04's input).
    readable = "readable" in rep
    arm_reps = card["arms"][last_arm]["repetitions"]
    lines += [
        "",
        f"## Per case ({last_arm}#1)",
        "",
        "| case | access | page | hits | core | core known | queries | reads | s |"
        + (" 1st query s |" if first_query else "")
        + (" gold seen |" if traced else "")
        + (" excluded | page n/N |" if readable else ""),
        "|---|---|---|---|---|---|---|---|---|"
        + ("---|" if first_query else "")
        + ("---|" if traced else "")
        + ("---|---|" if readable else ""),
    ]
    access = card["arms"][last_arm]["access"]
    for case_id, row in rep["cost"].items():
        hits = sum(
            1 for x in rep["outcomes"]["labels"] if x["case"] == case_id and x["outcome"] == "hit"
        )
        known = sum(1 for x in rep["outcomes"]["labels"] if x["case"] == case_id)
        acc = access.get(case_id, ("unknown", 0, 0))
        lines.append(
            f"| {case_id} | {acc[0]} ({acc[2]}/{acc[1]} failed) | "
            f"{rep.get('programme', {}).get(case_id, '-')} | {hits}/{known} | "
            f"{len(rep['core'].get(case_id, []))}/6 | "
            f"{rep['core_known'].get(case_id, {}).get('answered', 0)}"
            f"/{rep['core_known'].get(case_id, {}).get('known', 0)} | "
            f"{row['search_calls']} | {row['http_fetches']} | {row['latency_seconds']} |"
            + (f" {row.get('t_first_query', '-')} |" if first_query else "")
            + (f" {_gold_cell(gold.get(case_id))} |" if traced else "")
            + (
                f" {_excluded_cell(rep, case_id)} | {_stability(arm_reps, case_id)} |"
                if readable
                else ""
            )
        )
    return "\n".join(lines) + "\n"


def _excluded_cell(rep: dict[str, Any], case_id: str) -> str:
    """Why a case (``access``) or its core questions (``pdf:``, ``host_failed:``) left."""
    return ", ".join(rep["readable"]["excluded"].get(case_id, [])) or "-"


def _stability(reps: list[dict[str, Any]], case_id: str) -> str:
    """``n/N``: the programme page hit in n of the N repetitions that ran the case."""
    seen = [r["programme_pages"][case_id] for r in reps if case_id in r.get("programme_pages", {})]
    if not seen or all(v == "unadjudicated" for v in seen):
        return "-"
    return f"{sum(v == 'hit' for v in seen)}/{len(seen)}"


def _gold_cell(seen: dict[str, Any] | None) -> str:
    """``stage (how it was seen)`` for the per-case table."""
    if not seen:
        return "-"
    how = ", ".join(seen.get("seen_as") or [])
    return f"{seen['stage']} ({how})" if how else str(seen["stage"])


def _counted(values: Iterable[Any]) -> dict[str, int]:
    """Value -> how many times it occurs in ``values``, sorted by value."""
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[str(value)] += 1
    return dict(sorted(counts.items()))


def summarize(card: dict[str, Any]) -> dict[str, Any]:
    """The scorecard's aggregates only, for a look at the heldout split (ticket 19).

    Per arm and repetition: the metric ratios, the readable rows, and counts —
    of cases scored, unavailable, excluded, by programme outcome, by access.
    No case id, URL, claim value or label leaves this function: the stable
    gains and losses and the wrong claims become counts.
    """

    def ratio_of(value: dict[str, Any]) -> dict[str, Any]:
        return {k: value[k] for k in ("numerator", "denominator", "value")}

    arms: dict[str, Any] = {}
    for name, arm in card["arms"].items():
        reps = []
        for rep in arm["repetitions"]:
            core_known_rows = rep["core_known"].values()
            row: dict[str, Any] = {
                "pipeline_sha": rep["pipeline_sha"],
                "entry_path": rep.get("entry_path", "default"),
                "cases_scored": len(rep["cost"]),
                "metrics": {k: ratio_of(v) for k, v in sorted(rep["metrics"].items())},
                "core_questions_answered": {
                    "numerator": sum(len(v) for v in rep["core"].values()),
                    "denominator": len(rep["core"]) * len(CORE_QUESTIONS),
                },
                "known_core_answered": {
                    "numerator": sum(v["answered"] for v in core_known_rows),
                    "denominator": sum(v["known"] for v in core_known_rows),
                },
                "programme_pages": _counted(rep.get("programme_pages", {}).values()),
                "identity_established": {
                    "numerator": sum(rep.get("site_identity", {}).values()),
                    "denominator": len(rep.get("site_identity", {})),
                },
                "reads": sum(r["http_fetches"] or 0 for r in rep["cost"].values()),
                "cases_over_budget": sum(1 for r in rep["cost"].values() if r["over_budget"]),
                "wrong_claims": len(rep["outcomes"]["wrong_claims"]),
                **({"search_health": dict(rep["search_health"])} if "search_health" in rep else {}),
                **(
                    {"recorded_search": dict(rep["recorded_search"])}
                    if "recorded_search" in rep
                    else {}
                ),
                "known_labels_by_outcome": _counted(
                    x["outcome"] for x in rep["outcomes"]["labels"]
                ),
            }
            if "readable" in rep:
                readable = rep["readable"]
                reasons = [r for why in readable["excluded"].values() for r in why]
                row["readable"] = {
                    "programme_found_on_readable": ratio_of(
                        readable["programme_found_on_readable"]
                    ),
                    "wrong_programme_pages": readable["wrong_programme_pages"],
                    "core_known_rate": ratio_of(readable["core_known_rate"]),
                    "core_known_readable_rate": ratio_of(readable["core_known_readable_rate"]),
                }
                row["unavailable_cases"] = reasons.count("access")
                row["excluded_cases"] = len(readable["excluded"])
                row["excluded_core_questions"] = _counted(
                    r.split(":", 1)[0] for r in reasons if r != "access"
                )
            reps.append(row)
        arms[name] = {
            "repetitions": reps,
            "access": _counted(v[0] for v in arm["access"].values()),
        }
    summary: dict[str, Any] = {
        "dataset_version": card["dataset_version"],
        "summary_only": True,
        "arms": arms,
        "targets": [dict(row) for row in card["targets"]],
    }
    if "changes" in card:
        summary["changes"] = {k: len(v) for k, v in card["changes"].items()}
    return summary


def render_summary(summary: dict[str, Any]) -> str:
    """``summarize``'s aggregates as Markdown: no per-case row, id, URL or value."""
    lines = [f"# Scorecard (summary only) — corpus {summary['dataset_version']}", ""]
    columns = [
        (name, i, rep)
        for name, arm in summary["arms"].items()
        for i, rep in enumerate(arm["repetitions"], 1)
    ]
    lines += search_warning(columns)
    lines += recorded_warning(
        columns, recorded_baseline(summary["arms"]), recorded_judged_on(summary["arms"])
    )

    def frac(value: dict[str, Any]) -> str:
        return f"{value['numerator']}/{value['denominator']}"

    def line(label: str, cells: list[str]) -> None:
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    line("metric", [f"{n}#{i}" for n, i, _ in columns])
    lines.append("|---|" + "---|" * len(columns))
    _entry_path_line(lines, [rep.get("entry_path", "default") for *_, rep in columns])
    for metric in _SHOWN:
        if all(metric in rep["metrics"] for _, _, rep in columns):
            line(metric, [frac(rep["metrics"][metric]) for _, _, rep in columns])
    line("core questions answered", [frac(rep["core_questions_answered"]) for *_, rep in columns])
    line("known core answered", [frac(rep["known_core_answered"]) for *_, rep in columns])
    if all("readable" in rep for _, _, rep in columns):
        for label, metric in (
            ("known core answered (readable)", "core_known_readable_rate"),
            ("programme page on readable", "programme_found_on_readable"),
        ):
            line(label, [frac(rep["readable"][metric]) for *_, rep in columns])
        line(
            "wrong programme pages",
            [str(rep["readable"]["wrong_programme_pages"]) for *_, rep in columns],
        )
        line("unavailable cases", [str(rep["unavailable_cases"]) for *_, rep in columns])
        line("excluded cases", [str(rep["excluded_cases"]) for *_, rep in columns])
        line(
            "excluded core questions",
            [
                ", ".join(f"{k}: {v}" for k, v in rep["excluded_core_questions"].items()) or "0"
                for *_, rep in columns
            ],
        )
    outcome_names = [o for o in PROGRAMME_OUTCOMES if o != "unadjudicated"]
    line(
        f"programme pages {'/'.join(outcome_names)}",
        [
            "/".join(str(rep["programme_pages"].get(o, 0)) for o in outcome_names)
            for *_, rep in columns
        ],
    )
    line("identity established", [frac(rep["identity_established"]) for *_, rep in columns])
    line("cases scored", [str(rep["cases_scored"]) for *_, rep in columns])
    line("cases over budget", [str(rep["cases_over_budget"]) for *_, rep in columns])
    line("reads (all cases)", [str(rep["reads"]) for *_, rep in columns])
    line("wrong claims", [str(rep["wrong_claims"]) for *_, rep in columns])
    if all("search_health" in rep for *_, rep in columns):
        line(
            "search calls failed",
            [
                f"{rep['search_health']['failed']}/{rep['search_health']['calls']}"
                for *_, rep in columns
            ],
        )
    if all("recorded_search" in rep for *_, rep in columns):
        line(
            "recorded search answered/missed",
            [
                f"{rep['recorded_search']['hits']}/{rep['recorded_search']['misses']}"
                for *_, rep in columns
            ],
        )
    if all("misses_discovery" in rep.get("recorded_search", {}) for *_, rep in columns):
        line(
            "recorded search missed: discovery/topic/scholarship/identity",
            [
                "/".join(str(rep["recorded_search"]["misses_" + kind]) for kind in RECORDED_KINDS)
                for *_, rep in columns
            ],
        )
    if "changes" in summary:
        ch = summary["changes"]
        lines += [
            "",
            f"**Stable gains**: {ch['gained']} · **Stable losses**: {ch['lost']} · "
            f"Unstable: {ch['unstable']}",
        ]
    lines += ["", "## Access (cases per status, first repetition)", ""]
    for name, arm in summary["arms"].items():
        shown = ", ".join(f"{k}: {v}" for k, v in arm["access"].items()) or "none recorded"
        lines.append(f"- {name}: {shown}")
    lines += [
        "",
        "## Targets (worst repetition)",
        "",
        "| arm | metric | worst | target | met |",
        "|---|---|---|---|---|",
    ]
    for row in summary["targets"]:
        worst = row["worst"]
        shown = f"{worst:.3f}" if isinstance(worst, float) else str(worst)
        met = "yes" if row["met"] else "NO"
        lines.append(f"| {row['arm']} | {row['metric']} | {shown} | {row['target']} | {met} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "run_dir", type=Path, help="unpacked paired-run artifact, or one capture.json"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).parent / "data" / "ground_truth.reviewed11.json",
    )
    parser.add_argument("--allow-drafts", action="store_true")
    parser.add_argument(
        "--count-timeouts-over-budget",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="count a case the wall clock ended as over the latency budget (owner decision "
        "2026-10-18: on; --no-count-timeouts-over-budget restores the old measure)",
    )
    parser.add_argument(
        "--core-denominator",
        choices=sorted(CORE_DENOMINATORS),
        default="readable",
        help="target 4's denominator: the known core questions whose evidence the run could "
        "read (owner decision 2026-10-18, the default), or every known core question (all)",
    )
    parser.add_argument("--out", type=Path, help="write the full scorecard as JSON here")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="print and write aggregates only: no per-case row, case id, URL, claim value, "
        "label or gain/loss list (the heldout look, finish-algorithm ticket 19)",
    )
    args = parser.parse_args(argv)
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    card = build(
        dataset,
        load_run(args.run_dir),
        allow_drafts=args.allow_drafts,
        count_timeouts_over_budget=args.count_timeouts_over_budget,
        core_denominator=args.core_denominator,
    )
    shown = summarize(card) if args.summary_only else card
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(shown, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
        )
    print(render_summary(shown) if args.summary_only else render(card), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
