"""The worker loop.

The store's semantics are covered in test_jobs.py; these cover the process that
drives it — claiming, beating, dispatching, graceful shutdown and the schema
wait. The crash path itself is covered end to end by scripts/crash_test.py,
which kills a real process.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.jobs.store import JobStore
from app.jobs.worker import Worker, reconcile_startup, wait_for_schema
from app.models import ApplicantProfileRow, Job, JobStatus, ResearchRun
from app.pipeline.state import RunState


@pytest.fixture
def bound_db(settings, monkeypatch):
    """Point app.db at a migrated throwaway database for this test."""
    import app.db as db_module
    from app.db import migrate_to_head

    migrate_to_head(settings.database_url)
    engine = sa.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    factory = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", factory)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    try:
        yield factory
    finally:
        engine.dispose()


def seed_run(factory, profile, **run_kwargs) -> tuple[str, str]:
    """A profile, a run and a queued job. Returns (run_id, job_id)."""
    with factory() as session:
        row = ApplicantProfileRow(
            display_name="t", payload=profile.model_dump(mode="json")
        )
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id, stage="queued", demo_mode=True,
            candidate_limit=run_kwargs.pop("candidate_limit", 3),
            verify_limit=run_kwargs.pop("verify_limit", 3),
            stage_state=RunState.load(None).dump(), **run_kwargs,
        )
        session.add(run)
        session.flush()
        job_id = JobStore(session).enqueue("research", run_id=run.id).job_id
        session.commit()
        return run.id, job_id


class TestClaimAndExecute:
    def test_a_worker_claims_and_runs_a_job_to_completion(self, bound_db, settings, profile):
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)

        claimed = worker.claim_one()
        assert claimed == job_id
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            job = session.get(Job, job_id)
            run = session.get(ResearchRun, run_id)
            assert job.status == JobStatus.SUCCEEDED.value
            assert job.worker_id is None
            assert run.stage == "awaiting_user_decision"

    def test_an_empty_queue_yields_nothing(self, bound_db, settings):
        assert Worker(settings).claim_one() is None

    def test_a_job_whose_run_vanished_dies_rather_than_retrying(
        self, bound_db, settings, profile
    ):
        """Retrying work that can never succeed is a slower outage."""
        run_id, job_id = seed_run(bound_db, profile)
        with bound_db() as session:
            session.execute(sa.text("DELETE FROM research_runs WHERE id = :i"), {"i": run_id})
            session.commit()

        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            job = session.get(Job, job_id)
            assert job.status == JobStatus.DEAD.value
            assert "no longer exists" in job.last_error

    def test_an_unknown_job_kind_dies_rather_than_retrying(self, bound_db, settings, profile):
        run_id, _ = seed_run(bound_db, profile)
        with bound_db() as session:
            job_id = JobStore(session).enqueue("nonsense", run_id=run_id).job_id
            session.commit()

        worker = Worker(settings)
        while worker.claim_one() != job_id:
            pass
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            job = session.get(Job, job_id)
            assert job.status == JobStatus.DEAD.value
            assert "unknown job kind" in job.last_error

    def test_a_cancelled_job_stops_and_is_marked_cancelled(self, bound_db, settings, profile):
        """Not "succeeded" — the run did not finish — and not "dead" either,
        which means attempts were exhausted and a human must look."""
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        with bound_db() as session:
            JobStore(session).cancel(job_id)
            session.commit()

        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            job = session.get(Job, job_id)
            run = session.get(ResearchRun, run_id)
            assert job.status == JobStatus.CANCELLED.value
            assert "cancelled" in job.last_error.lower()
            assert run.stage == "cancelled"

    def test_a_cancelled_run_never_reports_success(self, bound_db, settings, profile):
        """The defect this guards: the runner swallowed the cancellation, so the
        worker saw a clean return and completed the job."""
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        with bound_db() as session:
            session.get(ResearchRun, run_id).cancelled = True
            session.commit()

        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            assert session.get(Job, job_id).status != JobStatus.SUCCEEDED.value


class TestReaping:
    def test_the_worker_reaps_an_expired_lease(self, bound_db, settings, profile):
        _, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()

        with bound_db() as session:
            session.execute(
                sa.update(Job).where(Job.id == job_id)
                .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
            session.commit()

        assert worker.reap() == [job_id]
        with bound_db() as session:
            assert session.get(Job, job_id).status == JobStatus.QUEUED.value


class TestReconciliation:
    def test_a_run_with_no_job_is_recovered(self, bound_db, settings, profile):
        with bound_db() as session:
            row = ApplicantProfileRow(
                display_name="t", payload=profile.model_dump(mode="json")
            )
            session.add(row)
            session.flush()
            run = ResearchRun(profile_id=row.id, stage="assessment", stage_state={})
            session.add(run)
            session.commit()
            run_id = run.id

        assert reconcile_startup()["runs_recovered"] == 1
        with bound_db() as session:
            assert session.get(ResearchRun, run_id).stage == "retryable_failed"

    def test_a_run_awaiting_a_decision_is_not_recovered(self, bound_db, settings, profile):
        """Waiting on the user is not stranded work, however long it waits."""
        with bound_db() as session:
            row = ApplicantProfileRow(
                display_name="t", payload=profile.model_dump(mode="json")
            )
            session.add(row)
            session.flush()
            run = ResearchRun(
                profile_id=row.id, stage="awaiting_user_decision", stage_state={}
            )
            session.add(run)
            session.commit()
            run_id = run.id

        assert reconcile_startup()["runs_recovered"] == 0
        with bound_db() as session:
            assert session.get(ResearchRun, run_id).stage == "awaiting_user_decision"


class TestLoopAndShutdown:
    def test_the_loop_drains_the_queue_and_stops_on_request(
        self, bound_db, settings, profile
    ):
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)

        async def drive() -> None:
            task = asyncio.create_task(worker.run_forever())
            for _ in range(400):
                await asyncio.sleep(0.05)
                with bound_db() as session:
                    if session.get(Job, job_id).status == JobStatus.SUCCEEDED.value:
                        break
            worker.request_stop()
            await asyncio.wait_for(task, timeout=30)

        asyncio.run(drive())

        assert worker.jobs_done == 1
        assert worker.jobs_failed == 0
        with bound_db() as session:
            assert session.get(Job, job_id).status == JobStatus.SUCCEEDED.value
            assert session.get(ResearchRun, run_id).stage == "awaiting_user_decision"

    def test_shutdown_is_idempotent(self, settings):
        worker = Worker(settings)
        worker.request_stop()
        worker.request_stop()
        assert worker.stopping.is_set()

    def test_a_worker_with_nothing_to_do_exits_promptly(self, bound_db, settings):
        worker = Worker(settings)

        async def drive() -> None:
            task = asyncio.create_task(worker.run_forever())
            await asyncio.sleep(0.2)
            worker.request_stop()
            await asyncio.wait_for(task, timeout=15)

        asyncio.run(drive())
        assert worker.jobs_done == 0


class TestSchemaWait:
    def test_it_returns_at_once_when_the_schema_is_current(self, bound_db):
        assert wait_for_schema(timeout=5) is True

    def test_it_waits_and_then_gives_up_on_an_unmigrated_database(
        self, tmp_path, monkeypatch
    ):
        """A worker in a rolling deploy may start before the migration job."""
        import app.db as db_module

        engine = sa.create_engine(
            f"sqlite:///{tmp_path / 'empty.db'}", connect_args={"check_same_thread": False}
        )
        monkeypatch.setattr(db_module, "engine", engine)
        assert wait_for_schema(timeout=0.1) is False
