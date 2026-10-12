"""Owned personal shared route: immutable ACK/history and current safe G1 views.

No provider, network, private G1 assembly, score write or legacy schedule DML.
GET/export/replay read the accepted allocation; only preview/new PUT allocate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.preparation_transactions import begin_owned_preparation_write
from app.api.routes_preparation import review_attempt
from app.api.routes_preparation_graph import preparation_graph
from app.api.tenancy import owned_profile
from app.db import get_session
from app.domain.learning_schedule import settings_fingerprint
from app.domain.shared_route_allocator import allocate_shared_v1
from app.models.applicant import ApplicantProfileRow
from app.models.auth import OrganizationMembership, User
from app.models.base import ensure_utc, utcnow
from app.models.research import ProgramResultRow, ResearchRun
from app.models.shared_route import SharedRouteCurrentRow, SharedRouteHistoryRow
from app.models.study_schedule import StudyScheduleRow
from app.payments.entitlements import has_full_access
from app.payments.preparation import preparation_access
from app.preparation.catalogue import EXAMS
from app.preparation.learning_pack import lesson_dispatch
from app.schemas.learning_schedule import AttemptReviewRef, LessonRef
from app.schemas.preparation import StudyAttemptReview
from app.schemas.preparation_graph import PreparationGraph
from app.schemas.preparation_graph_loader import assert_finite_floats
from app.schemas.shared_route import (
    CATALOGUE_VERSION,
    EXACT_LESSONS,
    PLANNER_VERSION,
    ContentState,
    ContentStatusV1,
    CurrentRouteStatusV1,
    ExactCatalogueLesson,
    FrozenExactCatalogue,
    GoalReason,
    GoalState,
    GoalStatusV1,
    LegacyAnchor,
    PerGoalDigest,
    ReviewCode,
    ReviewReasonV1,
    SharedRouteCurrentOutV1,
    SharedRouteInputV1,
    SharedRoutePreviewOutV1,
    SharedRoutePreviewRequestV1,
    SharedRouteViewV1,
    SharedRouteWriteReceiptV1,
    SharedRouteWriteV1,
    ValidatedOwnedReviewV1,
    shared_input_wire,
    shared_preview_fingerprint,
    shared_request_digest,
)
from app.schemas.study_schedule import ScheduleSettings
from app.security import Principal, get_principal

router = APIRouter(tags=["preparation"])
_PARSE_FAILURES = (ValidationError, ValueError, TypeError, PydanticSerializationError)
_REVISION_CONFLICT = {
    "code": "shared_route_revision_conflict",
    "message": "Shared route changed. Reload and review before saving.",
}
_UUID_CONFLICT = {
    "code": "shared_route_uuid_conflict",
    "message": "This write UUID belongs to a different request. Keep and reconcile the original request.",
}
_PREVIEW_STALE = {
    "code": "shared_route_preview_stale",
    "message": "Preview changed or its local date expired. Review a fresh preview before saving.",
}
_UNREADABLE = {
    "code": "shared_route_saved_unreadable",
    "message": "Saved shared route cannot be read safely. No repair or replacement was made.",
}
_UNCONFIRMED = {
    "code": "shared_route_write_unconfirmed",
    "message": "Write could not be confirmed. Keep the draft and retry the exact original UUID and request.",
}
_GOAL_CODES: dict[GoalReason, ReviewCode] = {
    "decision_changed": "goal_decision_changed",
    "result_unavailable": "goal_result_unavailable",
    "research_locked": "goal_research_locked",
    "source_changed": "goal_source_changed",
    "evidence_unknown": "goal_evidence_unknown",
}
_CONTENT_CODES: dict[ContentState, ReviewCode] = {
    "available": "content_unknown",  # The available branch adds no reason.
    "version_unavailable": "content_version_unavailable",
    "review_unavailable": "own_review_unavailable",
    "unknown": "content_unknown",
}
_LEGACY_CODES: dict[Literal["changed", "unknown"], ReviewCode] = {
    "changed": "legacy_structure_changed",
    "unknown": "legacy_structure_unknown",
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _assert_actor(session: Session, principal: Principal) -> None:
    # Actual development principals have the same real native rows; no bypass.
    actor = (
        session.query(User.id)
        .filter(User.id == principal.user_id, User.is_active.is_(True))
        .first()
    )
    membership = (
        session.query(OrganizationMembership.user_id)
        .filter(
            OrganizationMembership.user_id == principal.user_id,
            OrganizationMembership.organization_id == principal.organization_id,
        )
        .first()
    )
    if actor is None or membership is None:
        raise HTTPException(401, "Authentication required.")


def _history_receipt(row: SharedRouteHistoryRow) -> SharedRouteWriteReceiptV1:
    try:
        if not isinstance(row.receipt, dict):
            raise ValueError("Receipt must be a JSON object")
        json.dumps(row.receipt, allow_nan=False)
        receipt = SharedRouteWriteReceiptV1.model_validate(row.receipt)
        if (
            receipt.profile_id != row.profile_id
            or receipt.revision != row.revision
            or str(receipt.client_write_uuid) != row.client_write_uuid
            or receipt.canonical_request_digest != row.request_digest
            or receipt.accepted_at != ensure_utc(row.accepted_at)
            or row.origin != "applicant_confirmed"
        ):
            raise ValueError("History columns and immutable receipt disagree")
        return receipt
    except _PARSE_FAILURES as exc:
        raise HTTPException(503, _UNREADABLE) from exc


def _current_receipt(session: Session, row: SharedRouteCurrentRow) -> SharedRouteWriteReceiptV1:
    try:
        if not isinstance(row.snapshot, dict):
            raise ValueError("Current snapshot must be a JSON object")
        json.dumps(row.snapshot, allow_nan=False)
        receipt = SharedRouteWriteReceiptV1.model_validate(row.snapshot)
        if (
            receipt.profile_id != row.profile_id
            or receipt.revision != row.revision
            or receipt.schema_version != row.schema_version
            or receipt.snapshot_digest != row.digest
            or receipt.accepted_at != ensure_utc(row.updated_at)
        ):
            raise ValueError("Current columns and immutable receipt disagree")
        history = (
            session.query(SharedRouteHistoryRow)
            .filter(
                SharedRouteHistoryRow.profile_id == row.profile_id,
                SharedRouteHistoryRow.revision == row.revision,
            )
            .first()
        )
        if history is None or _history_receipt(history).model_dump(
            mode="json"
        ) != receipt.model_dump(mode="json"):
            raise ValueError("Current has no exact matching accepted history")
        return receipt
    except _PARSE_FAILURES as exc:
        raise HTTPException(503, _UNREADABLE) from exc


def _current_row(session: Session, profile_id: str) -> SharedRouteCurrentRow | None:
    latest = (
        session.query(
            SharedRouteHistoryRow.profile_id,
            func.max(SharedRouteHistoryRow.revision).label("accepted_revision"),
        )
        .filter(SharedRouteHistoryRow.profile_id == profile_id)
        .group_by(SharedRouteHistoryRow.profile_id)
        .subquery()
    )
    pair = (
        session.query(SharedRouteCurrentRow, latest.c.accepted_revision)
        .select_from(ApplicantProfileRow)
        .outerjoin(
            SharedRouteCurrentRow, SharedRouteCurrentRow.profile_id == ApplicantProfileRow.id
        )
        .outerjoin(latest, latest.c.profile_id == ApplicantProfileRow.id)
        .filter(ApplicantProfileRow.id == profile_id)
        .populate_existing()
        .first()
    )
    if pair is None:
        raise HTTPException(404, "Applicant case not found")
    row, revision = pair
    # One statement observes both sides of their atomic commit; two independent
    # current/latest reads could falsely flag a legitimate intervening save.
    if (row is None and revision is not None) or (row is not None and row.revision != revision):
        # A broken pointer must not look like an empty case/reset revision zero.
        raise HTTPException(503, _UNREADABLE)
    return row


def _accepted_uuid(
    session: Session, profile_id: str, payload: SharedRouteWriteV1, request_digest: str
) -> SharedRouteWriteReceiptV1 | None:
    row = (
        session.query(SharedRouteHistoryRow)
        .filter(
            SharedRouteHistoryRow.profile_id == profile_id,
            SharedRouteHistoryRow.client_write_uuid == str(payload.client_write_uuid),
        )
        .first()
    )
    if row is None:
        return None
    receipt = _history_receipt(row)
    if receipt.canonical_request_digest != request_digest:
        raise HTTPException(409, _UUID_CONFLICT)
    return receipt


def _fresh_uuid_reconcile(
    session: Session,
    profile_id: str,
    principal: Principal,
    payload: SharedRouteWriteV1,
    request_digest: str,
) -> SharedRouteWriteReceiptV1 | None:
    # Caller has already fully rolled back; no allocator/source/term gates.
    try:
        with session.no_autoflush:
            owned_profile(session, profile_id, principal)
            _assert_actor(session, principal)
            return _accepted_uuid(session, profile_id, payload, request_digest)
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, _UNCONFIRMED) from exc


def _require_preparation(session: Session, principal: Principal, now: datetime) -> None:
    if not preparation_access(session, principal.organization_id, now=now).allowed:
        raise HTTPException(
            402,
            {
                "code": "preparation_subscription_required",
                "message": "An eligible started subscription term is required for preparation.",
            },
        )


def _legacy_anchor(session: Session, profile_id: str) -> LegacyAnchor:
    row = (
        session.query(StudyScheduleRow)
        .filter(StudyScheduleRow.profile_id == profile_id)
        .populate_existing()
        .first()
    )
    if row is None:
        return LegacyAnchor(technical_revision=0, structural_fingerprint=None)
    try:
        assert_finite_floats(row.settings)
        settings = ScheduleSettings.model_validate(row.settings)
        return LegacyAnchor(
            technical_revision=row.revision,
            structural_fingerprint=settings_fingerprint(settings),
        )
    except _PARSE_FAILURES as exc:
        raise HTTPException(
            503,
            {
                "code": "shared_route_legacy_unreadable",
                "message": "The saved legacy calendar needs review before a new shared preview.",
            },
        ) from exc


def _checked_graph(
    value: PreparationGraph, profile_id: str, result_ids: list[str]
) -> PreparationGraph:
    assert_finite_floats(value.model_dump(mode="python"))
    graph = PreparationGraph.model_validate(value.model_dump(mode="python"))
    assert_finite_floats(graph.model_dump(mode="python"))
    if (
        graph.profile_id != profile_id
        or graph.requested_result_ids != result_ids
        or graph.selected_result_ids != result_ids
        or [item.result_id for item in graph.source_manifest] != result_ids
        or graph.selection_source != "server_verified_owned_explicit"
    ):
        raise ValueError("Native graph does not match the complete explicit owner selection")
    return graph


def _strict_graph(
    session: Session, profile_id: str, principal: Principal, result_ids: list[str]
) -> PreparationGraph:
    try:
        return _checked_graph(
            preparation_graph(
                profile_id=profile_id,
                result_id=list(result_ids),
                principal=principal,
                session=session,
            ),
            profile_id,
            result_ids,
        )
    except _PARSE_FAILURES as exc:
        raise HTTPException(
            503,
            {
                "code": "shared_route_evidence_unreadable",
                "message": "Current programme evidence cannot be bound safely; no plan was saved.",
            },
        ) from exc


def _source_references(graph: PreparationGraph) -> list[PerGoalDigest]:
    programmes = {item.result_id: item for item in graph.programmes}
    return [
        PerGoalDigest(
            result_id=item.result_id,
            reference_digest=None
            if (
                not programmes[item.result_id].research_access
                or programmes[item.result_id].projection_state in {"locked", "unavailable"}
            )
            else _digest(
                {
                    "schema_version": "shared-route-goal-reference-v1",
                    "g1_schema_version": graph.schema_version,
                    "profile_id": graph.profile_id,
                    "manifest": item.model_dump(mode="json"),
                }
            ),
        )
        for item in graph.source_manifest
    ]


def _freeze_catalogue() -> FrozenExactCatalogue:
    lessons = []
    for lesson_id, track, version in EXACT_LESSONS:
        try:
            lesson = lesson_dispatch(lesson_id, version)
            available = (
                lesson.id == lesson_id and lesson.version == version and lesson.track_id == track
            )
        except ValueError:
            available = False
        lessons.append(
            ExactCatalogueLesson(
                ref=LessonRef(
                    id=f"lesson:{lesson_id}:{version}", lesson_id=lesson_id, content_version=version
                ),
                track=track,
                available=available,
            )
        )
    return FrozenExactCatalogue(lessons=lessons)


def _checked_review(
    session: Session, profile_id: str, principal: Principal, ref: AttemptReviewRef
) -> StudyAttemptReview:
    native = review_attempt(
        profile_id=profile_id, attempt_uuid=ref.attempt_id, principal=principal, session=session
    )
    assert_finite_floats(native.model_dump(mode="python"))
    review = StudyAttemptReview.model_validate(native.model_dump(mode="python"))
    if (
        review.attempt.profile_id != profile_id
        or review.attempt.attempt_id != ref.attempt_id
        or review.attempt.lesson_id != ref.lesson_id
        or review.attempt.version != ref.content_version
    ):
        raise ValueError("The owned receipt does not match the exact selected reference")
    return review


def _owned_review_snapshot(
    session: Session, profile_id: str, principal: Principal, value: SharedRouteInputV1
) -> list[ValidatedOwnedReviewV1]:
    snapshots = []
    registry = {(lesson_id, version): track for lesson_id, track, version in EXACT_LESSONS}
    for requested in value.own_reviews:
        try:
            native = _checked_review(session, profile_id, principal, requested.ref)
        except _PARSE_FAILURES as exc:
            raise HTTPException(
                422,
                {
                    "code": "review_reference_mismatch",
                    "message": "An own review must retain its exact saved lesson, version and UUID.",
                },
            ) from exc
        lesson = native.lesson
        track = registry.get((requested.ref.lesson_id, requested.ref.content_version))
        if (
            lesson is None
            or track is None
            or lesson.id != requested.ref.lesson_id
            or lesson.version != requested.ref.content_version
            or lesson.track_id != track
        ):
            raise HTTPException(
                422,
                {
                    "code": "review_exam_unestablished",
                    "message": "This exact saved content version has no established native exam association for a new import.",
                },
            )
        exams = [exam.id for exam in EXAMS if track in exam.track_ids]
        if exams != [requested.exam]:
            raise HTTPException(
                422,
                {
                    "code": "review_exam_mismatch",
                    "message": "The selected personal exam does not match this exact native review content.",
                },
            )
        snapshots.append(
            ValidatedOwnedReviewV1(ref=requested.ref, exam=requested.exam, available=True)
        )
    return snapshots


@dataclass(frozen=True)
class _PreviewBundle:
    preview: SharedRoutePreviewOutV1
    source_references: list[PerGoalDigest]
    catalogue: FrozenExactCatalogue
    own_reviews: list[ValidatedOwnedReviewV1]


def _build_preview(
    session: Session,
    profile_id: str,
    principal: Principal,
    payload: SharedRoutePreviewRequestV1,
    now: datetime,
) -> _PreviewBundle:
    _require_preparation(session, principal, now)
    current = _current_row(session, profile_id)
    revision = _current_receipt(session, current).revision if current else 0
    if revision != payload.expected_revision:
        raise HTTPException(409, _REVISION_CONFLICT)
    legacy = _legacy_anchor(session, profile_id)
    graph = _strict_graph(
        session, profile_id, principal, payload.applicant_input.selected_result_ids
    )
    references = _source_references(graph)
    catalogue = _freeze_catalogue()
    reviews = _owned_review_snapshot(session, profile_id, principal, payload.applicant_input)
    today = now.astimezone(ZoneInfo(payload.applicant_input.timezone)).date()
    allocation = allocate_shared_v1(
        payload.applicant_input, catalogue=catalogue, own_reviews=reviews, planned_on=today
    )
    reasons = []
    for programme, reference in zip(graph.programmes, references, strict=True):
        if not programme.research_access:
            reasons.append(
                ReviewReasonV1(code="goal_research_locked", result_id=programme.result_id)
            )
        elif reference.reference_digest is None or programme.evidence_state != "current":
            reasons.append(
                ReviewReasonV1(code="goal_evidence_unknown", result_id=programme.result_id)
            )
    unavailable_refs = {item.ref.id for item in catalogue.lessons if not item.available}
    reasons.extend(
        ReviewReasonV1(code="content_version_unavailable", action_id=item.action_id)
        for item in [*allocation.slots, *allocation.unallocated]
        if item.ref.id in unavailable_refs
    )
    fingerprint = shared_preview_fingerprint(
        profile_id,
        payload.applicant_input,
        revision,
        legacy,
        today,
        graph.source_fingerprint,
        references,
        allocation,
    )
    preview = SharedRoutePreviewOutV1(
        profile_id=profile_id,
        expected_shared_revision=revision,
        legacy_anchor=legacy,
        planned_on=today,
        expires_on_local_date=today,
        requested_result_ids=graph.requested_result_ids,
        selected_result_ids=graph.selected_result_ids,
        source_fingerprint=graph.source_fingerprint,
        allocation=allocation,
        preview_fingerprint=fingerprint,
        review_reasons=reasons,
    )
    return _PreviewBundle(preview, references, catalogue, reviews)


def _make_receipt(
    profile_id: str, payload: SharedRouteWriteV1, bundle: _PreviewBundle, now: datetime
) -> SharedRouteWriteReceiptV1:
    value = {
        "schema_version": "shared-route-v1",
        "profile_id": profile_id,
        "revision": payload.expected_revision + 1,
        "expected_revision": payload.expected_revision,
        "client_write_uuid": str(payload.client_write_uuid),
        "canonical_request_digest": shared_request_digest(profile_id, payload),
        "accepted_at": now.isoformat().replace("+00:00", "Z"),
        "selected_result_ids": list(payload.applicant_input.selected_result_ids),
        "applicant_input": shared_input_wire(payload.applicant_input),
        "accepted_planned_on": bundle.preview.planned_on.isoformat(),
        "catalogue_version": CATALOGUE_VERSION,
        "planner_version": PLANNER_VERSION,
        "catalogue_snapshot": bundle.catalogue.model_dump(mode="json"),
        "owned_review_snapshot": [item.model_dump(mode="json") for item in bundle.own_reviews],
        "allocation": bundle.preview.allocation.model_dump(mode="json"),
        "allocation_digest": bundle.preview.allocation.digest,
        "source_fingerprint": bundle.preview.source_fingerprint,
        "source_reference_digests": [
            item.model_dump(mode="json") for item in bundle.source_references
        ],
        "preview_fingerprint": bundle.preview.preview_fingerprint,
        "legacy_anchor": bundle.preview.legacy_anchor.model_dump(mode="json"),
    }
    return SharedRouteWriteReceiptV1.model_validate({**value, "snapshot_digest": _digest(value)})


def _metadata(session: Session, profile_id: str, ids: list[str]) -> dict[str, str]:
    # Only safe owned metadata precedes any evidence entitlement/load.
    rows = (
        session.query(ProgramResultRow.id, ProgramResultRow.run_id, ProgramResultRow.user_decision)
        .join(ResearchRun)
        .filter(ResearchRun.profile_id == profile_id, ProgramResultRow.id.in_(ids))
        .all()
    )
    if len({row[0] for row in rows}) != len(rows):
        raise HTTPException(503, "Current programme metadata cannot be read safely.")
    return {row[0]: row[2] for row in rows}


def _status(result_id: str, state: GoalState) -> GoalStatusV1:
    return GoalStatusV1(
        result_id=result_id, state=state, safe_reason_code=None if state == "eligible" else state
    )


def _goal_statuses(
    session: Session, profile_id: str, principal: Principal, receipt: SharedRouteWriteReceiptV1
) -> tuple[list[GoalStatusV1], list[PreparationGraph]]:
    metadata = _metadata(session, profile_id, receipt.selected_result_ids)
    baselines = {item.result_id: item.reference_digest for item in receipt.source_reference_digests}
    statuses: list[GoalStatusV1] = []
    visible: list[PreparationGraph] = []
    locked = not has_full_access(session, principal.organization_id, profile_id)
    for result_id in receipt.selected_result_ids:
        decision = metadata.get(result_id)
        if result_id not in metadata:
            statuses.append(_status(result_id, "result_unavailable"))
            continue
        if decision not in {"approved", "maybe"}:
            statuses.append(_status(result_id, "decision_changed"))
            continue
        if locked or not has_full_access(session, principal.organization_id, profile_id):
            locked = True
            statuses.append(_status(result_id, "research_locked"))
            continue
        try:
            graph = _checked_graph(
                preparation_graph(
                    profile_id=profile_id,
                    result_id=[result_id],
                    principal=principal,
                    session=session,
                ),
                profile_id,
                [result_id],
            )
        except HTTPException as exc:
            if exc.status_code not in {404, 422} or exc.detail == "Applicant case not found":
                raise
            # At most one safe metadata recheck after a selection race.
            owned_profile(session, profile_id, principal)
            current_metadata = _metadata(session, profile_id, [result_id])
            current = current_metadata.get(result_id)
            state: GoalState = (
                "result_unavailable"
                if result_id not in current_metadata
                else "decision_changed"
                if current not in {"approved", "maybe"}
                else "evidence_unknown"
            )
            statuses.append(_status(result_id, state))
            continue
        except _PARSE_FAILURES:
            statuses.append(_status(result_id, "evidence_unknown"))
            continue
        programme = graph.programmes[0]
        if not programme.research_access:
            locked = True
            statuses.append(_status(result_id, "research_locked"))
            continue
        observed = _source_references(graph)[0].reference_digest
        baseline = baselines[result_id]
        state = (
            "evidence_unknown"
            if observed is None or baseline is None
            else "source_changed"
            if observed != baseline
            else "eligible"
            if programme.evidence_state == "current"
            and programme.projection_state in {"projected", "partial"}
            else "evidence_unknown"
        )
        statuses.append(_status(result_id, state))
        visible.append(graph)
    # Observed revocation clears earlier premium material, never cached receipt data.
    owned_profile(session, profile_id, principal)
    if locked or not has_full_access(session, principal.organization_id, profile_id):
        visible = []
        statuses = [
            item
            if item.state in {"result_unavailable", "decision_changed"}
            else _status(item.result_id, "research_locked")
            for item in statuses
        ]
    return statuses, visible


def _content_statuses(
    session: Session, profile_id: str, principal: Principal, receipt: SharedRouteWriteReceiptV1
) -> list[ContentStatusV1]:
    statuses = []
    for action in [*receipt.allocation.slots, *receipt.allocation.unallocated]:
        state: ContentState = "available"
        if isinstance(action.ref, LessonRef):
            try:
                lesson = lesson_dispatch(action.ref.lesson_id, action.ref.content_version)
                if (
                    lesson.id != action.ref.lesson_id
                    or lesson.version != action.ref.content_version
                ):
                    state = "version_unavailable"
            except ValueError:
                state = "version_unavailable"
        else:
            try:
                # Old own receipts need no new-command historical exam association.
                _checked_review(session, profile_id, principal, action.ref)
            except HTTPException as exc:
                if exc.status_code != 404 or exc.detail == "Applicant case not found":
                    raise
                state = "review_unavailable"
            except _PARSE_FAILURES:
                state = "unknown"
        statuses.append(ContentStatusV1(action_id=action.action_id, state=state))
    return statuses


def _view(
    session: Session, profile_id: str, principal: Principal, receipt: SharedRouteWriteReceiptV1
) -> SharedRouteViewV1:
    with session.no_autoflush:
        goals, visible = _goal_statuses(session, profile_id, principal, receipt)
        try:
            anchor = _legacy_anchor(session, profile_id)
            legacy: Literal["unchanged", "changed", "unknown"] = (
                "unchanged"
                if anchor.structural_fingerprint == receipt.legacy_anchor.structural_fingerprint
                else "changed"
            )
        except HTTPException as exc:
            if exc.status_code != 503:
                raise
            legacy = "unknown"
        content = _content_statuses(session, profile_id, principal, receipt)
        reasons = [
            ReviewReasonV1(code=_GOAL_CODES[item.safe_reason_code], result_id=item.result_id)
            for item in goals
            if item.safe_reason_code is not None
        ]
        if legacy != "unchanged":
            reasons.append(ReviewReasonV1(code=_LEGACY_CODES[legacy]))
        reasons.extend(
            ReviewReasonV1(code=_CONTENT_CODES[item.state], action_id=item.action_id)
            for item in content
            if item.state != "available"
        )
        current = CurrentRouteStatusV1(
            as_of=utcnow(),
            goal_statuses=goals,
            legacy_structure=legacy,
            imported_refs="not_used",
            content_statuses=content,
            preparation_access="active"
            if preparation_access(session, principal.organization_id).allowed
            else "expired",
            needs_review=bool(reasons),
            review_reasons=reasons,
        )
        # Final read after all content/term probes: no premium body on known lock.
        owned_profile(session, profile_id, principal)
        if not has_full_access(session, principal.organization_id, profile_id):
            goals = [
                item
                if item.state in {"result_unavailable", "decision_changed"}
                else _status(item.result_id, "research_locked")
                for item in goals
            ]
            reasons = [
                ReviewReasonV1(code=_GOAL_CODES[item.safe_reason_code], result_id=item.result_id)
                for item in goals
                if item.safe_reason_code is not None
            ] + [item for item in reasons if item.result_id is None]
            current = CurrentRouteStatusV1(
                **{
                    **current.model_dump(mode="python"),
                    "goal_statuses": goals,
                    "needs_review": bool(reasons),
                    "review_reasons": reasons,
                }
            )
            visible = []
        return SharedRouteViewV1(receipt=receipt, current_status=current, visible_evidence=visible)


@router.get(
    "/api/profiles/{profile_id}/preparation/shared-route", response_model=SharedRouteCurrentOutV1
)
def read_shared_route(
    profile_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> SharedRouteCurrentOutV1:
    with session.no_autoflush:
        owned_profile(session, profile_id, principal)
        row = _current_row(session, profile_id)
        if row is None:
            return SharedRouteCurrentOutV1(profile_id=profile_id, revision=0, view=None)
        receipt = _current_receipt(session, row)
        return SharedRouteCurrentOutV1(
            profile_id=profile_id,
            revision=receipt.revision,
            view=_view(session, profile_id, principal, receipt),
        )


@router.get(
    "/api/profiles/{profile_id}/preparation/shared-route/revisions/{revision}",
    response_model=SharedRouteViewV1,
)
def read_shared_route_revision(
    profile_id: str,
    revision: int,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> SharedRouteViewV1:
    with session.no_autoflush:
        owned_profile(session, profile_id, principal)
        row = (
            session.query(SharedRouteHistoryRow)
            .filter(
                SharedRouteHistoryRow.profile_id == profile_id,
                SharedRouteHistoryRow.revision == revision,
            )
            .first()
        )
        if row is None:
            raise HTTPException(404, "Shared route revision not found")
        return _view(session, profile_id, principal, _history_receipt(row))


@router.post(
    "/api/profiles/{profile_id}/preparation/shared-route/preview",
    response_model=SharedRoutePreviewOutV1,
)
def preview_shared_route(
    profile_id: str,
    payload: SharedRoutePreviewRequestV1,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> SharedRoutePreviewOutV1:
    with session.no_autoflush:
        owned_profile(session, profile_id, principal)
        _assert_actor(session, principal)
        return _build_preview(session, profile_id, principal, payload, utcnow()).preview


@router.put(
    "/api/profiles/{profile_id}/preparation/shared-route", response_model=SharedRouteWriteReceiptV1
)
def save_shared_route(
    profile_id: str,
    payload: SharedRouteWriteV1,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> SharedRouteWriteReceiptV1:
    if session.new or session.dirty or session.deleted or session.in_nested_transaction():
        raise HTTPException(503, "Preparation write requires a clean request session.")
    request_digest = shared_request_digest(profile_id, payload)
    try:
        with session.no_autoflush:
            owned_profile(session, profile_id, principal)
            _assert_actor(session, principal)
            accepted = _accepted_uuid(session, profile_id, payload, request_digest)
            if accepted is not None:
                return accepted
        begin_owned_preparation_write(session, profile_id, principal)
        with session.no_autoflush:
            # Recheck after parent/legacy wait, before any JSON/source/term gate.
            accepted = _accepted_uuid(session, profile_id, payload, request_digest)
            if accepted is not None:
                session.rollback()
                return accepted
            now = utcnow()
            bundle = _build_preview(
                session,
                profile_id,
                principal,
                SharedRoutePreviewRequestV1(
                    applicant_input=payload.applicant_input,
                    expected_revision=payload.expected_revision,
                ),
                now,
            )
            preview = bundle.preview
            if (
                payload.planned_on != preview.planned_on
                or payload.legacy_anchor != preview.legacy_anchor
                or payload.source_fingerprint != preview.source_fingerprint
                or payload.preview_fingerprint != preview.preview_fingerprint
            ):
                raise HTTPException(409, _PREVIEW_STALE)
            # Independent research writers do not take the profile fence. Re-read
            # near acceptance, with fresh ORM state, without claiming serializability.
            session.expire_all()
            fresh_graph = _strict_graph(
                session, profile_id, principal, payload.applicant_input.selected_result_ids
            )
            if (
                fresh_graph.source_fingerprint != preview.source_fingerprint
                or _source_references(fresh_graph) != bundle.source_references
                or _freeze_catalogue() != bundle.catalogue
            ):
                raise HTTPException(409, _PREVIEW_STALE)
            _assert_actor(session, principal)
            accepted_at = utcnow()
            _require_preparation(session, principal, accepted_at)
            if (
                accepted_at.astimezone(ZoneInfo(payload.applicant_input.timezone)).date()
                != preview.planned_on
            ):
                raise HTTPException(409, _PREVIEW_STALE)
            receipt = _make_receipt(profile_id, payload, bundle, accepted_at)
            snapshot = receipt.model_dump(mode="json")
            current = session.query(SharedRouteCurrentRow).filter(
                SharedRouteCurrentRow.profile_id == profile_id
            )
            if payload.expected_revision == 0:
                session.add(
                    SharedRouteCurrentRow(
                        profile_id=profile_id,
                        revision=receipt.revision,
                        schema_version=receipt.schema_version,
                        snapshot=snapshot,
                        digest=receipt.snapshot_digest,
                        updated_at=receipt.accepted_at,
                    )
                )
            else:
                changed = current.filter(
                    SharedRouteCurrentRow.revision == payload.expected_revision
                ).update(
                    {
                        SharedRouteCurrentRow.revision: receipt.revision,
                        SharedRouteCurrentRow.schema_version: receipt.schema_version,
                        SharedRouteCurrentRow.snapshot: snapshot,
                        SharedRouteCurrentRow.digest: receipt.snapshot_digest,
                        SharedRouteCurrentRow.updated_at: receipt.accepted_at,
                    },
                    synchronize_session=False,
                )
                if changed != 1:
                    raise HTTPException(409, _REVISION_CONFLICT)
            session.add(
                SharedRouteHistoryRow(
                    profile_id=profile_id,
                    revision=receipt.revision,
                    client_write_uuid=str(receipt.client_write_uuid),
                    request_digest=request_digest,
                    receipt=snapshot,
                    accepted_at=receipt.accepted_at,
                    origin="applicant_confirmed",
                    created_at=receipt.accepted_at,
                    updated_at=receipt.accepted_at,
                )
            )
            session.flush()
            session.commit()
            return receipt
    except HTTPException as exc:
        session.rollback()
        if exc.status_code in {409, 503}:
            accepted = _fresh_uuid_reconcile(
                session, profile_id, principal, payload, request_digest
            )
            if accepted is not None:
                return accepted
        raise
    except IntegrityError as exc:
        session.rollback()
        accepted = _fresh_uuid_reconcile(session, profile_id, principal, payload, request_digest)
        if accepted is not None:
            return accepted
        raise HTTPException(409, _REVISION_CONFLICT) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        accepted = _fresh_uuid_reconcile(session, profile_id, principal, payload, request_digest)
        if accepted is not None:
            return accepted
        raise HTTPException(503, _UNCONFIRMED) from exc
    except _PARSE_FAILURES as exc:
        session.rollback()
        raise HTTPException(
            503,
            {
                "code": "shared_route_binding_unreadable",
                "message": "The new plan could not be bound safely. No plan was saved.",
            },
        ) from exc


def export_shared_route_records(session: Session, profile_id: str) -> dict:
    """Caller has validated ownership; all immutable history, no status/reallocation."""
    with session.no_autoflush:
        current = _current_row(session, profile_id)
        current_receipt = _current_receipt(session, current) if current else None
        history = (
            session.query(SharedRouteHistoryRow)
            .filter(SharedRouteHistoryRow.profile_id == profile_id)
            .order_by(SharedRouteHistoryRow.revision, SharedRouteHistoryRow.id)
            .all()
        )
        receipts = [_history_receipt(item) for item in history]
        if (current_receipt is None) != (not receipts) or (
            current_receipt is not None
            and receipts
            and current_receipt.revision != receipts[-1].revision
        ):
            # A concurrent commit may advance history between the two reads.
            # Export fails closed rather than combine different accepted heads.
            raise HTTPException(503, _UNREADABLE)
        return {
            "current": current_receipt.model_dump(mode="json") if current_receipt else None,
            "history": [item.model_dump(mode="json") for item in receipts],
        }
