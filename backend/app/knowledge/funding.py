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

import re
from typing import Any

from app.adapters.applicability import assess_degree_applicability
from app.domain.costs import NO_COST_REASON, NO_COST_WARNING
from app.domain.enums import (
    ClaimStatus,
    ClaimType,
    CostCategory,
    FundingClassification,
    FundingFit,
)
from app.knowledge.claims import PER_UNIT_PERIODS
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


_PER_PERIOD = re.compile(r"Amount per ([^,]+), as published")


def fee_amount_text(value: dict[str, Any]) -> str:
    """ "66,720 USD", or "published range 27,650–34,670 GBP" for a printed range."""
    currency = str(value.get("currency") or "")
    low, high = value.get("range_low"), value.get("range_high")
    if low is not None and high is not None:
        return f"published range {float(low):,.0f}–{float(high):,.0f} {currency}".rstrip()
    return f"{float(value['amount']):,.0f} {currency}".rstrip()


def _fee_line(claim: ClaimOut) -> str | None:
    """One unused tuition claim as "66,720 USD a year, academic year 2026/2027 (why)".

    A per-credit (per-unit) rate says the page printed no yearly figure; it is
    never multiplied out, since the credit load is not ours to guess.
    """
    value = claim.normalized_value
    if not isinstance(value, dict) or value.get("amount") is None:
        return None
    period = _PER_PERIOD.search(claim.notes or "")
    if claim.status is ClaimStatus.POSSIBLY_STALE:
        why = f"not current: {_stale_reason(claim)}"
    elif period and period.group(1).lower() in PER_UNIT_PERIODS:
        why = f"published per {period.group(1)} (no yearly figure printed)"
    elif period:
        why = f"published per {period.group(1)}, not as a yearly figure"
    else:
        return None
    amount = fee_amount_text(value)
    per = f" per {period.group(1)}" if period else " a year"
    year = (
        f", academic year {claim.academic_year}"
        if claim.academic_year
        else ", no academic year stated"
    )
    return f"{amount}{per}{year} ({why})"


#: The gap's refusal in kb mode when the KB holds no fee for the row at all.
KB_NO_FEE_REASON = (
    "The verified knowledge base holds no tuition fee for this programme yet, so the remaining "
    "cost is not computed."
)


def explain_unused_tuition(result: ProgramResult) -> None:
    """Say on the gap that a verified fee exists when it is not this intake's yearly cost.

    The cost table takes only a current, yearly KB fee. Without this, a stale
    2026/27 fee or a per-semester fee left the Costs tab saying no official
    cost was found and the cost pages could not be verified, beside the
    verified fee itself. Where the KB holds no fee at all, the refusal says
    that in kb words (``KB_NO_FEE_REASON``): no cost page was read, so none
    "could not be verified". Only the refusal for an empty cost table is
    reworded; the arithmetic and every other refusal are unchanged.

    A fee the page printed only as a range enters the cost table at its upper
    bound (``app.knowledge.claims.tuition_value``); a warning says so on the
    gap, whatever its outcome, so neither the cost nor a remaining cost reads
    as one printed figure.
    """
    gap = result.funding_gap
    if gap is None:
        return
    tuition = result.costs.items.get(CostCategory.TUITION)
    if tuition is not None and tuition.range_low is not None and tuition.range_high is not None:
        # The cost table took a printed range at its upper bound; say so, so a
        # cost or remaining cost is never read as the page's single figure.
        printed = fee_amount_text(tuition.model_dump()).removeprefix("published range ")
        gap.warnings.append(
            f"Tuition is published only as a range, {printed}; the cost uses its upper "
            "bound, so it is not understated."
        )
    if gap.computable or result.costs.items or gap.reason != NO_COST_REASON:
        return
    fees = [c for c in result.claims if c.claim_type is ClaimType.TUITION]
    if not fees:
        # Edinburgh, Oxford: the KB has no fee. No cost page was read, so the
        # live "cost pages could not be verified" would describe a read that
        # never happened.
        gap.reason = KB_NO_FEE_REASON
        gap.warnings = [w for w in gap.warnings if w != NO_COST_WARNING] + [
            f"Confirm the {result.intake} fee with the university before relying on a cost figure."
        ]
        return
    lines = [line for line in (_fee_line(c) for c in fees) if line]
    if not lines:
        return
    other_year = any(
        c.status is ClaimStatus.POSSIBLY_STALE and "academic year" in _stale_reason(c) for c in fees
    )
    found = (
        f"for another academic year than the {result.intake} intake"
        if other_year
        else f"not as a current yearly figure for the {result.intake} intake"
    )
    gap.reason = (
        f"An official tuition fee was found, but {found}: {'; '.join(lines)}. It is not used "
        "as this intake's cost, so the remaining cost is not computed."
    )
    gap.warnings = [w for w in gap.warnings if w != NO_COST_WARNING] + [
        f"Confirm the {result.intake} fee with the university before relying on a cost figure."
    ]


def no_award_question(
    result: ProgramResult, scholarships: list[Scholarship]
) -> UnresolvedQuestion | None:
    """The open funding question of a KB row that names no award and states no "none".

    In kb mode no scholarship page is read, so the live wording ("no official
    scholarship page could be read") would be false. A row with no KB claims
    at all already carries its blocking "no verified data" question.
    """
    if scholarships or not result.claims or no_award_claims(result):
        return None
    return UnresolvedQuestion(
        topic="funding",
        question=(
            f"Which scholarships does {result.university} offer international students on "
            f"{result.program}?"
        ),
        why_it_matters=(
            "The verified knowledge base names no award for this programme, and live research "
            "is switched off, so no scholarship page was read. Funding is unknown, not "
            "confirmed absent."
        ),
        university=result.university,
        program=result.program,
        suggested_contact="scholarships office",
        blocking=False,
    )


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
