"""Funding classification: the product's highest-stakes judgement.

A page that says "full ride" earns nothing. Only a per-category coverage table
drawn from official claims can reach FULL_RIDE_CONFIRMED.
"""

from __future__ import annotations

import pytest

from app.domain.enums import ApplicationMode, FundingClassification, FundingFit, ScholarshipType
from app.domain.funding import (
    LARGE_GRANT_THRESHOLD,
    classify,
    detect_marketing_language,
    funding_fit_for,
)
from app.schemas.money import Money
from app.schemas.result import CoverageBreakdown, Scholarship


def award(coverage: dict[str, str] | None = None, **kwargs) -> Scholarship:
    return Scholarship(
        id="s1",
        name=kwargs.pop("name", "Test Award"),
        coverage=[CoverageBreakdown(category=k, covered=v) for k, v in (coverage or {}).items()],
        **kwargs,
    )


class TestFullRideDiscipline:
    def test_all_four_core_categories_confirmed_reaches_full_ride(self):
        result = classify(
            award({"tuition": "yes", "mandatory_fees": "yes", "housing": "yes", "meals": "yes"})
        )
        assert result.classification is FundingClassification.FULL_RIDE_CONFIRMED

    def test_tuition_and_fees_only_is_full_tuition(self):
        result = classify(
            award({"tuition": "yes", "mandatory_fees": "yes", "housing": "no", "meals": "no"})
        )
        assert result.classification is FundingClassification.FULL_TUITION
        assert "not a full ride" in result.reason

    @pytest.mark.parametrize(
        "phrase",
        [
            "a full ride to our degree",
            "this is a fully funded scholarship",
            "covers everything you need",
            "100% funded for international students",
        ],
    )
    def test_marketing_language_never_upgrades_a_classification(self, phrase):
        result = classify(
            award({"tuition": "yes", "mandatory_fees": "yes", "housing": "no", "meals": "no"}),
            page_text=phrase,
        )
        assert result.classification is FundingClassification.FULL_TUITION
        assert result.marketing_language_detected is True

    def test_marketing_language_without_a_coverage_table_stays_unknown(self):
        result = classify(award(None), page_text="Our most generous full ride award!")
        assert result.classification is FundingClassification.UNKNOWN
        assert result.marketing_language_detected is True
        assert "publishes no breakdown" in result.reason

    def test_a_confirmed_living_stipend_substitutes_for_a_meal_plan(self):
        result = classify(
            award({"tuition": "yes", "mandatory_fees": "yes", "housing": "yes", "personal": "yes"})
        )
        assert result.classification is FundingClassification.FULL_RIDE_CONFIRMED

    def test_an_unknown_category_does_not_count_as_covered(self):
        result = classify(
            award({"tuition": "yes", "mandatory_fees": "yes", "housing": "yes", "meals": "unknown"})
        )
        assert result.classification is FundingClassification.FULL_TUITION

    def test_the_weaker_of_two_assertions_about_one_category_wins(self):
        s = award()
        s.coverage = [
            CoverageBreakdown(category="tuition", covered="yes"),
            CoverageBreakdown(category="tuition", covered="partial"),
            CoverageBreakdown(category="mandatory_fees", covered="yes"),
            CoverageBreakdown(category="housing", covered="yes"),
            CoverageBreakdown(category="meals", covered="yes"),
        ]
        result = classify(s, total_cost_amount=40000, tuition_amount=30000)
        assert result.classification is not FundingClassification.FULL_RIDE_CONFIRMED


class TestEligibilityAndSizing:
    def test_an_award_closed_to_international_students_is_not_eligible(self):
        result = classify(award({"tuition": "yes"}, international_eligible="no"))
        assert result.classification is FundingClassification.NOT_ELIGIBLE

    def test_unsized_need_based_aid_cannot_be_classified_as_an_amount(self):
        result = classify(
            award({"tuition": "partial"}, scholarship_type=ScholarshipType.NEED_BASED)
        )
        assert result.classification is FundingClassification.NEED_BASED_POSSIBLE

    def test_a_grant_over_the_threshold_is_large_not_partial(self):
        s = award(
            {"tuition": "partial"},
            amount=Money(amount=30_000, currency="USD", academic_year="2026/27"),
        )
        result = classify(s, total_cost_amount=50_000, tuition_amount=35_000)
        assert result.classification is FundingClassification.LARGE_GRANT
        assert LARGE_GRANT_THRESHOLD <= 30_000 / 50_000

    def test_a_small_grant_is_partial(self):
        s = award(
            {"tuition": "partial"},
            amount=Money(amount=5_000, currency="USD", academic_year="2026/27"),
        )
        result = classify(s, total_cost_amount=50_000, tuition_amount=35_000)
        assert result.classification is FundingClassification.PARTIAL

    def test_a_partial_award_with_no_published_amount_is_unknown_not_partial(self):
        result = classify(award({"tuition": "partial"}), total_cost_amount=50_000)
        assert result.classification is FundingClassification.UNKNOWN


class TestFundingFitRollup:
    def test_no_scholarships_means_unknown_not_none(self):
        fit, classification, reason = funding_fit_for([])
        assert fit is FundingFit.UNKNOWN
        assert classification is FundingClassification.UNKNOWN
        assert "No scholarship information" in reason

    def test_every_award_ineligible_rolls_up_to_not_eligible(self):
        fit, _, _ = funding_fit_for([award(classification=FundingClassification.NOT_ELIGIBLE)])
        assert fit is FundingFit.NOT_ELIGIBLE

    def test_an_automatic_full_tuition_award_is_a_confirmed_opportunity(self):
        fit, _, reason = funding_fit_for(
            [
                award(
                    classification=FundingClassification.FULL_TUITION,
                    application_mode=ApplicationMode.AUTOMATIC,
                )
            ]
        )
        assert fit is FundingFit.CONFIRMED_OPPORTUNITY
        # "Confirmed" must describe the chance to apply, never the outcome.
        assert "still depends on the university" in reason

    def test_a_nomination_only_award_is_competitive_not_confirmed(self):
        fit, _, reason = funding_fit_for(
            [
                award(
                    classification=FundingClassification.FULL_RIDE_CONFIRMED,
                    application_mode=ApplicationMode.NOMINATION,
                )
            ]
        )
        assert fit is FundingFit.COMPETITIVE_OPPORTUNITY
        assert "nomination" in reason

    def test_the_best_eligible_award_drives_the_rollup(self):
        _, classification, _ = funding_fit_for(
            [
                award(classification=FundingClassification.PARTIAL),
                award(
                    classification=FundingClassification.FULL_RIDE_CONFIRMED,
                    application_mode=ApplicationMode.AUTOMATIC,
                ),
                award(classification=FundingClassification.NOT_ELIGIBLE),
            ]
        )
        assert classification is FundingClassification.FULL_RIDE_CONFIRMED


def test_marketing_phrase_detection_is_case_insensitive():
    assert detect_marketing_language("A FULL RIDE Scholarship") == ["full ride"]
    assert detect_marketing_language("nothing promotional here") == []
