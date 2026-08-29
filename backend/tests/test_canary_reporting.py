"""A failure must not be reported as an absence.

A holdout run died on the second of six institutions. The four after it were
reported NOT_ATTEMPTED, which reads as a finding about those universities — and
it took a while to notice it was a finding about one malformed page on another
site. The discovery failure is now contained, but the report still had no way
to say "this one was tried and it broke".
"""
from scripts.canary_discovery import access_state


def test_a_reached_institution_is_reached():
    assert access_state(checked=12, blocked=0, failed_discovery=False) == "REACHED"


def test_robots_blocking_everything_is_blocked():
    assert access_state(checked=6, blocked=6, failed_discovery=False) == "BLOCKED"


def test_partial_blocking_says_so():
    assert access_state(checked=10, blocked=2, failed_discovery=False) == "PARTIALLY_BLOCKED"


def test_nothing_tried_is_not_attempted():
    assert access_state(checked=0, blocked=0, failed_discovery=False) == "NOT_ATTEMPTED"


def test_a_discovery_that_raised_is_not_reported_as_untried():
    """The distinction that was missing. "We did not look" and "we looked and
    it broke" are different findings, and only one of them is about the
    institution."""
    assert access_state(checked=0, blocked=0, failed_discovery=True) == "FAILED"


def test_a_failure_outranks_pages_that_were_read_first():
    """Uppsala had read forty pages before the one that broke it. Reporting
    REACHED would hide that its result is incomplete."""
    assert access_state(checked=40, blocked=0, failed_discovery=True) == "FAILED"
