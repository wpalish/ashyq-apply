"""Explicit bounded capture of the unmodified pipeline; never reads ground truth.

Run from backend: python -m evaluation.research.live --live --out <directory>
Each institution runs in its own process with a hard wall-clock budget.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from pydantic import HttpUrl

from .identities import IdentityMap
from .mapping import evidence_scope, normalize_subject_claims
from .schema import Capture, Evidence, Observation, PageOutcome, Prediction, Telemetry

# Evaluation cohort IDs, not expected URLs/values. Registry remains production's input.
COHORT = {
    "groningen": "rug.nl",
    "delft": "tudelft.nl",
    "aalto": "aalto.fi",
    "vienna": "univie.ac.at",
    "warsaw": "uw.edu.pl",
    "ubc": "ubc.ca",
    "toronto": "utoronto.ca",
    "hku": "hku.hk",
    "ntu": "ntu.edu.sg",
    "kaist": "kaist.ac.kr",
}


#: Award and document identities the owner approved on 2026-09-23. Scoring
#: live with them is what lets a scholarship or document claim land on its
#: certified key; without them every such claim stays ``unmapped.*``.
REVIEWED_BINDINGS = Path(__file__).parent / "data" / "identity_bindings.reviewed.json"


async def capture_one(case_id: str, output: Path, max_pages: int) -> None:
    # Delayed imports keep ordinary offline evaluation entirely independent of I/O.
    from app.adapters import fetching
    from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter, PageCategory
    from app.adapters.search.exa import ExaSearchProvider
    from app.models.research import ClaimRow
    from scripts import canary_discovery as canary

    predictions: list[Prediction] = []
    raw_claims: list[dict[str, Any]] = []
    identities = IdentityMap.model_validate_json(REVIEWED_BINDINGS.read_text(encoding="utf-8"))
    started = time.monotonic()
    observation = Observation(
        case_id=case_id,
        error="CAPTURE_IN_PROGRESS",
        telemetry=Telemetry(
            http_fetches=0,
            browser_fetches=0,
            pdf_fetches=0,
            search_calls=0,
            model_input_tokens=0,
            jev_input_tokens=0,
        ),
    )

    fetchers: list[Any] = []

    def checkpoint() -> None:
        observation.telemetry.latency_seconds = time.monotonic() - started
        # Counted from the fetcher's own tier tally, never assumed: a zero
        # that nothing increments is a counter invented after the fact.
        observation.telemetry.browser_fetches = sum(
            f.tier_counts.get("browser", 0) for f in fetchers if hasattr(f, "tier_counts")
        )
        temporary = output.with_suffix(".pending")
        temporary.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(output)

    checkpoint()
    original_request = fetching._pinned_request
    original_search = ExaSearchProvider.search

    async def counted_search(provider, *args, **kwargs):
        # Each search call is counted and timed into this case's own log: a
        # case that runs out of wall clock after two fetches spent the time
        # somewhere, and search is the first place to look.
        observation.telemetry.search_calls = (observation.telemetry.search_calls or 0) + 1
        began = time.monotonic()
        try:
            return await original_search(provider, *args, **kwargs)
        except Exception as exc:
            print(f"search failed after {time.monotonic() - began:.1f}s: {type(exc).__name__}")
            raise
        finally:
            print(
                f"search #{observation.telemetry.search_calls} took "
                f"{time.monotonic() - began:.1f}s (t={time.monotonic() - started:.0f}s)",
                flush=True,
            )
            checkpoint()

    original_confirm = LiveDiscoveryAdapter._confirm_programs

    def counted_request(*args, **kwargs):
        observation.telemetry.http_fetches = (observation.telemetry.http_fetches or 0) + 1
        checkpoint()
        return original_request(*args, **kwargs)

    async def observed_confirm(adapter, selected, ranked, trace, profile):
        queued = list(selected[PageCategory.PROGRAM_PAGE])
        for _score, url in sorted(ranked[PageCategory.PROGRAM_PAGE], reverse=True):
            if url not in queued:
                queued.append(url)
        observation.ranked_urls = [HttpUrl(url) for url in queued]
        checkpoint()
        return await original_confirm(adapter, selected, ranked, trace, profile)

    class ObservedRunner(canary.CanaryRunner):
        def _make_fetcher(self):
            fetcher = super()._make_fetcher()
            fetchers.append(fetcher)
            original = fetcher.get
            requests = 0
            network_reads = 0

            async def bounded(url, **kwargs):
                nonlocal requests, network_reads
                # The budget bounds reads that reach a server. A page two
                # stages both need is served from the cache the second time,
                # and until 2026-09-23 that repeat still spent the budget: run
                # 20 ended Delft, Vienna and UBC in the funding stage with up
                # to a fifth of their 60 calls being cache hits.
                if network_reads >= max_pages:
                    raise RuntimeError("BENCHMARK_PAGE_BUDGET_EXHAUSTED")
                requests += 1
                began = time.monotonic()
                # Written before the read, so a read that never returns still
                # names itself in the log.
                print(f"get #{requests} start t={began - started:.0f}s {url[:120]}", flush=True)
                result = await original(url, **kwargs)
                # One line per page read, so a case that runs out of wall
                # clock shows which reads took it: its own log is printed by
                # the benchmark when the budget ends the case.
                print(
                    f"get #{requests} took {time.monotonic() - began:.1f}s "
                    f"{getattr(result, 'outcome', '?')}",
                    flush=True,
                )
                if not getattr(result, "from_cache", False):
                    network_reads += 1
                if result.ok and result.is_pdf and not result.from_cache:
                    observation.telemetry.pdf_fetches = (observation.telemetry.pdf_fetches or 0) + 1
                checkpoint()
                return result

            fetcher.get = bounded
            return fetcher

        async def run_to_decision(self):
            try:
                return await super().run_to_decision()
            finally:
                # Why a page produced nothing, in the runner's own vocabulary.
                # Read here rather than after the run, so a case killed by its
                # budget still records what it managed to read — which is
                # exactly the case whose zero needs explaining.
                observation.page_outcomes = [
                    PageOutcome(
                        category=record["category"],
                        url=record["url"],
                        page_type=record.get("page_type") or "",
                        detail=record.get("detail") or "",
                        characters=int(record["characters"]) if record.get("characters") else None,
                    )
                    for record in canary.page_outcomes(self.run)
                ]
                for row in self.session.query(ClaimRow).filter(ClaimRow.run_id == self.run.id):
                    raw = row.payload
                    raw_claims.append(raw)
                    # With the owner-approved identity bindings (2026-09-23),
                    # the same split the offline mapper makes: an award or a
                    # document claim becomes the fields of the identity it is
                    # bound to, and an unbound one stays under its raw key.
                    mapped = normalize_subject_claims(row.claim_type, raw, identities)
                    excerpt = raw.get("original_text_excerpt")
                    for key, value, programme, degree in mapped:
                        evidence = None
                        if excerpt and str(row.source_url).startswith(("http://", "https://")):
                            evidence = Evidence(
                                url=row.source_url,
                                excerpt=excerpt,
                                scope=evidence_scope(
                                    raw,
                                    university=next(iter(self._candidates)).name
                                    if self._candidates
                                    else case_id,
                                    programme=programme,
                                    degree=degree,
                                ),
                                accessed_on=row.accessed_at.date(),
                                source_type="official" if raw.get("official_domain") else "unknown",
                            )
                        predictions.append(Prediction(key=key, value=value, evidence=evidence))

    with (
        patch.object(canary, "CanaryRunner", ObservedRunner),
        patch.object(fetching, "_pinned_request", counted_request),
        patch.object(ExaSearchProvider, "search", counted_search),
        patch.object(LiveDiscoveryAdapter, "_confirm_programs", observed_confirm),
    ):
        report = await canary.run_canary(COHORT[case_id], False)
    rows = report["institutions"]
    observation.programme_urls = [HttpUrl(url) for r in rows for url in r["programs"]]
    observation.predictions = predictions
    observation.error = report["run_error"] or None
    checkpoint()
    # Preserve raw output for mapping/adjudication; do not invent unsupported counters.
    output.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
    output.with_suffix(".raw.json").write_text(
        json.dumps({"canary": report, "claims": raw_claims}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", choices=list(COHORT))
    parser.add_argument("--seconds-per-case", type=int, default=120)
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument(
        "--search-first",
        action="store_true",
        help="experiment: search before the navigation fallback (default off)",
    )
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.seconds_per_case <= 600 or not 1 <= args.max_pages <= 100:
        parser.error("Budget must be 1..600 seconds and 1..100 Fetcher.get calls per university")
    if args.child:
        if args.search_first:
            from app.adapters.discovery import live_discovery

            live_discovery.SEARCH_BEFORE_NAVIGATION = True
        asyncio.run(capture_one(args.case, args.out, args.max_pages))
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = args.out / stamp
    directory.mkdir(parents=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    observations = []
    for case_id in [args.case] if args.case else list(COHORT):
        output = directory / f"{case_id}.json"
        started = time.monotonic()
        environment = dict(
            os.environ,
            UNIMATCH_DEMO_MODE="false",
            UNIMATCH_ENABLE_BROWSER_TIER="false",
            UNIMATCH_FETCH_CONTACT="https://github.com/wpalish/ashyq-apply",
            PYTHONIOENCODING="utf-8",
        )
        with (directory / f"{case_id}.log").open("w", encoding="utf-8") as log:
            try:
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "evaluation.research.live",
                        "--live",
                        "--child",
                        "--case",
                        case_id,
                        "--out",
                        str(output),
                        "--max-pages",
                        str(args.max_pages),
                        *(["--search-first"] if args.search_first else []),
                    ],
                    env=environment,
                    stdout=log,
                    stderr=log,
                    timeout=args.seconds_per_case,
                    check=False,
                )
                error = f"PROCESS_EXIT_{completed.returncode}" if completed.returncode else None
            except subprocess.TimeoutExpired:
                error = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
        if output.exists():
            observation = Observation.model_validate_json(output.read_text(encoding="utf-8"))
            if error:
                observation.error = error
                observation.telemetry.latency_seconds = time.monotonic() - started
        else:
            observation = Observation(
                case_id=case_id,
                error=error or "MISSING_OUTPUT",
                telemetry=Telemetry(latency_seconds=time.monotonic() - started),
            )
        observations.append(observation)
        capture = Capture(
            pipeline_sha=sha,
            captured_at=stamp,
            mode="live",
            config={
                "seconds_per_case": args.seconds_per_case,
                "max_fetcher_calls_per_case": args.max_pages,
                "page_budget_counts": "network reads; cache hits are free (since 2026-09-23)",
                "search_before_navigation": args.search_first,
                "browser_enabled": False,
                "cohort": list(COHORT),
                "scope": "current production pipeline; HTTP-only bounded cold run",
                "rank_stage": "programme confirmation queue before catalogue walking",
                "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "mapping_sha256": hashlib.sha256(
                    Path(__file__).with_name("mapping.py").read_bytes()
                ).hexdigest(),
            },
            observations=observations,
        )
        (directory / "capture.json").write_text(capture.model_dump_json(indent=2), encoding="utf-8")
        print(f"{case_id}: {observation.error or 'complete'}", flush=True)
    print(directory / "capture.json", flush=True)


if __name__ == "__main__":
    main()
