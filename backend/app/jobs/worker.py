"""The worker.

Claims a job, runs it, and beats while it does. Every exit path is accounted
for: success completes the job, a failure retries it with backoff until its
attempts run out, a cancellation stops it at a consistent point, and a crash
leaves a lease that another worker's reaper takes back.

Runs as its own process, separate from the API. `python -m app.jobs.worker`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys

from app.config import Settings, get_settings
from app.db import session_scope
from app.domain.enums import PipelineStage
from app.jobs.store import JobStore, worker_identity
from app.models import ApplicantProfileRow, AuditEvent, Job, JobStatus, ResearchRun
from app.pipeline.runner import ResearchRunner, RunCancelled
from app.schemas.profile import ApplicantProfileIn

log = logging.getLogger("unimatch.worker")

#: Beat at a third of the lease so two beats can be missed before it expires.
HEARTBEAT_DIVISOR = 3


class Worker:
    def __init__(self, settings: Settings | None = None, *, worker_id: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.worker_id = worker_id or worker_identity()
        self.stopping = asyncio.Event()
        self.jobs_done = 0
        self.jobs_failed = 0

    # --- lifecycle --------------------------------------------------------

    def request_stop(self, *_args: object) -> None:
        """Finish the job in hand, then exit. No work is abandoned mid-stage."""
        if not self.stopping.is_set():
            log.info("shutdown requested; finishing the current job first")
            self.stopping.set()

    async def run_forever(self) -> None:
        log.info("worker %s starting (concurrency %d)", self.worker_id, self.settings.worker_concurrency)
        self.reap()
        semaphore = asyncio.Semaphore(self.settings.worker_concurrency)
        running: set[asyncio.Task] = set()

        while not self.stopping.is_set():
            await semaphore.acquire()
            job_id = self.claim_one()
            if job_id is None:
                semaphore.release()
                # Wake early if a stop is requested; otherwise poll on schedule.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self.stopping.wait(), timeout=self.settings.worker_poll_seconds
                    )
                self.reap()
                continue

            task = asyncio.create_task(self._run_and_release(job_id, semaphore))
            running.add(task)
            task.add_done_callback(running.discard)

        if running:
            log.info("waiting for %d job(s) to finish", len(running))
            await asyncio.gather(*running, return_exceptions=True)
        log.info("worker %s stopped (%d done, %d failed)", self.worker_id, self.jobs_done, self.jobs_failed)

    async def _run_and_release(self, job_id: str, semaphore: asyncio.Semaphore) -> None:
        try:
            await self.execute(job_id)
        finally:
            semaphore.release()

    # --- queue operations -------------------------------------------------

    def reap(self) -> list[str]:
        """Take back jobs whose worker stopped beating."""
        with session_scope() as session:
            return JobStore(session, lease_seconds=self.settings.job_lease_seconds).reap_expired()

    def claim_one(self) -> str | None:
        with session_scope() as session:
            store = JobStore(session, lease_seconds=self.settings.job_lease_seconds)
            job = store.claim(worker_id=self.worker_id)
            return job.id if job else None

    # --- execution --------------------------------------------------------

    async def execute(self, job_id: str) -> None:
        """Run one job to a terminal state."""
        heartbeat = asyncio.create_task(self._beat(job_id))
        try:
            with session_scope() as session:
                store = JobStore(session, lease_seconds=self.settings.job_lease_seconds)
                job = store.get(job_id)
                if job is None:
                    return
                log.info("running job %s (%s) attempt %d", job.id[:8], job.kind, job.attempts)
                await self._dispatch(session, store, job)
            self.jobs_done += 1
        except RunCancelled as exc:
            with session_scope() as session:
                JobStore(session).mark_cancelled(job_id, str(exc))
            log.info("job %s cancelled", job_id[:8])
        except Exception as exc:
            self.jobs_failed += 1
            log.exception("job %s failed", job_id[:8])
            with session_scope() as session:
                status = JobStore(session).fail(job_id, f"{type(exc).__name__}: {exc}")
            log.info("job %s -> %s", job_id[:8], status)
        finally:
            heartbeat.cancel()

    async def _beat(self, job_id: str) -> None:
        interval = max(1.0, self.settings.job_lease_seconds / HEARTBEAT_DIVISOR)
        try:
            while True:
                await asyncio.sleep(interval)
                with session_scope() as session:
                    if not JobStore(session).heartbeat(job_id):
                        log.warning("lost the lease on job %s", job_id[:8])
                        return
        except asyncio.CancelledError:
            return

    async def _dispatch(self, session, store: JobStore, job: Job) -> None:
        """Route a job to its handler, in the job's own transaction."""
        run = session.get(ResearchRun, job.run_id) if job.run_id else None
        if run is None:
            store.fail(job.id, f"run {job.run_id} no longer exists", retry=False)
            return

        profile_row = session.get(ApplicantProfileRow, run.profile_id)
        if profile_row is None:
            store.fail(job.id, "the applicant profile was deleted", retry=False)
            return

        profile = ApplicantProfileIn.model_validate(profile_row.payload)
        runner = ResearchRunner(session, run, profile, self.settings, job_id=job.id)

        if job.kind == "documents":
            await runner.collect_documents()
        elif job.kind == "research":
            await runner.run_to_decision()
        else:
            store.fail(job.id, f"unknown job kind {job.kind!r}", retry=False)
            return

        # The job's completion and the work it produced commit together, so a
        # crash can never mark a job done with its results missing.
        store.complete(job.id)
        session.add(AuditEvent(
            actor="worker", action="job_completed", entity_type="job", entity_id=job.id,
            detail={"kind": job.kind, "stage": run.stage},
        ))


#: A worker that starts before migrations finish should wait, not die: in a
#: rolling deploy their order is not guaranteed.
SCHEMA_WAIT_SECONDS = 60


def wait_for_schema(timeout: float = SCHEMA_WAIT_SECONDS) -> bool:
    """Block until the database matches this code, or give up saying why."""
    import time

    from app.db import SchemaOutOfDate, assert_at_head

    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            assert_at_head()
            return True
        except SchemaOutOfDate as exc:
            last = exc
            log.info("waiting for the database schema to be migrated…")
            time.sleep(2)
        except Exception as exc:  # a database that is not up yet at all
            last = exc
            log.info("waiting for the database to accept connections…")
            time.sleep(2)
    log.error("giving up waiting for the schema: %s", last)
    return False


def reconcile_startup() -> dict[str, int]:
    """Put the queue and the runs back into a consistent state.

    Runs before any work is claimed: expired leases go back to the queue, and a
    run whose job is no longer live stops claiming to be running.
    """
    settings = get_settings()
    with session_scope() as session:
        store = JobStore(session, lease_seconds=settings.job_lease_seconds)
        reaped = store.reap_expired()

        stranded = 0
        live_run_ids = {
            job.run_id for job in session.query(Job).filter(
                Job.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value])
            ) if job.run_id
        }
        in_progress = session.query(ResearchRun).filter(
            ResearchRun.finished_at.is_(None),
            ResearchRun.stage.notin_([
                PipelineStage.AWAITING_USER_DECISION.value,
                PipelineStage.COMPLETED.value,
                PipelineStage.CANCELLED.value,
                PipelineStage.RETRYABLE_FAILED.value,
                PipelineStage.FAILED.value,
            ]),
        ).all()
        for run in in_progress:
            if run.id in live_run_ids:
                continue
            run.stage = PipelineStage.RETRYABLE_FAILED.value
            run.worker_id = None
            run.recovery_count = (run.recovery_count or 0) + 1
            run.errors = [
                *(run.errors or []),
                "No job is queued or running for this run. It was recovered at startup and "
                "can be retried from the last completed stage.",
            ]
            session.add(run)
            session.add(AuditEvent(
                actor="system", action="run_recovered", entity_type="run", entity_id=run.id,
                detail={"recovery_count": run.recovery_count},
            ))
            stranded += 1

        return {"jobs_reaped": len(reaped), "runs_recovered": stranded}


def main() -> int:  # pragma: no cover - process entry point
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if not wait_for_schema():
        return 1
    summary = reconcile_startup()
    log.info("startup reconciliation: %s", summary)

    worker = Worker(settings)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.request_stop)
    try:
        loop.run_until_complete(worker.run_forever())
    finally:
        loop.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
