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


#: Both children the supervisor owns. Matching only the worker meant the API
#: was never reaped when a test killed the supervisor outright — and it cannot
#: run its trap when SIGKILLed. Three orphaned uvicorn processes on PPID 1 were
#: found this way, left by this file's own cleanup.
_CHILD_PATTERNS = ("app.jobs.worker", "uvicorn app.main")


def _children(session: int, pattern: str | None = None) -> list[int]:
    """Every child of the supervisor still alive, by process group."""
    out = subprocess.run(
        ["ps", "-Ao", "pid=,pgid=,command="], capture_output=True, text=True
    ).stdout
    found = []
    patterns = (pattern,) if pattern else _CHILD_PATTERNS
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, pgid, command = parts
        if not pgid.isdigit() or int(pgid) != session:
            continue
        if any(p in command for p in patterns):
            found.append(int(pid))
    return found


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
    """Leave nothing behind, including after a hard kill.

    A SIGKILLed supervisor cannot run its trap, so its children survive it.
    Reaping only the worker left the API running on a bound port, which is how
    a later run ends up talking to a server it did not start.
    """
    if proc.poll() is None:
        proc.send_signal(signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
    for pid in _children(proc.pid):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)


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


@pytest.mark.slow
def test_the_api_stops_before_the_worker(tmp_path):
    """Order matters, and it was backwards.

    The worker was stopped first and the API was given up to ten seconds to
    follow. In that window the API is still accepting requests and enqueueing
    jobs while the only thing that consumes them has already gone. Work
    accepted there sits until something else picks it up.

    Stop taking new work first, then drain.
    """
    port = _free_port()
    proc = _start(tmp_path, port)
    try:
        _await(lambda: _worker_children(proc.pid), START_TIMEOUT, "the worker to start")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=STOP_TIMEOUT)
        output = proc.stdout.read() if proc.stdout else ""
        api_line = output.find("stopping api")
        worker_line = output.find("stopping worker")
        assert api_line != -1 and worker_line != -1, output[-500:]
        assert api_line < worker_line, (
            "the worker was stopped before the API, leaving the API accepting "
            f"jobs nothing would consume:\n{output[-500:]}"
        )
    finally:
        _stop(proc)


@pytest.mark.slow
def test_a_child_dying_on_its_own_is_not_a_clean_exit(tmp_path):
    """A worker that exits by itself — even with status 0 — is a lost
    consumer, not a completed job.

    The supervisor returned the child's own status, so an orchestrator reading
    exit 0 would treat the disappearance of the only thing draining the queue
    as a successful shutdown and not restart it.
    """
    port = _free_port()
    proc = _start(tmp_path, port)
    try:
        workers = _await(
            lambda: _worker_children(proc.pid), START_TIMEOUT, "the worker to start"
        )
        # SIGTERM to the worker alone: it handles the signal and exits 0.
        os.kill(workers[0], signal.SIGTERM)
        proc.wait(timeout=STOP_TIMEOUT)
        assert proc.returncode not in (0, None), (
            "the supervisor reported a clean exit after losing its worker "
            f"(returncode={proc.returncode})"
        )
    finally:
        _stop(proc)
        for pid in _worker_children(proc.pid):
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)


@pytest.mark.slow
def test_nothing_survives_a_failed_run(tmp_path):
    """The cleanup in these tests SIGKILLs the supervisor, which cannot then
    take its children with it. If a failure path leaves an API behind, the next
    run binds a port it does not own — and that is how this suite started
    testing someone else's server in the first place."""
    port = _free_port()
    proc = _start(tmp_path, port)
    _await(lambda: _worker_children(proc.pid), START_TIMEOUT, "the worker")
    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=10)
    # Simulating the harness's own worst case: the supervisor is gone without
    # running its trap. Everything it started must still be reaped by the test.
    _stop(proc)
    _await(
        lambda: not _children(proc.pid),
        STOP_TIMEOUT,
        "every child — worker and API — to be gone after a hard kill",
    )
