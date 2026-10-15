"""Full unchanged native pytest, after coverage-safe dependency/bootstrap setup."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit

from guard_runtime import STATE, RUNTIME, arm, deny, private_path, write_state


def main() -> int:
    arm()
    runtime = Path(os.environ["FULL_BACKEND_RUNTIME"]).resolve()
    evidence = Path(os.environ["FULL_BACKEND_EVIDENCE"]).resolve()
    import fasteners
    import pgserver
    import psycopg
    import pytest
    from pgserver import PostgresServer

    # Both native postgres_url and the PG default use the caller-owned root.
    # No user-wide pgserver socket registry/lock is touched.
    registry = runtime / "pg-runtime"
    registry.mkdir(mode=0o700)
    PostgresServer.runtime_path = registry
    PostgresServer.lock_path = registry / ".lockfile"
    PostgresServer._lock = fasteners.InterProcessLock(PostgresServer.lock_path)
    original_get_uri = PostgresServer.get_uri

    def owned_synthetic_uri(self, *args, **kwargs):
        # Forward the installed method exactly once, then remove only its empty
        # password placeholder for this fresh synthetic Unix server. SQLAlchemy
        # str(URL) otherwise masks even empty password as '***' on migration tests.
        value = original_get_uri(self, *args, **kwargs)
        parsed = urlsplit(value)
        hosts = parse_qs(parsed.query, keep_blank_values=True).get('host', [])
        data = Path(self.pgdata).resolve()
        host = Path(hosts[0]).resolve() if len(hosts) == 1 and hosts[0].startswith('/') else None
        if (not private_path(data) or host is None or not private_path(host)
                or not host.is_dir() or host.stat().st_mode & 0o077
                or host.stat().st_uid != os.getuid()
                or parsed.scheme != 'postgresql' or parsed.hostname is not None
                or not parsed.username or parsed.password not in (None, '')):
            deny('pgserver URI is not an owned password-free synthetic Unix server')
        if parsed.password == '':
            if not parsed.netloc.endswith(':@'):
                deny('unexpected empty-password pgserver URI shape')
            normalized = urlunsplit(parsed._replace(netloc=parsed.netloc[:-2] + '@'))
            STATE.setdefault('normalized_empty_pgserver_password_events', []).append({
                'host': str(host), 'pgdata': str(data), 'database': parsed.path.lstrip('/'),
                'operation': 'empty placeholder removed; original method args forwarded unchanged',
            })
            return normalized
        return value

    PostgresServer.get_uri = owned_synthetic_uri
    pgdata = runtime / "bootstrap-pg"
    server = None
    code = 2
    try:
        server = pgserver.get_server(str(pgdata), cleanup_mode="stop")
        uri = server.get_uri()
        # Positive isolation probe: only an owned private Unix PG SELECT 1.
        with psycopg.connect(uri, connect_timeout=5) as connection:
            assert connection.execute("SELECT 1").fetchone() == (1,)
        (evidence / "private-pg-probe.json").write_text(json.dumps({
            "passed": True, "pgdata": str(pgdata), "probe": "SELECT 1",
            "endpoint_logged_without_uri_or_password": True,
        }, indent=2) + "\n")
        if os.environ["FULL_BACKEND_PHASE"] == "postgres":
            os.environ["UNIMATCH_DATABASE_URL"] = uri.replace("postgresql://", "postgresql+psycopg://")
        # No app import occurs before pytest.main loads pytest_cov and starts
        # measurement. Native conftest and native Settings semantics are unchanged.
        code = int(pytest.main(sys.argv[1:]))
    finally:
        STATE["pytest_exit_code"] = code
        if server is not None:
            server.cleanup()
        write_state()
    return 2 if STATE["outside_attempts"] else code


if __name__ == "__main__":
    raise SystemExit(main())
