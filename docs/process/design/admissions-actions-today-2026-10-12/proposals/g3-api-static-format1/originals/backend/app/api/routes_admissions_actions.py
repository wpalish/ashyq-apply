"""Owned personal admissions actions and supplied native Today projections.

This additive router performs no research, allocation, lesson submission or
source retrieval. Its immutable ACK is distinct from every mutable read view.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Annotated, Any, Literal, Self
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import Field, TypeAdapter, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.preparation_transactions import begin_owned_preparation_write
from app.api.routes_preparation import access, read_learning_path, read_schedule
from app.api.routes_preparation_graph import preparation_graph
from app.api.routes_shared_route import read_shared_route
from app.api.tenancy import owned_profile
from app.db import get_session
from app.domain import admissions_actions as d
from app.domain.learning_schedule import settings_fingerprint
from app.models import (
    AdmissionsActionsCurrentRow,
    AdmissionsActionsEventRow,
    ApplicantProfileRow,
    ClaimRow,
    ConflictRow,
    OrganizationMembership,
    ProgramResultRow,
    ResearchRun,
    SharedRouteCurrentRow,
    SharedRouteHistoryRow,
    StudyScheduleRow,
    User,
)
from app.models.base import ensure_utc, utcnow
from app.payments.entitlements import has_full_access
from app.schemas import admissions_actions as s
from app.schemas.learning_schedule import LearningPathOut, LearningPathSnapshot
from app.schemas.preparation_graph import PreparationGraph
from app.schemas.preparation import PreparationAccess
from app.schemas.preparation_graph_loader import StoredPreparationGraphFields
from app.schemas.shared_route import SharedRouteCurrentOutV1, SharedRouteWriteReceiptV1
from app.schemas.study_schedule import ScheduleSettings, StudyScheduleOut
from app.security import Principal, get_principal


def _http(code: str) -> HTTPException:
    error = d.ActionError(code)
    return HTTPException(error.status, error.detail)


class SafeActionRoute(APIRoute):
    """Only this router hides framework validation's input-bearing details."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def safe(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError:
                raise _http("input_invalid") from None
            except d.ActionError as exc:
                raise HTTPException(exc.status, exc.detail) from None

        return safe


router = APIRouter(tags=["admissions-actions"], route_class=SafeActionRoute)


class DocumentReportReviewV1(s.Base):
    task_id: s.ExactId
    reasons: list[
        Literal["report_refers_to_previous_binding", "not_needed_is_not_a_waiver"]
    ]


class ResultActionLinksV1(s.Base):
    result_id: s.ExactId
    programme_information: s.ActionLinkReadV1
    requirements_information: s.ActionLinkReadV1


class ActionsCurrentOutV1(s.Base):
    profile_id: s.ExactId
    revision: int = Field(strict=True, ge=0, le=2147483647)
    state: s.CaseActionsStateV1 | None
    head_receipt: s.ActionWriteReceiptV1 | None
    observed_at: s.UtcTimestamp
    current_source_statuses: list[s.SourceReadStatusV1] = Field(max_length=20)
    document_report_reviews: list[DocumentReportReviewV1] = Field(max_length=400)
    action_links: list[ResultActionLinksV1] = Field(max_length=20)

    @model_validator(mode="after")
    def current_pointer(self) -> Self:
        if self.state is None or self.head_receipt is None:
            if (
                self.state is not None
                or self.head_receipt is not None
                or self.revision != 0
                or self.current_source_statuses
                or self.document_report_reviews
                or self.action_links
            ):
                raise ValueError("Absent current has no fabricated personal or source state")
        elif (
            self.state.profile_id != self.profile_id
            or self.head_receipt.profile_id != self.profile_id
            or self.state.revision != self.revision
            or self.head_receipt.revision != self.revision
            or self.state.head_event_id != self.head_receipt.event_id
            or s.state_digest(self.state) != self.head_receipt.after_state_digest
        ):
            raise ValueError("Current state and own immutable head must agree")
        if len({item.result_id for item in self.current_source_statuses}) != len(
            self.current_source_statuses
        ) or len({item.result_id for item in self.action_links}) != len(self.action_links):
            raise ValueError("Current source roles are unique and bounded")
        return self


class ActionsHistoryOutV1(s.Base):
    profile_id: s.ExactId
    events: list[s.ActionWriteReceiptV1] = Field(max_length=100)
    next_after_revision: s.Revision | None
    source_evaluation: Literal["not_evaluated"] = "not_evaluated"

    @model_validator(mode="after")
    def ordered_own_page(self) -> Self:
        if any(item.profile_id != self.profile_id for item in self.events) or any(
            left.revision >= right.revision
            for left, right in pairwise(self.events)
        ):
            raise ValueError("A page contains only ascending own accepted events")
        if self.next_after_revision is not None and (
            not self.events or self.next_after_revision != self.events[-1].revision
        ):
            raise ValueError("Next cursor follows the last returned event")
        return self


class OccurrenceSelectionInV1(s.Base):
    location: s.ChecklistLocation
    index: int = Field(strict=True, ge=0)


class SourceBindingPreviewInV1(s.Base):
    result_id: s.ExactId
    purpose: Literal["admission", "scholarship", "both"]
    award_id: s.ReferenceId | None
    occurrences: list[OccurrenceSelectionInV1] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def exact_occurrences(self) -> Self:
        if len({item.location for item in self.occurrences}) != len(self.occurrences):
            raise ValueError("Select at most one exact occurrence in each original list")
        if self.purpose == "admission" and self.award_id is not None:
            raise ValueError("Admission does not invent a scholarship relation")
        return self


class SourceBindingPreviewOutV1(s.Base):
    profile_id: s.ExactId
    result_id: s.ExactId
    selection: s.BindingSelectionV1
    source_preview_digest: s.Digest
    source_status: s.SourceReadStatusV1
    observed_at: s.UtcTimestamp


class LegacyImportPreviewInV1(s.Base):
    expected_revision: s.ExpectedRevision
    legacy_snapshot_digest: s.Digest
    mappings: list[s.LegacyImportMappingV1] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def exact_mappings(self) -> Self:
        s.unique([item.task_id for item in self.mappings])
        s.unique([item.legacy_key_digest for item in self.mappings])
        return self


class LegacyImportPreviewOutV1(s.Base):
    profile_id: s.ExactId
    revision: int = Field(strict=True, ge=0, le=2147483647)
    legacy_snapshot_digest: s.Digest
    mappings: list[s.LegacyImportMappingV1] = Field(min_length=1, max_length=50)
    observed_at: s.UtcTimestamp


@dataclass(frozen=True, slots=True)
class _Current:
    state: s.CaseActionsStateV1 | None
    head: s.ActionWriteReceiptV1 | None
    token: str


def _db_utc(value: datetime | None) -> datetime:
    # Native ensure_utc leaves aware nonzero PG offsets intact. Normalize only
    # copied DB headers, never saved JSON, hashes or entered local dates.
    if type(value) is not datetime:
        raise d.ActionError("saved_unreadable")
    observed = ensure_utc(value)
    if observed is None:
        raise d.ActionError("saved_unreadable")
    return observed.astimezone(UTC)


def _assert_actor(session: Session, principal: Principal) -> None:
    actor = session.query(User.id).filter(
        User.id == principal.user_id, User.is_active.is_(True)
    ).first()
    membership = session.query(OrganizationMembership.user_id).filter(
        OrganizationMembership.user_id == principal.user_id,
        OrganizationMembership.organization_id == principal.organization_id,
    ).first()
    if actor is None or membership is None:
        raise HTTPException(401, "Authentication required.")


def _current_pair(
    session: Session, profile_id: str,
) -> tuple[AdmissionsActionsCurrentRow | None, int | None]:
    latest = session.query(
        AdmissionsActionsEventRow.profile_id,
        func.max(AdmissionsActionsEventRow.revision).label("accepted_revision"),
    ).filter(AdmissionsActionsEventRow.profile_id == profile_id).group_by(
        AdmissionsActionsEventRow.profile_id
    ).subquery()
    pair = session.query(AdmissionsActionsCurrentRow, latest.c.accepted_revision).select_from(
        ApplicantProfileRow
    ).outerjoin(
        AdmissionsActionsCurrentRow,
        AdmissionsActionsCurrentRow.profile_id == ApplicantProfileRow.id,
    ).outerjoin(latest, latest.c.profile_id == ApplicantProfileRow.id).filter(
        ApplicantProfileRow.id == profile_id
    ).populate_existing().first()
    if pair is None:
        raise HTTPException(404, "Applicant case not found")
    row, latest_revision = pair
    if (row is None and latest_revision is not None) or (
        row is not None and row.revision != latest_revision
    ):
        raise d.ActionError("saved_unreadable")
    return row, latest_revision


def _head_token(session: Session, profile_id: str) -> str:
    latest = session.query(func.max(AdmissionsActionsEventRow.revision)).filter(
        AdmissionsActionsEventRow.profile_id == profile_id
    ).scalar_subquery()
    observed = session.query(
        ApplicantProfileRow.id,
        AdmissionsActionsCurrentRow.revision,
        AdmissionsActionsCurrentRow.schema_version,
        AdmissionsActionsCurrentRow.state_digest,
        AdmissionsActionsCurrentRow.updated_at,
        latest,
    ).select_from(ApplicantProfileRow).outerjoin(
        AdmissionsActionsCurrentRow,
        AdmissionsActionsCurrentRow.profile_id == ApplicantProfileRow.id,
    ).filter(ApplicantProfileRow.id == profile_id).first()
    if observed is None:
        raise HTTPException(404, "Applicant case not found")
    return s.reference_digest("g3-observed-head-v1", {
        "profile_id": observed[0], "revision": observed[1], "schema": observed[2],
        "digest": observed[3],
        "updated_at": _db_utc(observed[4]) if observed[4] is not None else None,
        "latest_revision": observed[5],
    })


def _event_receipt(row: AdmissionsActionsEventRow) -> s.ActionWriteReceiptV1:
    # Revalidate the original finite JSON before any normalization can launder it.
    receipt = d.validate_model(s.ActionWriteReceiptV1, row.receipt, "saved_unreadable")
    affected = d.validate_model(s.EventAffectedRefsV1, row.affected_refs, "saved_unreadable")
    if (
        receipt.event_id != row.id or receipt.profile_id != row.profile_id
        or receipt.revision != row.revision or receipt.schema_version != row.schema_version
        or receipt.kind != row.kind or str(receipt.client_write_uuid) != row.client_write_uuid
        or receipt.canonical_request_digest != row.request_digest
        or receipt.receipt_digest != row.receipt_digest
        or receipt.accepted_at != _db_utc(row.accepted_at)
        or receipt.affected_refs != affected
    ):
        raise d.ActionError("saved_unreadable")
    return receipt


def _exact_event(session: Session, profile_id: str, event_id: str) -> s.ActionWriteReceiptV1:
    row = session.query(AdmissionsActionsEventRow).filter(
        AdmissionsActionsEventRow.profile_id == profile_id,
        AdmissionsActionsEventRow.id == event_id,
    ).populate_existing().first()
    if row is None:
        raise d.ActionError("record_not_found")
    return _event_receipt(row)


def _load_current(session: Session, profile_id: str) -> _Current:
    row, latest_revision = _current_pair(session, profile_id)
    if row is None:
        return _Current(None, None, s.reference_digest("g3-observed-head-v1", {
            "profile_id": profile_id, "revision": None, "schema": None,
            "digest": None, "updated_at": None, "latest_revision": None,
        }))
    state = d.validate_model(s.CaseActionsStateV1, row.state, "saved_unreadable")
    if (
        state.profile_id != profile_id or state.revision != row.revision
        or state.schema_version != row.schema_version
    ):
        raise d.ActionError("saved_unreadable")
    try:
        head = _exact_event(session, profile_id, state.head_event_id)
    except d.ActionError:
        raise d.ActionError("saved_unreadable") from None
    metadata: list[s.EventMetadataV1] = []
    for ids in d.metadata_batches(state):
        values = session.query(
            AdmissionsActionsEventRow.profile_id, AdmissionsActionsEventRow.id,
            AdmissionsActionsEventRow.revision, AdmissionsActionsEventRow.kind,
            AdmissionsActionsEventRow.accepted_at, AdmissionsActionsEventRow.affected_refs,
        ).filter(
            AdmissionsActionsEventRow.profile_id == profile_id,
            AdmissionsActionsEventRow.id.in_(ids),
        ).all()
        if len(values) != len(ids):
            raise d.ActionError("saved_unreadable")
        for value in values:
            metadata.append(d.validate_model(s.EventMetadataV1, {
                "profile_id": value[0], "event_id": value[1], "revision": value[2],
                "kind": value[3], "accepted_at": _db_utc(value[4]),
                "affected_refs": value[5],
            }, "saved_unreadable"))
    current = d.validate_current_snapshot(
        state, head, profile_id=profile_id, row_digest=row.state_digest,
        row_updated_at=_db_utc(row.updated_at), latest_revision=latest_revision,
        metadata=metadata,
    )
    token = s.reference_digest("g3-observed-head-v1", {
        "profile_id": profile_id, "revision": row.revision, "schema": row.schema_version,
        "digest": row.state_digest, "updated_at": _db_utc(row.updated_at),
        "latest_revision": latest_revision,
    })
    return _Current(current, head, token)


def _accepted_uuid(
    session: Session, profile_id: str, payload: s.ActionRequestV1,
) -> s.ActionWriteReceiptV1 | None:
    row = session.query(AdmissionsActionsEventRow).filter(
        AdmissionsActionsEventRow.profile_id == profile_id,
        AdmissionsActionsEventRow.client_write_uuid == str(payload.client_write_uuid),
    ).populate_existing().first()
    if row is None:
        return None
    return d.replay_receipt(profile_id, payload, _event_receipt(row))


def _fresh_uuid_reconcile(
    session: Session, profile_id: str, principal: Principal, payload: s.ActionRequestV1,
) -> s.ActionWriteReceiptV1 | None:
    try:
        with session.no_autoflush:
            owned_profile(session, profile_id, principal)
            _assert_actor(session, principal)
            return _accepted_uuid(session, profile_id, payload)
    except SQLAlchemyError:
        session.rollback()
        raise d.ActionError("write_unconfirmed") from None


@dataclass(frozen=True, slots=True)
class _Target:
    result_id: str
    run_id: str
    decision: str


@dataclass(frozen=True, slots=True)
class _Source:
    checklist: object
    graph: PreparationGraph
    digest: str
    award_ids: tuple[str, ...]
    programme_url: object
    requirements_url: object
    demo: bool


def _target_metadata(
    session: Session, profile_id: str, result_ids: list[str],
) -> dict[str, _Target]:
    if len(result_ids) > 40 or len(set(result_ids)) != len(result_ids):
        raise d.ActionError("saved_unreadable")
    if not result_ids:
        return {}
    rows = session.query(
        ProgramResultRow.id, ProgramResultRow.run_id, ProgramResultRow.user_decision,
    ).join(ResearchRun).filter(
        ResearchRun.profile_id == profile_id, ProgramResultRow.id.in_(result_ids),
    ).all()
    return {row[0]: _Target(row[0], row[1], row[2]) for row in rows}


def _target_observation(
    profile_id: str, result_id: str, metadata: dict[str, _Target], research: bool,
) -> d.TargetObservationV1:
    item = metadata.get(result_id)
    if item is None:
        return d.TargetObservationV1(
            profile_id=profile_id, result_id=result_id, state="unavailable",
            decision="unknown", research_access=research,
        )
    selected = item.decision in {"approved", "maybe"}
    decision: Literal["approved", "maybe", "other", "unknown"] = (
        "approved" if item.decision == "approved" else "maybe"
        if item.decision == "maybe" else "other"
    )
    return d.TargetObservationV1(
        profile_id=profile_id, result_id=result_id,
        state="selected" if selected else "decision_changed",
        decision=decision, research_access=research,
    )


def _selected_target(
    session: Session, profile_id: str, result_id: str, principal: Principal,
) -> d.TargetObservationV1:
    metadata = _target_metadata(session, profile_id, [result_id])
    target = _target_observation(profile_id, result_id, metadata, False)
    if target.state == "unavailable":
        raise d.ActionError("record_not_found")
    if target.state != "selected":
        raise d.ActionError("target_not_selected")
    research = has_full_access(session, principal.organization_id, profile_id)
    return d.validate_model(d.TargetObservationV1, {
        **target.model_dump(mode="python"), "research_access": research,
    })


def _award_ids(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        raise d.ActionError("source_unreadable")
    try:
        s.finite_wire(payload)
        fields = StoredPreparationGraphFields.model_validate({
            "scholarships": payload.get("scholarships", []),
        })
        s.finite_wire(fields)
        values = tuple(TypeAdapter(s.ReferenceId).validate_python(item.id) for item in fields.scholarships)
        if len(set(values)) != len(values):
            raise ValueError("Awards need exact unique stored identities")
        return values
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise d.ActionError("source_unreadable") from None


def _raw_checklist(
    payload: object, column: object, result_id: str, university: str, programme: str,
) -> dict:
    if not isinstance(payload, dict):
        raise d.ActionError("source_unreadable")
    s.finite_wire(payload)
    fallback = payload.get("checklist")
    # A non-null authoritative column is not replaced by a more convenient
    # payload. Compare typed raw identity without saving a normalized projection.
    if column is not None:
        column_identity = d.checklist_identity(column)
        if fallback is not None and column_identity != d.checklist_identity(fallback):
            raise d.ActionError("source_unreadable")
    chosen = column if column is not None else fallback
    if not isinstance(chosen, dict):
        raise d.ActionError("source_unreadable")
    d.checklist_identity(chosen)
    if (
        chosen.get("result_id") != result_id or chosen.get("university") != university
        or chosen.get("program") != programme
    ):
        raise d.ActionError("source_unreadable")
    return chosen


def _source_bundle(
    session: Session, profile_id: str, result_id: str, principal: Principal,
) -> _Source:
    # Public native singleton graph remains its own guarded source observation.
    # No private G1 loader, reconstructed claims or guessed document action ID.
    try:
        graph = preparation_graph(
            profile_id, result_id=[result_id], principal=principal, session=session,
        )
    except HTTPException as exc:
        if exc.status_code == 401 or (exc.status_code == 404 and exc.detail == "Applicant case not found"):
            raise
        raise d.ActionError("record_not_found" if exc.status_code == 404 else
                            "target_not_selected" if exc.status_code == 422 else
                            "source_unreadable") from None
    try:
        raw_graph = s.finite_wire(graph)
        checked = PreparationGraph.model_validate_json(s.canonical_bytes(raw_graph), strict=True)
        if (
            s.finite_wire(checked) != raw_graph or checked.profile_id != profile_id
            or checked.requested_result_ids != [result_id]
            or checked.selected_result_ids != [result_id]
            or checked.selection_source != "server_verified_owned_explicit"
        ):
            raise ValueError("Exact own public source observation required")
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise d.ActionError("source_unreadable") from None
    if not checked.programmes[0].research_access:
        raise d.ActionError("source_locked")
    if not has_full_access(session, principal.organization_id, profile_id):
        raise d.ActionError("source_locked")
    row = session.query(
        ProgramResultRow.payload, ProgramResultRow.checklist, ProgramResultRow.university,
        ProgramResultRow.program, ProgramResultRow.user_decision, ResearchRun.demo_mode,
    ).join(ResearchRun).filter(
        ResearchRun.profile_id == profile_id, ProgramResultRow.id == result_id,
    ).first()
    if row is None:
        raise d.ActionError("record_not_found")
    if row[4] not in {"approved", "maybe"}:
        raise d.ActionError("target_not_selected")
    try:
        checklist = _raw_checklist(row[0], row[1], result_id, row[2], row[3])
        awards = _award_ids(row[0])
        checklist_digest, _ = d.checklist_identity(checklist)
        digest = s.reference_digest("g3-current-source-reference-v1", {
            "profile_id": profile_id, "result_id": result_id,
            "checklist_digest": checklist_digest, "source_fingerprint": checked.source_fingerprint,
        })
        requirements_url: object = None
        for location in d.CHECKLIST_LOCATIONS:
            for item in checklist.get(location, []):
                if item.get("source_url") is not None:
                    requirements_url = item["source_url"]
                    break
            if requirements_url is not None:
                break
        return _Source(
            checklist, checked, digest, awards, row[0].get("program_url"), requirements_url,
            row[5] is True,
        )
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise d.ActionError("source_unreadable") from None


def _selection_for(
    bundle: _Source, profile_id: str, result_id: str,
    occurrences: list[tuple[s.ChecklistLocation, int]],
    purpose: Literal["admission", "scholarship", "both"], award_id: str | None,
) -> s.BindingSelectionV1:
    if award_id is not None and award_id not in bundle.award_ids:
        raise d.ActionError("record_not_found")
    return d.build_binding_selection(
        bundle.checklist, profile_id=profile_id, result_id=result_id,
        selected_occurrences=occurrences, purpose=purpose, award_id=award_id, graph=bundle.graph,
    )


def _preview_digest(profile_id: str, selection: s.BindingSelectionV1) -> str:
    return s.reference_digest("g3-source-preview-v1", {
        "profile_id": profile_id, "selection": selection,
    })


def _evidence_reasons(bundle: _Source, selection: s.BindingSelectionV1 | None) -> list[s.SourceReason]:
    reasons: list[s.SourceReason] = []
    programme = bundle.graph.programmes[0]
    if programme.evidence_state == "stale":
        reasons.append("stale")
    elif programme.evidence_state == "conflicted":
        reasons.append("conflict")
    elif programme.evidence_state != "current":
        reasons.append("proof_unresolved")
    actions = [
        item for item in bundle.graph.document_actions
        if selection is not None and selection.g1_document is not None
        and item.id == selection.g1_document.action_id
    ]
    if selection is not None and selection.g1_relation != "exact_projection":
        reasons.append("ambiguous_occurrence" if selection.g1_relation == "ambiguous_occurrence"
                       else "document_predicate_not_projected")
    mapping: dict[str, s.SourceReason] = {
        "document_scope_unknown": "scope_unknown", "scope_unknown": "scope_unknown",
        "scope_unrecorded": "scope_unknown", "document_scope_mismatch": "scope_mismatch",
        "scope_mismatch": "scope_mismatch", "evidence_stale": "stale",
        "evidence_conflicted": "conflict", "claim_reference_unresolved": "proof_unresolved",
        "document_exact_proof_required": "proof_unresolved", "evidence_unknown": "proof_unresolved",
    }
    for item in [programme, *actions]:
        reasons.extend(mapping[reason] for reason in item.unresolved_reasons if reason in mapping)
    if selection is not None and (selection.award_id is not None or selection.purpose != "admission"):
        reasons.append("award_relation_unknown")
    return list(dict.fromkeys(reasons))


def _status(
    target: d.TargetObservationV1, now: datetime, *, bundle: _Source | None = None,
    reasons: list[s.SourceReason] | None = None,
) -> s.SourceReadStatusV1:
    target_state: Literal["eligible", "decision_changed", "result_unavailable"] = (
        "eligible" if target.state == "selected" else "decision_changed"
        if target.state == "decision_changed" else "result_unavailable"
    )
    source_state: Literal[
        "not_evaluated", "research_locked", "current_reference", "source_changed", "evidence_unknown"
    ] = "not_evaluated"
    digest = None
    result_reasons: list[s.SourceReason] = []
    if target_state == "eligible":
        if not target.research_access:
            source_state = "research_locked"
        elif bundle is None:
            source_state = "evidence_unknown"
            result_reasons = ["proof_unresolved"]
        else:
            digest = bundle.digest
            result_reasons = list(dict.fromkeys(reasons or []))
            source_state = "source_changed" if any(reason in {
                "proof_changed_item_same", "item_changed", "procedure_order_changed",
            } for reason in result_reasons) else "evidence_unknown" if result_reasons else "current_reference"
    return s.SourceReadStatusV1(
        result_id=target.result_id, target_state=target_state, source_state=source_state,
        observed_at=now, current_digest=digest, reasons=result_reasons,
    )


def _unavailable_links(result_id: str) -> ResultActionLinksV1:
    return ResultActionLinksV1(
        result_id=result_id,
        programme_information=d.project_action_link(
            None, role="programme_information", provenance="unknown",
        ),
        requirements_information=d.project_action_link(
            None, role="requirements_information", provenance="unknown",
        ),
    )


def _current_sources(
    session: Session, profile_id: str, principal: Principal, state: s.CaseActionsStateV1 | None,
    now: datetime,
) -> tuple[list[s.SourceReadStatusV1], list[ResultActionLinksV1]]:
    ids = s.source_target_ids(state) if state is not None else []
    metadata = _target_metadata(session, profile_id, ids)
    research = has_full_access(session, principal.organization_id, profile_id)
    statuses: list[s.SourceReadStatusV1] = []
    links: list[ResultActionLinksV1] = []
    for result_id in ids:
        target = _target_observation(profile_id, result_id, metadata, research)
        bundle = None
        reasons: list[s.SourceReason] = []
        if target.state == "selected" and target.research_access:
            try:
                bundle = _source_bundle(session, profile_id, result_id, principal)
                reasons.extend(_evidence_reasons(bundle, None))
                for task in state.document_tasks if state is not None else []:
                    saved = task.binding
                    if saved is None or saved.result_id != result_id:
                        continue
                    try:
                        selection = _selection_for(
                            bundle, profile_id, result_id,
                            [(item.location, item.index) for item in saved.occurrences],
                            saved.purpose, saved.award_id,
                        )
                        reasons.extend(d.compare_binding(
                            saved, selection, evidence_reasons=_evidence_reasons(bundle, selection),
                        ))
                    except d.ActionError as exc:
                        if exc.detail["code"] in {
                            "admissions_actions_source_preview_stale", "admissions_actions_record_not_found",
                            "admissions_actions_input_invalid",
                        }:
                            reasons.append("item_changed")
                        else:
                            raise
            except d.ActionError as exc:
                if exc.detail["code"] == "admissions_actions_source_locked":
                    target = d.validate_model(d.TargetObservationV1, {
                        **target.model_dump(mode="python"), "research_access": False,
                    })
                bundle = None
            except HTTPException as exc:
                if exc.status_code == 401 or (exc.status_code == 404 and exc.detail == "Applicant case not found"):
                    raise
                bundle = None
        statuses.append(_status(target, now, bundle=bundle, reasons=reasons))
        if bundle is None:
            links.append(_unavailable_links(result_id))
        else:
            provenance: Literal["current_source", "demo"] = "demo" if bundle.demo else "current_source"
            links.append(ResultActionLinksV1(
                result_id=result_id,
                programme_information=d.project_action_link(
                    bundle.programme_url, role="programme_information", provenance=provenance,
                    authorized_current_source=True,
                ),
                requirements_information=d.project_action_link(
                    bundle.requirements_url, role="requirements_information", provenance=provenance,
                    authorized_current_source=True,
                ),
            ))
    return statuses, links


@dataclass(frozen=True, slots=True)
class _NativeMarkers:
    g2_current: bool
    g2_history: bool
    v2_marker: bool
    v1_row: bool
    token: str


def _native_markers(session: Session, profile_id: str) -> _NativeMarkers:
    latest = session.query(func.max(SharedRouteHistoryRow.revision)).filter(
        SharedRouteHistoryRow.profile_id == profile_id,
    ).scalar_subquery()
    value = session.query(
        ApplicantProfileRow.id, ApplicantProfileRow.updated_at,
        SharedRouteCurrentRow.profile_id, SharedRouteCurrentRow.revision,
        SharedRouteCurrentRow.schema_version, SharedRouteCurrentRow.digest,
        SharedRouteCurrentRow.updated_at, latest,
        StudyScheduleRow.id, StudyScheduleRow.revision, StudyScheduleRow.updated_at,
        StudyScheduleRow.learning_path.is_not(None),
    ).select_from(ApplicantProfileRow).outerjoin(
        SharedRouteCurrentRow, SharedRouteCurrentRow.profile_id == ApplicantProfileRow.id,
    ).outerjoin(StudyScheduleRow, StudyScheduleRow.profile_id == ApplicantProfileRow.id).filter(
        ApplicantProfileRow.id == profile_id,
    ).first()
    if value is None:
        raise HTTPException(404, "Applicant case not found")
    token = s.reference_digest("g3-native-presence-v1", {
        "profile_id": value[0], "profile_updated_at": _db_utc(value[1]),
        "g2_profile": value[2], "g2_revision": value[3], "g2_schema": value[4],
        "g2_digest": value[5], "g2_updated_at": _db_utc(value[6]) if value[6] is not None else None,
        "g2_history_revision": value[7], "legacy_id": value[8], "legacy_revision": value[9],
        "legacy_updated_at": _db_utc(value[10]) if value[10] is not None else None,
        "legacy_v2_marker": value[11] is True,
    })
    return _NativeMarkers(value[2] is not None, value[7] is not None,
                          value[8] is not None and value[11] is True, value[8] is not None, token)


def _preparation_permission(
    session: Session, profile_id: str, principal: Principal,
) -> s.PreparationAccessReadV1:
    native = access(profile_id, principal=principal, session=session)
    checked = d.validate_model(PreparationAccess, native, "plan_unreadable")
    observed = utcnow()  # After the actual native term SELECT, not its start.
    starts = _db_utc(checked.starts_at) if checked.starts_at is not None else None
    ends = _db_utc(checked.ends_at) if checked.ends_at is not None else None
    development = checked.development_only and checked.reason == "development_mode"
    allowed = checked.allowed and (development or (
        starts is not None and ends is not None and starts <= observed < ends
    ))
    reason: Literal["active", "expired", "not_started", "unavailable", "development"] = (
        "development" if development and allowed else "active" if allowed else "expired"
        if ends is not None and ends <= observed else "not_started"
        if starts is not None and starts > observed else "unavailable"
    )
    return s.PreparationAccessReadV1(
        allowed=allowed, reason=reason, starts_at=starts, ends_at=ends,
        development_only=development and allowed, observed_at=observed,
    )


def _source_token(
    session: Session, profile_id: str, result_ids: list[str], *, include_evidence: bool,
) -> tuple[str, dict[str, _Target]]:
    if len(set(result_ids)) != len(result_ids) or len(result_ids) > 40:
        raise d.ActionError("saved_unreadable")
    if not result_ids:
        return s.reference_digest("g3-owned-source-metadata-v1", []), {}
    metadata_rows = session.query(
        ProgramResultRow.id, ProgramResultRow.run_id, ProgramResultRow.user_decision,
        ProgramResultRow.updated_at, ProgramResultRow.decided_at,
        ResearchRun.stage, ResearchRun.cancelled, ResearchRun.updated_at,
        ResearchRun.recheck_generation,
    ).join(ResearchRun).filter(
        ResearchRun.profile_id == profile_id, ProgramResultRow.id.in_(result_ids),
    ).order_by(ProgramResultRow.id).all()
    metadata = {row[0]: _Target(row[0], row[1], row[2]) for row in metadata_rows}
    values = [{
        "id": row[0], "run_id": row[1], "decision": row[2],
        "result_updated_at": _db_utc(row[3]),
        "decided_at": _db_utc(row[4]) if row[4] is not None else None,
        "stage": row[5], "cancelled": row[6], "run_updated_at": _db_utc(row[7]),
        "recheck_generation": row[8],
    } for row in metadata_rows]
    # A locked recheck never queries source/claim/conflict metadata as a hidden
    # substitute for the refused premium slice.
    if not include_evidence:
        return s.reference_digest("g3-owned-source-metadata-v1", {
            "requested_ids": result_ids, "observed": values, "evidence": "not_read",
        }), metadata
    eligible = {key: item for key, item in metadata.items() if item.decision in {"approved", "maybe"}}
    if not eligible:
        return s.reference_digest("g3-owned-source-metadata-v1", {
            "requested_ids": result_ids, "observed": values, "evidence": [],
        }), metadata
    eligible_ids = list(eligible)
    owned_run_ids = [item.run_id for item in eligible.values()]
    claims = session.query(
        ClaimRow.run_id.label("run_id"), func.count(ClaimRow.id).label("count"),
        func.max(ClaimRow.updated_at).label("changed_at"),
    ).join(ResearchRun, ResearchRun.id == ClaimRow.run_id).filter(
        ResearchRun.profile_id == profile_id,
        ClaimRow.run_id.in_(owned_run_ids),
        ClaimRow.result_id.in_(eligible_ids) | ClaimRow.result_id.is_(None),
    ).group_by(
        ClaimRow.run_id,
    ).subquery()
    conflicts = session.query(
        ConflictRow.run_id.label("run_id"), func.count(ConflictRow.id).label("count"),
        func.max(ConflictRow.updated_at).label("changed_at"),
    ).join(ResearchRun, ResearchRun.id == ConflictRow.run_id).filter(
        ResearchRun.profile_id == profile_id,
        ConflictRow.run_id.in_(owned_run_ids),
        ConflictRow.result_id.in_(eligible_ids) | ConflictRow.result_id.is_(None),
    ).group_by(
        ConflictRow.run_id,
    ).subquery()
    rows = session.query(
        ProgramResultRow.id, ProgramResultRow.run_id, ProgramResultRow.user_decision,
        ProgramResultRow.updated_at, ProgramResultRow.decided_at,
        ResearchRun.stage, ResearchRun.cancelled, ResearchRun.updated_at,
        ResearchRun.recheck_generation, claims.c.count, claims.c.changed_at,
        conflicts.c.count, conflicts.c.changed_at,
    ).join(ResearchRun).outerjoin(claims, claims.c.run_id == ResearchRun.id).outerjoin(
        conflicts, conflicts.c.run_id == ResearchRun.id,
    ).filter(
        ResearchRun.profile_id == profile_id, ProgramResultRow.id.in_(eligible_ids),
        ProgramResultRow.user_decision.in_(["approved", "maybe"]),
    ).order_by(
        ProgramResultRow.id,
    ).all()
    evidence = []
    for row in rows:
        evidence.append({
            "id": row[0], "run_id": row[1], "decision": row[2],
            "result_updated_at": _db_utc(row[3]),
            "decided_at": _db_utc(row[4]) if row[4] is not None else None,
            "stage": row[5], "cancelled": row[6], "run_updated_at": _db_utc(row[7]),
            "recheck_generation": row[8], "claim_count": row[9],
            "claim_updated_at": _db_utc(row[10]) if row[10] is not None else None,
            "conflict_count": row[11],
            "conflict_updated_at": _db_utc(row[12]) if row[12] is not None else None,
        })
    return s.reference_digest("g3-owned-source-metadata-v1", {
        "requested_ids": result_ids, "observed": values, "evidence": evidence,
    }), metadata


@dataclass(frozen=True, slots=True)
class _Plan:
    read: s.ActivePreparationReadV1
    timezone: str | None
    source_statuses: tuple[s.SourceReadStatusV1, ...]


def _unavailable_plan(
    origin: Literal["g2", "legacy_v2", "legacy_v1", "unknown"],
    selection: s.ActivePreparationSelectionV1 | None, now: datetime,
) -> _Plan:
    selection_source: Literal["accepted_g3_event", "derived_backward_default", "unavailable"] = (
        "accepted_g3_event" if selection is not None else "unavailable"
        if origin == "unknown" else "derived_backward_default"
    )
    return _Plan(s.ActivePreparationReadV1(
        origin=origin, selection_source=selection_source, state="unavailable", selection=selection,
        current_observed_head=None, observed_at=now, goal_result_ids=[], study_actions=[],
        allocated_minutes=None, needs_review=True,
    ), None, ())


def _legacy_row(session: Session, profile_id: str) -> StudyScheduleRow | None:
    return session.query(StudyScheduleRow).filter(
        StudyScheduleRow.profile_id == profile_id,
    ).populate_existing().first()


def _g2_statuses(view: SharedRouteCurrentOutV1, now: datetime) -> tuple[s.SourceReadStatusV1, ...]:
    if view.view is None:
        return ()
    graphs = {item.selected_result_ids[0]: item for item in view.view.visible_evidence}
    statuses: list[s.SourceReadStatusV1] = []
    for goal in view.view.current_status.goal_statuses:
        target_state: Literal["eligible", "decision_changed", "result_unavailable"] = (
            "result_unavailable" if goal.state == "result_unavailable" else "decision_changed"
            if goal.state == "decision_changed" else "eligible"
        )
        graph = graphs.get(goal.result_id)
        digest = graph.source_fingerprint if graph is not None else None
        source_state: Literal[
            "not_evaluated", "research_locked", "current_reference", "source_changed", "evidence_unknown"
        ] = "not_evaluated"
        reasons: list[s.SourceReason] = []
        if target_state == "eligible":
            if goal.state == "research_locked":
                source_state = "research_locked"
                digest = None
            elif goal.state == "eligible" and graph is not None:
                source_state = "current_reference"
            elif goal.state == "source_changed" and graph is not None:
                source_state = "source_changed"
                reasons = ["proof_changed_item_same"]
            else:
                source_state = "evidence_unknown"
                reasons = ["proof_unresolved"]
        else:
            digest = None
        statuses.append(s.SourceReadStatusV1(
            result_id=goal.result_id, target_state=target_state, source_state=source_state,
            observed_at=now, current_digest=digest, reasons=reasons,
        ))
    return tuple(statuses)


def _read_plan(
    session: Session, profile_id: str, principal: Principal,
    origin: Literal["g2", "legacy_v2", "legacy_v1", "none", "unknown"],
    selection: s.ActivePreparationSelectionV1 | None, now: datetime,
) -> _Plan:
    source: Literal["accepted_g3_event", "derived_backward_default"] = (
        "accepted_g3_event" if selection is not None else "derived_backward_default"
    )
    if origin == "unknown":
        return _unavailable_plan("unknown", selection, now)
    if origin == "none":
        return _Plan(s.ActivePreparationReadV1(
            origin="none", selection_source=source, state="absent", selection=None,
            current_observed_head=None, observed_at=now, goal_result_ids=[], study_actions=[],
            allocated_minutes=None, needs_review=False,
        ), None, ())
    head: s.NativeHeadV1
    actions: list[s.StudyActionReadV1] = []
    goals: list[str] = []
    statuses: tuple[s.SourceReadStatusV1, ...] = ()
    if origin == "g2":
        native = read_shared_route(profile_id, principal=principal, session=session)
        checked = d.validate_model(SharedRouteCurrentOutV1, native, "plan_unreadable")
        if checked.profile_id != profile_id:
            raise d.ActionError("plan_unreadable")
        if checked.view is None:
            raise d.ActionError("plan_unavailable")
        receipt = checked.view.receipt
        head = s.G2HeadV1(
            profile_id=profile_id, revision=receipt.revision,
            client_write_uuid=receipt.client_write_uuid, snapshot_digest=receipt.snapshot_digest,
            allocation_digest=receipt.allocation_digest, accepted_at=_db_utc(receipt.accepted_at),
        )
        zone = receipt.applicant_input.timezone
        content = {item.action_id: item.state for item in checked.view.current_status.content_statuses}
        for slot in receipt.allocation.slots:
            actions.append(s.StudyActionReadV1(
                id=slot.occurrence_id, local_date=slot.local_date, timezone=zone, ref=slot.ref,
                planned_minutes=slot.planned_minutes,
                availability="available" if content.get(slot.action_id) == "available" else "unavailable",
                completion="not_projected",
            ))
        goals = list(receipt.selected_result_ids)
        statuses = _g2_statuses(checked, now)
        needs_review = checked.view.current_status.needs_review
    else:
        row = _legacy_row(session, profile_id)
        if row is None:
            raise d.ActionError("plan_unavailable")
        try:
            s.finite_wire(row.settings)
            settings = ScheduleSettings.model_validate(row.settings)
            s.finite_wire(settings)
            structural = settings_fingerprint(settings)
            if origin == "legacy_v2":
                # Test raw non-null presence first. Native read_learning_path
                # treats {} as false; G3 must not turn that marker into v1/none.
                if row.learning_path is None:
                    raise d.ActionError("plan_unavailable")
                s.finite_wire(row.learning_path)
                saved = LearningPathSnapshot.model_validate(row.learning_path)
                s.finite_wire(saved)
                head = s.LegacyV2HeadV1(
                    profile_id=profile_id, revision=row.revision,
                    persisted_sidecar_digest=s.reference_digest("g3-native-v2-sidecar-v1", saved),
                    draft_fingerprint=saved.draft.fingerprint,
                    legacy_fingerprint=saved.legacy_fingerprint,
                    observed_structural_fingerprint=structural,
                )
                projection = d.validate_model(LearningPathOut, read_learning_path(
                    profile_id, principal=principal, session=session,
                ), "plan_unreadable")
                if (
                    projection.profile_id != profile_id or projection.revision != row.revision
                    or projection.learning_path is None
                ):
                    raise d.ActionError("plan_unreadable")
                current = projection.learning_path
                # Fresh native availability/overdue status cannot replace any
                # saved date, identity, reference version, duration or ordering.
                saved_keys = [(item.id, item.due_on, item.learning_ref, item.minutes)
                              for item in saved.schedule.tasks]
                fresh_keys = [(item.id, item.due_on, item.learning_ref, item.minutes)
                              for item in current.schedule.tasks]
                if saved_keys != fresh_keys:
                    raise d.ActionError("plan_unreadable")
                zone = saved.legacy_settings.timezone
                for item in current.schedule.tasks:
                    supported = item.learning_ref is not None and item.learning_ref.kind in {
                        "lesson", "attempt_review",
                    }
                    actions.append(s.StudyActionReadV1(
                        id=item.id, local_date=item.due_on, timezone=zone, ref=item.learning_ref,
                        planned_minutes=item.minutes,
                        availability="unsupported" if not supported else "available"
                        if item.availability == "available" else "unavailable",
                        completion="self_reported_complete" if item.completed else "not_projected",
                    ))
                needs_review = projection.needs_review or current.schedule.diagnostic_required
            else:
                head = s.LegacyV1HeadV1(
                    profile_id=profile_id, revision=row.revision,
                    saved_settings_digest=s.reference_digest("g3-native-v1-settings-v1", settings),
                    settings_fingerprint=structural,
                )
                v1_projection = d.validate_model(StudyScheduleOut, read_schedule(
                    profile_id, principal=principal, session=session,
                ), "plan_unreadable")
                if (
                    v1_projection.profile_id != profile_id or v1_projection.revision != row.revision
                    or v1_projection.settings is None or v1_projection.schedule is None
                    or v1_projection.settings != settings
                ):
                    raise d.ActionError("plan_unreadable")
                zone = settings.timezone
                for v1_item in v1_projection.schedule.tasks:
                    actions.append(s.StudyActionReadV1(
                        id=v1_item.id, local_date=v1_item.due_on, timezone=zone, ref=None,
                        planned_minutes=v1_item.minutes, availability="unsupported",
                        completion="self_reported_complete" if v1_item.completed else "not_projected",
                    ))
                needs_review = v1_projection.schedule.diagnostic_required
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise d.ActionError("plan_unavailable") from None
    if selection is not None and head.revision < selection.observed_head.revision:
        raise d.ActionError("plan_unreadable")
    result = s.ActivePreparationReadV1(
        origin=origin, selection_source=source,
        state="needs_review" if needs_review else "available", selection=selection,
        current_observed_head=head, observed_at=now, goal_result_ids=goals, study_actions=actions,
        allocated_minutes=sum(item.planned_minutes for item in actions), needs_review=needs_review,
    )
    return _Plan(result, zone, statuses)


def _owned_read(session: Session, profile_id: str, principal: Principal) -> None:
    owned_profile(session, profile_id, principal)
    _assert_actor(session, principal)


def _safe_plan(
    session: Session, profile_id: str, principal: Principal,
    origin: Literal["g2", "legacy_v2", "legacy_v1", "none", "unknown"],
    selection: s.ActivePreparationSelectionV1 | None, now: datetime,
) -> _Plan:
    try:
        return _read_plan(session, profile_id, principal, origin, selection, now)
    except HTTPException as exc:
        if exc.status_code == 401 or (exc.status_code == 404 and exc.detail == "Applicant case not found"):
            raise
        raise d.ActionError("plan_unavailable" if exc.status_code in {404, 422} else
                            "plan_unreadable") from None


def _source_observation(
    session: Session, profile_id: str, principal: Principal,
    request: s.BindSourceTaskV1 | s.RebindSourceTaskV1,
) -> d.SourceObservationV1:
    target = _selected_target(session, profile_id, request.source.result_id, principal)
    if not target.research_access:
        raise d.ActionError("source_locked")
    bundle = _source_bundle(session, profile_id, request.source.result_id, principal)
    selection = _selection_for(
        bundle, profile_id, request.source.result_id,
        [(item.location, item.index) for item in request.source.occurrences],
        request.source.purpose, request.source.award_id,
    )
    target = d.validate_model(d.TargetObservationV1, {
        **target.model_dump(mode="python"), "award_ids": list(bundle.award_ids),
    }, "source_unreadable")
    return d.SourceObservationV1(
        target=target, state="readable", preview_digest=_preview_digest(profile_id, selection),
        selection=selection,
    )


def _application_target(
    session: Session, profile_id: str, principal: Principal, request: s.CreateApplicationV1,
) -> d.TargetObservationV1:
    target = _selected_target(session, profile_id, request.target.result_id, principal)
    if request.target.award_id is None:
        return target
    if not target.research_access:
        raise d.ActionError("source_locked")
    # An exact award target needs only authorized native award identities, not
    # a guessed relation, a checklist placeholder or copied scholarship content.
    row = session.query(ProgramResultRow.payload).join(ResearchRun).filter(
        ResearchRun.profile_id == profile_id,
        ProgramResultRow.id == request.target.result_id,
        ProgramResultRow.user_decision.in_(["approved", "maybe"]),
    ).first()
    if row is None:
        raise d.ActionError("record_not_found")
    return d.validate_model(d.TargetObservationV1, {
        **target.model_dump(mode="python"), "award_ids": list(_award_ids(row[0])),
    }, "source_unreadable")


def _legacy_observation(
    session: Session, profile_id: str, principal: Principal, state: s.CaseActionsStateV1 | None,
    snapshot_digest: str, mappings: list[s.LegacyImportMappingV1],
) -> d.LegacyMarkObservationV1:
    tasks = {item.id: item for item in state.document_tasks} if state is not None else {}
    bundles: dict[str, _Source] = {}
    for mapping in mappings:
        task = tasks.get(mapping.task_id)
        if task is None:
            raise d.ActionError("record_not_found")
        binding = task.binding
        expected = binding.binding_digest if binding is not None else None
        if mapping.expected_binding_digest != expected:
            raise d.ActionError("legacy_import_changed")
        if binding is None:
            if mapping.source_preview_digest is not None:
                raise d.ActionError("legacy_import_changed")
            continue
        if mapping.source_preview_digest is None:
            raise d.ActionError("legacy_import_changed")
        # Old binding hashes are retained personal references. A new source-bound
        # import additionally needs today's authorized exact-occurrence preview.
        if not has_full_access(session, principal.organization_id, profile_id):
            raise d.ActionError("source_locked")
        try:
            target = _selected_target(session, profile_id, binding.result_id, principal)
            if not target.research_access:
                raise d.ActionError("source_locked")
            bundle = bundles.get(binding.result_id)
            if bundle is None:
                bundle = _source_bundle(session, profile_id, binding.result_id, principal)
                bundles[binding.result_id] = bundle
            current = _selection_for(
                bundle, profile_id, binding.result_id,
                [(item.location, item.index) for item in binding.occurrences],
                binding.purpose, binding.award_id,
            )
        except d.ActionError as exc:
            if exc.detail["code"] == "admissions_actions_source_locked":
                raise
            raise d.ActionError("legacy_import_changed") from None
        if mapping.source_preview_digest != _preview_digest(profile_id, current):
            raise d.ActionError("legacy_import_changed")
    return d.LegacyMarkObservationV1(
        profile_id=profile_id, snapshot_digest=snapshot_digest, mappings=mappings,
    )


def _write_source_ids(
    request: s.ActionRequestV1, state: s.CaseActionsStateV1 | None,
) -> tuple[list[str], bool]:
    if isinstance(request, s.CreateApplicationV1):
        return [request.target.result_id], request.target.award_id is not None
    if isinstance(request, s.BindSourceTaskV1 | s.RebindSourceTaskV1):
        return [request.source.result_id], True
    if isinstance(request, s.ImportLegacyMarksV1):
        selected = {item.task_id for item in request.mappings}
        ids = [item.binding.result_id for item in state.document_tasks
               if item.id in selected and item.binding is not None] if state is not None else []
        unique = list(dict.fromkeys(ids))
        return unique, bool(unique)
    return [], False


def _write_context(
    session: Session, profile_id: str, principal: Principal,
    request: s.ActionRequestV1, current: _Current,
) -> d.ActionContextV1:
    target = None
    source = None
    legacy = None
    prior = None
    plan = None
    if isinstance(request, s.CreateApplicationV1):
        target = _application_target(session, profile_id, principal, request)
    elif isinstance(request, s.BindSourceTaskV1 | s.RebindSourceTaskV1):
        source = _source_observation(session, profile_id, principal, request)
    elif isinstance(request, s.CorrectDeclarationV1):
        prior = _exact_event(session, profile_id, request.prior_declaration.event_id)
    elif isinstance(request, s.ImportLegacyMarksV1):
        legacy = _legacy_observation(
            session, profile_id, principal, current.state,
            request.legacy_snapshot_digest, request.mappings,
        )
    elif isinstance(request, s.SelectActivePreparationV1):
        observed = _safe_plan(session, profile_id, principal, request.origin, None, utcnow())
        plan = d.PlanObservationV1(
            profile_id=profile_id,
            state="readable" if observed.read.current_observed_head is not None else "absent",
            head=observed.read.current_observed_head,
        )
    return d.ActionContextV1(
        profile_id=profile_id, event_id=uuid4().hex, accepted_at=utcnow(),
        actor=d.actor_reference(
            principal.user_id, principal.organization_id,
            local_development=principal.local_development,
        ),
        new_application_id=uuid4().hex if isinstance(request, s.CreateApplicationV1) else None,
        new_task_id=uuid4().hex if isinstance(request, s.CreatePersonalTaskV1 | s.BindSourceTaskV1)
        else None,
        target=target, source=source, plan=plan, prior_declaration_receipt=prior, legacy=legacy,
    )


def _persist_transition(
    session: Session, profile_id: str, request: s.ActionRequestV1, transition: d.ActionTransitionV1,
) -> None:
    state, receipt = transition.state, transition.receipt
    wire_state = state.model_dump(mode="json")
    wire_receipt = receipt.model_dump(mode="json")
    if request.expected_revision == 0:
        session.add(AdmissionsActionsCurrentRow(
            profile_id=profile_id, revision=state.revision, schema_version=state.schema_version,
            state=wire_state, state_digest=s.state_digest(state), updated_at=receipt.accepted_at,
        ))
    else:
        changed = session.query(AdmissionsActionsCurrentRow).filter(
            AdmissionsActionsCurrentRow.profile_id == profile_id,
            AdmissionsActionsCurrentRow.revision == request.expected_revision,
        ).update({
            AdmissionsActionsCurrentRow.revision: state.revision,
            AdmissionsActionsCurrentRow.schema_version: state.schema_version,
            AdmissionsActionsCurrentRow.state: wire_state,
            AdmissionsActionsCurrentRow.state_digest: s.state_digest(state),
            AdmissionsActionsCurrentRow.updated_at: receipt.accepted_at,
        }, synchronize_session=False)
        if changed != 1:
            raise d.ActionError("revision_conflict")
    session.add(AdmissionsActionsEventRow(
        id=receipt.event_id, profile_id=profile_id, revision=receipt.revision,
        schema_version=receipt.schema_version, kind=receipt.kind,
        client_write_uuid=str(receipt.client_write_uuid),
        request_digest=receipt.canonical_request_digest, receipt_digest=receipt.receipt_digest,
        accepted_at=receipt.accepted_at, affected_refs=receipt.affected_refs.model_dump(mode="json"),
        receipt=wire_receipt,
    ))
    session.flush()
    session.commit()


@router.post(
    "/api/profiles/{profile_id}/admissions-actions/commands",
    response_model=s.ActionWriteReceiptV1,
)
def write_admissions_action(
    profile_id: str, payload: s.ActionRequestV1,
    principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
) -> s.ActionWriteReceiptV1:
    # Outside every rollback-catching block: never discard unrelated pending
    # writes, including an auth mutation, just to make a new command fit.
    if session.new or session.dirty or session.deleted or session.in_nested_transaction():
        raise _http("write_session_unavailable")
    try:
        request = d.validate_request(payload)
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    try:
        begin_owned_preparation_write(session, profile_id, principal)
        with session.no_autoflush:
            # Plain owner/actor authority was checked under the strong parent.
            # Existing UUID replay precedes every current, source and plan read.
            accepted = _accepted_uuid(session, profile_id, request)
            if accepted is not None:
                session.rollback()
                return accepted
            current = _load_current(session, profile_id)
            revision = current.state.revision if current.state is not None else 0
            if request.expected_revision != revision:
                raise d.ActionError("revision_conflict")
            ids, needs_source = _write_source_ids(request, current.state)
            research = has_full_access(session, principal.organization_id, profile_id) if needs_source else False
            source_token, _ = _source_token(
                session, profile_id, ids, include_evidence=needs_source and research,
            )
            native_before = _native_markers(session, profile_id).token if isinstance(
                request, s.SelectActivePreparationV1,
            ) else None
            context = _write_context(session, profile_id, principal, request, current)
            # Independent research writers use different locks. One bounded
            # scalar recheck near acceptance refuses a stale authorized preview.
            if needs_source and not has_full_access(session, principal.organization_id, profile_id):
                raise d.ActionError("source_locked")
            rechecked, metadata = _source_token(
                session, profile_id, ids, include_evidence=needs_source,
            )
            for result_id in ids:
                observed = _target_observation(profile_id, result_id, metadata, needs_source)
                if observed.state != "selected":
                    if isinstance(request, s.ImportLegacyMarksV1):
                        raise d.ActionError("legacy_import_changed")
                    raise d.ActionError("record_not_found" if observed.state == "unavailable" else
                                        "target_not_selected")
            if needs_source and rechecked != source_token:
                raise d.ActionError("legacy_import_changed" if isinstance(request, s.ImportLegacyMarksV1)
                                    else "source_preview_stale")
            if native_before is not None and _native_markers(session, profile_id).token != native_before:
                raise d.ActionError("plan_head_changed")
            _assert_actor(session, principal)
            # The terminal observation follows actual bounded reads. No database
            # default, client clock, entitlement grant or silent allocation.
            context = d.validate_model(d.ActionContextV1, {
                **context.model_dump(mode="python"), "accepted_at": utcnow(),
            })
            transition = d.apply_action(current.state, request, context)
            _persist_transition(session, profile_id, request, transition)
            return transition.receipt
    except d.ActionError as exc:
        session.rollback()
        if exc.status in {409, 503}:
            try:
                accepted = _fresh_uuid_reconcile(session, profile_id, principal, request)
            except d.ActionError as reconcile:
                raise HTTPException(reconcile.status, reconcile.detail) from None
            if accepted is not None:
                return accepted
        raise HTTPException(exc.status, exc.detail) from None
    except HTTPException as exc:
        session.rollback()
        if exc.status_code == 503:
            try:
                accepted = _fresh_uuid_reconcile(session, profile_id, principal, request)
            except d.ActionError as reconcile:
                raise HTTPException(reconcile.status, reconcile.detail) from None
            if accepted is not None:
                return accepted
            raise _http("write_unconfirmed") from None
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        try:
            accepted = _fresh_uuid_reconcile(session, profile_id, principal, request)
        except d.ActionError as reconcile:
            raise HTTPException(reconcile.status, reconcile.detail) from None
        if accepted is not None:
            return accepted
        raise _http("revision_conflict" if isinstance(exc, IntegrityError) else "write_unconfirmed") from None
    except (ValueError, TypeError, OverflowError, RecursionError):
        session.rollback()
        raise _http("saved_unreadable") from None


@router.post(
    "/api/profiles/{profile_id}/admissions-actions/preview",
    response_model=SourceBindingPreviewOutV1,
)
def preview_source_binding(
    profile_id: str, payload: SourceBindingPreviewInV1,
    principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
) -> SourceBindingPreviewOutV1:
    try:
        with session.no_autoflush:
            _owned_read(session, profile_id, principal)
            request = d.validate_model(SourceBindingPreviewInV1, payload)
            target = _selected_target(session, profile_id, request.result_id, principal)
            if not target.research_access:
                raise d.ActionError("source_locked")
            before, _ = _source_token(session, profile_id, [request.result_id], include_evidence=True)
            bundle = _source_bundle(session, profile_id, request.result_id, principal)
            selected = _selection_for(
                bundle, profile_id, request.result_id,
                [(item.location, item.index) for item in request.occurrences],
                request.purpose, request.award_id,
            )
            if not has_full_access(session, principal.organization_id, profile_id):
                raise d.ActionError("source_locked")
            after, metadata = _source_token(session, profile_id, [request.result_id], include_evidence=True)
            if before != after:
                raise d.ActionError("source_preview_stale")
            target = _target_observation(profile_id, request.result_id, metadata, True)
            _assert_actor(session, principal)
            now = utcnow()
            return SourceBindingPreviewOutV1(
                profile_id=profile_id, result_id=request.result_id, selection=selected,
                source_preview_digest=_preview_digest(profile_id, selected),
                source_status=_status(target, now, bundle=bundle, reasons=_evidence_reasons(bundle, selected)),
                observed_at=now,
            )
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("source_unreadable") from None


@router.post(
    "/api/profiles/{profile_id}/admissions-actions/import-preview",
    response_model=LegacyImportPreviewOutV1,
)
def preview_legacy_import(
    profile_id: str, payload: LegacyImportPreviewInV1,
    principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
) -> LegacyImportPreviewOutV1:
    try:
        with session.no_autoflush:
            _owned_read(session, profile_id, principal)
            request = d.validate_model(LegacyImportPreviewInV1, payload)
            current = _load_current(session, profile_id)
            revision = current.state.revision if current.state is not None else 0
            if revision != request.expected_revision:
                raise d.ActionError("revision_conflict")
            task_ids = {item.task_id for item in request.mappings}
            ids = list(dict.fromkeys(item.binding.result_id for item in current.state.document_tasks
                                    if item.id in task_ids and item.binding is not None)) if current.state else []
            research = has_full_access(session, principal.organization_id, profile_id) if ids else False
            before, _ = _source_token(session, profile_id, ids, include_evidence=research)
            observed = _legacy_observation(
                session, profile_id, principal, current.state,
                request.legacy_snapshot_digest, request.mappings,
            )
            if ids and not has_full_access(session, principal.organization_id, profile_id):
                raise d.ActionError("source_locked")
            after, _ = _source_token(session, profile_id, ids, include_evidence=bool(ids))
            if before != after or _head_token(session, profile_id) != current.token:
                raise d.ActionError("legacy_import_changed")
            _assert_actor(session, principal)
            return LegacyImportPreviewOutV1(
                profile_id=profile_id, revision=revision,
                legacy_snapshot_digest=observed.snapshot_digest,
                mappings=observed.mappings, observed_at=utcnow(),
            )
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("saved_unreadable") from None


@router.get(
    "/api/profiles/{profile_id}/admissions-actions",
    response_model=ActionsCurrentOutV1,
)
def read_admissions_actions(
    profile_id: str, principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> ActionsCurrentOutV1:
    try:
        with session.no_autoflush:
            _owned_read(session, profile_id, principal)
            current = _load_current(session, profile_id)
            ids = s.source_target_ids(current.state) if current.state is not None else []
            research = has_full_access(session, principal.organization_id, profile_id) if ids else False
            initial, _ = _source_token(session, profile_id, ids, include_evidence=research)
            statuses, links = _current_sources(session, profile_id, principal, current.state, utcnow()) if ids else ([], [])
            research_after = has_full_access(session, principal.organization_id, profile_id) if ids else False
            rechecked, metadata = _source_token(session, profile_id, ids, include_evidence=research_after)
            if _head_token(session, profile_id) != current.token:
                raise d.ActionError("saved_unreadable")
            _assert_actor(session, principal)
            now = utcnow()
            if not research_after or initial != rechecked:
                statuses = [_status(_target_observation(profile_id, result_id, metadata, research_after), now)
                            for result_id in ids]
                links = [_unavailable_links(result_id) for result_id in ids]
            reviews = [DocumentReportReviewV1(task_id=item.id, reasons=d.report_review_reasons(item))
                       for item in current.state.document_tasks
                       if d.report_review_reasons(item)] if current.state is not None else []
            return ActionsCurrentOutV1(
                profile_id=profile_id, revision=current.state.revision if current.state is not None else 0,
                state=current.state, head_receipt=current.head, observed_at=now,
                current_source_statuses=statuses, document_report_reviews=reviews, action_links=links,
            )
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("saved_unreadable") from None


@router.get(
    "/api/profiles/{profile_id}/admissions-actions/events",
    response_model=ActionsHistoryOutV1,
)
def read_admissions_events(
    profile_id: str,
    after_revision: Annotated[int, Query(ge=0, le=2147483647)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
) -> ActionsHistoryOutV1:
    try:
        with session.no_autoflush:
            _owned_read(session, profile_id, principal)
            if type(after_revision) is not int or not 0 <= after_revision <= 2147483647 or type(limit) is not int or not 1 <= limit <= 100:
                raise d.ActionError("input_invalid")
            rows = session.query(AdmissionsActionsEventRow).filter(
                AdmissionsActionsEventRow.profile_id == profile_id,
                AdmissionsActionsEventRow.revision > after_revision,
            ).order_by(AdmissionsActionsEventRow.revision).limit(limit + 1).all()
            receipts = [_event_receipt(row) for row in rows]
            page = receipts[:limit]
            return ActionsHistoryOutV1(
                profile_id=profile_id, events=page,
                next_after_revision=page[-1].revision if len(receipts) > limit else None,
            )
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("saved_unreadable") from None


@router.get(
    "/api/profiles/{profile_id}/admissions-actions/events/{event_id}",
    response_model=s.ActionWriteReceiptV1,
)
def read_admissions_event(
    profile_id: str, event_id: str, principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> s.ActionWriteReceiptV1:
    try:
        with session.no_autoflush:
            _owned_read(session, profile_id, principal)
            try:
                checked = TypeAdapter(s.ExactId).validate_python(event_id)
            except (ValueError, TypeError):
                raise d.ActionError("input_invalid") from None
            return _exact_event(session, profile_id, checked)
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("saved_unreadable") from None


def export_admissions_action_records(session: Session, profile_id: str) -> dict:
    """All own accepted history, independently validated; no source/plan I/O."""
    try:
        with session.no_autoflush:
            current = _load_current(session, profile_id)
            rows = session.query(AdmissionsActionsEventRow).filter(
                AdmissionsActionsEventRow.profile_id == profile_id,
            ).order_by(AdmissionsActionsEventRow.revision).populate_existing().all()
            events = [_event_receipt(row) for row in rows]
            events = d.validate_complete_export(
                current.state, [item for item in events], profile_id=profile_id,
            )
            # Loading all history is not an atomic snapshot at READ COMMITTED.
            # Catch a save after its last row read as well as current N/history N+1.
            if _head_token(session, profile_id) != current.token:
                raise d.ActionError("saved_unreadable")
            return {
                "current": current.state.model_dump(mode="json") if current.state is not None else None,
                "events": [item.model_dump(mode="json") for item in events],
                "submission_declarations": [item.model_dump(mode="json") for item in events
                                            if isinstance(item.applied_delta.declaration, s.DeclaredSubmissionV1)],
            }
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("saved_unreadable") from None


def _g2_goal_ids(session: Session, profile_id: str) -> list[str]:
    """Saved own reference IDs bound before the public mutable G2 read.

    This is not a substitute for its guarded current/history validation. It
    only bounds the initial source token so a source change during that read
    cannot be accepted as an unchanged post-read baseline.
    """
    row = session.query(SharedRouteCurrentRow).filter(
        SharedRouteCurrentRow.profile_id == profile_id,
    ).populate_existing().first()
    if row is None:
        return []
    receipt = d.validate_model(SharedRouteWriteReceiptV1, row.snapshot, "plan_unreadable")
    if (
        receipt.profile_id != profile_id or receipt.revision != row.revision
        or receipt.schema_version != row.schema_version or receipt.snapshot_digest != row.digest
        or _db_utc(receipt.accepted_at) != _db_utc(row.updated_at)
    ):
        raise d.ActionError("plan_unreadable")
    return list(receipt.selected_result_ids)


def _permission_unavailable(now: datetime) -> s.PreparationAccessReadV1:
    return s.PreparationAccessReadV1(
        allowed=False, reason="unavailable", starts_at=None, ends_at=None,
        development_only=False, observed_at=now,
    )


def _permission_at(
    observed: s.PreparationAccessReadV1, now: datetime,
) -> s.PreparationAccessReadV1:
    """Terminal clock bound of the already observed native permission, no SQL."""
    if observed.development_only:
        return s.PreparationAccessReadV1(
            allowed=True, reason="development", starts_at=observed.starts_at,
            ends_at=observed.ends_at, development_only=True, observed_at=now,
        )
    starts, ends = observed.starts_at, observed.ends_at
    allowed = observed.allowed and starts is not None and ends is not None and starts <= now < ends
    reason: Literal["active", "expired", "not_started", "unavailable", "development"] = (
        "active" if allowed else "expired" if ends is not None and ends <= now else
        "not_started" if starts is not None and starts > now else "unavailable"
    )
    return s.PreparationAccessReadV1(
        allowed=allowed, reason=reason, starts_at=starts, ends_at=ends,
        development_only=False, observed_at=now,
    )


def _today_preparation_permission(
    session: Session, profile_id: str, principal: Principal,
) -> s.PreparationAccessReadV1:
    try:
        return _preparation_permission(session, profile_id, principal)
    except HTTPException as exc:
        if exc.status_code == 401 or (exc.status_code == 404 and exc.detail == "Applicant case not found"):
            raise
        return _permission_unavailable(utcnow())
    except (d.ActionError, ValueError, TypeError, OverflowError, RecursionError):
        return _permission_unavailable(utcnow())


def _component_token(
    actions: str, native: str, sources: str, research: bool,
    preparation: s.PreparationAccessReadV1, as_of: datetime, timezone: str,
) -> str:
    return s.reference_digest("g3-today-components-v1", {
        "actions": actions, "native": native, "sources": sources,
        "research_access": research,
        "preparation_access": {
            "allowed": preparation.allowed, "reason": preparation.reason,
            "starts_at": preparation.starts_at, "ends_at": preparation.ends_at,
            "development_only": preparation.development_only,
        },
        # A today-based native V1 read crossing its display day needs refresh,
        # even if no database head changed. Clock instants themselves are not
        # included, which would mark every stable component read as mixed.
        "comparison_date": as_of.astimezone(ZoneInfo(timezone)).date(),
        "comparison_zone": timezone,
    })


def _unknown_sources(
    profile_id: str, ids: list[str], metadata: dict[str, _Target], research: bool,
    now: datetime,
) -> list[s.SourceReadStatusV1]:
    return [_status(_target_observation(profile_id, result_id, metadata, research), now)
            for result_id in ids]


@router.get("/api/profiles/{profile_id}/today", response_model=s.TodayProjectionV1)
def read_today(
    profile_id: str, timezone: str | None = None,
    principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
) -> s.TodayProjectionV1:
    try:
        with session.no_autoflush:
            _owned_read(session, profile_id, principal)
            requested_zone = None
            if timezone is not None:
                try:
                    requested_zone = TypeAdapter(s.IanaZone).validate_python(timezone)
                except (ValueError, TypeError):
                    raise d.ActionError("input_invalid") from None
            started_at = utcnow()
            current: _Current
            action_state: Literal["readable", "absent", "unavailable"]
            try:
                current = _load_current(session, profile_id)
                action_state = "readable" if current.state is not None else "absent"
            except d.ActionError:
                # Malformed G3 is visible as unavailable, never as a reset or
                # permission to derive a different native preparation origin.
                try:
                    token = _head_token(session, profile_id)
                except d.ActionError:
                    token = s.reference_digest("g3-unreadable-head-v1", {"profile_id": profile_id})
                current = _Current(None, None, token)
                action_state = "unavailable"
            markers = _native_markers(session, profile_id)
            selection = current.state.active_preparation if current.state is not None else None
            origin = d.choose_origin(selection, d.NativePresenceV1(
                g3_readable=action_state != "unavailable",
                g2_current_present=markers.g2_current, g2_history_present=markers.g2_history,
                legacy_v2_marker_present=markers.v2_marker, legacy_v1_row_present=markers.v1_row,
            ))
            personal_ids = s.source_target_ids(current.state) if current.state is not None else []
            goals: list[str] = []
            pre_plan_unreadable = False
            if origin == "g2":
                try:
                    goals = _g2_goal_ids(session, profile_id)
                except d.ActionError:
                    pre_plan_unreadable = True
            ids = list(dict.fromkeys([*personal_ids, *goals]))
            research = has_full_access(session, principal.organization_id, profile_id)
            preparation_before = _today_preparation_permission(session, profile_id, principal)
            sources_before, _ = _source_token(session, profile_id, ids, include_evidence=research)
            plan: _Plan
            if pre_plan_unreadable:
                plan = _unavailable_plan("g2", selection, utcnow())
            else:
                try:
                    plan = _safe_plan(session, profile_id, principal, origin, selection, utcnow())
                except d.ActionError:
                    # Keep the selected origin. A corrupt/expired native slice
                    # cannot replace it with a more convenient legacy workload.
                    unavailable_origin: Literal["g2", "legacy_v2", "legacy_v1", "unknown"] = (
                        "g2" if origin == "g2" else "legacy_v2" if origin == "legacy_v2" else
                        "legacy_v1" if origin == "legacy_v1" else "unknown"
                    )
                    plan = _unavailable_plan(unavailable_origin, selection, utcnow())
            if origin == "g2" and plan.read.goal_result_ids != goals and plan.read.state in {"available", "needs_review"}:
                # The native current changed between the bounded saved-ref
                # observation and its public read. No unbound new source role.
                plan = _unavailable_plan("g2", selection, utcnow())
            display_zone = requested_zone or plan.timezone or "UTC"
            statuses, _ = _current_sources(
                session, profile_id, principal, current.state, utcnow(),
            ) if personal_ids else ([], [])
            by_id = {item.result_id: item for item in statuses}
            for item in plan.source_statuses:
                if item.result_id not in by_id:
                    by_id[item.result_id] = item
            # If a native plan failed, its saved goals remain bounded references
            # but do not get invented premium facts or a previous source digest.
            metadata = _target_metadata(session, profile_id, ids)
            for item in _unknown_sources(profile_id, ids, metadata, research, utcnow()):
                if item.result_id not in by_id:
                    by_id[item.result_id] = item
            statuses = [by_id[result_id] for result_id in ids if result_id in by_id]
            # Failed plan has no public goal IDs. Omit its goal-only status role;
            # own personal references remain independent and readable.
            visible_union = set(personal_ids) | set(plan.read.goal_result_ids)
            statuses = [item for item in statuses if item.result_id in visible_union]
            initial = _component_token(
                current.token, markers.token, sources_before, research,
                preparation_before, started_at, display_zone,
            )
            # One bounded scalar/token recheck, no loop, reallocation, source
            # assembly repeat, second Session or transactional snapshot claim.
            try:
                head_after = _head_token(session, profile_id)
            except d.ActionError:
                if action_state != "unavailable":
                    raise
                head_after = current.token
            native_after = _native_markers(session, profile_id)
            research_after = has_full_access(session, principal.organization_id, profile_id)
            preparation_after = _today_preparation_permission(session, profile_id, principal)
            sources_after, final_metadata = _source_token(
                session, profile_id, ids, include_evidence=research_after,
            )
            _owned_read(session, profile_id, principal)
            as_of = utcnow()
            preparation_after = _permission_at(preparation_after, as_of)
            rechecked = _component_token(
                head_after, native_after.token, sources_after, research_after,
                preparation_after, as_of, display_zone,
            )
            if sources_before != sources_after or not research_after:
                statuses = _unknown_sources(
                    profile_id, [item.result_id for item in statuses], final_metadata,
                    research_after, as_of,
                )
            return d.project_today(d.TodayComponentsV1(
                profile_id=profile_id, as_of=as_of, display_timezone=display_zone,
                action_state=action_state, actions=current.state, action_observed_at=started_at,
                active_plan=plan.read, preparation_access=preparation_after,
                source_statuses=statuses, initial_component_token=initial,
                rechecked_component_token=rechecked,
                research_access_after_recheck=research_after,
            ))
    except d.ActionError as exc:
        raise HTTPException(exc.status, exc.detail) from None
    except SQLAlchemyError:
        raise _http("saved_unreadable") from None

