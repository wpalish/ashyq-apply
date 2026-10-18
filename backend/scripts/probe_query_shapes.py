"""Plan v3 M5: which query shape returns a local-language programme page?

Ticket 07 (owner, 2026-10-18): up to 300 Serper credits, five query shapes
times six local-language development cases, run once on the GitHub runner
where the key is a secret. A shape that returns the gold programme page (or a
canonical variant of it, or a gold twin) in the top 10 on at least four of the
six cases becomes the ``local_language`` query family of rule R5, in the third
first-pass slot; ``programmes`` moves to the reserve and ``admissions`` is
dropped. No shape that clears the bar means R5 does not exist.

The five shapes (ticket 07 Q2):

* ``a_today``: today's ``field_and_degree`` family, without the intake year,
  ``site:{domain} "computer science" "bachelor"``;
* ``b_alias_or``: QA-1's OR-group of the ontology's strong English aliases;
* ``c_local``: the ontology's localized alias in the site's language with the
  local bachelor word, ``site:uio.no informatikk bachelor``;
* ``d_local_hl_gl``: shape c, with Serper ``hl``/``gl`` set to the site's
  language and country;
* ``e_local_natural``: unquoted natural language in the local language, no
  ``site:``.

Every word comes from the institution (its name, domain and country's
language), the request's public field and degree words, or the bundled
ontology — never from an applicant (I3). Each query is validated by the same
privacy check discovery uses before anything is sent.

The probe reads the development gold files only. It refuses a split that is
not ``development`` and never names a held-out case.

Run from ``backend`` (dry run by default; ``--live`` spends credits)::

    PYTHONPATH=. python scripts/probe_query_shapes.py --out out/query-probe
    UNIMATCH_SEARCH_PROVIDER=serper UNIMATCH_SERPER_API_KEY=... \\
        PYTHONPATH=. python scripts/probe_query_shapes.py --live --out out/query-probe
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from app.adapters.search.base import (
    SearchError,
    SearchProvider,
    SearchResponse,
    search_failure_diagnostic,
)
from app.adapters.search.intent import (
    DiscoveryIntent,
    _reject_applicant_data,
    queries_for,
)
from app.adapters.search.ontology import canonical_field, load_ontology
from app.domain.enums import DegreeLevel
from evaluation.research.metrics import same_programme_page
from evaluation.research.schema import Case, Dataset

#: The owner's budget (ticket 07 Q1). A hard ceiling, not a default: the plan
#: is refused before the first request when it would exceed this, and the
#: sender refuses the 301st request even if the plan was wrong.
MAX_PROBE_QUERIES = 300
#: Results read per query (ticket 07 Q2: "in the top 10").
TOP_K = 10
#: Ticket 07 Q2: a shape joins the first pass when it returns the gold or a
#: twin in the top 10 on at least this many of the six cases.
FIRST_PASS_THRESHOLD = 4
EXPECTED_CASES = 6

SHAPES = ("a_today", "b_alias_or", "c_local", "d_local_hl_gl", "e_local_natural")

#: Development gold files the probe reads. dev4 is not among them: ticket 07
#: names its six cases from dev2/dev3 and was decided before dev4 existed.
DEFAULT_DATASETS = (
    Path("evaluation/research/data/dev2.draft1.json"),
    Path("evaluation/research/data/dev3.draft1.json"),
)

#: Held-out ids (ticket 21). Named only so the probe can refuse them.
HELDOUT_IDS = frozenset(
    {"nu", "metu", "sabanci", "charles", "masaryk", "tum", "tartu", "polimi", "vilnius"}
)


@dataclass(frozen=True, slots=True)
class LocalTerms:
    """The institution's own-language words for one case. Institution data only.

    ``alias`` must be one of the ontology's ``localized_aliases`` for
    ``language``; ``degree_word`` is the local name of the bachelor level (the
    ontology has no localized degree words yet: R5 would add them).
    """

    language: str
    hl: str
    gl: str
    alias: str
    degree_word: str
    local_name: str


#: Ticket 07 names uba, puc, uio, kuleuven, tec-es and tsinghua-cn. tec has no
#: gold programme page in dev2 (``programme_status: unknown``), so it cannot be
#: scored; psaclay (French-only gold) takes its place. ucph and chula are
#: available through ``--cases`` and are not in the default six.
LOCAL_TERMS: dict[str, LocalTerms] = {
    "uba": LocalTerms(
        "es",
        "es",
        "ar",
        "ciencias de la computación",
        "licenciatura",
        "Universidad de Buenos Aires",
    ),
    "puc": LocalTerms(
        "es",
        "es",
        "cl",
        "ciencia de la computación",
        "licenciatura",
        "Pontificia Universidad Católica de Chile",
    ),
    "uio": LocalTerms("no", "no", "no", "informatikk", "bachelor", "Universitetet i Oslo"),
    "kuleuven": LocalTerms("nl", "nl", "be", "informatica", "bachelor", "KU Leuven"),
    "psaclay": LocalTerms("fr", "fr", "fr", "informatique", "licence", "Université Paris-Saclay"),
    "tsinghua": LocalTerms("zh", "zh-cn", "cn", "计算机科学与技术", "本科", "清华大学"),
    "ucph": LocalTerms("da", "da", "dk", "datalogi", "bachelor", "Københavns Universitet"),
    "chula": LocalTerms("th", "th", "th", "วิทยาการคอมพิวเตอร์", "ปริญญาตรี", "จุฬาลงกรณ์มหาวิทยาลัย"),
}
DEFAULT_CASES = ("uba", "puc", "uio", "kuleuven", "psaclay", "tsinghua")


class ProbeBudgetExceeded(RuntimeError):
    """The probe would send more than its budget allows; nothing more is sent."""


class LocalizedSearch(Protocol):
    async def search_localized(
        self,
        *,
        query: str,
        hl: str,
        gl: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse: ...


@dataclass(frozen=True, slots=True)
class PlannedQuery:
    case_id: str
    shape: str
    text: str
    hl: str = ""
    gl: str = ""


@dataclass(slots=True)
class ShapeResult:
    case_id: str
    shape: str
    query: str
    hl: str
    gl: str
    status: str = "planned"  # planned | ok | error | unsupported
    error: str = ""
    top: list[dict[str, Any]] = field(default_factory=list)
    gold_rank: int | None = None
    gold_url: str = ""
    matched_gold: str = ""
    related_rank: int | None = None


def _quoted(term: str) -> str:
    return f'"{term}"' if " " in term else term


def _strong_alias_group(field_words: str) -> str:
    """QA-1's OR-group, as ``intent._field_terms`` renders it with the flag on."""
    key = canonical_field(field_words)
    names = [field_words]
    if key is not None:
        for alias in load_ontology().fields[key]["strong_aliases"]:
            if alias.casefold() not in (n.casefold() for n in names):
                names.append(alias)
    if len(names) == 1:
        return f'"{field_words}"'
    return "(" + " OR ".join(_quoted(n) for n in names) + ")"


def check_local_terms(case: Case, terms: LocalTerms) -> None:
    """The alias must be the ontology's, in the case's language."""
    key = canonical_field(case.request.field or "")
    if key is None:
        raise ValueError(f"{case.id}: field {case.request.field!r} is not in the ontology")
    known = {
        (entry["language"], entry["alias"])
        for entry in load_ontology().fields[key].get("localized_aliases", [])
    }
    if (terms.language, terms.alias) not in known:
        raise ValueError(
            f"{case.id}: {terms.alias!r} is not an ontology alias in {terms.language!r}"
        )


def plan_case(case: Case, terms: LocalTerms) -> list[PlannedQuery]:
    """Exactly the five shapes for one case, each through the privacy check."""
    check_local_terms(case, terms)
    degree = DegreeLevel(case.request.degree or "bachelor")
    field_words = case.request.field or ""
    # Both intents validate every value with discovery's applicant-data check.
    english = DiscoveryIntent(
        institution=case.university, domain=case.domain, degree=degree, field=field_words
    )
    DiscoveryIntent(
        institution=terms.local_name, domain=case.domain, degree=degree, field=terms.alias
    )
    site = f"site:{case.domain}"
    (today,) = queries_for(english, families=("field_and_degree",))
    local = f"{site} {_quoted(terms.alias)} {terms.degree_word}"
    planned = [
        PlannedQuery(case.id, "a_today", today.text),
        PlannedQuery(
            case.id, "b_alias_or", f'{site} {_strong_alias_group(field_words)} "bachelor"'
        ),
        PlannedQuery(case.id, "c_local", local),
        PlannedQuery(case.id, "d_local_hl_gl", local, hl=terms.hl, gl=terms.gl),
        PlannedQuery(
            case.id,
            "e_local_natural",
            f"{terms.local_name} {terms.degree_word} {terms.alias}",
        ),
    ]
    for query in planned:
        _reject_applicant_data("query", query.text)
    return planned


def load_cases(datasets: Sequence[Path], case_ids: Sequence[str]) -> list[Case]:
    held = sorted(set(case_ids) & HELDOUT_IDS)
    if held:
        raise ValueError(f"Held-out cases are never probed: {held}")
    unknown = sorted(set(case_ids) - LOCAL_TERMS.keys())
    if unknown:
        raise ValueError(f"No local terms for {unknown}; known: {sorted(LOCAL_TERMS)}")
    by_id: dict[str, Case] = {}
    for path in datasets:
        if "heldout" in path.name:
            raise ValueError(f"{path} is a held-out file; the probe reads development gold only")
        dataset = Dataset.model_validate_json(path.read_text(encoding="utf-8"))
        if dataset.split != "development":
            raise ValueError(f"{path} is split {dataset.split!r}; the probe reads development only")
        by_id.update({case.id: case for case in dataset.cases})
    missing = [c for c in case_ids if c not in by_id]
    if missing:
        raise ValueError(f"Cases not in the datasets: {missing}")
    cases = [by_id[c] for c in case_ids]
    unscored = [c.id for c in cases if not c.programme_urls]
    if unscored:
        raise ValueError(f"No gold programme page to score against: {unscored}")
    return cases


def build_plan(cases: Sequence[Case], *, limit: int = MAX_PROBE_QUERIES) -> list[PlannedQuery]:
    if limit > MAX_PROBE_QUERIES:
        raise ProbeBudgetExceeded(f"limit {limit} is over the approved {MAX_PROBE_QUERIES}")
    plan = [q for case in cases for q in plan_case(case, LOCAL_TERMS[case.id])]
    if len(plan) > limit:
        raise ProbeBudgetExceeded(
            f"{len(plan)} queries planned, over the limit of {limit}; nothing was sent"
        )
    return plan


def score_results(case: Case, urls: Sequence[str]) -> tuple[int | None, str, str, int | None]:
    """Rank (1-based) of the first gold page, canonical variant or gold twin.

    The gold's ``programme_urls`` already list a page's twins (ticket 03 Q1),
    so "a twin in the top 10" is "any gold URL, up to a canonical variant".
    A search result has no ``<html lang>``, so ``?lang=`` is not stripped.
    """
    gold = [str(u) for u in case.programme_urls]
    related = [str(u) for u in case.related_programme_urls]
    gold_rank: int | None = None
    gold_url = matched = ""
    related_rank: int | None = None
    for rank, url in enumerate(urls[:TOP_K], start=1):
        if gold_rank is None:
            hit = next((g for g in gold if same_programme_page(url, g)), None)
            if hit is not None:
                gold_rank, gold_url, matched = rank, url, hit
        if related_rank is None and any(same_programme_page(url, r) for r in related):
            related_rank = rank
    return gold_rank, gold_url, matched, related_rank


class _Sender:
    """Counts every request attempt against the ceiling before making it."""

    def __init__(self, provider: SearchProvider, limit: int) -> None:
        self.provider = provider
        self.limit = limit
        self.sent = 0

    async def send(self, query: PlannedQuery) -> SearchResponse:
        if self.sent >= self.limit:
            raise ProbeBudgetExceeded(f"request {self.sent + 1} refused: limit {self.limit}")
        self.sent += 1
        if query.hl or query.gl:
            localized: LocalizedSearch = self.provider  # type: ignore[assignment]
            return await localized.search_localized(
                query=query.text, hl=query.hl, gl=query.gl, max_results=TOP_K
            )
        return await self.provider.search(query=query.text, max_results=TOP_K)


async def run_probe(
    cases: Sequence[Case],
    provider: SearchProvider | None,
    *,
    limit: int = MAX_PROBE_QUERIES,
) -> dict[str, Any]:
    """Send the plan (or only describe it when ``provider`` is None)."""
    plan = build_plan(cases, limit=limit)
    by_id = {case.id: case for case in cases}
    sender = _Sender(provider, limit) if provider is not None else None
    results: list[ShapeResult] = []
    for query in plan:
        row = ShapeResult(query.case_id, query.shape, query.text, query.hl, query.gl)
        results.append(row)
        if sender is None:
            continue
        if (query.hl or query.gl) and not hasattr(sender.provider, "search_localized"):
            row.status = "unsupported"
            row.error = f"{sender.provider.name} takes no hl/gl; not sent"
            continue
        try:
            response = await sender.send(query)
        except SearchError as exc:
            row.status = "error"
            # Fixed public categories only: never a key, a body or the query.
            row.error = search_failure_diagnostic(sender.provider.name, exc)
            continue
        row.status = "ok"
        ordered = sorted(response.results, key=lambda r: r.rank)[:TOP_K]
        row.top = [{"rank": r.rank, "url": r.url, "title": r.title} for r in ordered]
        row.gold_rank, row.gold_url, row.matched_gold, row.related_rank = score_results(
            by_id[query.case_id], [r.url for r in ordered]
        )
    return report(cases, results, provider=provider.name if provider else None, sent=sender)


def report(
    cases: Sequence[Case],
    results: Sequence[ShapeResult],
    *,
    provider: str | None,
    sent: _Sender | None,
) -> dict[str, Any]:
    shapes: dict[str, dict[str, Any]] = {}
    for shape in SHAPES:
        rows = [r for r in results if r.shape == shape]
        ok = [r for r in rows if r.status == "ok"]
        hits = sorted(r.case_id for r in ok if r.gold_rank is not None)
        complete = len(ok) == len(rows) == len(cases)
        shapes[shape] = {
            "hits": len(hits),
            "hit_cases": hits,
            "answered": len(ok),
            "not_answered": sorted(r.case_id for r in rows if r.status != "ok"),
            "joins_first_pass": complete and len(hits) >= FIRST_PASS_THRESHOLD,
            "complete": complete,
        }
    winners = [s for s in SHAPES if shapes[s]["joins_first_pass"]]
    local_winners = [s for s in winners if s not in {"a_today", "b_alias_or"}]
    gold_hosts = {
        case.id: sorted({str(u).split("/")[2] for u in case.programme_urls}) for case in cases
    }
    return {
        "probe": "v3-M5 query-shape probe (ticket 07)",
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": provider,
        "live": provider is not None,
        "query_limit": MAX_PROBE_QUERIES,
        "queries_planned": len(results),
        "requests_sent": sent.sent if sent else 0,
        "top_k": TOP_K,
        "rule": (
            f"a shape with the gold (or a canonical variant / gold twin) in the top {TOP_K} "
            f"on >= {FIRST_PASS_THRESHOLD} of {EXPECTED_CASES} cases joins the first pass; "
            "programmes -> reserve, admissions dropped"
        ),
        "cases": [
            {
                "id": case.id,
                "domain": case.domain,
                "country": case.country,
                "language": LOCAL_TERMS[case.id].language,
                "gold": [str(u) for u in case.programme_urls],
                "gold_outside_site_domain": [
                    host
                    for host in gold_hosts[case.id]
                    if not (host == case.domain or host.endswith("." + case.domain))
                ],
            }
            for case in cases
        ],
        "case_count_matches_rule": len(cases) == EXPECTED_CASES,
        "shapes": shapes,
        "decision": {
            "shapes_joining_first_pass": winners,
            "local_language_shapes_joining": local_winners,
            "r5_exists": bool(local_winners) and provider is not None,
            "complete": provider is not None and all(s["complete"] for s in shapes.values()),
        },
        "results": [asdict(r) for r in results],
    }


def _completeness(data: dict[str, Any]) -> str:
    if not data["live"]:
        return " (dry run: nothing was sent)"
    return "" if data["decision"]["complete"] else " (incomplete: not every query was answered)"


def markdown(data: dict[str, Any]) -> str:
    rows = data["results"]
    case_ids = [c["id"] for c in data["cases"]]
    cell: dict[tuple[str, str], str] = {}
    for r in rows:
        if r["status"] == "ok":
            value = str(r["gold_rank"]) if r["gold_rank"] is not None else "—"
        else:
            value = {"planned": "·", "unsupported": "n/a", "error": "err"}[r["status"]]
        cell[(r["case_id"], r["shape"])] = value
    lines = [
        "# Query-shape probe (v3-M5, ticket 07)",
        "",
        f"Provider: {data['provider'] or 'none (dry run)'} · requests sent: "
        f"{data['requests_sent']} of a {data['query_limit']} limit · {data['generated_at']}",
        "",
        f"Rule: {data['rule']}.",
        "",
        "Cell: rank of the first gold page (or variant / twin) in the top 10; "
        "— not in the top 10; err / n/a not answered; · not sent.",
        "",
        "| case | " + " | ".join(SHAPES) + " |",
        "|---|" + "---|" * len(SHAPES),
    ]
    for case_id in case_ids:
        lines.append(
            f"| {case_id} | " + " | ".join(cell.get((case_id, s), "·") for s in SHAPES) + " |"
        )
    lines.append(
        "| **hits** | "
        + " | ".join(
            f"**{data['shapes'][s]['hits']}**"
            + (" ✓" if data["shapes"][s]["joins_first_pass"] else "")
            for s in SHAPES
        )
        + " |"
    )
    decision = data["decision"]
    lines += [
        "",
        f"Shapes joining the first pass: {', '.join(decision['shapes_joining_first_pass']) or 'none'}."
        f" Local-language shapes joining: {', '.join(decision['local_language_shapes_joining']) or 'none'}."
        f" R5 exists: {'yes' if decision['r5_exists'] else 'no'}"
        f"{_completeness(data)}.",
    ]
    outside = {c["id"]: c["gold_outside_site_domain"] for c in data["cases"]}
    for case_id, hosts in outside.items():
        if hosts:
            lines.append(
                f"- {case_id}: gold host {', '.join(hosts)} is outside `site:` of its domain; "
                "only e_local_natural can return it."
            )
    lines += ["", "## Queries", "", "| case | shape | query | hl/gl |", "|---|---|---|---|"]
    for r in rows:
        locale = f"{r['hl']}/{r['gl']}" if r["hl"] else ""
        lines.append(f"| {r['case_id']} | {r['shape']} | `{r['query']}` | {locale} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", nargs="+", default=list(DEFAULT_CASES))
    parser.add_argument("--dataset", type=Path, action="append", dest="datasets")
    parser.add_argument("--max-queries", type=int, default=MAX_PROBE_QUERIES)
    parser.add_argument("--out", type=Path, required=True, help="directory for probe.json/.md")
    parser.add_argument(
        "--live", action="store_true", help="send the queries (spends credits); else dry run"
    )
    args = parser.parse_args(argv)
    if args.max_queries > MAX_PROBE_QUERIES or args.max_queries < 1:
        parser.error(f"--max-queries must be between 1 and {MAX_PROBE_QUERIES}")

    cases = load_cases(args.datasets or DEFAULT_DATASETS, args.cases)
    provider: SearchProvider | None = None
    if args.live:
        from app.adapters.search import get_search_provider

        provider = get_search_provider()
        if provider.name != "serper":
            parser.error(f"the probe is a Serper probe; configured provider is {provider.name!r}")
    data = asyncio.run(run_probe(cases, provider, limit=args.max_queries))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "probe.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    table = markdown(data)
    (args.out / "probe.md").write_text(table, encoding="utf-8")
    sys.stdout.write(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
