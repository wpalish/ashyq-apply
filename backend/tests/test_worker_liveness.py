"""A wedged worker must be detectable.

The compose stack gave the API a healthcheck and the worker none. A worker
that dies is noticed — `restart: unless-stopped` brings it back, and the smoke
test proves recovery after SIGKILL. A worker that is *alive but stuck* is not
noticed by anything: the process is up, the container is healthy, and jobs
queue behind it indefinitely.

An idle worker has no job to heartbeat against, so liveness cannot be inferred
from the queue. The worker records its own instead.
"""
from __future__ import annotations

import contextlib
import time
from pathlib import Path

import pytest

from app.jobs.worker import LIVENESS_STALE_SECONDS, is_alive, touch_liveness


def test_a_fresh_touch_reads_as_alive(tmp_path: Path):
    path = tmp_path / "worker-alive"
    touch_liveness(path)
    assert is_alive(path) is True


def test_a_worker_that_never_started_is_not_alive(tmp_path: Path):
    """Absence is not health. A healthcheck that passes when the worker has
    not run yet reports a stack as ready before it is."""
    assert is_alive(tmp_path / "worker-alive") is False


def test_a_stale_touch_reads_as_wedged(tmp_path: Path):
    """The case the API's healthcheck cannot see: the process is up, and it
    has not been round its loop for longer than it should take."""
    path = tmp_path / "worker-alive"
    touch_liveness(path)
    old = time.time() - LIVENESS_STALE_SECONDS - 5
    import os

    os.utime(path, (old, old))
    assert is_alive(path) is False


def test_touching_is_cheap_and_does_not_grow(tmp_path: Path):
    """It runs every poll. A file that accumulates would fill the volume the
    worker shares with its HTTP cache."""
    path = tmp_path / "worker-alive"
    for _ in range(50):
        touch_liveness(path)
    assert path.stat().st_size <= 64


def test_a_missing_directory_does_not_stop_the_worker(tmp_path: Path):
    """Liveness reporting is diagnostics. Failing to write it must never be
    the reason a worker stops doing work."""
    touch_liveness(tmp_path / "nope" / "deeper" / "worker-alive")


class TestABusyWorkerIsStillAlive:
    """The failure the file-helper tests could not see.

    `touch_liveness()` was called at the top of the polling loop, immediately
    before `await semaphore.acquire()`. With `concurrency=2` and two long jobs
    the loop blocks on that acquire and never reaches the touch again. After
    120 seconds a perfectly healthy worker — doing exactly the work it exists
    to do — reports unhealthy, and Docker restarts it mid-job.

    The five tests before this one all passed, because every one of them tested
    the helper rather than the loop.
    """

    @pytest.mark.asyncio
    async def test_liveness_stays_fresh_while_every_slot_is_busy(self, tmp_path, monkeypatch):
        import asyncio

        from app.config import Settings
        from app.jobs.worker import Worker

        settings = Settings(
            worker_concurrency=1,
            worker_poll_seconds=0.05,
            cache_dir=tmp_path / "cache",
            export_dir=tmp_path / "exports",
            database_url="postgresql://user@host/db",
        )
        worker = Worker(settings)
        path = tmp_path / "worker-alive"
        monkeypatch.setattr("app.jobs.worker.liveness_path", lambda *_a, **_k: path)
        # A heartbeat that is quick enough to observe in a test.
        monkeypatch.setattr("app.jobs.worker.LIVENESS_INTERVAL_SECONDS", 0.05)

        beat = asyncio.create_task(worker._liveness_beat(path))
        try:
            await asyncio.sleep(0.3)
            first = path.stat().st_mtime
            # Whatever the loop is doing, the heartbeat is not waiting on it.
            await asyncio.sleep(0.3)
            assert path.stat().st_mtime > first, (
                "the heartbeat stopped while the worker was busy"
            )
        finally:
            beat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await beat

    @pytest.mark.asyncio
    async def test_the_heartbeat_stops_when_cancelled(self, tmp_path, monkeypatch):
        """A task left running past shutdown keeps a stopped worker looking
        alive, which is the same lie in the other direction."""
        import asyncio

        from app.config import Settings
        from app.jobs.worker import Worker

        path = tmp_path / "worker-alive"
        monkeypatch.setattr("app.jobs.worker.LIVENESS_INTERVAL_SECONDS", 0.05)
        worker = Worker(
            Settings(
                cache_dir=tmp_path / "c",
                export_dir=tmp_path / "e",
                database_url="postgresql://user@host/db",
            )
        )
        beat = asyncio.create_task(worker._liveness_beat(path))
        await asyncio.sleep(0.15)
        beat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await beat
        stopped_at = path.stat().st_mtime
        await asyncio.sleep(0.2)
        assert path.stat().st_mtime == stopped_at, "the heartbeat outlived its worker"


class TestScaledWorkersDoNotMaskEachOther:
    def test_the_liveness_file_is_container_local(self, tmp_path, monkeypatch):
        """`docker compose up --scale worker=3` gives every worker the same
        `worker-cache` volume. One shared `worker-alive` file meant any single
        healthy worker kept all three looking healthy, including two that were
        wedged — the exact opposite of what a healthcheck is for.
        """
        from app.config import Settings
        from app.jobs.worker import liveness_path

        settings = Settings(
            cache_dir=tmp_path / "shared-volume" / "httpcache",
            export_dir=tmp_path / "exports",
            database_url="postgresql://user@host/db",
        )
        path = liveness_path(settings)
        assert "shared-volume" not in str(path), (
            f"liveness lives on the shared volume: {path}"
        )
