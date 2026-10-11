"""Retained twelve B7 year-comparability regressions, pure synthetic USD."""

from __future__ import annotations

import pytest


def award(identifier, amount, year="2026/27", stackable="yes"):
    from app.domain.enums import FundingClassification
    from app.schemas.money import Money
    from app.schemas.result import Scholarship

    return Scholarship(
        id=identifier,
        name=identifier,
        classification=FundingClassification.PARTIAL,
        amount=Money(amount=amount, currency="USD", academic_year=year),
        stackable=stackable,
    )


@pytest.mark.parametrize("old_amount", [5000, 8000])
def test_old_year_add_on_cannot_establish_zero_cost(old_amount):
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000, academic_year="2026/27"))
    gap = compute_funding_gap(costs, [award("current", 10000), award("old", old_amount, "2025/26")])
    assert not gap.computable
    assert gap.gap is None
    assert gap.year_mismatch
    assert any("old" in warning and "2025/26" in warning for warning in gap.warnings)


def test_positive_residual_retains_existing_policy_with_comparability_warning():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=20000, academic_year="2026/27"))
    gap = compute_funding_gap(costs, [award("current", 10000), award("old", 5000, "2025/26")])
    assert gap.computable
    assert gap.gap.amount == 5000
    assert gap.year_mismatch
    assert any("old" in warning for warning in gap.warnings)


def test_different_award_years_cannot_establish_zero_when_cost_year_is_unknown():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000))
    gap = compute_funding_gap(costs, [award("current", 10000), award("old", 5000, "2025/26")])
    assert not gap.computable
    assert gap.year_mismatch


def test_percentage_add_on_uses_the_tuition_year():
    from app.domain.costs import compute_funding_gap
    from app.domain.enums import FundingClassification
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown, Scholarship

    costs = CostBreakdown(
        total=Money(amount=15000, academic_year="2026/27"),
        items={"tuition": Money(amount=10000, academic_year="2025/26")},
    )
    percentage = Scholarship(
        id="old-percent",
        name="old-percent",
        classification=FundingClassification.PARTIAL,
        amount_is_percentage_of_tuition=50,
        stackable="yes",
    )
    gap = compute_funding_gap(costs, [award("current", 10000), percentage])
    assert not gap.computable
    assert gap.year_mismatch


def test_same_year_add_on_still_computes_zero():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000, academic_year="2026/27"))
    gap = compute_funding_gap(costs, [award("current", 10000), award("current-add-on", 5000)])
    assert gap.computable
    assert gap.gap.amount == 0
    assert not gap.year_mismatch


def test_primary_forbidding_stacking_does_not_compare_the_unused_old_award():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000, academic_year="2026/27"))
    gap = compute_funding_gap(
        costs, [award("current", 10000, stackable="no"), award("old", 5000, "2025/26")]
    )
    assert gap.computable
    assert gap.gap.amount == 5000
    assert not gap.year_mismatch
    assert gap.stackable_aid is None


def test_unknown_secondary_year_is_not_invented():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000, academic_year="2026/27"))
    gap = compute_funding_gap(costs, [award("current", 10000), award("unknown-year", 5000, None)])
    assert gap.computable
    assert not gap.year_mismatch


@pytest.mark.parametrize("cost_amount", [15000, 14000])
def test_different_known_add_on_years_refuse_zero_with_unknown_cost_and_primary_years(cost_amount):
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=cost_amount))
    gap = compute_funding_gap(
        costs,
        [
            award("unknown-primary", 10000, None),
            award("addon-new", 3000, "2026/27"),
            award("addon-old", 2000, "2025/26"),
        ],
    )
    assert not gap.computable
    assert gap.gap is None
    assert gap.year_mismatch
    assert any("addon-new" in warning and "addon-old" in warning for warning in gap.warnings)


def test_same_known_add_on_years_do_not_invent_a_cost_year():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000))
    gap = compute_funding_gap(
        costs,
        [
            award("unknown-primary", 10000, None),
            award("addon-one", 3000, "2026/27"),
            award("addon-two", 2000, "2026/27"),
        ],
    )
    assert gap.computable
    assert gap.gap.amount == 0
    assert gap.gap.academic_year is None
    assert not gap.year_mismatch


def test_known_and_unknown_add_on_years_do_not_invent_a_mismatch():
    from app.domain.costs import compute_funding_gap
    from app.schemas.money import Money
    from app.schemas.result import CostBreakdown

    costs = CostBreakdown(total=Money(amount=15000))
    gap = compute_funding_gap(
        costs,
        [
            award("unknown-primary", 10000, None),
            award("addon-one", 3000, "2026/27"),
            award("addon-two", 2000, None),
        ],
    )
    assert gap.computable
    assert not gap.year_mismatch
