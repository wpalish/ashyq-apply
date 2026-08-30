"""The worker.

Claims a job, runs it, and beats while it does. Every exit path is accounted
for: success completes the job, a failure retries it with backoff until its
attempts run out, a cancellation stops it at a consistent point, and a crash
leaves a lease that another worker's reaper takes back.

Runs as its own process, separate from the API. `python -m app.jobs.worker`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

from app.config import Settings, get_settings
from app.db import session_scope
from app.domain.enums import PipelineStage
from app.jobs.store import JobStore, worker_identity
from app.jobs.versioning import (
    BUILD_VERSION,
    SUPPORTED_PAYLOAD_SCHEMA_VERSIONS,
    incompatibility,
    supports,
)
from app.models import ApplicantProfileRow, AuditEvent, Job, JobStatus, ResearchRun
from app.pipeline.runner import LeaseLost, ResearchRunner, RunCancelled
from app.schemas.profile import ApplicantProfileIn

log = logging.getLogger("unimatch.worker")

#: Beat at a third of the lease so two beats can be missed before it expires.
HEARTBEAT_DIVISOR = 3

#: How long to wait for a beat thread to notice it has been told to stop. It is
#: parked in `Event.wait`, so this is a backstop against a wedged heartbeat
#: holding up the worker, not an expected delay.
BEAT_JOIN_SECONDS = 10.0


class Worker:
    def __init__(self, settings: Settings | None = None, *, worker_id: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.worker_id = worker_id or worker_identity()
        self.stopping = asyncio.Event()
        self.jobs_done = 0
        self.jobs_failed = 0

    # --- lifecycle --------------------------------------------------------

    def request_stop(self, *_args: object) -> None:
        """Finish the job in hand, then exit. No work is abandoned mid-stage."""
        if not self.stopping.is_set():
            log.info("shutdown requested; finishing the current job first")
            self.stopping.set()

    async def run_forever(self) -> None:
        log.info(
            "worker %s starting (build %s, payload schemas %s, concurrency %d)",
            self.worker_id,
            BUILD_VERSION,
            sorted(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS),
            self.settings.worker_concurrency,
        )
        self.reap()
        semaphore = asyncio.Semaphore(self.settings.worker_concurrency)
        running: set[asyncio.Task] = set()

        # A task of its own, not a call at the top of the loop.
        #
        # It was called just before `await semaphore.acquire()`, so with every
        # slot busy the loop blocked there and never touched again: after 120
        # seconds a worker doing exactly the work it exists to do reported
        # unhealthy and was restarted mid-job. A heartbeat that stops while the
        # worker is busiest measures the wrong thing.
        alive_at = liveness_path(self.settings)
        touch_liveness(alive_at)
        # A thread, not a task.
        #
        # As a task it shared the event loop with the job, and the pipeline is
        # synchronous work behind an `async def`: instrumenting a real 54s run
        # showed this task starting and never waking from its first sleep. So
        # the liveness file went untouched for exactly as long as the worker
        # was busy, and after 120s of honest work the container healthcheck
        # called it wedged and the orchestrator restarted it mid-job. "Busy"
        # and "wedged" looked the same again, which is what this file exists
        # to tell apart.
        stop_liveness = threading.Event()
        liveness = threading.Thread(
            target=self._hold_liveness, args=(alive_at, stop_liveness),
            name="worker-liveness", daemon=True,
        )
        liveness.start()

        try:
            await self._consume(semaphore, running)
        finally:
            # The liveness beat is stopped *after* the drain, and on every path
            # out of the loop rather than only the normal one. An exception in
            # `reap()` or `claim_one()` — both of which touch the database —
            # used to skip the drain and leave the thread running, so a dead
            # worker went on writing a file that says it is alive.
            if running:
                log.info("waiting for %d job(s) to finish", len(running))
                await asyncio.gather(*running, return_exceptions=True)
            stop_liveness.set()
            await asyncio.to_thread(liveness.join, BEAT_JOIN_SECONDS)
        log.info(
            "worker %s stopped (%d done, %d failed)",
            self.worker_id,
            self.jobs_done,
            self.jobs_failed,
        )

    async def _consume(
        self, semaphore: asyncio.Semaphore, running: set[asyncio.Task]
    ) -> None:
        """The claim loop, so that stopping it is a `finally` rather than a
        sequence of statements every exit path has to remember to reach."""
        while not self.stopping.is_set():
            await semaphore.acquire()
            if self.stopping.is_set():
                # The stop arrived while every slot was busy, so the loop was
                # parked on `acquire()` — past the `while` condition that would
                # have caught it. When a job finished, the released slot was
                # spent claiming *new* work from a process that had already
                # been told to stop, and that job then had to wait out its
                # whole lease before anyone else could take it.
                semaphore.release()
                break
            job_id = self.claim_one()
            if job_id is None:
                semaphore.release()
                # Wake early if a stop is requested; otherwise poll on schedule.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self.stopping.wait(), timeout=self.settings.worker_poll_seconds
                    )
                self.reap()
                continue

            task = asyncio.create_task(self._run_and_release(job_id, semaphore))
            running.add(task)
            task.add_done_callback(running.discard)


    async def _run_and_release(self, job_id: str, semaphore: asyncio.Semaphore) -> None:
        try:
            await self.execute(job_id)
        finally:
            semaphore.release()

    # --- queue operations -------------------------------------------------

    def reap(self) -> list[str]:
        """Take back jobs whose worker stopped beating."""
        with session_scope() as session:
            return JobStore(session, lease_seconds=self.settings.job_lease_seconds).reap_expired()

    def claim_one(self) -> str | None:
        with session_scope() as session:
            store = JobStore(session, lease_seconds=self.settings.job_lease_seconds)
            job = store.claim(worker_id=self.worker_id)
            return job.id if job else None

    # --- execution --------------------------------------------------------

    async def execute(self, job_id: str) -> None:
        """Run one job to a terminal state, for as long as it is ours.

        The lease token is read once, here, and presented on every write. A
        worker that stalls past its lease loses the job to another; without the
        token it could still have written to it, which is two writers on one
        job.
        """
        try:
            with session_scope() as session:
                claimed = JobStore(session).get(job_id)
                if claimed is None:
                    return
                lease_token = claimed.lease_token or ""
                payload_version = claimed.payload_schema_version
        except Exception:
            # The job is already RUNNING with an attempt spent — `claim_one`
            # saw to that — so an exception escaping here left it stranded with
            # nothing in the log to say why, until the reaper eventually took
            # it back. Every one of these lines used to sit inside the `try`
            # that the refactor moved them out of.
            log.exception("could not read job %s; leaving it to the reaper", job_id[:8])
            return

        # The version check comes before the token check, and deliberately.
        # Parking is not a lease-holding write — it is the same refusal
        # `park_unsupported` performs on rows nobody has claimed — and a job
        # this build cannot read must be named as such whether or not it is
        # ours. Putting the token guard first swallowed the refusal and left
        # the job sitting in `queued` with no explanation.
        if not supports(payload_version):
            # Refuse, do not attempt. Attempting a payload this build cannot
            # read spends the job's three attempts and ends in `dead`, which
            # needs a person; parking ends when a capable worker starts.
            detail = incompatibility(payload_version)
            log.warning(
                "job %s parked: payload schema v%s, this build runs %s",
                job_id[:8], payload_version, detail["worker_supports"],
            )
            with session_scope() as session:
                JobStore(session).park_incompatible(job_id, payload_version)
            return

        if not lease_token:
            # Nothing to fence with. Refusing is the safe direction: an
            # unfenced write is exactly what this exists to prevent.
            log.warning("job %s has no lease token; refusing to run it", job_id[:8])
            return

        # The dispatch runs as a task so the heartbeat can cancel it the moment
        # the lease is lost. Previously the heartbeat noticed and returned, and
        # the work carried on writing.
        #
        # `lease_lost` separates *our* cancellation from anyone else's. Without
        # it this swallowed every CancelledError, including the shutdown one:
        # `execute` then returned normally from a cancelled task, and callers
        # using `wait_for` were told the work had finished when it had been
        # abandoned. A cancellation that did not come from here is re-raised.
        lease_lost = threading.Event()
        beat_finished = threading.Event()
        work = asyncio.create_task(
            self._run_owned(job_id, lease_token, lease_lost)
        )
        beat = threading.Thread(
            target=self._hold_the_lease,
            args=(
                job_id, lease_token, lease_lost, beat_finished,
                asyncio.get_running_loop(), work,
            ),
            name=f"lease-{job_id[:8]}",
            daemon=True,
        )
        beat.start()
        try:
            await work
        except asyncio.CancelledError:
            if not lease_lost.is_set():
                raise
            # The job is already back in the queue and belongs to whoever
            # reclaimed it. Nothing further to write, and nothing to report as
            # a failure of the work itself.
            log.warning("job %s abandoned: the lease was lost", job_id[:8])
        finally:
            beat_finished.set()
            # Joined off the event loop. The thread is usually parked in
            # `Event.wait` and returns at once, but part of every cycle is
            # spent inside `session_scope()`, and a blocking `join` on the loop
            # thread would freeze every other concurrency slot for as long as
            # that database call takes. The timeout is a backstop so a wedged
            # heartbeat cannot wedge the worker with it.
            await asyncio.to_thread(beat.join, BEAT_JOIN_SECONDS)

    async def _run_owned(
        self,
        job_id: str,
        lease_token: str,
        lease_lost: threading.Event | None = None,
    ) -> None:
        """One job, with every write fenced by the lease token."""
        try:
            with session_scope() as session:
                store = JobStore(session, lease_seconds=self.settings.job_lease_seconds)
                job = store.get(job_id)
                if job is None:
                    return
                log.info("running job %s (%s) attempt %d", job.id[:8], job.kind, job.attempts)
                await self._dispatch(
                    session, store, job,
                    lease_token=lease_token, lease_lost=lease_lost,
                )
            self.jobs_done += 1
        except LeaseLost:
            # Another worker holds this job and is running it now. Writing
            # anything — success, failure, even a cancellation — would be the
            # second of two workers deciding one job's outcome. Its state is
            # already correct: it belongs to the holder.
            log.warning(
                "job %s stopped mid-run: the lease was lost to another worker",
                job_id[:8],
            )
            return
        except RunCancelled as exc:
            with session_scope() as session:
                JobStore(session).mark_cancelled(
                    job_id, str(exc), lease_token=lease_token
                )
            log.info("job %s cancelled", job_id[:8])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.jobs_failed += 1
            log.exception("job %s failed", job_id[:8])
            with session_scope() as session:
                status = JobStore(session).fail(
                    job_id, f"{type(exc).__name__}: {exc}", lease_token=lease_token
                )
            if status is None:
                log.warning(
                    "job %s failed but the lease was already lost; the holder "
                    "that reclaimed it decides its outcome",
                    job_id[:8],
                )
            else:
                log.info("job %s -> %s", job_id[:8], status)

    def _hold_liveness(self, path: Path, finished: threading.Event) -> None:
        """Report that this worker is still going round its loop.

        On a thread, so that a job holding the event loop cannot make a healthy
        worker look wedged. It is still a real liveness signal: a worker whose
        *process* is stuck — deadlocked, suspended, out of memory — cannot run
        this thread either, which is exactly what should make the file stale.
        """
        while not finished.wait(LIVENESS_INTERVAL_SECONDS):
            try:
                touch_liveness(path)
            except OSError:
                # A liveness file that cannot be written is a real problem, but
                # not one this thread can fix, and crashing it would remove the
                # only signal that says so. Going stale is the honest outcome.
                log.exception("could not write the liveness file at %s", path)

    def _hold_the_lease(
        self,
        job_id: str,
        lease_token: str,
        lease_lost: threading.Event,
        finished: threading.Event,
        loop: asyncio.AbstractEventLoop,
        work: asyncio.Task,
    ) -> None:
        """Extend this job's lease, and stop the work when it can no longer be.

        A thread rather than a task, because what it has to survive is the
        event loop being blocked — and the pipeline blocks it for the whole
        job. As a task this never ran at all between the start of a job and its
        end, so the lease was never extended while a job was running: every job
        longer than `job_lease_seconds` was reaped and handed to a second
        worker while the first was still working on it. The mechanism that
        exists for long jobs was disabled by exactly the jobs it was for.

        Two different things can go wrong, and they are not the same:

        - **the store says no** — another worker holds the job. Definitive, and
          acted on at once.
        - **the database cannot be reached** — unknown. Continuing to work is
          reasonable *until* the lease would have lapsed, because until then no
          reaper can have given the job away. After that it must stop, whether
          or not it can find out why: another worker may already be running it.
        """
        lease_seconds = self.settings.job_lease_seconds
        interval = max(1.0, lease_seconds / HEARTBEAT_DIVISOR)
        last_held = time.monotonic()

        while True:
            # Wake by the deadline even if that is sooner than the interval.
            # Sleeping a whole interval and only then looking at the clock let
            # the deadline pass unnoticed by up to one interval.
            remaining = lease_seconds - (time.monotonic() - last_held)
            if finished.wait(min(interval, max(0.1, remaining))):
                return
            if time.monotonic() - last_held >= lease_seconds:
                log.warning(
                    "the lease on job %s lapsed without being extended", job_id[:8]
                )
                held: bool | None = False
            else:
                held = self._try_heartbeat(job_id, lease_token, last_held, lease_seconds)

            if held:
                last_held = time.monotonic()
                continue

            stale_for = time.monotonic() - last_held
            if held is False:
                log.warning(
                    "lost the lease on job %s: it is no longer ours to extend",
                    job_id[:8],
                )
            elif stale_for < lease_seconds:
                # Unreachable, but the lease has not lapsed yet, so nobody else
                # can have taken this job. Keep working and try again.
                continue
            else:
                log.warning(
                    "could not extend the lease on job %s for %.0fs; it has "
                    "lapsed and another worker may hold it now",
                    job_id[:8], stale_for,
                )

            lease_lost.set()
            # Two routes, because there are two kinds of work. Blocking work
            # never yields, and stops at the pipeline's next checkpoint, which
            # reads `lease_lost`. Work that does await is cancelled here.
            # A closed loop means the work is over anyway.
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(self._cancel_if_running, work, job_id)
            return

    def _try_heartbeat(
        self, job_id: str, lease_token: str, last_held: float, lease_seconds: int
    ) -> bool | None:
        """One heartbeat, bounded by the time left on the lease.

        A database that refuses answers immediately; a *partitioned* one does
        not — the socket hangs until the driver gives up, which can be far
        longer than a heartbeat interval. The loop only looked at the clock
        after the call returned, so a hanging call let the work run past the
        lease it could no longer prove it held, which is the window another
        worker reclaims the job in.

        The attempt therefore runs on its own thread and is waited for only as
        long as the lease has left. A call that has not answered by then has
        already failed to do the one thing it was for. The thread is a daemon
        and is left to unwind on its own; blocking on it here would reintroduce
        exactly the hang this exists to bound.
        """
        answer: list[bool] = []

        def attempt() -> None:
            try:
                with session_scope() as session:
                    answer.append(
                        JobStore(session, lease_seconds=lease_seconds).heartbeat(
                            job_id, lease_token=lease_token
                        )
                    )
            except Exception:
                log.exception("could not extend the lease on job %s", job_id[:8])

        thread = threading.Thread(
            target=attempt, name=f"beat-{job_id[:8]}", daemon=True
        )
        thread.start()
        thread.join(timeout=max(0.1, lease_seconds - (time.monotonic() - last_held)))
        if not answer:
            # Either it raised, or it is still hanging. Both are "unknown", and
            # the caller decides what unknown costs.
            return None
        return answer[0]

    @staticmethod
    def _cancel_if_running(work: asyncio.Task, job_id: str) -> None:
        if not work.done():
            work.cancel()

    async def _dispatch(
        self,
        session,
        store: JobStore,
        job: Job,
        *,
        lease_token: str,
        lease_lost: threading.Event | None = None,
    ) -> None:
        """Route a job to its handler, in the job's own transaction."""
        run = session.get(ResearchRun, job.run_id) if job.run_id else None
        if run is None:
            store.fail(job.id, f"run {job.run_id} no longer exists", retry=False)
            return

        profile_row = session.get(ApplicantProfileRow, run.profile_id)
        if profile_row is None:
            store.fail(job.id, "the applicant profile was deleted", retry=False)
            return

        profile = ApplicantProfileIn.model_validate(profile_row.payload)
        runner = ResearchRunner(
            session, run, profile, self.settings,
            job_id=job.id, lease_lost=lease_lost,
        )

        if job.kind == "documents":
            await runner.collect_documents()
        elif job.kind == "research":
            await runner.run_to_decision()
        else:
            store.fail(job.id, f"unknown job kind {job.kind!r}", retry=False)
            return

        # The job's completion and the work it produced commit together, so a
        # crash can never mark a job done with its results missing.
        #
        # And the refusal is honoured. `complete()` returns a bool precisely so
        # a worker that has lost its lease learns that its write did not land;
        # dropping the value meant this went on to record a `job_completed`
        # audit event and count the job in `jobs_done` — two workers, one job,
        # both reporting success.
        if not store.complete(job.id, lease_token=lease_token):
            raise LeaseLost(
                f"job {job.id} was completed by another worker; this one no "
                "longer holds the lease"
            )
        session.add(
            AuditEvent(
                organization_id=profile_row.organization_id,
                actor="worker",
                action="job_completed",
                entity_type="job",
                entity_id=job.id,
                detail={"kind": job.kind, "stage": run.stage},
            )
        )


#: A worker that starts before migrations finish should wait, not die: in a
#: rolling deploy their order is not guaranteed.
SCHEMA_WAIT_SECONDS = 60


def wait_for_schema(timeout: float = SCHEMA_WAIT_SECONDS) -> bool:
    """Block until the database matches this code, or give up saying why."""
    import time

    from app.db import SchemaOutOfDate, assert_at_head

    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            assert_at_head()
            return True
        except SchemaOutOfDate as exc:
            last = exc
            log.info("waiting for the database schema to be migrated…")
            time.sleep(2)
        except Exception as exc:  # a database that is not up yet at all
            last = exc
            log.info("waiting for the database to accept connections…")
            time.sleep(2)
    log.error("giving up waiting for the schema: %s", last)
    return False


#: Job states that mean a run is still going to be worked on. `queued` and
#: `running` are obvious; `blocked_incompatible` belongs here because it is
#: paused work waiting for a deployment to finish, not abandoned work. Treating
#: it as stranded would mark the run failed and throw away something that is
#: about to resume by itself.
LIVE_JOB_STATUSES: frozenset[str] = frozenset({
    JobStatus.QUEUED.value,
    JobStatus.RUNNING.value,
    JobStatus.BLOCKED_INCOMPATIBLE.value,
})


def reconcile_startup() -> dict[str, int]:
    """Put the queue and the runs back into a consistent state.

    Runs before any work is claimed: expired leases go back to the queue, and a
    run whose job is no longer live stops claiming to be running.
    """
    settings = get_settings()
    with session_scope() as session:
        store = JobStore(session, lease_seconds=settings.job_lease_seconds)
        reaped = store.reap_expired()
        # A deployment finishing is what unblocks the queue: this worker
        # releases anything an earlier one parked because it could not read
        # the payload version. No operator action, no lost work.
        released = store.release_incompatible(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS)
        # And name anything queued that this build still cannot read, so it is
        # visibly paused rather than silently never claimed.
        parked = store.park_unsupported(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS)

        stranded = 0
        live_run_ids = {
            job.run_id
            for job in session.query(Job).filter(
                Job.status.in_(LIVE_JOB_STATUSES)
            )
            if job.run_id
        }
        in_progress = (
            session.query(ResearchRun)
            .filter(
                ResearchRun.finished_at.is_(None),
                ResearchRun.stage.notin_(
                    [
                        PipelineStage.AWAITING_USER_DECISION.value,
                        PipelineStage.COMPLETED.value,
                        PipelineStage.CANCELLED.value,
                        PipelineStage.RETRYABLE_FAILED.value,
                        PipelineStage.FAILED.value,
                    ]
                ),
            )
            .all()
        )
        for run in in_progress:
            if run.id in live_run_ids:
                continue
            run.stage = PipelineStage.RETRYABLE_FAILED.value
            run.worker_id = None
            run.recovery_count = (run.recovery_count or 0) + 1
            run.errors = [
                *(run.errors or []),
                "No job is queued or running for this run. It was recovered at startup and "
                "can be retried from the last completed stage.",
            ]
            session.add(run)
            session.add(
                AuditEvent(
                    organization_id=run.profile.organization_id,
                    actor="system",
                    action="run_recovered",
                    entity_type="run",
                    entity_id=run.id,
                    detail={"recovery_count": run.recovery_count},
                )
            )
            stranded += 1

        return {
            "jobs_reaped": len(reaped),
            "runs_recovered": stranded,
            "jobs_released": released,
            "jobs_parked": parked,
        }


#: How long a worker may go without completing a poll before it is considered
#: wedged. Generous relative to the poll interval: a worker running a long job
#: still comes back round the loop between units of work, and a healthcheck
#: that restarts a busy worker is worse than no healthcheck at all.
LIVENESS_STALE_SECONDS = 120


#: How often the heartbeat writes, comfortably inside LIVENESS_STALE_SECONDS so
#: an ordinary scheduling delay never looks like a wedge.
LIVENESS_INTERVAL_SECONDS = 10.0


def liveness_path(settings: Settings | None = None) -> Path:
    """Where this worker records that it is still going round its loop.

    Deliberately container-local, not on the shared volume.

    It lived beside the HTTP cache, which is `worker-cache:/app/data` — the
    same volume for every replica. `docker compose up --scale worker=3` gave
    three workers one `worker-alive` file, so any single healthy worker kept
    all three reporting healthy, including two that were wedged. A healthcheck
    that cannot fail for the container it is checking is worse than none: it
    provides the reassurance without the check.

    `/tmp` is per-container by construction and is already a tmpfs in the
    compose stack, so nothing needs mounting for this to work.
    """
    del settings  # deliberately not derived from a shared, mounted path
    return Path(os.environ.get("ASHYQ_LIVENESS_PATH", "/tmp/ashyq-worker-alive"))


def touch_liveness(path: Path) -> None:
    """Record that the worker completed a pass.

    Never raises. This is diagnostics, and failing to write it must not be the
    reason a worker stops doing work — the queue is durable, this file is not.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(int(time.time())))
    except OSError:
        log.debug("could not record worker liveness at %s", path, exc_info=True)


def is_alive(path: Path) -> bool:
    """Whether a worker has been round its loop recently enough.

    False for a file that does not exist: a worker that has not started yet is
    not healthy, and a healthcheck that passes on absence reports a stack ready
    before it is.
    """
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    return age <= LIVENESS_STALE_SECONDS


def main() -> int:  # pragma: no cover - process entry point
    # `--healthcheck` answers "is the worker still going round its loop" and
    # exits. Run by the container healthcheck, which cannot ask over HTTP
    # because a worker does not listen on a port.
    if "--healthcheck" in sys.argv[1:]:
        return 0 if is_alive(liveness_path()) else 1

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if not wait_for_schema():
        return 1
    summary = reconcile_startup()
    log.info("startup reconciliation: %s", summary)

    worker = Worker(settings)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.request_stop)
    try:
        loop.run_until_complete(worker.run_forever())
    finally:
        loop.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
