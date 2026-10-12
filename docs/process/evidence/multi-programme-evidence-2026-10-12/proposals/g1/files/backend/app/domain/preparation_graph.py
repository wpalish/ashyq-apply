"""G1 PROPOSAL / NOT_APPLIED: pure projection of already loaded owned evidence.

No clocks, sessions, adapters, filesystem access, model calls, targets or scheduling.
The caller owns authorization and authoritative-row/freshness validation. A frozen
dataclass is an input envelope, not proof that a database row is owned.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

from app.domain.claim_scope import ClaimScope, RequestedScope, Verdict
from app.domain.enums import ClaimType, UserDecision
from app.domain.preparation import (
    NOTICE,
    _claim_state,
    _compatible_with_label,
    _LEGACY_EXAM_TYPES,
    _referenced_claims,
    combine_states,
    project_checks,
)
from app.schemas.claim import ClaimOut, Conflict, UnresolvedQuestion
from app.schemas.preparation import EvidenceState, PreparationCheck
from app.schemas.preparation_graph import (
    ChecklistLocation,
    ClaimProof,
    DocumentAction,
    DocumentDependency,
    ExamFamily,
    ExamWorkstream,
    KnownExamFamily,
    LOCKED_NOTICE,
    PolicyGroup,
    PreparationGraph,
    PreparationGraphRequest,
    ProgrammeProjection,
    ProgrammeSourceManifest,
    ProjectionState,
    ReasonCode,
    RequirementAtom,
    RequirementMetric,
    ScopeProof,
)
from app.schemas.result import DocumentChecklist, RequirementCheck, Scholarship

GRAPH_NOTICE = NOTICE + (
    " This graph covers stored exam checks and stored document checklists only. "
    "Family groups do not establish an accepted test edition, route, shared workload or target. "
    "Document links do not record completion, validation, submission or university receipt."
)
_ENGLISH_TYPES = frozenset({
    ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE,
    ClaimType.IELTS_ACCEPTED_TYPES, ClaimType.TOEFL_MIN_TOTAL,
    ClaimType.DUOLINGO_MIN, ClaimType.ENGLISH_TEST_WAIVER,
    ClaimType.ENGLISH_EVIDENCE_MINIMUM,
})
_DOCUMENT_TYPES = frozenset({
    ClaimType.REQUIRED_DOCUMENT, ClaimType.ESSAY_PROMPT,
    ClaimType.RECOMMENDATION_REQUIREMENT, ClaimType.DOCUMENT_BY_COMPLETION,
})
_CHECKLIST_LOCATIONS: tuple[ChecklistLocation, ...] = (
    "admission_documents", "scholarship_documents", "applicant_actions",
    "school_actions", "recommender_actions", "certification_actions",
)
_FAMILIES: tuple[KnownExamFamily, ...] = ("ielts", "sat", "toefl", "duolingo")


@dataclass(frozen=True, slots=True)
class ProgrammeEvidence:
    """Server-loaded input. Never construct this envelope from a client result payload."""

    profile_id: str
    result_id: str
    run_id: str
    user_decision: UserDecision
    university: str
    programme: str
    requested_scope: RequestedScope
    research_access: bool
    requirement_checks: tuple[RequirementCheck, ...] = ()
    claims: tuple[ClaimOut, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    scholarships: tuple[Scholarship, ...] = ()
    checklist: DocumentChecklist | None = None
    unresolved_questions: tuple[UnresolvedQuestion, ...] = ()
    stale_result: bool = False
    partial: bool = False
    evidence_failure: Literal["unknown", "conflicted"] | None = None


class GraphSelectionError(ValueError):
    """Map missing/foreign uniformly to 404; ineligible explicit decisions to 422."""

    def __init__(self, code: Literal["result_not_found", "result_not_selected"]):
        self.code = code
        super().__init__(code)


def _digest(value: Any) -> str:
    # JSON-only evidence; unsupported historical objects fail validation, not str(object).
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _key(kind: str, value: Any) -> str:
    return f"{kind}-{_digest(value)[:24]}"


def _normal(value: str) -> str:
    return value.strip().casefold()


def _scope(scope: ClaimScope | None, requested: RequestedScope) -> ScopeProof:
    return ScopeProof(
        requested=requested,
        published=scope,
        verdict=scope.covers(requested) if scope is not None else Verdict.UNKNOWN,
        gaps=list(scope.gaps(requested)) if scope is not None else list(requested.stated()),
        contradictions=list(scope.contradictions(requested)) if scope is not None else [],
    )


def _proof(claim: ClaimOut, requested: RequestedScope) -> ClaimProof:
    return ClaimProof(claim=claim.model_copy(deep=True), scope=_scope(claim.scope, requested))


def _state_reason(state: EvidenceState) -> list[ReasonCode]:
    mapping: dict[EvidenceState, ReasonCode] = {
        "locked": "research_locked", "unknown": "evidence_unknown",
        "stale": "evidence_stale", "conflicted": "evidence_conflicted",
        "current": "evidence_unknown",  # Not read for current.
    }
    return [] if state == "current" else [mapping[state]]


def _family(claims: list[ClaimOut]) -> ExamFamily:
    families: set[ExamFamily] = set()
    for claim in claims:
        kind = claim.claim_type
        if kind in {ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE,
                    ClaimType.IELTS_ACCEPTED_TYPES}:
            families.add("ielts")
        elif kind in {ClaimType.SAT_MIN_TOTAL, ClaimType.SAT_POLICY, ClaimType.SUPERSCORE_POLICY}:
            families.add("sat")
        elif kind == ClaimType.TOEFL_MIN_TOTAL:
            families.add("toefl")
        elif kind == ClaimType.DUOLINGO_MIN:
            families.add("duolingo")
        elif kind == ClaimType.SCHOLARSHIP_MIN_TEST_SCORE:
            # Existing web_scholarships.py publishes exactly {exam_name: raw_value}.
            # Recognizing that one key is family observation, never a parsed numeric target.
            value = claim.normalized_value
            if isinstance(value, dict) and len(value) == 1:
                name = next(iter(value))
                if name in {"ielts", "sat", "toefl"}:
                    families.add(cast(ExamFamily, name))
                else:
                    families.add("unknown")
            else:
                families.add("unknown")
        else:
            families.add("unknown")
    return next(iter(families)) if len(families) == 1 else "unknown"


def _metric(check: RequirementCheck, claims: list[ClaimOut]) -> RequirementMetric:
    label = _normal(check.requirement)
    types = {claim.claim_type for claim in claims}
    if label == "ielts overall" and ClaimType.IELTS_MIN_OVERALL in types:
        return "overall"
    for component in ("listening", "reading", "writing", "speaking"):
        if label == f"ielts {component}" and ClaimType.IELTS_MIN_SUBSCORE in types:
            return cast(RequirementMetric, component)
    if label in {"sat total", "toefl total"} and types & {
        ClaimType.SAT_MIN_TOTAL, ClaimType.TOEFL_MIN_TOTAL
    }:
        return "total"
    if label == "sat policy" and ClaimType.SAT_POLICY in types:
        return "policy"
    if label == "accepted ielts test type" and ClaimType.IELTS_ACCEPTED_TYPES in types:
        return "accepted_type"
    # Legacy SAT skill labels alone cannot turn SAT_MIN_TOTAL into numeric section evidence.
    return "unknown"


def _atom(row: ProgrammeEvidence, projected: PreparationCheck, index: int,
          pool: list[ClaimOut], scholarship: Scholarship | None = None) -> RequirementAtom:
    check = projected.requirement_check
    proofs = [_proof(claim, row.requested_scope) for claim in sorted(projected.claims, key=lambda c: c.id)]
    reasons: list[ReasonCode] = _state_reason(projected.evidence_state)
    _, matched = _referenced_claims(check, pool, check.requirement.casefold())
    if not check.claim_ids or matched != set(check.claim_ids):
        reasons.append("claim_reference_unresolved")
    allowed = _LEGACY_EXAM_TYPES.get(check.requirement.casefold())
    for reference in set(check.claim_ids) - matched:
        if reference.startswith(("https://", "http://")) and allowed is not None:
            candidates = [claim for claim in pool if claim.source_url == reference
                          and claim.claim_type in allowed
                          and _compatible_with_label(claim, check.requirement.casefold())]
            if len(candidates) > 1:
                reasons.append("legacy_url_ambiguous")
    for proof in proofs:
        if proof.scope.published is None:
            reasons.append("scope_unrecorded")
        if proof.scope.verdict == Verdict.NO:
            reasons.append("scope_mismatch")
        elif proof.scope.verdict == Verdict.UNKNOWN:
            reasons.append("scope_unknown")
    state, policy = projected.evidence_state, projected.policy
    if scholarship is None and any(claim.claim_type.value.startswith("scholarship_")
                                   for claim in projected.claims):
        state = combine_states([state, "unknown"])
        policy = "unknown"
        reasons.append("requirement_purpose_unestablished")
    if scholarship is not None and not projected.claims:
        reasons.append("scholarship_subject_unestablished")
    if policy == "unknown":
        reasons.append("policy_unknown")
    elif policy == "waiver_check":
        reasons.append("waiver_requires_review")
    elif policy == "alternatives_unresolved":
        reasons.append("alternatives_unresolved")
    family = _family(projected.claims)
    if family == "unknown":
        reasons.append("exam_family_unestablished")
    reasons.append("exam_identity_unestablished")
    purpose: Literal["admission", "scholarship"] = "scholarship" if scholarship is not None else "admission"
    # G1 nodes are read-only occurrences in a stored ordered check snapshot. The index
    # keeps duplicate checks visible. Cite order/access time do not alter identity.
    # G2 must explicitly version/remap this occurrence identity before persistent use.
    identity = {
        "result_id": row.result_id, "purpose": purpose,
        "scholarship_id": scholarship.id if scholarship is not None else None,
        "requested": asdict(row.requested_scope), "check_index": index,
        "label": _normal(check.requirement),
        "published_value": check.model_dump(mode="json")["published_value"],
        "claim_types": sorted({claim.claim_type.value for claim in projected.claims}),
    }
    return RequirementAtom(
        id=_key("req", identity), result_id=row.result_id, source_check_index=index,
        purpose=purpose, scholarship_id=scholarship.id if scholarship is not None else None,
        scholarship_subject=scholarship.name if scholarship is not None else None,
        original_check=check.model_copy(deep=True), evidence_state=state, policy=policy,
        family=family, metric=_metric(check, projected.claims),
        original_reference_ids=list(check.claim_ids),
        resolved_claim_ids=[proof.claim.id for proof in proofs], proofs=proofs,
        source_urls=list(projected.source_urls),
        lesson_id_hints=list(projected.lesson_ids) if state == "current" else [],
        unresolved_reasons=sorted(set(reasons)),
    )


def _policy_groups(row: ProgrammeEvidence, atoms: list[RequirementAtom],
                   pool: list[ClaimOut], scholarship_id: str | None) -> list[PolicyGroup]:
    policies = {atom.policy for atom in atoms}
    contexts: list[tuple[Literal["waiver_check", "alternatives_unresolved"], ReasonCode, list[RequirementAtom]]] = []
    if "waiver_check" in policies:
        contexts.append(("waiver_check", "waiver_requires_review", [atom for atom in atoms if atom.policy == "waiver_check"]))
    all_types = {claim.claim_type for claim in pool}
    co_published_families = sum(bool(all_types & family) for family in (
        {ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE},
        {ClaimType.TOEFL_MIN_TOTAL}, {ClaimType.DUOLINGO_MIN},
    ))
    alternatives_context = co_published_families > 1 or ClaimType.ENGLISH_EVIDENCE_MINIMUM in all_types
    alternative_members = [atom for atom in atoms if atom.policy == "alternatives_unresolved"
                           or (atom.policy == "waiver_check" and alternatives_context)]
    if alternative_members:
        # Native atoms keep waiver-first policy semantics. A distinct unresolved
        # co-publication context prevents that precedence from hiding route gaps;
        # it still establishes no accepted OR/AND relation or applicable branch.
        contexts.append(("alternatives_unresolved", "alternatives_unresolved", alternative_members))
    return [PolicyGroup(
        id=_key("policy", {"result": row.result_id, "award": scholarship_id, "kind": kind}),
        result_id=row.result_id, purpose="scholarship" if scholarship_id is not None else "admission",
        scholarship_id=scholarship_id, kind=kind, requirement_ids=[atom.id for atom in members],
        context_proofs=[_proof(claim, row.requested_scope) for claim in sorted(pool, key=lambda c: c.id)
                        if claim.claim_type in _ENGLISH_TYPES],
        unresolved_reasons=[reason],
    ) for kind, reason, members in contexts]


def _document_actions(row: ProgrammeEvidence) -> list[DocumentAction]:
    checklist = row.checklist
    if checklist is None:
        return []
    if checklist.result_id != row.result_id:
        raise ValueError("Checklist belongs to a different result")
    actions: dict[str, DocumentAction] = {}
    semantic_occurrences: dict[str, list[str]] = {}
    for location in _CHECKLIST_LOCATIONS:
        for index, item in enumerate(getattr(checklist, location)):
            identity = item.model_dump(mode="json")
            identity.pop("claim_ids", None)
            semantic_key = _key("doc", {"result_id": row.result_id, "item": identity})
            candidates = [key for key in semantic_occurrences.get(semantic_key, [])
                          if location not in actions[key].source_locations]
            if len(candidates) == 1:
                key = candidates[0]
                actions[key].original_items.append(item.model_copy(deep=True))
                actions[key].source_locations.append(location)
                # A repeated owner projection may carry an additional exact proof reference.
                merged = {proof.claim.id: proof for proof in actions[key].proofs}
                for claim in row.claims:
                    if claim.id in item.claim_ids and claim.claim_type in _DOCUMENT_TYPES:
                        merged[claim.id] = _proof(claim, row.requested_scope)
                actions[key].proofs = [merged[value] for value in sorted(merged)]
                continue
            # Only a unique cross-location owner projection may be deduped. Repeated
            # same-list items or multiple potential matches remain separate occurrences.
            key = semantic_key if semantic_key not in actions else _key(
                "doc", {"semantic_key": semantic_key, "location": location, "index": index}
            )
            semantic_occurrences.setdefault(semantic_key, []).append(key)
            proofs = [_proof(claim, row.requested_scope) for claim in sorted(row.claims, key=lambda c: c.id)
                      if claim.id in item.claim_ids and claim.claim_type in _DOCUMENT_TYPES]
            item_scope = _scope(item.scope, row.requested_scope)
            reasons: list[ReasonCode] = ["document_predicate_not_projected"]
            if not item.claim_ids or set(item.claim_ids) != {proof.claim.id for proof in proofs}:
                reasons.append("document_exact_proof_required")
            if item_scope.verdict == Verdict.NO:
                reasons.append("document_scope_mismatch")
            elif item_scope.verdict == Verdict.UNKNOWN:
                reasons.append("document_scope_unknown")
            # G1 deliberately has no normalized document-predicate/format validator. Exact
            # refs and scope are displayed, but do not bless every copied constraint.
            initial_states: list[EvidenceState] = ["unknown"]
            initial_states.extend(_claim_state(proof.claim, row.requested_scope) for proof in proofs)
            if row.stale_result:
                initial_states.append("stale")
            actions[key] = DocumentAction(
                id=key, result_id=row.result_id, original_item=item.model_copy(deep=True),
                original_items=[item.model_copy(deep=True)], source_locations=[location],
                scope=item_scope, proofs=proofs, evidence_state=combine_states(initial_states),
                dependencies=[], unresolved_reasons=sorted(set(reasons)),
            )
    result = list(actions.values())
    for action in result:
        # Recompute after repeated owner projections have contributed their exact refs.
        states: list[EvidenceState] = ["unknown"]
        states.extend(_claim_state(proof.claim, row.requested_scope) for proof in action.proofs)
        if row.stale_result:
            states.append("stale")
        action.evidence_state = combine_states(states)
        for name in action.original_item.depends_on:
            dependency_candidates = [other for other in result if _normal(other.original_item.name) == _normal(name)]
            if not dependency_candidates:
                link = DocumentDependency(original_name=name, target_document_id=None, resolution="missing")
                reason: ReasonCode = "dependency_missing"
            elif action.scope.verdict != Verdict.YES or any(other.scope.verdict != Verdict.YES for other in dependency_candidates):
                link = DocumentDependency(original_name=name, target_document_id=None, resolution="scope_unresolved")
                reason = "dependency_scope_unresolved"
            elif len(dependency_candidates) != 1:
                link = DocumentDependency(original_name=name, target_document_id=None, resolution="ambiguous")
                reason = "dependency_ambiguous"
            else:
                link = DocumentDependency(original_name=name, target_document_id=dependency_candidates[0].id, resolution="linked")
                reason = "dependency_blocked"  # Structural link is not a completion receipt.
            action.dependencies.append(link)
            action.unresolved_reasons.append(reason)
    adjacency = {action.id: [link.target_document_id for link in action.dependencies
                            if link.target_document_id is not None] for action in result}

    def reaches(start: str, target: str) -> bool:
        pending = [start]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current not in seen:
                seen.add(current)
                pending.extend(adjacency[current])
        return False

    for action in result:
        for link in action.dependencies:
            if link.target_document_id is not None and reaches(link.target_document_id, action.id):
                link.resolution = "cycle"
                action.unresolved_reasons.append("dependency_cycle")
        action.unresolved_reasons = sorted(set(action.unresolved_reasons))
    return result


def _manifest(row: ProgrammeEvidence, atoms: list[RequirementAtom],
              documents: list[DocumentAction], groups: list[PolicyGroup]) -> ProgrammeSourceManifest:
    if not row.research_access:
        return ProgrammeSourceManifest(result_id=row.result_id, run_id=None,
                                       result_snapshot_digest=None, authoritative_evidence_digest=None,
                                       resolved_claim_ids=[])
    result = {
        "scope": asdict(row.requested_scope), "decision": row.user_decision.value,
        "checks": [check.model_dump(mode="json") for check in row.requirement_checks],
        "scholarships": [award.model_dump(mode="json") for award in row.scholarships],
        "checklist": row.checklist.model_dump(mode="json", exclude={"generated_at"}) if row.checklist else None,
        "unresolved": [question.model_dump(mode="json") for question in row.unresolved_questions],
        "partial": row.partial, "evidence_failure": row.evidence_failure,
        "stale_result": row.stale_result,
    }
    evidence = {
        "claims": [claim.model_dump(mode="json", exclude={"age_days"}) for claim in sorted(row.claims, key=lambda c: c.id)],
        "conflicts": sorted([conflict.model_dump(mode="json") for conflict in row.conflicts], key=_digest),
    }
    bound_ids = {value for atom in atoms for value in atom.resolved_claim_ids}
    bound_ids.update(proof.claim.id for document in documents for proof in document.proofs)
    bound_ids.update(proof.claim.id for group in groups for proof in group.context_proofs)
    return ProgrammeSourceManifest(
        result_id=row.result_id, run_id=row.run_id,
        result_snapshot_digest=_digest(result), authoritative_evidence_digest=_digest(evidence),
        resolved_claim_ids=sorted(bound_ids),
    )


def build_preparation_graph(profile_id: str, request: PreparationGraphRequest,
                            loaded: tuple[ProgrammeEvidence, ...]) -> PreparationGraph:
    """Project only the complete explicit selection, in requested order.

    Missing/foreign and ineligible IDs fail before projecting any stored payload. The
    API must still enforce owned_profile, query ownership and research entitlement.
    No saved row or progress receipt is produced by this pure function.
    """
    by_id: dict[str, ProgrammeEvidence] = {}
    for row in loaded:
        if row.result_id in by_id:
            raise ValueError("Duplicate server-loaded result identity")
        by_id[row.result_id] = row
    rows: list[ProgrammeEvidence] = []
    for key in request.selected_result_ids:
        row = by_id.get(key)
        if row is None or row.profile_id != profile_id:
            raise GraphSelectionError("result_not_found")
        if row.user_decision not in {UserDecision.APPROVED, UserDecision.MAYBE}:
            raise GraphSelectionError("result_not_selected")
        if len({claim.id for claim in row.claims}) != len(row.claims):
            raise ValueError("Ambiguous authoritative claim identity")
        if len({award.id for award in row.scholarships}) != len(row.scholarships):
            raise ValueError("Ambiguous scholarship identity")
        rows.append(row)
    programmes: list[ProgrammeProjection] = []
    requirements: list[RequirementAtom] = []
    groups: list[PolicyGroup] = []
    documents: list[DocumentAction] = []
    manifests: list[ProgrammeSourceManifest] = []
    for row in rows:
        if not row.research_access or row.evidence_failure is not None:
            if not row.research_access:
                failure_state: EvidenceState = "locked"
            else:
                assert row.evidence_failure is not None
                failure_state = row.evidence_failure
            programmes.append(ProgrammeProjection(
                result_id=row.result_id, run_id=None if failure_state == "locked" else row.run_id,
                user_decision=row.user_decision, university=None, programme=None, requested_scope=None,
                research_access=row.research_access, evidence_state=failure_state,
                projection_state="locked" if failure_state == "locked" else "unavailable",
                requirement_ids=[], document_action_ids=[], unprojected_checks=[], unresolved_questions=[],
                unresolved_reasons=["research_locked" if failure_state == "locked" else "evidence_unavailable"],
                notice=LOCKED_NOTICE if failure_state == "locked" else GRAPH_NOTICE,
            ))
            manifests.append(_manifest(row, [], [], []))
            continue
        atoms: list[RequirementAtom] = []
        unprojected: list[RequirementCheck] = []
        pool = list(row.claims)
        for index, check in enumerate(row.requirement_checks):
            projected = project_checks([check], pool, row.requested_scope,
                                       stale_result=row.stale_result, conflicts=list(row.conflicts))
            if projected:
                atoms.append(_atom(row, projected[0], index, pool))
            else:
                unprojected.append(check.model_copy(deep=True))
        groups.extend(_policy_groups(row, atoms, pool, None))
        reasons: list[ReasonCode] = []
        award_name_counts = {_normal(award.name): sum(_normal(other.name) == _normal(award.name)
                            for other in row.scholarships) for award in row.scholarships}
        for award in row.scholarships:
            # A duplicated award display name is not a unique subject identity.
            subject_keys = {_normal(award.id)}
            if award_name_counts[_normal(award.name)] == 1:
                subject_keys.add(_normal(award.name))
            award_pool = [claim for claim in pool if claim.subject_key is not None
                          and _normal(claim.subject_key) in subject_keys]
            award_atoms: list[RequirementAtom] = []
            if not award.eligibility_checks:
                reasons.append("scholarship_checks_missing")
            for index, check in enumerate(award.eligibility_checks):
                projected = project_checks([check], award_pool, row.requested_scope,
                                           stale_result=row.stale_result, conflicts=list(row.conflicts))
                if projected:
                    award_atoms.append(_atom(row, projected[0], index, award_pool, award))
                else:
                    unprojected.append(check.model_copy(deep=True))
            atoms.extend(award_atoms)
            groups.extend(_policy_groups(row, award_atoms, award_pool, award.id))
        own_documents = _document_actions(row)
        if not atoms:
            reasons.append("checks_missing")
        if unprojected:
            reasons.append("non_exam_checks_not_projected")
        if row.partial:
            reasons.append("evidence_partial")
        if row.checklist is None:
            reasons.append("checklist_missing")
        else:
            if row.checklist.completeness != "official":
                reasons.append("checklist_unavailable" if row.checklist.completeness == "unavailable" else "checklist_partial")
            if row.checklist.unresolved:
                reasons.append("checklist_unresolved")
        questions = [question.model_copy(deep=True) for question in row.unresolved_questions]
        if row.checklist is not None:
            questions.extend(question.model_copy(deep=True) for question in row.checklist.unresolved)
        programme_states: list[EvidenceState] = [atom.evidence_state for atom in atoms]
        if not atoms or row.partial:
            programme_states.append("unknown")
        state = combine_states(programme_states)
        partial = bool(reasons or questions or any(atom.unresolved_reasons for atom in atoms)
                       or any(document.unresolved_reasons for document in own_documents))
        programmes.append(ProgrammeProjection(
            result_id=row.result_id, run_id=row.run_id, user_decision=row.user_decision,
            university=row.university, programme=row.programme, requested_scope=row.requested_scope,
            research_access=True, evidence_state=state, projection_state="partial" if partial else "projected",
            requirement_ids=[atom.id for atom in atoms], document_action_ids=[document.id for document in own_documents],
            unprojected_checks=unprojected, unresolved_questions=questions,
            unresolved_reasons=sorted(set(reasons)), notice=GRAPH_NOTICE,
        ))
        requirements.extend(atoms)
        documents.extend(own_documents)
        manifests.append(_manifest(row, atoms, own_documents,
                                   [group for group in groups if group.result_id == row.result_id]))
    streams: list[ExamWorkstream] = []
    for family in _FAMILIES:
        members = [atom for atom in requirements if atom.family == family]
        if members:
            member_results = {atom.result_id for atom in members}
            streams.append(ExamWorkstream(
                id=_key("exam", {"profile_id": profile_id, "family": family}), family=family,
                requirement_ids=[atom.id for atom in members],
                contributing_result_ids=[key for key in request.selected_result_ids if key in member_results],
                missing_identity_dimensions=["edition", "accepted_variant", "retake_policy", "route"],
            ))
    states = [programme.evidence_state for programme in programmes]
    aggregate: EvidenceState = "locked" if all(state == "locked" for state in states) else combine_states(states)
    projection: ProjectionState
    if all(programme.projection_state == "locked" for programme in programmes):
        projection = "locked"
    elif all(programme.projection_state == "unavailable" for programme in programmes):
        projection = "unavailable"
    else:
        projection = "partial" if any(programme.projection_state != "projected" for programme in programmes) else "projected"
    return PreparationGraph(
        profile_id=profile_id, requested_result_ids=list(request.selected_result_ids),
        selected_result_ids=[row.result_id for row in rows], programmes=programmes,
        requirements=requirements, policy_groups=groups, exam_workstreams=streams,
        document_actions=documents, source_manifest=manifests,
        source_fingerprint=_digest({"profile_id": profile_id, "selection": request.selected_result_ids,
                                    "manifest": [entry.model_dump(mode="json") for entry in manifests]}),
        evidence_state=aggregate, projection_state=projection, notice=GRAPH_NOTICE,
    )
