"""V2-20 — evidence history: the versions of a page, and of a claim.

``SourcePage`` answers "has this changed?". V2-20a is about the question it
cannot answer — what did the page say when we claimed something from it — and
V2-20b's migration is checked here beside it, since both exist for the same
reason: history that survives the overwrite.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.models import Base, SourcePage, SourceSnapshot

PRE_SNAPSHOT_HEAD = "d9c4e7a21b83"
T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'snap.db'}")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()
    engine.dispose()


def record(session, *, content_hash, at, etag=None, url="https://example.edu/entry"):
    return SourcePage.record(
        session,
        url=url,
        registrable_domain="example.edu",
        content_hash=content_hash,
        etag=etag,
        http_status=200,
        fetched_at=at,
    )


class TestRecordingAVersion:
    def test_a_fetch_records_the_version_it_saw(self, session):
        page = record(session, content_hash="a" * 64, at=T0)
        rows = session.query(SourceSnapshot).all()
        assert len(rows) == 1
        assert rows[0].page_id == page.id
        assert rows[0].content_hash == "a" * 64

    def test_a_changed_page_keeps_what_it_said_before(self, session):
        """The whole point: the previous hash survives the page's own update."""
        record(session, content_hash="a" * 64, at=T0)
        record(session, content_hash="b" * 64, at=T0 + timedelta(days=1))
        hashes = {s.content_hash for s in session.query(SourceSnapshot).all()}
        assert hashes == {"a" * 64, "b" * 64}
        # The page itself still holds only the current one.
        assert session.query(SourcePage).one().content_hash == "b" * 64

    def test_seeing_the_same_content_again_is_not_a_new_version(self, session):
        record(session, content_hash="a" * 64, at=T0)
        record(session, content_hash="a" * 64, at=T0 + timedelta(days=2))
        snapshot = session.query(SourceSnapshot).one()
        assert snapshot.first_seen_at.replace(tzinfo=UTC) == T0
        assert snapshot.last_seen_at.replace(tzinfo=UTC) == T0 + timedelta(days=2)

    def test_a_page_that_reverts_is_the_same_content_seen_again(self, session):
        """Documented decision, not an accident: A → B → A is two versions.

        The order of events survives in last_seen_at, and B keeps its own row,
        so nothing is lost by refusing to invent a third version that is
        byte-for-byte one we already hold.
        """
        record(session, content_hash="a" * 64, at=T0)
        record(session, content_hash="b" * 64, at=T0 + timedelta(days=1))
        record(session, content_hash="a" * 64, at=T0 + timedelta(days=2))
        rows = {s.content_hash: s for s in session.query(SourceSnapshot).all()}
        assert set(rows) == {"a" * 64, "b" * 64}
        assert rows["a" * 64].first_seen_at.replace(tzinfo=UTC) == T0
        assert rows["a" * 64].last_seen_at.replace(tzinfo=UTC) == T0 + timedelta(days=2)

    def test_a_fetch_with_no_content_hash_records_no_version(self, session):
        """A failed or unreadable fetch has not observed a version of anything."""
        SourcePage.record(
            session,
            url="https://example.edu/gone",
            registrable_domain="example.edu",
            http_status=404,
            fetched_at=T0,
        )
        assert session.query(SourceSnapshot).count() == 0

    def test_two_pages_do_not_share_a_version(self, session):
        record(session, content_hash="a" * 64, at=T0, url="https://example.edu/one")
        record(session, content_hash="a" * 64, at=T0, url="https://example.edu/two")
        assert session.query(SourceSnapshot).count() == 2


class TestTheMigration:
    def test_there_is_exactly_one_head(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        from app.db import ALEMBIC_INI, MIGRATIONS_DIR, head_revision

        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(MIGRATIONS_DIR))
        heads = ScriptDirectory.from_config(config).get_heads()
        assert len(heads) == 1
        assert heads == [head_revision()]

    def test_upgrade_then_downgrade_on_postgresql(self, pg_engine):
        """On the real database, and exactly reversible."""
        from alembic import command

        from app.db import _alembic_config

        url = str(pg_engine.url)
        command.downgrade(_alembic_config(url), PRE_SNAPSHOT_HEAD)
        assert not sa.inspect(pg_engine).has_table("source_snapshots")

        command.upgrade(_alembic_config(url), "head")
        inspector = sa.inspect(pg_engine)
        assert inspector.has_table("source_snapshots")
        columns = {c["name"] for c in inspector.get_columns("source_snapshots")}
        assert {"page_id", "content_hash", "first_seen_at", "last_seen_at"} <= columns
        indexes = {i["name"] for i in inspector.get_indexes("source_snapshots")}
        assert "uq_snapshots_page_hash" in indexes

    def test_deleting_a_page_takes_its_versions_with_it(self, pg_engine):
        """CASCADE, and the behavioural reason for it: a version of a page that
        no longer exists is not evidence of anything."""
        from alembic import command

        from app.db import _alembic_config

        command.upgrade(_alembic_config(str(pg_engine.url)), "head")
        session = sessionmaker(bind=pg_engine)()
        try:
            page = record(session, content_hash="a" * 64, at=T0)
            session.commit()
            assert session.query(SourceSnapshot).count() == 1
            session.delete(page)
            session.commit()
            assert session.query(SourceSnapshot).count() == 0
        finally:
            session.close()


class TestTheSupersessionMigration:
    """V2-20b — `claims.superseded_at` / `superseded_by_id` on PostgreSQL."""

    def test_upgrade_then_downgrade_on_postgresql(self, pg_engine):
        from alembic import command

        from app.db import _alembic_config

        url = str(pg_engine.url)
        command.downgrade(_alembic_config(url), "a1f3c8d75e29")
        columns = {c["name"] for c in sa.inspect(pg_engine).get_columns("claims")}
        assert "superseded_at" not in columns
        assert "superseded_by_id" not in columns

        command.upgrade(_alembic_config(url), "head")
        columns = {c["name"] for c in sa.inspect(pg_engine).get_columns("claims")}
        assert {"superseded_at", "superseded_by_id"} <= columns
        keys = sa.inspect(pg_engine).get_foreign_keys("claims")
        by_name = {k["name"]: k for k in keys}
        assert by_name["fk_claims_superseded_by"]["referred_table"] == "claims"
        assert by_name["fk_claims_superseded_by"]["options"]["ondelete"] == "SET NULL"

    def test_deleting_a_successor_leaves_the_history_row(self, pg_engine):
        """SET NULL, and why: a purge must never take a history row with it."""
        from alembic import command

        from app.db import _alembic_config
        from app.models import ClaimRow

        command.upgrade(_alembic_config(str(pg_engine.url)), "head")
        session = sessionmaker(bind=pg_engine)()
        try:
            from app.models import ResearchRun
            from tests.conftest import profile_row

            owner = profile_row(session, {"display_name": "t"})
            run = ResearchRun(profile_id=owner.id, stage="awaiting_user_decision", demo_mode=True)
            session.add(run)
            session.flush()
            successor = ClaimRow(
                run_id=run.id,
                claim_type="ielts_min_overall",
                status="VERIFIED_CURRENT",
                source_url="https://example.edu/entry",
                source_specificity="program",
                accessed_at=T0,
                payload={"normalized_value": 7.0},
            )
            session.add(successor)
            session.flush()
            old = ClaimRow(
                run_id=run.id,
                claim_type="ielts_min_overall",
                status="SUPERSEDED",
                source_url="https://example.edu/entry",
                source_specificity="program",
                accessed_at=T0,
                payload={"normalized_value": 6.5},
                superseded_at=T0,
                superseded_by_id=successor.id,
            )
            session.add(old)
            session.commit()

            session.delete(successor)
            session.commit()
            session.refresh(old)
            assert old.superseded_at is not None, "the history row survives"
            assert old.superseded_by_id is None, "its successor link is cleared, not cascaded"
            assert old.payload["normalized_value"] == 6.5
        finally:
            session.close()
