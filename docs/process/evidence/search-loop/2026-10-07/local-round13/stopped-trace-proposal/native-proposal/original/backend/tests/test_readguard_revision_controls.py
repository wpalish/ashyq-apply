"""Actual caller/transaction regressions for the two independently found blockers."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import event, inspect, select, update

from app.adapters.base import AdapterResult
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import Fetcher
from app.domain.enums import DegreeLevel, PipelineStage
from app.models import AuditEvent, ClaimRow, Job, ProgramResultRow, ResearchRun
from app.pipeline import read_budget
from app.pipeline.control import UniversityReadStopped
from app.pipeline.runner import ResearchRunner, _to_out
from app.schemas.result import CostBreakdown, ProgramResult
from tests import readguard_support as controls
from tests.readguard_support import offline as offline


@pytest.fixture
def context(tmp_path, monkeypatch):
    with controls.sqlite_context(tmp_path, monkeypatch) as value:
        yield value


def snapshot(ctx):
    with ctx.factory() as session:
        return deepcopy(
            session.execute(
                select(ResearchRun.settings_snapshot).where(ResearchRun.id == ctx.run.id)
            ).scalar_one()
        )


def seed_prior(ctx, candidate):
    previous = ProgramResult(
        id="revision-old-result",
        run_id=ctx.run.id,
        university=candidate.name,
        university_id="old-key",
        country=candidate.country,
        city=candidate.city,
        program=candidate.programs[0].name,
        program_url=candidate.programs[0].url,
        degree=DegreeLevel.BACHELOR,
        intake="fall 2027",
    )
    claim = controls.program_claim("Previous completed official evidence")
    previous.claims = [_to_out(claim, "revision-old-claim")]
    ctx.runner._persist_result(previous, [claim], [])
    ctx.runner._save()
    with ctx.factory() as observer:
        return deepcopy(observer.query(ClaimRow).one().payload), deepcopy(
            observer.query(ProgramResultRow).one().payload
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["actual_stage_verify", "actual_run_to_decision"])
@pytest.mark.parametrize("blocker_mode", ["BEGIN IMMEDIATE", "BEGIN EXCLUSIVE"])
async def test_busy_actual_caller_propagates_typed_unknown_without_failed_or_claim_writes(
    context, monkeypatch, entry, blocker_mode
):
    from app.pipeline import runner as runner_module

    fetcher = controls.activate(context)
    candidate = controls.candidate()
    with context.runner._university_read_scope(candidate):
        pass
    prior_claim, prior_result = seed_prior(context, candidate)
    context.runner._candidates = [candidate]
    before = snapshot(context)
    seen = controls.mock_original_get(monkeypatch, context)

    def zero_timeout(dbapi_connection, *args):
        dbapi_connection.execute("PRAGMA busy_timeout=0")

    event.listen(context.engine, "checkout", zero_timeout)
    real_requirements = runner_module.WebRequirementsAdapter
    with context.engine.connect() as blocker:

        def requirements(*args, **kwargs):
            instance = real_requirements(*args, **kwargs)
            blocker.exec_driver_sql(blocker_mode)
            return instance

        monkeypatch.setattr(runner_module, "WebRequirementsAdapter", requirements)
        if entry == "actual_run_to_decision":
            context.runner.state[PipelineStage.PROFILE_VALIDATION].status = "done"

            async def discovered(fetcher):
                context.runner._candidates = [candidate]

            monkeypatch.setattr(context.runner, "_stage_discover", discovered)
        try:
            with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
                if entry == "actual_stage_verify":
                    await context.runner._stage_verify(fetcher)
                else:
                    await context.runner.run_to_decision()
        finally:
            context.session.rollback()
            blocker.rollback()
            event.remove(context.engine, "checkout", zero_timeout)
    assert seen == []
    assert snapshot(context)[read_budget.LEDGER_KEY] == before[read_budget.LEDGER_KEY]
    if entry == "actual_stage_verify":
        assert snapshot(context) == before
    with context.factory() as observer:
        assert observer.query(ClaimRow).one().payload == prior_claim
        assert observer.query(ProgramResultRow).one().payload == prior_result
        persisted = observer.get(ResearchRun, context.run.id)
        assert persisted.stage != PipelineStage.FAILED.value
        assert not any("checkpoint_busy" in text for text in persisted.unknowns or [])
        assert not any("checkpoint_busy" in text for text in persisted.errors or [])
        assert observer.query(AuditEvent).filter(AuditEvent.action == "run_failed").count() == 0
    # Busy is a typed unknown outcome. It cannot durably record a diagnostic
    # while the database refuses every write; the caller must not promise one.


def test_dirty_off_first_replacement_serializes_on_creation_before_60_and_preserves_60(
    context, monkeypatch
):
    fetcher = controls.activate(context)
    candidate = controls.candidate()
    seen = controls.mock_original_get(monkeypatch, context)
    context.session.connection().exec_driver_sql("PRAGMA busy_timeout=0")
    with context.factory() as off_session:
        stale = off_session.get(ResearchRun, context.run.id)
        off = ResearchRunner(
            off_session,
            stale,
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=1,
        )
        off._read_guard_enabled = False
        stale.settings_snapshot = {"off_writer": "predates first namespace"}
        actual = off_session.execute
        intercepted = []

        def execute(statement, *args, **kwargs):
            result = actual(statement, *args, **kwargs)
            if (
                not intercepted
                and getattr(statement, "is_select", False)
                and any(
                    getattr(description.get("expr"), "key", None) == "settings_snapshot"
                    for description in getattr(statement, "column_descriptions", [])
                )
            ):
                old = result.scalar_one()
                intercepted.append(old)

                async def on_work():
                    with context.runner._university_read_scope(candidate):
                        for i in range(60):
                            await fetcher.get("https://example.edu/on/" + str(i))

                # The first snapshot is now protected by the real write lock.
                # The exact A schedule cannot create its namespace inside it.
                with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
                    asyncio.run(on_work())
                return SimpleNamespace(scalar_one=lambda: old)
            return result

        monkeypatch.setattr(off_session, "execute", execute)
        off._save()
        assert seen == []
        monkeypatch.setattr(off_session, "execute", actual)

        async def permitted_then_stopped():
            with context.runner._university_read_scope(candidate):
                for i in range(60):
                    await fetcher.get("https://example.edu/after-unlock/" + str(i))

        asyncio.run(permitted_then_stopped())
        # A second replacement still uses the stale object's first snapshot.
        stale.settings_snapshot = {"off_writer": "second stale replacement"}
        off._save()
        assert controls.counts(context)["catalogue:u-one"] == 60

        async def no_extra():
            with context.runner._university_read_scope(candidate):
                await fetcher.get("https://example.edu/61")

        with pytest.raises(UniversityReadStopped, match="read_cap"):
            asyncio.run(no_extra())
    assert len(seen) == 60


def test_dirty_off_cancel_check_cannot_autoflush_away_first_namespace(context, monkeypatch):
    fetcher = controls.activate(context)
    candidate = controls.candidate()
    controls.mock_original_get(monkeypatch, context)
    with context.factory() as off_session:
        stale = off_session.get(ResearchRun, context.run.id)
        off = ResearchRunner(
            off_session,
            stale,
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=1,
        )
        stale.settings_snapshot = {"off_writer": "dirty before namespace"}

        async def on_work():
            with context.runner._university_read_scope(candidate):
                for i in range(60):
                    await fetcher.get("https://example.edu/on/" + str(i))

        asyncio.run(on_work())
        off._check_cancelled()
        assert read_budget.LEDGER_KEY in snapshot(context)
        assert controls.counts(context)["catalogue:u-one"] == 60
        off._save()
        assert controls.counts(context)["catalogue:u-one"] == 60


@pytest.mark.asyncio
async def test_actual_pending_settings_other_query_does_not_erase_concurrent_namespace(
    context, monkeypatch
):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    fetcher = controls.activate(context)
    candidate = controls.candidate()
    controls.mock_original_get(monkeypatch, context)
    with context.factory() as off_session:
        stale = off_session.get(ResearchRun, context.run.id)
        off = ResearchRunner(
            off_session,
            stale,
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=1,
        )

        async def early_stage():
            assert not inspect(stale).attrs.settings_snapshot.history.has_changes()
            assert off._pending_settings_snapshot is not None
            with context.runner._university_read_scope(candidate):
                await fetcher.get("https://example.edu/concurrent-intent")
            off_session.query(ProgramResultRow).count()  # Actual ordinary query autoflush.
            assert controls.counts(context)["catalogue:u-one"] == 1
            raise UniversityReadStopped("checkpoint_busy")  # Abort before persistence.

        monkeypatch.setattr(off, "_stage_validate", early_stage)
        with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
            await off.run_to_decision()
    assert controls.counts(context)["catalogue:u-one"] == 1


def test_clean_default_off_checkpoint_does_not_reread_or_assign_json(context, monkeypatch):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    context.run.pages_checked = 7

    def forbidden(*args, **kwargs):
        raise AssertionError("Clean default-off checkpoint needs no readguard serialization")

    monkeypatch.setattr(context.runner, "_read_snapshot", forbidden)
    context.runner._save()
    assert context.run.pages_checked == 7
    assert context.run.settings_snapshot == {}


@pytest.mark.parametrize("kind", ["documents", "recheck"])
def test_clean_excluded_job_checkpoint_leaves_namespace_untouched(context, monkeypatch, kind):
    controls.activate(context)
    with context.runner._university_read_scope(controls.candidate()):
        pass
    context.runner._read_guard_enabled = False
    context.job.kind = kind
    context.session.commit()
    before = snapshot(context)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unchanged excluded-job JSON must not gain locking overhead")

    monkeypatch.setattr(context.runner, "_read_snapshot", forbidden)
    context.run.pages_checked = 4
    context.runner._save()
    assert snapshot(context) == before


def test_direct_nojob_dirty_save_takes_actual_run_write_lock_before_snapshot(context, monkeypatch):
    direct = ResearchRunner(context.session, context.run, context.profile, context.settings)
    context.run.settings_snapshot = {"direct": "replacement"}
    statements = []

    def capture(state):
        statements.append(str(state.statement))

    event.listen(context.session, "do_orm_execute", capture)
    direct._save()
    run_write = next(
        i for i, statement in enumerate(statements) if statement.startswith("UPDATE research_runs")
    )
    run_read = next(
        i
        for i, statement in enumerate(statements)
        if "settings_snapshot" in statement and "FOR UPDATE" in statement
    )
    assert run_write < run_read
    assert not any("FROM jobs" in statement for statement in statements)
    assert snapshot(context) == {"direct": "replacement"}


@pytest.mark.asyncio
async def test_same_genuine_job_reclaim_honors_enabled_ledger_after_source_default_off(
    context, monkeypatch
):
    fetcher = controls.activate(context)
    candidate = controls.candidate()
    seen = controls.mock_original_get(monkeypatch, context)
    with context.runner._university_read_scope(candidate):
        for i in range(60):
            await fetcher.get("https://example.edu/prior/" + str(i))
    before = snapshot(context)
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    with context.factory() as updater:
        from datetime import timedelta

        from app.jobs.store import JobStore

        now = datetime.now(UTC)
        updater.execute(
            update(Job)
            .where(Job.id == context.job.id)
            .values(lease_expires_at=now - timedelta(seconds=1))
        )
        updater.commit()
        store = JobStore(updater, worker_id="worker-one")
        assert store.reap_expired(now=now) == [context.job.id]
        updater.execute(
            update(Job)
            .where(Job.id == context.job.id)
            .values(available_at=now - timedelta(seconds=1))
        )
        updater.commit()
        reclaimed = store.claim(worker_id="worker-one")
        assert reclaimed.id == context.job.id and reclaimed.attempts == 2
        updater.commit()
    with context.factory() as new_session:
        retry = ResearchRunner(
            new_session,
            new_session.get(ResearchRun, context.run.id),
            context.profile,
            context.settings,
            job_id=context.job.id,
            worker_id="worker-one",
            lease_token=2,
        )

        async def discovery(current_fetcher):
            assert isinstance(current_fetcher, read_budget.BudgetedFetcher)
            with retry._university_read_scope(candidate):
                await current_fetcher.get("https://example.edu/reclaimed/61")

        retry.state[PipelineStage.PROFILE_VALIDATION].status = "done"
        monkeypatch.setattr(retry, "_stage_discover", discovery)
        with pytest.raises(UniversityReadStopped, match="read_cap"):
            await retry.run_to_decision()
        assert retry._read_guard_enabled is True
    assert len(seen) == 60
    assert snapshot(context)[read_budget.LEDGER_KEY] == before[read_budget.LEDGER_KEY]
    assert controls.counts(context)["catalogue:u-one"] == 60


def previous_episode(ctx):
    previous = Job(
        kind="research",
        run_id=ctx.run.id,
        status="succeeded",
        attempts=1,
        worker_id="worker-one",
        available_at=datetime.now(UTC),
    )
    ctx.session.add(previous)
    ctx.session.flush()
    episode = "decision:" + previous.id
    ctx.run.started_at = datetime(2020, 1, 1, tzinfo=UTC)
    ctx.run.settings_snapshot = {
        read_budget.LEDGER_KEY: {
            "version": 1,
            "read_limit": 60,
            "active_episode": episode,
            "episodes": {episode: {"read_counts": {"catalogue:u-one": 60}}},
        }
    }
    ctx.session.commit()
    return episode


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit_enable", [False, True])
async def test_previous_episode_cannot_prove_untracked_current_job_intent_or_fake_zero(
    context, monkeypatch, explicit_enable
):
    from app.pipeline import runner as runner_module

    old_episode = previous_episode(context)
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", explicit_enable)
    seen = []

    async def original(fetcher, url, **kwargs):
        from app.adapters.fetching import FetchResult
        from app.domain.enums import FetchOutcome

        seen.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", original)
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
    monkeypatch.setattr(controls.catalogue, "retrieve", lambda *args, **kwargs: [uni])

    async def discovered(adapter, entry, profile, **kwargs):
        for i in range(61):
            await adapter.fetcher.get("https://example.edu/legacy/" + str(i))
        return controls.candidate(), DiscoveryTrace("Test University", "example.edu")

    async def requirements(*args, **kwargs):
        return AdapterResult()

    async def cost(*args, **kwargs):
        return CostBreakdown(), AdapterResult()

    async def government(*args, **kwargs):
        return AdapterResult()

    async def funding(*args, **kwargs):
        return [], AdapterResult()

    monkeypatch.setattr(controls.catalogue.CatalogueDiscoveryAdapter, "_discover_one", discovered)
    monkeypatch.setattr(runner_module.WebRequirementsAdapter, "verify", requirements)
    monkeypatch.setattr(runner_module.WebCostAdapter, "fetch", cost)
    monkeypatch.setattr(runner_module.WebGovernmentAdapter, "post_study_work", government)
    monkeypatch.setattr(runner_module.WebScholarshipAdapter, "find", funding)
    if explicit_enable:
        with pytest.raises(UniversityReadStopped, match="legacy_episode_untracked"):
            await context.runner.run_to_decision()
        assert seen == []
    else:
        await context.runner.run_to_decision()
        assert len(seen) == 61  # Named legacy-off behavior, not current ON intent.
    ledger = snapshot(context)[read_budget.LEDGER_KEY]
    assert list(ledger["episodes"]) == [old_episode]
    assert ledger["episodes"][old_episode]["read_counts"]["catalogue:u-one"] == 60


@pytest.mark.asyncio
async def test_malformed_current_on_ledger_is_not_bypassed_after_source_default_off(
    context, monkeypatch
):
    controls.activate(context)
    with context.runner._university_read_scope(controls.candidate()):
        pass
    malformed = deepcopy(context.run.settings_snapshot)
    episode = "decision:" + context.job.id
    malformed[read_budget.LEDGER_KEY]["episodes"][episode]["read_counts"]["catalogue:u-one"] = True
    context.run.settings_snapshot = malformed
    context.session.commit()
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    seen = controls.mock_original_get(monkeypatch, context)
    with pytest.raises(UniversityReadStopped, match="invalid_ledger"):
        await context.runner.run_to_decision()
    assert seen == []
    assert snapshot(context) == malformed


def test_demo_pending_replacement_preserves_legacy_checkpoint_without_readguard_lock(
    context, monkeypatch
):
    context.run.demo_mode = True
    runner = ResearchRunner(context.session, context.run, context.profile, context.settings)
    runner._pending_settings_snapshot = {"demo_mode": True, "test_marker": "legacy"}

    def forbidden(*args, **kwargs):
        raise AssertionError("Demo pending settings do not acquire a research read lock")

    monkeypatch.setattr(runner, "_read_snapshot", forbidden)
    runner._save()
    assert snapshot(context) == {"demo_mode": True, "test_marker": "legacy"}
    assert runner._pending_settings_snapshot is None


@pytest.mark.parametrize("kind", ["documents", "recheck"])
def test_dirty_excluded_job_replacement_serializes_and_preserves_research_namespace(context, kind):
    controls.activate(context)
    with context.runner._university_read_scope(controls.candidate()):
        pass
    before = snapshot(context)[read_budget.LEDGER_KEY]
    job = Job(
        kind=kind,
        run_id=context.run.id,
        status="running",
        attempts=1,
        worker_id="worker-one",
        available_at=datetime.now(UTC),
    )
    context.session.add(job)
    context.session.commit()
    runner = ResearchRunner(
        context.session,
        context.run,
        context.profile,
        context.settings,
        job_id=job.id,
        worker_id="worker-one",
        lease_token=1,
    )
    context.run.settings_snapshot = {"excluded_job": kind}
    runner._save()
    assert snapshot(context)[read_budget.LEDGER_KEY] == before
    assert snapshot(context)["excluded_job"] == kind
    assert runner._read_guard_enabled is False


def test_direct_nojob_dirty_replacement_real_sqlite_busy_is_typed_and_writes_nothing(context):
    before = snapshot(context)
    direct = ResearchRunner(context.session, context.run, context.profile, context.settings)
    context.run.settings_snapshot = {"direct": "never committed"}
    context.session.connection().exec_driver_sql("PRAGMA busy_timeout=0")
    with context.engine.connect() as blocker:
        blocker.exec_driver_sql("BEGIN IMMEDIATE")
        with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
            direct._save()
        blocker.rollback()
    assert snapshot(context) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["discovery", "funding"])
async def test_busy_actual_other_source_caller_stays_typed_and_preserves_prior_evidence(
    context, monkeypatch, stage
):
    from app.pipeline import runner as runner_module

    fetcher = controls.activate(context)
    candidate = controls.candidate()
    with context.runner._university_read_scope(candidate):
        pass
    prior_claim, prior_result = seed_prior(context, candidate)
    context.runner._candidates = [candidate]
    seen = controls.mock_original_get(monkeypatch, context)

    def zero_timeout(dbapi_connection, *args):
        dbapi_connection.execute("PRAGMA busy_timeout=0")

    event.listen(context.engine, "checkout", zero_timeout)
    with context.engine.connect() as blocker:
        if stage == "discovery":

            def retrieve(*args, **kwargs):
                blocker.exec_driver_sql("BEGIN IMMEDIATE")
                return [
                    SimpleNamespace(
                        id="u-one",
                        name=candidate.name,
                        country=candidate.country,
                        city=candidate.city,
                        domain=candidate.domain,
                        registry_entry={},
                    )
                ]

            monkeypatch.setattr(controls.catalogue, "retrieve", retrieve)
        else:
            real_adapter = runner_module.WebScholarshipAdapter

            def adapter(*args, **kwargs):
                instance = real_adapter(*args, **kwargs)
                blocker.exec_driver_sql("BEGIN IMMEDIATE")
                return instance

            monkeypatch.setattr(runner_module, "WebScholarshipAdapter", adapter)
        try:
            with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
                if stage == "discovery":
                    await context.runner._stage_discover(fetcher)
                else:
                    await context.runner._stage_funding(fetcher)
        finally:
            context.session.rollback()
            blocker.rollback()
            event.remove(context.engine, "checkout", zero_timeout)
    assert seen == []
    with context.factory() as observer:
        assert observer.query(ClaimRow).one().payload == prior_claim
        assert observer.query(ProgramResultRow).one().payload == prior_result
        assert not any(
            "checkpoint_busy" in text
            for text in observer.get(ResearchRun, context.run.id).unknowns or []
        )


@pytest.mark.asyncio
async def test_resume_intent_read_busy_is_typed_before_setup_or_source_io(context, monkeypatch):
    controls.activate(context)
    with context.runner._university_read_scope(controls.candidate()):
        pass
    before = snapshot(context)
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    seen = controls.mock_original_get(monkeypatch, context)
    context.session.connection().exec_driver_sql("PRAGMA busy_timeout=0")
    with context.engine.connect() as blocker:
        blocker.exec_driver_sql("BEGIN EXCLUSIVE")
        with pytest.raises(UniversityReadStopped, match="checkpoint_busy"):
            await context.runner.run_to_decision()
        blocker.rollback()
    assert seen == []
    assert snapshot(context) == before
    with context.factory() as observer:
        assert observer.query(AuditEvent).filter(AuditEvent.action == "run_failed").count() == 0
