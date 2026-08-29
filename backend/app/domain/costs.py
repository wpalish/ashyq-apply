"""Cost of attendance and the funding gap.

The arithmetic is trivial; the refusals are the point. A gap of zero is only
shown when the cost figure and the award figure describe the same academic
year, the same currency and comparable categories. Otherwise the calculator
reports that it will not compute, and says why.
"""

from __future__ import annotations

from app.domain.currency import FxProvider, FxUnavailable, convert
from app.domain.enums import CostCategory, FundingClassification
from app.schemas.money import Money
from app.schemas.result import CostBreakdown, FundingGap, Scholarship

#: Categories that make up a normal published cost of attendance.
CORE_COST_CATEGORIES = (
    CostCategory.TUITION,
    CostCategory.MANDATORY_FEES,
    CostCategory.HOUSING,
    CostCategory.MEALS,
)


def total_cost(
    breakdown: CostBreakdown, target_currency: str = "USD",
    *, provider: FxProvider | None = None,
) -> Money | None:
    """Sum a cost breakdown, refusing to mix academic years.

    A published ``total`` always wins over a reconstructed sum, because the
    university's own total may include items we did not itemise.
    """
    if breakdown.total is not None:
        # Convert it: a published total is still a Money in the university's own
        # currency, and returning it unconverted would let a CAD total be netted
        # against a USD award.
        try:
            converted = convert(breakdown.total, target_currency, provider=provider)
        except FxUnavailable:
            return None
        return Money(
            amount=converted.amount,
            currency=converted.currency,
            academic_year=breakdown.total.academic_year or breakdown.academic_year,
            is_estimate=breakdown.total.is_estimate,
            range_low=converted.range_low,
            range_high=converted.range_high,
            source_url=breakdown.total.source_url,
        )
    if not breakdown.items:
        return None

    years = {m.academic_year for m in breakdown.items.values() if m.academic_year}
    if len(years) > 1:
        return None  # caller surfaces the mismatch; we do not average years

    total = 0.0
    low = 0.0
    high = 0.0
    is_estimate = False
    for money in breakdown.items.values():
        try:
            conv = convert(money, target_currency, provider=provider)
        except FxUnavailable:
            return None
        total += conv.amount
        low += conv.range_low if conv.range_low is not None else conv.amount
        high += conv.range_high if conv.range_high is not None else conv.amount
        is_estimate = is_estimate or conv.is_estimate

    return Money(
        amount=round(total, 2),
        currency=target_currency.upper(),
        academic_year=next(iter(years), None) or breakdown.academic_year,
        is_estimate=is_estimate,
        range_low=round(low, 2) if low != total else None,
        range_high=round(high, 2) if high != total else None,
    )


def _award_amount(
    s: Scholarship, tuition: Money | None, target_currency: str,
    *, provider: FxProvider | None = None,
) -> Money | None:
    """Resolve an award to a currency amount, including percentage-of-tuition."""
    if s.amount is not None:
        try:
            conv = convert(s.amount, target_currency, provider=provider)
        except FxUnavailable:
            return None
        return Money(
            amount=conv.amount,
            currency=conv.currency,
            academic_year=s.amount.academic_year,
            is_estimate=s.amount.is_estimate,
        )
    if s.amount_is_percentage_of_tuition is not None and tuition is not None:
        try:
            conv_t = convert(tuition, target_currency, provider=provider)
        except FxUnavailable:
            return None
        return Money(
            amount=round(conv_t.amount * s.amount_is_percentage_of_tuition / 100.0, 2),
            currency=target_currency.upper(),
            academic_year=tuition.academic_year,
            is_estimate=True,
        )
    return None


def compute_funding_gap(
    costs: CostBreakdown,
    scholarships: list[Scholarship],
    target_currency: str = "USD",
    *,
    provider: FxProvider | None = None,
) -> FundingGap:
    """estimated_funding_gap = cost of attendance − confirmed aid − stackable aid.

    ``provider`` is the run's own exchange-rate source. It is passed explicitly
    rather than read from process state, so two runs in flight cannot end up
    sharing — or swapping — the rates their gaps were computed against.
    """
    warnings: list[str] = []

    cost = total_cost(costs, target_currency, provider=provider)
    if cost is None:
        years = sorted({m.academic_year for m in costs.items.values() if m.academic_year})
        if len(years) > 1:
            return FundingGap(
                computable=False,
                year_mismatch=True,
                reason=(
                    "Published cost components come from different academic years "
                    f"({', '.join(years)}). They are not summed, because a mixed-year total "
                    "would misstate the real cost."
                ),
                warnings=["Re-check the cost pages for a single academic year."],
            )
        return FundingGap(
            computable=False,
            reason="No official cost of attendance was found for this programme and intake.",
            warnings=["Cost pages could not be verified; the gap cannot be estimated."],
        )

    eligible = [
        s
        for s in scholarships
        if s.classification
        not in {FundingClassification.NOT_ELIGIBLE, FundingClassification.NEED_BASED_POSSIBLE}
    ]
    if any(s.classification == FundingClassification.NEED_BASED_POSSIBLE for s in scholarships):
        warnings.append(
            "A need-based award was found but cannot be sized before a need assessment is filed; "
            "it is excluded from this calculation."
        )

    tuition = costs.items.get(CostCategory.TUITION)
    # The award and its resolved amount travel together, so neither can be set
    # without the other.
    best: tuple[Money, Scholarship] | None = None
    for s in eligible:
        amt = _award_amount(s, tuition, target_currency, provider=provider)
        if amt is None:
            warnings.append(
                f"'{s.name}': no officially published amount, excluded from the arithmetic."
            )
            continue
        if best is None or amt.amount > best[0].amount:
            best = (amt, s)

    if best is None:
        return FundingGap(
            computable=False,
            total_cost=cost,
            reason=(
                "Cost of attendance is known, but no scholarship with an officially published "
                "amount was found, so the remaining cost cannot be estimated."
            ),
            warnings=warnings,
        )

    primary, primary_s = best

    # Stacking needs consent from both sides: the award being added must say it
    # stacks, and the primary award must not forbid being combined.
    stackable_total = 0.0
    others_offering_to_stack = [
        s for s in eligible if s is not primary_s and s.stackable == "yes"
    ]
    if primary_s.stackable == "no":
        if others_offering_to_stack:
            warnings.append(
                f"'{primary_s.name}' states it may not be combined with other awards, so other "
                "scholarships are not added on top even where they permit stacking."
            )
    else:
        for s in others_offering_to_stack:
            amt = _award_amount(s, tuition, target_currency, provider=provider)
            if amt is not None:
                stackable_total += amt.amount

    year_mismatch = bool(
        cost.academic_year and primary.academic_year and cost.academic_year != primary.academic_year
    )
    if year_mismatch:
        warnings.append(
            f"Cost is published for {cost.academic_year} but the award amount for "
            f"{primary.academic_year}. The figures below are not directly comparable."
        )

    # A "full ride" whose coverage list omits categories present in the cost
    # table is a category mismatch, not a zero gap.
    category_mismatch = False
    if primary_s.classification == FundingClassification.FULL_RIDE_CONFIRMED:
        covered = {c.category for c in primary_s.coverage if c.covered == "yes"}
        # A confirmed living stipend stands in for a meal plan here exactly as it
        # does in the classifier; the two must not disagree about the same award.
        if CostCategory.PERSONAL in covered:
            covered.add(CostCategory.MEALS)
        uncovered_core = [c for c in CORE_COST_CATEGORIES if c in costs.items and c not in covered]
        if uncovered_core:
            category_mismatch = True
            warnings.append(
                "Award coverage does not name every cost category the university publishes: "
                + ", ".join(c.value.replace("_", " ") for c in uncovered_core)
            )

    gap_amount = max(0.0, cost.amount - primary.amount - stackable_total)
    residual_positive = cost.amount - primary.amount - stackable_total

    if gap_amount <= 0 and (year_mismatch or category_mismatch):
        return FundingGap(
            computable=False,
            total_cost=cost,
            confirmed_aid=primary,
            stackable_aid=Money(amount=stackable_total, currency=target_currency.upper())
            if stackable_total
            else None,
            year_mismatch=year_mismatch,
            category_mismatch=category_mismatch,
            reason=(
                "The arithmetic reaches zero, but the cost and coverage figures are not "
                "comparable, so a zero remaining cost would be misleading."
            ),
            warnings=warnings,
        )

    low = high = None
    if cost.range_low is not None and cost.range_high is not None:
        low = max(0.0, cost.range_low - primary.amount - stackable_total)
        high = max(0.0, cost.range_high - primary.amount - stackable_total)
        warnings.append("Cost of attendance is published as a range; the gap is shown as a range.")

    if residual_positive < 0:
        warnings.append(
            "Confirmed aid exceeds the published cost of attendance. The surplus is not "
            "assumed to be paid out; the remaining cost is reported as zero."
        )

    return FundingGap(
        computable=True,
        gap=Money(
            amount=round(gap_amount, 2),
            currency=target_currency.upper(),
            academic_year=cost.academic_year,
            is_estimate=cost.is_estimate or primary.is_estimate,
            range_low=round(low, 2) if low is not None else None,
            range_high=round(high, 2) if high is not None else None,
        ),
        gap_low=round(low, 2) if low is not None else None,
        gap_high=round(high, 2) if high is not None else None,
        total_cost=cost,
        confirmed_aid=primary,
        stackable_aid=Money(amount=round(stackable_total, 2), currency=target_currency.upper())
        if stackable_total
        else None,
        year_mismatch=year_mismatch,
        category_mismatch=category_mismatch,
        reason="Remaining annual cost after officially published, applicable aid.",
        warnings=warnings,
    )
