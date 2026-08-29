"""Applicant cases: multiple profiles inside one organization."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ApplicantProfileRow, ResearchRun
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseView(BaseModel):
    id: str
    profile_id: str
    display_name: str
    status: str
    run_count: int
    created_at: str
    updated_at: str


@router.get("", response_model=list[CaseView])
def list_cases(
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[CaseView]:
    rows = (
        session.query(ApplicantProfileRow, func.count(ResearchRun.id))
        .outerjoin(ResearchRun, ResearchRun.profile_id == ApplicantProfileRow.id)
        .filter(ApplicantProfileRow.organization_id == principal.organization_id)
        .group_by(ApplicantProfileRow.id)
        .order_by(ApplicantProfileRow.updated_at.desc())
        .all()
    )
    return [
        CaseView(
            id=profile.id,
            profile_id=profile.id,
            display_name=profile.display_name,
            status="active",
            run_count=int(run_count),
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
        )
        for profile, run_count in rows
    ]
