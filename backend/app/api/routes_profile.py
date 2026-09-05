"""Profile CRUD, validation, grade-conversion offers, export and deletion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.adapters.extraction import pdf_to_text
from app.api.tenancy import owned_profile
from app.db import get_session
from app.domain.grades import METHODS, available_methods, propose_conversion
from app.domain.transcript import suggest_from_transcript
from app.domain.validation import validate_profile
from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    ClaimRow,
    ConflictRow,
    ProgramResultRow,
    ResearchRun,
)
from app.schemas.profile import (
    ApplicantProfile,
    ApplicantProfileIn,
    GradeValue,
    ProfileValidationReport,
)
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/profiles", tags=["profile"])


def _to_out(row: ApplicantProfileRow) -> ApplicantProfile:
    return ApplicantProfile(
        **row.payload,
        id=row.id,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


@router.post("", response_model=ApplicantProfile, status_code=201)
def create_profile(
    profile: ApplicantProfileIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ApplicantProfile:
    row = ApplicantProfileRow(
        organization_id=principal.organization_id,
        display_name=profile.display_name,
        payload=profile.model_dump(mode="json"),
    )
    session.add(row)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="profile_created",
            entity_type="profile",
            entity_id=row.id,
            detail={},
        )
    )
    session.commit()
    return _to_out(row)


@router.get("", response_model=list[ApplicantProfile])
def list_profiles(
    response: Response,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> list[ApplicantProfile]:
    """A page of applicants, newest first.

    The total travels in X-Total-Count rather than wrapping the array: the
    frontend already treats this response as a list, and a counsellor with
    three hundred applicants was previously sent all of them on every load.
    """
    query = session.query(ApplicantProfileRow).filter(
        ApplicantProfileRow.organization_id == principal.organization_id
    )
    response.headers["X-Total-Count"] = str(query.count())
    rows = query.order_by(ApplicantProfileRow.created_at.desc()).limit(limit).offset(offset).all()
    return [_to_out(r) for r in rows]


@router.get("/{profile_id}", response_model=ApplicantProfile)
def get_profile(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ApplicantProfile:
    row = owned_profile(session, profile_id, principal)
    return _to_out(row)


@router.put("/{profile_id}", response_model=ApplicantProfile)
def update_profile(
    profile_id: str,
    profile: ApplicantProfileIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ApplicantProfile:
    row = owned_profile(session, profile_id, principal)
    row.payload = profile.model_dump(mode="json")
    row.display_name = profile.display_name
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="profile_updated",
            entity_type="profile",
            entity_id=row.id,
            detail={},
        )
    )
    session.commit()
    session.refresh(row)
    return _to_out(row)


@router.post("/validate", response_model=ProfileValidationReport)
def validate(
    profile: ApplicantProfileIn,
    _principal: Principal = Depends(get_principal),
) -> ProfileValidationReport:
    """Validate without saving, so the onboarding form can preview the impact."""
    return validate_profile(profile)


#: A school transcript is a few pages. Ten megabytes is generous for a scan and
#: small enough that parsing one cannot be used to occupy a worker: pypdf's own
#: advisories include denial of service on malformed input.
MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024


@router.post("/transcript")
async def read_transcript(
    file: UploadFile = File(...),
    _principal: Principal = Depends(get_principal),
) -> dict:
    """Read a transcript PDF into suggestions. Nothing is saved, here or later.

    The applicant already has these numbers on a document; typing them again is
    where a 4.82 becomes a 4.28. The answer is a list of proposals, each
    quoting the line it came from, and the screen applies only what the person
    confirms — the same rule as a grade conversion, which is offered and never
    applied on the applicant's behalf.

    The upload is held in memory for the length of the request and then
    discarded. It is never written to disk, never attached to the profile, and
    never leaves the process.
    """
    if (file.content_type or "").split(";")[0].strip() not in (
        "application/pdf",
        "application/x-pdf",
    ):
        raise HTTPException(400, "Upload the transcript as a PDF.")

    # Read one byte past the cap: a file exactly at the limit is fine, and a
    # larger one is refused without ever holding all of it.
    data = await file.read(MAX_TRANSCRIPT_BYTES + 1)
    if len(data) > MAX_TRANSCRIPT_BYTES:
        raise HTTPException(413, "That file is larger than 10 MB. Upload the transcript alone.")
    if not data:
        raise HTTPException(400, "That file is empty.")

    text = pdf_to_text(data)
    if not text.strip():
        # A scan with no text layer is the ordinary case here, not a failure:
        # say which it is, because the two need different things from the user.
        return {
            "suggestions": [],
            "note": (
                "No text could be read from that PDF. If it is a photograph or a scan, the "
                "words are an image and there is nothing to read; type the values instead."
            ),
        }

    suggestions = suggest_from_transcript(text)
    return {
        "suggestions": [
            {
                "field": s.field,
                "label": s.label,
                "value": s.value,
                "excerpt": s.excerpt,
            }
            for s in suggestions
        ],
        "note": (
            "Nothing has been saved. Check each value against your own document and apply "
            "the ones that are right."
            if suggestions
            else (
                "The document was read, but it does not state a grade average with its scale, "
                "or a graduation date, in a form that can be quoted back to you."
            )
        ),
    }


@router.get("/{profile_id}/validation", response_model=ProfileValidationReport)
def validation_report(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ProfileValidationReport:
    row = owned_profile(session, profile_id, principal)
    return validate_profile(ApplicantProfileIn.model_validate(row.payload))


@router.get("/conversions/methods")
def conversion_methods(scale_label: str = "") -> dict:
    """Offer grade conversions. Applying one is always the user's choice."""
    methods = available_methods(scale_label) if scale_label else list(METHODS.values())
    return {
        "methods": [
            {
                "key": m.key,
                "from_scale": m.from_scale,
                "to_scale": m.to_scale,
                "description": m.description,
                "source": m.source,
                "caveat": m.caveat,
            }
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
def export_profile(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> dict:
    """Everything held about this applicant, in one document.

    It used to say "the complete record" while carrying the profile and a count
    of results - not the results themselves, not a single claim, not one audit
    line. A person exercising a data right was handed a summary and told it was
    everything.
    """
    row = owned_profile(session, profile_id, principal)
    runs = session.query(ResearchRun).filter(ResearchRun.profile_id == profile_id).all()
    run_ids = [r.id for r in runs]

    results = (
        session.query(ProgramResultRow).filter(ProgramResultRow.run_id.in_(run_ids)).all()
        if run_ids
        else []
    )
    claims = session.query(ClaimRow).filter(ClaimRow.run_id.in_(run_ids)).all() if run_ids else []
    conflicts = (
        session.query(ConflictRow).filter(ConflictRow.run_id.in_(run_ids)).all() if run_ids else []
    )
    # Audit events for this applicant's own entities, within their tenant.
    entity_ids = {profile_id, *run_ids, *[r.id for r in results]}
    audit = (
        session.query(AuditEvent)
        .filter(
            AuditEvent.organization_id == principal.organization_id,
            AuditEvent.entity_id.in_(entity_ids),
        )
        .order_by(AuditEvent.created_at)
        .all()
    )

    return {
        "profile": row.payload,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "runs": [
            {
                "id": r.id,
                "stage": r.stage,
                "demo_mode": r.demo_mode,
                "created_at": r.created_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "settings": dict(r.settings_snapshot or {}),
                "errors": list(r.errors or []),
                "unknowns": list(r.unknowns or []),
                "results": sum(1 for result in results if result.run_id == r.id),
            }
            for r in runs
        ],
        "results": [
            {
                "id": result.id,
                "run_id": result.run_id,
                "user_decision": result.user_decision,
                "user_decision_reason": result.user_decision_reason,
                "user_notes": result.user_notes,
                "decided_at": result.decided_at.isoformat() if result.decided_at else None,
                "checklist": result.checklist,
                **result.payload,
            }
            for result in results
        ],
        "claims": [
            {
                "id": c.id,
                "run_id": c.run_id,
                "result_id": c.result_id,
                "accessed_at": c.accessed_at.isoformat() if c.accessed_at else None,
                **c.payload,
            }
            for c in claims
        ],
        "conflicts": [
            {"id": c.id, "run_id": c.run_id, "result_id": c.result_id, **c.payload}
            for c in conflicts
        ],
        "audit": [
            {
                "id": event.id,
                "created_at": event.created_at.isoformat(),
                "actor": event.actor,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "detail": event.detail,
            }
            for event in audit
        ],
        "counts": {
            "runs": len(runs),
            "results": len(results),
            "claims": len(claims),
            "conflicts": len(conflicts),
            "audit_events": len(audit),
        },
        "note": (
            "This is the complete record held for this applicant: the profile, every run, "
            "every result with the decisions and notes on it, every claim and conflict behind "
            "those results, and the audit trail. Deleting the applicant removes all of it."
        ),
    }


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> Response:
    """Erase the applicant and every run, result and claim belonging to them."""
    row = owned_profile(session, profile_id, principal)
    run_ids = [
        r.id for r in session.query(ResearchRun).filter(ResearchRun.profile_id == profile_id)
    ]
    session.delete(row)
    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="profile_deleted",
            entity_type="profile",
            entity_id=profile_id,
            detail={"runs_removed": len(run_ids)},
        )
    )
    session.commit()
    return Response(status_code=204)
