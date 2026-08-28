#!/usr/bin/env python
"""Run a command against a local PostgreSQL.

`pgserver` ships PostgreSQL binaries and starts a cluster in a local directory,
so a developer needs neither Docker nor Homebrew. The server lives only as long
as this process, so anything that needs it has to run underneath.

    python scripts/pg.py alembic upgrade head
    python scripts/pg.py pytest -q
    python scripts/pg.py --print-uri

In a deployed environment nothing here is used: UNIMATCH_DATABASE_URL points at
a managed PostgreSQL. See docs/adr/0002-postgresql-provisioning.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BACKEND / "data" / "pgdata"


def start(data_dir: Path):
    try:
        import pgserver
    except ImportError:  # pragma: no cover
        sys.exit(
            "pgserver is not installed. Run ./setup.sh, or point "
            "UNIMATCH_DATABASE_URL at your own PostgreSQL."
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    server = pgserver.get_server(str(data_dir))
    # SQLAlchemy needs the driver named explicitly; psycopg 3 is what we pin.
    uri = server.get_uri().replace("postgresql://", "postgresql+psycopg://")
    return server, uri


def main() -> int:
    argv = sys.argv[1:]
    data_dir = Path(os.environ.get("UNIMATCH_PGDATA", DEFAULT_DATA_DIR))
    server, uri = start(data_dir)
    try:
        if not argv or argv[0] == "--print-uri":
            print(uri)
            return 0
        env = {**os.environ, "UNIMATCH_DATABASE_URL": uri}
        return subprocess.call(argv, cwd=BACKEND, env=env)
    finally:
        # Leave the cluster on disk so the next run is fast; only stop serving.
        server.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
