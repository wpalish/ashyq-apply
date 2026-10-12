"""Profile-owned G3 aggregate and reference-only accepted events.

The future fenced writer supplies every ID, timestamp and validated JSON body.
Events have no independent clock/UUID default and no updated-at mutation hook.
Storage alone does not validate JSON/header equality or implement a G3 API.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfileRow


class AdmissionsActionsCurrentRow(Base):
    __tablename__ = "admissions_actions_current"
    __table_args__ = (
        CheckConstraint(
            "revision >= 1 AND revision <= 2147483647",
            name="ck_admissions_actions_current_revision",
        ),
        CheckConstraint(
            "schema_version = 'admissions-actions-v1'",
            name="ck_admissions_actions_current_schema",
        ),
    )

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    state_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="admissions_actions_current")


class AdmissionsActionsEventRow(Base):
    __tablename__ = "admissions_actions_events"
    __table_args__ = (
        CheckConstraint(
            "revision >= 1 AND revision <= 2147483647",
            name="ck_admissions_actions_events_revision",
        ),
        CheckConstraint(
            "schema_version = 'admissions-actions-v1'",
            name="ck_admissions_actions_events_schema",
        ),
        CheckConstraint(
            "kind IN ('create_application', 'create_personal_task', 'bind_source_task', "
            "'rebind_source_task', 'set_document_self_report', 'set_personal_details', "
            "'set_planning_status', 'declare_submission', 'declare_withdrawal', "
            "'correct_declaration', 'import_legacy_marks', 'select_active_preparation')",
            name="ck_admissions_actions_events_kind",
        ),
        UniqueConstraint(
            "profile_id", "revision", name="uq_admissions_actions_events_profile_revision"
        ),
        UniqueConstraint(
            "profile_id", "client_write_uuid", name="uq_admissions_actions_events_profile_uuid"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    client_write_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    affected_refs: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    receipt: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )

    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="admissions_actions_events")
