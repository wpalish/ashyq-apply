"""SC-2 (``web_requirements.COORDINATED_DEGREE_SCOPE``): coordinated degree words scope a page too.

dev3 base2 clean baseline (2026-10-18): UNSW's English requirements page was
reached from the confirmed bachelor's programme page and read for English
(EN-2 picked the Engineering / Undergraduate cell, "6.5 overall (min 6.0 in
each subtest)"), then QR-1 withheld every claim: the page's one degree phrase
is "If you are applying for an undergraduate and postgraduate course", and
only "postgraduate course" was read, so the page scoped itself to master's.
A page naming two levels is silent on its degree; the bachelor's row it was
read for then stands, with the linking programme page's degree.

The fixture is the EN-2 UNSW fixture plus the English Waiver text of the same
page, verbatim (fetched by hand 2026-10-18).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.adapters import scope_reader
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import html_title, readable_text
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scope_reader import read_scope
from app.domain.enums import ClaimType, DegreeLevel

FIXTURES = Path(__file__).parent / "fixtures"
UNSW_ENGLISH = FIXTURES / "coordinated_degree_scope" / "unsw_english.html"
UNSW_PROGRAMME = FIXTURES / "english_readers_v2" / "unsw_programme.html"
#: The live programme page's link to the English page, verbatim but for the href.
ENGLISH_LINK = (
    '<p>For more details, visit the <a href="fixture://unsw/english.html" '
    'data-click_category="TextComponentRichText" data-click_id="text_English Language '
    'Requirements" data-click_title="RichText" data-click_name="English Language '
    'Requirements">English Language Requirements</a> page. </p>'
)


@pytest.fixture
def sc2(monkeypatch):
    monkeypatch.setattr(web_requirements, "COORDINATED_DEGREE_SCOPE", True)


@pytest.fixture
def sc1(monkeypatch):
    monkeypatch.setattr(web_requirements, "COORDINATED_DEGREE_SCOPE", False)


def _page_scope(coordinated: bool):
    html = UNSW_ENGLISH.read_text(encoding="utf-8")
    return read_scope(readable_text(html), title=html_title(html), coordinated_degrees=coordinated)


def _scope(text: str):
    return read_scope(text, coordinated_degrees=True)


def test_flag_is_on_by_default():
    assert web_requirements.COORDINATED_DEGREE_SCOPE is True


def test_unsw_english_page_default_reading_scopes_itself_to_master():
    assert _page_scope(False).degree == "master"
    # The default is the old reading: every caller but SC-2's is unchanged.
    html = UNSW_ENGLISH.read_text(encoding="utf-8")
    assert read_scope(readable_text(html), title=html_title(html)) == _page_scope(False)


def test_unsw_english_page_coordinated_reading_is_silent_on_its_degree():
    off, on = _page_scope(False), _page_scope(True)
    assert on.degree is None
    # Nothing else the page states changes.
    assert on == replace(off, degree=None)


@pytest.mark.parametrize(
    "text",
    [
        "If you are applying for an undergraduate and postgraduate course, apply here.",
        "Each bachelor's, master's or PhD programme has one form.",
        "This applies to undergraduate or postgraduate students.",
        "Undergraduate/postgraduate applicants submit one form.",
    ],
)
def test_coordinated_levels_are_silence(text):
    assert _scope(text).degree is None
    assert read_scope(text).degree is not None


@pytest.mark.parametrize(
    ("text", "degree"),
    [
        # One level, as before.
        ("Our master's programme in Computer Science.", "master"),
        # A qualification held is not the page's audience: a bare "degree" after
        # the list adds nothing, so the page keeps the level it names elsewhere.
        (
            "Applicants to this master's programme hold an undergraduate or postgraduate degree.",
            "master",
        ),
        # A negated coordinated word does not count.
        ("Not available to bachelor and master students; doctoral students apply.", None),
    ],
)
def test_single_levels_are_unchanged(text, degree):
    assert _scope(text).degree == degree


def test_without_a_noun_nothing_is_coordinated():
    # "undergraduate and postgraduate" with no programme/course/students noun
    # scopes nothing, as a bare degree word never did.
    assert _scope("We teach undergraduate and postgraduate.").degree is None
    assert scope_reader._coordinated_degrees("We teach undergraduate and postgraduate.") == []


async def _verify(settings, tmp_path: Path):
    root = tmp_path / "site"
    (root / "unsw").mkdir(parents=True)
    programme = UNSW_PROGRAMME.read_text(encoding="utf-8").replace(
        "</main>", f"{ENGLISH_LINK}\n</main>"
    )
    (root / "unsw" / "programme.html").write_text(programme, encoding="utf-8")
    (root / "unsw" / "english.html").write_text(
        UNSW_ENGLISH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidate = Candidate(
        name="The University of New South Wales",
        country="Australia",
        city="Sydney",
        domain="unsw.edu.au",
    )
    program = CandidateProgram(
        name="Bachelor of Science (Computer Science)",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://unsw/programme.html",
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(candidate, program, "fall 2027")


def _english(result) -> dict[ClaimType, object]:
    return {
        c.claim_type: c
        for c in result.claims
        if c.source_url == "fixture://unsw/english.html"
        and c.claim_type
        in (ClaimType.IELTS_MIN_OVERALL, ClaimType.IELTS_MIN_SUBSCORE, ClaimType.TOEFL_MIN_TOTAL)
    }


@pytest.mark.asyncio
async def test_adapter_flag_off_withholds_the_unsw_english_page(settings, tmp_path, sc1):
    result = await _verify(settings, tmp_path)
    assert _english(result) == {}
    assert any(
        "fixture://unsw/english.html: QR-1: the page scopes itself to another degree level" in e
        for e in result.errors
    )


@pytest.mark.asyncio
async def test_adapter_flag_on_keeps_the_engineering_undergraduate_row(settings, tmp_path, sc2):
    result = await _verify(settings, tmp_path)
    english = _english(result)
    assert {t: c.normalized_value for t, c in english.items()} == {
        ClaimType.IELTS_MIN_OVERALL: 6.5,
        ClaimType.IELTS_MIN_SUBSCORE: 6.0,
        ClaimType.TOEFL_MIN_TOTAL: 90,
    }
    ielts = english[ClaimType.IELTS_MIN_OVERALL]
    assert ielts.original_text_excerpt == "Engineering 6.5 overall (min 6.0 in each subtest)"
    # The page is silent on its degree; the linking programme page's bachelor's stands.
    assert ielts.scope is not None and ielts.scope.degree == "bachelor"
    assert "degree from the linking programme page" in ielts.notes
