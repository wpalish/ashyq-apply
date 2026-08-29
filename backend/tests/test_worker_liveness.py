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

import time
from pathlib import Path

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
