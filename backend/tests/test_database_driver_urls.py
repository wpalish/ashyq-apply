"""Provider PostgreSQL URLs must start with the installed production driver."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.config import Settings


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_standard_provider_url_uses_installed_psycopg_without_connecting(monkeypatch, scheme):
    raw = f"{scheme}://fixture:p%40ss%3Afixture@db.example:5432/apply?sslmode=require"
    monkeypatch.setenv("UNIMATCH_DATABASE_URL", raw)
    settings = Settings()
    engine = create_engine(settings.database_url)
    try:
        assert settings.is_postgres
        assert engine.dialect.driver == "psycopg"
        assert not engine.pool.checkedout()
        url = make_url(settings.database_url)
        assert url.username == "fixture"
        assert url.password == "p@ss:fixture"
        assert url.host == "db.example"
        assert url.port == 5432
        assert url.database == "apply"
        assert url.query == {"sslmode": "require"}
    finally:
        engine.dispose()


def test_explicit_psycopg_url_keeps_its_options():
    raw = "postgresql+psycopg://fixture@db.example/apply?sslmode=verify-full"
    assert Settings(database_url=raw).database_url == raw


def test_sqlite_demo_database_keeps_its_driver(tmp_path):
    raw = f"sqlite:///{tmp_path / 'demo.db'}"
    settings = Settings(database_url=raw)
    assert settings.database_url == raw
    engine = create_engine(settings.database_url)
    assert engine.dialect.driver == "pysqlite"
    engine.dispose()
