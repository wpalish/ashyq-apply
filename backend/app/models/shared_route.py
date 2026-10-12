"""Owned immutable personal planning receipts, without copied research evidence."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedBase, utcnow

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfileRow


class SharedRouteCurrentRow(Base):
    __tablename__ = "shared_route_current"
    __table_args__ = (
        CheckConstraint("revision > 0", name="ck_shared_route_current_revision"),
        CheckConstraint(
            "schema_version = 'shared-route-v1'", name="ck_shared_route_current_schema"
        ),
    )

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(32), default="shared-route-v1", nullable=False
    )
    snapshot: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="shared_route_current")


class SharedRouteHistoryRow(TimestampedBase):
    __tablename__ = "shared_route_history"
    __table_args__ = (
        UniqueConstraint("profile_id", "revision", name="uq_shared_route_history_profile_revision"),
        UniqueConstraint(
            "profile_id", "client_write_uuid", name="uq_shared_route_history_profile_uuid"
        ),
        CheckConstraint("revision > 0", name="ck_shared_route_history_revision"),
        Index("ix_shared_route_history_profile_accepted", "profile_id", "accepted_at"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    client_write_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="applicant_confirmed")
    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="shared_route_history")
