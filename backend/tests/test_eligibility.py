"""Eligibility: what may eliminate a university, and what may not.

The asymmetry under test: a confirmed published requirement the applicant
confirms they miss is a hard filter; absent or unverifiable data never is.
"""

from __future__ import annotations

from datetime import date

from app.domain.eligibility import evaluate_program
from app.domain.enums import EligibilityStatus
from app.schemas.profile import AcademicRecord, SatScore
from tests.conftest import make_claim as C

TODAY = date(2026, 8, 27)


class TestEnglishRequirements:
    def test_a_failed_per_band_minimum_is_a_hard_filter(self, profile):
        """Overall 7.0 clears a 6.5 overall rule; writing 6.0 does not clear 6.5 per band."""
        outcome = evaluate_program(
            profile,
            [C("ielts_min_overall", 6.5), C("ielts_min_subscore", 6.5)],
            today=TODAY,
        )
        assert outcome.status is EligibilityStatus.GAP
        assert "IELTS writing" in outcome.hard_filter_failures

    def test_passing_overall_alone_does_not_pass_the_programme(self, profile):
        outcome = evaluate_program(profile, [C("ielts_min_overall", 6.5)], today=TODAY)
        assert outcome.status is EligibilityStatus.MET

    def test_per_band_minimums_can_differ_by_section(self, profile):
        outcome = evaluate_program(
            profile,
            [C("ielts_min_subscore", {"writing": 5.5, "speaking": 7.0})],
            today=TODAY,
        )
        assert outcome.status is EligibilityStatus.MET

    def test_the_wrong_ielts_type_is_a_hard_filter(self, profile):
        profile.academics.ielts.test_type = "general_training"
        outcome = evaluate_program(
            profile, [C("ielts_accepted_types", ["academic"])], today=TODAY
        )
        assert "Accepted IELTS test type" in outcome.hard_filter_failures

    def test_a_missing_score_is_pending_not_a_gap(self, profile):
        profile.academics = AcademicRecord()
        outcome = evaluate_program(profile, [C("ielts_min_overall", 6.5)], today=TODAY)
        assert outcome.status is EligibilityStatus.PENDING
        assert outcome.hard_filter_failures == []


class TestTestOptional:
    def test_test_optional_never_eliminates_an_applicant_without_a_score(self, profile):
        profile.academics.sat = SatScore()
        outcome = evaluate_program(
            profile,
            [C("ielts_min_overall", 6.5), C("sat_policy", "Test-optional for 2027 entry")],
            today=TODAY,
        )
        assert outcome.status is EligibilityStatus.MET

    def test_a_published_sat_minimum_is_checked_when_the_policy_is_not_optional(self, profile):
        outcome = evaluate_program(profile, [C("sat_min_total", 1500)], today=TODAY)
        assert outcome.status is EligibilityStatus.GAP
        assert "SAT total" in outcome.hard_filter_failures


class TestDeadlines:
    def test_a_past_deadline_is_a_hard_filter(self, profile):
        outcome = evaluate_program(profile, [C("admission_deadline", "2026-01-15")], today=TODAY)
        assert "Admission deadline" in outcome.hard_filter_failures

    def test_a_future_deadline_is_met(self, profile):
        outcome = evaluate_program(profile, [C("admission_deadline", "2027-05-01")], today=TODAY)
        assert outcome.status is EligibilityStatus.MET

    def test_an_unparseable_deadline_asks_for_clarification(self, profile):
        outcome = evaluate_program(profile, [C("admission_deadline", "rolling")], today=TODAY)
        assert outcome.status is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert outcome.hard_filter_failures == []


class TestGpaScales:
    def test_a_mismatched_scale_is_not_silently_converted(self, profile):
        """The applicant is on a 5-point scale; the programme publishes 4.0."""
        outcome = evaluate_program(
            profile, [C("min_gpa", 3.5), C("gpa_scale", 4.0)], today=TODAY
        )
        check = next(c for c in outcome.checks if c.requirement == "Minimum GPA")
        assert check.status is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert "No conversion is applied" in check.explanation
        assert outcome.hard_filter_failures == []

    def test_a_matching_scale_is_compared_directly(self, profile):
        outcome = evaluate_program(
            profile, [C("min_gpa", 4.5), C("gpa_scale", 5.0)], today=TODAY
        )
        check = next(c for c in outcome.checks if c.requirement == "Minimum GPA")
        assert check.status is EligibilityStatus.MET

    def test_an_accepted_conversion_is_used(self, profile):
        from app.domain.grades import propose_conversion

        profile.academics.gpa = propose_conversion(profile.academics.gpa, "kz5_to_us4_linear")
        outcome = evaluate_program(
            profile, [C("min_gpa", 3.5), C("gpa_scale", 4.0)], today=TODAY
        )
        check = next(c for c in outcome.checks if c.requirement == "Minimum GPA")
        assert check.status is EligibilityStatus.MET


class TestSourceHandling:
    def test_the_more_specific_source_decides_a_contradiction(self, profile):
        """The conflict panel says the specific page is preferred; evaluation must agree."""
        profile.academics.ielts.overall = 6.0
        outcome = evaluate_program(
            profile,
            [
                C("ielts_min_overall", 6.0, specificity="university_admissions", status="CONFLICTING"),
                C("ielts_min_overall", 6.5, specificity="program_intake", status="CONFLICTING"),
            ],
            today=TODAY,
        )
        check = next(c for c in outcome.checks if c.requirement == "IELTS overall")
        assert check.published_value == 6.5

    def test_an_unverified_claim_never_eliminates_a_university(self, profile):
        """A requirement we could not confirm is a question, not a barrier."""
        outcome = evaluate_program(
            profile,
            [C("ielts_min_overall", 8.5, status="UNVERIFIED", specificity="aggregator")],
            today=TODAY,
        )
        assert outcome.status is EligibilityStatus.GAP
        assert outcome.hard_filter_failures == []

    def test_no_claims_at_all_means_needs_clarification(self, profile):
        outcome = evaluate_program(profile, [], today=TODAY)
        assert outcome.status is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION

    def test_a_closed_intake_is_a_hard_filter(self, profile):
        outcome = evaluate_program(profile, [C("intake_open", False)], today=TODAY)
        assert "Intake accepting applications" in outcome.hard_filter_failures


class TestOtherPrerequisites:
    def test_a_required_portfolio_is_an_action_not_a_disqualification(self, profile):
        outcome = evaluate_program(profile, [C("portfolio_required", True)], today=TODAY)
        assert outcome.status is EligibilityStatus.PENDING
        assert outcome.hard_filter_failures == []

    def test_missing_subject_prerequisites_are_pending_not_gap(self, profile):
        outcome = evaluate_program(
            profile, [C("required_subjects", ["mathematics", "physics"])], today=TODAY
        )
        check = next(c for c in outcome.checks if c.requirement == "Required subjects")
        assert check.status is EligibilityStatus.PENDING
        assert "Add them if they were studied" in check.explanation
