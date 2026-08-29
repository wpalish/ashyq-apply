"""A deadline only eliminates a programme if it belongs to the right intake.

Found on the frozen holdout set. Uppsala publishes "Application deadline 15
January 2026" on its programme pages. Read against a Fall 2027 applicant on
2026-08-29 the date has passed, and the programme was eliminated by a hard
filter — on a deadline belonging to the *2026* intake.

The rule the product states: eliminate only on a confirmed published
requirement the applicant confirms they miss. A previous cycle's deadline is
confirmed and published, and it is not this applicant's requirement.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.domain.eligibility import evaluate_program
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity
from app.schemas.claim import Claim


def deadline_claim(value: str, *, intake: str | None = None) -> Claim:
    return Claim(
        claim_type=ClaimType.ADMISSION_DEADLINE,
        normalized_value=value,
        original_text_excerpt=f"Application deadline {value}",
        source_url="https://uni.edu/programme",
        accessed_at=datetime.now(UTC),
        status=ClaimStatus.VERIFIED_CURRENT,
        source_specificity=SourceSpecificity.PROGRAM_INTAKE,
        intake=intake,
        confidence=0.9,
    )


def deadline_check(profile, value: str, *, today: date, intake: str | None = None):
    outcome = evaluate_program(profile, [deadline_claim(value, intake=intake)], today=today)
    return next(c for c in outcome.checks if c.requirement == "Admission deadline")


class TestAPreviousCyclesDeadlineDoesNotEliminate:
    def test_the_uppsala_case(self, profile):
        """Fall 2027 applicant, a January 2026 deadline, read in August 2026."""
        profile.context.intake_term = "fall"
        profile.context.intake_year = 2027
        check = deadline_check(profile, "2026-01-15", today=date(2026, 8, 29))
        assert not check.is_hard_filter, (
            "a Fall 2027 applicant was eliminated by the 2026 intake's deadline"
        )
        assert check.status.value == "NEEDS_OFFICIAL_CLARIFICATION"
        assert "2027" in check.explanation or "intake" in check.explanation.lower()

    def test_a_deadline_for_this_intake_that_has_passed_still_eliminates(self, profile):
        """The rule must keep working where it was right."""
        profile.context.intake_term = "fall"
        profile.context.intake_year = 2026
        check = deadline_check(profile, "2026-01-15", today=date(2026, 8, 29))
        assert check.is_hard_filter
        assert check.status.value == "GAP"

    def test_a_future_deadline_for_this_intake_is_met(self, profile):
        profile.context.intake_term = "fall"
        profile.context.intake_year = 2027
        check = deadline_check(profile, "2027-01-15", today=date(2026, 8, 29))
        assert not check.is_hard_filter
        assert check.status.value == "MET"

    @pytest.mark.parametrize("deadline,eliminates", [
        ("2026-11-01", True),   # within the year before a Fall 2027 start
        ("2027-01-15", True),   # the usual window
        ("2027-05-01", True),   # late but still this cycle
        ("2026-01-15", False),  # a year early: the previous cycle
        ("2025-01-15", False),  # two years early
    ])
    def test_the_window_is_the_year_or_so_before_the_intake(
        self, profile, deadline, eliminates
    ):
        """Only a deadline that could plausibly belong to this intake counts.

        Read on a date after all of them, so "has it passed" is true throughout
        and the intake scoping is the only thing deciding.
        """
        profile.context.intake_term = "fall"
        profile.context.intake_year = 2027
        check = deadline_check(profile, deadline, today=date(2027, 6, 1))
        assert check.is_hard_filter is eliminates, (
            f"{deadline} for a Fall 2027 intake: hard filter should be {eliminates}"
        )

    def test_the_explanation_says_which_intake_the_deadline_looked_like(self, profile):
        profile.context.intake_term = "fall"
        profile.context.intake_year = 2027
        check = deadline_check(profile, "2026-01-15", today=date(2026, 8, 29))
        assert "2026-01-15" in check.explanation
        assert "Fall 2027" in check.explanation or "2027" in check.explanation
