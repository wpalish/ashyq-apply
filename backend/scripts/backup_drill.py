#!/usr/bin/env python
"""Prove that a PostgreSQL backup restores into a fresh database.

Run under the bundled PostgreSQL harness:

    python scripts/pg.py .venv/bin/python scripts/backup_drill.py

The script creates one uniquely named scratch database, restores a custom-format
pg_dump into it, compares every application-table row count, then drops only the
scratch database it created.  The dump itself contains no credentials.
"""

from __future__ import annotations

import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import sqlalchemy as sa

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.db import migrate_to_head  # noqa: E402


def libpq_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def database_url(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{name}", parts.query, parts.fragment))


def postgres_binary(name: str) -> str:
    import pgserver

    path = Path(pgserver.__file__).resolve().parent / "pginstall" / "bin" / name
    if not path.is_file():
        raise RuntimeError(f"{name} not found at {path}")
    return str(path)


def counts(engine: sa.Engine) -> dict[str, int]:
    tables = sorted(
        name for name in sa.inspect(engine).get_table_names() if name not in {"alembic_version"}
    )
    with engine.connect() as connection:
        return {
            table: int(connection.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one())
            for table in tables
        }


def main() -> int:
    source_url = get_settings().database_url
    if not source_url.startswith("postgres"):
        raise SystemExit("backup drill requires a PostgreSQL UNIMATCH_DATABASE_URL")
    migrate_to_head(source_url)
    source = sa.create_engine(source_url)
    probe_id = secrets.token_hex(16)
    with source.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO applicant_profiles "
                "(id, organization_id, display_name, payload, created_at, updated_at) "
                "VALUES (:id, :org, :name, :payload, now(), now())"
            ),
            {
                "id": probe_id,
                "org": "00000000000000000000000000000001",
                "name": "Backup drill probe (synthetic)",
                "payload": '{"display_name":"Backup drill probe (synthetic)"}',
            },
        )
    before = counts(source)

    scratch = f"unimatch_restore_{secrets.token_hex(6)}"
    restored_url = database_url(source_url, scratch)
    admin = sa.create_engine(source_url, isolation_level="AUTOCOMMIT")
    dump_path = Path(tempfile.mkstemp(prefix="unimatch-backup-", suffix=".dump")[1])
    try:
        subprocess.run(
            [
                postgres_binary("pg_dump"),
                "--format=custom",
                "--file",
                str(dump_path),
                "--dbname",
                libpq_url(source_url),
            ],
            check=True,
        )
        with admin.connect() as connection:
            connection.execute(sa.text(f'CREATE DATABASE "{scratch}"'))
        subprocess.run(
            [
                postgres_binary("pg_restore"),
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                libpq_url(restored_url),
                str(dump_path),
            ],
            check=True,
        )
        restored = sa.create_engine(restored_url)
        try:
            after = counts(restored)
            with restored.connect() as connection:
                probe = connection.execute(
                    sa.text("SELECT display_name FROM applicant_profiles WHERE id = :id"),
                    {"id": probe_id},
                ).scalar_one()
            if before != after or probe != "Backup drill probe (synthetic)":
                raise RuntimeError(
                    f"restore mismatch: before={before}, after={after}, probe={probe!r}"
                )
        finally:
            restored.dispose()
        print(f"PASS: restored {len(before)} tables with identical row counts")
        print(f"backup_bytes={dump_path.stat().st_size} scratch_database={scratch}")
        return 0
    finally:
        source.dispose()
        with admin.connect() as connection:
            connection.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": scratch},
            )
            connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{scratch}"'))
        admin.dispose()
        dump_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
