"""INTAKE_TERM: the term a page states as a programme's start."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_intake_terms


def _builder() -> ClaimBuilder:
    return ClaimBuilder(
        source_url="https://cs.example.edu/bcs",
        page_title="BCS",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 27, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("text", "value"),
    [
        (
            "Students beginning their studies in September 2027 will be the first cohort.",
            "fall 2027",
        ),
        ("Program start\nFall 2027\nProgram length\n4 years", "fall 2027"),
        ("Entry for the fall 2027 intake.", "fall 2027"),
        ("Applications are open for the January 2028 intake.", "spring 2028"),
    ],
)
def test_a_stated_start_is_an_intake(text: str, value: str) -> None:
    claims = extract_intake_terms(text, _builder())
    assert [c.normalized_value for c in claims] == [value]


@pytest.mark.parametrize(
    "text",
    [
        "Application deadline: January 15, 2027 for admission in the fall.",
        "Beginning with the June 2028 graduation cycle, students may choose the degree.",
        "Tuition for students starting in September 2027 is CAD 60,000.",
        "The department was founded in September 1987.",
    ],
)
def test_deadlines_graduations_and_fees_are_not_intakes(text: str) -> None:
    assert extract_intake_terms(text, _builder()) == []


def test_each_term_is_claimed_once() -> None:
    text = "Entry for the fall 2027 intake.\nProgram start\nFall 2027"
    assert len(extract_intake_terms(text, _builder())) == 1
