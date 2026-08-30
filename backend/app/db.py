"""Database session management and schema versioning.

PostgreSQL is the production database; SQLite remains supported for a quick
local run. Nothing SQLite-only is used, and anything PostgreSQL-only is behind
a dialect check.

The schema is owned by Alembic. ``create_all()`` is not a migration mechanism —
it creates missing tables and silently ignores every changed column — so it is
confined to test setup and refused in production.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.base import Base

log = logging.getLogger("unimatch.db")
_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")

def ensure_database_parent(url: str) -> None:
    """Create the directory holding a SQLite file, if the URL names one.

    SQLAlchemy will not create it, and a fresh checkout has no `data/`. Doing
    it here rather than at import is what lets a process with a read-only root
    filesystem read its configuration without touching the disk.

    A no-op for every other driver: PostgreSQL has no parent directory.
    """
    if not url.startswith("sqlite:///"):
        return
    path = Path(url.removeprefix("sqlite:///"))
    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)


# Before the engine: SQLAlchemy will not create a SQLite file's directory,
# and a fresh checkout has no `data/`. A no-op for PostgreSQL, which is
# what the containers use — so this does not reintroduce a disk write on
# the read-only API path.
ensure_database_parent(_settings.database_url)

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    future=True,
)

if _is_sqlite:

    #: SQLite allows one writer at a time. With the API and a worker both
    #: writing, the loser fails immediately unless it is told to wait — which
    #: surfaced as a 500 from the API while a run was in progress. PostgreSQL
    #: does not need this; SQLite is a development convenience.
    SQLITE_BUSY_TIMEOUT_MS = 15_000

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


class SchemaOutOfDate(RuntimeError):
    """The database does not match the migrations the code expects."""


def _alembic_config(url: str):
    from alembic.config import Config

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", url)
    return config


def head_revision() -> str | None:
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(_alembic_config(_settings.database_url)).get_current_head()


def current_revision(target: Engine | None = None) -> str | None:
    target = target or engine
    with target.connect() as connection:
        if not inspect(target).has_table("alembic_version"):
            return None
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar()


def migrate_to_head(url: str | None = None) -> None:
    """Bring a database up to the newest migration."""
    from alembic import command

    command.upgrade(_alembic_config(url or _settings.database_url), "head")


def assert_at_head() -> None:
    """Refuse to serve against a database the code does not match.

    A mismatch used to surface as `table research_runs has no column named
    candidate_limit` on an unrelated request. It is a startup error now.
    """
    expected = head_revision()
    actual = current_revision()
    if actual == expected:
        return
    if actual is None:
        raise SchemaOutOfDate(
            "This database has never been migrated. Run:\n"
            "    python scripts/pg.py .venv/bin/alembic upgrade head\n"
            "or, for SQLite, `alembic upgrade head` with UNIMATCH_DATABASE_URL set."
        )
    raise SchemaOutOfDate(
        f"The database is at migration {actual!r} but this code expects {expected!r}. "
        "Run `alembic upgrade head` before starting."
    )


def init_db(*, auto_migrate: bool | None = None) -> None:
    """Prepare the database for use.

    In development the migrations are applied automatically; in production they
    are a deliberate, separate step and startup only verifies the result.
    """
    import app.models  # noqa: F401  (registers every mapper)

    settings = get_settings()
    should_migrate = settings.auto_migrate if auto_migrate is None else auto_migrate

    if should_migrate:
        log.info("applying migrations (auto_migrate is on)")
        migrate_to_head()
    assert_at_head()

    from app.models.meta import CURRENT_SCHEMA_VERSION, SchemaVersion

    with session_scope() as session:
        if session.query(SchemaVersion).first() is None:
            session.add(SchemaVersion(version=CURRENT_SCHEMA_VERSION))


def create_all_for_tests(target: Engine) -> None:
    """Create the schema directly. Test setup only.

    Named so that its appearance in a production path is obvious in review.
    """
    import app.models  # noqa: F401

    Base.metadata.create_all(target)


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
