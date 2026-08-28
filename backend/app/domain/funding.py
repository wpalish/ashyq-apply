"""Classifying what a scholarship actually pays for.

The single most dangerous failure mode in this product is echoing a
university's marketing language. A page that says "full ride" earns nothing;
only a per-category coverage table drawn from official claims can reach
FULL_RIDE_CONFIRMED, and only when tuition, mandatory fees, housing and meals
(or a living stipend) are each confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.enums import (
    FULL_RIDE_REQUIRED,
    ApplicationMode,
    CostCategory,
    FundingClassification,
    FundingFit,
    ScholarshipType,
)
from app.schemas.result import CoverageBreakdown, Scholarship

#: Marketing phrases that must never, alone, drive a classification.
MARKETING_PHRASES = (
    "full ride",
    "full-ride",
    "fully funded",
    "full scholarship",
    "all expenses paid",
    "covers everything",
    "complete funding",
    "100% funded",
)

#: A grant covering at least this share of total cost, without qualifying as
#: full tuition, is a LARGE_GRANT rather than PARTIAL.
LARGE_GRANT_THRESHOLD = 0.50

#: Living-stipend categories that can substitute for a meal plan.
_LIVING_SUBSTITUTES = (CostCategory.MEALS, CostCategory.PERSONAL)


@dataclass(frozen=True)
class ClassificationResult:
    classification: FundingClassification
    reason: str
    marketing_language_detected: bool = False
    unverified_categories: list[CostCategory] = field(default_factory=list)


def detect_marketing_language(text: str) -> list[str]:
    """Return the marketing phrases present in a page excerpt.

    Used to *flag* a scholarship for a stricter look, never to promote it.
    """
    low = (text or "").lower()
    return [p for p in MARKETING_PHRASES if p in low]


def _coverage_map(coverage: list[CoverageBreakdown]) -> dict[CostCategory, str]:
    out: dict[CostCategory, str] = {}
    for c in coverage:
        # A category asserted twice takes the weaker answer; we never upgrade
        # "unknown" to "yes" because one of two sources was optimistic.
        prev = out.get(c.category)
        out[c.category] = _weaker(prev, c.covered) if prev else c.covered
    return out


_STRENGTH = {"yes": 3, "partial": 2, "no": 1, "unknown": 0}


def _weaker(a: str, b: str) -> str:
    return a if _STRENGTH.get(a, 0) <= _STRENGTH.get(b, 0) else b


def classify(
    scholarship: Scholarship,
    total_cost_amount: float | None = None,
    tuition_amount: float | None = None,
    page_text: str = "",
) -> ClassificationResult:
    """Decide the funding classification from the coverage table alone."""
    marketing = detect_marketing_language(page_text or scholarship.name)

    if scholarship.international_eligible == "no":
        return ClassificationResult(
            FundingClassification.NOT_ELIGIBLE,
            "Official source states the award is not open to international students.",
            bool(marketing),
        )

    cov = _coverage_map(scholarship.coverage)
    if not cov:
        return ClassificationResult(
            FundingClassification.UNKNOWN,
            "No official per-category coverage information was found."
            + (
                f" Page uses promotional wording ({', '.join(marketing)}) but publishes no breakdown."
                if marketing
                else ""
            ),
            bool(marketing),
            list(FULL_RIDE_REQUIRED),
        )

    # Need-based awards whose amount depends on an unfiled assessment cannot be
    # sized at all, whatever the coverage table hints.
    if (
        scholarship.scholarship_type == ScholarshipType.NEED_BASED
        and scholarship.amount is None
        and cov.get(CostCategory.TUITION) != "yes"
    ):
        return ClassificationResult(
            FundingClassification.NEED_BASED_POSSIBLE,
            "Award size depends on a verified financial-need assessment that has not been filed.",
            bool(marketing),
        )

    missing = [c for c in FULL_RIDE_REQUIRED if cov.get(c) != "yes"]

    # A living stipend can stand in for a meal plan when it is confirmed.
    if missing == [CostCategory.MEALS] and any(
        cov.get(sub) == "yes" for sub in _LIVING_SUBSTITUTES
    ):
        missing = []

    if not missing:
        return ClassificationResult(
            FundingClassification.FULL_RIDE_CONFIRMED,
            "Official sources confirm coverage of tuition, mandatory fees, housing and "
            "meals or an equivalent living stipend.",
            bool(marketing),
        )

    tuition_covered = cov.get(CostCategory.TUITION) == "yes"
    if tuition_covered:
        return ClassificationResult(
            FundingClassification.FULL_TUITION,
            "Tuition is confirmed as covered, but "
            + _describe_missing(missing, cov)
            + " — this is full tuition, not a full ride.",
            bool(marketing),
            missing,
        )

    share = _coverage_share(scholarship, total_cost_amount, tuition_amount, cov)
    if share is None:
        return ClassificationResult(
            FundingClassification.UNKNOWN,
            "Coverage is partial but the award amount or the cost of attendance is "
            "not officially published, so the share cannot be computed.",
            bool(marketing),
            missing,
        )
    if share >= LARGE_GRANT_THRESHOLD:
        return ClassificationResult(
            FundingClassification.LARGE_GRANT,
            f"Covers roughly {share:.0%} of published cost of attendance; a substantial "
            "portion of the cost remains.",
            bool(marketing),
            missing,
        )
    return ClassificationResult(
        FundingClassification.PARTIAL,
        f"Covers roughly {share:.0%} of published cost of attendance.",
        bool(marketing),
        missing,
    )


def _describe_missing(missing: list[CostCategory], cov: dict[CostCategory, str]) -> str:
    parts = []
    for c in missing:
        state = cov.get(c, "unknown")
        label = c.value.replace("_", " ")
        parts.append(f"{label} is {'not covered' if state == 'no' else state}")
    return "; ".join(parts)


def _coverage_share(
    scholarship: Scholarship,
    total_cost_amount: float | None,
    tuition_amount: float | None,
    cov: dict[CostCategory, str],
) -> float | None:
    if scholarship.amount_is_percentage_of_tuition is not None and tuition_amount and total_cost_amount:
        return min(
            1.0,
            (scholarship.amount_is_percentage_of_tuition / 100.0 * tuition_amount) / total_cost_amount,
        )
    if scholarship.amount and total_cost_amount:
        return min(1.0, scholarship.amount.amount / total_cost_amount)
    return None


def funding_fit_for(scholarships: list[Scholarship]) -> tuple[FundingFit, FundingClassification, str]:
    """Roll a programme's scholarships up into one funding-fit verdict."""
    if not scholarships:
        return (
            FundingFit.UNKNOWN,
            FundingClassification.UNKNOWN,
            "No scholarship information was found on official sources for this programme.",
        )

    eligible = [s for s in scholarships if s.classification != FundingClassification.NOT_ELIGIBLE]
    if not eligible:
        return (
            FundingFit.NOT_ELIGIBLE,
            FundingClassification.NOT_ELIGIBLE,
            "Every scholarship found for this programme officially excludes this applicant.",
        )

    order = [
        FundingClassification.FULL_RIDE_CONFIRMED,
        FundingClassification.FULL_TUITION,
        FundingClassification.LARGE_GRANT,
        FundingClassification.PARTIAL,
        FundingClassification.NEED_BASED_POSSIBLE,
        FundingClassification.UNKNOWN,
    ]
    best = min(eligible, key=lambda s: order.index(s.classification))

    if best.classification == FundingClassification.UNKNOWN:
        return (
            FundingFit.UNKNOWN,
            FundingClassification.UNKNOWN,
            "Scholarships exist but official coverage detail is insufficient to classify them.",
        )
    if best.classification == FundingClassification.NEED_BASED_POSSIBLE:
        return (
            FundingFit.LIMITED_OPPORTUNITY,
            best.classification,
            "Support depends on a financial-need assessment that cannot be evaluated in advance.",
        )

    # "Confirmed" describes the opportunity to apply, never the outcome.
    if best.application_mode == ApplicationMode.AUTOMATIC and best.classification in {
        FundingClassification.FULL_RIDE_CONFIRMED,
        FundingClassification.FULL_TUITION,
    }:
        return (
            FundingFit.CONFIRMED_OPPORTUNITY,
            best.classification,
            f"'{best.name}' is awarded automatically on the admission application against "
            "published criteria; the award decision still depends on the university.",
        )
    if best.application_mode == ApplicationMode.NOMINATION:
        return (
            FundingFit.COMPETITIVE_OPPORTUNITY,
            best.classification,
            f"'{best.name}' requires a departmental nomination, so it cannot be applied for directly.",
        )
    if best.classification in {
        FundingClassification.FULL_RIDE_CONFIRMED,
        FundingClassification.FULL_TUITION,
        FundingClassification.LARGE_GRANT,
    }:
        return (
            FundingFit.COMPETITIVE_OPPORTUNITY,
            best.classification,
            f"'{best.name}' is open to this applicant by published criteria and is awarded "
            "by competitive selection.",
        )
    return (
        FundingFit.LIMITED_OPPORTUNITY,
        best.classification,
        f"The strongest confirmed option, '{best.name}', covers only a limited share of cost.",
    )
