"""Small, explicit ownership checks shared by tenant-scoped routes."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ApplicantProfileRow, ResearchRun
from app.security import Principal


def owned_profile(session: Session, profile_id: str, principal: Principal) -> ApplicantProfileRow:
    row = (
        session.query(ApplicantProfileRow)
        .filter(
            ApplicantProfileRow.id == profile_id,
            ApplicantProfileRow.organization_id == principal.organization_id,
        )
        .first()
    )
    if row is None:
        # 404, not 403: do not reveal that another tenant owns this identifier.
        raise HTTPException(404, "Applicant case not found")
    return row


def owned_run(session: Session, run_id: str, principal: Principal) -> ResearchRun:
    row = (
        session.query(ResearchRun)
        .join(ApplicantProfileRow, ResearchRun.profile_id == ApplicantProfileRow.id)
        .filter(
            ResearchRun.id == run_id,
            ApplicantProfileRow.organization_id == principal.organization_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(404, "Research run not found")
    return row


def organization_for_run(session: Session, run: ResearchRun) -> str:
    profile = session.get(ApplicantProfileRow, run.profile_id)
    if profile is None:
        raise RuntimeError(f"profile {run.profile_id} for run {run.id} no longer exists")
    return profile.organization_id
