#!/usr/bin/env python
"""Suspend a real worker mid-job, let another take the job, and wake it up.

SIGKILL is the easy case, and `crash_test.py` covers it: a dead process writes
nothing. The dangerous case is a worker that is *alive but stopped* — a long GC
pause, a suspended container, a host that swapped it out, a debugger — for
longer than its lease. Another worker reaps the job and starts running it. Then
the first one wakes up with a session, a job id, and every intention of
finishing.

Nothing in a mock can prove that does not corrupt the run, because the thing
under test is two operating-system processes holding the same row. SIGSTOP and
SIGCONT produce exactly that state, with no cooperation from the process being
stopped — it cannot handle the signal, flush anything, or notice it happened.

    python scripts/pg.py .venv/bin/python scripts/split_brain_test.py

Requires SIGSTOP/SIGCONT, so POSIX only; it exits 0 with a skip notice
elsewhere rather than pretending to have run.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

#: Short enough that a suspended worker outlives its lease inside this
#: script's patience. Production uses 120s.
LEASE_SECONDS = 4
#: How long to leave worker A suspended. Comfortably past the lease, so the
#: reaper has certainly acted before A is resumed.
SUSPEND_SECONDS = LEASE_SECONDS * 3


def env_for_worker() -> dict[str, str]:
    return {
        **os.environ,
        "UNIMATCH_JOB_LEASE_SECONDS": str(LEASE_SECONDS),
        "UNIMATCH_WORKER_POLL_SECONDS": "0.3",
        "UNIMATCH_WORKER_CONCURRENCY": "1",
        "UNIMATCH_AUTO_MIGRATE": "false",
        "UNIMATCH_LOG_LEVEL": "INFO",
        # Unbuffered, because this script reads the worker's own account of
        # what happened. Block-buffered output through a pipe arrives only at
        # exit, and a worker killed after a timeout never gets there.
        "PYTHONUNBUFFERED": "1",
    }


def start_worker() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "app.jobs.worker"],
        cwd=BACKEND, env=env_for_worker(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def wait_for(predicate, *, timeout: float, what: str):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value is not None:
            return value
        time.sleep(0.1)
    raise AssertionError(f"timed out after {timeout}s waiting for {what}")


def main() -> int:
    if not hasattr(signal, "SIGSTOP"):
        print("SKIP: SIGSTOP is not available on this platform")
        return 0

    os.environ["UNIMATCH_JOB_LEASE_SECONDS"] = str(LEASE_SECONDS)
    os.environ["UNIMATCH_AUTO_MIGRATE"] = "false"
    if not os.environ.get("UNIMATCH_DATABASE_URL"):
        scratch = Path(tempfile.mkdtemp(prefix="split-brain-"))
        os.environ["UNIMATCH_DATABASE_URL"] = f"sqlite:///{scratch / 'sb.sqlite3'}"
        print(f"using a throwaway database at {scratch}")

    from app.corpus.demo_profile import DEMO_PROFILE
    from app.db import migrate_to_head, session_scope
    from app.jobs.store import JobStore
    from app.models import (
        ApplicantProfileRow,
        Job,
        JobStatus,
        ProgramResultRow,
        ResearchRun,
    )
    from app.pipeline.state import RunState

    migrate_to_head()
    print(f"database migrated  lease={LEASE_SECONDS}s")

    with session_scope() as session:
        profile = ApplicantProfileRow(
            display_name="split-brain-test", payload=DEMO_PROFILE.model_dump(mode="json")
        )
        session.add(profile)
        session.flush()
        run = ResearchRun(
            profile_id=profile.id, stage="queued", demo_mode=True,
            candidate_limit=12, verify_limit=12, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        job_id = JobStore(session).enqueue(
            "research", run_id=run.id, idempotency_key=f"research:{run.id}"
        ).job_id
        run_id = run.id
    print(f"enqueued job {job_id[:8]} for run {run_id[:8]}")

    # --- 1. worker A claims it -------------------------------------------
    worker_a = start_worker()
    print(f"worker A pid {worker_a.pid} started")

    def claimed():
        with session_scope() as session:
            job = session.get(Job, job_id)
            if job and job.status == JobStatus.RUNNING.value and job.lease_token:
                return (job.worker_id, job.lease_token)
        return None

    a_worker_id, a_token = wait_for(claimed, timeout=60, what="worker A to claim the job")
    print(f"worker A claimed it  worker_id={a_worker_id}  token={a_token[:8]}…")

    # --- 2. suspend it, without warning -----------------------------------
    os.kill(worker_a.pid, signal.SIGSTOP)
    print(f"worker A SIGSTOPped; waiting {SUSPEND_SECONDS}s for its lease to lapse")
    time.sleep(SUSPEND_SECONDS)

    # --- 3. worker B reaps and takes over ---------------------------------
    worker_b = start_worker()
    print(f"worker B pid {worker_b.pid} started")

    def taken_over():
        with session_scope() as session:
            job = session.get(Job, job_id)
            if (
                job
                and job.status == JobStatus.RUNNING.value
                and job.lease_token
                and job.lease_token != a_token
            ):
                return (job.worker_id, job.lease_token)
        return None

    try:
        b_worker_id, b_token = wait_for(
            taken_over, timeout=90, what="worker B to reap and reclaim the job"
        )
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        os.kill(worker_a.pid, signal.SIGCONT)
        worker_a.kill()
        worker_b.kill()
        return 1
    print(f"worker B took the job  worker_id={b_worker_id}  token={b_token[:8]}…")

    # --- 4. wake A up and give it every chance to interfere ---------------
    os.kill(worker_a.pid, signal.SIGCONT)
    print("worker A SIGCONTed — it now believes it still owns the job")

    # A's heartbeat fires within a lease period. Wait out several, so if it is
    # going to write anything it has done so by now.
    time.sleep(LEASE_SECONDS * 3)

    failures: list[str] = []
    with session_scope() as session:
        job = session.get(Job, job_id)
        rows = session.query(ProgramResultRow).filter(
            ProgramResultRow.run_id == run_id
        ).all()
        keys = [r.dedupe_key for r in rows]
        duplicates = len(keys) - len(set(keys))

        if job is None:
            failures.append("the job disappeared")
        else:
            print(
                f"  job    : {job.status}  attempts={job.attempts}  "
                f"worker={job.worker_id}  token={(job.lease_token or 'none')[:8]}"
            )
            if job.lease_token == a_token:
                failures.append(
                    f"worker A's token is back on the job ({job.lease_token[:8]}…): "
                    "it wrote to a job it no longer owned"
                )
            if job.worker_id == a_worker_id:
                failures.append(
                    f"worker A ({a_worker_id}) is recorded as the holder after B "
                    "took over"
                )
            if job.attempts > 2:
                failures.append(
                    f"the job was attempted {job.attempts} times; one suspension "
                    "should cost exactly one re-claim"
                )
        print(
            f"  results: {len(rows)}  unique={len(set(keys))}  duplicates={duplicates}"
        )
        # The corruption itself. Two pipelines running one run write the same
        # programmes twice, and the applicant sees each result duplicated.
        if duplicates:
            failures.append(
                f"{duplicates} duplicate result(s): two workers ran the same run"
            )

    # Worker A's own account of what happened. The database can look tidy
    # afterwards — B's completion clears the worker id and the token — so a
    # state check alone cannot tell "A stopped" from "A finished the job and B
    # cleaned up after it". A has to say it noticed.
    for proc in (worker_a, worker_b):
        proc.terminate()
    a_output = worker_a.communicate(timeout=20)[0] or ""
    worker_b.communicate(timeout=20)
    for proc in (worker_a, worker_b):
        if proc.poll() is None:
            proc.kill()

    if "lost the lease" not in a_output:
        failures.append(
            "worker A never reported losing the lease; it was suspended past its "
            "lease and woke up believing it still owned the job:\n"
            + "\n".join(f"      A| {line}" for line in a_output.splitlines()[-15:])
        )

    if failures:
        print()
        print("\n".join(f"  FAIL: {f}" for f in failures))
        return 1

    print("  PASS: a suspended worker could not write to the job another had taken")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
