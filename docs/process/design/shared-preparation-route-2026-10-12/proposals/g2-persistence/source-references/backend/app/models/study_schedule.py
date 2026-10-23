"""One applicant-owned active preparation calendar, separate from official scores."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfileRow


class StudyScheduleRow(TimestampedBase):
    __tablename__ = "study_schedules"
    __table_args__ = (CheckConstraint("revision > 0", name="ck_study_schedules_revision"),)

    profile_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False)
    learning_path: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="study_schedules")
