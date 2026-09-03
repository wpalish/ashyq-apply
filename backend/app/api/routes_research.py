"""Starting, monitoring, cancelling and retrying research runs."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.tenancy import owned_profile, owned_run
from app.config import get_settings
from app.db import get_session
from app.domain.enums import STAGE_ORDER, PipelineStage, UserDecision
from app.jobs.store import JobStore
from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    Job,
    JobStatus,
    ProgramResultRow,
    ResearchRun,
)
from app.models.base import ensure_utc
from app.pipeline.state import IN_PROGRESS_STAGES, RunState, is_lease_expired
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/runs", tags=["research"])


class StartRunIn(BaseModel):
    profile_id: str
    demo_mode: bool | None = Field(
        default=None, description="Defaults to the server setting; live mode fetches real sites."
    )
    candidate_limit: int | None = Field(
        default=None,
        ge=1,
        le=200,
        description="How many candidates to discover. Persisted on the run and reused on retry.",
    )
    verify_limit: int | None = Field(
        default=None,
        ge=1,
        le=200,
        description="How many candidates to verify in depth. Capped at candidate_limit.",
    )


class StageView(BaseModel):
    stage: str
    status: str
    detail: str = ""
    error: str = ""
    items_done: int = 0
    items_total: int = 0
    started_at: str | None = None
    finished_at: str | None = None


class RunView(BaseModel):
    id: str
    profile_id: str
    stage: str
    demo_mode: bool
    cancelled: bool
    progress: float
    candidates_found: int
    programs_verified: int
    pages_checked: int
    pages_failed: int
    claims_recorded: int
    candidate_limit: int
    verify_limit: int
    fetch_tiers: dict
    results_count: int
    decided_count: int
    stages: list[StageView]
    errors: list[str]
    #: Diagnostics that mean "the page was read and does not say". Separate
    #: from `errors` so the UI can stop presenting them as problems.
    unknowns: list[str] = []
    retry_urls: list[str]
    settings: dict
    created_at: str
    started_at: str | None
    finished_at: str | None
    job_running: bool
    job_error: str = ""
    job_id: str | None = None
    job_status: str | None = None
    job_attempts: int = 0
    #: True when the run claims to be working but its worker has gone silent.
    stale: bool = False
    worker_id: str | None = None
    heartbeat_at: str | None = None
    recovery_count: int = 0
    #: When the evidence in this run next ages out and is re-read automatically.
    next_recheck_at: str | None = None


def settings_default(name: str) -> int:
    return int(getattr(get_settings(), name))


def _view(session: Session, run: ResearchRun) -> RunView:
    state = RunState.load(run.stage_state)
    lease_seconds = get_settings().job_lease_seconds
    # The job the user is waiting on, which is not always the newest row: a
    # recheck is queued months ahead, and reporting it as this run's job made
    # every screen believe work was in flight for ever.
    now = datetime.now(UTC)
    job = (
        session.query(Job)
        .filter(Job.run_id == run.id, Job.available_at <= now)
        .order_by(Job.created_at.desc())
        .first()
    )
    # "Running" is a property of the job, not of the stage the run stopped at.
    job_running = job is not None and job.status == JobStatus.RUNNING.value
    lease_expiry = ensure_utc(job.lease_expires_at) if job else None
    stale = is_lease_expired(run.stage, run.heartbeat_at, lease_seconds=lease_seconds) or (
        job is not None
        and job.status == JobStatus.RUNNING.value
        and lease_expiry is not None
        and lease_expiry < datetime.now(UTC)
    )
    results = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id)
    return RunView(
        id=run.id,
        profile_id=run.profile_id,
        stage=run.stage,
        demo_mode=run.demo_mode,
        cancelled=run.cancelled,
        progress=state.progress(),
        candidates_found=run.candidates_found,
        programs_verified=run.programs_verified,
        pages_checked=run.pages_checked,
        pages_failed=run.pages_failed,
        claims_recorded=run.claims_recorded,
        candidate_limit=run.candidate_limit or settings_default("candidate_limit"),
        verify_limit=run.verify_limit or settings_default("verify_limit"),
        fetch_tiers=dict(run.fetch_tiers or {}),
        results_count=results.count(),
        decided_count=results.filter(
            ProgramResultRow.user_decision != UserDecision.UNDECIDED.value
        ).count(),
        stages=[
            StageView(stage=name, **{k: v for k, v in vars(st).items() if k != "stage"})
            for name, st in state.stages.items()
            if name not in ("queued",)
        ],
        errors=list(run.errors or []),
        unknowns=list(run.unknowns or []),
        retry_urls=list(run.retry_urls or []),
        settings=dict(run.settings_snapshot or {}),
        created_at=run.created_at.isoformat(),
        started_at=run.started_at.isoformat() if run.started_at else None,
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        # A run whose lease expired is not running, whatever its stage says.
        job_running=job_running and not stale,
        job_error=(job.last_error if job else ""),
        job_id=job.id if job else None,
        job_status=job.status if job else None,
        job_attempts=job.attempts if job else 0,
        stale=stale,
        worker_id=run.worker_id,
        heartbeat_at=run.heartbeat_at.isoformat() if run.heartbeat_at else None,
        recovery_count=run.recovery_count or 0,
        next_recheck_at=run.next_recheck_at.isoformat() if run.next_recheck_at else None,
    )


@router.post("", response_model=RunView, status_code=202)
def start_run(
    payload: StartRunIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    """Start research for one profile.

    Two guards, because they answer different questions. `Idempotency-Key`
    identifies one *click*: replaying it returns the run that click created,
    which is what a retried request or a double submit needs. The active-run
    check answers "is this profile already being researched?" and refuses a
    genuinely new request with 409, naming the run to join.
    """
    settings = get_settings()
    owned_profile(session, payload.profile_id, principal)

    if idempotency_key:
        replayed = (
            session.query(ResearchRun)
            .filter(
                ResearchRun.profile_id == payload.profile_id,
                ResearchRun.client_request_key == idempotency_key,
            )
            .first()
        )
        if replayed is not None:
            return _view(session, replayed)

    active = (
        session.query(ResearchRun)
        .filter(
            ResearchRun.profile_id == payload.profile_id,
            ResearchRun.cancelled.is_(False),
            ResearchRun.stage.in_([s.value for s in IN_PROGRESS_STAGES]),
        )
        .order_by(ResearchRun.created_at.desc())
        .first()
    )
    if active is not None:
        raise HTTPException(
            409,
            f"Research is already running for this applicant (run {active.id}). "
            "Wait for it to finish, or cancel it first.",
        )

    run = ResearchRun(
        client_request_key=idempotency_key,
        profile_id=payload.profile_id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=settings.demo_mode if payload.demo_mode is None else payload.demo_mode,
        candidate_limit=payload.candidate_limit,
        verify_limit=payload.verify_limit,
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="run_started",
            entity_type="run",
            entity_id=run.id,
            detail={"demo_mode": run.demo_mode},
        )
    )
    # One job per run. The request-level guards above are what stop a second
    # run being created in the first place; this key only keeps a retried
    # enqueue for the same run from queueing the work twice.
    JobStore(session).enqueue(
        "research",
        run_id=run.id,
        idempotency_key=f"research:{run.id}",
        priority=0,
    )
    session.commit()
    session.refresh(run)
    return _view(session, run)


@router.get("", response_model=list[RunView])
def list_runs(
    profile_id: str | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[RunView]:
    q = (
        session.query(ResearchRun)
        .join(ApplicantProfileRow, ResearchRun.profile_id == ApplicantProfileRow.id)
        .filter(ApplicantProfileRow.organization_id == principal.organization_id)
        .order_by(ResearchRun.created_at.desc())
    )
    if profile_id:
        q = q.filter(ResearchRun.profile_id == profile_id)
    return [_view(session, r) for r in q.limit(50).all()]


@router.get("/{run_id}", response_model=RunView)
def get_run(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    run = owned_run(session, run_id, principal)
    return _view(session, run)


@router.post("/{run_id}/cancel", response_model=RunView)
def cancel_run(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    """Ask the run to stop.

    The flag is the real signal: the worker observes it between units of work
    so cancellation lands at a consistent point instead of tearing a stage.
    """
    run = owned_run(session, run_id, principal)
    run.cancelled = True
    store = JobStore(session)
    for job in store.for_run(run_id):
        store.cancel(job.id)
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="run_cancel_requested",
            entity_type="run",
            entity_id=run_id,
            detail={},
        )
    )
    session.commit()
    session.refresh(run)
    return _view(session, run)


@router.post("/{run_id}/retry", response_model=RunView)
def retry_run(
    run_id: str,
    stage: Literal["candidate_discovery", "program_verification", "funding_discovery", "assessment"]
    | None = None,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    """Re-run a run, in whole or from one stage onwards.

    Naming a stage re-enters the pipeline there: that stage and every stage
    after it in STAGE_ORDER are reset, and the earlier ones keep their work.
    Without a stage every stage is reset, which is what "re-run everything"
    has to mean — resetting only the failed ones made a retry of a *successful*
    run skip the whole pipeline.

    Results are not deleted. `_persist_result` upserts on (run_id, dedupe_key),
    so a re-run refreshes rows in place and carries the user's decisions over;
    deleting them first is how a retry used to end with an empty shortlist.
    """
    run = owned_run(session, run_id, principal)
    store = JobStore(session)
    if any(j.status == JobStatus.RUNNING.value for j in store.for_run(run_id)):
        raise HTTPException(409, "This run is still executing; cancel it before retrying.")

    run.cancelled = False
    run.stage = PipelineStage.QUEUED.value
    run.errors = []
    run.retry_urls = []
    run.pages_checked = 0
    run.pages_failed = 0
    run.claims_recorded = 0
    run.programs_verified = 0
    state = RunState.load(run.stage_state)
    order = [s.value for s in STAGE_ORDER]
    from_index = order.index(stage) if stage else 0
    for name, st in state.stages.items():
        after_entry_point = name in order and order.index(name) >= from_index
        # A failed or half-run stage is always reset: leaving it "running" would
        # make the runner skip it and the run would stall in the same place.
        if after_entry_point or st.status in ("failed", "running"):
            st.status = "pending"
            st.error = ""
    run.stage_state = state.dump()
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="run_retried",
            entity_type="run",
            entity_id=run_id,
            detail={"from_stage": stage or "start"},
        )
    )
    # A new attempt gets a new idempotency key so it is not deduplicated
    # against the attempt the user is explicitly retrying.
    attempt = len(store.for_run(run_id)) + 1
    store.enqueue("research", run_id=run_id, idempotency_key=f"research:{run_id}:retry{attempt}")
    session.commit()
    session.refresh(run)
    return _view(session, run)


@router.post("/{run_id}/collect-documents", response_model=RunView, status_code=202)
def collect_documents(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    """Deep document collection, for approved and maybe rows only.

    Idempotent by *shortlist content*: the job key is a hash of the approved
    row ids, so pressing the button twice on the same shortlist is a no-op,
    while changing which programmes are approved always enqueues real work.
    Keying on the number of approved rows - the previous behaviour - made
    swapping one approval for another silently return the finished job, and
    the newly approved programme never received a checklist.

    A finished job for the same key is therefore a deliberate no-op, not a
    lost request: the documents it collected are still the right ones.
    """
    run = owned_run(session, run_id, principal)
    approved_ids = sorted(
        row.id
        for row in session.query(ProgramResultRow.id).filter(
            ProgramResultRow.run_id == run_id,
            ProgramResultRow.user_decision.in_(
                [UserDecision.APPROVED.value, UserDecision.MAYBE.value]
            ),
        )
    )
    approved = len(approved_ids)
    if approved == 0:
        raise HTTPException(
            400,
            "Approve at least one programme first — documents are only collected for shortlisted rows.",
        )
    run.cancelled = False
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="documents_requested",
            entity_type="run",
            entity_id=run_id,
            detail={"approved": approved},
        )
    )
    shortlist_digest = hashlib.sha256(",".join(approved_ids).encode()).hexdigest()[:16]
    JobStore(session).enqueue(
        "documents",
        run_id=run_id,
        idempotency_key=f"documents:{run_id}:{shortlist_digest}",
        priority=5,
    )
    session.commit()
    session.refresh(run)
    return _view(session, run)


@router.post("/{run_id}/recheck", response_model=RunView, status_code=202)
def recheck_now(
    run_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    """Re-read the evidence for this run now, instead of waiting for its date.

    The automatic recheck is queued for `next_recheck_at`; this is the same job
    made available immediately. Results are upserted and decisions are kept.
    """
    run = owned_run(session, run_id, principal)
    store = JobStore(session)
    if any(j.status == JobStatus.RUNNING.value for j in store.for_run(run_id)):
        raise HTTPException(409, "This run is still executing; wait for it to finish.")

    now = datetime.now(UTC)
    store.enqueue(
        "recheck",
        run_id=run_id,
        idempotency_key=f"recheck:{run_id}:manual:{now.isoformat(timespec='seconds')}",
        available_at=now,
        priority=0,
    )
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="run_recheck_requested",
            entity_type="run",
            entity_id=run_id,
            detail={},
        )
    )
    session.commit()
    session.refresh(run)
    return _view(session, run)
