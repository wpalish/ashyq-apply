"""Research runs, results, claims, conflicts and the audit log."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase, utcnow

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfileRow


class ResearchRun(TimestampedBase):
    """One execution of the pipeline, resumable stage by stage."""

    __tablename__ = "research_runs"

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Per-run research scope. Persisted so a retry or a restart uses the scope
    #: the user asked for, not whatever the server default happens to be.
    candidate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verify_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)

    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    programs_verified: Mapped[int] = mapped_column(Integer, default=0)
    pages_checked: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)
    claims_recorded: Mapped[int] = mapped_column(Integer, default=0)

    #: Per-stage {status, started_at, finished_at, error} so a failed stage can
    #: be retried without redoing the whole run.
    stage_state: Mapped[dict] = mapped_column(JSON, default=dict)
    #: How many pages each fetch tier produced. Proves the browser tier is
    #: actually doing work rather than merely being constructed.
    fetch_tiers: Mapped[dict] = mapped_column(JSON, default=dict)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    retry_urls: Mapped[list] = mapped_column(JSON, default=list)
    settings_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- lease, so a dead worker cannot leave a run "running" forever -----
    #: Which worker holds this run. Cleared when the run reaches a terminal state.
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    #: Refreshed as the run makes progress. A lease that stops being refreshed
    #: is how a crashed worker becomes visible.
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: How many times this run has been recovered after a worker died.
    recovery_count: Mapped[int] = mapped_column(Integer, default=0)

    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="runs")
    results: Mapped[list[ProgramResultRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=False
    )
    claims: Mapped[list[ClaimRow]] = relationship(
        cascade="all, delete-orphan", passive_deletes=False
    )
    conflicts: Mapped[list[ConflictRow]] = relationship(
        cascade="all, delete-orphan", passive_deletes=False
    )


class ProgramResultRow(TimestampedBase):
    __tablename__ = "program_results"
    __table_args__ = (
        Index("ix_results_run_decision", "run_id", "user_decision"),
        Index("ix_results_dedupe", "run_id", "dedupe_key", unique=True),
    )

    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("research_runs.id", ondelete="CASCADE"), index=True
    )
    dedupe_key: Mapped[str] = mapped_column(String(400), index=True)
    university: Mapped[str] = mapped_column(String(200))
    university_key: Mapped[str] = mapped_column(String(300), index=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    program: Mapped[str] = mapped_column(String(300))

    eligibility: Mapped[str] = mapped_column(String(40), index=True)
    admissions_fit: Mapped[str] = mapped_column(String(40), index=True)
    funding_fit: Mapped[str] = mapped_column(String(40), index=True)
    funding_classification: Mapped[str] = mapped_column(String(40), index=True)
    score_total: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    user_decision: Mapped[str] = mapped_column(String(20), default="undecided", index=True)
    user_decision_reason: Mapped[str] = mapped_column(Text, default="")
    user_notes: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: The full ProgramResult document. Kept whole so the exact shape shown to
    #: the user is what gets exported, with no re-derivation drift.
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    checklist: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped[ResearchRun] = relationship(back_populates="results")


class ClaimRow(TimestampedBase):
    """Persisted evidence. Never deleted while its run exists."""

    __tablename__ = "claims"
    __table_args__ = (Index("ix_claims_run_type", "run_id", "claim_type"),)

    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("research_runs.id", ondelete="CASCADE"), index=True
    )
    result_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    claim_type: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_specificity: Mapped[str] = mapped_column(String(40))
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class ConflictRow(TimestampedBase):
    __tablename__ = "conflicts"

    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("research_runs.id", ondelete="CASCADE"), index=True
    )
    result_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    claim_type: Mapped[str] = mapped_column(String(60))
    unresolved: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class AuditEvent(TimestampedBase):
    """Append-only trail of what the system and the user did.

    Deliberately holds no applicant data: entity ids and action names only, so
    the log can be shipped or shared without a privacy review.
    """

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    actor: Mapped[str] = mapped_column(String(20), default="system")
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
