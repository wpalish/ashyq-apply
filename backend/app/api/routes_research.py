"""Starting, monitoring, cancelling and retrying research runs."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.domain.enums import PipelineStage, UserDecision
from app.models import ApplicantProfileRow, AuditEvent, ProgramResultRow, ResearchRun
from app.pipeline.queue import queue
from app.pipeline.state import RunState, is_lease_expired

router = APIRouter(prefix="/api/runs", tags=["research"])


class StartRunIn(BaseModel):
    profile_id: str
    demo_mode: bool | None = Field(
        default=None, description="Defaults to the server setting; live mode fetches real sites."
    )
    candidate_limit: int | None = Field(
        default=None, ge=1, le=200,
        description="How many candidates to discover. Persisted on the run and reused on retry.",
    )
    verify_limit: int | None = Field(
        default=None, ge=1, le=200,
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
    #: True when the run claims to be working but its worker has gone silent.
    stale: bool = False
    worker_id: str | None = None
    heartbeat_at: str | None = None
    recovery_count: int = 0


def settings_default(name: str) -> int:
    return int(getattr(get_settings(), name))


def _view(session: Session, run: ResearchRun) -> RunView:
    state = RunState.load(run.stage_state)
    handle = queue.get(run.id)
    stale = is_lease_expired(run.stage, run.heartbeat_at)
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
        decided_count=results.filter(ProgramResultRow.user_decision != UserDecision.UNDECIDED.value).count(),
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
        job_running=bool(handle and not handle.done) and not stale,
        job_error=handle.error if handle else "",
        stale=stale,
        worker_id=run.worker_id,
        heartbeat_at=run.heartbeat_at.isoformat() if run.heartbeat_at else None,
        recovery_count=run.recovery_count or 0,
    )


@router.post("", response_model=RunView, status_code=202)
def start_run(payload: StartRunIn, session: Session = Depends(get_session)) -> RunView:
    settings = get_settings()
    profile = session.get(ApplicantProfileRow, payload.profile_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")

    run = ResearchRun(
        profile_id=payload.profile_id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=settings.demo_mode if payload.demo_mode is None else payload.demo_mode,
        candidate_limit=payload.candidate_limit,
        verify_limit=payload.verify_limit,
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    session.add(AuditEvent(actor="user", action="run_started", entity_type="run",
                           entity_id=run.id, detail={"demo_mode": run.demo_mode}))
    session.commit()
    session.refresh(run)
    queue.submit(run.id, "research")
    return _view(session, run)


@router.get("", response_model=list[RunView])
def list_runs(profile_id: str | None = None, session: Session = Depends(get_session)) -> list[RunView]:
    q = session.query(ResearchRun).order_by(ResearchRun.created_at.desc())
    if profile_id:
        q = q.filter(ResearchRun.profile_id == profile_id)
    return [_view(session, r) for r in q.limit(50).all()]


@router.get("/{run_id}", response_model=RunView)
def get_run(run_id: str, session: Session = Depends(get_session)) -> RunView:
    run = session.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return _view(session, run)


@router.post("/{run_id}/cancel", response_model=RunView)
def cancel_run(run_id: str, session: Session = Depends(get_session)) -> RunView:
    if not queue.cancel(run_id):
        raise HTTPException(404, "Run not found")
    session.expire_all()
    run = session.get(ResearchRun, run_id)
    return _view(session, run)


@router.post("/{run_id}/retry", response_model=RunView)
def retry_run(
    run_id: str,
    stage: Literal["candidate_discovery", "program_verification", "funding_discovery", "assessment"] | None = None,
    session: Session = Depends(get_session),
) -> RunView:
    """Re-run a failed run.

    A stage can be named to re-enter the pipeline there; without one the run
    restarts from discovery. Existing results are cleared first so a retry
    cannot silently double up rows.
    """
    run = session.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    handle = queue.get(run_id)
    if handle and not handle.done:
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
    session.add(AuditEvent(actor="user", action="run_retried", entity_type="run",
                           entity_id=run_id, detail={"from_stage": stage or "start"}))
    session.commit()
    session.refresh(run)
    queue.submit(run_id, "research")
    return _view(session, run)


@router.post("/{run_id}/collect-documents", response_model=RunView, status_code=202)
def collect_documents(run_id: str, session: Session = Depends(get_session)) -> RunView:
    """Deep document collection, for approved and maybe rows only."""
    run = session.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
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
            400, "Approve at least one programme first — documents are only collected for shortlisted rows."
        )
    run.cancelled = False
    session.add(AuditEvent(actor="user", action="documents_requested", entity_type="run",
                           entity_id=run_id, detail={"approved": approved}))
    session.commit()
    session.refresh(run)
    queue.submit(run_id, "documents")
    return _view(session, run)
