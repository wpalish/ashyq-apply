"""Operational visibility into the queue, scoped to the caller's workspace.

A dead job is work the queue gave up on after exhausting its attempts. Until
now the only way to see one was to open the database: a run showed as failed
and said nothing about the job behind it, so a queue slowly filling with work
that would never run was invisible to everyone but a developer.

Scoped to one organization rather than to the deployment, deliberately. The
person who needs this answer is the owner of a workspace asking "is my research
stuck", not an administrator of the whole service. A global view would need a
deployment-wide credential, and inventing one would put every tenant's job
errors behind a single shared token — the opposite of the tenant isolation the
rest of the API is built on.

A job with no run (nothing enqueues one today) therefore belongs to no tenant
and is not listed here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ApplicantProfileRow, Job, JobStatus, ResearchRun
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/jobs")
def list_jobs(
    response: Response,
    status: str = "dead",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Jobs of this organization in one status, newest first.

    `X-Total-Count` carries the whole count, which is what the UI needs to say
    "3 jobs need attention" without pulling the list itself.
    """
    if status not in {s.value for s in JobStatus}:
        raise HTTPException(400, f"Unknown job status {status!r}.")
    if principal.role != "owner":
        raise HTTPException(403, "Only a workspace owner can read the job queue.")

    q = (
        session.query(Job)
        .join(ResearchRun, Job.run_id == ResearchRun.id)
        .join(ApplicantProfileRow, ResearchRun.profile_id == ApplicantProfileRow.id)
        .filter(
            Job.status == status,
            ApplicantProfileRow.organization_id == principal.organization_id,
        )
    )
    response.headers["X-Total-Count"] = str(q.count())
    jobs = q.order_by(Job.created_at.desc()).limit(limit).offset(offset).all()
    return [
        {
            "id": job.id,
            "kind": job.kind,
            "status": job.status,
            "run_id": job.run_id,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            # The worker's own message. It is about this workspace's own run,
            # and hiding it would leave the owner with a number and no cause.
            "last_error": job.last_error,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }
        for job in jobs
    ]
