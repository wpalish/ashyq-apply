"""Native readguard production-path regressions; no external source loader."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import event, update

from app.adapters.base import AdapterResult, Candidate
from app.adapters.discovery.catalog_walker import CatalogWalker
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher, FetchResult
from app.catalogue import discovery as catalogue
from app.domain.enums import ClaimType, DegreeLevel, PipelineStage
from app.models import (
    AuditEvent,
    ClaimRow,
    Job,
    ProgramResultRow,
    ResearchRun,
)
from app.pipeline import read_budget
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.runner import ResearchRunner
from app.schemas.result import CostBreakdown, ProgramResult
from tests import readguard_support as controls
from tests.readguard_support import activate, candidate, counts, mock_original_get, program_claim
from tests.readguard_support import offline as offline


@pytest.fixture
def context(tmp_path, monkeypatch):
    with controls.sqlite_context(tmp_path, monkeypatch) as value:
        yield value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome", ["ok", "cached", "http_error", "robots_disallowed", "refused_privacy"]
)
async def test_60_actual_fetcher_get_then_no_original_61(context, monkeypatch, outcome):
    fetcher = activate(context)
    cand = candidate()
    seen = mock_original_get(monkeypatch, context, outcome=outcome)
    with context.runner._university_read_scope(cand):
        for i in range(60):
            await fetcher.get("https://example.edu/" + str(i), use_cache=True)
        with pytest.raises(UniversityReadStopped, match="read_cap"):
            await fetcher.get("https://example.edu/blocked")
    assert len(seen) == 60
    assert [x["durable"]["catalogue:u-one"] for x in seen] == list(range(1, 61))
    assert counts(context) == {"catalogue:u-one": 60}
    assert context.run.pages_failed == 0


@pytest.mark.asyncio
async def test_conditional_cache_arguments_are_preserved(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context, outcome="cached")
    with context.runner._university_read_scope(candidate()):
        await fetcher.get(
            "https://example.edu/page",
            use_cache=False,
            etag="public-tag",
            if_modified_since="public-date",
        )
    assert seen[0]["kwargs"] == {
        "use_cache": False,
        "etag": "public-tag",
        "if_modified_since": "public-date",
    }
    assert counts(context)["catalogue:u-one"] == 1


@pytest.mark.asyncio
async def test_same_university_all_programmes_and_stages_share_counter(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    for stage in [
        PipelineStage.CANDIDATE_DISCOVERY,
        PipelineStage.PROGRAM_VERIFICATION,
        PipelineStage.FUNDING_DISCOVERY,
    ]:
        context.run.stage = stage.value
        for programme in range(2):
            with context.runner._university_read_scope(candidate()):
                for i in range(10):
                    await fetcher.get(f"https://example.edu/{stage.value}/{programme}/{i}")
    assert len(seen) == 60
    with (
        pytest.raises(UniversityReadStopped, match="read_cap"),
        context.runner._university_read_scope(candidate()),
    ):
        await fetcher.get("https://gov.example.gov/permit")
    with context.runner._university_read_scope(candidate("u-two")):
        await fetcher.get("https://gov.example.gov/permit")
    assert counts(context) == {"catalogue:u-one": 60, "catalogue:u-two": 1}


@pytest.mark.asyncio
async def test_worker_retry_and_stale_attempt_same_worker_never_reset(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        for i in range(58):
            await fetcher.get(f"https://example.edu/old/{i}")
    with context.factory() as changer:
        changer.execute(update(Job).where(Job.id == context.job.id).values(attempts=2))
        changer.commit()
    with pytest.raises(LeaseLost), context.runner._university_read_scope(candidate()):
        await fetcher.get("https://example.edu/stale")
    assert len(seen) == 58
    with context.factory() as newer:
        run = newer.get(ResearchRun, context.run.id)
        next_runner = ResearchRunner(
            newer,
            run,
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=2,
        )
        next_runner._read_guard_enabled = True
        next_runner._read_episode_fresh = False
        f = next_runner._make_fetcher()
        with next_runner._university_read_scope(candidate()):
            await f.get("https://example.edu/retry/1")
            await f.get("https://example.edu/retry/2")
            with pytest.raises(UniversityReadStopped, match="read_cap"):
                await f.get("https://example.edu/retry/3")
    assert len(seen) == 60
    assert counts(context)["catalogue:u-one"] == 60


@pytest.mark.asyncio
async def test_save_refreshes_stale_json_without_erasing_pending_counters(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        await fetcher.get("https://example.edu/1")
    stale = deepcopy(context.run.settings_snapshot)
    with context.factory() as fresh:
        run = fresh.get(ResearchRun, context.run.id)
        ledger = deepcopy(run.settings_snapshot)
        ledger[read_budget.LEDGER_KEY]["episodes"]["decision:" + context.job.id]["read_counts"][
            "catalogue:u-one"
        ] = 59
        ledger[read_budget.LEDGER_KEY]["opaque_query_ledger"] = {"queries_reserved": 4}
        run.settings_snapshot = ledger
        fresh.commit()
    context.run.settings_snapshot = stale
    context.run.pages_checked += 7
    context.runner._save()
    assert counts(context)["catalogue:u-one"] == 59
    with context.runner._university_read_scope(candidate()):
        await fetcher.get("https://example.edu/60")
    assert counts(context)["catalogue:u-one"] == 60
    with context.factory() as observer:
        run = observer.get(ResearchRun, context.run.id)
        assert run.pages_checked == 7
        assert run.settings_snapshot[read_budget.LEDGER_KEY]["opaque_query_ledger"] == {
            "queries_reserved": 4
        }
    assert len(seen) == 2


@pytest.mark.asyncio
async def test_scope_less_or_unfenced_get_has_no_original_call(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with pytest.raises(UniversityReadStopped, match="missing_university_scope"):
        await fetcher.get("https://example.edu/none")
    context.runner.job_id = None
    with (
        pytest.raises(UniversityReadStopped, match="unfenced_episode"),
        context.runner._university_read_scope(candidate()),
    ):
        await fetcher.get("https://example.edu/unfenced")
    assert seen == []


@pytest.mark.asyncio
async def test_cancel_is_not_budget_or_http_failure_and_does_not_reserve(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        await fetcher.get("https://example.edu/1")
        with context.factory() as changer:
            changer.execute(
                update(ResearchRun).where(ResearchRun.id == context.run.id).values(cancelled=True)
            )
            changer.commit()
        with pytest.raises(RunCancelled):
            await fetcher.get("https://example.edu/cancelled")
    assert len(seen) == 1 and counts(context)["catalogue:u-one"] == 1


@pytest.mark.asyncio
async def test_foreign_asyncio_cancel_preserves_pre_io_reservation(context, monkeypatch):
    fetcher = activate(context)
    started = asyncio.Event()

    async def wait_forever(fetcher, url, **kwargs):
        assert counts(context)["catalogue:u-one"] == 1
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(Fetcher, "_get", wait_forever)
    with context.runner._university_read_scope(candidate()):
        task = asyncio.create_task(fetcher.get("https://example.edu/pending"))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert counts(context)["catalogue:u-one"] == 1


@pytest.mark.asyncio
async def test_checkpoint_failure_prevents_original_io(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):

        def refuse_commit():
            raise RuntimeError("offline injected DB commit refusal")

        monkeypatch.setattr(context.session, "commit", refuse_commit)
        with pytest.raises(RuntimeError, match="DB commit refusal"):
            await fetcher.get("https://example.edu/no-commit")
    context.session.rollback()
    assert seen == [] and counts(context)["catalogue:u-one"] == 0


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        [],
        {},
        {"version": 1, "read_limit": 61, "episodes": {}},
        {"version": True, "read_limit": 60, "episodes": {}},
        {"version": 1, "read_limit": 60, "episodes": {"x": {"read_counts": {"x": True}}}},
        {"version": 1, "read_limit": 60, "episodes": {"x": {"read_counts": {"x": -1}}}},
    ],
)
def test_corrupt_envelope_no_reset_no_io(context, invalid):
    activate(context)
    context.run.settings_snapshot = {read_budget.LEDGER_KEY: invalid}
    context.session.commit()
    with (
        pytest.raises(UniversityReadStopped, match="invalid_ledger"),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert context.run.settings_snapshot[read_budget.LEDGER_KEY] == invalid


def test_curated_identity_exact_normalization_and_qualifier_distinction():
    a = Candidate("  Test  University (North) ", "ExAMPLE", "City")
    b = Candidate("test university (north)", "example", "Other city")
    c = Candidate("Test University (South)", "Example", "City")
    assert read_budget.university_key(a) == read_budget.university_key(b)
    assert read_budget.university_key(a) != read_budget.university_key(c)
    with pytest.raises(UniversityReadStopped):
        read_budget.university_key(Candidate("", "Example", "City"))


@pytest.mark.asyncio
async def test_real_catalogue_discovery_61_is_local_unknown(context, monkeypatch):
    fetcher = activate(context)
    seen = mock_original_get(monkeypatch, context)
    uni = SimpleNamespace(
        id="u-one",
        name="Test University",
        country="Example",
        city="City",
        domain="example.edu",
        registry_entry={
            "name": "Test University",
            "country": "Example",
            "city": "City",
            "homepage": "https://example.edu/",
        },
    )
    monkeypatch.setattr(catalogue, "retrieve", lambda *a, **k: [uni])

    async def deep(adapter, entry, profile, **kwargs):
        for i in range(61):
            await adapter.fetcher.get(f"https://example.edu/discovery/{i}")
        return candidate(), DiscoveryTrace("Test University", "example.edu")

    monkeypatch.setattr(catalogue.CatalogueDiscoveryAdapter, "_discover_one", deep)
    adapter = context.runner._make_discovery_adapter(fetcher)
    out = await adapter.discover(context.profile, 1)
    assert len(seen) == 60 and len(out) == 1
    assert out[0].catalogue_id == "u-one" and out[0].programs == []
    assert any("read_cap" in x and "unknown" in x for x in adapter.traces[0].search_limitations)
    assert not any("HTTP" in x for x in adapter.traces[0].errors)


@pytest.mark.asyncio
async def test_legacy_flag_off_still_allows_61(context, monkeypatch):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    f = context.runner._make_fetcher()
    assert type(f) is Fetcher

    async def success(fetcher, url, **kwargs):
        from app.domain.enums import FetchOutcome

        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", success)
    for i in range(61):
        await f.get(f"https://example.edu/{i}")
    assert read_budget.LEDGER_KEY not in context.run.settings_snapshot


@pytest.mark.asyncio
async def test_actual_disk_cache_hit_is_charged(context):
    from app.domain.enums import FetchOutcome

    f = activate(context)
    url = "https://example.edu/degree"
    f.cache.put(
        FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            content=b"BSc Computer Science",
            text="BSc Computer Science",
            final_url=url,
        )
    )
    with context.runner._university_read_scope(candidate()):
        for i in range(60):
            page = await f.get(url)
            assert page.from_cache and counts(context)["catalogue:u-one"] == i + 1
        with pytest.raises(UniversityReadStopped, match="read_cap"):
            await f.get(url)
    assert f.stats["cached"] == 60


@pytest.mark.asyncio
async def test_fence_loss_between_precheck_and_job_lock_prevents_charge(context, monkeypatch):
    f = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        original_lock = context.runner._lock_read_checkpoint_job

        def race():
            with context.factory() as newer:
                newer.execute(update(Job).where(Job.id == context.job.id).values(attempts=2))
                newer.commit()
            original_lock()

        monkeypatch.setattr(context.runner, "_lock_read_checkpoint_job", race)
        with pytest.raises(LeaseLost):
            await f.get("https://example.edu/race")
    assert seen == [] and counts(context)["catalogue:u-one"] == 0


@pytest.mark.asyncio
async def test_existing_save_final_heartbeat_refusal_rolls_back_reserved_charge(
    context, monkeypatch
):
    from app.jobs.store import JobStore

    f = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        monkeypatch.setattr(JobStore, "heartbeat", lambda *args, **kwargs: False)
        with pytest.raises(LeaseLost):
            await f.get("https://example.edu/final-fence-refusal")
    assert seen == [] and counts(context)["catalogue:u-one"] == 0


@pytest.mark.asyncio
async def test_failed_original_get_reservation_never_refunded(context, monkeypatch):
    f = activate(context)

    async def original(fetcher, url, **kwargs):
        raise ValueError("offline injected parse failure")

    monkeypatch.setattr(Fetcher, "_get", original)
    with context.runner._university_read_scope(candidate()), pytest.raises(ValueError):
        await f.get("https://example.edu/broken")
    assert counts(context)["catalogue:u-one"] == 1


@pytest.mark.asyncio
async def test_real_run_to_decision_shared_61_stops_funding_and_preserves_programme(
    context, monkeypatch
):
    from app.pipeline import runner as runner_module

    seen = mock_original_get(monkeypatch, context)
    uni = SimpleNamespace(
        id="u-one",
        name="Test University",
        country="Example",
        city="City",
        domain="example.edu",
        registry_entry={
            "name": "Test University",
            "country": "Example",
            "city": "City",
            "homepage": "https://example.edu/",
        },
    )
    monkeypatch.setattr(catalogue, "retrieve", lambda *a, **k: [uni])

    async def discovered(adapter, entry, profile, **kwargs):
        for i in range(11):
            await adapter.fetcher.get(f"https://example.edu/discovery/{i}")
        return candidate(), DiscoveryTrace("Test University", "example.edu")

    async def requirements(adapter, cand, prog, intake):
        for i in range(25):
            await adapter.fetcher.get(f"https://example.edu/requirements/{i}")
        return AdapterResult(claims=[program_claim()], pages_checked=25)

    async def cost(adapter, cand):
        return CostBreakdown(), AdapterResult()

    async def government(adapter, country):
        return AdapterResult()

    async def scholarships(adapter, cand, prog, profile, **kwargs):
        for i in range(25):
            await adapter.fetcher.get(f"https://example.edu/funding/{i}")
        return [], AdapterResult()

    monkeypatch.setattr(catalogue.CatalogueDiscoveryAdapter, "_discover_one", discovered)
    monkeypatch.setattr(runner_module.WebRequirementsAdapter, "verify", requirements)
    monkeypatch.setattr(runner_module.WebCostAdapter, "fetch", cost)
    monkeypatch.setattr(runner_module.WebGovernmentAdapter, "post_study_work", government)
    monkeypatch.setattr(runner_module.WebScholarshipAdapter, "find", scholarships)
    await context.runner.run_to_decision()
    assert len(seen) == 60 and counts(context) == {"catalogue:u-one": 60}
    assert context.run.stage == PipelineStage.AWAITING_USER_DECISION.value
    assert context.run.pages_failed == 0
    assert context.session.query(ClaimRow).count() == 1
    result = ProgramResult.model_validate(context.session.query(ProgramResultRow).one().payload)
    assert any(c.claim_type is ClaimType.PROGRAM_EXISTS for c in result.claims)
    assert any(q.topic == "research read allowance" for q in result.unresolved)
    assert any("read_cap" in message for message in context.run.unknowns)
    assert not any("read allowance" in message for message in context.run.errors)
    # Exact run_to_decision settings replacement on a later worker retry keeps 60.
    with context.factory() as change:
        change.execute(update(Job).where(Job.id == context.job.id).values(attempts=2))
        change.commit()
    with context.factory() as newer:
        run = newer.get(ResearchRun, context.run.id)
        retry = ResearchRunner(
            newer,
            run,
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=2,
        )
        await retry.run_to_decision()
        assert len(seen) == 60
        assert (
            run.settings_snapshot[read_budget.LEDGER_KEY]["episodes"]["decision:" + context.job.id][
                "read_counts"
            ]["catalogue:u-one"]
            == 60
        )
        assert newer.query(ClaimRow).count() == 1
        assert not any("read allowance" in message for message in run.errors)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing", [False, True], ids=["new_partial_row", "existing_evidence_preserved"]
)
async def test_actual_verify_later_cost_stop_keeps_completed_requirements(
    context, monkeypatch, existing
):
    from app.pipeline import runner as runner_module

    f = activate(context)
    seen = mock_original_get(monkeypatch, context)
    cand = candidate()
    context.runner._candidates = [cand]
    original = None
    if existing:
        with context.runner._university_read_scope(cand):
            pass  # Genuine guarded intent precedes the seeded prior evidence.
        result = ProgramResult(
            id="synthetic-result",
            run_id=context.run.id,
            university=cand.name,
            university_id="test-key",
            country=cand.country,
            city=cand.city,
            program="BSc Computer Science",
            program_url=cand.programs[0].url,
            degree=DegreeLevel.BACHELOR,
            intake="fall 2027",
        )
        claim = program_claim("Old official degree identity")
        from app.pipeline.runner import _to_out

        result.claims = [_to_out(claim, "old-claim")]
        context.runner._persist_result(result, [claim], [])
        context.runner._save()
        original = context.session.query(ClaimRow).one().payload.copy()

    async def requirements(adapter, cand, prog, intake):
        for i in range(40):
            await adapter.fetcher.get(f"https://example.edu/requirements/{i}")
        return AdapterResult(
            claims=[program_claim("New completed degree identity")], pages_checked=40
        )

    async def cost(adapter, cand):
        for i in range(21):
            await adapter.fetcher.get(f"https://example.edu/cost/{i}")
        return CostBreakdown(), AdapterResult()

    async def government(adapter, country):
        return AdapterResult()

    monkeypatch.setattr(runner_module.WebRequirementsAdapter, "verify", requirements)
    monkeypatch.setattr(runner_module.WebCostAdapter, "fetch", cost)
    monkeypatch.setattr(runner_module.WebGovernmentAdapter, "post_study_work", government)
    await context.runner._stage_verify(f)
    assert len(seen) == 60 and counts(context)["catalogue:u-one"] == 60
    assert context.run.pages_failed == 0
    result = ProgramResult.model_validate(context.session.query(ProgramResultRow).one().payload)
    assert any(q.topic == "research read allowance" for q in result.unresolved)
    assert context.session.query(ClaimRow).count() == 1
    if existing:
        assert context.session.query(ClaimRow).one().payload == original
        assert result.claims[0].original_text_excerpt == "Old official degree identity"
        retained = (
            context.session.query(AuditEvent)
            .filter(AuditEvent.action == "partial_read_evidence_retained")
            .one()
        )
        assert (
            retained.detail["claims"][0]["original_text_excerpt"] == "New completed degree identity"
        )
        assert (
            context.run.claims_recorded == 0
        )  # Quarantined audit proof is not reported as displayed claims.
    else:
        assert result.claims[0].original_text_excerpt == "New completed degree identity"
        assert context.run.claims_recorded == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("signal", [RunCancelled, LeaseLost, UniversityReadStopped])
async def test_catalogue_walker_broad_catch_does_not_swallow_control_stop(
    context, monkeypatch, signal
):
    walker = CatalogWalker(
        fetcher=context.runner._make_fetcher(),
        domain="example.edu",
        degree="bachelor",
        fields=["computer science"],
    )

    async def stopped(*args, **kwargs):
        raise signal("offline_control")

    monkeypatch.setattr(walker, "walk_catalog", stopped)
    with pytest.raises(signal):
        await walker.walk(["https://example.edu/catalogue"])


@pytest.mark.asyncio
@pytest.mark.parametrize("signal", [RunCancelled, LeaseLost, UniversityReadStopped])
async def test_sitemap_broad_catch_does_not_swallow_control_stop(context, monkeypatch, signal):
    adapter = LiveDiscoveryAdapter(context.runner._make_fetcher())

    async def stopped(*args, **kwargs):
        raise signal("offline_control")

    monkeypatch.setattr(adapter.sitemaps, "collect", stopped)
    entry = {
        "name": "Test University",
        "country": "Example",
        "city": "City",
        "homepage": "https://example.edu/",
    }
    with pytest.raises(signal):
        await adapter._discover_one(entry, context.profile)


@pytest.mark.asyncio
async def test_curated_fallback_real_discovery_loop_has_stable_scope(context, monkeypatch):
    f = activate(context)
    seen = mock_original_get(monkeypatch, context)
    monkeypatch.setattr(catalogue, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(
        LiveDiscoveryAdapter,
        "registry",
        lambda _: [
            {
                "name": "Test University",
                "country": "Example",
                "city": "City",
                "homepage": "https://example.edu/",
            }
        ],
    )

    async def deep(adapter, entry, profile, **kwargs):
        for i in range(61):
            await adapter.fetcher.get(f"https://example.edu/curated/{i}")
        return Candidate(entry["name"], entry["country"], entry["city"]), DiscoveryTrace(
            entry["name"], "example.edu"
        )

    monkeypatch.setattr(LiveDiscoveryAdapter, "_discover_one", deep)
    context.run.university_ids = None
    adapter = context.runner._make_discovery_adapter(f)
    out = await adapter.discover(context.profile, 1)
    assert len(seen) == 60 and out[0].catalogue_id is None
    assert counts(context) == {read_budget.university_key(out[0]): 60}


@pytest.mark.asyncio
async def test_documents_explicitly_do_not_claim_guard_contract_but_keep_ledger(
    context, monkeypatch
):
    f = activate(context)
    mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        await f.get("https://example.edu/1")
    context.runner._candidates = [candidate()]
    built = await context.runner.collect_documents()
    assert built == 0 and context.runner._read_guard_enabled is False
    assert type(context.runner._make_fetcher()) is Fetcher
    assert counts(context)["catalogue:u-one"] == 1


def test_fresh_row_statement_requests_for_update(context, monkeypatch):
    activate(context)
    statements = []
    from sqlalchemy import event

    def observed(orm_execute_state):
        statement = orm_execute_state.statement
        if hasattr(statement, "_for_update_arg") and statement._for_update_arg is not None:
            statements.append(statement)

    event.listen(context.session, "do_orm_execute", observed)
    with context.runner._university_read_scope(candidate()):
        pass
    assert statements
    from sqlalchemy.dialects import postgresql

    assert "FOR UPDATE" in str(statements[-1].compile(dialect=postgresql.dialect()))


@pytest.mark.parametrize("missing", ["active_episode", "current_episode"])
def test_missing_active_episode_is_corrupt_not_fresh_allowance(context, missing):
    activate(context)
    ledger = read_budget.new_ledger()
    key = "decision:" + context.job.id
    ledger["active_episode"] = key
    ledger["episodes"][key] = {"read_counts": {"catalogue:u-one": 60}}
    if missing == "active_episode":
        ledger.pop("active_episode")
    else:
        ledger["episodes"].pop(key)
    context.run.settings_snapshot = {read_budget.LEDGER_KEY: ledger}
    context.session.commit()
    with (
        pytest.raises(UniversityReadStopped, match="invalid_ledger"),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert context.run.settings_snapshot[read_budget.LEDGER_KEY] == ledger


def test_missing_retry_episode_never_resets_to_zero(context):
    activate(context)
    previous = Job(
        kind="research",
        run_id=context.run.id,
        status="done",
        attempts=1,
        worker_id="worker-one",
        available_at=datetime.now(UTC),
    )
    context.session.add(previous)
    context.session.flush()
    ledger = read_budget.new_ledger()
    ledger["active_episode"] = "decision:" + previous.id
    ledger["episodes"]["decision:" + previous.id] = {"read_counts": {"catalogue:u-one": 60}}
    context.run.settings_snapshot = {read_budget.LEDGER_KEY: ledger}
    context.job.attempts = 2
    context.session.commit()
    context.runner.lease_token = 2
    context.runner._read_episode_fresh = False
    with (
        pytest.raises(UniversityReadStopped, match="missing_retry_episode"),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert context.run.settings_snapshot[read_budget.LEDGER_KEY] == ledger


@pytest.mark.asyncio
async def test_untracked_new_job_on_started_run_is_unknown_preserving_old_history(
    context, monkeypatch
):
    f = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        await f.get("https://example.edu/old")
    old_job_id = context.job.id
    fresh = Job(
        kind="research",
        run_id=context.run.id,
        status="running",
        attempts=1,
        worker_id="worker-one",
        available_at=datetime.now(UTC),
    )
    context.session.add(fresh)
    context.session.commit()
    newer = ResearchRunner(
        context.session,
        context.run,
        context.profile,
        context.settings,
        job_id=fresh.id,
        worker_id="worker-one",
        lease_token=1,
    )
    newer._read_guard_enabled = True
    newer._read_episode_fresh = False
    with (
        pytest.raises(UniversityReadStopped, match="legacy_episode_untracked"),
        newer._university_read_scope(candidate()),
    ):
        await newer._make_fetcher().get("https://example.edu/new")
    ledger = context.run.settings_snapshot[read_budget.LEDGER_KEY]
    assert ledger["episodes"]["decision:" + old_job_id]["read_counts"]["catalogue:u-one"] == 1
    assert "decision:" + fresh.id not in ledger["episodes"]
    assert ledger["active_episode"] == "decision:" + old_job_id
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_guard_off_checkpoint_with_existing_envelope_preserves_latest(context, monkeypatch):
    f = activate(context)
    mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        await f.get("https://example.edu/1")
    with context.factory() as change:
        run = change.get(ResearchRun, context.run.id)
        replacement = deepcopy(run.settings_snapshot)
        replacement[read_budget.LEDGER_KEY]["episodes"]["decision:" + context.job.id][
            "read_counts"
        ]["catalogue:u-one"] = 60
        run.settings_snapshot = replacement
        change.commit()
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    context.runner._read_guard_enabled = False
    context.runner._save()
    assert counts(context)["catalogue:u-one"] == 60


@pytest.mark.asyncio
async def test_lock_order_job_then_run_and_both_nowait(context, monkeypatch):
    f = activate(context)
    mock_original_get(monkeypatch, context)
    locks = []

    def capture(state):
        statement = state.statement
        arg = getattr(statement, "_for_update_arg", None)
        if arg is not None:
            locks.append((str(statement), arg.nowait))

    event.listen(context.session, "do_orm_execute", capture)
    with context.runner._university_read_scope(candidate()):
        await f.get("https://example.edu/1")
    assert len(locks) >= 4
    for i in range(0, len(locks), 2):
        assert "jobs" in locks[i][0] and "research_runs" in locks[i + 1][0]
        assert locks[i][1] is True and locks[i + 1][1] is True
    assert "jobs.attempts" in locks[0][0] and "jobs.worker_id" in locks[0][0]


@pytest.mark.asyncio
async def test_postgres_lock_unavailable_refuses_read_without_dispatch(context, monkeypatch):
    from sqlalchemy.exc import OperationalError

    f = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):

        def busy(*args, **kwargs):
            raise OperationalError("offline NOWAIT refusal", {}, SimpleNamespace(sqlstate="55P03"))

        monkeypatch.setattr(context.runner, "_lock_read_checkpoint_job", busy)
        with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
            await f.get("https://example.edu/busy")
    assert seen == [] and counts(context)["catalogue:u-one"] == 0


@pytest.mark.asyncio
async def test_parallel_same_episode_reads_never_exceed_60(context, monkeypatch):
    f = activate(context)
    seen = mock_original_get(monkeypatch, context)

    async def one(i):
        try:
            await f.get(f"https://example.edu/concurrent/{i}")
            return "admitted"
        except UniversityReadStopped:
            return "stopped"

    with context.runner._university_read_scope(candidate()):
        outcomes = await asyncio.gather(*(one(i) for i in range(65)))
    assert outcomes.count("admitted") == 60 and outcomes.count("stopped") == 5
    assert len(seen) == 60 and counts(context)["catalogue:u-one"] == 60


def test_demo_factory_never_claims_new_live_guard(context):
    context.run.demo_mode = True
    runner = ResearchRunner(context.session, context.run, context.profile, context.settings)
    assert type(runner._make_fetcher()) is Fetcher


@pytest.mark.asyncio
async def test_recheck_explicitly_excluded_and_ledger_preserved(context, monkeypatch):
    f = activate(context)
    mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        await f.get("https://example.edu/1")
    old = deepcopy(context.run.settings_snapshot[read_budget.LEDGER_KEY])
    # A stale synthetic claim makes the real recheck entry point call decision stages.
    claim = program_claim()
    claim.accessed_at = datetime(2020, 1, 1, tzinfo=UTC)
    context.session.add(
        ClaimRow(
            run_id=context.run.id,
            result_id=None,
            claim_type=claim.claim_type.value,
            status=claim.status.value,
            source_url=claim.source_url,
            source_specificity=claim.source_specificity.value,
            accessed_at=claim.accessed_at,
            payload=claim.model_dump(mode="json"),
        )
    )
    context.session.commit()
    observed = []

    async def entered():
        observed.append(context.runner._read_guard_out_of_scope)

    monkeypatch.setattr(context.runner, "run_to_decision", entered)
    assert await context.runner.recheck_stale() == 1
    assert observed == [True]
    assert context.run.settings_snapshot[read_budget.LEDGER_KEY] == old


@pytest.mark.asyncio
@pytest.mark.parametrize("signal", [RunCancelled, LeaseLost, UniversityReadStopped])
async def test_standalone_renderer_control_not_swallowed(context, signal):
    async def render(url):
        raise signal("offline renderer control")

    f = context.runner._make_fetcher()
    f._renderer = SimpleNamespace(render=render, catalog_payloads=[])
    walker = CatalogWalker(
        fetcher=f, domain="example.edu", degree="bachelor", fields=["computer science"]
    )
    with pytest.raises(signal):
        await walker._read_catalogue("https://example.edu/catalogue")


@pytest.mark.parametrize("invalid_count", [-1, 61, True, False, "1", 1.5, None])
def test_bad_count_with_valid_episode_and_university_key_never_resets(context, invalid_count):
    activate(context)
    episode_id = "decision:" + context.job.id
    ledger = {
        "version": 1,
        "read_limit": 60,
        "active_episode": episode_id,
        "episodes": {episode_id: {"read_counts": {"catalogue:u-one": invalid_count}}},
    }
    context.run.settings_snapshot = {read_budget.LEDGER_KEY: ledger}
    context.session.commit()
    with (
        pytest.raises(UniversityReadStopped, match="invalid_ledger"),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert context.run.settings_snapshot[read_budget.LEDGER_KEY] == ledger


@pytest.mark.parametrize(
    "episode_id,reason",
    [
        ("arbitrary-episode", "invalid_ledger"),
        ("decision:nonexistent-job", "unknown_saved_episode"),
    ],
)
def test_unknown_saved_episode_cannot_create_new_allowance(context, episode_id, reason):
    activate(context)
    context.runner._read_episode_fresh = False
    ledger = {
        "version": 1,
        "read_limit": 60,
        "active_episode": episode_id,
        "episodes": {episode_id: {"read_counts": {"catalogue:u-one": 60}}},
    }
    context.run.settings_snapshot = {read_budget.LEDGER_KEY: ledger}
    context.session.commit()
    with (
        pytest.raises(UniversityReadStopped, match=reason),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert context.run.settings_snapshot[read_budget.LEDGER_KEY] == ledger


@pytest.mark.asyncio
async def test_same_job_two_stale_runners_share_fresh_row_counter(context, monkeypatch):
    first = activate(context)
    seen = mock_original_get(monkeypatch, context)
    with context.factory() as second_session:
        stale_run = second_session.get(ResearchRun, context.run.id)
        second_runner = ResearchRunner(
            second_session,
            stale_run,
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=1,
        )
        second_runner._read_guard_enabled = True
        second_runner._read_episode_fresh = False
        second = second_runner._make_fetcher()
        for i in range(30):
            with context.runner._university_read_scope(candidate()):
                await first.get(f"https://example.edu/first/{i}")
            with second_runner._university_read_scope(candidate()):
                await second.get(f"https://example.edu/second/{i}")
        with (
            pytest.raises(UniversityReadStopped, match="read_cap"),
            second_runner._university_read_scope(candidate()),
        ):
            await second.get("https://example.edu/no61")
    assert len(seen) == 60
    assert [entry["durable"]["catalogue:u-one"] for entry in seen] == list(range(1, 61))
    assert counts(context)["catalogue:u-one"] == 60


def test_started_legacy_episode_without_ledger_fails_closed(context):
    activate(context)
    context.runner._read_episode_fresh = False
    context.session.commit()  # Persist actual pre-existing started state.
    with (
        pytest.raises(UniversityReadStopped, match="legacy_episode_untracked"),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert read_budget.LEDGER_KEY not in context.run.settings_snapshot


@pytest.mark.asyncio
async def test_real_direct_run_without_worker_job_is_unknown_before_get(context, monkeypatch):
    seen = mock_original_get(monkeypatch, context)
    uni = SimpleNamespace(
        id="u-one",
        name="Test University",
        country="Example",
        city="City",
        domain="example.edu",
        registry_entry={},
    )
    monkeypatch.setattr(catalogue, "retrieve", lambda *a, **k: [uni])
    direct = ResearchRunner(context.session, context.run, context.profile, context.settings)
    await direct.run_to_decision()
    assert seen == []
    assert direct._candidates[0].programs == []
    assert any("unfenced_episode" in text for text in context.run.unknowns)
    assert context.run.pages_failed == 0


def test_nonresearch_fenced_job_has_no_decision_allowance(context):
    activate(context)
    context.job.kind = "documents"
    context.session.commit()
    with (
        pytest.raises(UniversityReadStopped, match="unsupported_job_episode"),
        context.runner._university_read_scope(candidate()),
    ):
        pass
    assert read_budget.LEDGER_KEY not in context.run.settings_snapshot


def test_guard_off_stale_snapshot_that_predates_namespace_still_keeps_latest(context):
    stale = deepcopy(context.run.settings_snapshot)
    assert read_budget.LEDGER_KEY not in stale
    episode = "decision:" + context.job.id
    ledger = {
        "version": 1,
        "read_limit": 60,
        "active_episode": episode,
        "episodes": {episode: {"read_counts": {"catalogue:u-one": 60}}},
    }
    with context.factory() as fresh:
        row = fresh.get(ResearchRun, context.run.id)
        row.settings_snapshot = {read_budget.LEDGER_KEY: ledger}
        fresh.commit()
    context.run.settings_snapshot = stale
    context.run.pages_checked = 3
    context.runner._read_guard_enabled = False
    context.runner._save()
    assert counts(context)["catalogue:u-one"] == 60
    assert context.run.pages_checked == 3


@pytest.mark.asyncio
async def test_guarded_cancellation_read_never_autoflushes_run_before_job_lock(
    context, monkeypatch
):
    f = activate(context)
    mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate()):
        context.run.pages_checked = 11
        statements = []

        def capture(state):
            statements.append(str(state.statement))

        def flush_capture(
            connection, cursor, statement, parameters, execution_context, executemany
        ):
            if statement.startswith("UPDATE research_runs"):
                statements.append(statement)

        event.listen(context.session, "do_orm_execute", capture)
        event.listen(context.engine, "before_cursor_execute", flush_capture)
        await f.get("https://example.edu/pending-progress")
        first_job = next(
            i
            for i, value in enumerate(statements)
            if "FROM jobs" in value and "FOR UPDATE" in value
        )
        first_run_update = next(
            i for i, value in enumerate(statements) if value.startswith("UPDATE research_runs")
        )
        assert first_job < first_run_update
    assert context.run.pages_checked == 11


def test_actual_application_module_paths_control_classes_and_default(tmp_path):
    """Provenance checks ordinary imports, never a shadow candidate fallback."""
    import ast
    import hashlib
    import importlib
    import json
    from pathlib import Path

    from app.jobs import worker as worker_module
    from app.pipeline import control
    from app.pipeline import runner as runner_module

    backend = Path(__file__).resolve().parents[1]
    names = [
        "app.adapters.base",
        "app.pipeline.runner",
        "app.catalogue.discovery",
        "app.adapters.discovery.live_discovery",
        "app.adapters.discovery.catalog_walker",
        "app.pipeline.control",
        "app.pipeline.read_budget",
        "app.jobs.worker",
        "app.adapters.fetching",
    ]
    manifest = []
    for name in names:
        module = importlib.import_module(name)
        source = Path(module.__file__).resolve()
        expected = backend / Path(*name.split(".")).with_suffix(".py")
        assert source == expected.resolve()
        manifest.append(
            {
                "module": name,
                "path": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    assert worker_module.UniversityReadStopped is control.UniversityReadStopped
    assert runner_module.LeaseLost is control.LeaseLost
    assert runner_module.RunCancelled is control.RunCancelled
    assert read_budget.UNIVERSITY_READ_BUDGET is False
    tree = ast.parse(Path(read_budget.__file__).read_text())
    defaults = [
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "UNIVERSITY_READ_BUDGET"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
    ]
    assert defaults == [False]
    (tmp_path / "actual-imports.json").write_text(
        json.dumps({"modules": manifest, "default": False, "same_control_classes": True}, indent=2)
        + "\n"
    )


def test_context_initial_claim_uses_real_enqueued_job_token_one(context):
    with context.factory() as observer:
        persisted = observer.get(Job, context.job_id)
        assert persisted.status == "running"
        assert persisted.attempts == 1 and persisted.worker_id == "worker-one"
        assert persisted.idempotency_key == "test-research:" + context.run_id
        assert persisted.run_id == context.run_id
