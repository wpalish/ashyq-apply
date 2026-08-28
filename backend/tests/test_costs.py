"""The funding gap, and the cases where it must refuse to compute.

A zero remaining cost is the most consequential number this product can show.
These tests exist mostly to prove it is not shown when it would be misleading.
"""

from __future__ import annotations

from app.domain.costs import compute_funding_gap, total_cost
from app.domain.currency import UnsupportedCurrency, convert, rate
from app.domain.enums import FundingClassification
from app.schemas.money import Money
from app.schemas.result import CostBreakdown, CoverageBreakdown, Scholarship

YEAR = "2026/27"


def costs(**items) -> CostBreakdown:
    return CostBreakdown(
        items={k: Money(amount=v, currency="USD", academic_year=YEAR) for k, v in items.items()},
        academic_year=YEAR,
    )


def award(amount: float, currency="USD", year=YEAR, **kwargs) -> Scholarship:
    return Scholarship(
        id="a", name=kwargs.pop("name", "Award"),
        amount=Money(amount=amount, currency=currency, academic_year=year),
        classification=kwargs.pop("classification", FundingClassification.FULL_TUITION),
        **kwargs,
    )


class TestArithmetic:
    def test_gap_is_cost_minus_aid(self):
        gap = compute_funding_gap(costs(tuition=40000, housing=12000), [award(40000)])
        assert gap.computable
        assert gap.gap.amount == 12000

    def test_a_published_total_is_converted_to_the_target_currency(self):
        """A CAD total netted against a USD award would be off by ~35%."""
        breakdown = CostBreakdown(
            total=Money(amount=69_200, currency="CAD", academic_year=YEAR), academic_year=YEAR
        )
        total = total_cost(breakdown, "USD")
        assert total.currency == "USD"
        assert 50_000 < total.amount < 52_000

    def test_a_published_total_wins_over_a_reconstructed_sum(self):
        breakdown = costs(tuition=40000, housing=12000)
        breakdown.total = Money(amount=59_000, currency="USD", academic_year=YEAR)
        assert total_cost(breakdown, "USD").amount == 59_000

    def test_aid_exceeding_cost_reports_zero_and_says_so(self):
        gap = compute_funding_gap(costs(tuition=20000), [award(30000)])
        assert gap.gap.amount == 0
        assert any("exceeds the published cost" in w for w in gap.warnings)

    def test_a_percentage_of_tuition_award_is_resolved_against_tuition(self):
        s = Scholarship(id="p", name="Pct", amount_is_percentage_of_tuition=100.0,
                        classification=FundingClassification.FULL_TUITION)
        gap = compute_funding_gap(costs(tuition=15000, housing=8000), [s])
        assert gap.computable
        assert gap.gap.amount == 8000


class TestRefusals:
    def test_cost_components_from_different_years_are_not_summed(self):
        mixed = CostBreakdown(items={
            "tuition": Money(amount=40000, currency="USD", academic_year="2026/27"),
            "housing": Money(amount=12000, currency="USD", academic_year="2024/25"),
        })
        gap = compute_funding_gap(mixed, [award(40000)])
        assert not gap.computable
        assert gap.year_mismatch
        assert "different academic years" in gap.reason

    def test_a_cross_year_zero_is_refused(self):
        """The arithmetic reaches zero, but the figures describe different years."""
        full_ride = Scholarship(
            id="fr", name="Full Ride",
            classification=FundingClassification.FULL_RIDE_CONFIRMED,
            amount=Money(amount=90_000, currency="USD", academic_year="2024/25"),
            coverage=[CoverageBreakdown(category=c, covered="yes")
                      for c in ("tuition", "mandatory_fees", "housing", "meals")],
        )
        gap = compute_funding_gap(
            costs(tuition=40000, mandatory_fees=2000, housing=12000, meals=6000), [full_ride]
        )
        assert not gap.computable
        assert gap.year_mismatch
        assert "would be misleading" in gap.reason

    def test_a_full_ride_missing_a_published_category_is_flagged(self):
        partial_ride = Scholarship(
            id="fr", name="Full Ride",
            classification=FundingClassification.FULL_RIDE_CONFIRMED,
            amount=Money(amount=100_000, currency="USD", academic_year=YEAR),
            coverage=[CoverageBreakdown(category=c, covered="yes")
                      for c in ("tuition", "mandatory_fees", "housing")],
        )
        gap = compute_funding_gap(
            costs(tuition=40000, mandatory_fees=2000, housing=12000, meals=6000), [partial_ride]
        )
        assert gap.category_mismatch
        assert not gap.computable

    def test_a_confirmed_living_stipend_satisfies_the_meals_category(self):
        """The gap check must agree with the classifier about the same award."""
        stipend_ride = Scholarship(
            id="fr", name="Full Ride",
            classification=FundingClassification.FULL_RIDE_CONFIRMED,
            amount=Money(amount=100_000, currency="USD", academic_year=YEAR),
            coverage=[CoverageBreakdown(category=c, covered="yes")
                      for c in ("tuition", "mandatory_fees", "housing", "personal")],
        )
        gap = compute_funding_gap(
            costs(tuition=40000, mandatory_fees=2000, housing=12000, meals=6000), [stipend_ride]
        )
        assert not gap.category_mismatch

    def test_no_cost_data_means_no_gap(self):
        gap = compute_funding_gap(CostBreakdown(), [award(40000)])
        assert not gap.computable
        assert "No official cost of attendance" in gap.reason

    def test_an_award_with_no_published_amount_is_excluded_and_named(self):
        unsized = Scholarship(id="u", name="Mystery Grant",
                              classification=FundingClassification.FULL_TUITION)
        gap = compute_funding_gap(costs(tuition=40000), [unsized])
        assert not gap.computable
        assert any("Mystery Grant" in w for w in gap.warnings)

    def test_need_based_aid_is_excluded_from_the_arithmetic(self):
        need = Scholarship(id="n", name="Need Aid",
                           classification=FundingClassification.NEED_BASED_POSSIBLE)
        gap = compute_funding_gap(costs(tuition=40000), [need, award(10000)])
        assert gap.computable
        assert gap.gap.amount == 30000
        assert any("need assessment" in w for w in gap.warnings)


class TestStacking:
    def test_only_awards_that_say_they_stack_are_added(self):
        primary = award(20000, stackable="yes", name="Primary")
        secondary = award(5000, stackable="yes", name="Secondary")
        no_stack = award(3000, stackable="no", name="Solo")
        gap = compute_funding_gap(costs(tuition=40000), [primary, secondary, no_stack])
        assert gap.stackable_aid.amount == 5000

    def test_a_primary_that_forbids_combining_blocks_stacking_entirely(self):
        primary = award(20000, stackable="no", name="Exclusive")
        secondary = award(5000, stackable="yes", name="Add-on")
        gap = compute_funding_gap(costs(tuition=40000), [primary, secondary])
        assert gap.stackable_aid is None
        assert gap.gap.amount == 20000
        assert any("may not be combined" in w for w in gap.warnings)


class TestCurrency:
    def test_conversion_records_its_rate_and_date(self):
        converted = convert(Money(amount=1000, currency="EUR", academic_year=YEAR), "USD")
        assert converted.original_currency == "EUR"
        assert converted.rate > 0
        assert converted.rate_date is not None

    def test_converting_to_the_same_currency_creates_no_conversion_record(self):
        same = convert(Money(amount=5, currency="USD"), "USD")
        assert not hasattr(same, "rate")

    def test_an_unknown_currency_raises_rather_than_guessing(self):
        try:
            rate("USD", "XYZ")
        except UnsupportedCurrency as exc:
            assert "XYZ" in str(exc)
        else:
            raise AssertionError("an unknown currency must not be silently converted")
