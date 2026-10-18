"""QH-1 and AN-1: two scholarship answers the funding walk lost on found pages.

Evidence-extraction analysis 2026-10-18 (base2 clean baseline, every rule on):

* QH-1 (``web_scholarships.QUOTED_HREF_GUARD``): TCD's undergraduate
  scholarships index writes five award links as ``href="&quot;/geug.php&quot;"``.
  The walk read four of them as ``.../scholarships/"/geug.php"``, and RL-1's
  read budget then refused the E3 page that describes the gold award.
* AN-1 (``page_classifier.AWARD_NAME_QUALIFIER``): Uppsala's bachelor's
  scholarships page describes "Anders Wall's Scholarship for Studies at
  Uppsala University" under its own heading; a proper award name had to end in
  the award noun, so the section was never read as an award.

Both pages are the hand-fetched originals in
``tests/fixtures/award_page_evidence/`` (source URL in each file's first
line). Each rule is pinned off (nothing changes) and on, next to the
negatives it must refuse.
"""

from __future__ import annotations

import pytest

from app.adapters import page_classifier
from app.adapters.page_classifier import proper_award_name
from app.adapters.scholarship import web_scholarships
from app.domain.enums import ClaimType
from tests.test_award_page_evidence import TCD_E3, _claims, _find, _fixture

TCD_UG_INDEX = "https://www.tcd.ie/study/international/scholarships/undergraduate"
TCD_QUOTED = [
    'https://www.tcd.ie/study/international/scholarships/"/geug.php"',
    'https://www.tcd.ie/study/international/scholarships/"/fundacaoestudar-ug.php"',
    'https://www.tcd.ie/study/international/scholarships/"/chinaug.php"',
    'https://www.tcd.ie/study/international/scholarships/"/ScholarshipsforJapaneseStudents.php"',
    'https://www.tcd.ie/study/international/scholarships/"/sport.php"',
]
UU_SCHOLARSHIPS = (
    "https://www.uu.se/en/study/bachelors-studies/scholarships/uppsala-university-scholarships"
)
ANDERS_WALL = "Anders Wall's Scholarship for Studies at Uppsala University"


# --- QH-1: quoted hrefs ----------------------------------------------------------


@pytest.mark.parametrize("on", [False, True])
def test_qh1_quoted_hrefs_on_the_tcd_index(monkeypatch, on):
    monkeypatch.setattr(web_scholarships, "QUOTED_HREF_GUARD", on)
    links = web_scholarships._award_links(
        _fixture("tcd_undergraduate_scholarships_index.html"), TCD_UG_INDEX
    )
    quoted = [link for link in links if link in TCD_QUOTED]
    assert quoted == ([] if on else TCD_QUOTED)
    # The real award links are kept either way, E3 among them.
    assert TCD_E3 in links
    assert (
        "https://www.tcd.ie/study/international/scholarships/undergraduate/"
        "dr-jonathan-chiu-and-dr-margaret-sau-sheung-ip"
    ) in links
    assert len(links) == (4 if on else 9)


@pytest.mark.parametrize(
    ("href", "kept"),
    [
        ('"/geug.php"', False),
        ("'/geug.php'", False),
        ("/awards/%22smith%22-scholarship", False),
        ("/awards/st-john's-scholarship", True),
        ("/awards/smith-scholarship", True),
    ],
)
def test_qh1_only_broken_quoting_is_refused(monkeypatch, href, kept):
    monkeypatch.setattr(web_scholarships, "QUOTED_HREF_GUARD", True)
    html = f'<html><body><main><a href="{href.replace(chr(34), "&quot;")}">Scholarship</a></main></body></html>'
    assert bool(web_scholarships._award_links(html, "https://uni.edu/scholarships")) is kept


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_qh1_the_walk_does_not_read_quoted_links(tmp_path, monkeypatch, on):
    monkeypatch.setattr(web_scholarships, "QUOTED_HREF_GUARD", on)
    pages = {
        TCD_UG_INDEX: _fixture("tcd_undergraduate_scholarships_index.html"),
        TCD_E3: _fixture("tcd_e3_scholarships_index.html"),
    }
    awards, result, site = await _find(
        tmp_path, monkeypatch, pages, on=True, domain="tcd.ie", scholarships_url=TCD_UG_INDEX
    )
    assert any(url in site.requested for url in TCD_QUOTED) is (not on)
    assert TCD_E3 in site.requested
    name = "Undergraduate E3 Balanced Solutions for a Better World Scholarship"
    assert name in [a.name for a in awards]
    international = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, name)
    assert [c.normalized_value for c in international] == [True]


# --- AN-1: a qualifier after the award noun --------------------------------------


@pytest.mark.parametrize(
    ("text", "name"),
    [
        (ANDERS_WALL, ANDERS_WALL),
        ("Smith Scholarship in Computer Science", "Smith Scholarship in Computer Science"),
        # Categories stay categories: a population, a level or no distinctive word.
        ("UNSW Scholarships for International Students", None),
        ("Global Award for Master's Students", None),
        ("Merit Scholarship for Students from Africa", None),
        ("Vice-Chancellor Scholarship for Excellence", None),
        ("Scholarship for Studies at Uppsala University", None),
        ("Sports Bursary of the Year", None),
        ("Smith Scholarship for international students", None),
        ("How to Apply for a Scholarship at Uppsala University", None),
    ],
)
def test_an1_qualified_award_names(monkeypatch, text, name):
    monkeypatch.setattr(page_classifier, "AWARD_NAME_QUALIFIER", False)
    assert proper_award_name(text) is None
    monkeypatch.setattr(page_classifier, "AWARD_NAME_QUALIFIER", True)
    assert proper_award_name(text) == name


def test_an1_names_that_end_in_the_noun_are_unchanged(monkeypatch):
    for on in (False, True):
        monkeypatch.setattr(page_classifier, "AWARD_NAME_QUALIFIER", on)
        assert proper_award_name(
            "Undergraduate E3 Balanced Solutions for a Better World Scholarship"
        ) == ("Undergraduate E3 Balanced Solutions for a Better World Scholarship")
        assert proper_award_name("Scholarships") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_an1_uppsala_award_is_read_from_its_section(tmp_path, monkeypatch, on):
    monkeypatch.setattr(page_classifier, "AWARD_NAME_QUALIFIER", on)
    pages = {UU_SCHOLARSHIPS: _fixture("uppsala_bachelors_scholarships.html")}
    awards, result, _ = await _find(
        tmp_path, monkeypatch, pages, on=True, domain="uu.se", scholarships_url=UU_SCHOLARSHIPS
    )
    exists = _claims(result, ClaimType.SCHOLARSHIP_EXISTS, ANDERS_WALL)
    if not on:
        assert exists == []
        assert ANDERS_WALL not in [a.name for a in awards]
        return
    assert [c.normalized_value for c in exists] == [ANDERS_WALL], result.errors
    assert exists[0].source_url == UU_SCHOLARSHIPS
    assert [a.name for a in awards] == [ANDERS_WALL]
    # "Citizens of a country in Africa" names a population: international
    # applicability is abstained on, never turned into a yes.
    assert _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, ANDERS_WALL) == []
