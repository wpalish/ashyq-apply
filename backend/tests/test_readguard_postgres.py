"""Actual PostgreSQL native guard/fence tests; SQLite and historical PG09 are separate."""

from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select, text, update

from app.adapters.discovery.catalog_walker import CatalogWalker
from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.catalogue import discovery
from app.domain.enums import PipelineStage
from app.jobs.store import JobStore
from app.models import AuditEvent, Job, ResearchRun, SourcePage
from app.pipeline import read_budget
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.runner import ResearchRunner
from tests import readguard_support as c
from tests.readguard_support import offline as offline

activate = c.activate
candidate = c.candidate
counts = c.counts
snapshot = c.snapshot
original_mock = c.original_mock
new_runner = c.new_runner
lock_row = c.lock_row
seed_prior = c.seed_prior
prior = c.prior
error_chain = c.error_chain


@pytest.fixture
def ctx(pg_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", True)

    def timeout(connection, record):
        connection.execute("SET statement_timeout=1500")

    event.listen(pg_engine, "connect", timeout)
    with pg_engine.connect() as conn:
        conn.exec_driver_sql("SET statement_timeout=1500")
        conn.commit()
    with c.make_context(pg_engine, tmp_path) as value:
        yield value


def test_pg_00_real_isolated_runtime_and_independent_sessions(ctx):
    with ctx.factory() as a, ctx.factory() as b:
        first = a.execute(
            text(
                "SELECT pg_backend_pid(), current_schema(), current_setting('server_version'), current_setting('listen_addresses')"
            )
        ).one()
        second = b.execute(text("SELECT pg_backend_pid()")).scalar_one()
        assert first[0] != second and ctx.engine.dialect.name == "postgresql"
        assert first[1] == "public" and first[3] == ""
        ctx.record(
            "PG-00",
            {
                "backend_pids": [first[0], second],
                "schema": first[1],
                "server_version": first[2],
                "listen_addresses": first[3],
                "original_io": 0,
            },
        )


@pytest.mark.parametrize("row", ["job", "run"])
def test_pg_01_02_actual_nowait_lock_order_and_rollback(ctx, monkeypatch, row):
    fetcher = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    before = snapshot(ctx)
    with ctx.factory() as blocker:
        lock_row(ctx, blocker, row)
        start = time.monotonic_ns()
        with (
            pytest.raises(UniversityReadStopped) as info,
            ctx.runner._university_read_scope(candidate()),
        ):
            asyncio.run(fetcher.get("https://example.edu/denied"))
        end = time.monotonic_ns()
        assert info.value.reason == "checkpoint_busy"
        assert info.value.__cause__.orig.sqlstate == "55P03"
        assert not ctx.session.in_transaction()
        assert seen == [] and snapshot(ctx) == before
        if row == "run":
            with ctx.factory() as observer:
                observer.execute(
                    select(Job.id).where(Job.id == ctx.job_id).with_for_update(nowait=True)
                )
        blocker.rollback()
    lock_sql = [q["sql"] for q in ctx.queries if "sql" in q and "FOR UPDATE NOWAIT" in q["sql"]]
    assert "jobs" in lock_sql[0]
    if row == "run":
        assert "research_runs" in lock_sql[1]
    ctx.record(
        "PG-01" if row == "job" else "PG-02",
        {
            "exception": error_chain(info.value),
            "caller_elapsed_ns": end - start,
            "lock_sql": lock_sql,
            "original_get": len(seen),
            "counter_before_after": [before, snapshot(ctx)],
            "job_lock_released": row == "run",
        },
    )


def test_pg_03_exact_80_attempts_60_committed_admissions_two_pg_sessions(ctx, monkeypatch):
    activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        pass
    cv = threading.Condition()
    turn = {"next": 0}
    outcomes = []
    pids = []
    errors = []

    def thread_work(index):
        try:
            with ctx.factory() as s:
                pids.append(s.execute(text("SELECT pg_backend_pid()")).scalar_one())
                s.commit()
                r = new_runner(ctx, s)
                fetcher = r._make_fetcher()
                for i in range(40):
                    ordinal = 2 * i + index
                    with cv:
                        ok = cv.wait_for(
                            lambda ordinal=ordinal: turn["next"] == ordinal, timeout=10
                        )
                        assert ok, ("round_robin_timeout", ordinal)
                        try:
                            with r._university_read_scope(candidate()):
                                asyncio.run(
                                    fetcher.get(
                                        f"https://example.edu/program-{index}/{i}", use_cache=True
                                    )
                                )
                            outcomes.append({"ordinal": ordinal, "status": "admitted"})
                        except UniversityReadStopped as exc:
                            outcomes.append({"ordinal": ordinal, "status": exc.reason})
                        finally:
                            turn["next"] += 1
                            cv.notify_all()
        except BaseException as exc:
            errors.append(error_chain(exc))

    ts = [threading.Thread(target=thread_work, args=(i,)) for i in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(15)
        assert not t.is_alive()
    ctx.record(
        "PG-03",
        {
            "attempts": len(outcomes),
            "original_get": len(seen),
            "outcomes": outcomes,
            "seen": seen,
            "durable": counts(ctx),
            "backend_pids": pids,
            "errors": errors,
            "coordination": "round-robin attempt start, no retry",
        },
    )
    assert not errors and len(set(pids)) == 2
    assert len(outcomes) == 80 and len(seen) == 60
    assert sum(x["status"] == "read_cap" for x in outcomes) == 20
    assert [x["durable"]["catalogue:u-one"] for x in seen] == list(range(1, 61))
    assert counts(ctx) == {"catalogue:u-one": 60}


def test_pg_04_simultaneous_nowait_and_cap_saturation_no_hidden_retry(ctx, monkeypatch):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        for i in range(59):
            asyncio.run(f.get(f"https://example.edu/prior/{i}"))
    holding = threading.Event()
    release = threading.Event()
    first_errors = []

    def first():
        try:
            with ctx.factory() as s:
                r = new_runner(ctx, s)
                fetcher = r._make_fetcher()
                original = r._lock_read_checkpoint_job

                def hold():
                    original()
                    holding.set()
                    assert release.wait(5)

                r._lock_read_checkpoint_job = hold
                with r._university_read_scope(candidate()):
                    asyncio.run(fetcher.get("https://example.edu/last"))
        except BaseException as exc:
            first_errors.append(error_chain(exc))

    thread = threading.Thread(target=first)
    thread.start()
    assert holding.wait(5)
    with ctx.factory() as s:
        r = new_runner(ctx, s)
        ff = r._make_fetcher()
        with (
            pytest.raises(UniversityReadStopped) as info,
            r._university_read_scope(candidate()),
        ):
            asyncio.run(ff.get("https://example.edu/racing-denied"))
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
    release.set()
    thread.join(5)
    assert not thread.is_alive() and not first_errors
    with (
        pytest.raises(UniversityReadStopped, match="read_cap"),
        ctx.runner._university_read_scope(candidate()),
    ):
        asyncio.run(f.get("https://example.edu/61"))
    statuses = []
    errors = []
    ready = threading.Barrier(2)

    def race(index):
        try:
            with ctx.factory() as s:
                r = new_runner(ctx, s)
                ff = r._make_fetcher()
                ready.wait(5)
                for i in range(40):
                    try:
                        with r._university_read_scope(candidate("concurrent")):
                            asyncio.run(ff.get(f"https://example.edu/race-{index}/{i}"))
                        statuses.append("admitted")
                    except UniversityReadStopped as exc:
                        statuses.append(exc.reason)
        except BaseException as exc:
            errors.append(error_chain(exc))

    ts = [threading.Thread(target=race, args=(i,)) for i in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(15)
        assert not t.is_alive()
    ctx.record(
        "PG-04",
        {
            "saturation_prior_gets": 59,
            "racing_refusal": error_chain(info.value),
            "saturation_count": counts(ctx).get("catalogue:u-one"),
            "concurrent_attempts": len(statuses),
            "concurrent_outcomes": {x: statuses.count(x) for x in set(statuses)},
            "concurrent_admitted_original": sum("/race-" in x["url"] for x in seen),
            "durable": counts(ctx),
            "errors": errors,
            "retry": False,
        },
    )
    assert not errors and len(statuses) == 80
    n = sum("/race-" in x["url"] for x in seen)
    assert n == statuses.count("admitted") and n <= 60
    assert counts(ctx)["catalogue:concurrent"] == n and counts(ctx)["catalogue:u-one"] == 60


@pytest.mark.parametrize("new_worker", ["worker-two", "worker-one"])
def test_pg_05_real_reap_claim_fresh_attempt_fence(ctx, monkeypatch, new_worker):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        asyncio.run(f.get("https://example.edu/before-reap"))
    now = datetime.now(UTC)
    with ctx.factory() as other:
        other.execute(
            update(Job)
            .where(Job.id == ctx.job_id)
            .values(lease_expires_at=now - timedelta(seconds=1))
        )
        other.commit()
        store = JobStore(other, worker_id=new_worker)
        assert store.reap_expired(now=now) == [ctx.job_id]
        other.execute(
            update(Job).where(Job.id == ctx.job_id).values(available_at=now - timedelta(seconds=1))
        )
        other.commit()
        claimed = store.claim(worker_id=new_worker)
        assert claimed.id == ctx.job_id and claimed.attempts == 2
        other.commit()
    with (
        pytest.raises(LeaseLost),
        ctx.runner._university_read_scope(candidate()),
    ):
        asyncio.run(f.get("https://example.edu/stale"))
    assert len(seen) == 1 and counts(ctx)["catalogue:u-one"] == 1
    with ctx.factory() as current:
        r = new_runner(ctx, current, new_worker, 2)
        monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
        assert r._effective_read_guard() is True
        with r._university_read_scope(candidate()):
            asyncio.run(r._make_fetcher().get("https://example.edu/reclaimed"))
    ctx.record(
        "PG-05-" + new_worker,
        {
            "original_get": len(seen),
            "durable": counts(ctx),
            "new_worker": new_worker,
            "new_attempt": 2,
            "stale_denied": True,
            "recorded_on_source_false": True,
            "expiry_alone_claim": False,
        },
    )
    assert len(seen) == 2 and counts(ctx)["catalogue:u-one"] == 2


@pytest.mark.parametrize("kind", ["user", "coroutine"])
def test_pg_06_committed_user_cancel_and_post_charge_async_cancel(ctx, monkeypatch, kind):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        if kind == "user":
            asyncio.run(f.get("https://example.edu/before-cancel"))
            with ctx.factory() as cancel:
                assert JobStore(cancel).cancel(ctx.job_id)
                cancel.commit()
            with pytest.raises(RunCancelled):
                asyncio.run(f.get("https://example.edu/after-cancel"))
            assert len(seen) == 1
        else:

            async def entered(fetcher, url, **kwargs):
                assert counts(ctx)["catalogue:u-one"] == 1
                raise asyncio.CancelledError("independent cancellation after committed charge")

            monkeypatch.setattr(Fetcher, "_get", entered)
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(f.get("https://example.edu/coroutine-cancel"))
    ctx.record(
        "PG-06-" + kind,
        {
            "durable": counts(ctx),
            "original_mock_completed": len(seen),
            "post_charge_no_refund": kind == "coroutine",
            "pages_failed": ctx.run.pages_failed,
        },
    )
    assert counts(ctx)["catalogue:u-one"] == 1 and ctx.run.pages_failed == 0


def test_pg_07_first_namespace_dirty_off_save_serializes_and_preserves_60(ctx, monkeypatch):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    interleaved = []
    with ctx.factory() as off_s:
        off_run = off_s.get(ResearchRun, ctx.run_id)
        off = ResearchRunner(
            off_s,
            off_run,
            ctx.profile,
            ctx.settings,
            job_id=ctx.job_id,
            worker_id="worker-one",
            lease_token=1,
        )
        off_run.settings_snapshot = {"off_writer": "first dirty replacement"}
        actual = off_s.execute

        def intercept(statement, *args, **kwargs):
            result = actual(statement, *args, **kwargs)
            if (
                not interleaved
                and getattr(statement, "is_select", False)
                and any(
                    getattr(d.get("expr"), "key", None) == "settings_snapshot"
                    for d in getattr(statement, "column_descriptions", [])
                )
            ):
                value = result.scalar_one()
                with (
                    pytest.raises(UniversityReadStopped) as info,
                    ctx.runner._university_read_scope(candidate()),
                ):
                    asyncio.run(f.get("https://example.edu/interleaved"))
                interleaved.append(error_chain(info.value))
                assert info.value.reason == "checkpoint_busy"
                return SimpleNamespace(scalar_one=lambda: value)
            return result

        monkeypatch.setattr(off_s, "execute", intercept)
        off._save()
        monkeypatch.setattr(off_s, "execute", actual)
        assert seen == []
        f = activate(ctx)
        with ctx.runner._university_read_scope(candidate()):
            for i in range(60):
                asyncio.run(f.get(f"https://example.edu/allowed/{i}"))
        saved_ledger = deepcopy(snapshot(ctx)[read_budget.LEDGER_KEY])
        off_run.settings_snapshot = {"off_writer": "second stale replacement"}
        off._save()
        assert snapshot(ctx)[read_budget.LEDGER_KEY] == saved_ledger
        with (
            pytest.raises(UniversityReadStopped, match="read_cap"),
            ctx.runner._university_read_scope(candidate()),
        ):
            asyncio.run(f.get("https://example.edu/61"))
    ctx.record(
        "PG-07",
        {
            "first_on_refused": interleaved,
            "original_get": len(seen),
            "durable": snapshot(ctx),
            "fresh_namespace_not_erased": True,
            "scope": "dirty/pending checkpoint writer; not universal OFF I/O cap",
        },
    )
    assert len(seen) == 60 and counts(ctx)["catalogue:u-one"] == 60


@pytest.mark.parametrize("row", ["job", "run"])
@pytest.mark.parametrize("entry", ["stage_verify", "run_to_decision"])
def test_pg_08_busy_actual_caller_preserves_completed_facts(ctx, monkeypatch, row, entry):
    from app.pipeline import runner as rm

    f = activate(ctx)
    with ctx.runner._university_read_scope(candidate()):
        pass
    old = seed_prior(ctx)
    before = snapshot(ctx)
    seen = original_mock(monkeypatch, ctx)
    ctx.runner._candidates = [candidate()]
    real = rm.WebRequirementsAdapter
    with ctx.factory() as blocker:

        def requirements(*args, **kwargs):
            value = real(*args, **kwargs)
            lock_row(ctx, blocker, row)
            return value

        monkeypatch.setattr(rm, "WebRequirementsAdapter", requirements)
        if entry == "run_to_decision":
            ctx.runner.state[PipelineStage.PROFILE_VALIDATION].status = "done"

            async def discovered(fetcher):
                ctx.runner._candidates = [candidate()]

            monkeypatch.setattr(ctx.runner, "_stage_discover", discovered)
        start = time.monotonic_ns()
        with pytest.raises(UniversityReadStopped) as info:
            asyncio.run(
                ctx.runner._stage_verify(f)
                if entry == "stage_verify"
                else ctx.runner.run_to_decision()
            )
        elapsed = time.monotonic_ns() - start
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
        assert not ctx.session.in_transaction() and seen == []
        blocker.rollback()
    after = prior(ctx)
    with ctx.factory() as observer:
        persisted = observer.get(ResearchRun, ctx.run_id)
        details = {
            "stage": persisted.stage,
            "unknowns": persisted.unknowns,
            "errors": persisted.errors,
            "run_failed_audits": observer.query(AuditEvent)
            .filter(AuditEvent.action == "run_failed")
            .count(),
        }
    ctx.record(
        "PG-08-" + row + "-" + entry,
        {
            "exception": error_chain(info.value),
            "caller_elapsed_ns": elapsed,
            "original_get": len(seen),
            "prior_before": old,
            "prior_after": after,
            "ledger_before": before[read_budget.LEDGER_KEY],
            "ledger_after": snapshot(ctx)[read_budget.LEDGER_KEY],
            "run": details,
            "durable_busy_unknown_promised": False,
        },
    )
    assert after == old and snapshot(ctx)[read_budget.LEDGER_KEY] == before[read_budget.LEDGER_KEY]
    assert details["stage"] != PipelineStage.FAILED.value and details["run_failed_audits"] == 0
    assert not any("checkpoint_busy" in x for x in details["unknowns"] or [])


def test_pg_10_prior_dirty_run_flush_then_job_nowait_releases_opposite_order(ctx, monkeypatch):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        pass
    original = snapshot(ctx)
    ctx.run.pages_checked = 17
    ctx.session.flush()  # Actual dirty ORM Run row lock predates next guarded Job lock.
    with ctx.factory() as blocker:
        lock_row(ctx, blocker, "job")
        with (
            pytest.raises(UniversityReadStopped) as info,
            ctx.runner._university_read_scope(candidate()),
        ):
            asyncio.run(f.get("https://example.edu/opposite"))
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
        with ctx.factory() as observer:
            observer.execute(
                select(ResearchRun.id)
                .where(ResearchRun.id == ctx.run_id)
                .with_for_update(nowait=True)
            )
        blocker.rollback()
    with ctx.factory() as observer:
        persisted_pages = observer.get(ResearchRun, ctx.run_id).pages_checked
    ctx.record(
        "PG-10",
        {
            "exception": error_chain(info.value),
            "original_get": len(seen),
            "durable_ledger": snapshot(ctx),
            "pages_checked_after_rollback": persisted_pages,
            "prior_run_lock_released": True,
            "deadlock_freedom_claim": False,
        },
    )
    assert not seen and persisted_pages == 0 and snapshot(ctx) == original


def test_pg_11_corrupt_envelope_and_commit_refusal_fail_closed(ctx, monkeypatch):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        pass
    valid = snapshot(ctx)
    with ctx.factory() as other:
        run = other.get(ResearchRun, ctx.run_id)
        run.settings_snapshot = {read_budget.LEDGER_KEY: {"version": True}}
        other.commit()
    with (
        pytest.raises(UniversityReadStopped, match="invalid_ledger"),
        ctx.runner._university_read_scope(candidate()),
    ):
        asyncio.run(f.get("https://example.edu/corrupt"))
    ctx.session.rollback()
    assert not seen
    assert snapshot(ctx) == {read_budget.LEDGER_KEY: {"version": True}}
    with ctx.factory() as other:
        run = other.get(ResearchRun, ctx.run_id)
        run.settings_snapshot = deepcopy(valid)
        other.commit()
    with ctx.runner._university_read_scope(candidate()):

        def refuse():
            raise RuntimeError("independent injected pre-commit refusal")

        monkeypatch.setattr(ctx.session, "commit", refuse)
        with pytest.raises(RuntimeError, match="pre-commit refusal"):
            asyncio.run(f.get("https://example.edu/not-committed"))
        visible = counts(ctx)
        ctx.session.rollback()
    ctx.record(
        "PG-11",
        {
            "original_get": len(seen),
            "counter_visible_while_uncommitted": visible,
            "durable_after_rollback": snapshot(ctx),
            "explicit_rollback": True,
        },
    )
    assert not seen and visible == {"catalogue:u-one": 0} and snapshot(ctx) == valid


@pytest.mark.parametrize("renderer", [False, True])
def test_pg_06_actual_walker_plain_and_renderer_broad_catch_propagates_db_busy(
    ctx, monkeypatch, renderer
):
    f = c.activate(ctx)
    seen = c.original_mock(monkeypatch, ctx)
    if renderer:

        async def render(url):
            return await f.get(url)

        f._renderer = SimpleNamespace(render=render, catalog_payloads=[])
    walker = CatalogWalker(
        fetcher=f, domain="example.edu", degree="bachelor", fields=["computer science"]
    )
    with (
        ctx.runner._university_read_scope(c.candidate()),
        ctx.factory() as blocker,
    ):
        c.lock_row(ctx, blocker, "run")
        with pytest.raises(UniversityReadStopped) as info:
            asyncio.run(walker.walk(["https://example.edu/catalogue"]))
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
        blocker.rollback()
    ctx.record(
        "PG-06-walker-renderer-" + str(renderer),
        {
            "exception": c.error_chain(info.value),
            "original_get": len(seen),
            "durable": c.counts(ctx),
            "actual_walk": True,
            "renderer_callback_uses_guarded_fetcher": renderer,
        },
    )
    assert seen == [] and c.counts(ctx) == {"catalogue:u-one": 0}


@pytest.mark.parametrize("signal", ["cancel", "fence"])
def test_pg_06_actual_walker_cancellation_and_lease_control_not_swallowed(ctx, monkeypatch, signal):
    f = c.activate(ctx)
    seen = c.original_mock(monkeypatch, ctx)
    walker = CatalogWalker(
        fetcher=f, domain="example.edu", degree="bachelor", fields=["computer science"]
    )
    with ctx.runner._university_read_scope(c.candidate()):
        with ctx.factory() as other:
            fields = {"cancel_requested": True} if signal == "cancel" else {"attempts": 2}
            other.execute(update(Job).where(Job.id == ctx.job_id).values(**fields))
            other.commit()
        expected = RunCancelled if signal == "cancel" else LeaseLost
        with pytest.raises(expected) as info:
            asyncio.run(walker.walk(["https://example.edu/catalogue"]))
    ctx.record(
        "PG-06-walker-" + signal,
        {
            "exception": c.error_chain(info.value),
            "original_get": len(seen),
            "durable": c.counts(ctx),
            "actual_walk": True,
        },
    )
    assert seen == [] and c.counts(ctx) == {"catalogue:u-one": 0}


@pytest.mark.parametrize("row", ["job", "run"])
def test_pg_08_actual_funding_busy_retains_prior_claims(ctx, monkeypatch, row):
    from app.pipeline import runner as rm

    f = c.activate(ctx)
    with ctx.runner._university_read_scope(c.candidate()):
        pass
    old = c.seed_prior(ctx)
    seen = c.original_mock(monkeypatch, ctx)
    before = c.snapshot(ctx)
    ctx.runner._candidates = [c.candidate()]
    real = rm.WebScholarshipAdapter
    with ctx.factory() as blocker:

        def scholarship(*args, **kwargs):
            value = real(*args, **kwargs)
            c.lock_row(ctx, blocker, row)
            return value

        monkeypatch.setattr(rm, "WebScholarshipAdapter", scholarship)
        with pytest.raises(UniversityReadStopped) as info:
            asyncio.run(ctx.runner._stage_funding(f))
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
        assert not ctx.session.in_transaction()
        blocker.rollback()
    after = c.prior(ctx)
    ctx.record(
        "PG-08-funding-" + row,
        {
            "exception": c.error_chain(info.value),
            "original_get": len(seen),
            "prior_before": old,
            "prior_after": after,
            "ledger_before": before[read_budget.LEDGER_KEY],
            "ledger_after": c.snapshot(ctx)[read_budget.LEDGER_KEY],
        },
    )
    assert (
        not seen
        and after == old
        and c.snapshot(ctx)[read_budget.LEDGER_KEY] == before[read_budget.LEDGER_KEY]
    )


@pytest.mark.parametrize("route", ["catalogue", "curated"])
def test_pg_09_real_discovery_broad_catch_preserves_typed_busy(ctx, monkeypatch, route):
    f = c.activate(ctx)
    seen = c.original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(c.candidate()):
        pass
    entry = {
        "name": "Independent Test University",
        "country": "Example",
        "city": "City",
        "homepage": "https://example.edu/",
    }
    if route == "catalogue":
        uni = SimpleNamespace(
            id="u-one",
            name=entry["name"],
            country=entry["country"],
            city="City",
            domain="example.edu",
            registry_entry=entry,
        )
        monkeypatch.setattr(discovery, "retrieve", lambda *a, **k: [uni])
    else:
        monkeypatch.setattr(discovery, "retrieve", lambda *a, **k: [])
        monkeypatch.setattr(LiveDiscoveryAdapter, "registry", lambda _: [entry])
        ctx.run.university_ids = None
    adapter = ctx.runner._make_discovery_adapter(f)
    with ctx.factory() as blocker:
        c.lock_row(ctx, blocker, "job")
        with pytest.raises(UniversityReadStopped) as info:
            asyncio.run(adapter.discover(ctx.profile, 1))
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
        blocker.rollback()
    ctx.record(
        "PG-09-discovery-" + route,
        {
            "exception": c.error_chain(info.value),
            "original_get": len(seen),
            "durable": c.counts(ctx),
            "actual_discover_loop": True,
        },
    )
    assert not seen and c.counts(ctx) == {"catalogue:u-one": 0}


def test_pg_10_actual_source_recorder_flush_can_hold_run_before_job_nowait(ctx, monkeypatch):
    f = c.activate(ctx)
    seen = c.original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(c.candidate()):
        pass
    before = c.snapshot(ctx)
    old = c.seed_prior(ctx)
    ctx.run.pages_checked = 23
    adapter = ctx.runner._make_discovery_adapter(f)
    page = adapter.page_recorder(
        url="https://example.edu/earlier-recorded-page",
        registrable_domain="example.edu",
        http_status=200,
        page_type="program_detail",
    )
    assert page.id and ctx.session.query(SourcePage).count() == 1
    with ctx.factory() as blocker:
        c.lock_row(ctx, blocker, "job")
        with (
            pytest.raises(UniversityReadStopped) as info,
            ctx.runner._university_read_scope(c.candidate()),
        ):
            asyncio.run(f.get("https://example.edu/next"))
        assert (
            info.value.reason == "checkpoint_busy" and info.value.__cause__.orig.sqlstate == "55P03"
        )
        with ctx.factory() as third:
            third.execute(
                select(ResearchRun.id)
                .where(ResearchRun.id == ctx.run_id)
                .with_for_update(nowait=True)
            )
        blocker.rollback()
    with ctx.factory() as observer:
        source_count = observer.query(SourcePage).count()
        pages = observer.get(ResearchRun, ctx.run_id).pages_checked
    source_path = __import__("pathlib").Path(
        __import__("app.models.source_page", fromlist=["SourcePage"]).__file__
    )
    ctx.record(
        "PG-10-actual-source-recorder",
        {
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "exception": c.error_chain(info.value),
            "original_get": len(seen),
            "source_rows_after_rollback": source_count,
            "pages_checked_after_rollback": pages,
            "prior_before": old,
            "prior_after": c.prior(ctx),
            "prior_run_lock_released": True,
            "source_insertion_was_uncommitted": True,
        },
    )
    assert (
        not seen
        and source_count == 0
        and pages == 0
        and c.prior(ctx) == old
        and c.snapshot(ctx) == before
    )


def test_pg_07_explicit_new_untracked_default_false_is_legacy_not_universal_cap(ctx, monkeypatch):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", False)
    assert ctx.runner._effective_read_guard() is False
    seen = c.original_mock(monkeypatch, ctx)
    f = ctx.runner._make_fetcher()
    assert type(f) is Fetcher
    for i in range(61):
        asyncio.run(f.get(f"https://example.edu/legacy-off/{i}"))
    ctx.record(
        "PG-07-untracked-off-boundary",
        {
            "original_get": len(seen),
            "durable_snapshot": c.snapshot(ctx),
            "classification": "explicitly excluded untracked OFF legacy path; no universal preexisting OFF/ON deployment cap",
        },
    )
    assert len(seen) == 61 and read_budget.LEDGER_KEY not in c.snapshot(ctx)
