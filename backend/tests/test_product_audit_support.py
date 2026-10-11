"""Function-scoped native fixtures for retained product-audit regressions.

This helper has no application imports, Settings overrides or environment
mutation at collection. Native conftest remains unchanged. PG provisioning and
migrations use its pg_engine fixture; root owns guarded process bootstrap.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ORG = "a" * 32
PROFILE = "p" * 32
READER = "1" * 32
SENDER = "2" * 32
OTHER_ORG = "z" * 32


@dataclass
class Sandbox:
    client: object
    sessions: object
    identity: dict
    settings: object
    network_attempts: list
    dialect: str
    observations: list = field(default_factory=list)


@pytest.fixture
def product_audit_settings(tmp_path, monkeypatch, corpus_dir):
    """Use the native cached getter with restored, synthetic env per case."""
    from app.config import Settings, get_settings
    from tests.conftest import configure_from_env

    # Function-scoped monkeypatch only; never replace the shared getter.
    monkeypatch.setattr(Settings, "model_config", {**Settings.model_config, "env_file": None})
    for name in list(os.environ):
        if name.startswith(("UNIMATCH_", "PG")) or name in {
            "EXA_API_KEY",
            "TAVILY_API_KEY",
            "BRAVE_API_KEY",
            "SERPER_API_KEY",
            "TYPESAFE_API_KEY",
            "APIPAY_API_KEY",
        }:
            monkeypatch.delenv(name, raising=False)
    passfile = tmp_path / "empty.pgpass"
    passfile.write_bytes(b"")
    passfile.chmod(0o600)
    pgconfig = tmp_path / "pg-config"
    pgconfig.mkdir(mode=0o700)
    monkeypatch.setenv("PGPASSFILE", str(passfile))
    monkeypatch.setenv("PGSYSCONFDIR", str(pgconfig))
    configure_from_env(
        monkeypatch,
        tmp_path,
        corpus_dir,
        UNIMATCH_ENVIRONMENT="development",
        UNIMATCH_AUTH_ENABLED="true",
        UNIMATCH_PAYMENTS_ENABLED="true",
        UNIMATCH_PAYMENTS_PROVIDER="fake",
        UNIMATCH_APIPAY_WEBHOOK_SECRET="synthetic-product-audit-secret",
        UNIMATCH_PASSWORD_SCRYPT_LOG2="10",
        UNIMATCH_SEARCH_PROVIDER="none",
        UNIMATCH_DECISION_PROVIDER="none",
        UNIMATCH_AUTH_RATE_LIMIT_PER_MINUTE="200",
        UNIMATCH_SOCIAL_RATE_LIMIT_PER_MINUTE="200",
    )
    value = get_settings()
    value.ensure_dirs()
    try:
        yield value
    finally:
        get_settings.cache_clear()
    # monkeypatch restores all env and class config after fixture teardown.


def install_private_database_guard(monkeypatch, engine):
    """Permit only this native fixture's Unix PG endpoint; deny other I/O.

    Armed after native DB provisioning/migration, before any audit API call.
    Root must isolate the process and PG fixture bootstrap itself. libpq's C
    path is checked separately from Python sockets; no kwargs are dropped.
    """
    import psycopg
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    attempts = []
    expected = None
    if engine.dialect.name == "postgresql":
        host = engine.url.query.get("host")
        assert isinstance(host, str) and host.startswith("/"), "Native PG must use a Unix socket"
        assert engine.url.host in (None, ""), "IP PostgreSQL fixture is forbidden"
        directory = Path(host)
        assert directory.is_dir()
        assert directory.stat().st_mode & 0o077 == 0, "PG Unix socket directory must be private"
        expected = {
            "host": host,
            "dbname": engine.url.database,
            "user": engine.url.username,
            "port": str(engine.url.query.get("port") or engine.url.port or 5432),
        }
        pg_socket = str(directory / (".s.PGSQL." + expected["port"]))
    else:
        assert engine.dialect.name == "sqlite"
        pg_socket = None
    passfile = Path(os.environ["PGPASSFILE"])
    assert passfile.read_bytes() == b"" and passfile.stat().st_mode & 0o077 == 0

    def forbidden(label):
        attempts.append(label)
        raise AssertionError(f"Outside synthetic audit I/O: {label}")

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_bind = socket.socket.bind
    real_sendto = socket.socket.sendto

    def connect(sock, address):
        if sock.family != socket.AF_UNIX or pg_socket is None or address != pg_socket:
            return forbidden("socket.connect")
        return real_connect(sock, address)

    def connect_ex(sock, address):
        if sock.family != socket.AF_UNIX or pg_socket is None or address != pg_socket:
            return forbidden("socket.connect_ex")
        return real_connect_ex(sock, address)

    def bind(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            return forbidden("socket.bind IP")
        return real_bind(sock, address)

    def sendto(sock, *args):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            return forbidden("socket.sendto IP")
        return real_sendto(sock, *args)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket.socket, "bind", bind)
    monkeypatch.setattr(socket.socket, "sendto", sendto)
    for name in [
        "create_connection",
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "getnameinfo",
    ]:
        monkeypatch.setattr(
            socket, name, lambda *a, _label=name, **k: forbidden("socket." + _label)
        )
    native_module = psycopg.connect
    native_class = psycopg.Connection.connect
    python_keys = {"autocommit", "prepare_threshold", "context", "row_factory", "cursor_factory"}

    def validate(conninfo, kwargs):
        options = {key: value for key, value in kwargs.items() if key not in python_keys}
        values = conninfo_to_dict(make_conninfo(conninfo, **options))
        if (
            expected is None
            or any(values.get(key) != value for key, value in expected.items() if key != "port")
            or str(values.get("port") or 5432) != expected["port"]
            or values.get("hostaddr")
            or values.get("service")
            or values.get("password")
            or values.get("passfile") not in (None, str(passfile))
        ):
            return forbidden("libpq outside native private fixture")

    def module_connect(conninfo="", **kwargs):
        validate(conninfo, kwargs)
        return native_module(conninfo, **kwargs)

    def class_connect(cls, conninfo="", **kwargs):
        validate(conninfo, kwargs)
        return native_class(conninfo, **kwargs)

    monkeypatch.setattr(psycopg, "connect", module_connect)
    monkeypatch.setattr(psycopg.Connection, "connect", classmethod(class_connect))
    return attempts


@pytest.fixture
def sandbox(request, tmp_path, monkeypatch, product_audit_settings):
    """Migrate a function-isolated database and supply only synthetic rows."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from app import db as db_module
    from app import main as main_module
    from app.corpus.demo_profile import DEMO_PROFILE
    from app.db import get_session
    from app.models import ApplicantProfileRow, Organization, User
    from app.models.social import SocialProfile
    from app.security import Principal, get_principal

    settings = product_audit_settings
    backend = getattr(request, "param", "sqlite")
    if backend == "postgres":
        engine = request.getfixturevalue("pg_engine")
        settings.database_url = str(engine.url)
        owned_engine = False
    else:
        assert backend == "sqlite"
        db_module.migrate_to_head(settings.database_url)
        engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
        owned_engine = True

        @event.listens_for(engine, "connect")
        def sqlite_pragmas(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=15000")

    attempts = install_private_database_guard(monkeypatch, engine)
    sessions = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", sessions)
    monkeypatch.setattr(main_module, "settings", settings)
    identity = {
        "principal": Principal(
            user_id=READER,
            organization_id=ORG,
            email="synthetic-reader@example.invalid",
            display_name="Synthetic Reader",
            role="owner",
        )
    }

    def dependency():
        with sessions() as session:
            yield session

    app = main_module.app
    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_session] = dependency
    app.dependency_overrides[get_principal] = lambda: identity["principal"]
    client = None
    try:
        with sessions() as session:
            session.add(
                Organization(id=ORG, name="Synthetic workspace", slug="synthetic-workspace")
            )
            session.add_all(
                [
                    User(
                        id=READER,
                        email="synthetic-reader@example.invalid",
                        display_name="Reader",
                        password_hash="disabled",
                    ),
                    User(
                        id=SENDER,
                        email="synthetic-sender@example.invalid",
                        display_name="Sender",
                        password_hash="disabled",
                    ),
                ]
            )
            session.flush()
            session.add(
                ApplicantProfileRow(
                    id=PROFILE,
                    organization_id=ORG,
                    display_name="Synthetic applicant",
                    payload=DEMO_PROFILE.model_dump(mode="json"),
                )
            )
            session.add_all([SocialProfile(user_id=READER), SocialProfile(user_id=SENDER)])
            session.commit()
        # No context manager: API lifespan/reconcile/worker starts are excluded.
        client = TestClient(app)
        request.node.user_properties.append(("product_audit_database", engine.dialect.name))
        lab = Sandbox(client, sessions, identity, settings, attempts, engine.dialect.name)
        yield lab
        for observation in lab.observations:
            request.node.user_properties.append(
                ("product_audit_lock_observation", repr(observation))
            )
    finally:
        if client is not None:
            client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        if owned_engine:
            engine.dispose()
        assert attempts == [], f"Unexpected outside I/O: {attempts}"
