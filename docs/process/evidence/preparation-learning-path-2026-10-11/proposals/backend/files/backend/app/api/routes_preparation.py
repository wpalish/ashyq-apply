"""Original preparation: owned-case practice with a separate, read-only term entitlement."""

from __future__ import annotations

from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.tenancy import owned_profile
from app.db import get_session
from app.domain.claim_scope import RequestedScope
from app.domain.enums import ClaimStatus
from app.domain.freshness import age_days, is_stale
from app.domain.preparation import NOTICE, combine_states, project_checks
from app.domain.study_schedule import build_schedule
from app.models import (
    ClaimRow,
    ConflictRow,
    ProgramResultRow,
    ResearchRun,
    StudyAttempt,
)
from app.models.base import ensure_utc, utcnow
from app.models.study_schedule import StudyScheduleRow
from app.payments.entitlements import has_full_access
from app.payments.preparation import preparation_access
from app.preparation.catalogue import (
    CONTENT_VERSION,
    LESSONS,
    catalogue,
)
from app.preparation.learning_pack import (
    PACK_VERSION,
    completed_lesson_refs,
    digest_dispatch,
    grade_dispatch,
    lesson_dispatch,
    pack_catalogue,
    use_learning_pack,
)
from app.schemas.claim import ClaimOut, Conflict
from app.schemas.preparation import (
    LearningPackCatalogue,
    LearningPackLesson,
    LearningPackProgress,
    LearningPackStudyAttemptIn,
    LearningPackStudyAttemptOut,
    PreparationAccess,
    PreparationCatalogue,
    PreparationLesson,
    PreparationPlan,
    PreparationProgress,
    StudyAttemptIn,
    StudyAttemptOut,
    StudyAttemptReview,
)
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RequirementCheck
from app.schemas.study_schedule import ScheduleSettings, ScheduleWrite, StudyScheduleOut
from app.security import Principal, get_principal

router = APIRouter(tags=["preparation"])


def _schedule_view(profile_id: str, row: StudyScheduleRow | None) -> StudyScheduleOut:
    if row is None:
        return StudyScheduleOut(
            profile_id=profile_id,
            revision=0,
            settings=None,
            schedule=None,
            updated_at=None,
        )
    try:
        settings = ScheduleSettings.model_validate(row.settings)
        today = utcnow().astimezone(ZoneInfo(settings.timezone)).date()
        schedule = build_schedule(settings, today=today)
    except ValueError as exc:
        raise HTTPException(422, "Saved study plan needs correction; reload its settings") from exc
    return StudyScheduleOut(
        profile_id=profile_id,
        revision=row.revision,
        settings=settings,
        schedule=schedule,
        updated_at=ensure_utc(row.updated_at),
    )


@router.get("/api/profiles/{profile_id}/preparation/schedule", response_model=StudyScheduleOut)
def read_schedule(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> StudyScheduleOut:
    owned_profile(session, profile_id, principal)
    row = session.query(StudyScheduleRow).filter(StudyScheduleRow.profile_id == profile_id).first()
    return _schedule_view(profile_id, row)


@router.put("/api/profiles/{profile_id}/preparation/schedule", response_model=StudyScheduleOut)
def save_schedule(
    profile_id: str,
    payload: ScheduleWrite,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> StudyScheduleOut:
    owned_profile(session, profile_id, principal)
    _require_access(session, principal)
    now = utcnow()
    today = now.astimezone(ZoneInfo(payload.settings.timezone)).date()
    try:
        generated = build_schedule(payload.settings, today=today)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not set(payload.settings.completed_task_ids).issubset(task.id for task in generated.tasks):
        raise HTTPException(422, "Task completion belongs to a different study calendar")
    query = session.query(StudyScheduleRow).filter(StudyScheduleRow.profile_id == profile_id)
    if payload.expected_revision == 0:
        row = StudyScheduleRow(
            profile_id=profile_id,
            revision=1,
            settings=payload.settings.model_dump(mode="json"),
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            if query.first() is None:
                raise
            raise HTTPException(
                409, "Study plan changed. Reload and review before saving."
            ) from exc
    else:
        changed = query.filter(StudyScheduleRow.revision == payload.expected_revision).update(
            {
                StudyScheduleRow.settings: payload.settings.model_dump(mode="json"),
                StudyScheduleRow.revision: payload.expected_revision + 1,
                StudyScheduleRow.updated_at: now,
            },
            synchronize_session=False,
        )
        if changed != 1:
            session.rollback()
            raise HTTPException(409, "Study plan changed. Reload and review before saving.")
        session.commit()
    return _schedule_view(profile_id, query.one())


def attempt_view(row: StudyAttempt) -> StudyAttemptOut | LearningPackStudyAttemptOut:
    created_at = ensure_utc(row.created_at)
    assert created_at is not None
    view = (
        LearningPackStudyAttemptOut
        if any("text" in answer for answer in row.answers)
        else StudyAttemptOut
    )
    return view(
        id=row.id,
        attempt_id=row.client_attempt_id,
        profile_id=row.profile_id,
        lesson_id=row.lesson_id,
        version=row.content_version,
        answers=row.answers,
        correct=row.correct,
        total=row.total,
        feedback=row.feedback,
        created_at=created_at,
    )


def _require_access(session: Session, principal: Principal) -> None:
    if not preparation_access(session, principal.organization_id).allowed:
        raise HTTPException(
            402,
            {
                "code": "preparation_subscription_required",
                "message": "An eligible started subscription term is required for preparation.",
            },
        )


@router.get(
    "/api/preparation/catalogue",
    response_model=PreparationCatalogue | LearningPackCatalogue,
)
def preparation_catalogue(
    catalogue_version: str | None = Query(None, min_length=1, max_length=40),
) -> PreparationCatalogue | LearningPackCatalogue:
    try:
        return pack_catalogue() if use_learning_pack(catalogue_version) else catalogue()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/profiles/{profile_id}/preparation/access", response_model=PreparationAccess)
def access(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PreparationAccess:
    owned_profile(session, profile_id, principal)
    return preparation_access(session, principal.organization_id)


@router.get(
    "/api/profiles/{profile_id}/preparation/lessons/{lesson_id}",
    response_model=PreparationLesson | LearningPackLesson,
)
def lesson(
    profile_id: str,
    lesson_id: str,
    version: str = Query(..., min_length=1, max_length=40),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PreparationLesson | LearningPackLesson:
    owned_profile(session, profile_id, principal)
    _require_access(session, principal)
    try:
        return lesson_dispatch(lesson_id, version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _replay(row: StudyAttempt, digest: str) -> StudyAttemptOut | LearningPackStudyAttemptOut:
    if row.request_digest != digest:
        raise HTTPException(409, "Attempt UUID already belongs to a different payload")
    return attempt_view(row)


@router.post(
    "/api/profiles/{profile_id}/preparation/attempts",
    response_model=StudyAttemptOut | LearningPackStudyAttemptOut,
)
def submit_attempt(
    profile_id: str,
    payload: StudyAttemptIn | LearningPackStudyAttemptIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> StudyAttemptOut | LearningPackStudyAttemptOut:
    owned_profile(session, profile_id, principal)
    client_id = str(payload.attempt_id)
    digest = digest_dispatch(payload)
    query = session.query(StudyAttempt).filter(
        StudyAttempt.profile_id == profile_id,
        StudyAttempt.client_attempt_id == client_id,
    )
    existing = query.first()
    if existing is not None:
        # An already-submitted receipt remains the applicant's data after the term ends.
        return _replay(existing, digest)
    _require_access(session, principal)
    try:
        answers, feedback, correct = grade_dispatch(payload)
    except ValueError as exc:
        # No answer keys or explanations are included in validation errors.
        raise HTTPException(422, str(exc)) from exc
    row = StudyAttempt(
        profile_id=profile_id,
        client_attempt_id=client_id,
        lesson_id=payload.lesson_id,
        content_version=payload.version,
        request_digest=digest,
        answers=answers,
        feedback=feedback,
        correct=correct,
        total=len(answers),
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Database uniqueness closes concurrent retries; every original argument stays bound.
        existing = query.first()
        if existing is None:
            raise
        return _replay(existing, digest)
    session.refresh(row)
    return attempt_view(row)


@router.get(
    "/api/profiles/{profile_id}/preparation/attempts/{attempt_uuid}/review",
    response_model=StudyAttemptReview,
)
def review_attempt(
    profile_id: str,
    attempt_uuid: UUID,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> StudyAttemptReview:
    owned_profile(session, profile_id, principal)
    row = (
        session.query(StudyAttempt)
        .filter(
            StudyAttempt.profile_id == profile_id,
            StudyAttempt.client_attempt_id == str(attempt_uuid),
        )
        .first()
    )
    if row is None:
        raise HTTPException(404, "Attempt not found")
    saved = attempt_view(row)
    try:
        original = lesson_dispatch(row.lesson_id, row.content_version)
    except ValueError:
        return StudyAttemptReview(
            attempt=saved,
            lesson=None,
            notice="The original lesson version is not available. This is the unchanged saved receipt; no replacement content or score is inferred.",
        )
    return StudyAttemptReview(
        attempt=saved,
        lesson=original,
        notice="Saved practice receipt and exact recorded content version. Familiar items are review, not unseen diagnosis or official scores.",
    )


@router.get(
    "/api/profiles/{profile_id}/preparation/progress",
    response_model=PreparationProgress | LearningPackProgress,
)
def progress(
    profile_id: str,
    limit: int = Query(20, ge=1, le=100),
    catalogue_version: str | None = Query(None, min_length=1, max_length=40),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PreparationProgress | LearningPackProgress:
    owned_profile(session, profile_id, principal)
    try:
        pack = use_learning_pack(catalogue_version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    query = session.query(StudyAttempt).filter(StudyAttempt.profile_id == profile_id)
    count, correct, total = query.with_entities(
        func.count(StudyAttempt.id),
        func.coalesce(func.sum(StudyAttempt.correct), 0),
        func.coalesce(func.sum(StudyAttempt.total), 0),
    ).one()
    known = {item.id for item in LESSONS}
    completed = sorted(
        {
            row[0]
            for row in query.with_entities(StudyAttempt.lesson_id)
            .filter(StudyAttempt.content_version == CONTENT_VERSION)
            .distinct()
            .all()
            if row[0] in known
        }
    )
    response = PreparationProgress(
        profile_id=profile_id,
        attempt_count=count,
        correct=correct,
        answered=total,
        completed_lesson_ids=completed,
        attempts=[
            attempt_view(row)
            for row in query.order_by(StudyAttempt.created_at.desc(), StudyAttempt.id.desc())
            .limit(limit)
            .all()
        ],
    )
    if pack:
        refs = completed_lesson_refs(
            [
                (row[0], row[1])
                for row in query.with_entities(StudyAttempt.lesson_id, StudyAttempt.content_version)
                .distinct()
                .all()
            ]
        )
        return LearningPackProgress(
            **response.model_dump(exclude={"completed_lesson_ids"}),
            completed_lesson_ids=sorted(ref.lesson_id for ref in refs),
            catalogue_version=PACK_VERSION,
            completed_lessons=refs,
        )
    return response


@router.get("/api/profiles/{profile_id}/preparation/plan", response_model=PreparationPlan)
def plan(
    profile_id: str,
    result_id: str | None = Query(None, min_length=1, max_length=32),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PreparationPlan:
    profile = owned_profile(session, profile_id, principal)
    research_access = has_full_access(session, principal.organization_id, profile_id)
    result = None
    if result_id is not None:
        result = (
            session.query(ProgramResultRow)
            .join(ResearchRun)
            .filter(
                ProgramResultRow.id == result_id,
                ResearchRun.profile_id == profile_id,
            )
            .first()
        )
        if result is None:
            raise HTTPException(404, "Result not found")
    if not research_access:
        return PreparationPlan(
            profile_id=profile_id,
            result_id=result_id,
            research_access=False,
            evidence_state="locked",
            checks=[],
            notice=NOTICE,
        )
    if result is None:
        return PreparationPlan(
            profile_id=profile_id,
            research_access=True,
            evidence_state="unknown",
            checks=[],
            notice=NOTICE,
        )
    now = utcnow()
    rows = (
        session.query(ClaimRow)
        .filter(
            ClaimRow.run_id == result.run_id,
            or_(ClaimRow.result_id == result.id, ClaimRow.result_id.is_(None)),
        )
        .all()
    )
    claims = []
    for row in rows:
        try:
            claim = ClaimOut.model_validate(
                {
                    **row.payload,
                    "id": row.id,
                    "status": row.status,
                    "source_url": row.source_url,
                    "accessed_at": row.accessed_at,
                }
            )
        except ValidationError:
            continue  # A malformed historical record cannot become evidence by guessing its fields.
        claim.is_stale = is_stale(claim.claim_type, claim.accessed_at, now) or claim.status in {
            ClaimStatus.POSSIBLY_STALE,
            ClaimStatus.SUPERSEDED,
        }
        claim.age_days = age_days(claim.accessed_at, now)
        claims.append(claim)
    conflict_rows = (
        session.query(ConflictRow)
        .filter(
            ConflictRow.run_id == result.run_id,
            or_(ConflictRow.result_id == result.id, ConflictRow.result_id.is_(None)),
            ConflictRow.unresolved.is_(True),
        )
        .all()
    )
    conflicts = []
    for conflict_row in conflict_rows:
        try:
            conflicts.append(Conflict.model_validate({**conflict_row.payload, "unresolved": True}))
        except ValidationError:
            # Unreadable conflict evidence cannot be silently treated as resolved.
            return PreparationPlan(
                profile_id=profile_id,
                result_id=result.id,
                research_access=True,
                evidence_state="conflicted",
                checks=[],
                notice=NOTICE,
            )
    try:
        checks = [
            RequirementCheck.model_validate(check)
            for check in result.payload.get("requirement_checks", [])
        ]
        applicant = ApplicantProfileIn.model_validate(profile.payload)
    except ValidationError:
        return PreparationPlan(
            profile_id=profile_id,
            result_id=result.id,
            research_access=True,
            evidence_state="unknown",
            checks=[],
            notice=NOTICE,
        )
    requested = RequestedScope(
        university=result.university,
        programme=result.program,
        degree=applicant.context.level.value,
        intake=f"{applicant.context.intake_term} {applicant.context.intake_year}",
        nationality=applicant.context.citizenship,
        residency=applicant.context.country_of_residence,
        qualification=applicant.context.education_system,
    )
    updated = ensure_utc(profile.updated_at)
    recorded = ensure_utc(result.created_at)
    stale_result = updated is not None and recorded is not None and updated > recorded
    projected = project_checks(
        checks, claims, requested, stale_result=stale_result, conflicts=conflicts
    )
    return PreparationPlan(
        profile_id=profile_id,
        result_id=result.id,
        research_access=True,
        evidence_state=combine_states([check.evidence_state for check in projected]),
        checks=projected,
        notice=NOTICE,
    )
