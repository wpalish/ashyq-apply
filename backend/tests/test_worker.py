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
from app.models.base import ensure_utc
from app.pipeline.state import RunState
from tests.conftest import profile_row


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
        row = profile_row(session, profile)
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
            row = profile_row(session, profile)
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
            row = profile_row(session, profile)
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


class TestLeaseFencing:
    """A worker that lost its lease must not speak for the job any more.

    The audited defect: _beat only logged when the lease was gone, and the
    terminal updates had no owner check, so a zombie worker could mark a job
    succeeded that another worker had already taken over - and both of them
    added to the same read-modify-write run counters.
    """

    def test_a_worker_that_lost_the_lease_cannot_complete_the_job(
        self, bound_db, settings, profile
    ):
        _, job_id = seed_run(bound_db, profile)
        with bound_db() as session:
            JobStore(session, worker_id="worker-a").claim(worker_id="worker-a")
            session.commit()

        # A reaper hands the job to someone else while worker-a is still busy.
        with bound_db() as session:
            session.execute(
                sa.text("UPDATE jobs SET worker_id = 'worker-b' WHERE id = :i"), {"i": job_id}
            )
            session.commit()

        with bound_db() as session:
            store = JobStore(session, worker_id="worker-a")
            assert store.complete(job_id) is False
            session.commit()

        with bound_db() as session:
            job = session.get(Job, job_id)
            assert job.status == JobStatus.RUNNING.value, "the new owner still holds it"
            assert job.worker_id == "worker-b"

    def test_a_worker_that_lost_the_lease_cannot_fail_or_cancel_the_job(
        self, bound_db, settings, profile
    ):
        _, job_id = seed_run(bound_db, profile)
        with bound_db() as session:
            JobStore(session, worker_id="worker-a").claim(worker_id="worker-a")
            session.execute(
                sa.text("UPDATE jobs SET worker_id = 'worker-b' WHERE id = :i"), {"i": job_id}
            )
            session.commit()

        with bound_db() as session:
            store = JobStore(session, worker_id="worker-a")
            assert store.fail(job_id, "boom") == JobStatus.RUNNING.value
            store.mark_cancelled(job_id)
            session.commit()

        with bound_db() as session:
            job = session.get(Job, job_id)
            assert job.status == JobStatus.RUNNING.value
            assert job.worker_id == "worker-b"
            assert job.last_error == ""

    def test_heartbeat_fails_once_the_job_belongs_to_someone_else(
        self, bound_db, settings, profile
    ):
        _, job_id = seed_run(bound_db, profile)
        with bound_db() as session:
            store = JobStore(session, worker_id="worker-a")
            store.claim(worker_id="worker-a")
            session.commit()
            assert store.heartbeat(job_id) is True

        with bound_db() as session:
            session.execute(
                sa.text("UPDATE jobs SET worker_id = 'worker-b' WHERE id = :i"), {"i": job_id}
            )
            session.commit()

        with bound_db() as session:
            assert JobStore(session, worker_id="worker-a").heartbeat(job_id) is False

    def test_a_run_stops_when_its_job_is_taken_away(self, bound_db, settings, profile):
        """The worker must abort the work itself, not merely log the loss."""
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        assert worker.claim_one() == job_id

        with bound_db() as session:
            session.execute(
                sa.text("UPDATE jobs SET worker_id = 'someone-else' WHERE id = :i"), {"i": job_id}
            )
            session.commit()

        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            job = session.get(Job, job_id)
            run = session.get(ResearchRun, run_id)
            # Untouched by the worker that no longer owns it.
            assert job.worker_id == "someone-else"
            assert job.status == JobStatus.RUNNING.value
            assert run.stage != "awaiting_user_decision", "the abandoned run must not finish"


class TestEnqueueTransaction:
    def test_a_racing_enqueue_leaves_the_caller_s_own_work_alone(
        self, bound_db, settings, profile, monkeypatch
    ):
        """enqueue used to rollback() the caller's whole session on a race.

        In collect_documents that silently discarded run.cancelled = False and
        the audit event written in the same transaction. Here the pre-check is
        forced to miss, so the insert hits the unique constraint - the path a
        second concurrent request really takes.
        """
        from sqlalchemy.orm import Session as OrmSession

        run_id, _ = seed_run(bound_db, profile)
        with bound_db() as session:
            JobStore(session).enqueue("documents", run_id=run_id, idempotency_key="shared")
            session.commit()

        original_scalar = OrmSession.scalar
        seen = {"n": 0}

        def blind_first_precheck(self, statement, *args, **kwargs):
            seen["n"] += 1
            if seen["n"] == 1:
                return None  # the winner committed after we looked
            return original_scalar(self, statement, *args, **kwargs)

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            run.cancelled = True  # the caller's own pending change
            session.add(run)

            monkeypatch.setattr(OrmSession, "scalar", blind_first_precheck)
            result = JobStore(session).enqueue(
                "documents", run_id=run_id, idempotency_key="shared"
            )
            monkeypatch.undo()

            assert result.created is False
            assert "concurrently" in result.reason
            session.commit()

        with bound_db() as session:
            assert session.get(ResearchRun, run_id).cancelled is True
            assert session.query(Job).filter(Job.idempotency_key == "shared").count() == 1


class TestLeaseConfiguration:
    """`job_lease_seconds` is configurable, so nothing may assume 120."""

    def test_the_expiry_check_follows_the_configured_lease(self, settings, monkeypatch):
        from datetime import timedelta

        from app.pipeline.state import is_lease_expired

        monkeypatch.setattr("app.config.get_settings", lambda: settings)
        settings.job_lease_seconds = 600
        beat = datetime.now(UTC) - timedelta(seconds=300)
        assert not is_lease_expired("funding_discovery", beat), (
            "a 300s silence is fine when the lease is 600s"
        )

        settings.job_lease_seconds = 60
        assert is_lease_expired("funding_discovery", beat)

    def test_the_api_reports_stale_using_the_configured_lease(
        self, bound_db, settings, profile, monkeypatch
    ):
        """The run view used a hardcoded 120s while the worker used the setting."""
        from datetime import timedelta

        import app.api.routes_research as routes_research
        from app.api.routes_research import _view

        monkeypatch.setattr(routes_research, "get_settings", lambda: settings)
        settings.job_lease_seconds = 30
        run_id, _ = seed_run(bound_db, profile)
        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            run.stage = "program_verification"
            run.heartbeat_at = datetime.now(UTC) - timedelta(seconds=60)
            session.commit()

        with bound_db() as session:
            view = _view(session, session.get(ResearchRun, run_id))
            assert view.stale is True, "60s of silence exceeds a 30s lease"


class TestHeartbeatCadence:
    def test_every_verified_candidate_refreshes_the_heartbeat(
        self, bound_db, settings, profile, monkeypatch
    ):
        """A healthy run was flagged stale because verification beat once per
        four candidates, which in live mode can outlast the whole lease."""
        beats: list[str] = []
        original = ResearchRun.__setattr__

        def record(self, name, value):
            if name == "heartbeat_at" and value is not None:
                beats.append(self.stage)
            original(self, name, value)

        run_id, job_id = seed_run(bound_db, profile, candidate_limit=8, verify_limit=8)
        monkeypatch.setattr(ResearchRun, "__setattr__", record)
        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))
        monkeypatch.undo()

        with bound_db() as session:
            verified = session.get(ResearchRun, run_id).programs_verified
        during_verification = [s for s in beats if s == "program_verification"]
        assert verified >= 8, f"the corpus must supply enough candidates (got {verified})"
        assert len(during_verification) >= verified, (
            f"only {len(during_verification)} heartbeats while verifying {verified} programmes"
        )


class TestFreshnessRecheck:
    """POSSIBLY_STALE claims used to stay stale for ever.

    `next_recheck_at` existed but was computed only in tests: nothing ever
    went back to re-read a page whose evidence had aged out.
    """

    def test_a_finished_run_queues_its_own_next_look(self, bound_db, settings, profile):
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            assert run.next_recheck_at is not None, "the run must know when its evidence ages out"
            recheck = (
                session.query(Job)
                .filter(Job.run_id == run_id, Job.kind == "recheck")
                .one()
            )
            assert recheck.status == JobStatus.QUEUED.value
            # Queued for the date the evidence expires, not for now.
            assert ensure_utc(recheck.available_at) == ensure_utc(run.next_recheck_at)
            assert ensure_utc(recheck.available_at) > datetime.now(UTC)

    def test_a_recheck_with_nothing_stale_does_no_work_and_re_arms(
        self, bound_db, settings, profile
    ):
        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            recheck_id = (
                session.query(Job).filter(Job.run_id == run_id, Job.kind == "recheck").one().id
            )
            # Pull it forward, as the queue would once the date arrives.
            session.execute(
                sa.update(Job).where(Job.id == recheck_id).values(available_at=datetime.now(UTC))
            )
            before = session.get(ResearchRun, run_id).pages_checked
            session.commit()

        assert worker.claim_one() == recheck_id
        asyncio.run(worker.execute(recheck_id))

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            assert session.get(Job, recheck_id).status == JobStatus.SUCCEEDED.value
            assert run.pages_checked == before, "nothing was stale, so nothing was re-read"
            assert run.stage == "awaiting_user_decision"

    def test_a_stale_claim_is_re_read_and_decisions_survive(
        self, bound_db, settings, profile
    ):
        from app.models import ClaimRow, ProgramResultRow

        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            row = (
                session.query(ProgramResultRow)
                .filter(ProgramResultRow.run_id == run_id)
                .first()
            )
            row.user_decision = "approved"
            row.user_decision_reason = "best funded"
            payload = dict(row.payload)
            payload["user_decision"] = "approved"
            payload["user_decision_reason"] = "best funded"
            row.payload = payload
            decided_id = row.id
            # Age every claim well past its window.
            session.execute(
                sa.update(ClaimRow)
                .where(ClaimRow.run_id == run_id)
                .values(accessed_at=datetime.now(UTC) - timedelta(days=900))
            )
            recheck_id = (
                session.query(Job).filter(Job.run_id == run_id, Job.kind == "recheck").one().id
            )
            session.execute(
                sa.update(Job).where(Job.id == recheck_id).values(available_at=datetime.now(UTC))
            )
            session.commit()

        assert worker.claim_one() == recheck_id
        asyncio.run(worker.execute(recheck_id))

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            assert run.stage == "awaiting_user_decision"
            fresh = session.get(ProgramResultRow, decided_id)
            assert fresh.user_decision == "approved", "a recheck must not discard decisions"
            assert fresh.user_decision_reason == "best funded"
            newest = max(
                ensure_utc(c.accessed_at)
                for c in session.query(ClaimRow).filter(ClaimRow.run_id == run_id)
            )
            assert newest > datetime.now(UTC) - timedelta(minutes=5), "evidence was re-read"


class TestProgressCounters:
    def test_progress_counts_programmes_on_both_sides_of_the_ratio(
        self, bound_db, settings, profile
    ):
        """items_done counted candidates while programs_verified counted
        programmes, so the screen showed two numbers for the same work."""
        run_id, job_id = seed_run(bound_db, profile, candidate_limit=6, verify_limit=6)
        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            verification = RunState.load(run.stage_state).stages["program_verification"]
            assert verification.items_done == run.programs_verified
            assert verification.items_total >= verification.items_done
            assert verification.items_done > 0

    def test_counters_survive_an_interrupted_run(self, bound_db, settings, profile):
        """A run stopped mid-flight must not report more done than it has."""
        from app.models import ProgramResultRow

        run_id, job_id = seed_run(bound_db, profile, candidate_limit=6, verify_limit=6)
        worker = Worker(settings)
        worker.claim_one()

        with bound_db() as session:
            session.get(ResearchRun, run_id).cancelled = True
            session.commit()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            rows = (
                session.query(ProgramResultRow)
                .filter(ProgramResultRow.run_id == run_id)
                .count()
            )
            verification = RunState.load(run.stage_state).stages["program_verification"]
            assert run.programs_verified == rows
            assert verification.items_done <= verification.items_total
