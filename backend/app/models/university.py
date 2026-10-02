"""Public institution identity and immutable imported observations.

Seed observations never become applicant Claims. The existing source-page and
claim histories remain the authority for programme decisions.
"""

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class University(TimestampedBase):
    __tablename__ = "universities"

    identity_key: Mapped[str] = mapped_column(String(400), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    country: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str] = mapped_column(String(200), default="")
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    domain: Mapped[str | None] = mapped_column(String(253), nullable=True)
    domain_status: Mapped[str] = mapped_column(String(40), default="unknown")
    # Only the existing curated registry may populate this field.
    registry_entry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Points to the most recently imported seed, without deleting its history.
    seed_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seed_version: Mapped[str | None] = mapped_column(String(80), nullable=True)


class UniversityObservation(TimestampedBase):
    __tablename__ = "university_observations"
    __table_args__ = (UniqueConstraint("university_id", "fingerprint"),)

    university_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("universities.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    seed_version: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
