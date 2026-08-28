"""Removed: the in-process job queue.

Superseded by the durable queue in ``app.jobs``. It was not durable — a worker
crash lost the job and left the run claiming to be running — and it ran inside
the API process, so deploying the API interrupted research.

See docs/adr/0001-durable-job-queue.md.
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    raise ImportError(
        f"app.pipeline.queue.{name} no longer exists. Use app.jobs.store.JobStore to "
        "enqueue and app.jobs.worker.Worker to consume. See docs/adr/0001-durable-job-queue.md."
    )
