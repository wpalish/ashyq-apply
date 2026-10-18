"""EN-2 / TF-2 (``extraction.ENGLISH_READERS_V2``): English tables and levels the readers missed.

Core-gap analysis 2026-10-18, change 2 (EN-2) and change 7 (TF-2). Every
fixture under ``tests/fixtures/english_readers_v2/`` is trimmed from the
official page named in its first line, fetched by hand on 2026-10-18:

* TCD: the test names are a header row of ``<td>`` cells and the rows are
  entry bands; the programme page names "Band B (Standard Entry)".
* UNSW: the test name is the accordion label around each table and the rows
  are faculties; the programme page names the Faculty of Engineering.
* Imperial: each test is a tab with a "Standard" and a "Higher" column; the
  programme page names the standard requirement.
* Delft, Uppsala: the first number after "TOEFL" is a date or a section score.

A table of several rows is read only for the row the programme page names;
otherwise nothing is claimed, never the first, highest or lowest row.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters import extraction
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import (
    ClaimBuilder,
    EnglishHint,
    english_programme_hint,
    extract_requirements,
    for_matching,
    readable_text,
)
from app.adapters.fetching import Fetcher
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.structured_extraction import extract_table_requirements
from app.domain.enums import ClaimType, DegreeLevel
from app.schemas.claim import Claim

FIXTURES = Path(__file__).parent / "fixtures" / "english_readers_v2"
TCD_ENGLISH = "https://www.tcd.ie/study/english-language-requirements/"
UNSW_ENGLISH = "https://www.unsw.edu.au/study/how-to-apply/english-language-requirements"
IMPERIAL_ENGLISH = "https://www.imperial.ac.uk/study/apply/english-language/"

IELTS = ClaimType.IELTS_MIN_OVERALL
IELTS_SUB = ClaimType.IELTS_MIN_SUBSCORE
TOEFL = ClaimType.TOEFL_MIN_TOTAL
DUOLINGO = ClaimType.DUOLINGO_MIN
ENGLISH = (IELTS, IELTS_SUB, TOEFL, DUOLINGO)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _hint(programme: str, degree: str | None = "bachelor") -> EnglishHint:
    html = _page(programme)
    return english_programme_hint(readable_text(html), html, degree)


@pytest.fixture
def v2(monkeypatch):
    monkeypatch.setattr(extraction, "ENGLISH_READERS_V2", True)


@pytest.fixture
def v1(monkeypatch):
    monkeypatch.setattr(extraction, "ENGLISH_READERS_V2", False)


def _read(
    name: str, url: str, hint: EnglishHint | None = None
) -> tuple[dict[ClaimType, Claim], list[Claim], ClaimBuilder]:
    """The page as the QR-1 English read does it: tables first, then prose."""
    html = _page(name)
    text = readable_text(html)
    builder = ClaimBuilder(source_url=url, official_domain=True, page_text=text)
    builder.english_hint = hint
    tabled = extract_table_requirements(build_document_ir(html, url), builder)
    before = len(builder.claims)
    extract_requirements(text, builder)
    answered = {c.claim_type for c in tabled}
    builder.claims[before:] = [c for c in builder.claims[before:] if c.claim_type not in answered]
    english = [c for c in builder.claims if c.claim_type in ENGLISH]
    return {c.claim_type: c for c in english}, tabled, builder


def _values(claims: dict[ClaimType, Claim]) -> dict[ClaimType, object]:
    return {t: c.normalized_value for t, c in claims.items()}


# --- the programme page names its row -----------------------------------------


def test_tcd_programme_page_names_band_b_standard():
    hint = _hint("tcd_programme.html")
    assert (hint.band, hint.level, hint.degree) == ("b", "standard", "bachelor")


def test_imperial_programme_page_names_the_standard_requirement():
    hint = _hint("imperial_programme.html")
    assert (hint.band, hint.level) == (None, "standard")


def test_unsw_programme_page_names_its_faculty():
    assert "engineering" in _hint("unsw_programme.html").units


def test_a_level_word_outside_an_english_sentence_is_not_a_hint():
    html = "<p>Applicants must meet the higher entry requirements in Mathematics.</p>"
    assert english_programme_hint(readable_text(html), html).level is None


def test_two_levels_on_one_programme_page_are_no_hint():
    html = (
        "<p>Applicants to this course are required to meet Band B (Standard Entry) English "
        "language requirements.</p><p>Applicants to the joint course are required to meet "
        "Band C (Higher Entry) English language requirements.</p>"
    )
    hint = english_programme_hint(readable_text(html), html)
    assert (hint.band, hint.level) == (None, None)


# --- (a) TCD: test names in a header row of <td>s, rows are entry bands ----------


def test_tcd_band_b_row_gives_ielts_toefl_and_duolingo(v2):
    claims, tabled, _ = _read("tcd_english.html", TCD_ENGLISH, _hint("tcd_programme.html"))
    assert _values(claims) == {IELTS: 6.5, IELTS_SUB: 6.0, TOEFL: 90, DUOLINGO: 120}
    assert {c.claim_type for c in tabled} == set(claims)
    ielts = claims[IELTS]
    # The quote is the row, from its band label to the IELTS cell, verbatim.
    assert ielts.original_text_excerpt == (
        "Band B (Standard entry) UG & PG Standard requirements 6.5 overall 6.0 in each band"
    )
    assert "IELTS Academic" in ielts.relevant_section
    assert "Band B (Standard entry)" in ielts.relevant_section
    # The pre-2026 TOEFL column; the new 1-6 banded column is not a 0-120 total.
    assert "TOEFL iBT (Before January 2026)" in claims[TOEFL].relevant_section
    assert claims[TOEFL].original_text_excerpt.endswith("90 overall 21 in each section")


def test_tcd_without_a_programme_hint_abstains_on_every_test(v2):
    claims, _, builder = _read("tcd_english.html", TCD_ENGLISH, None)
    assert claims == {}
    assert {IELTS, IELTS_SUB, TOEFL, DUOLINGO} <= builder.english_abstained


def test_tcd_higher_band_reads_band_c_not_the_first_row(v2):
    claims, _, _ = _read(
        "tcd_english.html", TCD_ENGLISH, EnglishHint(band="c", level="higher", degree="bachelor")
    )
    assert _values(claims) == {IELTS: 7.0, IELTS_SUB: 6.5, TOEFL: 100, DUOLINGO: 130}


def test_tcd_band_hint_naming_no_row_abstains(v2):
    claims, _, _ = _read("tcd_english.html", TCD_ENGLISH, EnglishHint(band="e"))
    assert claims == {}


def test_tcd_flag_off_reads_no_english_minimum(v1):
    claims, tabled, builder = _read("tcd_english.html", TCD_ENGLISH, _hint("tcd_programme.html"))
    assert claims == {} and tabled == []
    assert builder.english_abstained == set()


# --- (a)+(b) UNSW: the test is the accordion label, rows are faculties ------------


def test_unsw_engineering_undergraduate_cell_gives_overall_and_floor(v2):
    claims, tabled, _ = _read("unsw_english.html", UNSW_ENGLISH, _hint("unsw_programme.html"))
    assert _values(claims) == {IELTS: 6.5, IELTS_SUB: 6.0, TOEFL: 90}
    assert claims[IELTS].original_text_excerpt == (
        "Engineering 6.5 overall (min 6.0 in each subtest)"
    )
    assert claims[IELTS].relevant_section.startswith("IELTS (International English")
    assert "Undergraduate" in claims[IELTS].relevant_section
    assert claims[TOEFL].original_text_excerpt == (
        "Engineering 90 overall (min. 23 in writing, 22 in reading, listening and speaking)"
    )
    # The PTE accordion is another test's table: nothing from it.
    assert all("PTE" not in c.relevant_section for c in tabled)


def test_unsw_every_unit_the_full_programme_page_names_still_picks_engineering(v2):
    # The live programme page names three units (its school, its faculty and a
    # scholarship programme); only "engineering" is a row of the table.
    hint = EnglishHint(
        units=frozenset(
            {"computer science and engineering", "engineering", "engineering rural scholarships"}
        ),
        degree="bachelor",
    )
    claims, _, _ = _read("unsw_english.html", UNSW_ENGLISH, hint)
    assert _values(claims) == {IELTS: 6.5, IELTS_SUB: 6.0, TOEFL: 90}


def test_unsw_without_a_faculty_abstains_rather_than_take_a_row(v2):
    claims, _, builder = _read("unsw_english.html", UNSW_ENGLISH, EnglishHint(degree="bachelor"))
    assert claims == {}
    assert {IELTS, IELTS_SUB, TOEFL} <= builder.english_abstained


def test_unsw_business_row_reads_its_own_band(v2):
    claims, _, _ = _read(
        "unsw_english.html",
        UNSW_ENGLISH,
        EnglishHint(units=frozenset({"business"}), degree="bachelor"),
    )
    assert _values(claims) == {IELTS: 7.0, IELTS_SUB: 6.0, TOEFL: 94}


def test_unsw_a_cell_with_exceptions_is_not_read(v2):
    # Arts, Design & Architecture: "6.5 overall (min. 6.0 in each subtest)
    # Exceptions: Bachelor of Education (Secondary) (Honours): 7.5 overall ...".
    claims, _, _ = _read(
        "unsw_english.html",
        UNSW_ENGLISH,
        EnglishHint(units=frozenset({"arts, design and architecture"}), degree="bachelor"),
    )
    assert IELTS not in claims and TOEFL not in claims


def test_unsw_without_a_degree_the_faculty_columns_must_agree(v2):
    # Engineering states 6.5 (min 6.0) for every degree column: no choice is made.
    claims, _, _ = _read(
        "unsw_english.html", UNSW_ENGLISH, EnglishHint(units=frozenset({"engineering"}))
    )
    assert _values(claims)[IELTS] == 6.5
    # Business: postgraduate research is "7.0 overall (min 7.0 in writing, 6.5 in
    # other subtests)", which differs from the other two columns.
    claims, _, _ = _read(
        "unsw_english.html", UNSW_ENGLISH, EnglishHint(units=frozenset({"business"}))
    )
    assert IELTS not in claims


def test_unsw_flag_off_reads_no_english_minimum(v1):
    claims, tabled, _ = _read("unsw_english.html", UNSW_ENGLISH, _hint("unsw_programme.html"))
    assert IELTS not in claims and TOEFL not in claims and tabled == []


# --- (a)+(c) Imperial: tabs labelled by test, Standard and Higher columns --------


def test_imperial_standard_column_is_read_for_a_standard_programme(v2):
    claims, tabled, _ = _read(
        "imperial_english.html", IMPERIAL_ENGLISH, _hint("imperial_programme.html")
    )
    assert _values(claims) == {IELTS: 6.5, IELTS_SUB: 6.0, TOEFL: 92, DUOLINGO: 115}
    assert claims[IELTS].original_text_excerpt == "6.5 overall (minimum 6.0 in all elements)"
    assert claims[IELTS].relevant_section == (
        "IELTS – Academic (Test-Centre/UKVI SELT/Online) / Standard"
    )
    assert {c.claim_type for c in tabled} == set(claims)


def test_imperial_higher_programme_reads_the_higher_column(v2):
    claims, _, _ = _read("imperial_english.html", IMPERIAL_ENGLISH, EnglishHint(level="higher"))
    assert _values(claims) == {IELTS: 7.0, IELTS_SUB: 6.5, TOEFL: 100, DUOLINGO: 125}


def test_imperial_without_a_level_abstains_on_every_test(v2):
    claims, _, builder = _read("imperial_english.html", IMPERIAL_ENGLISH, None)
    # The flag-off reader's Duolingo 115 (the first number after the word) goes too.
    assert claims == {}
    assert {IELTS, IELTS_SUB, TOEFL, DUOLINGO} <= builder.english_abstained


def test_imperial_flag_off_is_unchanged(v1):
    claims, tabled, _ = _read(
        "imperial_english.html", IMPERIAL_ENGLISH, _hint("imperial_programme.html")
    )
    assert tabled == []
    assert _values(claims) == {DUOLINGO: 115}


def _prose(text: str, hint: EnglishHint | None) -> dict[ClaimType, object]:
    builder = ClaimBuilder(source_url="fixture://page", official_domain=True, page_text=text)
    builder.english_hint = hint
    extract_requirements(text, builder)
    return {c.claim_type: c.normalized_value for c in builder.claims if c.claim_type in ENGLISH}


def test_imperial_prose_level_layout_reads_the_standard_band(v2):
    text = readable_text(_page("imperial_english.html"))
    got = _prose(text, EnglishHint(level="standard"))
    assert (got[IELTS], got[IELTS_SUB]) == (6.5, 6.0)
    assert _prose(text, EnglishHint(level="higher"))[IELTS] == 7.0


def test_imperial_prose_level_layout_without_a_level_claims_no_ielts(v2):
    text = readable_text(_page("imperial_english.html"))
    got = _prose(text, None)
    assert IELTS not in got and IELTS_SUB not in got


def test_prose_level_layout_whose_bands_do_not_pair_abstains(v2):
    text = "IELTS Academic Standard Higher 6.5 overall (minimum 6.0 in all elements)"
    assert IELTS not in _prose(text, EnglishHint(level="standard"))


def test_prose_without_a_level_layout_reads_as_before(v2):
    text = "Applicants need IELTS overall 6.5 with no band below 6.0."
    assert _prose(text, None) == {IELTS: 6.5, IELTS_SUB: 6.0}


# --- (b) cell phrasing in an IELTS row the v1 reader already attributes ----------

UNSW_STYLE_ROW = """<html><body><table>
<tr><th>Test</th><th>Minimum</th></tr>
<tr><td>IELTS Academic</td><td>6.5 overall (min 6.0 in each subtest)</td></tr>
</table></body></html>"""


def test_an_ielts_row_cell_with_min_in_each_subtest_gives_both(v2):
    claims, _, _ = _read_html(UNSW_STYLE_ROW)
    assert _values(claims) == {IELTS: 6.5, IELTS_SUB: 6.0}


def test_an_ielts_row_cell_with_min_in_each_subtest_flag_off_is_unchanged(v1):
    claims, tabled, _ = _read_html(UNSW_STYLE_ROW)
    assert tabled == []


def test_a_floor_above_the_overall_band_is_not_read(v2):
    claims, _, _ = _read_html(UNSW_STYLE_ROW.replace("min 6.0", "min 7.0"))
    assert claims == {}


def test_a_table_of_test_dates_under_an_ielts_heading_silences_nothing(v2):
    html = """<html><body><h3>IELTS</h3><table>
<tr><th>Test centre</th><th>Next sitting</th></tr>
<tr><th>Dublin</th><td>15 March 2027</td></tr>
<tr><th>Cork</th><td>22 March 2027</td></tr>
</table><p>Applicants need IELTS overall 6.5 with no band below 6.0.</p></body></html>"""
    text = readable_text(html)
    builder = ClaimBuilder(source_url="fixture://page", official_domain=True, page_text=text)
    assert extract_table_requirements(build_document_ir(html, "fixture://page"), builder) == []
    assert builder.english_abstained == set()
    extract_requirements(text, builder)
    got = {c.claim_type: c.normalized_value for c in builder.claims if c.claim_type in ENGLISH}
    assert got == {IELTS: 6.5, IELTS_SUB: 6.0}


def _read_html(html: str) -> tuple[dict[ClaimType, Claim], list[Claim], ClaimBuilder]:
    text = readable_text(html)
    builder = ClaimBuilder(source_url="fixture://page", official_domain=True, page_text=text)
    tabled = extract_table_requirements(build_document_ir(html, "fixture://page"), builder)
    english = [c for c in tabled if c.claim_type in ENGLISH]
    return {c.claim_type: c for c in english}, tabled, builder


def test_a_table_whose_rows_agree_needs_no_hint(v2):
    html = """<html><body><h3>IELTS Academic</h3><table>
<tr><th>Faculty</th><th>Undergraduate</th></tr>
<tr><th>Science</th><td>6.5 overall (min 6.0 in each subtest)</td></tr>
<tr><th>Engineering</th><td>6.5 overall (min 6.0 in each subtest)</td></tr>
</table></body></html>"""
    claims, _, _ = _read_html(html)
    assert _values(claims) == {IELTS: 6.5, IELTS_SUB: 6.0}


def test_a_heading_naming_two_tests_attributes_nothing(v2):
    html = """<html><body><h3>IELTS and PTE Academic</h3><table>
<tr><th>Faculty</th><th>Undergraduate</th></tr>
<tr><th>Science</th><td>6.5 overall (min 6.0 in each subtest)</td></tr>
</table></body></html>"""
    claims, tabled, _ = _read_html(html)
    assert claims == {} and tabled == []


def test_a_row_stated_in_words_counts_as_a_disagreeing_row(v2):
    # "Score of 7.0 overall" is not read, so it cannot be told apart from 6.5:
    # the readable row alone is never claimed.
    html = """<html><body><h3>IELTS Academic</h3><table>
<tr><th>Faculty</th><th>Undergraduate</th></tr>
<tr><th>Science</th><td>6.5 overall</td></tr>
<tr><th>Medicine</th><td>Score of 7.0 overall in one sitting, at most twice</td></tr>
</table></body></html>"""
    claims, _, _ = _read_html(html)
    assert claims == {}


# --- (d) TF-2: the TOEFL total, not the first number after the word -------------


def _toefl(text: str) -> object:
    return _prose(for_matching(text), None).get(TOEFL)


def test_delft_toefl_skips_the_test_date_and_the_new_band(v2):
    assert _toefl(readable_text(_page("delft_admission_requirements.html"))) == 90


def test_uppsala_toefl_skips_the_section_score_on_its_scale(v2):
    assert _toefl(readable_text(_page("uppsala_entry_requirements.html"))) == 90


def test_delft_and_uppsala_flag_off_are_unchanged(v1):
    # The first number after the word: 21 (a date) and 20 (a section score),
    # both outside 40-120, so no TOEFL claim at all.
    assert _toefl(readable_text(_page("delft_admission_requirements.html"))) is None
    assert _toefl(readable_text(_page("uppsala_entry_requirements.html"))) is None


@pytest.mark.parametrize(
    "text",
    [
        "TOEFL iBT (Before January 2026) TOEFL iBT (After January 2026) Cambridge Advanced",
        "TOEFL iBT after 21 January 2026. Tests taken from this date onwards.",
        "TOEFL iBT: 20 in each section.",
        "TOEFL iBT: a score of 79-93 is typical.",
        "TOEFL iBT: 25 in writing and 22 in reading.",
    ],
)
def test_toefl_dates_sections_and_ranges_are_no_total(v2, text):
    assert _toefl(text) is None


@pytest.mark.parametrize(
    ("text", "score"),
    [
        ("TOEFL iBT: score of 20 (scale 0-30) in written test, total score of 90", 90),
        ("TOEFL test reports obtained before January 21, 2026: a total of 88.", 88),
        ("TOEFL iBT 100 (minimum 22 in writing)", 100),
        ("A minimum score of 78 in TOEFL iBT (Centre-based)", 78),
        ("TOEFL iBT\n90.0 Overall\nMin: 22.0 in reading", 90),
        ("TOEFL iBT 90 may be accepted", 90),
    ],
)
def test_toefl_total_v2_reads_the_total(v2, text, score):
    assert _toefl(text) == score


# --- wiring: the programme page's hint reaches its English page ------------------

PROGRAMME = """<html><head><title>Computer Science - Trinity College Dublin</title></head><body>
<h1>Computer Science</h1>
<p>Bachelor in Computer Science (B.A. (Mod.)), four years, full-time.</p>
<p>All applicants to Trinity are required to provide official evidence of proficiency in the
English language. Applicants to this course are required to meet <strong>Band B (Standard
Entry)</strong> English language requirements. For more details of qualifications that meet
Band B, see the <a href="fixture://tcd/english.html">English Language Requirements</a> page.</p>
</body></html>"""


async def _verify(settings, tmp_path: Path):
    root = tmp_path / "site"
    (root / "tcd").mkdir(parents=True)
    (root / "tcd" / "programme.html").write_text(PROGRAMME, encoding="utf-8")
    (root / "tcd" / "english.html").write_text(_page("tcd_english.html"), encoding="utf-8")
    candidate = Candidate(name="TCD", country="Ireland", city="Dublin", domain="tcd.ie")
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://tcd/programme.html",
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(candidate, program, "fall 2027")


@pytest.mark.asyncio
async def test_the_adapter_reads_tcd_band_b_from_the_linked_english_page(settings, tmp_path, v2):
    result = await _verify(settings, tmp_path)
    english = {
        c.claim_type: c
        for c in result.claims
        if c.claim_type in ENGLISH and c.source_url == "fixture://tcd/english.html"
    }
    assert _values(english) == {IELTS: 6.5, IELTS_SUB: 6.0, TOEFL: 90, DUOLINGO: 120}


@pytest.mark.asyncio
async def test_the_adapter_flag_off_reads_no_minimum_from_the_tcd_english_page(
    settings, tmp_path, v1
):
    result = await _verify(settings, tmp_path)
    assert not [
        c
        for c in result.claims
        if c.claim_type in ENGLISH and c.source_url == "fixture://tcd/english.html"
    ]
