"""Applicant storage.

The profile is stored as one JSON document rather than shredded into columns.
That is deliberate: the profile is read and written whole, it is validated by
Pydantic at the boundary, and keeping it in one place makes 'export everything'
and 'delete everything' single, auditable operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase

if TYPE_CHECKING:
    from app.models.research import ResearchRun


class ApplicantProfileRow(TimestampedBase):
    __tablename__ = "applicant_profiles"

    #: An applicant profile is the product's case boundary.  Every API query
    #: scopes through this organization id; knowing a UUID is never authority.
    #: No default on purpose. A default meant a caller that forgot the tenant
    #: silently wrote into the development organization, which is the one
    #: mistake this column exists to prevent.
    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(80), default="Applicant")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    #: Deleting an applicant must erase every run, result, claim and conflict
    #: belonging to them. That is a privacy guarantee, so the ORM issues the
    #: deletes itself rather than trusting SQLite's foreign_keys pragma to be
    #: on - a pragma is per-connection and easy to lose.
    runs: Mapped[list[ResearchRun]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=False
    )
