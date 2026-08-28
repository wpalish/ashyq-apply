from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CURRENT_SCHEMA_VERSION = 1


class SchemaVersion(Base):
    """Schema version stamp.

    Alembic is configured for real migrations; this row lets the API report the
    schema it is running against without loading Alembic at request time.
    """

    __tablename__ = "schema_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(String(200), default="initial schema")
