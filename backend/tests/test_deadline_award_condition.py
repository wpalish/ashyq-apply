"""Plan rule DL-3: a deadline its own sentence ties to an award application.

Serper run 39058503662 claimed UBC's scholarship-consideration date,
2026-11-15, as the admission deadline. The admission deadline for
September 2027 entry is 2027-01-15.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import app.adapters.extraction as extraction
from app.adapters.extraction import ClaimBuilder, extract_requirements

#: Verbatim from https://you.ubc.ca/applying-ubc (run 39058503662).
UBC_HUB = (
    "Deadline November 15, 2026 Apply before 11:59 pm PDT International students: Deadline to "
    "apply to UBC and submit an award application if you wish to be considered for the UBC "
    "International Major Entrance Scholarship and other awards."
)
PLAIN = "Applications due January 15, 2027 for Winter Session (September 2027 to April 2028)."


def deadlines(text: str) -> list[str]:
    builder = ClaimBuilder(
        source_url="https://you.ubc.ca/applying-ubc/",
        page_title="Applying to UBC",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 17, tzinfo=UTC),
        page_text=text,
    )
    extract_requirements(text, builder)
    return [
        str(c.normalized_value)
        for c in builder.claims
        if c.claim_type.value == "admission_deadline"
    ]


@pytest.fixture
def dl3(monkeypatch):
    monkeypatch.setattr(extraction, "DEADLINE_AWARD_CONDITION", True)


def test_off_by_default():
    assert extraction.DEADLINE_AWARD_CONDITION is False


def test_flag_off_keeps_todays_reading():
    """Today the first deadline on the page wins: the award date, alone."""
    assert deadlines(UBC_HUB + " " + PLAIN) == ["2026-11-15"]
    assert deadlines(UBC_HUB) == ["2026-11-15"]


def test_the_award_date_is_not_the_admission_deadline(dl3):
    assert deadlines(UBC_HUB) == []
    assert deadlines(UBC_HUB + " " + PLAIN) == ["2027-01-15"]


def test_an_unconditional_deadline_on_the_same_page_is_read(dl3):
    assert deadlines(PLAIN) == ["2027-01-15"]
    assert deadlines(PLAIN + " " + UBC_HUB) == ["2027-01-15"]


@pytest.mark.parametrize(
    "sentence",
    [
        "Scholarship application deadline: March 1, 2027.",
        "Priority deadline for scholarships December 1, 2026.",
        "Deadline December 1, 2026 to be considered for the Presidential Scholars Award.",
    ],
)
def test_each_condition_phrase_drops_its_date(dl3, sentence):
    assert deadlines(sentence + " " + PLAIN) == ["2027-01-15"]


def test_scholarships_elsewhere_on_the_page_do_not_taint_the_deadline(dl3):
    text = (
        "Applications due January 15, 2027. Scholarships and awards: an award application is "
        "made separately if you wish to be considered for entrance scholarships."
    )
    assert deadlines(text) == ["2027-01-15"]


def test_a_neighbouring_scholarship_date_without_a_full_stop_stays_apart(dl3):
    text = "Scholarship application deadline December 1, 2026 Applications due January 15, 2027"
    assert deadlines(text) == ["2027-01-15"]


def test_clock_dots_do_not_end_the_sentence(dl3):
    text = (
        "Deadline November 15, 2026 (11:59 p.m. PST) International applicants: submit an award "
        "application if you wish to be considered for the International Scholars Program. "
    )
    assert deadlines(text + PLAIN) == ["2027-01-15"]
