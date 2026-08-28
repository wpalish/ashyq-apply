"""A small in-process job queue.

Deliberately minimal: an asyncio task per run, a registry so the API can report
progress and request cancellation, and no external broker. The interface
(``submit`` / ``status`` / ``cancel``) is the same one a Celery or RQ backend
would expose, so replacing it later touches this file only.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.config import get_settings
from app.db import session_scope
from app.domain.enums import PipelineStage
from app.models import ApplicantProfileRow, AuditEvent, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.schemas.profile import ApplicantProfileIn

log = logging.getLogger("unimatch.queue")


@dataclass
class JobHandle:
    run_id: str
    kind: str
    #: An asyncio.Task when submitted from the loop, a concurrent Future when
    #: submitted from a threadpool worker. Both expose done/cancel/exception.
    task: object
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def done(self) -> bool:
        return bool(self.task.done())

    @property
    def error(self) -> str:
        if not self.task.done() or self.task.cancelled():
            return ""
        try:
            exc = self.task.exception()
        except Exception:  # a cancelled concurrent Future raises here
            return ""
        return f"{type(exc).__name__}: {exc}" if exc else ""


class JobQueue:
    def __init__(self, max_concurrent: int = 2) -> None:
        self._jobs: dict[str, JobHandle] = {}
        self._max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the application's loop.

        FastAPI runs synchronous route handlers in a threadpool, where there is
        no running loop to create a task on. Binding the loop at startup lets
        those handlers schedule work onto it safely.
        """
        self._loop = loop
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

    def submit(self, run_id: str, kind: str = "research") -> JobHandle:
        existing = self._jobs.get(run_id)
        if existing is not None and not existing.done:
            return existing

        coro = self._execute(run_id, kind)
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is not None:
            task: object = running.create_task(coro, name=f"{kind}:{run_id}")
        elif self._loop is not None:
            task = asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            coro.close()
            raise RuntimeError(
                "The job queue has no event loop bound. Call queue.bind_loop() during startup."
            )

        handle = JobHandle(run_id=run_id, kind=kind, task=task)
        self._jobs[run_id] = handle
        return handle

    def get(self, run_id: str) -> JobHandle | None:
        return self._jobs.get(run_id)

    def cancel(self, run_id: str) -> bool:
        """Ask the run to stop.

        The DB flag is the real signal - the runner checks it between units of
        work so a cancellation lands at a consistent point instead of tearing a
        stage in half. The task is only cancelled as a backstop.
        """
        with session_scope() as s:
            run = s.get(ResearchRun, run_id)
            if run is None:
                return False
            run.cancelled = True
            s.add(AuditEvent(actor="user", action="run_cancel_requested",
                             entity_type="run", entity_id=run_id, detail={}))
        handle = self._jobs.get(run_id)
        if handle and not handle.done:
            handle.task.cancel()
        return True

    async def _execute(self, run_id: str, kind: str) -> None:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        async with self._semaphore:
            settings = get_settings()
            with session_scope() as session:
                run = session.get(ResearchRun, run_id)
                if run is None:
                    log.warning("run %s vanished before execution", run_id)
                    return
                profile_row = session.get(ApplicantProfileRow, run.profile_id)
                if profile_row is None:
                    log.warning("profile for run %s is gone", run_id)
                    return
                profile = ApplicantProfileIn.model_validate(profile_row.payload)
                runner = ResearchRunner(session, run, profile, settings)
                if kind == "documents":
                    await runner.collect_documents()
                else:
                    await runner.run_to_decision()

    async def shutdown(self) -> None:
        pending = [h.task for h in self._jobs.values() if not h.done]
        for task in pending:
            task.cancel()
        awaitable = [t for t in pending if isinstance(t, asyncio.Task)]
        if awaitable:
            await asyncio.gather(*awaitable, return_exceptions=True)


def reconcile_orphaned_runs(lease_seconds: int | None = None) -> list[str]:
    """Find runs whose worker died and mark them recoverable.

    Called at startup. Without it a crashed worker leaves a run claiming to be
    running forever, and the UI polls it indefinitely.
    """
    from app.pipeline.state import LEASE_SECONDS, is_lease_expired

    recovered: list[str] = []
    with session_scope() as session:
        candidates = (
            session.query(ResearchRun)
            .filter(ResearchRun.finished_at.is_(None))
            .all()
        )
        for run in candidates:
            if not is_lease_expired(
                run.stage, run.heartbeat_at,
                lease_seconds=lease_seconds or LEASE_SECONDS,
            ):
                continue
            run.stage = PipelineStage.RETRYABLE_FAILED.value
            run.worker_id = None
            run.recovery_count = (run.recovery_count or 0) + 1
            run.errors = [
                *(run.errors or []),
                "The worker running this stage stopped without finishing. The run was "
                "recovered at startup and can be retried from the last completed stage.",
            ]
            session.add(run)
            session.add(AuditEvent(
                actor="system", action="run_recovered", entity_type="run",
                entity_id=run.id, detail={"recovery_count": run.recovery_count},
            ))
            recovered.append(run.id)
    if recovered:
        log.warning("recovered %d orphaned run(s): %s", len(recovered), ", ".join(recovered))
    return recovered


queue = JobQueue()
