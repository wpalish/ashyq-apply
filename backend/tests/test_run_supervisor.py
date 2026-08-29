"""`run.sh --with-worker` must not leave a worker behind.

The old script set an EXIT trap to kill the worker and then called `exec
uvicorn`. `exec` replaces the shell with uvicorn, so the shell that owned the
trap no longer exists and the trap can never run. Every API shutdown orphaned
its worker to PPID 1.

This is not theoretical. A worker started at 11:56 was still running six and a
half hours later, consuming jobs from the shared development database with the
model definitions it had loaded at startup. It took three `documents` jobs
produced by the newer API and failed each of them three times with
`ValidationError: scholarships.0.restriction_logic — Extra inputs are not
permitted`, then buried them in the dead-letter state. A user's research simply
stopped, and nothing in the API said why.

These tests drive the real script and assert on real process tables.
"""
from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
RUN_SH = BACKEND / "run.sh"
START_TIMEOUT = 90.0
STOP_TIMEOUT = 30.0


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _worker_children(session: int) -> list[int]:
    """Worker PIDs in the supervisor's process group, from the real table.

    Matched by process *group*, not by parent. An orphaned process is
    reparented to init, so a parent-based search stops seeing exactly the
    process this suite exists to catch — the first version of these tests
    passed for that reason, which is worse than failing. The group survives
    reparenting.

    `start_new_session=True` gives each supervisor its own group, so a
    developer's own worker is never matched, let alone signalled.
    """
    out = subprocess.run(
        ["ps", "-Ao", "pid=,pgid=,command="], capture_output=True, text=True
    ).stdout
    found = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, pgid, command = parts
        if "app.jobs.worker" in command and pgid.isdigit() and int(pgid) == session:
            found.append(int(pid))
    return found


def _await(predicate, timeout: float, what: str):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError(f"timed out after {timeout}s waiting for {what}")


def _env(tmp_path: Path, port: int) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        UNIMATCH_DATABASE_URL=f"sqlite:///{tmp_path / 'supervisor.sqlite3'}",
        UNIMATCH_DEMO_MODE="true",
        PORT=str(port),
        PATH=os.environ.get("PATH", ""),
    )
    env.pop("UNIMATCH_AUTO_MIGRATE", None)
    return env


def _start(tmp_path: Path, port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [str(RUN_SH), "--with-worker"],
        cwd=str(BACKEND),
        env=_env(tmp_path, port),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.send_signal(signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)


@pytest.mark.slow
@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
def test_the_worker_dies_with_the_supervisor(tmp_path, sig):
    port = _free_port()
    proc = _start(tmp_path, port)
    try:
        workers = _await(
            lambda: _worker_children(proc.pid), START_TIMEOUT, "the worker to start"
        )
        proc.send_signal(sig)
        proc.wait(timeout=STOP_TIMEOUT)
        _await(
            lambda: all(not _alive(pid) for pid in workers),
            STOP_TIMEOUT,
            f"the worker to exit after {sig.name}",
        )
    finally:
        _stop(proc)
        for pid in _worker_children(proc.pid):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.slow
def test_no_worker_is_left_when_the_api_cannot_start(tmp_path):
    """The port is already taken, so uvicorn exits almost immediately.

    Under the old script the worker had already been started by then and was
    orphaned by a shell that no longer existed. Failing to start is exactly
    when cleanup matters most, because nobody is watching.
    """
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    port = int(holder.getsockname()[1])
    proc = _start(tmp_path, port)
    try:
        # Capture the worker before the API gives up, so the assertion is
        # about a process that really existed rather than about an empty list.
        seen: list[int] = []
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            seen = _worker_children(proc.pid) or seen
            if proc.poll() is not None and seen:
                break
            time.sleep(0.1)
        assert proc.poll() is not None, "the supervisor never exited"
        assert proc.returncode != 0, "the API should have failed to bind"
        assert seen, "no worker was ever started, so this proves nothing"
        _await(
            lambda: all(not _alive(pid) for pid in seen),
            STOP_TIMEOUT,
            "the worker to be cleaned up after the API failed to start",
        )
    finally:
        holder.close()
        _stop(proc)
        for pid in _worker_children(proc.pid):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.slow
def test_the_supervisor_reports_a_clean_exit_code(tmp_path):
    port = _free_port()
    proc = _start(tmp_path, port)
    try:
        _await(lambda: _worker_children(proc.pid), START_TIMEOUT, "the worker to start")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=STOP_TIMEOUT)
        # A signalled shutdown is not a crash. 143 is SIGTERM's conventional
        # code; 0 is acceptable for a supervisor that treats it as requested.
        assert proc.returncode in (0, 143), proc.returncode
    finally:
        _stop(proc)


if __name__ == "__main__":  # pragma: no cover - manual probe
    sys.exit(pytest.main([__file__, "-x", "-q"]))
