"""A read-only programme projection, never an accepted study plan."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.claim_scope import ClaimScope, RequestedScope, Verdict
from app.domain.enums import UserDecision
from app.schemas.claim import ClaimOut, UnresolvedQuestion
from app.schemas.preparation import EvidenceState, Policy
from app.schemas.result import DocumentItem, RequirementCheck

ResultId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=32)]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
KnownExamFamily = Literal["ielts", "sat", "toefl", "duolingo"]
ExamFamily = Literal["ielts", "sat", "toefl", "duolingo", "unknown"]
RequirementMetric = Literal[
    "overall",
    "total",
    "listening",
    "reading",
    "writing",
    "speaking",
    "math",
    "reading_writing",
    "policy",
    "accepted_type",
    "unknown",
]
ProjectionState = Literal["projected", "partial", "unavailable", "locked"]
LOCKED_NOTICE = (
    "Research evidence is locked. This view retains only the selected result ID and decision."
)
ReasonCode = Literal[
    "research_locked",
    "evidence_unavailable",
    "evidence_partial",
    "checks_missing",
    "non_exam_checks_not_projected",
    "claim_reference_unresolved",
    "legacy_url_ambiguous",
    "scope_unrecorded",
    "scope_unknown",
    "scope_mismatch",
    "evidence_unknown",
    "evidence_stale",
    "evidence_conflicted",
    "policy_unknown",
    "alternatives_unresolved",
    "waiver_requires_review",
    "exam_family_unestablished",
    "exam_identity_unestablished",
    "scholarship_checks_missing",
    "scholarship_subject_unestablished",
    "requirement_purpose_unestablished",
    "checklist_missing",
    "checklist_partial",
    "checklist_unavailable",
    "checklist_unresolved",
    "document_exact_proof_required",
    "document_predicate_not_projected",
    "document_scope_unknown",
    "document_scope_mismatch",
    "dependency_missing",
    "dependency_ambiguous",
    "dependency_scope_unresolved",
    "dependency_cycle",
    "dependency_blocked",
]
ChecklistLocation = Literal[
    "admission_documents",
    "scholarship_documents",
    "applicant_actions",
    "school_actions",
    "recommender_actions",
    "certification_actions",
]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreparationGraphRequest(Base):
    """Explicit ordered intent, not a list of IDs that the server may silently trim."""

    selected_result_ids: list[ResultId] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def exact_selection(self) -> Self:
        if any(value != value.strip() for value in self.selected_result_ids):
            raise ValueError("Result IDs must not have surrounding whitespace")
        if len(set(self.selected_result_ids)) != len(self.selected_result_ids):
            raise ValueError("Duplicate result IDs are not a selection")
        return self


class ScopeProof(Base):
    requested: RequestedScope
    published: ClaimScope | None
    verdict: Verdict
    gaps: list[str]
    contradictions: list[str]

    @model_validator(mode="after")
    def exact_scope_comparison(self) -> Self:
        expected = (
            self.published.covers(self.requested) if self.published is not None else Verdict.UNKNOWN
        )
        gaps = (
            list(self.published.gaps(self.requested))
            if self.published is not None
            else list(self.requested.stated())
        )
        contradictions = (
            list(self.published.contradictions(self.requested))
            if self.published is not None
            else []
        )
        if self.verdict != expected or self.gaps != gaps or self.contradictions != contradictions:
            raise ValueError("Scope verdict must use the existing exact three-valued comparison")
        return self


class ClaimProof(Base):
    """An exact stored claim plus applicability, without inventing a relation operator."""

    claim: ClaimOut
    scope: ScopeProof

    @model_validator(mode="after")
    def preserve_recorded_scope(self) -> Self:
        if self.scope.published != self.claim.scope:
            raise ValueError("A proof cannot rewrite the stored claim scope")
        return self


class RequirementAtom(Base):
    id: str
    result_id: ResultId
    source_check_index: int = Field(ge=0)
    purpose: Literal["admission", "scholarship"]
    scholarship_id: str | None = None
    scholarship_subject: str | None = None
    original_check: RequirementCheck
    evidence_state: EvidenceState
    policy: Policy
    family: ExamFamily
    metric: RequirementMetric
    original_reference_ids: list[str]
    resolved_claim_ids: list[str]
    proofs: list[ClaimProof]
    source_urls: list[str]
    lesson_id_hints: list[str]
    unresolved_reasons: list[ReasonCode]

    @model_validator(mode="after")
    def exact_proof_identity(self) -> Self:
        if self.resolved_claim_ids != [proof.claim.id for proof in self.proofs]:
            raise ValueError("Resolved IDs must be exact stored proof IDs")
        if self.original_reference_ids != self.original_check.claim_ids:
            raise ValueError("Original check references must remain unchanged")
        if self.purpose == "admission" and self.scholarship_id is not None:
            raise ValueError("An admission requirement cannot borrow an award identity")
        if self.purpose == "scholarship" and self.scholarship_id is None:
            raise ValueError("A scholarship requirement needs its own award identity")
        if self.evidence_state != "current" and (self.policy != "unknown" or self.lesson_id_hints):
            raise ValueError("Uncertain evidence cannot gain a policy or practice hint")
        if self.evidence_state == "current" and (
            not self.proofs or any(proof.scope.verdict != Verdict.YES for proof in self.proofs)
        ):
            raise ValueError("Current requirements need exact applicable evidence")
        return self


class PolicyGroup(Base):
    """G1 does not accept all_of/any_of, selected branches or accepted waivers."""

    id: str
    result_id: ResultId
    purpose: Literal["admission", "scholarship"]
    scholarship_id: str | None = None
    kind: Literal["waiver_check", "alternatives_unresolved", "unresolved"]
    requirement_ids: list[str] = Field(min_length=1)
    context_proofs: list[ClaimProof]
    unresolved_reasons: list[ReasonCode]


class ExamWorkstream(Base):
    """Family-only observation group. It establishes neither compatibility nor a target."""

    id: str
    family: KnownExamFamily
    grouping: Literal["family_only"] = "family_only"
    identity_state: Literal["unknown"] = "unknown"
    edition: Literal[None] = None
    requirement_ids: list[str] = Field(min_length=1)
    contributing_result_ids: list[ResultId]
    missing_identity_dimensions: list[
        Literal["edition", "accepted_variant", "retake_policy", "route"]
    ]


class DocumentDependency(Base):
    original_name: str
    target_document_id: str | None
    resolution: Literal["linked", "missing", "ambiguous", "scope_unresolved", "cycle"]
    fulfillment_state: Literal["untracked"] = "untracked"

    @model_validator(mode="after")
    def target_matches_resolution(self) -> Self:
        if (self.resolution in {"linked", "cycle"}) != (self.target_document_id is not None):
            raise ValueError("Only exact linked/cyclic dependencies have a target ID")
        return self


class DocumentAction(Base):
    id: str
    result_id: ResultId
    original_item: DocumentItem
    original_items: list[DocumentItem] = Field(min_length=1)
    source_locations: list[ChecklistLocation]
    scope: ScopeProof
    proofs: list[ClaimProof]
    evidence_state: EvidenceState
    fulfillment_state: Literal["untracked"] = "untracked"
    action_state: Literal["requires_review"] = "requires_review"
    dependencies: list[DocumentDependency]
    unresolved_reasons: list[ReasonCode]


class ProgrammeProjection(Base):
    result_id: ResultId
    run_id: str | None
    user_decision: UserDecision
    university: str | None
    programme: str | None
    requested_scope: RequestedScope | None
    research_access: bool
    evidence_state: EvidenceState
    projection_state: ProjectionState
    requirement_ids: list[str]
    document_action_ids: list[str]
    unprojected_checks: list[RequirementCheck]
    unresolved_questions: list[UnresolvedQuestion]
    unresolved_reasons: list[ReasonCode]
    notice: str

    @model_validator(mode="after")
    def locked_selection_receipt(self) -> Self:
        if (
            not self.research_access
            or self.evidence_state == "locked"
            or self.projection_state == "locked"
        ):
            if (
                self.research_access
                or self.evidence_state != "locked"
                or self.projection_state != "locked"
            ):
                raise ValueError("Locked entitlement and projection states must remain consistent")
            if (
                self.run_id is not None
                or self.university is not None
                or self.programme is not None
                or self.requested_scope is not None
                or self.requirement_ids
                or self.document_action_ids
                or self.unprojected_checks
                or self.unresolved_questions
            ):
                raise ValueError("Locked programme cannot expose a source payload or run identity")
            if self.unresolved_reasons != ["research_locked"] or self.notice != LOCKED_NOTICE:
                raise ValueError(
                    "Locked programme must use only the fixed public reason and notice"
                )
        return self


class ProgrammeSourceManifest(Base):
    result_id: ResultId
    run_id: str | None
    result_snapshot_digest: Digest | None
    authoritative_evidence_digest: Digest | None
    resolved_claim_ids: list[str]


class PreparationGraph(Base):
    schema_version: Literal["preparation-graph-v1"] = "preparation-graph-v1"
    profile_id: str
    requested_result_ids: list[ResultId] = Field(min_length=1, max_length=20)
    selected_result_ids: list[ResultId] = Field(min_length=1, max_length=20)
    selection_source: Literal["server_verified_owned_explicit"] = "server_verified_owned_explicit"
    programmes: list[ProgrammeProjection]
    requirements: list[RequirementAtom]
    policy_groups: list[PolicyGroup]
    exam_workstreams: list[ExamWorkstream]
    document_actions: list[DocumentAction]
    source_manifest: list[ProgrammeSourceManifest]
    source_fingerprint: Digest
    evidence_state: EvidenceState
    projection_state: ProjectionState
    notice: str

    @model_validator(mode="after")
    def graph_links(self) -> Self:
        ids = [programme.result_id for programme in self.programmes]
        if ids != self.selected_result_ids or ids != self.requested_result_ids:
            raise ValueError("Projection must retain the complete explicit owned selection order")
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate programmes are forbidden")
        if [entry.result_id for entry in self.source_manifest] != ids:
            raise ValueError("Manifest must cover the same ordered programme selection")
        requirements = {atom.id: atom for atom in self.requirements}
        documents = {item.id: item for item in self.document_actions}
        if len(requirements) != len(self.requirements) or len(documents) != len(
            self.document_actions
        ):
            raise ValueError("Duplicate requirement/document IDs are forbidden")
        for programme in self.programmes:
            if programme.user_decision not in {UserDecision.APPROVED, UserDecision.MAYBE}:
                raise ValueError("Only explicit approved/maybe results belong in G1")
            if any(
                requirements[key].result_id != programme.result_id
                for key in programme.requirement_ids
                if key in requirements
            ):
                raise ValueError("A programme cannot borrow another programme's requirement")
            if any(key not in requirements for key in programme.requirement_ids):
                raise ValueError("Requirement link is missing")
            if any(
                proof.scope.requested != programme.requested_scope
                for key in programme.requirement_ids
                for proof in requirements[key].proofs
            ):
                raise ValueError("A requirement proof cannot borrow another requested scope")
            if any(
                key not in documents or documents[key].result_id != programme.result_id
                for key in programme.document_action_ids
            ):
                raise ValueError("Document link is missing or belongs to a different programme")
            if not programme.research_access:
                if (
                    programme.requirement_ids
                    or programme.document_action_ids
                    or programme.unprojected_checks
                ):
                    raise ValueError("Locked evidence must not expose stored checks or documents")
                if (
                    programme.requested_scope is not None
                    or programme.university is not None
                    or programme.programme is not None
                ):
                    raise ValueError(
                        "Locked payload must retain only the permitted selection receipt"
                    )
        referenced_atoms = [
            key for programme in self.programmes for key in programme.requirement_ids
        ]
        referenced_docs = [
            key for programme in self.programmes for key in programme.document_action_ids
        ]
        if sorted(referenced_atoms) != sorted(requirements) or sorted(referenced_docs) != sorted(
            documents
        ):
            raise ValueError("Every node must be referenced by exactly one programme")
        for group in self.policy_groups:
            if any(
                key not in requirements
                or requirements[key].result_id != group.result_id
                or requirements[key].purpose != group.purpose
                or requirements[key].scholarship_id != group.scholarship_id
                for key in group.requirement_ids
            ):
                raise ValueError("Policy group cannot cross programme scope")
            programme = next(
                value for value in self.programmes if value.result_id == group.result_id
            )
            if any(
                proof.scope.requested != programme.requested_scope for proof in group.context_proofs
            ):
                raise ValueError("A policy context cannot borrow another requested scope")
        for stream in self.exam_workstreams:
            if any(
                key not in requirements or requirements[key].family != stream.family
                for key in stream.requirement_ids
            ):
                raise ValueError("Exam group must contain only its observed family")
            contributing = {requirements[key].result_id for key in stream.requirement_ids}
            if stream.contributing_result_ids != [key for key in ids if key in contributing]:
                raise ValueError("Exam group contributors must retain the selected programme order")
        for document in self.document_actions:
            programme = next(
                value for value in self.programmes if value.result_id == document.result_id
            )
            if (
                document.scope.published != document.original_item.scope
                or document.scope.requested != programme.requested_scope
            ):
                raise ValueError("A document cannot rewrite its original or requested scope")
            if any(proof.scope.requested != programme.requested_scope for proof in document.proofs):
                raise ValueError("A document proof cannot borrow another requested scope")
            for dependency in document.dependencies:
                target = dependency.target_document_id
                if target is not None and (
                    target not in documents or documents[target].result_id != document.result_id
                ):
                    raise ValueError("Document dependencies cannot cross programme scope")
        for entry in self.source_manifest:
            programme = next(
                value for value in self.programmes if value.result_id == entry.result_id
            )
            proofs = {
                proof.claim.id
                for atom in self.requirements
                if atom.result_id == entry.result_id
                for proof in atom.proofs
            }
            proofs.update(
                proof.claim.id
                for document in self.document_actions
                if document.result_id == entry.result_id
                for proof in document.proofs
            )
            proofs.update(
                proof.claim.id
                for group in self.policy_groups
                if group.result_id == entry.result_id
                for proof in group.context_proofs
            )
            if entry.resolved_claim_ids != sorted(proofs):
                raise ValueError("Manifest must identify every displayed exact proof")
            if not programme.research_access and (
                entry.run_id is not None
                or entry.result_snapshot_digest is not None
                or entry.authoritative_evidence_digest is not None
                or entry.resolved_claim_ids
            ):
                raise ValueError("Locked manifest cannot disclose evidence digests or proof IDs")
        return self
