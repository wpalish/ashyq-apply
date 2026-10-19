"""Scholarships and the funding outcome from the verified knowledge base (kb mode).

The KB's scholarship facts are already claims on the row
(``app.knowledge.claims.answer``). This module turns them into the same
``Scholarship`` objects the live award reader builds, so the funding stage's
eligibility checks, classification and the assessment's funding fit run
unchanged. Nothing is read beyond the claims: the KB holds no award amount,
coverage table, deadline or restriction, so those stay unknown, and the
classification of a KB award is therefore UNKNOWN or NOT_ELIGIBLE, never more.

A stale claim (``POSSIBLY_STALE``) still names its award, but it settles
nothing about the current cycle: it is not used for eligibility, and the
applicant gets a question to confirm the award is still offered.
"""

from __future__ import annotations

from app.adapters.applicability import assess_degree_applicability
from app.domain.enums import ClaimStatus, ClaimType, FundingClassification, FundingFit
from app.schemas.claim import ClaimOut, UnresolvedQuestion
from app.schemas.result import ProgramResult, Scholarship, Tristate

_AWARD_TYPES = (ClaimType.SCHOLARSHIP_EXISTS, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE)
_STALE_MARK = "Stale, not current: "


def _stale_reason(claim: ClaimOut) -> str:
    notes = claim.notes or ""
    index = notes.find(_STALE_MARK)
    return notes[index + len(_STALE_MARK) :].rstrip(".") if index >= 0 else "stale"


def _tristate(values: set[object]) -> Tristate:
    if values == {True}:
        return "yes"
    if values == {False}:
        return "no"
    return "unknown"


def kb_scholarships(result: ProgramResult) -> tuple[list[Scholarship], list[UnresolvedQuestion]]:
    """One ``Scholarship`` per award the row's KB claims name, and the questions they leave.

    Built as the live reader builds an award section
    (``WebScholarshipAdapter``): the id, name, source pages and evidence; the
    award exists; international eligibility from the award's own statement;
    degree applicability from its quoted text. Everything the KB does not hold
    keeps the model's unknown default.
    """
    groups: dict[str, list[ClaimOut]] = {}
    for claim in result.claims:
        if claim.claim_type in _AWARD_TYPES and claim.subject_key:
            groups.setdefault(claim.subject_key, []).append(claim)

    scholarships: list[Scholarship] = []
    questions: list[UnresolvedQuestion] = []
    for name, claims in groups.items():
        current = [c for c in claims if c.status is ClaimStatus.VERIFIED_CURRENT]
        stale = [c for c in claims if c.status is ClaimStatus.POSSIBLY_STALE]
        sch = Scholarship(
            id=f"{result.university}::{name}"[:200],
            name=name,
            source_urls=sorted({c.source_url for c in claims}),
            claim_ids=[c.id for c in claims],
            last_verified=max(c.accessed_at for c in claims),
        )
        # An official page named the award, whether or not it is current.
        sch.opportunity_exists = True
        exists = {
            c.normalized_value for c in current if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS
        }
        if exists == {False}:
            # The page says the award is withdrawn, as the live reader records it.
            sch.currently_available = "no"
            sch.award_current_for_intake = "no"
        sch.international_eligible = _tristate(
            {
                c.normalized_value
                for c in current
                if c.claim_type is ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE
            }
        )
        quoted = " ".join(c.original_text_excerpt for c in current)
        applicability = assess_degree_applicability(quoted, str(result.degree.value))
        sch.degree_applicability = applicability.verdict
        sch.degree_applicability_reason = applicability.reason
        sch.applies_to_degrees = list(applicability.mentioned_degrees)
        scholarships.append(sch)

        if stale:
            reasons = "; ".join(dict.fromkeys(_stale_reason(c) for c in stale))
            questions.append(
                UnresolvedQuestion(
                    topic="funding",
                    question=(
                        f"Is {name} still offered, and open to international applicants, for "
                        f"the {result.intake} intake?"
                    ),
                    why_it_matters=(
                        f"What the verified knowledge base holds about this award is stale "
                        f"({reasons}), so it is not shown as current and does not count as "
                        "funding until the scholarships office confirms it."
                    ),
                    university=result.university,
                    program=result.program,
                    suggested_contact="scholarships office",
                    blocking=False,
                )
            )
    return scholarships, questions


def no_award_claims(result: ProgramResult) -> list[ClaimOut]:
    """The KB's "no scholarship for this applicant" claims: no award named, value False."""
    return [
        c
        for c in result.claims
        if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS
        and not c.subject_key
        and c.normalized_value is False
    ]


def kb_funding_outcome(
    result: ProgramResult,
) -> tuple[FundingFit, FundingClassification, str] | None:
    """The explicit outcome of a verified "no institutional scholarship" statement.

    None when the row has awards or no such statement: the ordinary
    ``funding_fit_for`` then decides. A current statement is a known absence,
    so no institutional funding is open to the applicant. A stale one leaves
    funding unknown and says so; it is never silence.
    """
    if result.scholarships:
        return None
    claims = no_award_claims(result)
    if not claims:
        return None
    current = [c for c in claims if c.status is ClaimStatus.VERIFIED_CURRENT]
    if current:
        claim = current[0]
        return (
            FundingFit.NOT_ELIGIBLE,
            FundingClassification.NOT_ELIGIBLE,
            f"No institutional scholarship: {result.university} states that it offers none "
            f'for this applicant ("{claim.original_text_excerpt}", {claim.source_url}).',
        )
    claim = claims[0]
    return (
        FundingFit.UNKNOWN,
        FundingClassification.UNKNOWN,
        f"No institutional scholarship was stated by {result.university}, but the statement "
        f"is stale ({_stale_reason(claim)}), so funding is unknown, not confirmed absent.",
    )
