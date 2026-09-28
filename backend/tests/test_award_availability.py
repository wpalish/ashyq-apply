"""Phase 3 §7 — the availability roll-up, deterministic and honest.

The rule lived inside the scholarship adapter and was neither complete nor
findable: it ignored `opportunity_exists` and `award_current_for_intake`
entirely, so an award a page calls discontinued could still roll up to
available for the intake. Both of those fields were declared and never set.
"""

from __future__ import annotations

from app.domain.funding import roll_up_availability


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
