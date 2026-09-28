"""UBC states IELTS under its full name, and one floor for every part.

Both came from the oracle's page context in live run 35825874826: the words
were on the page and no claim came out.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder, extract_requirements
from evaluation.research.mapping import normalize_claim

_UBC = (
    "IELTS *IELTS General, IELTS Indicator, and IELTS One Skill Retake are not accepted "
    "International English Language Testing System (Academic) 6.5, with no part less than 6.0 "
    "PTE Pearson Test of English (Academic) Overall: 65 Reading: 60"
)


def _claims(text: str) -> dict[str, object]:
    builder = ClaimBuilder(
        source_url="https://you.ubc.ca/applying-ubc/requirements/english-language-competency/",
        page_title="English language competency",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    extract_requirements(text, builder)
    return {c.claim_type.value: c.normalized_value for c in builder.claims}


def test_the_spelled_out_name_carries_the_overall_band():
    claims = _claims(_UBC)
    assert claims["ielts_min_overall"] == 6.5
    assert claims["ielts_min_subscore"] == 6.0


def test_a_number_after_the_full_name_without_a_floor_is_not_an_overall_band():
    """ "Testing System 7 locations" must not become a requirement."""
    claims = _claims("International English Language Testing System 7 test centres in Vancouver.")
    assert "ielts_min_overall" not in claims


def test_one_floor_is_spelled_out_as_the_four_bands_it_governs():
    key, value, _, _ = normalize_claim("ielts_min_subscore", {"normalized_value": 6.0})
    assert key == "ielts.subscores"
    assert value == {"listening": 6.0, "reading": 6.0, "speaking": 6.0, "writing": 6.0}


def test_bands_stated_one_by_one_are_left_as_stated():
    bands = {"writing": 6.0, "speaking": 6.5}
    _, value, _, _ = normalize_claim("ielts_min_subscore", {"normalized_value": bands})
    assert value == bands
