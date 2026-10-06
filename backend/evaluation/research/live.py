"""Explicit bounded capture of the unmodified pipeline; never reads ground truth.

Run from backend: python -m evaluation.research.live --live --out <directory>
Each institution runs in its own process with a hard wall-clock budget.

``--strict-expert-budget`` adds evaluation wrappers around the unchanged app:
60 cumulative cold Fetcher.get calls and six configured Exa queries across
all stages, with no further provider call after HTTP 429. Active time starts
at capture_one entry and lasts the requested 120 seconds by default, including
canary setup, discovery, verification, and funding. The parent adds a separate
15-second process reserve for startup and cancellation/output cleanup; this
reserve never authorizes more tool calls. Legacy mode retains its five-second
child reserve and cache-free page accounting.

``--finalization-reserve-ms 1000`` is an optional strict evaluation setting.
Source/work stops at 119000ms of the same 120000ms case clock; cancellation
cleanup and final output/checkpoint work remain measured, without clamping an
overrun. The final metering-envelope write is audit persistence after that work.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
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

#: Registry institutions outside the certified ten. They have no signed
#: labels: a capture of one is scored by process measures and by hand, never
#: by the corpus. They exist so that a rule tuned on the ten is tested
#: somewhere it was not tuned (expert recovery protocol, 2026-09-27).
HELDOUT = {
    "nu": "nu.edu.kz",
    "metu": "metu.edu.tr",
    "sabanci": "sabanciuniv.edu",
    "charles": "cuni.cz",
    "masaryk": "muni.cz",
    "tum": "tum.de",
    "tartu": "ut.ee",
    "polimi": "polimi.it",
    "vilnius": "vu.lt",
}

STRICT_MAX_FETCHER_CALLS = 60
STRICT_MAX_SEARCH_QUERIES = 6
STRICT_MAX_SECONDS = 120
STRICT_PROCESS_RESERVE_SECONDS = 15
STRICT_PROVIDERS = frozenset({"exa", "exa_mcp"})


@dataclass
class _ExpertBudget:
    """One case ledger shared by every Fetcher/provider instance and stage."""

    max_fetcher_calls: int
    seconds: float
    provider_name: str
    started: float
    max_search_queries: int = STRICT_MAX_SEARCH_QUERIES
    clock: Callable[[], float] = time.monotonic
    finalization_reserve_ms: int = 0
    fetcher_calls: int = 0
    search_queries: int = 0
    blocked_search_queries: int = 0
    network_http_requests: int = 0
    stop_reason: str | None = None
    provider_failure: dict[str, Any] | None = None

    @property
    def source_work_deadline_ms(self) -> int:
        return int(self.seconds * 1000) - self.finalization_reserve_ms

    @property
    def active_time_basis(self) -> str:
        basis = "capture_one entry; includes canary setup and all pipeline stages"
        if self.finalization_reserve_ms:
            basis += (
                ", cancellation cleanup, output/raw persistence and final checkpoint work; "
                "final metering-envelope persistence is audit only"
            )
        return basis

    def remaining(self) -> float:
        remaining = (
            self.seconds - self.finalization_reserve_ms / 1000 - (self.clock() - self.started)
        )
        if remaining <= 0:
            self.stop_reason = self.stop_reason or (
                "source_work_deadline_exhausted"
                if self.finalization_reserve_ms
                else "wall_clock_budget_exhausted"
            )
            raise TimeoutError("BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED")
        return remaining

    def before_fetch(self) -> None:
        self.remaining()
        if self.fetcher_calls >= self.max_fetcher_calls:
            self.stop_reason = self.stop_reason or "page_budget_exhausted"
            raise RuntimeError("BENCHMARK_PAGE_BUDGET_EXHAUSTED")
        self.fetcher_calls += 1

    def before_search(self, provider_name: str) -> None:
        from app.adapters.search.base import SearchUnavailable

        self.remaining()
        if provider_name != self.provider_name or provider_name not in STRICT_PROVIDERS:
            raise SearchUnavailable("Strict capture refused a different provider identity")
        if self.provider_failure and self.provider_failure.get("http_status") == 429:
            self.blocked_search_queries += 1
            raise SearchUnavailable(
                "Strict capture stopped provider calls after HTTP 429", http_status=429
            )
        if self.search_queries >= self.max_search_queries:
            self.blocked_search_queries += 1
            self.stop_reason = self.stop_reason or "search_budget_exhausted"
            raise SearchUnavailable("Strict capture search query budget exhausted")
        self.search_queries += 1

    def failed_search(self, exc: Exception) -> Exception:
        """Keep a fixed diagnostic/status, never vendor exception text or keys."""
        from app.adapters.search.base import (
            SearchFailureReason,
            SearchUnavailable,
            search_failure_diagnostic,
        )

        status = getattr(exc, "http_status", None)
        if type(status) is not int or not 100 <= status <= 599:
            status = getattr(getattr(exc, "response", None), "status_code", None)
        if type(status) is not int or not 100 <= status <= 599:
            status = None
        reason = getattr(exc, "reason", None)
        reason = reason if isinstance(reason, SearchFailureReason) else None
        sanitized = SearchUnavailable(
            "Configured search provider unavailable", http_status=status, reason=reason
        )
        self.provider_failure = {
            "http_status": status,
            "reason": reason.value if reason else None,
            "error": search_failure_diagnostic(self.provider_name, sanitized),
        }
        if status == 429:
            self.stop_reason = "http_429"
        return sanitized

    def snapshot(self) -> dict[str, Any]:
        return {
            "strict_expert_budget": True,
            "provider": self.provider_name,
            "max_fetcher_calls": self.max_fetcher_calls,
            "max_search_queries": self.max_search_queries,
            "max_active_seconds": self.seconds,
            "finalization_reserve_ms": self.finalization_reserve_ms,
            "source_work_deadline_ms": self.source_work_deadline_ms,
            "fetcher_calls": self.fetcher_calls,
            "search_queries": self.search_queries,
            "blocked_search_queries": self.blocked_search_queries,
            "network_http_requests": self.network_http_requests,
            "elapsed_ms": max(0, int((self.clock() - self.started) * 1000)),
            "stop_reason": self.stop_reason,
            "provider_failure": self.provider_failure,
            "active_time_basis": self.active_time_basis,
        }


#: Award and document identities the owner approved on 2026-09-23. Scoring
#: live with them is what lets a scholarship or document claim land on its
#: certified key; without them every such claim stays ``unmapped.*``.
REVIEWED_BINDINGS = Path(__file__).parent / "data" / "identity_bindings.reviewed.json"


async def _jev_shadow(case_id: str, queued: list[str], profile: Any) -> None:
    """Shadow only: where a decision model would rank the certified programme page.

    Nothing the run reads changes. The line it prints is the Phase 4 experiment's
    evidence: the gold page's rank in the heuristic queue beside its rank after the
    model reorders the same candidates (analysis/v2/07, Experiment 2).
    """
    from app.adapters.decisions import get_decision_model
    from app.adapters.decisions.link_ranker import LinkCandidate, rank_links

    model = get_decision_model()
    if model is None or not queued:
        return
    from .metrics import canonical_url
    from .schema import Dataset

    dataset = Dataset.model_validate_json(
        (Path(__file__).parent / "data" / "ground_truth.reviewed.json").read_text(encoding="utf-8")
    )
    case = next((c for c in dataset.cases if c.id == case_id), None)
    gold = {canonical_url(u) for u in (case.programme_urls if case else [])}
    context = profile.context
    ranked, model_id = await rank_links(
        model,
        [LinkCandidate(u) for u in queued[:48]],
        field=", ".join(context.intended_fields),
        degree=str(context.level),
        target="programme page",
    )

    def rank(urls: list[str]) -> int | None:
        return next((i + 1 for i, u in enumerate(urls) if canonical_url(u) in gold), None)

    print(
        f"jev shadow: gold programme rank heuristic={rank(queued[:48])} "
        f"model={rank([r.url for r in ranked])} of {len(ranked)} ({model_id or 'unavailable'})",
        flush=True,
    )


#: D7: seconds the documents stage gets after the decision stage; 0 skips it.
DOCUMENT_SECONDS = 0.0


async def capture_one(
    case_id: str,
    output: Path,
    max_pages: int,
    seconds: float | None = None,
    *,
    strict_expert_budget: bool = False,
    finalization_reserve_ms: int = 0,
) -> None:
    entered = time.monotonic()
    if type(finalization_reserve_ms) is not int or finalization_reserve_ms < 0:
        raise ValueError("Finalization reserve must be a nonnegative integer in milliseconds")
    if finalization_reserve_ms and not strict_expert_budget:
        raise ValueError("Finalization reserve requires strict expert budget mode")
    # Delayed imports keep ordinary offline evaluation entirely independent of I/O.
    from app.adapters import fetching
    from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter, PageCategory
    from app.adapters.search.exa import ExaSearchProvider
    from app.domain.enums import UserDecision
    from app.models.research import ClaimRow, ProgramResultRow
    from scripts import canary_discovery as canary

    budget = None
    if strict_expert_budget:
        from app.config import get_settings

        seconds = STRICT_MAX_SECONDS if seconds is None else seconds
        if (
            type(max_pages) is not int
            or not 1 <= max_pages <= STRICT_MAX_FETCHER_CALLS
            or not 0 < seconds <= STRICT_MAX_SECONDS
        ):
            raise ValueError(
                "Strict capture budget must be at most 60 Fetcher calls and 120 active seconds"
            )
        if finalization_reserve_ms >= seconds * 1000:
            raise ValueError("Finalization reserve must be less than the full case clock")
        settings = get_settings()
        if settings.search_provider not in STRICT_PROVIDERS:
            raise ValueError("Strict live capture requires configured exa or exa_mcp")
        if settings.enable_browser_tier or not settings.respect_robots:
            raise ValueError("Strict live capture requires browser tier off and robots respected")
        budget = _ExpertBudget(
            max_pages,
            seconds,
            settings.search_provider,
            entered,
            clock=time.monotonic,
            finalization_reserve_ms=finalization_reserve_ms,
        )

    predictions: list[Prediction] = []
    raw_claims: list[dict[str, Any]] = []
    identities = IdentityMap.model_validate_json(REVIEWED_BINDINGS.read_text(encoding="utf-8"))
    started = entered if budget else time.monotonic()
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
    #: D7: the runner, kept for the documents stage that follows the decision.
    runners: list[Any] = []
    recorded_claims: set[str] = set()
    documents_phase = False

    def budget_checkpoint() -> None:
        assert budget is not None
        budget_output = output.with_suffix(".budget.json")
        budget_temporary = budget_output.with_suffix(".pending")
        budget_temporary.write_text(json.dumps(budget.snapshot(), indent=2), encoding="utf-8")
        budget_temporary.replace(budget_output)

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
        if budget:
            budget_checkpoint()

    def final_checkpoint() -> None:
        checkpoint()
        if budget and budget.finalization_reserve_ms:
            # Record the completed first checkpoint's own work from the same
            # clock. This final metering envelope never opens a new work budget.
            budget_checkpoint()

    checkpoint()
    original_request = fetching._pinned_request
    # Every provider's search is counted, not only Exa's: runs 80-93 used
    # Serper and recorded search_calls=0 while six queries ran per case.
    from app.adapters.search.brave import BraveSearchProvider
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider
    from app.adapters.search.serper import SerperSearchProvider
    from app.adapters.search.tavily import TavilySearchProvider

    provider_classes = (
        ExaSearchProvider,
        ExaMcpSearchProvider,
        TavilySearchProvider,
        BraveSearchProvider,
        SerperSearchProvider,
    )
    originals = {cls: cls.search for cls in provider_classes}

    def counted_for(cls):
        async def counted(provider, *args, **kwargs):
            return await counted_search(originals[cls], provider, *args, **kwargs)

        return counted

    async def counted_search(original_search, provider, *args, **kwargs):
        # Each search call is counted and timed into this case's own log: a
        # case that runs out of wall clock after two fetches spent the time
        # somewhere, and search is the first place to look.
        if budget:
            budget.before_search(getattr(provider, "name", ""))
            observation.telemetry.search_calls = budget.search_queries
        else:
            observation.telemetry.search_calls = (observation.telemetry.search_calls or 0) + 1
        began = time.monotonic()
        if budget:
            checkpoint()
            if budget.finalization_reserve_ms:
                budget.remaining()
        try:
            return await original_search(provider, *args, **kwargs)
        except Exception as exc:
            print(f"search failed after {time.monotonic() - began:.1f}s: {type(exc).__name__}")
            if budget:
                raise budget.failed_search(exc) from None
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
        if budget:
            budget.network_http_requests += 1
        else:
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
        if budget is None:
            await _jev_shadow(case_id, queued, profile)
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
                if documents_phase:
                    # The documents stage has its own clock (D7); its reads
                    # never spend the decision stage's budget.
                    pass
                elif budget:
                    budget.before_fetch()
                    observation.telemetry.http_fetches = budget.fetcher_calls
                    kwargs["use_cache"] = False
                elif network_reads >= max_pages:
                    raise RuntimeError("BENCHMARK_PAGE_BUDGET_EXHAUSTED")
                requests += 1
                began = time.monotonic()
                # Written before the read, so a read that never returns still
                # names itself in the log.
                print(f"get #{requests} start t={began - started:.0f}s {url[:120]}", flush=True)
                if budget and not documents_phase:
                    checkpoint()
                    if budget.finalization_reserve_ms:
                        budget.remaining()
                result = await original(url, **kwargs)
                # One line per page read, so a case that runs out of wall
                # clock shows which reads took it: its own log is printed by
                # the benchmark when the budget ends the case.
                print(
                    f"get #{requests} took {time.monotonic() - began:.1f}s "
                    f"{getattr(result, 'outcome', '?')}",
                    flush=True,
                )
                if documents_phase:
                    observation.telemetry.document_reads = (
                        observation.telemetry.document_reads or 0
                    ) + 1
                    return result
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
                runners.append(self)
                self.record_claims()

        def record_claims(self) -> None:
            for row in self.session.query(ClaimRow).filter(ClaimRow.run_id == self.run.id):
                if row.id in recorded_claims:
                    continue
                recorded_claims.add(row.id)
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

    async def documents_stage() -> None:
        nonlocal documents_phase
        if not (DOCUMENT_SECONDS and runners):
            return
        # D7: the documents stage, after the decision stage is measured and on
        # its own clock, so the decision metrics stay comparable with runs
        # that never collected documents. Every row is approved, as an
        # applicant approving the whole shortlist would.
        documents_phase = True
        began = time.monotonic()
        runner = runners[-1]
        for row in runner.session.query(ProgramResultRow).filter(
            ProgramResultRow.run_id == runner.run.id
        ):
            row.user_decision = UserDecision.APPROVED.value
        runner.session.flush()
        try:
            await asyncio.wait_for(runner.collect_documents(), DOCUMENT_SECONDS)
            observation.telemetry.document_stop = "completed"
        except TimeoutError:
            observation.telemetry.document_stop = "document_seconds_exhausted"
        except Exception as exc:  # recorded, never raised: the decision stage stands
            observation.telemetry.document_stop = f"{type(exc).__name__}: {exc}"[:200]
        runner.record_claims()
        observation.telemetry.document_seconds = time.monotonic() - began
        print(
            f"documents stage {observation.telemetry.document_stop} in "
            f"{observation.telemetry.document_seconds:.1f}s, "
            f"{observation.telemetry.document_reads or 0} reads",
            flush=True,
        )

    with (
        patch.object(canary, "CanaryRunner", ObservedRunner),
        patch.object(fetching, "_pinned_request", counted_request),
        patch.object(ExaSearchProvider, "search", counted_for(ExaSearchProvider)),
        patch.object(ExaMcpSearchProvider, "search", counted_for(ExaMcpSearchProvider)),
        patch.object(TavilySearchProvider, "search", counted_for(TavilySearchProvider)),
        patch.object(BraveSearchProvider, "search", counted_for(BraveSearchProvider)),
        patch.object(SerperSearchProvider, "search", counted_for(SerperSearchProvider)),
        patch.object(LiveDiscoveryAdapter, "_confirm_programs", observed_confirm),
    ):
        try:
            active_seconds = budget.remaining() if budget else seconds
            report = await asyncio.wait_for(
                canary.run_canary({**COHORT, **HELDOUT}[case_id], False), active_seconds
            )
        except TimeoutError:
            # The child stops itself just short of the parent's kill, so the
            # claims already filed are kept: run_to_decision's finally reads
            # them on cancellation, which a killed process never reaches.
            # Runs 59-62: UBC filed nothing because the kill came mid-funding.
            observation.predictions = predictions
            observation.error = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
            if budget:
                budget.stop_reason = budget.stop_reason or (
                    "source_work_deadline_exhausted"
                    if budget.finalization_reserve_ms
                    else "wall_clock_budget_exhausted"
                )
            final_checkpoint()
            # D7: a decision stage that ran out of clock still filed rows; the
            # documents stage has its own clock and reads them. Run 37351314325:
            # Groningen's documents were measured in one repetition of two.
            if DOCUMENT_SECONDS and runners:
                await documents_stage()
                output.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
            return
    rows = report["institutions"]
    observation.programme_urls = [HttpUrl(url) for r in rows for url in r["programs"]]
    observation.predictions = predictions
    observation.error = report["run_error"] or None
    if budget is None or not budget.finalization_reserve_ms:
        checkpoint()
    await documents_stage()
    # Preserve raw output for mapping/adjudication; do not invent unsupported counters.
    output.write_text(observation.model_dump_json(indent=2), encoding="utf-8")
    output.with_suffix(".raw.json").write_text(
        json.dumps({"canary": report, "claims": raw_claims}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if budget and budget.finalization_reserve_ms:
        final_checkpoint()


def main() -> None:
    from app.adapters.discovery import live_discovery
    from app.adapters.scholarship import web_scholarships
    from app.adapters.search import KNOWN_SEARCH_PROVIDERS
    from app.config import Settings, get_settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", choices=[*COHORT, *HELDOUT])
    parser.add_argument("--seconds-per-case", type=int, default=120)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument(
        "--strict-expert-budget",
        action="store_true",
        help="evaluation only: cold 60 get / 6 provider query / 120 active second caps; stop batch on 429",
    )
    parser.add_argument(
        "--finalization-reserve-ms",
        type=int,
        default=None,
        help="strict evaluation only: reserve case-clock milliseconds for cancellation/output cleanup (V4:1000)",
    )
    parser.add_argument(
        "--search-provider",
        choices=sorted(KNOWN_SEARCH_PROVIDERS),
        help="search provider for this capture (default: configured provider)",
    )
    parser.add_argument(
        "--search-first",
        action="store_true",
        help="experiment: search before the navigation fallback (default off)",
    )
    parser.add_argument(
        "--skip-refused-hosts",
        action="store_true",
        help="experiment ER-04: search candidates on hosts that refused this run take no slot",
    )
    parser.add_argument(
        "--reject-archive-hosts",
        action="store_true",
        help="experiment ER-06: mirror/repository/journal/archive hosts are not programme pages",
    )
    parser.add_argument(
        "--admission-lexicon",
        action="store_true",
        help="experiment ER-05: links naming undergraduate admission become candidates",
    )
    parser.add_argument(
        "--applicant-academic-year",
        action="store_true",
        help="plan rule AY-1: read fee and requirement tables for the applicant's academic "
        "year (fall 2027 -> 2027/28) instead of the server default",
    )
    parser.add_argument(
        "--shared-query-budget",
        action="store_true",
        help="plan rule BL-1: every stage's provider queries count against one budget of six "
        "per institution; topic search leaves one for the scholarship search",
    )
    parser.add_argument(
        "--deadline-v2",
        action="store_true",
        help="plan rule DL-2: abbreviated months, date-first 'Applications due' rows, and a "
        "window table's catch-all qualification row",
    )
    parser.add_argument(
        "--euro-grouping",
        action="store_true",
        help="plan rule EU-1: continental euro amounts ('€ 20.563', '€ 18.750,00') read a "
        "dot as a thousands separator and a comma as the cents mark",
    )
    parser.add_argument(
        "--with-documents",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="D7: after the decision stage, approve every row and run the documents stage "
        "on its own clock of SECONDS; the decision stage's budget is untouched",
    )
    parser.add_argument(
        "--fee-year-columns",
        action="store_true",
        help="plan rule DF-1: fee tables with academic years as columns and named "
        "tariffs (statutory / institutional rate) as rows",
    )
    parser.add_argument(
        "--search-rate-limit-retry",
        action="store_true",
        help="plan rule SR-1: one retry, after a short pause, when the keyless Exa MCP "
        "reports its rate limit",
    )
    parser.add_argument(
        "--document-leads",
        action="store_true",
        help="plan rule DOC-3: the documents stage also reads the institution's own "
        "application-documents page, at most two links from the programme page",
    )
    parser.add_argument(
        "--document-rules-v2",
        action="store_true",
        help="plan rule DOC-2: gpt-6-astra's PR #41 document rules (measured only with "
        "--with-documents)",
    )
    parser.add_argument(
        "--tuition-row-year",
        action="store_true",
        help="plan rule TY-1: a fee table row that prints its academic year records it "
        "in the claim's scope",
    )
    parser.add_argument(
        "--walker-subject-cap",
        action="store_true",
        help="experiment ER-10: a catalogue walk reads at most three leads that name none "
        "of the applicant's subjects, lists first",
    )
    parser.add_argument(
        "--navigation-field-leads",
        action="store_true",
        help="experiment ER-09: the navigation fallback keeps a programme lead only when "
        "its URL or link text names the applicant's subject",
    )
    parser.add_argument(
        "--topic-search",
        action="store_true",
        help="experiment ER-08: one public query per topic (English, fees, deadline) finds "
        "the official page that publishes it",
    )
    parser.add_argument(
        "--navigation-slot",
        action="store_true",
        help="experiment ER-07: one programme-page slot is kept for the navigation hop",
    )
    parser.add_argument(
        "--recover-search-candidates",
        action=argparse.BooleanOptionalAction,
        default=live_discovery.RECOVER_SEARCH_CANDIDATES,
        help="experiment: verify search identities and backfill rejected programme leads",
    )
    parser.add_argument(
        "--search-funding-fallback",
        action=argparse.BooleanOptionalAction,
        default=web_scholarships.SEARCH_FUNDING_FALLBACK,
        help="experiment: search official awards when index walking yields no scholarships",
    )
    parser.add_argument(
        "--target-award-search",
        action=argparse.BooleanOptionalAction,
        default=web_scholarships.TARGET_AWARD_SEARCH,
        help="experiment: target award policies instead of generic scholarship indices",
    )
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.max_pages is None:
        args.max_pages = STRICT_MAX_FETCHER_CALLS if args.strict_expert_budget else 40
    if not 1 <= args.seconds_per_case <= 600 or not 1 <= args.max_pages <= 100:
        parser.error("Budget must be 1..600 seconds and 1..100 Fetcher.get calls per university")
    if args.strict_expert_budget and (
        args.seconds_per_case > STRICT_MAX_SECONDS or args.max_pages > STRICT_MAX_FETCHER_CALLS
    ):
        parser.error(
            "Strict expert budget cannot exceed 60 Fetcher.get calls and 120 active seconds"
        )
    if args.finalization_reserve_ms is not None:
        if not args.strict_expert_budget:
            parser.error("Finalization reserve requires --strict-expert-budget")
        if not 0 <= args.finalization_reserve_ms < args.seconds_per_case * 1000:
            parser.error("Finalization reserve must be 0..(full case clock minus 1) milliseconds")
    finalization_reserve_ms = args.finalization_reserve_ms or 0
    settings = (
        Settings(search_provider=args.search_provider) if args.search_provider else Settings()
    )
    if args.search_provider or args.strict_expert_budget:
        try:
            settings._validate_search()
        except RuntimeError as exc:
            parser.error(str(exc))
    search_provider = settings.search_provider
    if args.strict_expert_budget and search_provider not in STRICT_PROVIDERS:
        parser.error("Strict expert budget requires configured exa or exa_mcp")
    print(f"search provider: {search_provider}", flush=True)
    if args.child:
        web_scholarships.SEARCH_FUNDING_FALLBACK = args.search_funding_fallback
        web_scholarships.TARGET_AWARD_SEARCH = args.target_award_search
        live_discovery.RECOVER_SEARCH_CANDIDATES = args.recover_search_candidates
        if args.search_first:
            from app.adapters.discovery import live_discovery

            live_discovery.SEARCH_BEFORE_NAVIGATION = True
        if args.skip_refused_hosts:
            from app.adapters.discovery import live_discovery

            live_discovery.SKIP_REFUSED_SEARCH_HOSTS = True
        if args.reject_archive_hosts:
            from app.adapters.search import retrieval

            retrieval.REJECT_ARCHIVE_HOSTS = True
        if args.admission_lexicon:
            from app.adapters.search import navigation

            navigation.ADMISSION_LEXICON = True
        if args.navigation_slot:
            from app.adapters.discovery import live_discovery

            live_discovery.NAVIGATION_SLOT = True
        if args.applicant_academic_year:
            from app.pipeline import runner as runner_module

            runner_module.APPLICANT_ACADEMIC_YEAR = True
        if args.shared_query_budget:
            from app.adapters.search import intent as intent_module

            intent_module.SHARED_QUERY_BUDGET = True
        if args.deadline_v2:
            from app.adapters import extraction as extraction_module

            extraction_module.DEADLINE_V2 = True
        if args.euro_grouping:
            from app.adapters import extraction as euro_module

            euro_module.EURO_GROUPING = True
        if args.with_documents:
            global DOCUMENT_SECONDS
            DOCUMENT_SECONDS = args.with_documents
        if args.fee_year_columns:
            from app.adapters import extraction as fee_module

            fee_module.FEE_YEAR_COLUMNS = True
        if args.search_rate_limit_retry:
            from app.adapters.search import exa_mcp as exa_mcp_module

            exa_mcp_module.RATE_LIMIT_RETRY = True
        if args.document_leads:
            from app.adapters.documents import web_documents as leads_module

            leads_module.DOCUMENT_LEADS = True
        if args.document_rules_v2:
            from app.adapters import document_ir
            from app.adapters.documents import web_documents

            web_documents.DOCUMENT_RULES_V2 = True
            document_ir.FORM_LABEL_HEADINGS = True
        if args.tuition_row_year:
            from app.adapters import extraction as year_module

            year_module.TUITION_ROW_YEAR = True
        if args.walker_subject_cap:
            from app.adapters.discovery import catalog_walker

            catalog_walker.WALKER_SIGNAL_LESS_CAP = 3
        if args.navigation_field_leads:
            from app.adapters.discovery import live_discovery as discovery_module

            discovery_module.NAVIGATION_FIELD_LEADS = True
        if args.topic_search:
            from app.adapters.requirements import web_requirements

            web_requirements.TOPIC_SEARCH = True
        # A few seconds under the parent's timeout, so the child's own stop
        # comes first and writes what it has.
        soft = (
            args.seconds_per_case
            if args.strict_expert_budget
            else max(args.seconds_per_case - 5, 1)
        )
        # Apply the selection before the pipeline constructs Settings. Clearing
        # the cache also covers direct --child invocation in an existing process.
        child_configuration = {"UNIMATCH_SEARCH_PROVIDER": search_provider}
        if args.strict_expert_budget:
            child_configuration.update(
                UNIMATCH_ENABLE_BROWSER_TIER="false", UNIMATCH_RESPECT_ROBOTS="true"
            )
        with patch.dict(os.environ, child_configuration):
            get_settings.cache_clear()
            try:
                strict_arguments: dict[str, Any] = (
                    {"strict_expert_budget": True} if args.strict_expert_budget else {}
                )
                if args.finalization_reserve_ms is not None:
                    strict_arguments["finalization_reserve_ms"] = finalization_reserve_ms
                asyncio.run(
                    capture_one(args.case, args.out, args.max_pages, soft, **strict_arguments)
                )
            finally:
                get_settings.cache_clear()
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = args.out / stamp
    directory.mkdir(parents=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    observations = []
    planned_cases = [args.case] if args.case else list(COHORT)
    case_budgets: dict[str, Any] = {}
    batch_stop_reason = None
    for case_index, case_id in enumerate(planned_cases):
        output = directory / f"{case_id}.json"
        started = time.monotonic()
        environment = dict(
            os.environ,
            UNIMATCH_DEMO_MODE="false",
            UNIMATCH_ENABLE_BROWSER_TIER="false",
            UNIMATCH_FETCH_CONTACT="https://github.com/wpalish/ashyq-apply",
            UNIMATCH_SEARCH_PROVIDER=search_provider,
            PYTHONIOENCODING="utf-8",
        )
        if args.strict_expert_budget:
            environment["UNIMATCH_RESPECT_ROBOTS"] = "true"
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
                        "--seconds-per-case",
                        str(args.seconds_per_case),
                        *(["--strict-expert-budget"] if args.strict_expert_budget else []),
                        *(
                            ["--finalization-reserve-ms", str(finalization_reserve_ms)]
                            if args.finalization_reserve_ms is not None
                            else []
                        ),
                        *(["--search-provider", search_provider] if args.search_provider else []),
                        *(["--search-first"] if args.search_first else []),
                        *(["--skip-refused-hosts"] if args.skip_refused_hosts else []),
                        *(["--reject-archive-hosts"] if args.reject_archive_hosts else []),
                        *(["--admission-lexicon"] if args.admission_lexicon else []),
                        *(["--navigation-slot"] if args.navigation_slot else []),
                        *(["--topic-search"] if args.topic_search else []),
                        *(["--navigation-field-leads"] if args.navigation_field_leads else []),
                        *(["--walker-subject-cap"] if args.walker_subject_cap else []),
                        *(["--deadline-v2"] if args.deadline_v2 else []),
                        *(["--euro-grouping"] if args.euro_grouping else []),
                        *(["--tuition-row-year"] if args.tuition_row_year else []),
                        *(["--document-rules-v2"] if args.document_rules_v2 else []),
                        *(["--document-leads"] if args.document_leads else []),
                        *(["--search-rate-limit-retry"] if args.search_rate_limit_retry else []),
                        *(["--fee-year-columns"] if args.fee_year_columns else []),
                        *(
                            ["--with-documents", str(args.with_documents)]
                            if args.with_documents
                            else []
                        ),
                        *(["--shared-query-budget"] if args.shared_query_budget else []),
                        *(["--applicant-academic-year"] if args.applicant_academic_year else []),
                        "--search-funding-fallback"
                        if args.search_funding_fallback
                        else "--no-search-funding-fallback",
                        *(
                            ["--recover-search-candidates"]
                            if args.recover_search_candidates
                            else ["--no-recover-search-candidates"]
                        ),
                        "--target-award-search"
                        if args.target_award_search
                        else "--no-target-award-search",
                    ],
                    env=environment,
                    stdout=log,
                    stderr=log,
                    timeout=(
                        args.seconds_per_case + STRICT_PROCESS_RESERVE_SECONDS
                        if args.strict_expert_budget
                        else args.seconds_per_case
                    )
                    + args.with_documents,
                    check=False,
                )
                error = f"PROCESS_EXIT_{completed.returncode}" if completed.returncode else None
            except subprocess.TimeoutExpired:
                error = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
        process_elapsed_seconds = time.monotonic() - started
        if output.exists():
            observation = Observation.model_validate_json(output.read_text(encoding="utf-8"))
            if error:
                observation.error = error
                if not args.strict_expert_budget:
                    observation.telemetry.latency_seconds = process_elapsed_seconds
        else:
            observation = Observation(
                case_id=case_id,
                error=error or "MISSING_OUTPUT",
                telemetry=Telemetry(
                    latency_seconds=None if args.strict_expert_budget else process_elapsed_seconds
                ),
            )
        observations.append(observation)
        if args.strict_expert_budget:
            budget_output = output.with_suffix(".budget.json")
            if budget_output.exists():
                case_budgets[case_id] = json.loads(budget_output.read_text(encoding="utf-8"))
                if case_budgets[case_id].get("stop_reason") == "http_429":
                    batch_stop_reason = "http_429"
            case_budgets.setdefault(case_id, {}).update(
                parent_process_elapsed_seconds=process_elapsed_seconds,
                process_error=error,
                active_checkpoint_available=budget_output.exists(),
            )
        strict_config = (
            {
                "strict_expert_budget": True,
                "max_search_queries_per_case": STRICT_MAX_SEARCH_QUERIES,
                "page_budget_counts": "every Fetcher.get invocation; cache hits consume a call",
                "cold_fetcher_reads": True,
                "child_active_seconds": args.seconds_per_case,
                "finalization_reserve_ms": finalization_reserve_ms,
                "source_work_deadline_ms": args.seconds_per_case * 1000 - finalization_reserve_ms,
                "active_time_basis": _ExpertBudget(
                    args.max_pages,
                    args.seconds_per_case,
                    search_provider,
                    0.0,
                    finalization_reserve_ms=finalization_reserve_ms,
                ).active_time_basis,
                "parent_process_reserve_seconds": STRICT_PROCESS_RESERVE_SECONDS,
                "parent_process_timeout_seconds": args.seconds_per_case
                + STRICT_PROCESS_RESERVE_SECONDS,
                "case_budgets": case_budgets,
                "batch_stop_reason": batch_stop_reason,
                "batch_completed_case_ids": planned_cases[: case_index + 1],
                "batch_remaining_case_ids": planned_cases[case_index + 1 :],
            }
            if args.strict_expert_budget
            else {}
        )
        capture = Capture(
            pipeline_sha=sha,
            captured_at=stamp,
            mode="live",
            config={
                "search_provider": search_provider,
                "seconds_per_case": args.seconds_per_case,
                "max_fetcher_calls_per_case": args.max_pages,
                "page_budget_counts": "network reads; cache hits are free (since 2026-09-23)",
                "search_before_navigation": args.search_first,
                "recover_search_candidates": args.recover_search_candidates,
                "search_funding_fallback": args.search_funding_fallback,
                "target_award_search": args.target_award_search,
                "skip_refused_search_hosts": args.skip_refused_hosts,
                "reject_archive_hosts": args.reject_archive_hosts,
                "admission_lexicon": args.admission_lexicon,
                "navigation_slot": args.navigation_slot,
                "browser_enabled": False,
                "cohort": list(COHORT),
                "scope": "current production pipeline; HTTP-only bounded cold run",
                "rank_stage": "programme confirmation queue before catalogue walking",
                "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "mapping_sha256": hashlib.sha256(
                    Path(__file__).with_name("mapping.py").read_bytes()
                ).hexdigest(),
                **strict_config,
            },
            observations=observations,
        )
        (directory / "capture.json").write_text(capture.model_dump_json(indent=2), encoding="utf-8")
        print(f"{case_id}: {observation.error or 'complete'}", flush=True)
        if batch_stop_reason:
            print(
                "Capture stopped after provider HTTP 429; remaining cases were not attempted.",
                flush=True,
            )
            break
    print(directory / "capture.json", flush=True)


if __name__ == "__main__":
    main()
