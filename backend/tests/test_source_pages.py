"""SourcePage: one mutable row per fetched page, and the retention contract.

Contract tests for T28's storage half, authored RED-first on baseline
28d729ca76cd (branch ai/c2/t28/qa). On that baseline the model, its ``record``
upsert and the migration do not exist, so:

- 8, 9, 10  RED (ImportError): no ``app.models.SourcePage`` yet.
- 11        RED (assertion): the migration round-trip finds no source_pages
            table at head.
- 12        RED (assertion): the same on PostgreSQL.
- 13        RED: the constant-agreement half fails with a clear "no migration
            defines SOURCE_PAGE_RETENTION_DAYS" assertion (the revision id is
            not knowable before the developer names the file, so the migration
            is located by content); the truth-table half is an ImportError.
- 14        GREEN by design: the single-head invariant is model-free and must
            hold before and after T28 — it guards the migration chain itself.

PG scenarios run against the real local PostgreSQL from conftest (pgserver);
SQLite scenarios migrate a throwaway file. Nothing here creates schema with
``create_all`` — the migration is the thing under test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

#: The head T28's migration hangs off — the chain head on the baseline.
PRE_T28_HEAD = "e7c1a4d90b52"


@pytest.fixture
def source_session(tmp_path):
    """A migrated SQLite database.

    Migrated rather than created with ``create_all``, so the migration itself
    is under test on every run.
    """
    from app.db import migrate_to_head

    url = f"sqlite:///{tmp_path / 'source_pages.db'}"
    migrate_to_head(url)
    engine = sa.create_engine(url)
    session = sessionmaker(bind=engine, future=True)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# --- 8-9: one row per URL ---------------------------------------------------


class TestOneRowPerUrl:
    def test_two_sessions_recording_the_same_url_write_one_row(self, pg_engine):
        """The upsert is atomic (insert .. on conflict), so two independent
        sessions converge on one row instead of racing two inserts."""
        from app.models import SourcePage

        factory = sessionmaker(bind=pg_engine, future=True)
        first_session, second_session = factory(), factory()
        try:
            page_a = SourcePage.record(
                first_session,
                url="https://example.edu/programme",
                registrable_domain="example.edu",
                etag='"v1"',
                http_status=200,
            )
            # A claim writer touched the row after the fetch. record() itself
            # never does this; the column belongs to the claim system.
            page_a.active_claims = 2
            first_session.commit()

            page_b = SourcePage.record(
                second_session,
                url="https://example.edu/programme",
                registrable_domain="example.edu",
                etag='"v2"',
                content_hash="ab" * 32,
            )
            second_session.commit()

            assert page_b is not None
            rows = second_session.query(SourcePage).all()
            assert len(rows) == 1
            row = rows[0]
            assert row.etag == '"v2"'  # B's values win on the conflict
            assert row.content_hash == "ab" * 32
            assert row.active_claims == 2  # ...and the claims count is untouched
        finally:
            first_session.close()
            second_session.close()

    def test_a_duplicate_url_is_refused_by_the_database(self, pg_session):
        """Beneath record() sits a unique index; a raw duplicate insert must
        hit it, or the one-row-per-page design has no floor."""
        from app.models import SourcePage

        pg_session.add(SourcePage(url="https://example.edu/one", registrable_domain="example.edu"))
        pg_session.commit()
        pg_session.add(SourcePage(url="https://example.edu/one", registrable_domain="example.edu"))
        with pytest.raises(IntegrityError):
            pg_session.commit()
        pg_session.rollback()
        assert pg_session.query(SourcePage).count() == 1


# --- 10: record() upsert semantics ------------------------------------------


class TestRecordSemantics:
    def test_the_upsert_coalesces_ownership_and_overwrites_fetch_metadata(self, source_session):
        """Fetch metadata (etag/status/page_type/fetched_at) always takes the
        new value, even when it is None; ownership (institution_key,
        lastmod_seen) coalesces — an existing value wins over None; and
        active_claims is never touched by a fetch."""
        from app.models import SourcePage
        from app.models.base import ensure_utc

        now = datetime.now(UTC)
        earlier = now - timedelta(days=3)
        SourcePage.record(
            source_session,
            url="https://example.edu/programme",
            registrable_domain="example.edu",
            etag='"v1"',
            page_type="programme",
            institution_key="university-of-nowhere",
            lastmod_seen=earlier,
            fetched_at=earlier,
        )
        first = source_session.query(SourcePage).one()
        first.active_claims = 1
        source_session.commit()

        SourcePage.record(
            source_session,
            url="https://example.edu/programme",
            registrable_domain="example.edu",
            etag=None,  # None overwrites: the new fetch had no validator
            http_status=200,
            page_type="catalogue",
            institution_key=None,  # ownership coalesces: existing wins
            lastmod_seen=None,
            fetched_at=now,
        )
        source_session.commit()

        row = source_session.query(SourcePage).one()
        assert row.etag is None
        assert row.http_status == 200
        assert row.page_type == "catalogue"
        assert ensure_utc(row.fetched_at) == now
        assert row.institution_key == "university-of-nowhere"
        assert ensure_utc(row.lastmod_seen) == earlier
        assert row.active_claims == 1


# --- 11-12: the migration round-trip ----------------------------------------


class TestMigrationRoundTrip:
    def test_the_migration_upgrades_and_downgrades_on_sqlite(self, tmp_path):
        import sqlalchemy as sa

        from app.db import _alembic_config, migrate_to_head

        url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
        migrate_to_head(url)
        engine = sa.create_engine(url)
        try:
            assert sa.inspect(engine).has_table("source_pages")
        finally:
            engine.dispose()

        # Downgrade removes exactly the T28 migration, nothing else.
        from alembic import command

        command.downgrade(_alembic_config(url), PRE_T28_HEAD)
        engine = sa.create_engine(url)
        try:
            assert not sa.inspect(engine).has_table("source_pages")
        finally:
            engine.dispose()

        migrate_to_head(url)
        engine = sa.create_engine(url)
        try:
            assert sa.inspect(engine).has_table("source_pages")
        finally:
            engine.dispose()

    def test_the_migration_upgrades_and_downgrades_on_postgresql(self, pg_engine):
        """pg_engine's fixture has already migrated the throwaway database to
        head; the same URL drives the downgrade and the re-upgrade."""
        import sqlalchemy as sa
        from alembic import command

        from app.db import _alembic_config

        url = str(pg_engine.url)
        assert sa.inspect(pg_engine).has_table("source_pages")

        command.downgrade(_alembic_config(url), PRE_T28_HEAD)
        assert not sa.inspect(pg_engine).has_table("source_pages")

        command.upgrade(_alembic_config(url), "head")
        assert sa.inspect(pg_engine).has_table("source_pages")


# --- 13: the retention contract ---------------------------------------------


class TestRetentionContract:
    def test_the_migration_and_the_model_agree_on_retention(self):
        """SOURCE_PAGE_RETENTION_DAYS in the migration == RETENTION_DAYS in the
        model == 180.

        A migration must not import the application, so the constant is
        written down twice; this is what stops the copies drifting. The
        revision id is not knowable until the developer names the file, so the
        migration is located by content: the one file under
        migrations/versions that defines SOURCE_PAGE_RETENTION_DAYS.
        """
        import importlib.util

        versions = Path(__file__).resolve().parent.parent / "migrations" / "versions"
        matches = [
            path
            for path in sorted(versions.glob("*.py"))
            if path.name != "__init__.py" and "SOURCE_PAGE_RETENTION_DAYS" in path.read_text()
        ]
        assert matches != [], "no migration file defines SOURCE_PAGE_RETENTION_DAYS"
        assert len(matches) == 1, f"retention constant defined in several migrations: {matches}"

        spec = importlib.util.spec_from_file_location("t28_source_pages_migration", matches[0])
        migration = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(migration)

        from app.models.source_page import RETENTION_DAYS

        assert migration.SOURCE_PAGE_RETENTION_DAYS == RETENTION_DAYS == 180

    def test_is_purgeable_truth_table(self):
        """Purgeable = nothing claims the page and it is strictly older than
        the retention window (or never fetched, and the row itself is)."""
        from app.models.source_page import RETENTION_DAYS, is_purgeable

        now = datetime.now(UTC)
        old = now - timedelta(days=RETENTION_DAYS + 1)
        fresh = now - timedelta(days=RETENTION_DAYS - 1)
        boundary = now - timedelta(days=RETENTION_DAYS)  # exactly at the line: kept

        # active_claims > 0 is never purged, however old, however stored.
        assert not is_purgeable(old, now, 1, now)
        assert not is_purgeable(None, old, 3, now)
        # Fetched, unclaimed: purgeable strictly past the boundary only.
        assert is_purgeable(old, now, 0, now)
        assert not is_purgeable(fresh, now, 0, now)
        assert not is_purgeable(boundary, now, 0, now)
        # Never fetched: age on created_at, same boundary rule.
        assert is_purgeable(None, old, 0, now)
        assert not is_purgeable(None, boundary, 0, now)
        assert not is_purgeable(None, fresh, 0, now)


# --- 14: the chain stays linear (model-free, GREEN before and after) --------


class TestMigrationChainHealth:
    def test_there_is_exactly_one_head_and_it_is_what_the_app_expects(self):
        """Deliberately model-free: the single-head invariant must hold before
        T28 lands and still hold after, or the migration chain forked."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        from app.db import ALEMBIC_INI, MIGRATIONS_DIR, head_revision

        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(MIGRATIONS_DIR))
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()

        assert len(heads) == 1, f"migration chain forked: {heads}"
        assert heads == [head_revision()]
