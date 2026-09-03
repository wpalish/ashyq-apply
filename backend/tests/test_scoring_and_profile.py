"""Scoring, grade conversion, dedupe, and profile validation."""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.domain.dedupe import dedupe_by, program_key, scholarship_key, university_key
from app.domain.enums import AdmissionsFit, EligibilityStatus, FundingFit
from app.domain.grades import METHODS, available_methods, propose_conversion
from app.domain.scoring import (
    MAX_MISSING_PENALTY,
    admissions_fit_for,
    score_result,
)
from app.domain.validation import validate_profile
from app.schemas.money import Money
from app.schemas.profile import GradeValue
from app.schemas.result import FundingGap, ProgramResult, RankingEntry, RequirementCheck


def result(**kwargs) -> ProgramResult:
    return ProgramResult(**{
        "id": "r", "run_id": "run", "university": "Test University", "university_id": "u",
        "country": "Netherlands", "city": "Delft", "program": "BSc CS", "degree": "bachelor",
        "intake": "fall 2027",
        **kwargs,
    })


class TestAffordabilityRespectsTheStatedCurrency:
    """The ceiling is in the family's currency; the gap is in the target one.

    Comparing them as bare numbers made a 6,000,000 KZT ceiling look infinitely
    generous against a 20,000 USD gap: ratio ~= 0.003, "affordable" at every
    university on the list.
    """

    @staticmethod
    def _result_with_gap(amount: float, currency: str = "USD"):
        return result(
            funding_gap=FundingGap(
                computable=True, gap=Money(amount=amount, currency=currency)
            )
        )

    def test_a_tenge_ceiling_is_converted_before_it_is_compared(self, profile):
        # 2,880,000 KZT is 6,000 USD at the bundled 480 KZT/USD snapshot rate.
        profile.funding.budget_currency = "KZT"
        profile.funding.max_acceptable_gap = 2_880_000
        affordable = self._affordability(self._result_with_gap(6_000), profile)
        assert affordable.raw == pytest.approx(1.0), "equal purchasing power must score as met"

        stretched = self._affordability(self._result_with_gap(24_000), profile)
        assert stretched.raw < 0.5, "four times the ceiling is not affordable"
        assert "KZT" in stretched.explanation and "USD" in stretched.explanation

    def test_a_ceiling_of_zero_is_a_real_ceiling_not_a_missing_one(self, profile):
        profile.funding.budget_currency = "USD"
        profile.funding.max_acceptable_gap = 0
        profile.funding.max_annual_budget = 50_000

        component = self._affordability(self._result_with_gap(10_000), profile)
        assert component.raw == 0.0, "'I can pay nothing' must not fall through to the budget"

    def test_an_unsupported_currency_is_missing_data_not_a_number(self, profile):
        profile.funding.budget_currency = "XTS"
        profile.funding.max_acceptable_gap = 1_000

        component = self._affordability(self._result_with_gap(6_000), profile)
        assert component.data_present is False, "an unknown rate must not become a score"
        assert "XTS" in component.explanation
        assert "guessed" in component.explanation

    @staticmethod
    def _affordability(res, profile):
        score = score_result(res, profile)
        component = next(c for c in score.components if c.name == "Affordability")
        return component


class TestScoreIsExplainable:
    def test_the_score_carries_a_disclaimer_that_it_is_not_a_probability(self, profile):
        score = score_result(result(), profile)
        assert "not a probability" in score.disclaimer

    def test_every_component_names_its_weight_and_its_reason(self, profile):
        score = score_result(result(), profile)
        assert score.components
        for component in score.components:
            assert component.explanation
            assert component.weighted == pytest.approx(component.raw * component.weight, abs=1e-4)

    def test_missing_data_is_penalised_and_the_fields_are_named(self, profile):
        score = score_result(result(), profile)
        assert score.missing_data_penalty > 0
        assert score.missing_fields

    def test_the_penalty_is_capped(self, profile):
        score = score_result(result(), profile)
        assert score.missing_data_penalty <= MAX_MISSING_PENALTY

    def test_user_weights_change_the_result(self, profile):
        rich = result(eligibility=EligibilityStatus.MET,
                      funding_fit=FundingFit.CONFIRMED_OPPORTUNITY,
                      rankings=[RankingEntry(source="QS", year=2026, position="49")])
        baseline = score_result(rich, profile).total
        profile.weights.funding_fit = 3.0
        assert score_result(rich, profile).total > baseline

    def test_an_excluded_country_scores_zero_on_country_preference(self, profile):
        profile.preferences.excluded_countries = ["Netherlands"]
        profile.preferences.preferred_countries = []
        score = score_result(result(), profile)
        country = next(c for c in score.components if c.name == "Country preference")
        assert country.raw == 0.0

    def test_a_score_never_goes_negative(self, profile):
        score = score_result(result(eligibility=EligibilityStatus.GAP), profile)
        assert score.total >= 0.0


class TestAdmissionsFit:
    def test_unverifiable_requirements_give_insufficient_data(self, profile):
        fit, reason = admissions_fit_for(
            result(eligibility=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION), profile
        )
        assert fit is AdmissionsFit.INSUFFICIENT_DATA
        assert "could not be verified" in reason

    def test_an_unmet_requirement_makes_the_option_ambitious(self, profile):
        fit, _ = admissions_fit_for(result(eligibility=EligibilityStatus.GAP), profile)
        assert fit is AdmissionsFit.AMBITIOUS

    #: Scores comfortably above every published minimum. Only the activity
    #: record then separates a stronger fit from a plausible one.
    CLEAR_MARGIN: ClassVar[list[RequirementCheck]] = [
        RequirementCheck(requirement="IELTS overall", published_value=6.0,
                         applicant_value=7.5, status=EligibilityStatus.MET),
        RequirementCheck(requirement="SAT total", published_value=1200,
                         applicant_value=1450, status=EligibilityStatus.MET),
    ]

    def _with_activities(self, profile, count: int, achievements: int):
        from app.schemas.profile import Achievement, Activity

        profile.activities = [
            Activity(name=f"Activity {i}", category="academic", role="lead",
                     hours_per_week=8, weeks_per_year=36, responsibility_level="leader",
                     measurable_outcome="Led a team to a national placing.")
            for i in range(count)
        ]
        profile.achievements = [
            Achievement(name=f"Olympiad {i}", level="national", year=2026)
            for i in range(achievements)
        ]
        return profile

    def test_a_substantive_activity_record_plus_clear_margins_is_a_stronger_fit(self, profile):
        self._with_activities(profile, 3, 2)
        fit, reason = admissions_fit_for(
            result(eligibility=EligibilityStatus.MET, requirement_checks=self.CLEAR_MARGIN),
            profile,
        )
        assert fit is AdmissionsFit.STRONGER_FIT
        assert "competitive selection" in reason

    def test_the_same_margins_with_a_thin_record_stay_plausible(self, profile):
        """Margins alone are not enough; the activity gate is a separate judgement."""
        self._with_activities(profile, 1, 1)
        fit, _ = admissions_fit_for(
            result(eligibility=EligibilityStatus.MET, requirement_checks=self.CLEAR_MARGIN),
            profile,
        )
        assert fit is AdmissionsFit.PLAUSIBLE_FIT

    def test_scores_at_the_minimum_stay_ambitious(self, profile):
        checks = [RequirementCheck(requirement="IELTS overall", published_value=7.0,
                                   applicant_value=7.0, status=EligibilityStatus.MET)]
        fit, _ = admissions_fit_for(
            result(eligibility=EligibilityStatus.MET, requirement_checks=checks), profile
        )
        assert fit is AdmissionsFit.AMBITIOUS

    def test_no_numeric_thresholds_gives_a_plausible_fit_not_a_strong_one(self, profile):
        checks = [RequirementCheck(requirement="Portfolio", published_value=True,
                                   applicant_value=None, status=EligibilityStatus.MET)]
        fit, reason = admissions_fit_for(
            result(eligibility=EligibilityStatus.MET, requirement_checks=checks), profile
        )
        assert fit is AdmissionsFit.PLAUSIBLE_FIT
        assert "no numeric published thresholds" in reason

    def test_no_fit_verdict_is_ever_a_percentage(self):
        assert set(AdmissionsFit) == {
            AdmissionsFit.STRONGER_FIT, AdmissionsFit.PLAUSIBLE_FIT,
            AdmissionsFit.AMBITIOUS, AdmissionsFit.INSUFFICIENT_DATA,
        }


class TestGradeConversion:
    def test_a_converted_value_without_a_documented_method_is_rejected(self):
        with pytest.raises(ValueError, match="silent grade conversion"):
            GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point",
                       converted_value=3.9)

    def test_a_proposed_conversion_carries_its_method_and_its_caveat(self):
        original = GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point")
        converted = propose_conversion(original, "kz5_to_us4_linear")
        assert converted.converted_value == pytest.approx(3.8, abs=0.01)
        assert "kz5_to_us4_linear" in converted.method
        assert "not a credential evaluation" in converted.method_source

    def test_conversion_does_not_mutate_the_original(self):
        original = GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point")
        propose_conversion(original, "kz5_to_us4_linear")
        assert original.converted_value is None

    def test_an_unknown_method_raises(self):
        original = GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point")
        with pytest.raises(ValueError, match="Unknown conversion method"):
            propose_conversion(original, "made_up")

    def test_every_method_documents_a_caveat(self):
        assert all(m.caveat and m.source for m in METHODS.values())

    def test_methods_are_offered_for_a_5_point_scale(self):
        assert any(m.key == "kz5_to_us4_linear" for m in available_methods("KZ 5-point"))

    def test_a_grade_above_its_own_scale_is_rejected(self):
        with pytest.raises(ValueError, match="exceeds"):
            GradeValue(raw_value=6.0, raw_scale_max=5.0, raw_scale_label="KZ 5-point")


class TestDedupe:
    def test_two_spellings_of_one_university_produce_one_key(self):
        assert university_key("The University of Melbourne", "Australia") == \
               university_key("Univ. of Melbourne", "australia")

    def test_different_universities_keep_different_keys(self):
        assert university_key("University of Toronto", "Canada") != \
               university_key("York University", "Canada")

    def test_the_same_name_in_two_countries_stays_distinct(self):
        assert university_key("Trinity College", "Ireland") != \
               university_key("Trinity College", "United States")

    def test_a_programme_key_includes_degree_and_intake(self):
        a = program_key("X University", "Computer Science", "bachelor", "fall 2027", "NL")
        b = program_key("X University", "Computer Science", "master", "fall 2027", "NL")
        assert a != b

    def test_award_keys_ignore_the_word_scholarship(self):
        assert scholarship_key("X", "Talent Grant", "NL") == \
               scholarship_key("X", "Talent Grant Scholarship", "NL")

    def test_dedupe_keeps_the_first_occurrence_in_order(self):
        items = [{"k": "a", "n": 1}, {"k": "b", "n": 2}, {"k": "a", "n": 3}]
        assert [i["n"] for i in dedupe_by(items, lambda i: i["k"])] == [1, 2]


class TestProfileValidation:
    def test_a_complete_profile_can_proceed(self, profile):
        report = validate_profile(profile)
        assert report.can_proceed

    def test_no_field_of_study_blocks_research(self, profile):
        profile.context.intended_fields = []
        report = validate_profile(profile)
        assert not report.can_proceed
        assert report.blocking_count == 1

    def test_every_gap_states_a_concrete_consequence(self, profile):
        profile.academics.ielts.overall = None
        for gap in validate_profile(profile).gaps:
            assert len(gap.impact) > 40, f"{gap.field_path} has no real explanation"

    def test_a_non_four_point_gpa_scale_is_flagged_as_undecidable(self, profile):
        paths = [g.field_path for g in validate_profile(profile).gaps]
        assert "academics.gpa.converted_value" in paths

    def test_missing_ielts_subscores_are_called_out_separately(self, profile):
        profile.academics.ielts.writing = None
        paths = [g.field_path for g in validate_profile(profile).gaps]
        assert "academics.ielts subscores" in paths

    def test_a_country_cannot_be_both_preferred_and_excluded(self, profile):
        with pytest.raises(ValueError, match="both preferred and excluded"):
            profile.preferences.__class__(
                preferred_countries=["Canada"], excluded_countries=["canada"]
            )
