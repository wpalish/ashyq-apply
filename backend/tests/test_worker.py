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
from app.models import Job, JobStatus, ResearchRun
from app.models.base import ensure_utc
from app.pipeline.state import RunState
from tests.conftest import profile_row


@pytest.fixture
def bound_db(settings, monkeypatch):
    """Point app.db at a migrated throwaway database for this test."""
    import app.db as db_module
    from app.db import migrate_to_head

    migrate_to_head(settings.database_url)
    engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
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
            profile_id=row.id,
            stage="queued",
            demo_mode=True,
            candidate_limit=run_kwargs.pop("candidate_limit", 3),
            verify_limit=run_kwargs.pop("verify_limit", 3),
            stage_state=RunState.load(None).dump(),
            **run_kwargs,
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

    def test_a_job_whose_run_vanished_dies_rather_than_retrying(self, bound_db, settings, profile):
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
                sa.update(Job)
                .where(Job.id == job_id)
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
            run = ResearchRun(profile_id=row.id, stage="awaiting_user_decision", stage_state={})
            session.add(run)
            session.commit()
            run_id = run.id

        assert reconcile_startup()["runs_recovered"] == 0
        with bound_db() as session:
            assert session.get(ResearchRun, run_id).stage == "awaiting_user_decision"


class TestLoopAndShutdown:
    def test_the_loop_drains_the_queue_and_stops_on_request(self, bound_db, settings, profile):
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

    def test_it_waits_and_then_gives_up_on_an_unmigrated_database(self, tmp_path, monkeypatch):
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
            result = JobStore(session).enqueue("documents", run_id=run_id, idempotency_key="shared")
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
            recheck = session.query(Job).filter(Job.run_id == run_id, Job.kind == "recheck").one()
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

    def test_a_stale_claim_is_re_read_and_decisions_survive(self, bound_db, settings, profile):
        from app.models import ClaimRow, ProgramResultRow

        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            row = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).first()
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
            rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).count()
            verification = RunState.load(run.stage_state).stages["program_verification"]
            assert run.programs_verified == rows
            assert verification.items_done <= verification.items_total


# ---------------------------------------------------------------------------
# J02: fenced writes after lease loss.
#
# Two layers of RED are recorded against the baseline:
#   * assertion-level — the stale attempt really corrupts state today: the
#     runner's ``except Exception`` writes a terminal run state out of the
#     LeaseLost handler, the dispatch commit writes a ``job_completed`` audit
#     for a job the worker no longer owns, and checkpoints discard the
#     stage's pending counter increments. Those tests use only the existing
#     signatures.
#   * contract-field-level — the two-session PostgreSQL proofs pass
#     ``lease_token=``, the attempt token the frozen planner contract
#     specifies (the job's ``attempts`` value at claim time). The baseline
#     signatures do not accept it yet, so those tests fail with TypeError
#     until the fence exists. The worker_id-only fence cannot express these
#     scenarios at all: where both attempts share one worker_id, nothing but
#     the attempt token can tell them apart.
# ---------------------------------------------------------------------------


@pytest.fixture
def pg_factory(pg_engine):
    """Independent sessions off one migrated PostgreSQL database.

    The fencing proofs need two sessions that share nothing — no transaction,
    no identity map: one claims, the other takes the job away, which is how
    the reaper and a rival worker meet in production. A single session would
    hide the very race it is supposed to expose.
    """
    return sessionmaker(bind=pg_engine, future=True)


def _expire_lease_and_reap(factory, job_id: str) -> None:
    """Age the lease past its horizon and let the reaper take the job back."""
    with factory() as session:
        session.execute(
            sa.update(Job)
            .where(Job.id == job_id)
            .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        session.commit()
        assert JobStore(session).reap_expired() == [job_id]
        # The reaper queues the job with backoff; pull that forward the way the
        # queue itself would once the backoff elapsed.
        session.execute(
            sa.update(Job).where(Job.id == job_id).values(available_at=datetime.now(UTC))
        )
        session.commit()


class TestStaleWorkerRunState:
    """Losing the lease is control flow, not a run failure.

    runner.run_to_decision's ``except Exception`` cannot tell a LeaseLost from
    a real stage failure, so the stale attempt used to write stage=failed, a
    run error and a run_failed audit over the run another worker is redoing.
    test_a_run_stops_when_its_job_is_taken_away only asserts the run did not
    finish — a "failed" stage satisfies it, which is why the defect survived.
    """

    def test_a_mid_run_takeover_does_not_write_terminal_run_state(
        self, bound_db, settings, profile, monkeypatch
    ):
        from app.models import AuditEvent, ProgramResultRow
        from app.pipeline.runner import ResearchRunner

        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        assert worker.claim_one() == job_id

        checkpoint: dict = {}
        original_verify = ResearchRunner._stage_verify

        async def verify_then_takeover(self, fetcher):
            await original_verify(self, fetcher)
            # Another worker takes the job over mid-run; the next checkpoint
            # must end this attempt as pure control flow.
            with bound_db() as other:
                other.execute(
                    sa.text("UPDATE jobs SET worker_id = 'worker-b' WHERE id = :i"),
                    {"i": job_id},
                )
                other.commit()
            # Everything this attempt legitimately committed so far.
            with bound_db() as other:
                run = other.get(ResearchRun, run_id)
                checkpoint["stage"] = run.stage
                checkpoint["errors"] = list(run.errors or [])
                checkpoint["results"] = (
                    other.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).count()
                )

        monkeypatch.setattr(ResearchRunner, "_stage_verify", verify_then_takeover)
        asyncio.run(worker.execute(job_id))

        assert checkpoint["results"] > 0, "the corpus must verify enough to commit artifacts"
        assert worker.jobs_failed == 0, "the attempt must exit through the LeaseLost branch"
        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            job = session.get(Job, job_id)
            # The stale attempt leaves the run exactly as it last committed it.
            assert run.stage == checkpoint["stage"], (
                f"a lost lease must not rewrite the run's stage (it became {run.stage!r})"
            )
            assert run.errors == checkpoint["errors"], "a lost lease is not a run error"
            assert run.finished_at is None
            audits = (
                session.query(AuditEvent)
                .filter(AuditEvent.entity_id == run_id, AuditEvent.action == "run_failed")
                .count()
            )
            assert audits == 0, "the stale attempt must not audit run_failed"
            # Work committed before the lease was lost survives untouched.
            results = (
                session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).count()
            )
            assert results == checkpoint["results"]
            # And the job itself stays with its new owner.
            assert job.status == JobStatus.RUNNING.value
            assert job.worker_id == "worker-b"


class TestCheckpointKeepsPendingCounters:
    """A checkpoint must observe cancellation, not destroy progress.

    _check_cancelled used to session.refresh(self.run), which silently
    discarded the stage's uncommitted counter increments. In _stage_funding a
    _save lands only every fourth row, so the increments of the rows in
    between were lost at the very checkpoints meant to protect the run.
    """

    def test_pending_counter_increments_survive_a_checkpoint(self, bound_db, settings, profile):
        from app.models import ApplicantProfileRow
        from app.pipeline.runner import ResearchRunner
        from app.schemas.profile import ApplicantProfileIn

        run_id, job_id = seed_run(bound_db, profile)
        worker = Worker(settings)
        assert worker.claim_one() == job_id

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            profile_payload = session.get(ApplicantProfileRow, run.profile_id).payload
            runner = ResearchRunner(
                session,
                run,
                ApplicantProfileIn.model_validate(profile_payload),
                settings,
                job_id=job_id,
                worker_id=worker.worker_id,
            )
            session.commit()  # the previous save boundary
            # The long stage moves its counters on...
            runner.run.pages_checked += 7
            runner.run.claims_recorded += 3
            # ...and reaches the next checkpoint uncancelled.
            runner._check_cancelled()
            runner._save()

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            assert run.pages_checked == 7, "the checkpoint discarded pending increments"
            assert run.claims_recorded == 3


class TestFencedWritesTwoSessionPostgreSQL:
    """Two independent PostgreSQL sessions: a stale attempt must not be able
    to speak for a job it no longer owns.

    Written against the frozen planner contract:
      * the lease token is the job's ``attempts`` value at claim time, read
        off the job claim() returns;
      * the fenced methods (``complete``, ``heartbeat``, ``fail``,
        ``mark_cancelled``) take an optional ``lease_token`` keyword;
      * a fenced write updates zero rows: no status, no last_error, no
        finished_at, no worker_id change, and the caller's session is left
        with nothing to commit.
    """

    def test_same_worker_reclaim_fences_the_first_attempt(self, pg_factory, profile):
        """worker_concurrency=2 plus the self-reap loop: one worker can hold
        two attempts of the same job under an identical worker_id. Only the
        attempt token can tell the stale one from the live one."""
        run_id, job_id = seed_run(pg_factory, profile)

        s1 = pg_factory()
        try:
            store1 = JobStore(s1, worker_id="w")
            job1 = store1.claim(worker_id="w")
            s1.commit()
            t1 = job1.attempts

            # The lease expires and the worker's own reap loop takes the job
            # back; the very same worker_id immediately re-claims it.
            _expire_lease_and_reap(pg_factory, job_id)
            s2 = pg_factory()
            try:
                store2 = JobStore(s2, worker_id="w")
                job2 = store2.claim(worker_id="w")
                s2.commit()
                assert job2.id == job_id
                assert job2.attempts == t1 + 1
                t2 = job2.attempts
                # The reaper's note is the last legitimate write; nothing the
                # stale attempt does may change it.
                reap_note = job2.last_error

                # Attempt 1's writes are refused even though the worker_id
                # matches on every row it touches.
                assert store1.complete(job_id, lease_token=t1) is False
                assert store1.heartbeat(job_id, lease_token=t1) is False
                assert store1.fail(job_id, "stale attempt 1", lease_token=t1) == (
                    JobStatus.RUNNING.value
                )
                store1.mark_cancelled(job_id, "stale attempt 1", lease_token=t1)
                s1.commit()

                with pg_factory() as check:
                    job = check.get(Job, job_id)
                    assert job.status == JobStatus.RUNNING.value
                    assert job.attempts == t2, "the stale attempt must not move the counter"
                    assert job.last_error == reap_note, "a fenced fail must not write last_error"
                    assert job.finished_at is None

                # The second attempt owns the outcome.
                assert store2.complete(job_id, lease_token=t2) is True
                s2.commit()
                with pg_factory() as check:
                    assert check.get(Job, job_id).status == JobStatus.SUCCEEDED.value
            finally:
                s2.close()
        finally:
            s1.close()

    def test_a_takeover_leaves_the_outcome_to_the_new_owner(self, pg_factory, profile):
        """The reaper hands the job to worker-b; worker-a's complete, fail and
        mark_cancelled must all be refused, and worker-b's must stand."""
        run_id, job_id = seed_run(pg_factory, profile)

        s1 = pg_factory()
        s2 = pg_factory()
        try:
            job1 = JobStore(s1, worker_id="worker-a").claim(worker_id="worker-a")
            s1.commit()
            t1 = job1.attempts

            _expire_lease_and_reap(pg_factory, job_id)
            job2 = JobStore(s2, worker_id="worker-b").claim(worker_id="worker-b")
            s2.commit()
            t2 = job2.attempts
            reap_note = job2.last_error

            assert JobStore(s1, worker_id="worker-a").complete(job_id, lease_token=t1) is False
            assert (
                JobStore(s1, worker_id="worker-a").fail(
                    job_id, "worker-a reports failure", lease_token=t1
                )
                == JobStatus.RUNNING.value
            )
            JobStore(s1, worker_id="worker-a").mark_cancelled(
                job_id, "worker-a cancels", lease_token=t1
            )
            s1.commit()

            with pg_factory() as check:
                job = check.get(Job, job_id)
                assert job.status == JobStatus.RUNNING.value, "worker-b still owns the job"
                assert job.worker_id == "worker-b"
                assert job.last_error == reap_note, "a fenced fail must not write last_error"
                assert job.finished_at is None

            assert JobStore(s2, worker_id="worker-b").complete(job_id, lease_token=t2) is True
            s2.commit()
            with pg_factory() as check:
                assert check.get(Job, job_id).status == JobStatus.SUCCEEDED.value
        finally:
            s1.close()
            s2.close()

    def test_a_renewed_lease_survives_the_reaper(self, pg_factory, profile):
        """A heartbeat the owner just extended is not the reaper's to take."""
        run_id, job_id = seed_run(pg_factory, profile)

        s1 = pg_factory()
        try:
            store1 = JobStore(s1, worker_id="worker-a")
            job1 = store1.claim(worker_id="worker-a")
            s1.commit()
            assert store1.heartbeat(job_id, lease_token=job1.attempts) is True
            s1.commit()

            with pg_factory() as reaper:
                assert JobStore(reaper).reap_expired() == []
            with pg_factory() as check:
                job = check.get(Job, job_id)
                assert job.status == JobStatus.RUNNING.value
                assert job.attempts == 1, "a healthy lease must not be re-claimed"
                assert job.heartbeat_at is not None
        finally:
            s1.close()

    def test_a_finished_reap_refuses_the_dead_worker_s_heartbeat(self, pg_factory, profile):
        """Once the reap dead-letters the job, the dead worker's beat must not
        resurrect a lease."""
        run_id, job_id = seed_run(pg_factory, profile)

        s1 = pg_factory()
        try:
            store1 = JobStore(s1, worker_id="worker-a")
            job1 = store1.claim(worker_id="worker-a")
            s1.commit()
            t1 = job1.attempts

            # Attempts exhausted: the reap dead-letters instead of requeueing.
            with pg_factory() as session:
                session.execute(
                    sa.update(Job)
                    .where(Job.id == job_id)
                    .values(
                        max_attempts=1,
                        lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
                    )
                )
                session.commit()
                assert JobStore(session).reap_expired() == [job_id]
                session.commit()
            with pg_factory() as check:
                assert check.get(Job, job_id).status == JobStatus.DEAD.value

            assert store1.heartbeat(job_id, lease_token=t1) is False
            s1.commit()
            with pg_factory() as check:
                job = check.get(Job, job_id)
                assert job.status == JobStatus.DEAD.value
                assert job.lease_expires_at is None
        finally:
            s1.close()

    def test_fenced_terminal_writes_change_nothing(self, pg_factory, profile):
        """A fenced complete or fail is zero rows: no status, no finished_at,
        no last_error — there is nothing for the caller's commit to carry."""
        run_id, job_id = seed_run(pg_factory, profile)

        s1 = pg_factory()
        try:
            job1 = JobStore(s1, worker_id="worker-a").claim(worker_id="worker-a")
            s1.commit()
            t1 = job1.attempts

            # A direct handover keeps last_error empty, so the assertion on it
            # is sharp: the fenced writes must not be the first to fill it.
            with pg_factory() as session:
                session.execute(
                    sa.text("UPDATE jobs SET worker_id = 'worker-b' WHERE id = :i"),
                    {"i": job_id},
                )
                session.commit()
            with pg_factory() as check:
                assert check.get(Job, job_id).worker_id == "worker-b"

            assert JobStore(s1, worker_id="worker-a").complete(job_id, lease_token=t1) is False
            s1.commit()
            assert (
                JobStore(s1, worker_id="worker-a").fail(
                    job_id, "a failure nobody owns any more", lease_token=t1
                )
                == JobStatus.RUNNING.value
            )
            s1.commit()
            JobStore(s1, worker_id="worker-a").mark_cancelled(
                job_id, "a cancellation nobody owns any more", lease_token=t1
            )
            s1.commit()

            with pg_factory() as check:
                job = check.get(Job, job_id)
                assert job.status == JobStatus.RUNNING.value
                assert job.worker_id == "worker-b"
                assert job.last_error == "", "a fenced fail must not write last_error"
                assert job.finished_at is None
        finally:
            s1.close()


class TestStaleDispatchCommit:
    """The dispatch completion commit belongs to the owner alone.

    worker._dispatch used to ignore store.complete()'s False and commit the
    job_completed audit anyway, so a worker that lost its job after its last
    checkpoint still stamped the trail as if it had finished it.
    """

    def test_a_stale_worker_writes_no_completion_audit(
        self, pg_engine, pg_factory, settings, profile, monkeypatch
    ):
        import app.db as db_module
        from app.models import AuditEvent
        from app.pipeline.runner import ResearchRunner

        run_id, job_id = seed_run(pg_factory, profile)

        # worker-a claims, then loses the job to worker-b through the reaper.
        with pg_factory() as session:
            JobStore(session, worker_id="worker-a").claim(worker_id="worker-a")
            session.commit()
        _expire_lease_and_reap(pg_factory, job_id)
        with pg_factory() as session:
            job = JobStore(session, worker_id="worker-b").claim(worker_id="worker-b")
            assert job.attempts == 2
            session.commit()

        # The takeover lands after the runner's last checkpoint: from the
        # stale worker's view the run finished cleanly, and _dispatch walks
        # straight into its completion commit.
        async def already_finished(self):
            return None

        monkeypatch.setattr(ResearchRunner, "run_to_decision", already_finished)
        monkeypatch.setattr(db_module, "engine", pg_engine)
        monkeypatch.setattr(db_module, "SessionLocal", pg_factory)
        monkeypatch.setattr("app.config.get_settings", lambda: settings)

        worker = Worker(settings, worker_id="worker-a")
        asyncio.run(worker.execute(job_id))

        with pg_factory() as check:
            job = check.get(Job, job_id)
            assert job.status == JobStatus.RUNNING.value, "worker-b still owns the job"
            assert job.worker_id == "worker-b"
            audits = (
                check.query(AuditEvent)
                .filter(AuditEvent.entity_id == job_id, AuditEvent.action == "job_completed")
                .count()
            )
            assert audits == 0, "the stale worker must not record job_completed"
            assert check.get(ResearchRun, run_id).stage == "queued", (
                "the stale dispatch must not move the run"
            )

    def test_a_stale_payment_poll_rolls_back_its_provider_journal(
        self, pg_engine, pg_factory, settings, profile, monkeypatch
    ):
        """A provider answer and the fenced queue transition are one commit.

        Payment reconciliation writes an append-only PaymentEvent even when a
        provider still says "pending".  If the lease changes owner during the
        provider call, that journal entry belongs to the stale attempt and must
        be rolled back with every other payment-side write.
        """
        import app.db as db_module
        from app.jobs import payment_reconcile
        from app.models.billing import Order, OrderStatus, PaymentEvent
        from app.payments.provider import ProviderInvoice

        with pg_factory() as session:
            row = profile_row(session, profile)
            order = Order(
                organization_id=row.organization_id,
                profile_id=row.id,
                amount_kzt=4990,
                status=OrderStatus.PENDING.value,
                provider="fake",
                provider_invoice_id="invoice-stale-poll",
                external_order_id="order-stale-poll",
                method="phone",
                phone_masked="8707***4455",
            )
            session.add(order)
            session.flush()
            order_id = order.id
            job_id = (
                JobStore(session)
                .enqueue(
                    "payment_reconcile",
                    payload={"order_id": order_id},
                    idempotency_key=f"payment_reconcile:{order_id}",
                    max_attempts=30,
                )
                .job_id
            )
            session.commit()

        monkeypatch.setattr(db_module, "engine", pg_engine)
        monkeypatch.setattr(db_module, "SessionLocal", pg_factory)
        monkeypatch.setattr("app.config.get_settings", lambda: settings)

        class TakeoverDuringPoll:
            def get_invoice(self, invoice_id: str) -> ProviderInvoice:
                assert invoice_id == "invoice-stale-poll"
                with pg_factory() as other:
                    other.execute(
                        sa.update(Job)
                        .where(Job.id == job_id)
                        .values(worker_id="worker-b", attempts=Job.attempts + 1)
                    )
                    other.commit()
                return ProviderInvoice(invoice_id=invoice_id, status="processing")

        monkeypatch.setattr(payment_reconcile, "get_provider", TakeoverDuringPoll)

        worker = Worker(settings, worker_id="worker-a")
        assert worker.claim_one() == job_id
        asyncio.run(worker.execute(job_id))

        with pg_factory() as check:
            job = check.get(Job, job_id)
            order = check.get(Order, order_id)
            assert job.status == JobStatus.RUNNING.value
            assert job.worker_id == "worker-b"
            assert job.attempts == 2
            assert order.status == OrderStatus.PENDING.value
            assert (
                check.query(PaymentEvent).filter(PaymentEvent.order_id == order_id).count() == 0
            ), "a stale payment attempt committed its provider journal"
