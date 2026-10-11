"""A separate read-only router for owned programme evidence.

No calls to v1 handlers, worker/provider/collection, schedule or attempt seams.
Native ownership/entitlement/freshness rules are reused; private loader logic is
duplicated intentionally so every existing preparation handler remains unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.tenancy import owned_profile
from app.db import get_session
from app.domain.claim_scope import RequestedScope
from app.domain.enums import ClaimStatus, PipelineStage, UserDecision
from app.domain.freshness import age_days, is_stale
from app.domain.preparation_graph import (
    GraphSelectionError,
    ProgrammeEvidence,
    build_preparation_graph,
)
from app.models import ApplicantProfileRow, ClaimRow, ConflictRow, ProgramResultRow, ResearchRun
from app.models.base import ensure_utc, utcnow
from app.payments.entitlements import has_full_access
from app.schemas.claim import ClaimOut, Conflict
from app.schemas.preparation_graph import PreparationGraph, PreparationGraphRequest
from app.schemas.preparation_graph_loader import StoredPreparationGraphFields
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import DocumentChecklist
from app.security import Principal, get_principal

router = APIRouter(tags=["preparation"])
_PARSE_FAILURES = (ValidationError, TypeError, ValueError, PydanticSerializationError)
_DECISIONS = {UserDecision.APPROVED, UserDecision.MAYBE}


@dataclass(frozen=True, slots=True)
class _Selection:
    result_id: str
    run_id: str
    decision: UserDecision


@dataclass(frozen=True, slots=True)
class _LoadedResult:
    row: ProgramResultRow
    stage: str
    cancelled: bool


def _selection(requested: list[str], rows: list[tuple[str, str, str]]) -> list[_Selection]:
    metadata = {key: (run_id, decision) for key, run_id, decision in rows}
    # Check completeness before decisions: a mixed foreign/rejected selection
    # must not disclose a partial graph or change the generic missing response.
    if len(metadata) != len(rows) or set(metadata) != set(requested):
        raise HTTPException(404, "Result not found")
    selected = []
    for key in requested:
        run_id, raw_decision = metadata[key]
        try:
            decision = UserDecision(raw_decision)
        except ValueError as exc:
            raise HTTPException(422, "Only approved or maybe results can be selected") from exc
        if decision not in _DECISIONS:
            raise HTTPException(422, "Only approved or maybe results can be selected")
        selected.append(_Selection(key, run_id, decision))
    return selected


def _minimal_evidence(
    profile_id: str,
    selected: _Selection,
    *,
    locked: bool = False,
    failure: Literal["unknown", "conflicted"] | None = None,
) -> ProgrammeEvidence:
    # Nothing in this envelope is guessed from unreadable premium fields.
    # The sealed pure DTO hides the run ID for locked cards and the unreadable
    # names/scope/payload for unavailable cards. An authorized unavailable card
    # can retain its validated run receipt.
    return ProgrammeEvidence(
        profile_id=profile_id,
        result_id=selected.result_id,
        run_id=selected.run_id,
        user_decision=selected.decision,
        university="",
        programme="",
        requested_scope=RequestedScope(),
        research_access=not locked,
        evidence_failure=failure,
    )


def _json_snapshot(value: object) -> None:
    # RequirementCheck/Claim.normalized_value is Any. Finite JSON is required
    # before the sealed pure projector hashes it; do not stringify arbitrary data.
    json.dumps(value, allow_nan=False)


def _stored_fields(result: ProgramResultRow) -> StoredPreparationGraphFields:
    if not isinstance(result.payload, dict):
        raise ValueError("Stored result payload is not a document")
    payload = result.payload
    fields = StoredPreparationGraphFields.model_validate(
        {
            "requirement_checks": payload.get("requirement_checks", []),
            "scholarships": payload.get("scholarships", []),
            "unresolved": payload.get("unresolved", []),
            "checklist": payload.get("checklist"),
        }
    )
    column_checklist = None
    if result.checklist is not None:
        column_checklist = DocumentChecklist.model_validate(result.checklist)
    if (
        column_checklist is not None
        and fields.checklist is not None
        and column_checklist.model_dump(mode="json") != fields.checklist.model_dump(mode="json")
    ):
        raise ValueError("Stored checklist projections disagree")
    checklist = column_checklist if column_checklist is not None else fields.checklist
    if checklist is not None and (
        checklist.result_id != result.id
        or checklist.university != result.university
        or checklist.program != result.program
    ):
        raise ValueError("Checklist identity belongs to a different programme result")
    # Revalidate after the authoritative column/legacy fallback choice. No payload
    # mutation or normalization is saved to the result row.
    return StoredPreparationGraphFields.model_validate(
        {
            **fields.model_dump(mode="json"),
            "checklist": checklist.model_dump(mode="json") if checklist is not None else None,
        }
    )


def _claims(rows: list[ClaimRow], now: datetime) -> tuple[tuple[ClaimOut, ...], bool]:
    claims: list[ClaimOut] = []
    failed = False
    for row in rows:
        try:
            if not isinstance(row.payload, dict):
                raise ValueError("Stored claim payload is not a document")
            claim = ClaimOut.model_validate(
                {
                    **row.payload,
                    "id": row.id,
                    "claim_type": row.claim_type,
                    "status": row.status,
                    "source_url": row.source_url,
                    "source_specificity": row.source_specificity,
                    "accessed_at": row.accessed_at,
                }
            )
            claim.is_stale = is_stale(claim.claim_type, claim.accessed_at, now) or claim.status in {
                ClaimStatus.POSSIBLY_STALE,
                ClaimStatus.SUPERSEDED,
            }
            claim.age_days = age_days(claim.accessed_at, now)
            _json_snapshot(claim.model_dump(mode="json"))
        except _PARSE_FAILURES:
            failed = True
            continue
        claims.append(claim)
    if len({claim.id for claim in claims}) != len(claims):
        failed = True
    return tuple(claims), failed


def _conflicts(rows: list[ConflictRow]) -> tuple[tuple[Conflict, ...], bool]:
    conflicts: list[Conflict] = []
    failed = False
    for row in rows:
        try:
            if not isinstance(row.payload, dict):
                raise ValueError("Stored conflict payload is not a document")
            conflict = Conflict.model_validate(
                {
                    **row.payload,
                    "claim_type": row.claim_type,
                    "unresolved": True,
                }
            )
            _json_snapshot(conflict.model_dump(mode="json"))
        except _PARSE_FAILURES:
            failed = True
            continue
        conflicts.append(conflict)
    return tuple(conflicts), failed


def _source_slice(
    profile: ApplicantProfileRow,
    applicant: ApplicantProfileIn | None,
    selected: _Selection,
    loaded: _LoadedResult,
    claim_rows: list[ClaimRow],
    conflict_rows: list[ConflictRow],
    now: datetime,
) -> ProgrammeEvidence:
    # Conflict refusal takes precedence over other malformed stored fields.
    conflicts, conflict_failure = _conflicts(conflict_rows)
    if conflict_failure:
        return _minimal_evidence(profile.id, selected, failure="conflicted")
    claims, claim_failure = _claims(claim_rows, now)
    if applicant is None or claim_failure:
        return _minimal_evidence(
            profile.id, selected, failure="conflicted" if conflicts else "unknown"
        )
    result = loaded.row
    try:
        fields = _stored_fields(result)
        recorded = ensure_utc(result.created_at)
        updated = ensure_utc(profile.updated_at)
        if recorded is None or updated is None:
            raise ValueError("Stored evidence timestamps are incomplete")
        requested = RequestedScope(
            university=result.university,
            programme=result.program,
            degree=applicant.context.level.value,
            intake=f"{applicant.context.intake_term} {applicant.context.intake_year}",
            nationality=applicant.context.citizenship,
            residency=applicant.context.country_of_residence,
            qualification=applicant.context.education_system,
        )
        partial = (
            loaded.stage != PipelineStage.COMPLETED.value
            or loaded.cancelled
            or bool(fields.unresolved)
        )
        if fields.checklist is not None:
            partial = (
                partial
                or fields.checklist.completeness != "official"
                or bool(fields.checklist.unresolved)
            )
        evidence = ProgrammeEvidence(
            profile_id=profile.id,
            result_id=result.id,
            run_id=result.run_id,
            user_decision=selected.decision,
            university=result.university,
            programme=result.program,
            requested_scope=requested,
            research_access=True,
            requirement_checks=tuple(fields.requirement_checks),
            claims=claims,
            conflicts=conflicts,
            scholarships=tuple(fields.scholarships),
            checklist=fields.checklist,
            unresolved_questions=tuple(fields.unresolved),
            stale_result=updated > recorded,
            partial=partial,
        )
        # Per-slice validation/hashing must succeed before joining the graph.
        # This is a second pure projection only, with no I/O or saved state.
        build_preparation_graph(
            profile.id,
            PreparationGraphRequest(selected_result_ids=[result.id]),
            (evidence,),
        )
        return evidence
    except _PARSE_FAILURES:
        # Keep a validated unresolved conflict conservative if another field
        # was unreadable. Do not hide it behind an optimistic empty slice.
        failure: Literal["unknown", "conflicted"] = "conflicted" if conflicts else "unknown"
        return _minimal_evidence(profile.id, selected, failure=failure)


@router.get("/api/profiles/{profile_id}/preparation/graph", response_model=PreparationGraph)
def preparation_graph(
    profile_id: str,
    result_id: list[str] = Query(..., min_length=1, max_length=20),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> PreparationGraph:
    try:
        request = PreparationGraphRequest(selected_result_ids=result_id)
    except ValidationError as exc:
        raise HTTPException(422, "Select 1 to 20 unique exact result IDs") from exc
    with session.no_autoflush:
        profile = owned_profile(session, profile_id, principal)
        # Select only ID/run/decision columns here. No premium result payload,
        # checklist, names, run diagnostics, claims or conflicts enter the locked path.
        metadata_rows = (
            session.query(
                ProgramResultRow.id, ProgramResultRow.run_id, ProgramResultRow.user_decision
            )
            .join(ResearchRun)
            .filter(
                ResearchRun.profile_id == profile_id,
                ProgramResultRow.id.in_(request.selected_result_ids),
            )
            .all()
        )
        selected = _selection(
            request.selected_result_ids, [(row[0], row[1], row[2]) for row in metadata_rows]
        )
        if not has_full_access(session, principal.organization_id, profile_id):
            return build_preparation_graph(
                profile_id,
                request,
                tuple(_minimal_evidence(profile_id, item, locked=True) for item in selected),
            )
        now = utcnow()  # One freshness timestamp for the entire authorized read.
        result_rows = (
            session.query(ProgramResultRow, ResearchRun.stage, ResearchRun.cancelled)
            .join(ResearchRun)
            .filter(
                ResearchRun.profile_id == profile_id,
                ProgramResultRow.id.in_(request.selected_result_ids),
            )
            .all()
        )
        # Revalidate the whole owned selection against this current read view;
        # no guarantee of repeatable-read is implied by a source fingerprint.
        selected = _selection(
            request.selected_result_ids,
            [(row.id, row.run_id, row.user_decision) for row, _stage, _cancelled in result_rows],
        )
        loaded = {
            row.id: _LoadedResult(row, stage, cancelled) for row, stage, cancelled in result_rows
        }
        run_ids = {item.run_id for item in selected}
        claim_rows = (
            session.query(ClaimRow)
            .filter(
                ClaimRow.run_id.in_(run_ids),
                or_(
                    ClaimRow.result_id.in_(request.selected_result_ids),
                    ClaimRow.result_id.is_(None),
                ),
            )
            .order_by(ClaimRow.run_id, ClaimRow.id)
            .all()
        )
        conflict_rows = (
            session.query(ConflictRow)
            .filter(
                ConflictRow.run_id.in_(run_ids),
                ConflictRow.unresolved.is_(True),
                or_(
                    ConflictRow.result_id.in_(request.selected_result_ids),
                    ConflictRow.result_id.is_(None),
                ),
            )
            .order_by(ConflictRow.run_id, ConflictRow.id)
            .all()
        )
        try:
            applicant = ApplicantProfileIn.model_validate(profile.payload)
        except _PARSE_FAILURES:
            applicant = None
        evidence = tuple(
            _source_slice(
                profile,
                applicant,
                item,
                loaded[item.result_id],
                [
                    row
                    for row in claim_rows
                    if row.run_id == item.run_id and row.result_id in {None, item.result_id}
                ],
                [
                    row
                    for row in conflict_rows
                    if row.run_id == item.run_id and row.result_id in {None, item.result_id}
                ],
                now,
            )
            for item in selected
        )
        try:
            return build_preparation_graph(profile_id, request, evidence)
        except GraphSelectionError as exc:
            if exc.code == "result_not_found":
                raise HTTPException(404, "Result not found") from exc
            raise HTTPException(422, "Only approved or maybe results can be selected") from exc
