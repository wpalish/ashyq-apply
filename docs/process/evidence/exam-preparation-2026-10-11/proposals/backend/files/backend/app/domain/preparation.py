"""Read-only evidence projection. Never re-evaluates admission or fabricates a score goal."""

from __future__ import annotations

from app.domain.claim_scope import RequestedScope, Verdict
from app.domain.enums import (
    DISCOVERY_ONLY_SPECIFICITY,
    ClaimStatus,
    ClaimType,
    EligibilityStatus,
)
from app.schemas.claim import ClaimOut, Conflict
from app.schemas.preparation import EvidenceState, Policy, PreparationCheck
from app.schemas.result import RequirementCheck

EXAM_CLAIM_TYPES = frozenset(
    {
        ClaimType.SAT_POLICY,
        ClaimType.SAT_MIN_TOTAL,
        ClaimType.SUPERSCORE_POLICY,
        ClaimType.IELTS_MIN_OVERALL,
        ClaimType.IELTS_MIN_SUBSCORE,
        ClaimType.IELTS_ACCEPTED_TYPES,
        ClaimType.TOEFL_MIN_TOTAL,
        ClaimType.DUOLINGO_MIN,
        ClaimType.TEST_VALIDITY_MONTHS,
        ClaimType.ENTRANCE_EXAM_REQUIRED,
        ClaimType.ENGLISH_TEST_WAIVER,
        ClaimType.OTHER_LANGUAGE_MINIMUM,
        ClaimType.ENGLISH_EVIDENCE_MINIMUM,
        ClaimType.SCHOLARSHIP_MIN_TEST_SCORE,
    }
)
_ENGLISH_TYPES = frozenset(
    {
        ClaimType.IELTS_MIN_OVERALL,
        ClaimType.IELTS_MIN_SUBSCORE,
        ClaimType.IELTS_ACCEPTED_TYPES,
        ClaimType.TOEFL_MIN_TOTAL,
        ClaimType.DUOLINGO_MIN,
        ClaimType.ENGLISH_TEST_WAIVER,
        ClaimType.ENGLISH_EVIDENCE_MINIMUM,
    }
)
_MINIMUM_TYPES = frozenset(
    {
        ClaimType.IELTS_MIN_OVERALL,
        ClaimType.IELTS_MIN_SUBSCORE,
        ClaimType.SAT_MIN_TOTAL,
        ClaimType.TOEFL_MIN_TOTAL,
        ClaimType.DUOLINGO_MIN,
        ClaimType.OTHER_LANGUAGE_MINIMUM,
        ClaimType.SCHOLARSHIP_MIN_TEST_SCORE,
    }
)
NOTICE = (
    "Stored requirement checks are quoted snapshots, not new admission decisions. Unknown "
    "scope, alternatives, waivers, test editions and missing components require confirmation. "
    "Starter links practise only their named skills; completing them does not satisfy a "
    "published score minimum or predict admission. IELTS overall is not each component. "
    "Programme and scholarship test policies are separate. No official pages are fetched here."
)


def combine_states(states: list[EvidenceState]) -> EvidenceState:
    if not states:
        return "unknown"
    for state in ("conflicted", "stale", "unknown", "locked"):
        if state in states:
            return state
    return "current"


def _claim_state(claim: ClaimOut, requested: RequestedScope) -> EvidenceState:
    if claim.status == ClaimStatus.CONFLICTING:
        return "conflicted"
    if claim.is_stale or claim.status in {ClaimStatus.POSSIBLY_STALE, ClaimStatus.SUPERSEDED}:
        return "stale"
    if (
        claim.status != ClaimStatus.VERIFIED_CURRENT
        or not claim.official_domain
        or claim.source_specificity in DISCOVERY_ONLY_SPECIFICITY
        or not claim.source_url.startswith("https://")
        or claim.scope is None
        or claim.scope.covers(requested) is not Verdict.YES
    ):
        return "unknown"
    return "current"


def _policy(check: RequirementCheck, claims: list[ClaimOut], all_claims: list[ClaimOut]) -> Policy:
    types = {claim.claim_type for claim in claims}
    all_types = {claim.claim_type for claim in all_claims}
    if types & _ENGLISH_TYPES:
        if ClaimType.ENGLISH_TEST_WAIVER in all_types:
            return "waiver_check"
        families = sum(
            bool(all_types & family)
            for family in (
                {ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE},
                {ClaimType.TOEFL_MIN_TOTAL},
                {ClaimType.DUOLINGO_MIN},
            )
        )
        if families > 1 or ClaimType.ENGLISH_EVIDENCE_MINIMUM in all_types:
            # Co-published minima do not establish AND/OR or which route applies.
            return "alternatives_unresolved"
    if (
        check.status == EligibilityStatus.NOT_APPLICABLE
        and ClaimType.SAT_POLICY in types
        and any(
            check.published_value == claim.normalized_value
            and isinstance(claim.normalized_value, str)
            and claim.normalized_value.strip().casefold()
            in {"optional", "test-optional", "test optional", "not required"}
            for claim in claims
            if claim.claim_type == ClaimType.SAT_POLICY
        )
    ):
        return "optional"
    if types & _MINIMUM_TYPES and check.status != EligibilityStatus.NOT_APPLICABLE:
        return "required"
    return "unknown"


def _lessons(check: RequirementCheck, claims: list[ClaimOut]) -> list[str]:
    types = {claim.claim_type for claim in claims}
    label = check.requirement.casefold()
    if ClaimType.SAT_MIN_TOTAL in types:
        if label in {"sat math", "sat mathematics"}:
            return ["sat-math-1"]
        if label in {"sat reading and writing", "sat reading/writing", "sat reading_writing"}:
            return ["sat-rw-1"]
        return ["sat-math-1", "sat-rw-1"]
    if ClaimType.IELTS_MIN_OVERALL in types or (
        ClaimType.IELTS_MIN_SUBSCORE in types and label == "ielts reading"
    ):
        return ["ielts-reading-1"]
    return []


def project_checks(
    checks: list[RequirementCheck],
    claims: list[ClaimOut],
    requested: RequestedScope,
    *,
    stale_result: bool = False,
    conflicts: list[Conflict] | None = None,
) -> list[PreparationCheck]:
    rows = []
    for check in checks:
        referenced = [
            claim
            for claim in claims
            if (claim.id in check.claim_ids or claim.source_url in check.claim_ids)
            and claim.claim_type in EXAM_CLAIM_TYPES
        ]
        label = check.requirement.casefold()
        if not referenced and not any(
            word in label
            for word in (
                "ielts",
                "sat ",
                "sat policy",
                "toefl",
                "duolingo",
                "english",
                "language",
                "exam",
            )
        ):
            continue
        matched = {
            reference
            for reference in check.claim_ids
            if any(reference in {claim.id, claim.source_url} for claim in referenced)
        }
        states = [_claim_state(claim, requested) for claim in referenced]
        if not check.claim_ids or matched != set(check.claim_ids):
            states.append("unknown")
        if stale_result:
            states.append("stale")
        types = {claim.claim_type for claim in referenced}
        references = {
            *check.claim_ids,
            *[claim.id for claim in referenced],
            *[claim.source_url for claim in referenced],
        }
        if any(
            conflict.unresolved
            and (references.intersection(conflict.claim_ids) or conflict.claim_type in types)
            for conflict in conflicts or []
        ):
            states.append("conflicted")
        state = combine_states(states)
        policy = _policy(check, referenced, claims) if state == "current" else "unknown"
        # A waiver is a condition to check, never a verified waived state here.
        if state == "current" and policy in {"waiver_check", "alternatives_unresolved"}:
            lesson_ids = []
        else:
            lesson_ids = _lessons(check, referenced) if state == "current" else []
        rows.append(
            PreparationCheck(
                requirement_check=check,
                evidence_state=state,
                policy=policy,
                claims=referenced,
                claim_ids=list(check.claim_ids),
                source_urls=sorted({claim.source_url for claim in referenced}),
                lesson_ids=lesson_ids,
            )
        )
    return rows
