"""Profile CRUD, validation, grade-conversion offers, export and deletion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.domain.grades import METHODS, available_methods, propose_conversion
from app.domain.validation import validate_profile
from app.models import ApplicantProfileRow, AuditEvent, ResearchRun
from app.schemas.profile import (
    ApplicantProfile,
    ApplicantProfileIn,
    GradeValue,
    ProfileValidationReport,
)

router = APIRouter(prefix="/api/profiles", tags=["profile"])


def _to_out(row: ApplicantProfileRow) -> ApplicantProfile:
    return ApplicantProfile(
        **row.payload,
        id=row.id,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


@router.post("", response_model=ApplicantProfile, status_code=201)
def create_profile(profile: ApplicantProfileIn, session: Session = Depends(get_session)) -> ApplicantProfile:
    row = ApplicantProfileRow(
        display_name=profile.display_name, payload=profile.model_dump(mode="json")
    )
    session.add(row)
    session.flush()
    session.add(AuditEvent(actor="user", action="profile_created", entity_type="profile",
                           entity_id=row.id, detail={}))
    session.commit()
    return _to_out(row)


@router.get("", response_model=list[ApplicantProfile])
def list_profiles(session: Session = Depends(get_session)) -> list[ApplicantProfile]:
    rows = session.query(ApplicantProfileRow).order_by(ApplicantProfileRow.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.get("/{profile_id}", response_model=ApplicantProfile)
def get_profile(profile_id: str, session: Session = Depends(get_session)) -> ApplicantProfile:
    row = session.get(ApplicantProfileRow, profile_id)
    if row is None:
        raise HTTPException(404, "Profile not found")
    return _to_out(row)


@router.put("/{profile_id}", response_model=ApplicantProfile)
def update_profile(
    profile_id: str, profile: ApplicantProfileIn, session: Session = Depends(get_session)
) -> ApplicantProfile:
    row = session.get(ApplicantProfileRow, profile_id)
    if row is None:
        raise HTTPException(404, "Profile not found")
    row.payload = profile.model_dump(mode="json")
    row.display_name = profile.display_name
    session.add(AuditEvent(actor="user", action="profile_updated", entity_type="profile",
                           entity_id=row.id, detail={}))
    session.commit()
    session.refresh(row)
    return _to_out(row)


@router.post("/validate", response_model=ProfileValidationReport)
def validate(profile: ApplicantProfileIn) -> ProfileValidationReport:
    """Validate without saving, so the onboarding form can preview the impact."""
    return validate_profile(profile)


@router.get("/{profile_id}/validation", response_model=ProfileValidationReport)
def validation_report(profile_id: str, session: Session = Depends(get_session)) -> ProfileValidationReport:
    row = session.get(ApplicantProfileRow, profile_id)
    if row is None:
        raise HTTPException(404, "Profile not found")
    return validate_profile(ApplicantProfileIn.model_validate(row.payload))


@router.get("/conversions/methods")
def conversion_methods(scale_label: str = "") -> dict:
    """Offer grade conversions. Applying one is always the user's choice."""
    methods = available_methods(scale_label) if scale_label else list(METHODS.values())
    return {
        "methods": [
            {"key": m.key, "from_scale": m.from_scale, "to_scale": m.to_scale,
             "description": m.description, "source": m.source, "caveat": m.caveat}
            for m in methods
        ],
        "note": (
            "No conversion is ever applied automatically. Accepting one stores the method and "
            "its source alongside the converted value."
        ),
    }


@router.post("/conversions/preview", response_model=GradeValue)
def preview_conversion(grade: GradeValue, method_key: str) -> GradeValue:
    try:
        return propose_conversion(grade, method_key)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{profile_id}/export")
def export_profile(profile_id: str, session: Session = Depends(get_session)) -> dict:
    """Everything held about this applicant, in one document."""
    row = session.get(ApplicantProfileRow, profile_id)
    if row is None:
        raise HTTPException(404, "Profile not found")
    runs = session.query(ResearchRun).filter(ResearchRun.profile_id == profile_id).all()
    return {
        "profile": row.payload,
        "created_at": row.created_at.isoformat(),
        "runs": [
            {"id": r.id, "stage": r.stage, "demo_mode": r.demo_mode,
             "created_at": r.created_at.isoformat(), "results": len(r.results)}
            for r in runs
        ],
        "note": "This is the complete record held for this applicant.",
    }


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, session: Session = Depends(get_session)) -> Response:
    """Erase the applicant and every run, result and claim belonging to them."""
    row = session.get(ApplicantProfileRow, profile_id)
    if row is None:
        raise HTTPException(404, "Profile not found")
    run_ids = [r.id for r in session.query(ResearchRun).filter(ResearchRun.profile_id == profile_id)]
    session.delete(row)
    session.add(
        AuditEvent(actor="user", action="profile_deleted", entity_type="profile",
                   entity_id=profile_id, detail={"runs_removed": len(run_ids)})
    )
    session.commit()
    return Response(status_code=204)
