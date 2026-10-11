"""Case-owned submitted practice. No draft essays, audio, or official score fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfileRow


class StudyAttempt(TimestampedBase):
    __tablename__ = "study_attempts"
    __table_args__ = (
        Index("uq_study_attempts_profile_client", "profile_id", "client_attempt_id", unique=True),
        Index("ix_study_attempts_profile_created", "profile_id", "created_at"),
        CheckConstraint("total > 0 AND total <= 20", name="ck_study_attempts_total"),
        CheckConstraint("correct >= 0 AND correct <= total", name="ck_study_attempts_correct"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), nullable=False
    )
    client_attempt_id: Mapped[str] = mapped_column(String(36), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String(80), nullable=False)
    content_version: Mapped[str] = mapped_column(String(40), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    answers: Mapped[list] = mapped_column(JSON, nullable=False)
    feedback: Mapped[list] = mapped_column(JSON, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    profile: Mapped[ApplicantProfileRow] = relationship(back_populates="study_attempts")
