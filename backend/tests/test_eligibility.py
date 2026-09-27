"""Eligibility: what may eliminate a university, and what may not.

The asymmetry under test: a confirmed published requirement the applicant
confirms they miss is a hard filter; absent or unverifiable data never is.
"""

from __future__ import annotations

from datetime import date

from app.domain.claim_scope import ClaimScope
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
        outcome = evaluate_program(profile, [C("ielts_accepted_types", ["academic"])], today=TODAY)
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
        outcome = evaluate_program(profile, [C("min_gpa", 3.5), C("gpa_scale", 4.0)], today=TODAY)
        check = next(c for c in outcome.checks if c.requirement == "Minimum GPA")
        assert check.status is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert "No conversion is applied" in check.explanation
        assert outcome.hard_filter_failures == []

    def test_a_matching_scale_is_compared_directly(self, profile):
        outcome = evaluate_program(profile, [C("min_gpa", 4.5), C("gpa_scale", 5.0)], today=TODAY)
        check = next(c for c in outcome.checks if c.requirement == "Minimum GPA")
        assert check.status is EligibilityStatus.MET

    def test_an_accepted_conversion_is_used(self, profile):
        from app.domain.grades import propose_conversion

        profile.academics.gpa = propose_conversion(profile.academics.gpa, "kz5_to_us4_linear")
        outcome = evaluate_program(profile, [C("min_gpa", 3.5), C("gpa_scale", 4.0)], today=TODAY)
        check = next(c for c in outcome.checks if c.requirement == "Minimum GPA")
        assert check.status is EligibilityStatus.MET


class TestSourceHandling:
    def test_the_more_specific_source_decides_a_contradiction(self, profile):
        """The conflict panel says the specific page is preferred; evaluation must agree."""
        profile.academics.ielts.overall = 6.0
        outcome = evaluate_program(
            profile,
            [
                C(
                    "ielts_min_overall",
                    6.0,
                    specificity="university_admissions",
                    status="CONFLICTING",
                ),
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


class TestScopeGovernsWhatMayAnswer:
    """V2-23 — a claim answers the question its page says it is about.

    The benchmark's five wrong-scope claims were all the same shape: a true
    fact, published for another intake or year, stated as the answer here.
    """

    def test_a_claim_for_another_intake_is_not_the_answer(self, profile):
        """The page says 2026; the run asked about fall 2027."""
        outcome = evaluate_program(
            profile,
            [
                C(
                    "admission_deadline",
                    "2026-01-15",
                    intake="fall 2027",
                    scope=ClaimScope(intake="Fall 2026"),
                )
            ],
            today=TODAY,
        )
        assert not any(c.requirement == "Admission deadline" for c in outcome.checks)
        assert outcome.hard_filter_failures == []

    def test_a_page_silent_on_the_intake_may_inform_but_may_not_eliminate(self, profile):
        """Silence is not agreement, and it is not grounds to end an application."""
        outcome = evaluate_program(
            profile,
            [
                C(
                    "admission_deadline",
                    "2026-01-15",
                    intake="fall 2027",
                    scope=ClaimScope(population="international"),
                )
            ],
            today=TODAY,
        )
        deadline = next(c for c in outcome.checks if c.requirement == "Admission deadline")
        assert deadline.status is EligibilityStatus.GAP
        assert deadline.is_hard_filter is False
        assert outcome.hard_filter_failures == []

    def test_a_page_stating_the_requested_intake_still_eliminates(self, profile):
        outcome = evaluate_program(
            profile,
            [
                C(
                    "admission_deadline",
                    "2026-01-15",
                    intake="fall 2027",
                    # The run carries an academic year from the server's
                    # settings. A page that names the requested intake has
                    # answered the question; it is not asked to also restate a
                    # year nobody requested.
                    academic_year="2026/27",
                    scope=ClaimScope(intake="Fall 2027"),
                )
            ],
            today=TODAY,
        )
        assert "Admission deadline" in outcome.hard_filter_failures

    def test_a_page_that_says_who_it_is_for_outranks_one_that_does_not(self, profile):
        """Ahead of specificity: answering the question beats being specific."""
        outcome = evaluate_program(
            profile,
            [
                C(
                    "ielts_min_overall",
                    9.0,
                    intake="fall 2027",
                    specificity="program_intake",
                    scope=ClaimScope(population="international"),
                ),
                C(
                    "ielts_min_overall",
                    6.5,
                    intake="fall 2027",
                    specificity="university_admissions",
                    scope=ClaimScope(intake="fall 2027"),
                ),
            ],
            today=TODAY,
        )
        overall = next(c for c in outcome.checks if c.requirement == "IELTS overall")
        assert overall.published_value == 6.5

    def test_a_claim_written_before_scope_existed_is_judged_exactly_as_before(self, profile):
        """Bug-compatible on purpose: None is a gap in our pipeline, not a fact."""
        outcome = evaluate_program(
            profile,
            [C("admission_deadline", "2026-01-15", intake="fall 2027")],
            today=TODAY,
        )
        assert "Admission deadline" in outcome.hard_filter_failures

    def test_two_intakes_in_one_run_ask_about_neither(self, profile):
        """Nothing coherent was requested, so nothing can be refused for scope."""
        from app.domain.eligibility import requested_scope

        claims = [
            C("admission_deadline", "2026-01-15", intake="fall 2027"),
            C("ielts_min_overall", 6.5, intake="spring 2028"),
        ]
        assert requested_scope(claims).intake is None


class TestARefusalIsCarriedOut:
    """V2-24 — the assessment says which evidence it declined, and why."""

    def test_a_declined_claim_is_reported_with_its_page_and_reason(self, profile):
        outcome = evaluate_program(
            profile,
            [
                C(
                    "admission_deadline",
                    "2026-01-15",
                    intake="fall 2027",
                    url="https://example.edu/2026-deadlines",
                    scope=ClaimScope(intake="Fall 2026"),
                )
            ],
            today=TODAY,
        )
        assert len(outcome.out_of_scope) == 1
        declined = outcome.out_of_scope[0]
        assert declined.source_url == "https://example.edu/2026-deadlines"
        assert "does not apply" in declined.reason
        # Nothing else published a deadline, so the requirement is unanswered.
        assert declined.unanswered is True

    def test_a_requirement_another_page_answered_is_not_left_unanswered(self, profile):
        outcome = evaluate_program(
            profile,
            [
                C(
                    "admission_deadline",
                    "2026-01-15",
                    intake="fall 2027",
                    scope=ClaimScope(intake="Fall 2026"),
                ),
                C(
                    "admission_deadline",
                    "2027-01-15",
                    intake="fall 2027",
                    url="https://example.edu/2027-deadlines",
                    scope=ClaimScope(intake="fall 2027"),
                ),
            ],
            today=TODAY,
        )
        assert [d.unanswered for d in outcome.out_of_scope] == [False]

    def test_nothing_is_reported_when_nothing_was_declined(self, profile):
        outcome = evaluate_program(
            profile,
            [C("ielts_min_overall", 6.5, intake="fall 2027", scope=ClaimScope(intake="fall 2027"))],
            today=TODAY,
        )
        assert outcome.out_of_scope == []


class TestARequirementSaysWhoItIsFor:
    """Plan V2-30 — the visible half of scope.

    Phase 3's question in one line: does this exact rule apply to this exact
    applicant. A number alone cannot answer it; a number with "published for
    international applicants, Fall 2027" beside it can.
    """

    def test_a_scoped_requirement_says_so_in_the_page_s_own_terms(self, profile):
        outcome = evaluate_program(
            profile,
            [
                C(
                    "ielts_min_overall",
                    9.0,
                    intake="fall 2027",
                    scope=ClaimScope(population="international", intake="fall 2027"),
                )
            ],
            today=TODAY,
        )
        check = next(c for c in outcome.checks if c.requirement == "IELTS overall")
        assert check.published_scope == "published for intake fall 2027, population international"

    def test_a_page_that_said_nothing_says_nothing_here(self, profile):
        """Silence is not a phrase to invent; the evidence carries the detail."""
        outcome = evaluate_program(
            profile,
            [C("ielts_min_overall", 9.0, intake="fall 2027", scope=ClaimScope())],
            today=TODAY,
        )
        check = next(c for c in outcome.checks if c.requirement == "IELTS overall")
        assert check.published_scope == ""

    def test_a_claim_predating_scope_says_nothing_rather_than_guessing(self, profile):
        outcome = evaluate_program(
            profile, [C("ielts_min_overall", 9.0, intake="fall 2027")], today=TODAY
        )
        check = next(c for c in outcome.checks if c.requirement == "IELTS overall")
        assert check.published_scope == ""

    def test_a_deadline_carries_its_scope_too(self, profile):
        outcome = evaluate_program(
            profile,
            [
                C(
                    "admission_deadline",
                    "2027-01-15",
                    intake="fall 2027",
                    scope=ClaimScope(intake="fall 2027"),
                )
            ],
            today=TODAY,
        )
        check = next(c for c in outcome.checks if c.requirement == "Admission deadline")
        assert check.published_scope == "published for intake fall 2027"


class TestAPublishedEnglishWaiver:
    """Phase 3 §3 — waiver conditions are their own fact.

    A Kazakhstani applicant from an English-medium school lives or dies by one
    sentence on the page, and the pipeline used to read only *fee* waivers and
    drop this one entirely.
    """

    def test_the_conditions_are_shown_as_the_page_wrote_them(self, profile):
        outcome = evaluate_program(
            profile,
            [
                C(
                    "english_test_waiver",
                    "Applicants schooled in English are exempt from the English language requirement.",
                    intake="fall 2027",
                )
            ],
            today=TODAY,
        )
        check = next(c for c in outcome.checks if c.requirement == "English test waiver")
        assert "schooled in English" in str(check.published_value)
        assert check.status is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION

    def test_a_published_waiver_stops_the_english_minimum_eliminating_anyone(self, profile):
        """Absent data never eliminates, and whether a waiver covers this
        applicant is exactly absent data."""
        with_waiver = evaluate_program(
            profile,
            [
                C("ielts_min_overall", 9.0, intake="fall 2027"),
                C("english_test_waiver", "Exempt if taught in English.", intake="fall 2027"),
            ],
            today=TODAY,
        )
        assert "IELTS overall" not in with_waiver.hard_filter_failures

    def test_without_a_waiver_the_minimum_still_eliminates(self, profile):
        without = evaluate_program(
            profile, [C("ielts_min_overall", 9.0, intake="fall 2027")], today=TODAY
        )
        assert "IELTS overall" in without.hard_filter_failures

    def test_a_page_refusing_waivers_is_not_a_waiver(self, profile):
        """ "No waivers are granted" is recorded with an empty value, and an
        empty value must never disarm anything."""
        outcome = evaluate_program(
            profile,
            [
                C("ielts_min_overall", 9.0, intake="fall 2027"),
                C("english_test_waiver", "", intake="fall 2027"),
            ],
            today=TODAY,
        )
        assert "IELTS overall" in outcome.hard_filter_failures
        assert not any(c.requirement == "English test waiver" for c in outcome.checks)


class TestTestOptionalIsNotTestIrrelevant:
    """Phase 3 §4 — the trap the guide names outright.

    An applicant reads "test-optional" on the admissions page, skips the SAT,
    and loses the scholarship rather than the offer. The two pages are
    published by different offices and neither mentions the other.
    """

    def _claims(self, policy: str):
        return [C("sat_policy", policy, intake="fall 2027")]

    def test_an_award_requiring_a_test_the_programme_made_optional_is_named(self):
        from app.domain.eligibility import awards_needing_a_test_the_programme_made_optional

        clashing = awards_needing_a_test_the_programme_made_optional(
            self._claims("test-optional"),
            [("Merit Award", {"sat": 1400.0}), ("Need Grant", {})],
        )
        assert clashing == ["Merit Award"]

    def test_nothing_is_named_when_the_programme_requires_the_test_anyway(self):
        from app.domain.eligibility import awards_needing_a_test_the_programme_made_optional

        assert (
            awards_needing_a_test_the_programme_made_optional(
                self._claims("SAT required for all applicants"),
                [("Merit Award", {"sat": 1400.0})],
            )
            == []
        )

    def test_nothing_is_named_when_no_award_asks_for_the_test(self):
        from app.domain.eligibility import awards_needing_a_test_the_programme_made_optional

        assert (
            awards_needing_a_test_the_programme_made_optional(
                self._claims("test-blind"), [("Merit Award", {"ielts": 7.0})]
            )
            == []
        )

    def test_a_programme_with_no_published_policy_names_nothing(self):
        """Silence about a policy is not a test-optional policy."""
        from app.domain.eligibility import awards_needing_a_test_the_programme_made_optional

        assert (
            awards_needing_a_test_the_programme_made_optional(
                [], [("Merit Award", {"sat": 1400.0})]
            )
            == []
        )
