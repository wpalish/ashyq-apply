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

import json
import logging
import os
import secrets
import socket
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.jobs.versioning import (
    BUILD_VERSION,
    PAYLOAD_SCHEMA_VERSION,
    SUPPORTED_PAYLOAD_SCHEMA_VERSIONS,
    incompatibility,
)
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
            payload_schema_version=PAYLOAD_SCHEMA_VERSION,
            producer_version=BUILD_VERSION,
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

    def claim(
        self,
        *,
        worker_id: str | None = None,
        queue: str = "default",
        supported_versions: Iterable[int] | None = None,
    ) -> Job | None:
        """Take the next ready job, or None.

        The row is locked and updated in one statement. On PostgreSQL
        SKIP LOCKED lets a second worker step over a row another is claiming
        instead of waiting behind it.
        """
        worker = worker_id or worker_identity()
        now = datetime.now(UTC)
        dialect = self.session.get_bind().dialect.name

        skip_locked = "FOR UPDATE SKIP LOCKED" if dialect == "postgresql" else ""
        # Payloads this build cannot read are excluded here, before the claim.
        #
        # Checking after claiming was not enough: claiming is what increments
        # `attempts`, so refusing the work still spent one of the job's three,
        # and after three refusals it would be `dead` — needing a person for
        # something a deployment resolves. The applicant is told "nothing has
        # been charged against your attempts", and this is what makes that
        # true.
        # `is None` rather than a falsy check. An empty set is a caller saying
        # "this build supports nothing" — a worker mid-rollout, or a test
        # proving refusal. `or` read that as "unspecified" and substituted the
        # default, so the one input that must claim nothing claimed everything
        # this build supports. An empty `IN ()` is also not valid SQL, so the
        # bug hid behind the fallback that caused it.
        if supported_versions is None:
            supported = sorted(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS)
        else:
            supported = sorted(set(supported_versions))
            if not supported:
                return None
        placeholders = ", ".join(f":v{i}" for i in range(len(supported)))
        candidate_id = self.session.execute(
            text(
                f"""
                SELECT id FROM jobs
                WHERE status = :queued AND queue = :queue AND available_at <= :now
                  AND payload_schema_version IN ({placeholders})
                ORDER BY priority DESC, available_at ASC
                LIMIT 1
                {skip_locked}
                """
            ),
            {
                "queued": JobStatus.QUEUED.value,
                "queue": queue,
                "now": now,
                **{f"v{i}": v for i, v in enumerate(supported)},
            },
        ).scalar()

        if candidate_id is None:
            return None

        claimed = self.session.execute(
            update(Job)
            .where(Job.id == candidate_id, Job.status == JobStatus.QUEUED.value)
            .values(
                status=JobStatus.RUNNING.value,
                worker_id=worker,
                # A fresh token per claim. Every subsequent write to this job
                # must present it, so a worker that stalled past its lease
                # cannot act on a run that is no longer its own.
                lease_token=secrets.token_hex(16),
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

    def heartbeat(self, job_id: str, *, lease_token: str) -> bool:
        """Extend the lease. False when the job is no longer ours to extend.

        That sentence used to be untrue of the query beneath it: it matched job
        id and RUNNING status alone, so a stalled worker could extend a lease
        another worker now held. The token is what makes it true.

        An empty token matches nothing, deliberately: treating it as a wildcard
        would restore the original bug in a shape nobody would notice.
        """
        if not lease_token:
            return False
        now = datetime.now(UTC)
        updated = self.session.execute(
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.RUNNING.value,
                Job.lease_token == lease_token,
            )
            .values(heartbeat_at=now, lease_expires_at=now + timedelta(seconds=self.lease_seconds))
            .returning(Job.id)
        ).scalar()
        return updated is not None

    def complete(self, job_id: str, *, lease_token: str) -> bool:
        """Mark the job done. False when this holder no longer owns it.

        Returns a result rather than nothing: a worker that has lost its lease
        needs to know that its completion did not land, and silently doing
        nothing is how it would carry on believing otherwise.
        """
        if not lease_token:
            return False
        now = datetime.now(UTC)
        updated = self.session.execute(
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == JobStatus.RUNNING.value,
                Job.lease_token == lease_token,
            )
            .values(
                status=JobStatus.SUCCEEDED.value, finished_at=now,
                lease_expires_at=None, worker_id=None, last_error="",
                lease_token=None,
            )
            .returning(Job.id)
        ).scalar()
        return updated is not None

    def park_incompatible(self, job_id: str, payload_schema_version: int) -> str:
        """Set a job aside because this build cannot read its payload.

        Deliberately not `fail()`. Failing spends an attempt, and three
        attempts against a payload the worker will never understand ends in
        `dead`, which means a person has to intervene. That is exactly what
        happened to three real `documents` jobs, and from the applicant's side
        their research simply stopped.

        Refusing work is not an attempt at it, so `attempts` is untouched and
        the job waits for a worker that can do it.
        """
        job = self.session.get(Job, job_id)
        if job is None:
            return JobStatus.DEAD.value
        job.status = JobStatus.BLOCKED_INCOMPATIBLE.value
        job.lease_expires_at = None
        job.worker_id = None
        job.finished_at = None
        job.last_error = json.dumps(incompatibility(payload_schema_version))[:4000]
        self.session.add(job)
        self.session.flush()
        return job.status

    def park_unsupported(self, supported: Iterable[int]) -> int:
        """Mark queued work this build cannot read, without claiming it.

        Visibility only. `claim()` already refuses these, so they would sit in
        `queued` looking ordinary while nothing ever picked them up — a stall
        with no name on it. Parking says why, and costs no attempt because
        nothing is claimed: this is an UPDATE against `queued` rows, not a
        worker taking the job.
        """
        supported_set = set(supported)
        parked = [
            job
            for job in self.session.scalars(
                select(Job).where(Job.status == JobStatus.QUEUED.value)
            )
            if job.payload_schema_version not in supported_set
        ]
        for job in parked:
            job.status = JobStatus.BLOCKED_INCOMPATIBLE.value
            job.last_error = json.dumps(
                incompatibility(job.payload_schema_version)
            )[:4000]
            self.session.add(job)
        self.session.flush()
        return len(parked)

    def release_incompatible(self, supported: Iterable[int]) -> int:
        """Re-queue parked jobs this build *can* read. Returns how many.

        Called at worker startup, so finishing a rollout is what unblocks the
        queue — no operator action, no lost work. Only touches parked jobs: a
        `dead` job still needs a human decision and must not be silently
        revived by a deployment.
        """
        parked = list(
            self.session.scalars(
                select(Job).where(Job.status == JobStatus.BLOCKED_INCOMPATIBLE.value)
            )
        )
        releasable = [j for j in parked if j.payload_schema_version in set(supported)]
        now = datetime.now(UTC)
        for job in releasable:
            job.status = JobStatus.QUEUED.value
            job.available_at = now
            job.last_error = ""
            self.session.add(job)
        self.session.flush()
        return len(releasable)

    def fail(
        self,
        job_id: str,
        error: str,
        *,
        retry: bool = True,
        lease_token: str | None = None,
    ) -> str | None:
        """Record a failure. Returns the resulting status, or None if refused.

        A job that has used its attempts goes to ``dead`` rather than looping:
        an automatic retry that can never succeed is just a slower outage.

        `lease_token` is optional for callers that hold no lease — the reaper,
        a payload refusal — and required in effect for a worker: presenting the
        wrong one returns None and writes nothing, so a stalled worker cannot
        fail work another has already finished, nor spend its attempts.
        """
        job = self.session.get(Job, job_id)
        if job is None:
            return JobStatus.DEAD.value
        if lease_token is not None and job.lease_token != lease_token:
            return None
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
        job.lease_token = None
        job.last_error = error[:4000]
        self.session.add(job)
        self.session.flush()
        return job.status

    def mark_cancelled(
        self,
        job_id: str,
        reason: str = "cancelled by the user",
        *,
        lease_token: str | None = None,
    ) -> bool:
        """Terminal status for work a person stopped deliberately.

        `lease_token` is optional because a person cancelling from the API holds
        no lease. When a *worker* calls it, it must present its token: a stalled
        worker cancelling a run another worker is midway through is the same
        split-brain write as any other.
        """
        job = self.session.get(Job, job_id)
        if job is None:
            return False
        if lease_token is not None and job.lease_token != lease_token:
            return False
        job.status = JobStatus.CANCELLED.value
        job.finished_at = datetime.now(UTC)
        job.lease_expires_at = None
        job.worker_id = None
        job.last_error = reason[:4000]
        job.lease_token = None
        self.session.add(job)
        self.session.flush()
        return True

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
            # Reaping revokes ownership. Leaving the token in place would let
            # the worker that stopped beating wake up and still match, which is
            # the whole thing the token exists to prevent.
            job.lease_token = None
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
