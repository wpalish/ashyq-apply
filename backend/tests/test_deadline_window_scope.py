"""Plan rule EX-2: a study period is not an application window, and a page with
one section per intake is read for the requested intake only.

The fixtures are shaped like Uppsala's programme page, hand-fetched on
2026-10-17 (evidence analysis 2026-10-17 §1.2), cut to the lines that decide.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import app.adapters.extraction as extraction
from app.adapters.extraction import ClaimBuilder, extract_requirements

#: One intake; its study period and its semester dates are two date ranges
#: that end on different days, and neither is an application window.
ONE_INTAKE = (
    "Bachelor's Programme in Computer Science\n"
    "180 credits\n"
    "Location\nUppsala\n"
    "Study period\n30 August 2027–9 June 2030\n"
    "Semester dates\n30 August 2027 – 16 January 2028\n"
    "Language of instruction\nEnglish\n"
    "Total tuition fee: \nSEK 450,000\n"
    "Application deadline\n15 April 2027\n"
    "Application code\nUU-P1100\n"
)
#: A tab bar naming both intakes, then one section each.
TWO_INTAKES = (
    "Bachelor's Programme in Computer Science\n"
    "Application and entry requirements\n"
    " \nAutumn 2027\n \nSpring 2028\n \n"
    "Expand the information below to show details on entry requirements.\n"
    " \nAutumn 2027\n \nAutumn 2027, \n"
    "Uppsala, 100%, On-campus, English\n"
    "Study period\n30 August 2027–9 June 2030\n"
    "Application deadline\n15 April 2027\n"
    "Application code\nUU-P1100\n"
    " \nSpring 2028\n \nSpring 2028, \n"
    "Uppsala, 100%, On-campus, English\n"
    "Study period\n17 January 2028–2 June 2031\n"
    "Application deadline\n15 October 2027\n"
    "Application code\nUU-P1200\n"
)
#: Two real application windows, one per qualification: still no claim.
TWO_WINDOWS = (
    "Applications close 19 March 2027 for IB diploma holders: application window "
    "15 October 2026 - 19 March 2027. A-level holders: application window "
    "15 October 2026 - 20 January 2027."
)


def deadlines(text: str, intake: str | None = "Fall 2027") -> list[str]:
    builder = ClaimBuilder(
        source_url="https://www.uu.se/en/study/programme/bachelors-programme-computer-science",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 17, tzinfo=UTC),
        intake=intake,
        page_text=text,
    )
    extract_requirements(text, builder)
    return [
        c.normalized_value for c in builder.claims if c.claim_type.value == "admission_deadline"
    ]


@pytest.fixture
def scope(monkeypatch):
    monkeypatch.setattr(extraction, "DEADLINE_WINDOW_SCOPE", True)


def test_off_by_default_and_study_periods_block_the_deadline_today():
    assert extraction.DEADLINE_WINDOW_SCOPE is False
    assert deadlines(ONE_INTAKE) == []
    assert deadlines(TWO_INTAKES) == []
    assert deadlines(TWO_INTAKES, "Spring 2028") == []


def test_a_study_period_is_not_an_application_window(scope):
    assert deadlines(ONE_INTAKE) == ["2027-04-15"]


def test_the_requested_intakes_section_is_read(scope):
    assert deadlines(TWO_INTAKES, "Fall 2027") == ["2027-04-15"]
    assert deadlines(TWO_INTAKES, "Autumn 2027") == ["2027-04-15"]
    assert deadlines(TWO_INTAKES, "Spring 2028") == ["2027-10-15"]


def test_no_section_for_the_requested_intake_claims_no_other_intakes_deadline(scope):
    assert deadlines(TWO_INTAKES, "Fall 2029") == []
    assert deadlines(TWO_INTAKES, None) == []


def test_two_application_windows_still_claim_nothing(scope):
    assert deadlines(TWO_WINDOWS) == []


def test_a_range_after_an_application_word_is_still_a_window():
    text = "Study period starts in August. Application period: 1 March 2027 – 15 April 2027"
    window = extraction._DATE_RANGE_V2.search(text)
    assert window is not None
    assert not extraction._study_period_range(text, window)
    study = "Study period\n30 August 2027–9 June 2030"
    window = extraction._DATE_RANGE_V2.search(study)
    assert window is not None
    assert extraction._study_period_range(study, window)


def test_the_excerpt_is_the_pages_own_text(scope):
    builder = ClaimBuilder(
        source_url="https://www.uu.se/x",
        page_title="x",
        official_domain=True,
        accessed_at=datetime(2026, 10, 17, tzinfo=UTC),
        intake="Spring 2028",
        page_text=TWO_INTAKES,
    )
    extract_requirements(TWO_INTAKES, builder)
    (claim,) = [c for c in builder.claims if c.claim_type.value == "admission_deadline"]
    assert "15 October 2027" in claim.original_text_excerpt
    assert "15 April 2027" not in claim.original_text_excerpt
