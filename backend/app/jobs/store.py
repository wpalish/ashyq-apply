"""The durable job store.

Claiming uses ``SELECT … FOR UPDATE SKIP LOCKED`` on PostgreSQL: two workers
racing for the same job cannot both win, and neither blocks the other. SQLite
has no such clause and needs none — it serialises writers — so the same query
runs there without it.

Everything a broker gives you is here: leases, heartbeats, retry with backoff,
idempotency, cancellation, dead-lettering and reaping. The surface is
deliberately broker-shaped so swapping in Redis later replaces this file and
nothing else. See docs/adr/0001-durable-job-queue.md.
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TERMINAL_STATUSES, Job, JobStatus
from app.models.base import ensure_utc, new_id

log = logging.getLogger("unimatch.jobs")

#: How long a claim is held before the reaper may take it back. Long enough to
#: cover one slow page fetch with its retries and backoff; short enough that a
#: dead worker is noticed quickly.
DEFAULT_LEASE_SECONDS = 120
#: Retry delays. Beyond the last entry the final value repeats.
BACKOFF_SECONDS = (30, 120, 600)


def worker_identity() -> str:
    """Host and pid. Enough to tell two workers apart and to read in a log."""
    return f"{socket.gethostname()}:{os.getpid()}"


def backoff_for(attempt: int) -> timedelta:
    index = min(max(attempt - 1, 0), len(BACKOFF_SECONDS) - 1)
    return timedelta(seconds=BACKOFF_SECONDS[index])


@dataclass(frozen=True)
class EnqueueResult:
    job_id: str
    created: bool
    reason: str = ""


class JobStore:
    """Transactional job operations. The caller owns the session and commits."""

    def __init__(self, session: Session, *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> None:
        self.session = session
        self.lease_seconds = lease_seconds

    # --- producing -------------------------------------------------------

    def enqueue(
        self,
        kind: str,
        *,
        payload: dict | None = None,
        run_id: str | None = None,
        idempotency_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
        available_at: datetime | None = None,
        queue: str = "default",
    ) -> EnqueueResult:
        """Add a job, or return the existing one for this idempotency key.

        Two paths guard against duplicates: a pre-check for the common case, and
        the unique constraint for the race. Relying on the pre-check alone would
        let two concurrent requests both create a run.
        """
        if idempotency_key:
            existing = self.session.scalar(
                select(Job).where(Job.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return EnqueueResult(existing.id, False, "an identical job already exists")

        job = Job(
            id=new_id(),
            kind=kind,
            queue=queue,
            run_id=run_id,
            idempotency_key=idempotency_key,
            status=JobStatus.QUEUED.value,
            priority=priority,
            max_attempts=max_attempts,
            available_at=available_at or datetime.now(UTC),
            payload=payload or {},
        )
        self.session.add(job)
        try:
            self.session.flush()
        except IntegrityError:
            # Lost the race on the unique key; the winner's job is the answer.
            self.session.rollback()
            existing = self.session.scalar(
                select(Job).where(Job.idempotency_key == idempotency_key)
            )
            if existing is None:
                raise
            return EnqueueResult(existing.id, False, "an identical job was enqueued concurrently")
        return EnqueueResult(job.id, True)

    # --- consuming --------------------------------------------------------

    def claim(self, *, worker_id: str | None = None, queue: str = "default") -> Job | None:
        """Take the next ready job, or None.

        The row is locked and updated in one statement. On PostgreSQL
        SKIP LOCKED lets a second worker step over a row another is claiming
        instead of waiting behind it.
        """
        worker = worker_id or worker_identity()
        now = datetime.now(UTC)
        dialect = self.session.get_bind().dialect.name

        skip_locked = "FOR UPDATE SKIP LOCKED" if dialect == "postgresql" else ""
        candidate_id = self.session.execute(
            text(
                f"""
                SELECT id FROM jobs
                WHERE status = :queued AND queue = :queue AND available_at <= :now
                ORDER BY priority DESC, available_at ASC
                LIMIT 1
                {skip_locked}
                """
            ),
            {"queued": JobStatus.QUEUED.value, "queue": queue, "now": now},
        ).scalar()

        if candidate_id is None:
            return None

        claimed = self.session.execute(
            update(Job)
            .where(Job.id == candidate_id, Job.status == JobStatus.QUEUED.value)
            .values(
                status=JobStatus.RUNNING.value,
                worker_id=worker,
                attempts=Job.attempts + 1,
                started_at=now,
                heartbeat_at=now,
                lease_expires_at=now + timedelta(seconds=self.lease_seconds),
            )
            .returning(Job.id)
        ).scalar()

        if claimed is None:
            # Another worker took it between the select and the update. Not an
            # error: the caller simply asks again.
            return None
        self.session.flush()
        return self.session.get(Job, claimed)

    def heartbeat(self, job_id: str) -> bool:
        """Extend the lease. False if the job is no longer ours to extend."""
        now = datetime.now(UTC)
        updated = self.session.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.RUNNING.value)
            .values(heartbeat_at=now, lease_expires_at=now + timedelta(seconds=self.lease_seconds))
            .returning(Job.id)
        ).scalar()
        return updated is not None

    def complete(self, job_id: str) -> None:
        now = datetime.now(UTC)
        self.session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.SUCCEEDED.value, finished_at=now,
                lease_expires_at=None, worker_id=None, last_error="",
            )
        )

    def fail(self, job_id: str, error: str, *, retry: bool = True) -> str:
        """Record a failure. Returns the resulting status.

        A job that has used its attempts goes to ``dead`` rather than looping:
        an automatic retry that can never succeed is just a slower outage.
        """
        job = self.session.get(Job, job_id)
        if job is None:
            return JobStatus.DEAD.value
        now = datetime.now(UTC)
        exhausted = job.attempts >= job.max_attempts

        if not retry or exhausted:
            job.status = JobStatus.DEAD.value
            job.finished_at = now
        else:
            job.status = JobStatus.QUEUED.value
            job.available_at = now + backoff_for(job.attempts)
            job.finished_at = None

        job.lease_expires_at = None
        job.worker_id = None
        job.last_error = error[:4000]
        self.session.add(job)
        self.session.flush()
        return job.status

    def mark_cancelled(self, job_id: str, reason: str = "cancelled by the user") -> None:
        """Terminal status for work a person stopped deliberately."""
        job = self.session.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.CANCELLED.value
        job.finished_at = datetime.now(UTC)
        job.lease_expires_at = None
        job.worker_id = None
        job.last_error = reason[:4000]
        self.session.add(job)
        self.session.flush()

    def cancel(self, job_id: str) -> bool:
        """Request cancellation.

        A queued job is cancelled at once. A running one is flagged; the worker
        observes the flag between units of work so it stops at a consistent
        point rather than mid-stage.
        """
        job = self.session.get(Job, job_id)
        if job is None or job.status in TERMINAL_STATUSES:
            return False
        job.cancel_requested = True
        if job.status == JobStatus.QUEUED.value:
            job.status = JobStatus.CANCELLED.value
            job.finished_at = datetime.now(UTC)
        self.session.add(job)
        self.session.flush()
        return True

    def is_cancel_requested(self, job_id: str) -> bool:
        return bool(self.session.execute(
            select(Job.cancel_requested).where(Job.id == job_id)
        ).scalar())

    # --- recovery ---------------------------------------------------------

    def reap_expired(self, *, now: datetime | None = None) -> list[str]:
        """Return jobs whose worker stopped beating to the queue.

        This is what makes a crash recoverable: the job is not lost, and it is
        not left claiming to run. Attempts are already counted by the claim, so
        a job that keeps killing its worker still reaches ``dead``.
        """
        now = now or datetime.now(UTC)
        expired = list(self.session.scalars(
            select(Job).where(
                Job.status == JobStatus.RUNNING.value,
                Job.lease_expires_at.is_not(None),
                Job.lease_expires_at < now,
            )
        ))
        reaped: list[str] = []
        for job in expired:
            expiry = ensure_utc(job.lease_expires_at)
            expired_at = expiry.isoformat() if expiry else "unknown"
            note = (
                f"The worker holding this job ({job.worker_id or 'unknown'}) stopped without "
                f"finishing. Lease expired at {expired_at}."
            )
            if job.attempts >= job.max_attempts:
                job.status = JobStatus.DEAD.value
                job.finished_at = now
            else:
                job.status = JobStatus.QUEUED.value
                job.available_at = now + backoff_for(job.attempts)
            job.worker_id = None
            job.lease_expires_at = None
            job.last_error = note
            self.session.add(job)
            reaped.append(job.id)
        if reaped:
            log.warning("reaped %d job(s) with expired leases", len(reaped))
        self.session.flush()
        return reaped

    # --- reading ----------------------------------------------------------

    def get(self, job_id: str) -> Job | None:
        return self.session.get(Job, job_id)

    def for_run(self, run_id: str) -> list[Job]:
        return list(self.session.scalars(
            select(Job).where(Job.run_id == run_id).order_by(Job.created_at.desc())
        ))

    def counts(self) -> dict[str, int]:
        rows = self.session.execute(
            text("SELECT status, COUNT(*) FROM jobs GROUP BY status")
        ).all()
        return dict(rows)  # type: ignore[arg-type]
