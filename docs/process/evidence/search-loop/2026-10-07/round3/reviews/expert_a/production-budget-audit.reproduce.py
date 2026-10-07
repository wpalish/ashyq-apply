"""Offline production read/time guard audit; no provider, DNS, or HTTP is allowed.

Run from backend with PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python PATH.
The actual runner/Fetcher/catalogue control flow is used. Persistence and the
leaf discovery/verification/funding workloads are mocks, clearly recorded below.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch
from urllib.parse import urlsplit

import httpx

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.network_policy import ResolvedTarget
from app.config import Settings
from app.domain.enums import PipelineStage
from app.pipeline.runner import ResearchRunner, RunCancelled

BACKEND = Path.cwd()
OUT = Path(__file__).resolve().parent
SOURCES = (
    "app/pipeline/runner.py", "app/adapters/fetching.py", "app/config.py",
    "app/catalogue/discovery.py", "app/adapters/discovery/live_discovery.py",
    "app/jobs/worker.py", "app/jobs/store.py", "app/api/routes_research.py",
    "app/adapters/browser.py", "app/adapters/discovery/catalog_walker.py",
    "app/adapters/requirements/web_requirements.py", "app/adapters/cost/web_costs.py",
    "app/adapters/scholarship/web_scholarships.py", "app/adapters/government/web_government.py",
    "evaluation/research/live.py",
)
source_bytes = {p: (BACKEND / p).read_bytes() for p in SOURCES}
source_hashes = {p: hashlib.sha256(b).hexdigest() for p, b in source_bytes.items()}


class FakeSession:
    def __init__(self):
        self.cancelled = False
        self.cancel_checks = 0

    def execute(self, statement):
        self.cancel_checks += 1
        return SimpleNamespace(scalar=lambda: self.cancelled)

    def add(self, value):
        pass


class MockPersistenceRunner(ResearchRunner):
    """Only persistence/recheck side effects are replaced; no guard is added."""
    def _save(self):
        pass

    def _audit(self, *args, **kwargs):
        pass

    def _arm_recheck(self, *args, **kwargs):
        pass

    def earliest_recheck(self):
        return None


class VirtualClock:
    def __init__(self, loop):
        self.loop = loop
        self.original = loop.time
        self.start = self.original()
        self.elapsed = 0.0

    def now(self):
        return self.start + self.elapsed


def make_runner(case: str, selected: bool, session: FakeSession):
    # Explicit non-secret settings; .env is never read or printed.
    settings = Settings(
        _env_file=None, demo_mode=False, enable_browser_tier=False,
        cache_dir=OUT / "production-budget-audit.mock-cache" / case,
        fetch_delay_seconds=0, respect_robots=False, fetch_timeout_seconds=20,
        candidate_limit=2, verify_limit=2,
    )
    run = SimpleNamespace(
        id=case, stage_state=None, demo_mode=False, candidate_limit=2, verify_limit=2,
        university_ids=["audit-university"] if selected else None,
        started_at=None, finished_at=None, settings_snapshot={}, errors=[], unknowns=[],
        stage="queued", candidates_found=0, pages_checked=0, pages_failed=0,
    )
    profile = SimpleNamespace(
        context=SimpleNamespace(intake_term="fall", intake_year=2027),
        preferences=SimpleNamespace(preferred_countries=[], excluded_countries=[]),
    )
    return MockPersistenceRunner(session, run, profile, settings)


def university(index=0):
    return SimpleNamespace(
        id=f"audit-university-{index}", name=f"Audit University {index}",
        country="Example", city="Example City", domain="audit-university.invalid",
        registry_entry={"name": f"Audit University {index}", "country": "Example", "homepage": "https://audit-university.invalid/"},
    )


async def resolve_mock(url):
    parsed = urlsplit(url)
    return ResolvedTarget(url, parsed.scheme, parsed.hostname or "", 443, ("192.0.2.1",))


def forbid_network(*args, **kwargs):
    raise AssertionError("Offline audit forbids network/DNS")


async def forbid_http_send(*args, **kwargs):
    raise AssertionError("Offline audit forbids httpx network send")


def attach_transport(fetcher, clock, log, session=None, cancel_after=None):
    async def send_mock(self, target, current, headers):
        entry = {"url": current, "virtual_started_s": clock.elapsed}
        log.append(entry)
        if session is not None and len(log) == cancel_after:
            session.cancelled = True
            entry["cancel_requested_here"] = True
        clock.elapsed += 3.0
        await asyncio.sleep(0)
        entry["virtual_finished_s"] = clock.elapsed
        return httpx.Response(
            200, content=b"<html><main><p>" + b"Mock official public page. " * 30 + b"</p></main></html>",
            headers={"Content-Type": "text/html"}, request=httpx.Request("GET", current),
        )
    fetcher._send_to_any_address = MethodType(send_mock, fetcher)


async def read_work(fetcher, count, phase, log):
    for i in range(count):
        page = await fetcher.get(f"https://audit-university.invalid/{phase}/page-{i}.html", use_cache=False)
        assert page.ok and not page.from_cache, (phase, i, page.outcome, page.error)
        log[-1]["phase"] = phase


async def run_case(case: str, selected: bool, discovery_reads: int, verify_reads=0, funding_reads=0, cancellation=False):
    loop = asyncio.get_running_loop()
    clock = VirtualClock(loop)
    session = FakeSession()
    runner = make_runner(case, selected, session)
    fetcher = runner._make_fetcher()  # actual production factory
    reads = []
    attach_transport(fetcher, clock, reads, session if cancellation else None, 1 if cancellation else None)
    runner._make_fetcher = lambda: fetcher

    async def discover_work(adapter, entry, profile):
        await read_work(adapter.fetcher, discovery_reads, "discovery-" + entry["name"].split()[-1], reads)
        return Candidate(entry["name"], entry["country"], "Example City", domain="audit-university.invalid"), DiscoveryTrace(entry["name"], "audit-university.invalid")

    async def validate():
        runner._check_cancelled()
        runner.state[PipelineStage.PROFILE_VALIDATION].finish("mock validation")

    async def verify(shared_fetcher):
        runner._check_cancelled()
        assert shared_fetcher is fetcher
        await read_work(shared_fetcher, verify_reads, "verification", reads)
        runner.state[PipelineStage.PROGRAM_VERIFICATION].finish("mock requirements/cost workload")

    async def funding(shared_fetcher):
        runner._check_cancelled()
        assert shared_fetcher is fetcher
        await read_work(shared_fetcher, funding_reads, "funding", reads)
        runner.state[PipelineStage.FUNDING_DISCOVERY].finish("mock funding workload")

    async def assess(shared_fetcher):
        runner._check_cancelled()
        runner.state[PipelineStage.ASSESSMENT].finish("mock assessment")

    runner._stage_validate = validate
    if not cancellation:
        runner._stage_verify, runner._stage_funding, runner._stage_assess = verify, funding, assess
    # Cancellation case deliberately leaves the actual _stage_verify pre-check.
    rows = [university(i) for i in range(2 if cancellation else 1)]
    started_real = time.monotonic()
    outcome = "completed"
    with patch.object(loop, "time", clock.now), patch("app.adapters.fetching._resolve_checked", resolve_mock), patch("app.catalogue.discovery.retrieve", return_value=rows), patch("app.catalogue.discovery.CatalogueDiscoveryAdapter._discover_one", discover_work), patch.object(socket, "getaddrinfo", forbid_network), patch.object(socket, "create_connection", forbid_network), patch.object(httpx.AsyncClient, "send", forbid_http_send):
        try:
            await runner.run_to_decision()  # actual production orchestration
        except RunCancelled:
            outcome = "RunCancelled"
    real_seconds = time.monotonic() - started_real
    return {
        "case": case, "selected_catalogue": selected,
        "production_orchestration": "ResearchRunner.run_to_decision -> actual _stage_discover -> CatalogueDiscoveryAdapter.discover/_enrich; real Fetcher.get/_request_with_redirects/_request_one_hop/_read_response",
        "mocked": ["DB/persistence/recheck", "university retrieval", "leaf discovery workload", "verification/funding workloads except cancellation case", "DNS resolution", "HTTP send", "event-loop clock (3 simulated seconds per successful response)", "politeness delay/robots disabled solely for offline mock response"],
        "source_bytes_pinned": True, "outcome": outcome, "run_stage": runner.run.stage,
        "fetcher_get_successes": fetcher.stats["ok"], "mock_http_responses": len(reads),
        "fetch_tiers": fetcher.tier_counts, "virtual_elapsed_s": clock.elapsed,
        "real_wall_s": round(real_seconds, 6), "virtual_is_real_wall": False,
        "per_request_virtual_seconds": 3, "production_request_timeout_s": fetcher.timeout,
        "candidates_returned": runner.run.candidates_found, "cancel_checks": session.cancel_checks,
        "responses_after_cancel_request": len(reads) - 1 if cancellation else None,
        "reads": reads,
    }


def evaluation_positive_controls():
    # Compile the original ledger class alone: no dataset/gold import or read.
    tree = ast.parse(source_bytes["evaluation/research/live.py"].decode())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_ExpertBudget")
    unit = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), cls], type_ignores=[])
    ast.fix_missing_locations(unit)
    ns = {"dataclass": dataclass, "time": time, "Callable": Callable, "Any": Any, "Path": Path, "STRICT_MAX_SEARCH_QUERIES": 6, "STRICT_PROVIDERS": {"exa", "exa_mcp"}}
    exec(compile(unit, "original evaluation _ExpertBudget AST", "exec"), ns)
    cls = ns["_ExpertBudget"]
    budget = cls(max_fetcher_calls=60, seconds=120, provider_name="exa", started=0, clock=lambda: 0)
    for _ in range(60):
        budget.before_fetch()
    try:
        budget.before_fetch()
    except RuntimeError as exc:
        count_control = {"accepted": budget.fetcher_calls, "attempt_61": str(exc), "stop_reason": budget.stop_reason}
    else:
        raise AssertionError("Evaluation count positive control failed")
    now = [119.0]
    budget = cls(max_fetcher_calls=60, seconds=120, provider_name="exa", started=0, clock=lambda: now[0])
    budget.before_fetch()
    now[0] = 120.0
    try:
        budget.before_fetch()
    except TimeoutError as exc:
        time_control = {"accepted_at_s": 119, "blocked_at_s": 120, "error": str(exc), "stop_reason": budget.stop_reason}
    else:
        raise AssertionError("Evaluation deadline positive control failed")
    return {"class_extracted_from_exact_original_source": True, "module_or_dataset_not_imported": True, "reads": count_control, "time": time_control}


async def main():
    results = []
    results.append(await run_case("selected-discovery-61", True, 61))
    results.append(await run_case("ordinary-catalogue-shared-61", False, 11, 25, 25))
    results.append(await run_case("selected-cancel-during-discovery", True, 3, cancellation=True))
    assert results[0]["fetcher_get_successes"] == 61 and results[0]["virtual_elapsed_s"] == 183
    assert results[1]["fetcher_get_successes"] == 61 and results[1]["virtual_elapsed_s"] == 183
    assert results[0]["outcome"] == results[1]["outcome"] == "completed"
    assert results[2]["outcome"] == "RunCancelled" and results[2]["responses_after_cancel_request"] == 5
    unchanged = {p: hashlib.sha256((BACKEND / p).read_bytes()).hexdigest() == h for p, h in source_hashes.items()}
    assert all(unchanged.values()), "Root source changed during this audit; do not claim a stable hash"
    snapshot = OUT / "production-budget-audit.source-snapshot"
    for p, body in source_bytes.items():
        dest = snapshot / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == body
        else:
            dest.write_bytes(body)
    payload = {
        "status": "unreviewed offline audit", "created_at_utc": datetime.now(UTC).isoformat(),
        "network_calls_attempted": 0, "provider_calls": 0, "original_cache_reads": 0,
        "scope": "Production read and elapsed-time guards only; query budget is reviewed separately.",
        "source_root": str(BACKEND), "source_hashes_sha256_raw_bytes": source_hashes,
        "source_unchanged_during_run": unchanged, "reproducer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "results": results, "evaluation_positive_controls": evaluation_positive_controls(),
        "limits_of_reproduction": ["Workloads are synthetic mocks, not actual Dalian or another university trace.", "183 seconds is a controlled event-loop clock, not real elapsed time or benchmark latency.", "Browser disabled; renderer subrequests are discussed from source only.", "DB persistence and worker dispatch were traced from source, not exercised in a live worker.", "No launch success, empirical production read maximum, or university facts are asserted."],
    }
    target = OUT / "production-budget-audit.offline.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "cases": [{k: r[k] for k in ("case", "outcome", "fetcher_get_successes", "virtual_elapsed_s", "responses_after_cancel_request")} for r in results], "positive_controls": payload["evaluation_positive_controls"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
