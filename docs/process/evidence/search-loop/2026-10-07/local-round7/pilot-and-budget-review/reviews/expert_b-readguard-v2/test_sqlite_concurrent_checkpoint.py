"""Exercise two actual SQLite sessions, one job attempt, and the real read guard.

The barrier exposes an unlocked snapshot race. It never pauses a holder of
SQLite's real write transaction: that would manufacture a lock deadlock.
"""

# ruff: noqa: E402
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pytest
import test_production_readguard as controls

pytest_plugins = ("test_production_readguard",)
activate = controls.activate
candidate = controls.candidate
counts = controls.counts

from app.adapters.fetching import Fetcher, FetchResult
from app.domain.enums import FetchOutcome
from app.models import ResearchRun
from app.pipeline.control import UniversityReadStopped
from app.pipeline.runner import ResearchRunner


def test_two_sqlite_sessions_cannot_charge_two_gets_as_one(context, monkeypatch):
    activate(context)
    with context.runner._university_read_scope(candidate()):
        pass
    barrier = Barrier(2, timeout=5)
    bodies = []

    async def original(fetcher, url, **kwargs):
        bodies.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", original)

    def worker(index):
        with context.factory() as session:
            run = session.get(ResearchRun, context.run.id)
            runner = ResearchRunner(
                session,
                run,
                context.profile,
                context.settings,
                job_id=context.job.id,
                worker_id="worker-one",
                lease_token=1,
            )
            runner._read_guard_enabled = True
            runner._read_episode_fresh = False
            actual_snapshot = runner._read_snapshot

            def observed_snapshot(*, lock):
                saved = actual_snapshot(lock=lock)
                # FOR UPDATE is ignored by SQLite. A read alone has not
                # acquired a write transaction, so another session can read
                # the same counter before either checkpoint commits.
                database = session.connection().connection.driver_connection
                if not database.in_transaction:
                    barrier.wait()
                return saved

            monkeypatch.setattr(runner, "_read_snapshot", observed_snapshot)

            async def read():
                with runner._university_read_scope(candidate()):
                    await runner._make_fetcher().get(f"https://example.edu/twin/{index}")

            asyncio.run(read())

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, i) for i in range(2)]
        for future in futures:
            future.result(timeout=15)
    assert len(bodies) == 2
    assert counts(context)["catalogue:u-one"] == 2


def test_two_actual_sqlite_sessions_never_admit_more_than_60(context, monkeypatch):
    activate(context)
    with context.runner._university_read_scope(candidate()):
        pass
    start = Barrier(2, timeout=5)
    mutex = Lock()
    bodies = []

    async def original(fetcher, url, **kwargs):
        with mutex:
            bodies.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", original)

    def worker(index):
        with context.factory() as session:
            runner = ResearchRunner(
                session,
                session.get(ResearchRun, context.run.id),
                context.profile,
                context.settings,
                job_id=context.job.id,
                worker_id="worker-one",
                lease_token=1,
            )
            runner._read_guard_enabled = True
            runner._read_episode_fresh = False
            start.wait()

            async def read():
                for i in range(40):
                    try:
                        with runner._university_read_scope(candidate()):
                            await runner._make_fetcher().get(f"https://example.edu/{index}/{i}")
                    except UniversityReadStopped as stopped:
                        assert stopped.reason == "read_cap"
                        break

            asyncio.run(read())

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, i) for i in range(2)]
        for future in futures:
            future.result(timeout=15)
    assert len(bodies) == 60
    assert counts(context)["catalogue:u-one"] == 60


@pytest.mark.asyncio
async def test_actual_sqlite_write_lock_refusal_creates_no_get(context, monkeypatch):
    fetcher = activate(context)
    with context.runner._university_read_scope(candidate()):
        pass
    bodies = []

    async def original(fetcher, url, **kwargs):
        bodies.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.OK)

    monkeypatch.setattr(Fetcher, "_get", original)
    context.session.connection().exec_driver_sql("PRAGMA busy_timeout=0")
    with context.engine.connect() as blocker:
        blocker.exec_driver_sql("BEGIN IMMEDIATE")
        with (
            pytest.raises(UniversityReadStopped, match="checkpoint_busy"),
            context.runner._university_read_scope(candidate()),
        ):
            await fetcher.get("https://example.edu/busy")
        blocker.rollback()
    assert bodies == []
    assert counts(context)["catalogue:u-one"] == 0
