"""Actual SQL fences/native I/O controls, entirely offline synthetic evidence."""

import asyncio
import socket
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import update

from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.search import SearchResponse, _ThrottleLatch
from app.domain.enums import FetchOutcome
from app.jobs.store import JobStore
from app.models import Job, ResearchRun
from app.pipeline.control import LeaseLost, UniversityReadStopped
from app.research import runtime, staging
from app.research.io import ACTIVE_RESERVATION
from tests import readguard_support as support


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original_connect = socket.socket.connect

    def connect(sock, address):
        # Windows asyncio creates its private socketpair using loopback TCP.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("External network forbidden")

    def deny(*args, **kwargs):
        raise AssertionError("Network/provider/model forbidden")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(httpx.AsyncClient, "send", deny)
    monkeypatch.setattr(httpx.Client, "send", deny)


@pytest.fixture
def context(tmp_path, monkeypatch):
    with support.sqlite_context(tmp_path, monkeypatch) as ctx:
        monkeypatch.setattr("app.pipeline.read_budget.UNIVERSITY_READ_BUDGET", False)
        ctx.run.settings_snapshot = runtime.replace(
            {
                runtime.INTENT_KEY: {
                    "enabled": True,
                    "mode": "fast_then_deep",
                    "deep_tier": 300,
                }
            },
            staging.StagedResearch(episode_id=ctx.run_id, research_mode="fast_then_deep"),
        )
        ctx.session.commit()
        ctx.runner._staged_enabled = True
        assert ctx.runner.prepare_staged("research")
        yield ctx


def durable(ctx):
    with ctx.factory() as session:
        return runtime.load(session.get(ResearchRun, ctx.run_id).settings_snapshot)


def count(ctx, field):
    return getattr(
        next(u for u in durable(ctx).universities if u.university == "catalogue:u-one"), field
    )


@pytest.mark.asyncio
async def test_native_fetcher_sees_durable_reservation_before_original_get(context, monkeypatch):
    observed = []

    async def get(self, url, **kwargs):
        observed.append(count(context, "reads"))
        return FetchResult(url=url, outcome=FetchOutcome.CACHED, text="public")

    monkeypatch.setattr(Fetcher, "_get", get)
    fetcher = context.runner._make_fetcher()
    token = ACTIVE_RESERVATION.set(context.runner._reserve_staged_io)
    try:
        with context.runner._university_read_scope(support.candidate()):
            for i in range(60):
                await fetcher.get(f"https://example.edu/{i}")
            with pytest.raises(UniversityReadStopped, match="staged_budget_cap"):
                await fetcher.get("https://example.edu/refused")
    finally:
        ACTIVE_RESERVATION.reset(token)
    assert observed == list(range(1, 61))
    assert count(context, "reads") == 60


@pytest.mark.asyncio
async def test_actual_search_latch_fences_calls_before_provider(context):
    observed = []

    class Provider:
        name = "staged-synthetic"

        async def search(self, *, query, domains=(), max_results=10):
            observed.append(count(context, "queries"))
            return SearchResponse(
                query=query, provider=self.name, retrieved_at=datetime.now(UTC), results=()
            )

    provider = _ThrottleLatch(Provider())
    token = ACTIVE_RESERVATION.set(context.runner._reserve_staged_io)
    try:
        with context.runner._university_read_scope(support.candidate()):
            for _ in range(6):
                await provider.search(query="public university")
            with pytest.raises(UniversityReadStopped):
                await provider.search(query="refused")
    finally:
        ACTIVE_RESERVATION.reset(token)
    assert observed == list(range(1, 7))


@pytest.mark.asyncio
async def test_stale_attempt_cannot_reserve_or_dispatch(context, monkeypatch):
    calls = []

    async def get(self, url, **kwargs):
        calls.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", get)
    with context.factory() as session:
        session.execute(update(Job).where(Job.id == context.job_id).values(attempts=2))
        session.commit()
    token = ACTIVE_RESERVATION.set(context.runner._reserve_staged_io)
    try:
        with pytest.raises(LeaseLost), context.runner._university_read_scope(support.candidate()):
            await context.runner._make_fetcher().get("https://example.edu/")
    finally:
        ACTIVE_RESERVATION.reset(token)
    assert calls == []
    assert durable(context).universities == ()


@pytest.mark.asyncio
async def test_real_native_timeout_is_enforced(context, monkeypatch):
    fixed = {"session_id": "test-clock", "monotonic_ms": 0, "wall_at": datetime.now(UTC)}
    monkeypatch.setattr(runtime, "clock", lambda: fixed)
    ledger = durable(context)
    ledger = staging.StagedResearch.model_validate(
        {
            **ledger.model_dump(),
            "universities": (
                staging.UniversityUsage(university="catalogue:u-one", elapsed_ms=119999),
            ),
        }
    )
    context.run.settings_snapshot = runtime.replace(context.run.settings_snapshot, ledger)
    context.session.commit()
    completed = []

    async def slow(self, url, **kwargs):
        await asyncio.sleep(0.05)
        completed.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", slow)
    token = ACTIVE_RESERVATION.set(context.runner._reserve_staged_io)
    try:
        with (
            context.runner._university_read_scope(support.candidate()),
            pytest.raises(UniversityReadStopped, match="staged_time_cap"),
        ):
            await context.runner._make_fetcher().get("https://example.edu/")
    finally:
        ACTIVE_RESERVATION.reset(token)
    assert completed == [] and count(context, "reads") == 1


def test_deep_queue_phase_and_insert_are_idempotent(context):
    store = JobStore(context.session, worker_id="worker-one")
    context.runner.finish_staged(store)
    context.runner.finish_staged(store)
    assert durable(context).phase == "deep_queued"
    with context.factory() as session:
        jobs = (
            session.query(Job)
            .filter(Job.run_id == context.run_id, Job.kind == "research_deep")
            .all()
        )
        assert len(jobs) == 1
        assert jobs[0].idempotency_key == durable(context).enqueue_key


def test_ordinary_save_preserves_durable_staged_namespace(context):
    context.run.settings_snapshot = {"demo_mode": False}
    context.runner._save()
    assert durable(context).phase == "fast"
    assert runtime.enabled(context.run.settings_snapshot)


@pytest.mark.asyncio
async def test_actual_worker_fast_then_deep_retains_reservations_and_user_decisions(
    context, monkeypatch
):
    from contextlib import contextmanager

    from app.catalogue.discovery import CatalogueDiscoveryAdapter
    from app.jobs.worker import Worker
    from app.models import ProgramResultRow

    @contextmanager
    def session_scope():
        with context.factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    monkeypatch.setattr("app.jobs.worker.session_scope", session_scope)

    # Underlying native Fetcher remains in the actual pipeline, with public synthetic bytes.
    async def get(self, url, **kwargs):
        return FetchResult(
            url=url,
            final_url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            text="<title>BSc Computer Science</title><h1>Bachelor of Science in Computer Science</h1><p>IELTS overall band of 6.5.</p>",
        )

    monkeypatch.setattr(Fetcher, "_get", get)

    async def discovery(self, profile, limit=50):
        cand = support.candidate()
        self.traces = []
        with self.research_scope(cand):
            await self.fetcher.get("https://example.edu/")
        return [cand]

    monkeypatch.setattr(CatalogueDiscoveryAdapter, "discover", discovery)
    worker = Worker(context.settings, worker_id="worker-one")
    await worker.execute(context.job_id)
    assert durable(context).phase == "deep_queued"
    first_count = count(context, "reads")
    assert first_count > 0
    with context.factory() as session:
        rows = session.query(ProgramResultRow).filter_by(run_id=context.run_id).all()
        assert rows
        row = rows[0]
        row.user_decision = "approved"
        row.user_notes = "Keep my preliminary choice"
        row_id = row.id
        session.commit()
    deep_id = worker.claim_one()
    assert deep_id is not None
    await worker.execute(deep_id)
    assert durable(context).phase == "complete"
    assert count(context, "reads") > first_count
    with context.factory() as session:
        row = session.get(ProgramResultRow, row_id)
        assert row.user_decision == "approved" and row.user_notes == "Keep my preliminary choice"
        assert session.get(Job, deep_id).status == "succeeded"
        assert (
            session.query(Job).filter_by(run_id=context.run_id, kind="research_deep").count() == 1
        )


@pytest.mark.asyncio
async def test_actual_deep_job_continues_fast_query_ledger(context):
    from app.pipeline.runner import ResearchRunner

    observed = []

    class Provider:
        name = "two-phase-synthetic"

        async def search(self, *, query, domains=(), max_results=10):
            observed.append(count(context, "queries"))
            return SearchResponse(
                query=query, provider=self.name, retrieved_at=datetime.now(UTC), results=()
            )

    provider = _ThrottleLatch(Provider())
    token = ACTIVE_RESERVATION.set(context.runner._reserve_staged_io)
    try:
        with context.runner._university_read_scope(support.candidate()):
            for _ in range(6):
                await provider.search(query="public university")
    finally:
        ACTIVE_RESERVATION.reset(token)
    store = JobStore(context.session, worker_id="worker-one")
    context.runner.finish_staged(store)
    assert store.complete(context.job_id, lease_token=1)
    context.session.commit()
    deep = store.claim(worker_id="worker-one")
    assert deep.kind == "research_deep"
    context.session.commit()
    runner = ResearchRunner(
        context.session,
        context.run,
        context.profile,
        context.settings,
        job_id=deep.id,
        worker_id="worker-one",
        lease_token=deep.attempts,
    )
    assert runner.prepare_staged("research_deep")
    token = ACTIVE_RESERVATION.set(runner._reserve_staged_io)
    try:
        with runner._university_read_scope(support.candidate()):
            for _ in range(6):
                await provider.search(query="public university deep")
            with pytest.raises(UniversityReadStopped, match="staged_budget_cap"):
                await provider.search(query="thirteenth refused")
    finally:
        ACTIVE_RESERVATION.reset(token)
    assert observed == list(range(1, 13))
    assert count(context, "queries") == 12


@pytest.mark.asyncio
async def test_cancel_before_next_io_prevents_dispatch(context, monkeypatch):
    from app.pipeline.control import RunCancelled

    calls = []

    async def get(self, url, **kwargs):
        calls.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", get)
    token = ACTIVE_RESERVATION.set(context.runner._reserve_staged_io)
    try:
        with (
            pytest.raises(RunCancelled),
            context.runner._university_read_scope(support.candidate()),
        ):
            with context.factory() as session:
                session.execute(
                    update(ResearchRun)
                    .where(ResearchRun.id == context.run_id)
                    .values(cancelled=True)
                )
                JobStore(session).cancel(context.job_id)
                session.commit()
            await context.runner._make_fetcher().get("https://example.edu/cancelled")
    finally:
        ACTIVE_RESERVATION.reset(token)
    assert calls == [] and count(context, "reads") == 0


def test_saved_intent_cannot_mismatch_ledger(context):
    snapshot = context.run.settings_snapshot.copy()
    snapshot[runtime.INTENT_KEY] = {"enabled": True, "mode": "fast", "deep_tier": 900}
    with pytest.raises(ValueError, match="mismatch"):
        runtime.load(snapshot)
