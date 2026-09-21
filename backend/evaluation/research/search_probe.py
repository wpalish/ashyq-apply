"""Would a web search generator raise the retrieval ceiling?

V2-14 measured that the correct programme page is present in the current
pipeline's candidate set for one case in ten, and that the ranking already has
that one first. So the ceiling *is* the recall, and only retrieval can move it.

This probe answers the next question directly and cheaply: run the Phase 1
retrieval path — intent, bounded queries, provider, prefilter, ranking —
against the certified corpus's ten cases, and check whether the signed correct
URL turns up in the candidate set at all.

It deliberately does not touch the pipeline. Wiring discovery is a separate
change with its own risk; this measures whether that change would be worth
making, which is the order the phase guide asks for: *a discovery change is
good only if the benchmark improves.*

Live by explicit opt-in only. One run is ten cases times the query budget.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.adapters.discovery.live_discovery import canonical_url
from app.adapters.search.base import SearchProvider, SearchUnavailable
from app.adapters.search.identity import verify_candidate
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel

#: Ten cases at six queries each. Stated so a reader can price a run before
#: starting one.
QUERIES_PER_CASE = 6


@dataclass(frozen=True)
class CaseProbe:
    case_id: str
    university: str
    domain: str
    candidates: int
    #: 1-based position of the signed correct URL, or None if it never appeared.
    correct_position: int | None
    queries_run: int
    failed_queries: int
    #: What the identity check said about the top candidate, if there was one.
    top_url: str = ""
    top_identity: str = ""
    top_applies_to_intake: str = ""
    rejection_counts: dict[str, int] | None = None


def _intake_year(request: dict[str, Any]) -> int | None:
    intake = (request.get("intake") or "").strip()
    for token in intake.split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def _intent(case: dict[str, Any]) -> DiscoveryIntent:
    request = case["request"]
    return DiscoveryIntent(
        institution=case["university"],
        domain=case["domain"],
        degree=DegreeLevel(request["degree"]),
        field=request["field"],
        intake_year=_intake_year(request),
    )


async def probe_case(provider: SearchProvider, case: dict[str, Any]) -> CaseProbe:
    intent = _intent(case)
    truth = {canonical_url(u) for u in case["programme_urls"]}

    try:
        report = await discover_candidates(provider, intent, top_k=25)
    except SearchUnavailable as exc:  # pragma: no cover - network failure path
        return CaseProbe(
            case_id=case["id"],
            university=case["university"],
            domain=case["domain"],
            candidates=0,
            correct_position=None,
            queries_run=0,
            failed_queries=QUERIES_PER_CASE,
            top_identity=f"provider unavailable: {exc}",
        )

    urls = [canonical_url(c.url) for c in report.candidates]
    positions = [i + 1 for i, u in enumerate(urls) if u in truth]

    top_identity = top_applies = top_url = ""
    if report.candidates:
        best = report.candidates[0]
        identity = verify_candidate(url=best.url, title=best.title, intent=intent)
        top_url = best.url
        top_identity = str(identity.identity_state)
        top_applies = str(identity.applies_to_requested_intake())

    return CaseProbe(
        case_id=case["id"],
        university=case["university"],
        domain=case["domain"],
        candidates=len(report.candidates),
        correct_position=min(positions) if positions else None,
        queries_run=len(report.queries_run),
        failed_queries=len(report.failed_queries),
        top_url=top_url,
        top_identity=top_identity,
        top_applies_to_intake=top_applies,
        rejection_counts=report.rejection_counts or {},
    )


async def run(provider: SearchProvider, dataset: dict[str, Any]) -> dict[str, Any]:
    probes = [
        await probe_case(provider, case) for case in dataset["cases"] if case["programme_urls"]
    ]
    reachable = sum(1 for p in probes if p.correct_position is not None)
    first = sum(1 for p in probes if p.correct_position == 1)
    return {
        "dataset_version": dataset["version"],
        "provider": getattr(provider, "name", "unknown"),
        "probed_at": datetime.now(UTC).isoformat(),
        "scored_cases": len(probes),
        "retrieval_ceiling": reachable,
        "correct_at_rank_one": first,
        "cases_with_no_candidates": sum(1 for p in probes if p.candidates == 0),
        "queries_issued": sum(p.queries_run for p in probes),
        "cases": [asdict(p) for p in probes],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--live",
        action="store_true",
        help="required: this probe calls a paid provider",
    )
    args = parser.parse_args(argv)

    if not args.live:
        raise SystemExit("Refusing to run without --live: this probe calls a paid search provider.")

    key = os.environ.get("UNIMATCH_EXA_API_KEY") or os.environ.get("EXA_API_KEY")
    if not key:
        raise SystemExit("Set UNIMATCH_EXA_API_KEY (never in a file in this repository).")

    from app.adapters.search.exa import ExaSearchProvider

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    report = asyncio.run(run(ExaSearchProvider(key), dataset))
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
