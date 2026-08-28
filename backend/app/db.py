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


class SchemaOutOfDate(RuntimeError):
    """The database predates the current models."""


def init_db() -> None:
    """Create the schema and stamp its version.

    ``create_all`` creates missing *tables*; it never alters an existing one.
    A database created before a column was added therefore stays broken until
    it is migrated, and the failure surfaces as a 500 on an unrelated request.
    Until Alembic lands this check turns that into an explicit startup error
    naming the missing columns and how to recover.
    """
    import app.models  # noqa: F401  (registers every mapper)

    Base.metadata.create_all(engine)
    _assert_schema_matches_models()
    from app.models.meta import CURRENT_SCHEMA_VERSION, SchemaVersion

    with session_scope() as s:
        row = s.query(SchemaVersion).first()
        if row is None:
            s.add(SchemaVersion(version=CURRENT_SCHEMA_VERSION))


def _assert_schema_matches_models() -> None:
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(engine)
    missing: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        present = {c["name"] for c in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in present:
                missing.append(f"{table_name}.{column.name}")

    if missing:
        raise SchemaOutOfDate(
            "The database is missing columns the models define: "
            + ", ".join(sorted(missing))
            + ". create_all() cannot add columns to an existing table. "
            "Run the migrations, or for a local development database delete "
            "backend/data/unimatch.db and start again."
        )


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
