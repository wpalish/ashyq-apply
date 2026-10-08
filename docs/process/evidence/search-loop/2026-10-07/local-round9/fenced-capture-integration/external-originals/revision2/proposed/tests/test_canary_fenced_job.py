"""Genuine canary Job protocol, zero networking, real isolated SQLite/app SQL."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.adapters.base import AdapterResult
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import Fetcher, FetchResult
from app.catalogue import discovery as catalogue
from app.config import Settings
from app.domain.enums import FetchOutcome
from app.jobs.store import JobStore
from app.models import AuditEvent, Job, ResearchRun, University
from app.pipeline import read_budget
from app.pipeline import runner as rm
from app.pipeline.control import UniversityReadStopped
from scripts import canary_discovery as canary
from tests.readguard_support import candidate, program_claim
from tests.readguard_support import offline as offline

ID = "a" * 32


@pytest.fixture
def case(tmp_path, monkeypatch, request):
    registry = tmp_path / "registry.json"
    entry = {
        "name": "Test University",
        "country": "Example",
        "city": "City",
        "homepage": "https://example.edu/",
    }
    registry.write_text(json.dumps([entry]))
    monkeypatch.setattr(canary, "REGISTRY_PATH", registry)
    engines = []

    def close_engines():
        # State assertions may reopen a disposed canary engine. Close those
        # test-only pools as well; no source database is touched.
        for engine in engines:
            engine.dispose()

    request.addfinalizer(close_engines)
    transport = []
    attempts = []
    mode = {"value": "normal"}
    real_engine = create_engine
    real_settings = Settings
    real_mkdtemp = canary.tempfile.mkdtemp
    monkeypatch.setattr(
        canary.tempfile, "mkdtemp", lambda **kwargs: real_mkdtemp(dir=tmp_path, **kwargs)
    )

    def engine(*args, **kwargs):
        result = real_engine(*args, connect_args={"timeout": 0}, **kwargs)
        engines.append(result)
        return result

    def settings(**kwargs):
        return real_settings(
            _env_file=None, enable_browser_tier=False, fetch_delay_seconds=0, **kwargs
        )

    def import_catalogue(session):
        session.add(
            University(
                id=ID,
                identity_key="example",
                name="Test University",
                country="Example",
                city="City",
                domain="example.edu",
                registry_entry=entry,
            )
        )
        session.flush()

    monkeypatch.setattr(canary, "create_engine", engine)
    monkeypatch.setattr(canary, "Settings", settings)
    monkeypatch.setattr(canary, "import_catalogue", import_catalogue)
    monkeypatch.setattr(
        catalogue, "retrieve", lambda session, *args, **kwargs: session.query(University).all()
    )

    def state():
        with sessionmaker(bind=engines[-1])() as session:
            run = session.query(ResearchRun).one()
            jobs = session.query(Job).filter_by(kind="research").all()
            job = jobs[0] if jobs else None
            return {
                "job_id": job.id if job else None,
                "attempts": job.attempts if job else None,
                "status": job.status if job else None,
                "worker_id": job.worker_id if job else None,
                "native_ledger": (run.settings_snapshot or {}).get(read_budget.LEDGER_KEY),
                "completed": session.query(AuditEvent).filter_by(action="job_completed").count(),
            }

    async def source(fetcher, url, **kwargs):
        transport.append({"url": url, "state_before_io": state()})
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            from_cache=True,
            text="Synthetic official CS degree",
        )

    async def discovered(adapter, entry, profile, **kwargs):
        for i in range(11):
            attempts.append("discovery")
            await adapter.fetcher.get(f"https://example.edu/discovery/{i}")
        return candidate(ID), DiscoveryTrace("Test University", "example.edu")

    async def requirements(adapter, cand, prog, intake):
        for i in range(25):
            attempts.append("requirements")
            await adapter.fetcher.get(f"https://example.edu/requirements/{i}")
        return AdapterResult(claims=[program_claim()], pages_checked=25)

    async def costs(*args, **kwargs):
        from app.schemas.result import CostBreakdown

        return CostBreakdown(), AdapterResult()

    async def government(*args, **kwargs):
        return AdapterResult()

    async def funding(adapter, cand, prog, profile, **kwargs):
        if mode["value"] == "cancel":
            with sessionmaker(bind=engines[-1])() as session:
                job = session.query(Job).filter_by(kind="research").one()
                assert JobStore(session).cancel(job.id)
                session.commit()
        elif mode["value"] == "takeover":
            now = datetime.now(UTC)
            with sessionmaker(bind=engines[-1])() as session:
                job = session.query(Job).filter_by(kind="research").one()
                session.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(lease_expires_at=now - timedelta(seconds=1))
                )
                session.commit()
                store = JobStore(session, worker_id="new-owner")
                assert store.reap_expired(now=now) == [job.id]
                session.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(available_at=now - timedelta(seconds=1))
                )
                session.commit()
                assert store.claim(worker_id="new-owner").attempts == 2
                session.commit()
        elif mode["value"] == "async_cancel":
            raise asyncio.CancelledError()
        for i in range(25):
            attempts.append("funding")
            await adapter.fetcher.get(f"https://example.edu/funding/{i}")
        return [], AdapterResult()

    monkeypatch.setattr(Fetcher, "_get", source)
    monkeypatch.setattr(catalogue.CatalogueDiscoveryAdapter, "_discover_one", discovered)
    monkeypatch.setattr(rm.WebRequirementsAdapter, "verify", requirements)
    monkeypatch.setattr(rm.WebCostAdapter, "fetch", costs)
    monkeypatch.setattr(rm.WebGovernmentAdapter, "post_study_work", government)
    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", funding)
    return SimpleNamespace(
        state=state,
        engines=engines,
        transport=transport,
        attempts=attempts,
        mode=mode,
        root=tmp_path,
        entry=entry,
    )


def native_count(protocol):
    ledger = protocol["native_ledger"]
    return ledger["episodes"][ledger["active_episode"]]["read_counts"]


@pytest.mark.parametrize("native", [False, True, True, False])
def test_same_genuine_job_path_off_on_on_off(case, monkeypatch, native):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    report = asyncio.run(
        canary.run_canary(
            None, False, catalogue_ids=[ID], university_read_budget=native, fenced_research_job=True
        )
    )
    p = report["job_protocol"]
    assert p["claim_token"] == 1 and p["lease_token"] == 1 and p["job_status"] == "succeeded"
    assert p["worker_id"] and p["observation_available"] and p["worker_jobs_done"] == 1
    assert all(p["heartbeat_done"]) and p["heartbeat_tasks"] == 1
    (case.root / "genuine-proof.json").write_text(
        json.dumps({"report": report, "transport": case.transport}, indent=2)
    )
    assert case.state()["completed"] == 1
    assert len(case.transport) == (60 if native else 61)
    assert all(
        x["state_before_io"]["status"] == "running" and x["state_before_io"]["attempts"] == 1
        for x in case.transport
    )
    assert read_budget.UNIVERSITY_READ_BUDGET is False
    if native:
        assert native_count(p) == {"catalogue:" + ID: 60}
        assert [
            native_count(x["state_before_io"])["catalogue:" + ID] for x in case.transport
        ] == list(range(1, 61))
        assert report["institutions"][0]["claims"] == 1
        assert any(
            "read_cap" in d["detail"] for d in p["page_outcomes"]
        ) or "read_cap" in json.dumps(report)
    else:
        assert p["native_ledger"] is None


def test_explicit_false_overrides_hostile_true_and_restores(case, monkeypatch):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", True)
    report = asyncio.run(
        canary.run_canary(
            None, False, catalogue_ids=[ID], university_read_budget=False, fenced_research_job=True
        )
    )
    assert len(case.transport) == 61 and report["job_protocol"]["native_ledger"] is None
    assert read_budget.UNIVERSITY_READ_BUDGET is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"university_read_budget": True},
        {"fenced_research_job": True},
        {"fenced_research_job": True, "catalogue_ids": [ID, ID]},
        {"fenced_research_job": True, "batch": ["example.edu", "second.edu"]},
        {"fenced_research_job": True, "batch": ["example.edu"], "catalogue_ids": [ID]},
    ],
)
def test_invalid_protocol_rejected_before_db_and_io(case, kwargs):
    with pytest.raises(ValueError):
        asyncio.run(canary.run_canary(None, False, **kwargs))
    assert case.engines == [] and case.transport == []


def test_ambiguous_resolved_selector_never_enqueues(case, monkeypatch):
    case.root.joinpath("registry.json").write_text(
        json.dumps([case.entry, {**case.entry, "name": "Other University"}])
    )
    with pytest.raises(ValueError, match="resolve"):
        asyncio.run(canary.run_canary("example.edu", False, fenced_research_job=True))
    with sessionmaker(bind=case.engines[-1])() as session:
        assert session.query(Job).count() == 0
    assert case.transport == []


def test_pre_stop_no_db_job_or_fake_native_zero(case):
    stop = case.root / "local-stop.json"
    stop.write_text('{"reason":"synthetic refusal"}')
    with pytest.raises(ValueError, match="PROVIDER_STOP"):
        asyncio.run(
            canary.run_canary(
                None, False, catalogue_ids=[ID], fenced_research_job=True, stop_file=stop
            )
        )
    assert case.engines == [] and case.transport == []


@pytest.mark.parametrize(
    "mode,control,status,token",
    [("cancel", "RunCancelled", "cancelled", 1), ("takeover", "LeaseLost", "running", 2)],
)
def test_actual_cancel_reclaim_control_and_prior_evidence(case, mode, control, status, token):
    case.mode["value"] = mode
    report = asyncio.run(
        canary.run_canary(
            None, False, catalogue_ids=[ID], university_read_budget=True, fenced_research_job=True
        )
    )
    p = report["job_protocol"]
    assert p["control_type"] == control and p["job_status"] == status and p["lease_token"] == token
    assert len(case.transport) == 36 and native_count(p) == {"catalogue:" + ID: 36}
    assert len(p["claim_records"]) == 1 and all(p["heartbeat_done"])
    assert case.state()["completed"] == 0


def test_original_typed_busy_not_masked_by_fresh_observation_contention(case, monkeypatch):
    blockers = []
    real = rm.WebScholarshipAdapter

    def locked(*args, **kwargs):
        adapter = real(*args, **kwargs)
        blocker = case.engines[-1].connect()
        blocker.exec_driver_sql("BEGIN EXCLUSIVE")
        blockers.append(blocker)
        return adapter

    monkeypatch.setattr(rm, "WebScholarshipAdapter", locked)
    try:
        report = asyncio.run(
            canary.run_canary(
                None,
                False,
                catalogue_ids=[ID],
                university_read_budget=True,
                fenced_research_job=True,
            )
        )
        p = report["job_protocol"]
        assert (
            p["control_type"] == "UniversityReadStopped"
            and p["control_reason"] == "checkpoint_busy"
        )
        assert report["run_error"] == "UniversityReadStopped: checkpoint_busy"
        assert p["observation_available"] is False and p["native_ledger"] is None
        assert p["observation_error"] == "OperationalError" and all(p["heartbeat_done"])
        assert (
            report["totals"]["claims"] is None
            and report["totals"]["recall"]["program"]["numerator"] is None
        )
        (case.root / "busy-proof.json").write_text(json.dumps(report, indent=2))
        assert len(case.transport) == 36
    finally:
        for b in blockers:
            b.rollback()
            b.close()
    assert case.state()["status"] == "running" and case.state()["completed"] == 0


def test_async_cancel_observes_closed_worker_then_propagates_original(case, monkeypatch):
    case.mode["value"] = "async_cancel"
    observed = []
    monkeypatch.setattr(
        canary.CanaryRunner,
        "_record_fenced_report",
        lambda self, report: observed.append(report),
        raising=False,
    )
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            canary.run_canary(
                None,
                False,
                catalogue_ids=[ID],
                university_read_budget=True,
                fenced_research_job=True,
            )
        )
    p = observed[0]["job_protocol"]
    assert p["control_type"] == "CancelledError" and p["job_status"] == "running"
    assert all(p["heartbeat_done"]) and len(p["claim_records"]) == 1


def test_fresh_mapping_failure_does_not_replace_typed_control(case, monkeypatch):
    case.mode["value"] = "cancel"

    def broken(*args):
        raise ValueError("synthetic mapping failure")

    monkeypatch.setattr(canary.CanaryRunner, "_record_fenced_report", broken, raising=False)
    report = asyncio.run(
        canary.run_canary(
            None, False, catalogue_ids=[ID], university_read_budget=True, fenced_research_job=True
        )
    )
    assert (
        report["run_error"] == "RunCancelled"
        and report["job_protocol"]["mapping_error"] == "ValueError"
    )


def test_capture_outer_attempts_and_native_ledger_are_independent(case, monkeypatch):
    from app import config
    from evaluation.research import live

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa", enable_browser_tier=False, respect_robots=True
        ),
    )
    bindings = case.root / "bindings.json"
    bindings.write_text('{"version":"synthetic","bindings":[]}')
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)
    output = case.root / "observed.json"
    asyncio.run(
        live.capture_one(
            ID,
            output,
            60,
            120,
            strict_expert_budget=True,
            catalogue_id=ID,
            university_read_budget=True,
            fenced_research_job=True,
        )
    )
    budget = json.loads(output.with_suffix(".budget.json").read_text())
    raw = json.loads(output.with_suffix(".raw.json").read_text())
    assert budget["fetcher_calls"] == 60 and len(case.transport) == 60
    assert native_count(raw["canary"]["job_protocol"]) == {"catalogue:" + ID: 60}
    assert budget["stop_reason"] == "page_budget_exhausted"
    assert (
        raw["canary"]["job_protocol"]["control_type"] == "RuntimeError"
    )  # outer limit precedes native attempt61
    assert raw["canary"]["job_protocol"]["control_message"] == "BENCHMARK_PAGE_BUDGET_EXHAUSTED"
    assert raw["canary"]["run_error"] == "RuntimeError: BENCHMARK_PAGE_BUDGET_EXHAUSTED"
    assert raw["canary"]["job_protocol"]["terminal_run_error_payload_redacted"] is False
    assert json.loads(output.read_text())["error"] == raw["canary"]["run_error"]
    assert raw["claims"] and "predictions" in json.loads(output.read_text())


def test_legacy_direct_false_full_report_matches_original(case, monkeypatch):
    # Frozen complete normalized public report captured from original canary
    # 37f60bc... on the identical synthetic inputs; time only was removed.
    frozen = json.loads(
        '{"run_error":"","batch":["Test University"],"institutions":[{"catalogue_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","institution":"Test University","country":"Example","domain":"example.edu","access":"REACHED","robots_disallowed_requests":0,"pages_checked":61,"pages_failed":0,"failures":[],"outcomes":{"ok":61},"discovered":{},"discovery_trace":{"institution":"Test University","domain":"example.edu","sitemaps_declared":[],"sitemaps_read":[],"sitemap_urls_seen":0,"sitemap_urls_kept":0,"manual_seeds":{},"selected":{},"rejected_sample":[],"rejected_total":0,"errors":[],"search_failures":[],"search_limitations":[],"field_sources":{},"search_coverage":{},"search_queries_attempted":0,"used_navigation_fallback":false,"kept_by_link_text":[],"walker":{"catalogs_walked":0,"candidates":[],"programs_confirmed":0,"outcomes":[]}},"programs":["https://example.edu/degree"],"program_page_found":true,"scholarship_page_found":false,"discovery_notes":"","claims":1,"claims_verified":1,"completeness":0.0,"eligibility":"NEEDS_OFFICIAL_CLARIFICATION","funding_fit":"UNKNOWN","scholarships_found":0,"false_positives":[],"page_outcomes":{},"page_types":{},"page_diagnostics":[]}],"totals":{"institutions":1,"reached":1,"blocked":0,"program_pages_found":1,"scholarship_pages_found":0,"claims":1,"false_positives":0,"page_outcomes":{},"page_types":{},"recall":{"program":{"numerator":1,"denominator":1,"target":0.7},"category":{"numerator":0,"denominator":3,"target":0.8666666666666667}},"catalogs_walked":0,"walker_programs_confirmed":0,"source_pages_recorded":0,"fetch_tiers":{"fixture":0,"http":0,"browser":0,"pdf":0}}}'
    )
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    new = asyncio.run(
        canary.run_canary(None, False, catalogue_ids=[ID], university_read_budget=False)
    )
    new.pop("accessed_at")
    new.pop("duration_seconds")
    (case.root / "legacy-proposal.json").write_text(json.dumps(new, indent=2))
    assert new == frozen and "job_protocol" not in new
    assert case.state()["job_id"] is None and len(case.transport) == 61


def test_real_claim_refusal_never_executes_or_invents_lease(case, monkeypatch):
    monkeypatch.setattr(JobStore, "claim", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="claim"):
        asyncio.run(
            canary.run_canary(
                None,
                False,
                catalogue_ids=[ID],
                university_read_budget=True,
                fenced_research_job=True,
            )
        )
    assert (
        case.transport == []
        and case.state()["status"] == "queued"
        and case.state()["attempts"] == 0
    )
    assert case.state()["native_ledger"] is None and read_budget.UNIVERSITY_READ_BUDGET is False


def test_capture_pre_stop_never_constructs_job(case, monkeypatch):
    from app import config
    from evaluation.research import live

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa", enable_browser_tier=False, respect_robots=True
        ),
    )
    bindings = case.root / "bindings.json"
    bindings.write_text('{"version":"synthetic","bindings":[]}')
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)
    stop = case.root / "stop.json"
    stop.write_text('{"reason":"synthetic refusal"}')
    output = case.root / "observed.json"
    asyncio.run(
        live.capture_one(
            ID,
            output,
            60,
            120,
            strict_expert_budget=True,
            catalogue_id=ID,
            university_read_budget=True,
            fenced_research_job=True,
            stop_file=stop,
        )
    )
    assert case.engines == [] and case.transport == []
    raw = json.loads(output.with_suffix(".raw.json").read_text())
    assert (
        raw["canary"]["job_protocol"]["started"] is False
        and raw["canary"]["job_protocol"]["native_ledger"] is None
    )
    assert json.loads(output.with_suffix(".budget.json").read_text())["fetcher_calls"] == 0


def test_capture_setup_time_spends_original_clock(case, monkeypatch):
    from app import config
    from evaluation.research import live

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa", enable_browser_tier=False, respect_robots=True
        ),
    )
    bindings = case.root / "bindings.json"
    bindings.write_text('{"version":"synthetic","bindings":[]}')
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)
    clock = [10.0]
    monkeypatch.setattr(live.time, "monotonic", lambda: clock[0])
    actual = canary._run_canary

    async def spend_setup(*args, **kwargs):
        clock[0] += 17
        return await actual(*args, **kwargs)

    monkeypatch.setattr(canary, "_run_canary", spend_setup)
    output = case.root / "observed.json"
    asyncio.run(
        live.capture_one(
            ID,
            output,
            60,
            120,
            strict_expert_budget=True,
            catalogue_id=ID,
            university_read_budget=False,
            fenced_research_job=True,
        )
    )
    budget = json.loads(output.with_suffix(".budget.json").read_text())
    assert budget["elapsed_ms"] == 17000 and budget["max_active_seconds"] == 120


def test_capture_timeout_keeps_real_job_native_ledger_after_cleanup(case, monkeypatch):
    from app import config
    from evaluation.research import live

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa", enable_browser_tier=False, respect_robots=True
        ),
    )
    bindings = case.root / "bindings.json"
    bindings.write_text('{"version":"synthetic","bindings":[]}')
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)

    async def waiting_funding(*args, **kwargs):
        await asyncio.sleep(2)
        raise AssertionError("Source work must have been cancelled")

    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", waiting_funding)
    output = case.root / "observed.json"
    asyncio.run(
        live.capture_one(
            ID,
            output,
            60,
            1,
            strict_expert_budget=True,
            catalogue_id=ID,
            university_read_budget=True,
            fenced_research_job=True,
        )
    )
    observed = json.loads(output.read_text())
    raw = json.loads(output.with_suffix(".raw.json").read_text())
    p = raw["canary"]["job_protocol"]
    assert observed["error"] == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert p["control_type"] == "CancelledError" and p["job_status"] == "running"
    assert p["observation_available"] and p["heartbeat_done"] == [True]
    assert native_count(p) == {"catalogue:" + ID: 36} and len(raw["claims"]) == 1
    assert read_budget.UNIVERSITY_READ_BUDGET is False


def test_fenced_cli_cancel_is_partial_exit_and_real_job_cancelled(case, monkeypatch):
    import sys

    case.mode["value"] = "cancel"
    monkeypatch.setattr(
        sys,
        "argv",
        ["canary", "--catalogue-id", ID, "--fenced-research-job", "--university-read-budget"],
    )
    result = asyncio.run(canary.main())
    assert result == 2 and case.state()["status"] == "cancelled"
    assert case.state()["completed"] == 0 and len(case.transport) == 36
    assert read_budget.UNIVERSITY_READ_BUDGET is False


@pytest.mark.parametrize("error_kind", ["runtime", "operational"])
def test_unrecognized_generic_control_payload_is_redacted(case, monkeypatch, error_kind):
    private = "SYNTHETIC_PRIVATE_CONTROL_PAYLOAD"
    error = (
        RuntimeError(private)
        if error_kind == "runtime"
        else OperationalError("SELECT synthetic_private", {"private": private}, Exception(private))
    )

    async def failed_funding(*args, **kwargs):
        raise error

    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", failed_funding)
    report = asyncio.run(
        canary.run_canary(
            None,
            False,
            catalogue_ids=[ID],
            university_read_budget=True,
            fenced_research_job=True,
        )
    )
    protocol = report["job_protocol"]
    assert protocol["control_type"] == type(error).__name__
    assert protocol["control_message"] is None and protocol["control_reason"] is None
    assert report["run_error"] == type(error).__name__
    assert private not in json.dumps(protocol) + report["run_error"]
    assert protocol["terminal_run_error_payload_redacted"] is True
    assert protocol["run_errors"][-1] == type(error).__name__
    assert native_count(protocol) == {"catalogue:" + ID: 36}
    assert protocol["job_status"] == "queued" and protocol["heartbeat_done"] == [True]
    (case.root / "generic-control-proof.json").write_text(
        json.dumps({"protocol": protocol, "run_error": report["run_error"]}, indent=2)
    )
    assert case.state()["completed"] == 0 and read_budget.UNIVERSITY_READ_BUDGET is False


def _capture_persistence_case(case, monkeypatch):
    from app import config
    from evaluation.research import live

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa", enable_browser_tier=False, respect_robots=True
        ),
    )
    bindings = case.root / "bindings.json"
    bindings.write_text('{"version":"synthetic","bindings":[]}')
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)
    return live, case.root / "observed.json"


async def _funding_exceeds_timeout(*args, **kwargs):
    await asyncio.sleep(2)
    raise AssertionError("Source work must have been cancelled")


def _capture_with_native_job(live, output, seconds=1):
    asyncio.run(
        live.capture_one(
            ID,
            output,
            60,
            seconds,
            strict_expert_budget=True,
            catalogue_id=ID,
            university_read_budget=True,
            fenced_research_job=True,
        )
    )


def test_actual_timeout_raw_write_is_charged_before_final_checkpoint(case, monkeypatch):
    live, output = _capture_persistence_case(case, monkeypatch)
    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", _funding_exceeds_timeout)
    original_clock = live.time.monotonic
    offset = [0.0]
    monkeypatch.setattr(live.time, "monotonic", lambda: original_clock() + offset[0])
    original_write = Path.write_text
    raw_writes = []

    def advancing_write(path, data, *args, **kwargs):
        written = original_write(path, data, *args, **kwargs)
        if path == output.with_suffix(".raw.json"):
            raw_writes.append(path)
            offset[0] += 3.0
        return written

    monkeypatch.setattr(Path, "write_text", advancing_write)
    _capture_with_native_job(live, output)
    budget = json.loads(output.with_suffix(".budget.json").read_text())
    observed = json.loads(output.read_text())
    raw = json.loads(output.with_suffix(".raw.json").read_text())
    protocol = raw["canary"]["job_protocol"]
    assert raw_writes == [output.with_suffix(".raw.json")]
    assert budget["elapsed_ms"] >= 4000
    assert observed["telemetry"]["latency_seconds"] >= 4
    assert observed["error"] == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert budget["max_active_seconds"] == 1 and budget["source_work_deadline_ms"] == 1000
    assert budget["max_fetcher_calls"] == 60 and budget["max_search_queries"] == 6
    assert budget["finalization_reserve_ms"] == 0 and budget["fetcher_calls"] == 36
    assert native_count(protocol) == {"catalogue:" + ID: 36}
    assert protocol["claim_token"] == 1 and protocol["job_status"] == "running"
    assert protocol["control_type"] == "CancelledError"
    assert protocol["observation_available"] and protocol["heartbeat_done"] == [True]
    assert len(raw["claims"]) == 1 and case.state()["completed"] == 0
    assert read_budget.UNIVERSITY_READ_BUDGET is False


def test_raw_failure_preserves_actual_timeout_and_committed_native_provenance(case, monkeypatch):
    live, output = _capture_persistence_case(case, monkeypatch)
    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", _funding_exceeds_timeout)
    original_write = Path.write_text

    def failed_raw(path, data, *args, **kwargs):
        if path == output.with_suffix(".raw.json"):
            raise OSError("synthetic raw persistence error")
        return original_write(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failed_raw)
    with pytest.raises(TimeoutError):
        _capture_with_native_job(live, output)
    budget = json.loads(output.with_suffix(".budget.json").read_text())
    audit = budget["protocol_persistence_error"]
    assert audit["stage"] == "raw" and audit["error_type"] == "OSError"
    assert audit["original_control_type"] == "TimeoutError"
    assert audit["original_error"] == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert native_count(audit["job_protocol"]) == {"catalogue:" + ID: 36}
    assert audit["job_protocol"]["job_status"] == "running"
    assert audit["job_protocol"]["heartbeat_done"] == [True]
    assert json.loads(output.read_text())["error"] == audit["original_error"]
    assert not output.with_suffix(".raw.json").exists()
    assert case.state()["completed"] == 0 and read_budget.UNIVERSITY_READ_BUDGET is False


def test_raw_failure_preserves_actual_typed_busy_with_readable_prior_state(case, monkeypatch):
    live, output = _capture_persistence_case(case, monkeypatch)
    blockers = []
    original_adapter = rm.WebScholarshipAdapter
    original_write = Path.write_text

    def locked_adapter(*args, **kwargs):
        adapter = original_adapter(*args, **kwargs)
        blocker = case.engines[-1].connect()
        blocker.exec_driver_sql("BEGIN IMMEDIATE")
        blockers.append(blocker)
        return adapter

    def failed_raw(path, data, *args, **kwargs):
        if path == output.with_suffix(".raw.json"):
            raise OSError("synthetic raw persistence error")
        return original_write(path, data, *args, **kwargs)

    monkeypatch.setattr(rm, "WebScholarshipAdapter", locked_adapter)
    monkeypatch.setattr(Path, "write_text", failed_raw)
    try:
        with pytest.raises(UniversityReadStopped) as caught:
            _capture_with_native_job(live, output, 120)
        assert caught.value.reason == "checkpoint_busy"
        audit = json.loads(output.with_suffix(".budget.json").read_text())[
            "protocol_persistence_error"
        ]
        assert audit["original_control_type"] == "UniversityReadStopped"
        assert audit["original_error"] == "UniversityReadStopped: checkpoint_busy"
        assert audit["error_type"] == "OSError" and audit["stage"] == "raw"
        assert native_count(audit["job_protocol"]) == {"catalogue:" + ID: 36}
        assert audit["job_protocol"]["observation_available"]
        assert audit["job_protocol"]["job_status"] == "running"
        assert audit["job_protocol"]["heartbeat_done"] == [True]
    finally:
        for blocker in blockers:
            blocker.rollback()
            blocker.close()
    assert case.state()["completed"] == 0 and len(case.transport) == 36
    assert read_budget.UNIVERSITY_READ_BUDGET is False


def test_successful_job_raw_failure_is_failed_capture_with_honest_job_state(case, monkeypatch):
    live, output = _capture_persistence_case(case, monkeypatch)
    original_write = Path.write_text

    async def no_funding(*args, **kwargs):
        return [], AdapterResult()

    def failed_raw(path, data, *args, **kwargs):
        if path == output.with_suffix(".raw.json"):
            raise OSError("synthetic raw persistence error")
        return original_write(path, data, *args, **kwargs)

    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", no_funding)
    monkeypatch.setattr(Path, "write_text", failed_raw)
    with pytest.raises(RuntimeError, match="^BENCHMARK_PROTOCOL_PERSISTENCE_FAILED$"):
        _capture_with_native_job(live, output, 120)
    observed = json.loads(output.read_text())
    audit = json.loads(output.with_suffix(".budget.json").read_text())["protocol_persistence_error"]
    assert observed["error"] == "BENCHMARK_PROTOCOL_PERSISTENCE_FAILED"
    assert audit["original_control_type"] is None and audit["original_error"] is None
    assert audit["job_protocol"]["job_status"] == "succeeded"
    assert native_count(audit["job_protocol"]) == {"catalogue:" + ID: 36}
    assert case.state()["completed"] == 1 and len(case.transport) == 36
    assert read_budget.UNIVERSITY_READ_BUDGET is False


def test_final_checkpoint_failure_preserves_timeout_without_false_durable_claim(
    case, monkeypatch, capsys
):
    live, output = _capture_persistence_case(case, monkeypatch)
    monkeypatch.setattr(rm.WebScholarshipAdapter, "find", _funding_exceeds_timeout)
    original_write = Path.write_text
    raw_written = [False]

    def failed_checkpoint(path, data, *args, **kwargs):
        if raw_written[0] and path == output.with_suffix(".pending"):
            raise OSError("synthetic final checkpoint error")
        written = original_write(path, data, *args, **kwargs)
        if path == output.with_suffix(".raw.json"):
            raw_written[0] = True
        return written

    monkeypatch.setattr(Path, "write_text", failed_checkpoint)
    with pytest.raises(TimeoutError):
        _capture_with_native_job(live, output)
    raw = json.loads(output.with_suffix(".raw.json").read_text())
    assert native_count(raw["canary"]["job_protocol"]) == {"catalogue:" + ID: 36}
    assert raw["canary"]["job_protocol"]["heartbeat_done"] == [True]
    assert json.loads(output.read_text())["error"] == "CAPTURE_IN_PROGRESS"
    assert (
        "PROTOCOL_PERSISTENCE_FAILED OSError original=BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
        in capsys.readouterr().out
    )
    assert case.state()["status"] == "running" and case.state()["completed"] == 0
    assert read_budget.UNIVERSITY_READ_BUDGET is False
