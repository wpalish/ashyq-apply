"""A worker must stop working the moment the job stops being its own.

`test_job_lease_fencing.py` proves the *store* refuses a stale holder's writes.
That is necessary and not sufficient: refusing the write at the end still lets
the stalled worker run the entire job — fetching, extracting, and writing
decision rows keyed on the run rather than on the job — while another worker
runs the same job alongside it. Two pipelines, one run.

The heartbeat is the only thing that finds out early. It used to notice, log
"lost the lease on job …", and return, leaving the work it was beating for
running. These tests pin down that losing the lease stops the work.
"""
from __future__ import annotations

import asyncio
import gc
import time

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.jobs.store import JobStore
from app.jobs.worker import Worker, liveness_path
from app.models import ApplicantProfileRow, Job, JobStatus, ResearchRun
from app.models.base import ensure_utc
from app.pipeline.state import RunState

#: Long enough that the beat runs at its 1.0s floor, short enough that a test
#: waiting two beats is still a fast test.
LEASE_SECONDS = 3
#: A dispatch that is never stopped runs for this long. Any assertion that the
#: work stopped has to be well under it, or it is only measuring the test's own
#: patience.
UNSTOPPED_DISPATCH_SECONDS = 30
#: Two beats plus slack. Losing the lease must stop the work inside this.
STOP_WITHIN_SECONDS = 5


@pytest.fixture
def bound_db(settings, monkeypatch):
    import app.db as db_module
    from app.db import migrate_to_head

    settings.job_lease_seconds = LEASE_SECONDS
    settings.worker_poll_seconds = 0.05
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


def seed_job(factory, profile) -> str:
    with factory() as session:
        row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id, stage="queued", demo_mode=True,
            candidate_limit=1, verify_limit=1, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        job_id = JobStore(session).enqueue("research", run_id=run.id).job_id
        session.commit()
        return job_id


class Dispatch:
    """A stand-in for the pipeline that can be held open and watched.

    The real dispatch is the whole research run. What matters here is only
    whether it is still running after the lease is gone, so the smallest thing
    that can answer that is the right one.
    """

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = False
        self.completed = False

    # No `self`-as-worker parameter: a plain instance set on the class is not
    # a descriptor, so `worker._dispatch(...)` calls this with the arguments
    # the worker passes and nothing else.
    async def __call__(self, session, store, job, **_fencing) -> None:
        self.started.set()
        try:
            await asyncio.sleep(UNSTOPPED_DISPATCH_SECONDS)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        self.completed = True


def steal(factory, job_id: str) -> str:
    """Another worker reclaims the job, exactly as reap-then-claim would."""
    with factory() as session:
        job = session.get(Job, job_id)
        job.lease_token = "the-other-worker's-token"
        job.worker_id = "worker-b"
        session.commit()
        return job.lease_token


async def _execute_with_capture(worker: Worker, job_id: str) -> list[dict]:
    """Run one job, collecting anything asyncio reports about stray tasks."""
    unhandled: list[dict] = []
    asyncio.get_running_loop().set_exception_handler(
        lambda _loop, context: unhandled.append(context)
    )
    await worker.execute(job_id)
    return unhandled


class TestALostLeaseStopsTheWork:
    def test_the_dispatch_is_cancelled_when_another_worker_takes_the_job(
        self, bound_db, settings, profile, monkeypatch
    ):
        job_id = seed_job(bound_db, profile)
        worker = Worker(settings)
        assert worker.claim_one() == job_id
        dispatch = Dispatch()
        monkeypatch.setattr(Worker, "_dispatch", dispatch)

        async def scenario() -> tuple[list[dict], float]:
            loop = asyncio.get_running_loop()
            task = asyncio.create_task(_execute_with_capture(worker, job_id))
            await asyncio.wait_for(dispatch.started.wait(), timeout=5)
            steal(bound_db, job_id)
            # Elapsed time, not just "did it return". A `wait_for` timeout
            # cancels the task it is waiting on, so it *causes* the very
            # cancellation being asserted — the test would pass on its own
            # impatience. The clock is what distinguishes the heartbeat
            # stopping the work from this test stopping it.
            began = loop.time()
            unhandled = await asyncio.wait_for(task, timeout=10)
            return unhandled, loop.time() - began

        unhandled, elapsed = asyncio.run(scenario())

        assert dispatch.cancelled is True
        assert dispatch.completed is False
        assert elapsed < STOP_WITHIN_SECONDS, (
            f"the work ran for {elapsed:.1f}s after the lease was taken; "
            "the heartbeat noticed but did not stop it"
        )
        assert unhandled == [], f"asyncio reported a stray task: {unhandled}"

    def test_the_old_worker_does_not_decide_the_job_s_outcome(
        self, bound_db, settings, profile, monkeypatch
    ):
        """B owns the job. A must leave it exactly as B holds it."""
        job_id = seed_job(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        dispatch = Dispatch()
        monkeypatch.setattr(Worker, "_dispatch", dispatch)

        async def scenario() -> float:
            loop = asyncio.get_running_loop()
            task = asyncio.create_task(worker.execute(job_id))
            await asyncio.wait_for(dispatch.started.wait(), timeout=5)
            steal(bound_db, job_id)
            began = loop.time()
            await asyncio.wait_for(task, timeout=10)
            return loop.time() - began

        elapsed = asyncio.run(scenario())
        assert elapsed < STOP_WITHIN_SECONDS

        with bound_db() as session:
            job = session.get(Job, job_id)
            assert job.status == JobStatus.RUNNING.value
            assert job.worker_id == "worker-b"
            assert job.lease_token == "the-other-worker's-token"
            assert job.finished_at is None

    def test_a_heartbeat_that_cannot_reach_the_database_stops_the_work(
        self, bound_db, settings, profile, monkeypatch
    ):
        """An unreachable database is not permission to keep going unfenced.

        The lease cannot be extended through a broken connection either, so a
        worker that carries on is running on nothing but an exception nobody
        saw. It used to: the heartbeat raised inside the beat task, which
        nothing awaited, and the dispatch ran to completion.
        """
        job_id = seed_job(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        dispatch = Dispatch()
        monkeypatch.setattr(Worker, "_dispatch", dispatch)

        def explode(self, job_id, *, lease_token):
            raise sa.exc.OperationalError("SELECT 1", {}, Exception("connection lost"))

        monkeypatch.setattr(JobStore, "heartbeat", explode)

        async def scenario() -> tuple[list[dict], float]:
            loop = asyncio.get_running_loop()
            task = asyncio.create_task(_execute_with_capture(worker, job_id))
            await asyncio.wait_for(dispatch.started.wait(), timeout=5)
            began = loop.time()
            unhandled = await asyncio.wait_for(task, timeout=10)
            return unhandled, loop.time() - began

        unhandled, elapsed = asyncio.run(scenario())
        gc.collect()
        assert elapsed < STOP_WITHIN_SECONDS

        assert dispatch.cancelled is True
        assert unhandled == [], f"asyncio reported a stray task: {unhandled}"

        with bound_db() as session:
            job = session.get(Job, job_id)
            # Honest retryable state: still RUNNING, holding a lease that will
            # expire and be reaped. Not succeeded, and not failed by a worker
            # that could not talk to the database.
            assert job.status == JobStatus.RUNNING.value
            assert job.finished_at is None

    def test_a_cancellation_from_outside_is_not_swallowed(
        self, bound_db, settings, profile, monkeypatch
    ):
        """Shutdown cancels `execute`. It must not report success.

        Catching `CancelledError` to mean "the lease went" caught every
        cancellation, including the one that stops the process. `execute` then
        returned normally out of a cancelled task, so `wait_for` — which
        decides it timed out by re-raising the cancellation it injected — saw
        an ordinary return value and reported the work finished. Abandoned
        work being indistinguishable from finished work is the failure this
        whole file is about, arriving through the shutdown path instead.
        """
        job_id = seed_job(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        dispatch = Dispatch()
        monkeypatch.setattr(Worker, "_dispatch", dispatch)

        async def scenario() -> None:
            task = asyncio.create_task(worker.execute(job_id))
            await asyncio.wait_for(dispatch.started.wait(), timeout=5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert task.cancelled() is True

        asyncio.run(scenario())
        assert dispatch.cancelled is True

    def test_a_job_with_no_lease_token_is_refused_rather_than_run_unfenced(
        self, bound_db, settings, profile, monkeypatch
    ):
        """Rows claimed before this column existed have no token.

        Running them anyway would be an unfenced write, which is the one thing
        this mechanism exists to prevent. Refusing leaves the job to the
        reaper, which re-claims it and mints one.
        """
        job_id = seed_job(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        with bound_db() as session:
            session.get(Job, job_id).lease_token = None
            session.commit()

        dispatch = Dispatch()
        monkeypatch.setattr(Worker, "_dispatch", dispatch)
        asyncio.run(worker.execute(job_id))

        assert dispatch.started.is_set() is False


class TestTheBeatsSurviveABlockingJob:
    """The pipeline is synchronous work behind an `async def`.

    Both beats were `asyncio.Task`s, so neither got a turn between the start of
    a job and its end: instrumenting `_beat` during a real 54-second run showed
    the task starting and then never waking from its first sleep. The lease was
    therefore never extended while a job ran, and the liveness file never
    touched — the two mechanisms that exist precisely for long jobs were the
    two that a long job disabled.

    Consequences, both reachable in production with the shipped 120s settings:
    any job longer than the lease is reaped and handed to a second worker while
    the first is still running it, and any job longer than 120s makes a healthy
    worker fail its container healthcheck and be restarted mid-job.
    """

    def test_the_lease_is_extended_while_a_blocking_job_runs(
        self, bound_db, settings, profile, monkeypatch
    ):
        job_id = seed_job(bound_db, profile)
        worker = Worker(settings)
        worker.claim_one()
        with bound_db() as session:
            claimed = session.get(Job, job_id)
            beat_at_claim = ensure_utc(claimed.heartbeat_at)
            expiry_at_claim = ensure_utc(claimed.lease_expires_at)

        async def blocking(self, session, store, job, **_fencing) -> None:
            # `time.sleep`, not `asyncio.sleep`: this is what the real pipeline
            # does to the event loop, and the whole point of the test.
            time.sleep(LEASE_SECONDS)

        monkeypatch.setattr(Worker, "_dispatch", blocking)
        asyncio.run(worker.execute(job_id))

        with bound_db() as session:
            job = session.get(Job, job_id)
            assert ensure_utc(job.heartbeat_at) > beat_at_claim, (
                "the heartbeat never ran while the job held the event loop, so "
                "the lease was never extended"
            )
            assert ensure_utc(job.lease_expires_at) > expiry_at_claim

    def test_the_liveness_file_is_touched_while_a_blocking_job_runs(
        self, bound_db, settings, profile, monkeypatch
    ):
        """A busy worker must not look wedged to the container healthcheck."""
        monkeypatch.setattr("app.jobs.worker.LIVENESS_INTERVAL_SECONDS", 0.2)
        seed_job(bound_db, profile)
        worker = Worker(settings)
        alive = liveness_path(settings)
        seen: dict[str, float] = {}

        async def blocking_then_stop(inner, session, store, job, **_fencing) -> None:
            # Read the mtime *inside* the job, after the loop has already
            # touched the file at startup. Anything later than this had to be
            # written while the event loop was blocked.
            seen["before"] = alive.stat().st_mtime
            time.sleep(1.5)
            # Read again *before* releasing the loop. Reading after the job
            # ends measures the beat catching up on its overdue sleep, which
            # is exactly the broken behaviour, and it would pass.
            seen["after"] = alive.stat().st_mtime
            worker.stopping.set()

        monkeypatch.setattr(Worker, "_dispatch", blocking_then_stop)
        asyncio.run(worker.run_forever())

        assert seen["after"] > seen["before"], (
            "the liveness file was not touched while a job held the event loop; "
            "after 120s of honest work the healthcheck calls the worker wedged "
            "and the orchestrator restarts it mid-job"
        )


class TestTheRunnerStopsAtItsOwnCheckpoint:
    """The half of "losing the lease stops the work" that a stub cannot reach.

    Every other test in this file replaces `_dispatch`, so none of them
    exercises the checkpoint inside the pipeline — and the checkpoint is what
    stops *blocking* work, which is the only kind the pipeline actually does.
    Deleting those four lines left the whole suite green, which is a fair
    definition of untested.
    """

    def test_a_lost_lease_raises_at_the_cancellation_checkpoint(self, settings, profile):
        import threading

        from app.pipeline.runner import LeaseLost, ResearchRunner

        lease_lost = threading.Event()
        runner = ResearchRunner.__new__(ResearchRunner)
        runner.lease_lost = lease_lost
        runner.job_id = "job-1234"

        # Not yet lost: the checkpoint must fall through to its other checks,
        # which need a session. Reaching them proves it did not stop here.
        with pytest.raises(AttributeError):
            runner._check_cancelled()

        lease_lost.set()
        with pytest.raises(LeaseLost, match="job-1234"):
            runner._check_cancelled()

    def test_ownership_is_checked_before_the_database_is_touched(
        self, settings, profile
    ):
        """A job that is no longer ours must not even read through the session
        it holds: every row it would touch belongs to another worker's run."""
        import threading

        from app.pipeline.runner import LeaseLost, ResearchRunner

        class ExplodingSession:
            def refresh(self, _row):
                raise AssertionError("the database was touched after the lease was lost")

        runner = ResearchRunner.__new__(ResearchRunner)
        runner.lease_lost = threading.Event()
        runner.lease_lost.set()
        runner.job_id = "job-1234"
        runner.session = ExplodingSession()

        with pytest.raises(LeaseLost):
            runner._check_cancelled()


class TestStoppingDoesNotTakeMoreWork:
    def test_a_stop_while_every_slot_is_busy_claims_nothing_more(
        self, bound_db, settings, profile, monkeypatch
    ):
        """The stop check sat at the top of the loop, above `acquire()`.

        With every slot busy the loop parked on the acquire, so the stop was
        not seen; when a job finished, the freed slot was spent claiming new
        work from a process already told to shut down. That job then had to
        wait out its full lease before another worker could have it.
        """
        settings.worker_concurrency = 1
        seed_job(bound_db, profile)
        second = seed_job(bound_db, profile)
        worker = Worker(settings)
        dispatch = Dispatch()

        async def held_dispatch(self, session, store, job, **_fencing) -> None:
            dispatch.started.set()
            await asyncio.sleep(0.4)

        monkeypatch.setattr(Worker, "_dispatch", held_dispatch)

        async def scenario() -> None:
            loop = asyncio.create_task(worker.run_forever())
            await asyncio.wait_for(dispatch.started.wait(), timeout=5)
            worker.stopping.set()
            await asyncio.wait_for(loop, timeout=15)

        asyncio.run(scenario())

        with bound_db() as session:
            still_queued = session.get(Job, second)
            assert still_queued.status == JobStatus.QUEUED.value
            assert still_queued.attempts == 0, (
                "a stopping worker claimed another job; its attempt is spent "
                "and it is leased to a process that is going away"
            )
        # The first job ran to the end of its dispatch — the stop drained it
        # rather than abandoning it. `jobs_done` is the worker's own counter,
        # incremented after the dispatch returns; the stub stands in for the
        # pipeline, so the job row itself is not marked succeeded here.
        assert worker.jobs_done == 1
        assert worker.jobs_failed == 0


class TestSupportedVersionsAreTakenLiterally:
    def test_an_empty_supported_set_claims_nothing(self, bound_db, settings, profile):
        """`supported_versions or DEFAULT` read "supports nothing" as "unset".

        An empty set is a caller saying this build can run no payload at all —
        a worker mid-rollout, or this test. Falling back to the default made
        the one input that must claim nothing claim everything.
        """
        seed_job(bound_db, profile)
        with bound_db() as session:
            assert JobStore(session).claim(supported_versions=frozenset()) is None
            assert JobStore(session).claim(supported_versions=[]) is None
            # And the job really was claimable, so the assertion above is not
            # passing for the wrong reason.
            assert JobStore(session).claim() is not None
