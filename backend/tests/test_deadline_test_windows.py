"""An admissions test's sitting and booking dates are not the application deadline.

The Imperial fixture is cut from its BEng Computing page (UCAS G400), hand-fetched
on 2026-10-18 (structural analysis 2026-10-18 §2 F4): the TMUA block comes before
the "How to apply" block, and the deadline reader took "Booking closes: 28
September 2026" — the TMUA's first booking window — as the deadline.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_requirements, for_matching

IMPERIAL = (
    "Test dates\n\n"
    "There are two test sitting windows for the TMUA for 2027 entry.\n\n"
    "For candidates in all countries except China, Hong Kong and Macau\n \n\n"
    "Test window 1\n: 12–16 October 2026\n \n\n"
    "Test window 2\n: 4–8 January 2027\n \n\n"
    "For candidates sitting the test in China, Macau and Hong Kong\n \n\n"
    "Test window 2\n: \n8\n January 2027\n \n\n"
    "Booking windows (all candidates)\n \n\n"
    "Test window 1\n \n\n"
    "Booking for the October TMUA test sitting is now closed\n\n"
    "Booking closes: 28 September 2026 at 18.00 (UK time)\n \n\n"
    "Test window 2\n \n\n"
    "Booking opens: 26 October 2026 at 15.00 (UK time)\n \n\n"
    "Booking closes: 21 December 2026 at 18.00 (UK time)\n \n\n"
    "How to apply\n\n"
    "Apply via UCAS\n\n"
    "Submit your application via UCAS | G400\n"
    "UCAS institution code: I50\n"
    "Application deadlines – Wednesday 13 January 2027 at 18.00 (UK time)\n\n \n\n"
    "Admissions test – the TMUA\n\n"
    "To be eligible for selection for this course for 2027 entry, you must sit the \n"
    "Test of Mathematics for University Admission (TMUA)\n as part of the application process.\n"
)


def deadlines(text: str) -> list[tuple[str, str]]:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    extract_requirements(text, builder)
    return [
        (str(c.normalized_value), c.original_text_excerpt)
        for c in builder.claims
        if c.claim_type.value == "admission_deadline"
    ]


def test_imperials_application_deadline_is_read_not_the_tmua_booking_window():
    ((value, excerpt),) = deadlines(IMPERIAL)
    assert value == "2027-01-13"
    assert "13 January 2027" in excerpt


def test_the_same_page_reads_the_same_through_for_matching():
    assert [v for v, _ in deadlines(for_matching(IMPERIAL))] == ["2027-01-13"]


@pytest.mark.parametrize(
    "text",
    [
        "Booking closes: 28 September 2026 at 18.00 (UK time)",
        "Register for the UCAT: the registration deadline is 19 September 2026.",
        "LNAT registration closes 15 January 2027.",
        "You must sit the test by its deadline of 15 October 2026.",
        "Test dates: the deadline to book is 1 October 2026.",
        "TMUA results are released and booking closes on 21 December 2026.",
    ],
)
def test_a_test_date_alone_is_no_deadline(text):
    assert deadlines(text) == []


def test_an_application_deadline_label_beats_an_earlier_closing_date():
    text = (
        "Accommodation applications close 1 June 2027. "
        "Application deadline: 15 January 2027 for the fall 2027 intake."
    )
    assert [v for v, _ in deadlines(text)] == ["2027-01-15"]


def test_a_late_application_deadline_is_not_preferred():
    text = (
        "The deadline for applications is 15 January 2027. "
        "Late application deadline: 30 June 2027, places permitting."
    )
    assert [v for v, _ in deadlines(text)] == ["2027-01-15"]


@pytest.mark.parametrize(
    ("text", "iso"),
    [
        # A test named in another sentence does not taint the deadline.
        (
            "You must sit the TMUA in October. Applications close 13 January 2027.",
            "2027-01-13",
        ),
        # Nor does a test named beside another date before this one.
        (
            "TMUA test window: 12 October 2026 Applications close 13 January 2027",
            "2027-01-13",
        ),
        # A deadline sentence that mentions no test is read as before.
        ("The application deadline is 1 February 2027 at 23:59 MST.", "2027-02-01"),
        ("Deadline: 15 January 2027", "2027-01-15"),
    ],
)
def test_an_application_deadline_beside_a_test_is_still_read(text, iso):
    assert [v for v, _ in deadlines(text)] == [iso]


def test_the_excerpt_quotes_from_the_deadline_word_as_the_generic_reader_did():
    """The demo golden's excerpts must not move: a label read by the new reader
    is quoted from the same character as the generic reader quoted it."""
    text = (
        "x " * 100
        + "Key dates The application deadline for the fall 2027 intake is 9 January 2027."
    )
    ((_, excerpt),) = deadlines(text)
    assert excerpt.startswith("x x")
    assert excerpt.endswith("9 January 2027.")
