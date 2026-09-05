"""Starting, monitoring, cancelling and retrying research runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.paywall import require_full_access
from app.api.tenancy import owned_profile, owned_run
from app.config import get_settings
from app.db import get_session
from app.domain.enums import PipelineStage, UserDecision
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
from app.payments.entitlements import has_full_access
from app.pipeline.state import RunState, is_lease_expired
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


def settings_default(name: str) -> int:
    return int(getattr(get_settings(), name))


def _view(session: Session, run: ResearchRun) -> RunView:
    state = RunState.load(run.stage_state)
    job = session.query(Job).filter(Job.run_id == run.id).order_by(Job.created_at.desc()).first()
    # "Running" is a property of the job, not of the stage the run stopped at.
    job_running = job is not None and job.status == JobStatus.RUNNING.value
    lease_expiry = ensure_utc(job.lease_expires_at) if job else None
    stale = is_lease_expired(run.stage, run.heartbeat_at) or (
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
    )


@router.post("", response_model=RunView, status_code=202)
def start_run(
    payload: StartRunIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> RunView:
    settings = get_settings()
    owned_profile(session, payload.profile_id, principal)

    # An unpaid case is not merely shown less — it is allowed to fetch less, so
    # a free run costs us little. Paying afterwards cannot widen this run; it
    # queues a new one.
    full_access = has_full_access(session, principal.organization_id, payload.profile_id)
    if not full_access:
        # A school with quota gets a full run without being asked. The unit is
        # spent here, once, when the case is actually opened.
        from app.payments.subscriptions import consume_for_case

        full_access = consume_for_case(
            session,
            organization_id=principal.organization_id,
            profile_id=payload.profile_id,
        ).granted

    candidate_limit = payload.candidate_limit
    if not full_access:
        candidate_limit = min(candidate_limit or settings.free_candidate_limit,
                              settings.free_candidate_limit)

    run = ResearchRun(
        profile_id=payload.profile_id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=settings.demo_mode if payload.demo_mode is None else payload.demo_mode,
        candidate_limit=candidate_limit,
        verify_limit=payload.verify_limit,
        access_tier="full" if full_access else "free",
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
    # Idempotent by run: a retried request or a double click cannot start the
    # same research twice.
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
    """Re-run a failed run.

    A stage can be named to re-enter the pipeline there; without one the run
    restarts from discovery. Existing results are cleared first so a retry
    cannot silently double up rows.
    """
    run = owned_run(session, run_id, principal)
    store = JobStore(session)
    if any(j.status == JobStatus.RUNNING.value for j in store.for_run(run_id)):
        raise HTTPException(409, "This run is still executing; cancel it before retrying.")

    session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).delete()
    run.cancelled = False
    run.stage = PipelineStage.QUEUED.value
    run.errors = []
    run.retry_urls = []
    run.pages_checked = 0
    run.pages_failed = 0
    run.claims_recorded = 0
    run.programs_verified = 0
    state = RunState.load(run.stage_state)
    for name, st in state.stages.items():
        if st.status in ("failed", "running") or (stage and name == stage):
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
    """Deep document collection, for approved and maybe rows only."""
    require_full_access(session, run_id, principal)
    run = owned_run(session, run_id, principal)
    approved = (
        session.query(ProgramResultRow)
        .filter(
            ProgramResultRow.run_id == run_id,
            ProgramResultRow.user_decision.in_(
                [UserDecision.APPROVED.value, UserDecision.MAYBE.value]
            ),
        )
        .count()
    )
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
    JobStore(session).enqueue(
        "documents",
        run_id=run_id,
        idempotency_key=f"documents:{run_id}:{approved}",
        priority=5,
    )
    session.commit()
    session.refresh(run)
    return _view(session, run)
