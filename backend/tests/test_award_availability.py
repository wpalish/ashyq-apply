"""Phase 3 §7 — the availability roll-up, deterministic and honest.

The rule lived inside the scholarship adapter and was neither complete nor
findable: it ignored `opportunity_exists` and `award_current_for_intake`
entirely, so an award a page calls discontinued could still roll up to
available for the intake. Both of those fields were declared and never set.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from unittest.mock import Mock

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageClassification, PageType
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.conflicts import find_conflicts
from app.domain.enums import ClaimStatus, ClaimType, DegreeLevel
from app.domain.funding import roll_up_availability
from app.schemas.claim import Claim
from app.schemas.result import Scholarship


def roll(**over):
    kwargs = {
        "opportunity_exists": True,
        "applicant_eligible": "yes",
        "application_window_open": "yes",
        "award_current_for_intake": "unknown",
    }
    kwargs.update(over)
    return roll_up_availability(**kwargs)


class TestWhatProvesItClosed:
    def test_no_award_page_means_no_award(self):
        assert roll(opportunity_exists=False) == "no"

    def test_a_page_saying_it_is_not_offered_this_cycle_closes_it(self):
        """The case the old roll-up could not see at all."""
        assert roll(award_current_for_intake="no") == "no"

    def test_a_stated_ineligibility_closes_it(self):
        assert roll(applicant_eligible="no") == "no"

    def test_a_passed_deadline_closes_it(self):
        assert roll(application_window_open="no") == "no"


class TestWhatIsEnoughToSayYes:
    def test_a_silent_cycle_does_not_block_a_yes(self):
        """Most pages never state a cycle; demanding one would make every
        award unknown, which is the guide's own reason for `!= no`."""
        assert roll(award_current_for_intake="unknown") == "yes"

    def test_an_explicit_current_cycle_is_also_yes(self):
        assert roll(award_current_for_intake="yes") == "yes"


class TestUnknownPropagates:
    def test_an_unknown_eligibility_is_not_rounded_up(self):
        assert roll(applicant_eligible="unknown") == "unknown"

    def test_an_unfound_deadline_is_not_an_open_window(self):
        assert roll(application_window_open="unknown") == "unknown"

    def test_two_unknowns_stay_unknown(self):
        assert roll(applicant_eligible="unknown", application_window_open="unknown") == "unknown"


class TestReadingItFromAPage:
    def test_withdrawal_language_is_recognised(self):
        from app.adapters.scholarship.web_scholarships import _AWARD_WITHDRAWN

        for line in (
            "This scholarship has been discontinued.",
            "The award is no longer offered.",
            "Applications are suspended for the 2026/27 cycle.",
            "This programme is not being awarded this year.",
        ):
            assert _AWARD_WITHDRAWN.search(line), line

    def test_an_ordinary_award_page_is_not_read_as_withdrawn(self):
        from app.adapters.scholarship.web_scholarships import _AWARD_WITHDRAWN

        for line in (
            "The award is worth 12,000 EUR per year.",
            "Applications close on 15 January 2027.",
            "International students of any nationality are eligible to apply.",
        ):
            assert not _AWARD_WITHDRAWN.search(line), line


def test_a_count_sentence_is_not_evidence_that_the_scheme_runs_now() -> None:
    """The reversal this file records.

    I wrote a positive pattern — "is/are offered", "applications are open" —
    and the demo caught it reading Delft's "30 awards are offered each year"
    as a statement about *this* cycle. There is no positive branch now: the
    roll-up needs only `!= no` from this dimension, so the rule bought nothing
    and could be wrong.
    """
    import app.adapters.scholarship.web_scholarships as module

    assert not hasattr(module, "_AWARD_OFFERED_AGAIN")


def _read_availability_page(*paragraphs: str) -> tuple[Scholarship, list[Claim]]:
    """Exercise the production parser with official, entirely synthetic HTML."""
    name = "Example Scholarship"
    html = (
        f"<html><head><title>{name}</title></head><body><main><h1>{name}</h1>"
        f"<p>{name} is awarded to outstanding freshmen pursuing undergraduate programmes.</p>"
        "<p>Open to all nationalities.</p>"
        + "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        + "</main></body></html>"
    )
    candidate = Candidate("Example University", "Singapore", "Example", "example.edu")
    program = CandidateProgram("Computer Science", "computer science", DegreeLevel.BACHELOR)
    fetcher = Mock(spec=Fetcher)
    award, claims = WebScholarshipAdapter(fetcher, "2026/27")._parse_award(
        candidate,
        program,
        "https://example.edu/scholarships/example",
        html,
        datetime.now(UTC),
        PageClassification(PageType.SCHOLARSHIP_AWARD, 1.0, subject=name),
        0,
    )
    fetcher.get.assert_not_called()
    return award, claims


class TestHolderRevocationIsNotSchemeWithdrawal:
    """NTU's live evidence: a holder can lose an award that is still offered."""

    @pytest.mark.parametrize(
        "holder_condition",
        [
            (
                "The scholarship may be withdrawn at any time if, in the opinion of the "
                "University, the scholarship holder's progress or behaviour is deemed "
                "unsatisfactory."
            ),
            (
                "The Scholarship may be withdrawn at any time if, in the opinion of the "
                "University, the scholarship holder 's progress or behaviour is deemed "
                "unsatisfactory."
            ),
            "The scholarship will be withdrawn if the recipient fails to maintain a CGPA of 3.5.",
            (
                "The scholarship will be withdrawn\n"
                "if the recipient fails to maintain a CGPA of 3.5."
            ),
            "The scholarship has not been withdrawn.",
            "If the scholarship is withdrawn, recipients will be notified by email.",
            "This scholarship has not been discontinued.",
            "Applications for this scholarship are not suspended.",
            "This scholarship is not paused.",
            ("The scholarship is withdrawn if the holder fails to maintain satisfactory progress."),
        ],
    )
    def test_holder_conditions_do_not_remove_the_award_or_invent_a_conflict(
        self, holder_condition: str
    ) -> None:
        award, claims = _read_availability_page(holder_condition)

        assert award.opportunity_exists is True
        assert award.currently_available == "unknown"
        assert award.award_current_for_intake == "unknown"
        # No deadline was read, so this remains an open question rather than
        # becoming a false refusal or a fabricated open application window.
        assert award.application_window_open == "unknown"
        assert award.available_this_intake == "unknown"
        conflicts, updated = find_conflicts(claims)
        assert conflicts == []
        existence = [c for c in updated if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS]
        assert len(existence) == 1
        assert existence[0].normalized_value == award.name
        assert existence[0].status is ClaimStatus.VERIFIED_CURRENT

    @pytest.mark.parametrize(
        "closure",
        [
            "This scholarship has been discontinued.",
            "The award is no longer offered.",
            "Applications are suspended for the 2026/27 cycle.",
            "This scholarship has been withdrawn for the 2026/27 cycle.",
        ],
    )
    def test_definite_scheme_closure_still_refuses_availability(self, closure: str) -> None:
        award, claims = _read_availability_page(closure)

        assert award.currently_available == "no"
        assert award.award_current_for_intake == "no"
        assert award.available_this_intake == "no"
        withdrawal = [
            c
            for c in claims
            if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS and c.normalized_value is False
        ]
        assert len(withdrawal) == 1
        assert withdrawal[0].original_text_excerpt == closure
        assert roll(award_current_for_intake=award.award_current_for_intake) == "no"

    @pytest.mark.parametrize("closure_first", [False, True])
    def test_holder_prose_cannot_hide_or_replace_a_real_scheme_closure(
        self, closure_first: bool
    ) -> None:
        holder_condition = (
            "The scholarship may be withdrawn if the holder's conduct is unsatisfactory."
        )
        closure = "Applications are suspended for the 2026/27 cycle."
        paragraphs = (closure, holder_condition) if closure_first else (holder_condition, closure)
        award, claims = _read_availability_page(*paragraphs)

        assert award.award_current_for_intake == "no"
        assert award.available_this_intake == "no"
        withdrawal = [
            c
            for c in claims
            if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS and c.normalized_value is False
        ]
        assert len(withdrawal) == 1
        assert withdrawal[0].original_text_excerpt == closure
        assert withdrawal[0].status is ClaimStatus.VERIFIED_CURRENT

    @pytest.mark.parametrize("closure_first", [False, True])
    def test_a_same_paragraph_holder_condition_does_not_contaminate_the_closure_quote(
        self, closure_first: bool
    ) -> None:
        holder_condition = (
            "The scholarship may be withdrawn if the holder's conduct is unsatisfactory."
        )
        closure = "Applications are suspended for the 2026/27 cycle."
        paragraph = (
            f"{closure} {holder_condition}" if closure_first else f"{holder_condition} {closure}"
        )
        award, claims = _read_availability_page(paragraph)

        assert award.currently_available == "no"
        assert award.award_current_for_intake == "no"
        assert award.available_this_intake == "no"
        withdrawal = [
            c
            for c in claims
            if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS and c.normalized_value is False
        ]
        assert len(withdrawal) == 1
        assert withdrawal[0].original_text_excerpt == closure
        assert withdrawal[0].status is ClaimStatus.VERIFIED_CURRENT
