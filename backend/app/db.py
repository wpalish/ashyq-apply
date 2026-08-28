"""Database session management and schema versioning.

SQLite for the MVP with a PostgreSQL-compatible model layer: no SQLite-only
types are used, and JSON columns are portable. Swapping the URL is the only
change PostgreSQL needs.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.base import Base

_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    future=True,
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    """Create the schema and stamp its version."""
    import app.models  # noqa: F401  (registers every mapper)

    Base.metadata.create_all(engine)
    from app.models.meta import CURRENT_SCHEMA_VERSION, SchemaVersion

    with session_scope() as s:
        row = s.query(SchemaVersion).first()
        if row is None:
            s.add(SchemaVersion(version=CURRENT_SCHEMA_VERSION))


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
