#!/usr/bin/env python
"""Kill a worker mid-run and prove the system recovers.

Not a simulation: a real worker process is started, allowed to reach the
funding-discovery stage, and killed with SIGKILL — no cleanup, no signal
handler, nothing flushed. A second worker then has to notice, recover the job
and finish it without duplicating anything.

    python scripts/pg.py .venv/bin/python scripts/crash_test.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


def must_get(session: Session, model: type[T], pk: str, what: str) -> T:
    """Fetch a row that has to exist, or say plainly that it does not.

    Every call site here reads an attribute off the result. Without this, a
    missing row raised `AttributeError: 'NoneType' object has no attribute
    'status'` — from a harness whose whole purpose is to detect a job or run
    disappearing after a crash. The failure mode the tool exists to catch was
    the one it reported worst.
    """
    row = session.get(model, pk)
    if row is None:
        raise AssertionError(f"{what} {pk} is not in the database")
    return row

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

#: Short so the reaper acts inside a test's patience. Production uses 120s.
LEASE_SECONDS = 5
#: Kill only once results have been written. Killing earlier is the easy case:
#: the retry starts from nothing and cannot collide. The interesting case is a
#: retry that meets the rows the first attempt already stored.
STAGE_TO_KILL_IN = ("funding_discovery", "assessment")
MIN_RESULTS_BEFORE_KILL = 1


def env_for_worker() -> dict[str, str]:
    return {
        **os.environ,
        "UNIMATCH_JOB_LEASE_SECONDS": str(LEASE_SECONDS),
        "UNIMATCH_WORKER_POLL_SECONDS": "0.3",
        "UNIMATCH_AUTO_MIGRATE": "false",
        "UNIMATCH_LOG_LEVEL": "WARNING",
    }


def start_worker() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "app.jobs.worker"],
        cwd=BACKEND, env=env_for_worker(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def main() -> int:
    os.environ["UNIMATCH_JOB_LEASE_SECONDS"] = str(LEASE_SECONDS)
    os.environ["UNIMATCH_AUTO_MIGRATE"] = "false"
    # A throwaway database. This wrote into the project's working database,
    # which is the one the dev server and the E2E suite use: eight runs of this
    # script left eight "crash-test" applicants and their results behind, and a
    # test harness must not leave anything in the data a person is using.
    # Honoured if the caller set one explicitly, so CI can point it at
    # PostgreSQL.
    if not os.environ.get("UNIMATCH_DATABASE_URL"):
        scratch = Path(tempfile.mkdtemp(prefix="crash-test-"))
        os.environ["UNIMATCH_DATABASE_URL"] = f"sqlite:///{scratch / 'crash.sqlite3'}"
        print(f"using a throwaway database at {scratch}")

    from app.corpus.demo_profile import DEMO_PROFILE
    from app.db import migrate_to_head, session_scope
    from app.jobs.store import JobStore
    from app.models import ApplicantProfileRow, Job, ProgramResultRow, ResearchRun
    from app.pipeline.state import RunState

    migrate_to_head()
    print(f"database migrated  lease={LEASE_SECONDS}s")

    with session_scope() as session:
        profile = ApplicantProfileRow(
            display_name="crash-test", payload=DEMO_PROFILE.model_dump(mode="json")
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

    # --- 1. start a worker and let it get into the pipeline ---------------
    worker = start_worker()
    print(f"worker A pid {worker.pid} started")

    reached = None
    written = 0
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        with session_scope() as session:
            stage = must_get(session, ResearchRun, run_id, "run").stage
            written = session.query(ProgramResultRow).filter(
                ProgramResultRow.run_id == run_id
            ).count()
        if stage in STAGE_TO_KILL_IN and written >= MIN_RESULTS_BEFORE_KILL:
            reached = stage
            break
        if stage in ("awaiting_user_decision", "completed"):
            print(f"FAIL: the run finished before it could be interrupted (stage={stage})")
            worker.kill()
            return 1
        time.sleep(0.1)

    if reached is None:
        print("FAIL: the run never reached a stage worth interrupting")
        worker.kill()
        return 1

    # --- 2. kill it outright ------------------------------------------------
    os.kill(worker.pid, signal.SIGKILL)
    worker.wait(timeout=10)
    print(f"worker A SIGKILLed during {reached}, with {written} results already written")

    with session_scope() as session:
        job = must_get(session, Job, job_id, "job")
        run = must_get(session, ResearchRun, run_id, "run")
        results_before = session.query(ProgramResultRow).filter(
            ProgramResultRow.run_id == run_id
        ).count()
        print(f"  immediately after: job={job.status} worker={job.worker_id} "
              f"run={run.stage} results={results_before}")
        assert job.status == "running", "the job should still look claimed"

    # --- 3. a new worker must notice and recover ---------------------------
    time.sleep(LEASE_SECONDS + 1)

    # The kill races the run: worker A can finish between the moment we decide
    # to kill it and the moment the signal lands. When that happens there is
    # nothing to recover and the job legitimately ends on attempt 1, which is
    # not a recovery failure and must not be reported as one. Attempts are
    # incremented on claim, so a genuinely recovered job always reaches 2.
    with session_scope() as session:
        job = must_get(session, Job, job_id, "job")
        if job.status in ("succeeded", "completed"):
            print()
            print("  INCONCLUSIVE: the kill landed after worker A had already "
                  "finished the job, so there was nothing to recover.")
            print("  This is a race in this script, not a product failure. Re-run it.")
            return 2

    recovery = start_worker()
    print(f"worker B pid {recovery.pid} started after the lease expired")

    deadline = time.monotonic() + 120
    final_job = None
    while time.monotonic() < deadline:
        with session_scope() as session:
            job = must_get(session, Job, job_id, "job")
            run = must_get(session, ResearchRun, run_id, "run")
            if job.status in ("succeeded", "dead", "cancelled"):
                final_job = job.status
                break
        time.sleep(0.3)

    recovery.terminate()
    try:
        recovery.wait(timeout=15)
    except subprocess.TimeoutExpired:
        recovery.kill()

    if final_job is None:
        print("FAIL: the job never reached a terminal state")
        output = (recovery.stdout.read() if recovery.stdout else "") or "(no output)"
        print("  worker B said:", output[-1500:])
        return 1

    # --- 4. what does the world look like now? ------------------------------
    with session_scope() as session:
        job = must_get(session, Job, job_id, "job")
        run = must_get(session, ResearchRun, run_id, "run")
        rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).all()
        keys = [r.dedupe_key for r in rows]

        print()
        print(f"  job    : {job.status}  attempts={job.attempts}/{job.max_attempts}  worker={job.worker_id}")
        print(f"  run    : {run.stage}  recovery_count={run.recovery_count}")
        print(f"  results: {len(rows)}  unique={len(set(keys))}  duplicates={len(keys) - len(set(keys))}")
        print(f"  claims : {run.claims_recorded}")

        problems = []
        if job.status != "succeeded":
            problems.append(f"job ended {job.status}, expected succeeded")
        if job.attempts < 2:
            problems.append(
                "the job was not re-attempted after the crash: attempts stayed at "
                f"{job.attempts}, and a claim always increments it"
            )
        if run.stage not in ("awaiting_user_decision", "completed"):
            problems.append(f"run ended at {run.stage}, not a decision point")
        if len(keys) != len(set(keys)):
            problems.append("duplicate results were produced by the retry")
        if job.worker_id is not None:
            problems.append("the lease was not released")
        if len(rows) < written:
            problems.append(
                f"the retry lost results: {written} existed before the crash, {len(rows)} after"
            )

    print()
    if problems:
        for problem in problems:
            print(f"  FAIL: {problem}")
        return 1
    print("  PASS: recovered after SIGKILL, re-attempted, finished, no duplicates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
