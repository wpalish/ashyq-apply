"""``_SAT_MIN`` reads a total-score label with a dash or colon.

NTU's English-proficiency alternatives read "SAT Total score – 1250" (the
signed corpus quotes exactly that). The reader wanted "minimum", "at least" or
"score of" between SAT and the number, or "1250 for the SAT", so the page was
read and no SAT minimum came of it (core-gap analysis 2026-10-18, B1).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_requirements
from app.domain.enums import ClaimType


def _sat(text: str) -> list[int]:
    builder = ClaimBuilder(
        source_url="https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements",
        official_domain=True,
        accessed_at=datetime(2026, 10, 18, tzinfo=UTC),
        page_text=text,
    )
    extract_requirements(text, builder)
    return [c.normalized_value for c in builder.claims if c.claim_type is ClaimType.SAT_MIN_TOTAL]


@pytest.mark.parametrize(
    ("text", "score"),
    [
        ("English proficiency alternatives: SAT Total score – 1250", 1250),
        ("SAT Total score - 1250", 1250),
        ("SAT Total score: 1300", 1300),
        ("SAT: 1350", 1350),
        ("SAT Composite – 1400", 1400),
        ("SAT total — 1200", 1200),
    ],
)
def test_a_labelled_total_is_the_minimum(text: str, score: int) -> None:
    assert _sat(text) == [score]


@pytest.mark.parametrize(
    "text",
    [
        "SAT: 650 in Math",
        "SAT – 650 for each section",
        "SAT Total score – 1250-1450 (middle 50% of admitted students)",
        "SAT – 1250 to 1450",
        "SAT – 2027 test dates",
        "SAT: 80 places",
        "SAT is optional. SAT Total score – 1250",
    ],
    ids=["section", "each-section", "range", "range-to", "year", "small", "optional"],
)
def test_not_a_minimum_total(text: str) -> None:
    assert _sat(text) == []


def test_the_earlier_wordings_still_read() -> None:
    assert _sat("SAT with a minimum score of 1300") == [1300]
    assert _sat("1250 for redesigned SAT") == [1250]
