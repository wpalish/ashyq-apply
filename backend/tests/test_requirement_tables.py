"""English requirements published as a table are published, and were unread.

The gold audit of Groningen's BSc Computing Science found three questions the
university answers and the extractor misses, and two of them are one table:

    IELTS 6.5 / CEFR B2-C1 | Overall | Reading | Listening | Speaking | Writing
    IELTS (Academic)       |    6.5  |    6.5  |      6.5  |     6.5  |    6.5

`extract_requirements` reads flattened text, where that row is the string
"IELTS (Academic) 6.5 6.5 6.5 6.5 6.5" and the column that gives each number its
meaning is gone. The extractor produced **nothing at all** from that page.

This is the same argument `extract_cost_tables` already makes for fees: on
flattened text a label near a number is an accident of layout and must not be
trusted, while a table row is a deliberate statement of association. What was
missing is that the argument was only ever applied to money.

The TOEFL row is here because it is the honest hard case. The institution
stacked the new 1-6 scale and the old 0-120 scale in one cell, so "Overall" for
TOEFL is both 4.5 and 90. There is no reading of that cell which is not a guess,
and a guessed English requirement is a rejected application — so the row must be
refused rather than resolved.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.extraction import ClaimBuilder, extract_requirement_tables
from app.domain.enums import ClaimType, SourceSpecificity

FIXTURES = Path(__file__).parent / "fixtures" / "requirement_tables"


@pytest.fixture
def builder() -> ClaimBuilder:
    return ClaimBuilder(
        source_url="https://www.rug.nl/fse/education/admission-application/apply-bsc/language",
        specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
        official_domain=True,
    )


@pytest.fixture
def claims(builder: ClaimBuilder):
    html = (FIXTURES / "rug_english.html").read_text()
    return extract_requirement_tables(html, builder)


def of_type(claims, claim_type: ClaimType):
    return [c for c in claims if c.claim_type == claim_type]


class TestTheRowIsReadColumnByColumn:
    def test_the_overall_ielts_band_is_read(self, claims):
        overall = of_type(claims, ClaimType.IELTS_MIN_OVERALL)
        assert [c.normalized_value for c in overall] == [6.5]

    def test_each_section_minimum_is_read(self, claims):
        subscores = of_type(claims, ClaimType.IELTS_MIN_SUBSCORE)
        assert {c.subject_key for c in subscores} == {
            "reading", "listening", "speaking", "writing"
        }
        assert {c.normalized_value for c in subscores} == {6.5}

    def test_every_claim_quotes_the_row_it_came_from(self, claims):
        """The excerpt is what lets an applicant check the machine's reading,
        and a bare "6.5" shows nothing."""
        for claim in claims:
            assert "IELTS" in claim.original_text_excerpt
            assert "6.5" in claim.original_text_excerpt

    def test_a_test_on_its_own_scale_is_not_read_as_ielts(self, claims):
        """Pearson scores 58-70 on a 10-90 scale. Read as IELTS bands they are
        impossible, and read as a requirement they are wrong."""
        for claim in of_type(claims, ClaimType.IELTS_MIN_OVERALL):
            assert claim.normalized_value <= 9.0


class TestAnAmbiguousCellIsRefusedRatherThanResolved:
    def test_the_toefl_row_with_two_scales_in_one_cell_produces_nothing(self, claims):
        """4.5 on the new scale and 90 on the old are in the same cell. Either
        answer is a guess, and the product does not guess."""
        assert of_type(claims, ClaimType.TOEFL_MIN_TOTAL) == []

    def test_the_prose_row_is_not_mined_for_a_number(self, claims):
        """"CAE or CPE Certificate with a minimum score of 180" spans all five
        columns. 180 is not an overall band, a reading score, or anything else
        this table's headers describe."""
        for claim in claims:
            assert claim.normalized_value != 180


class TestItReadsNothingFromATableThatIsNotAboutLanguage:
    def test_a_fee_table_produces_no_language_requirement(self, builder):
        html = """
        <h2>Tuition fees</h2>
        <table>
          <tr><th>Year</th><th>Overall</th></tr>
          <tr><td>2026-2027</td><td>2694</td></tr>
        </table>
        """
        assert extract_requirement_tables(html, builder) == []

    def test_a_page_with_no_tables_produces_nothing(self, builder):
        assert extract_requirement_tables("<p>IELTS 6.5 is required.</p>", builder) == []
