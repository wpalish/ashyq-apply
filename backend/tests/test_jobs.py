"""The durable job queue, against real PostgreSQL.

These run on PostgreSQL rather than SQLite because the mechanism under test —
`SELECT … FOR UPDATE SKIP LOCKED`, the unique idempotency constraint, the
cascade behaviour — is PostgreSQL's. Testing it on SQLite would test a
different thing and say nothing about production.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.jobs.store import BACKOFF_SECONDS, JobStore, backoff_for
from app.models import Job, JobStatus


@pytest.fixture
def store(pg_session):
    return JobStore(pg_session, lease_seconds=60)


class TestEnqueue:
    def test_a_job_is_queued_and_immediately_available(self, store, pg_session):
        result = store.enqueue("research", run_id="r1")
        pg_session.commit()
        job = store.get(result.job_id)
        assert result.created
        assert job.status == JobStatus.QUEUED.value
        assert job.available_at <= datetime.now(UTC)

    def test_an_idempotency_key_prevents_a_duplicate(self, store, pg_session):
        first = store.enqueue("research", run_id="r1", idempotency_key="research:r1")
        pg_session.commit()
        second = store.enqueue("research", run_id="r1", idempotency_key="research:r1")
        pg_session.commit()

        assert first.created and not second.created
        assert first.job_id == second.job_id
        assert pg_session.query(Job).count() == 1

    def test_the_unique_constraint_backs_up_the_pre_check(self, pg_engine):
        """The pre-check can miss; the constraint is what actually guarantees it.

        Session B's pre-check runs before A commits, so it sees nothing and
        proceeds to insert. The unique key is what stops a second job existing.
        (B's insert is issued after A commits: PostgreSQL blocks a conflicting
        insert until the other transaction resolves, so issuing both first
        would simply deadlock the test rather than test anything.)
        """
        factory = sessionmaker(bind=pg_engine, future=True)
        a, b = factory(), factory()
        try:
            # B looks first and sees an empty table.
            assert b.query(Job).filter(Job.idempotency_key == "k").first() is None
            JobStore(a).enqueue("research", run_id="r1", idempotency_key="k")
            a.commit()

            result = JobStore(b).enqueue("research", run_id="r1", idempotency_key="k")
            b.commit()
            assert not result.created
            assert "concurrent" in result.reason or "already exists" in result.reason
            assert a.query(Job).count() == 1
        finally:
            a.close()
            b.close()

    def test_different_keys_create_different_jobs(self, store, pg_session):
        store.enqueue("research", idempotency_key="a")
        store.enqueue("research", idempotency_key="b")
        pg_session.commit()
        assert pg_session.query(Job).count() == 2


class TestClaim:
    def test_claiming_takes_a_lease_and_counts_the_attempt(self, store, pg_session):
        enqueued = store.enqueue("research", run_id="r1")
        pg_session.commit()

        job = store.claim(worker_id="worker-1")
        pg_session.commit()

        assert job.id == enqueued.job_id
        assert job.status == JobStatus.RUNNING.value
        assert job.worker_id == "worker-1"
        assert job.attempts == 1
        assert job.lease_expires_at > datetime.now(UTC)

    def test_a_claimed_job_is_invisible_to_another_worker(self, store, pg_session):
        store.enqueue("research", run_id="r1")
        pg_session.commit()
        store.claim(worker_id="worker-1")
        pg_session.commit()

        assert store.claim(worker_id="worker-2") is None

    def test_two_workers_racing_never_both_win(self, pg_engine):
        """This is what SKIP LOCKED is for."""
        factory = sessionmaker(bind=pg_engine, future=True)
        setup = factory()
        JobStore(setup).enqueue("research", run_id="r1")
        setup.commit()
        setup.close()

        a, b = factory(), factory()
        try:
            first = JobStore(a).claim(worker_id="A")
            # B looks while A still holds the row lock; it must step over it.
            second = JobStore(b).claim(worker_id="B")
            a.commit()
            b.commit()
            assert first is not None
            assert second is None
        finally:
            a.close()
            b.close()

    def test_a_deferred_job_is_not_claimable_yet(self, store, pg_session):
        store.enqueue("research", available_at=datetime.now(UTC) + timedelta(hours=1))
        pg_session.commit()
        assert store.claim() is None

    def test_higher_priority_is_claimed_first(self, store, pg_session):
        store.enqueue("research", idempotency_key="low", priority=0)
        store.enqueue("documents", idempotency_key="high", priority=10)
        pg_session.commit()

        job = store.claim()
        pg_session.commit()
        assert job.kind == "documents"

    def test_an_empty_queue_returns_nothing_rather_than_blocking(self, store):
        assert store.claim() is None


class TestCompletionAndFailure:
    def test_completing_releases_the_lease(self, store, pg_session):
        enqueued = store.enqueue("research")
        pg_session.commit()
        store.claim()
        pg_session.commit()
        store.complete(enqueued.job_id)
        pg_session.commit()

        job = store.get(enqueued.job_id)
        assert job.status == JobStatus.SUCCEEDED.value
        assert job.lease_expires_at is None
        assert job.worker_id is None
        assert job.finished_at is not None

    def test_a_failure_requeues_with_backoff(self, store, pg_session):
        enqueued = store.enqueue("research")
        pg_session.commit()
        store.claim()
        pg_session.commit()

        status = store.fail(enqueued.job_id, "network unreachable")
        pg_session.commit()

        job = store.get(enqueued.job_id)
        assert status == JobStatus.QUEUED.value
        assert job.available_at > datetime.now(UTC)
        assert "network unreachable" in job.last_error

    def test_backoff_grows_and_then_plateaus(self):
        delays = [backoff_for(n).total_seconds() for n in (1, 2, 3, 4, 10)]
        assert delays[:3] == list(BACKOFF_SECONDS)
        assert delays[3] == delays[4] == BACKOFF_SECONDS[-1]

    def test_exhausted_attempts_go_dead_rather_than_looping(self, store, pg_session):
        enqueued = store.enqueue("research", max_attempts=2)
        pg_session.commit()

        for _ in range(2):
            job = store.get(enqueued.job_id)
            job.available_at = datetime.now(UTC)
            pg_session.commit()
            store.claim()
            pg_session.commit()
            store.fail(enqueued.job_id, "boom")
            pg_session.commit()

        job = store.get(enqueued.job_id)
        assert job.status == JobStatus.DEAD.value
        assert job.attempts == 2
        assert store.claim() is None, "a dead job must never be picked up again"

    def test_a_non_retryable_failure_goes_dead_immediately(self, store, pg_session):
        enqueued = store.enqueue("research", max_attempts=5)
        pg_session.commit()
        store.claim()
        pg_session.commit()

        status = store.fail(enqueued.job_id, "the profile was deleted", retry=False)
        pg_session.commit()
        assert status == JobStatus.DEAD.value
        assert store.get(enqueued.job_id).attempts == 1


class TestLeaseAndReaping:
    def test_a_heartbeat_extends_the_lease(self, store, pg_session):
        enqueued = store.enqueue("research")
        pg_session.commit()
        job = store.claim()
        pg_session.commit()
        before = job.lease_expires_at

        store.heartbeat(enqueued.job_id)
        pg_session.commit()
        pg_session.refresh(job)
        assert job.lease_expires_at >= before

    def test_a_heartbeat_on_a_finished_job_fails(self, store, pg_session):
        enqueued = store.enqueue("research")
        pg_session.commit()
        store.claim()
        store.complete(enqueued.job_id)
        pg_session.commit()
        assert store.heartbeat(enqueued.job_id) is False

    def test_an_expired_lease_returns_the_job_to_the_queue(self, store, pg_session):
        """The crash case: the worker stopped beating."""
        enqueued = store.enqueue("research")
        pg_session.commit()
        store.claim(worker_id="doomed-worker")
        pg_session.commit()

        pg_session.execute(
            sa.update(Job).where(Job.id == enqueued.job_id)
            .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        pg_session.commit()

        reaped = store.reap_expired()
        pg_session.commit()

        job = store.get(enqueued.job_id)
        assert reaped == [enqueued.job_id]
        assert job.status == JobStatus.QUEUED.value
        assert job.worker_id is None
        assert "stopped without finishing" in job.last_error
        assert "doomed-worker" in job.last_error

    def test_a_live_lease_is_left_alone(self, store, pg_session):
        store.enqueue("research")
        pg_session.commit()
        store.claim()
        pg_session.commit()
        assert store.reap_expired() == []

    def test_a_job_that_keeps_killing_its_worker_eventually_dies(self, store, pg_session):
        """Otherwise a poison job loops forever, quietly."""
        enqueued = store.enqueue("research", max_attempts=2)
        pg_session.commit()

        for _ in range(2):
            job = store.get(enqueued.job_id)
            job.available_at = datetime.now(UTC)
            pg_session.commit()
            store.claim()
            pg_session.commit()
            pg_session.execute(
                sa.update(Job).where(Job.id == enqueued.job_id)
                .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
            pg_session.commit()
            store.reap_expired()
            pg_session.commit()

        assert store.get(enqueued.job_id).status == JobStatus.DEAD.value


class TestCancellation:
    def test_a_queued_job_is_cancelled_at_once(self, store, pg_session):
        enqueued = store.enqueue("research")
        pg_session.commit()

        assert store.cancel(enqueued.job_id)
        pg_session.commit()
        assert store.get(enqueued.job_id).status == JobStatus.CANCELLED.value
        assert store.claim() is None

    def test_a_running_job_is_flagged_for_the_worker_to_observe(self, store, pg_session):
        """Cancelling mid-stage would tear the work; the worker stops cleanly."""
        enqueued = store.enqueue("research")
        pg_session.commit()
        store.claim()
        pg_session.commit()

        assert store.cancel(enqueued.job_id)
        pg_session.commit()

        job = store.get(enqueued.job_id)
        assert job.status == JobStatus.RUNNING.value
        assert job.cancel_requested is True
        assert store.is_cancel_requested(enqueued.job_id)

    def test_a_finished_job_cannot_be_cancelled(self, store, pg_session):
        enqueued = store.enqueue("research")
        pg_session.commit()
        store.claim()
        store.complete(enqueued.job_id)
        pg_session.commit()
        assert store.cancel(enqueued.job_id) is False


class TestPostgresSchema:
    """Constraints that only exist on a real database."""

    def test_deleting_a_profile_cascades_at_the_database_level(self, pg_session):
        from app.models import ApplicantProfileRow, ClaimRow, ProgramResultRow, ResearchRun

        profile = ApplicantProfileRow(display_name="x", payload={})
        pg_session.add(profile)
        pg_session.flush()
        run = ResearchRun(profile_id=profile.id, stage="queued", stage_state={})
        pg_session.add(run)
        pg_session.flush()
        pg_session.add(ProgramResultRow(
            run_id=run.id, dedupe_key="k", university="U", university_key="u",
            country="C", program="P", eligibility="MET", admissions_fit="PLAUSIBLE_FIT",
            funding_fit="UNKNOWN", funding_classification="UNKNOWN", payload={},
        ))
        pg_session.add(ClaimRow(
            run_id=run.id, claim_type="min_gpa", status="UNVERIFIED",
            source_url="https://x.edu", source_specificity="program", payload={},
        ))
        pg_session.commit()

        pg_session.execute(
            sa.text("DELETE FROM applicant_profiles WHERE id = :i"), {"i": profile.id}
        )
        pg_session.commit()

        assert pg_session.query(ResearchRun).count() == 0
        assert pg_session.query(ProgramResultRow).count() == 0
        assert pg_session.query(ClaimRow).count() == 0

    def test_the_dedupe_index_is_unique_per_run(self, pg_session):
        from app.models import ApplicantProfileRow, ProgramResultRow, ResearchRun

        profile = ApplicantProfileRow(display_name="x", payload={})
        pg_session.add(profile)
        pg_session.flush()
        run = ResearchRun(profile_id=profile.id, stage="queued", stage_state={})
        pg_session.add(run)
        pg_session.flush()

        def row():
            return ProgramResultRow(
                run_id=run.id, dedupe_key="same", university="U", university_key="u",
                country="C", program="P", eligibility="MET", admissions_fit="PLAUSIBLE_FIT",
                funding_fit="UNKNOWN", funding_classification="UNKNOWN", payload={},
            )

        pg_session.add(row())
        pg_session.commit()
        pg_session.add(row())
        with pytest.raises(sa.exc.IntegrityError):
            pg_session.commit()
        pg_session.rollback()

    def test_the_migration_is_at_head(self, pg_engine):
        from app.db import head_revision

        with pg_engine.connect() as connection:
            current = connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
        assert current == head_revision()


class TestTimezoneHandling:
    """SQLite has no timezone type, so stored timestamps come back naive.

    Comparing one to an aware `now()` raises TypeError. It reached the run
    endpoint as an intermittent 500 while a worker was writing.
    """

    def test_a_naive_timestamp_is_treated_as_utc(self):
        from app.models.base import ensure_utc

        # A fixed past date: using "today" would depend on the clock's hour.
        naive = datetime(2020, 1, 1, 12, 0, 0)
        assert ensure_utc(naive).tzinfo is UTC
        assert ensure_utc(naive) < datetime.now(UTC), "comparison must not raise"

    def test_an_aware_timestamp_is_left_alone(self):
        from app.models.base import ensure_utc

        aware = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert ensure_utc(aware) is aware

    def test_none_stays_none(self):
        from app.models.base import ensure_utc

        assert ensure_utc(None) is None

    def test_the_run_view_survives_a_naive_lease_timestamp(self, settings, profile, tmp_path):
        """The exact shape of the 500: a naive lease read back from SQLite."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.api.routes_research import _view
        from app.db import migrate_to_head
        from app.jobs.store import JobStore
        from app.models import ApplicantProfileRow, Job, ResearchRun

        url = f"sqlite:///{tmp_path / 'naive.db'}"
        migrate_to_head(url)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        session = sessionmaker(bind=engine, future=True)()
        try:
            row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
            session.add(row)
            session.flush()
            run = ResearchRun(profile_id=row.id, stage="funding_discovery", stage_state={})
            session.add(run)
            session.flush()
            job_id = JobStore(session).enqueue("research", run_id=run.id).job_id
            session.commit()
            JobStore(session).claim(worker_id="w")
            session.commit()

            session.expire_all()
            stored = session.get(Job, job_id)
            assert stored.lease_expires_at.tzinfo is None, "SQLite returns naive datetimes"

            view = _view(session, run)  # used to raise TypeError
            assert view.job_running is True
            assert view.stale is False
        finally:
            session.close()
            engine.dispose()
