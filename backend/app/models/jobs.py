"""Durable jobs.

A job's row and the work it produced are written in one transaction, so a crash
can never leave a job marked finished with its results missing. See
docs/adr/0001-durable-job-queue.md for why this lives in PostgreSQL rather than
in a broker.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    #: Failed but retryable: it will be picked up again after its backoff.
    FAILED = "failed"
    #: Attempts exhausted. Requires a human decision; never retried automatically.
    DEAD = "dead"
    CANCELLED = "cancelled"


#: Statuses from which no further work happens without a new decision.
TERMINAL_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.DEAD, JobStatus.CANCELLED})


class Job(TimestampedBase):
    __tablename__ = "jobs"
    __table_args__ = (
        # The claim query's access path: ready work, best priority first.
        Index("ix_jobs_claimable", "status", "available_at", "priority"),
        # The reaper's access path: running work whose lease has expired.
        Index("ix_jobs_lease", "status", "lease_expires_at"),
        Index("ix_jobs_run", "run_id"),
    )

    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    queue: Mapped[str] = mapped_column(String(40), default="default", nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    #: Enqueueing the same key twice is a no-op. This is what stops a double
    #: click, a retried HTTP request or a restarted scheduler creating two runs.
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)

    status: Mapped[str] = mapped_column(String(20), default=JobStatus.QUEUED.value, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    #: Not claimable before this moment. Backoff is expressed by moving it.
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: A claimed job is held until here. Past it, the reaper takes it back.
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    #: Set by cancel(); the running worker observes it between units of work so
    #: cancellation lands at a consistent point instead of tearing a stage.
    cancel_requested: Mapped[bool] = mapped_column(default=False, nullable=False)

    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_error: Mapped[str] = mapped_column(Text, default="", nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Job {self.kind} {self.status} attempt {self.attempts}/{self.max_attempts}>"
