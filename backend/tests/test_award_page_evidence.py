"""AP-1: awards read from the page in hand (core-gap analysis 2026-10-18, change 1).

The four live shapes are pinned on the hand-fetched pages in
``tests/fixtures/award_page_evidence/`` (source URL in each file's first
line): Imperial's award page that its hub links made an index, UBC's and
TCD's awards described under their own headings on an index, TCD's index
refused by the index budget, and HKU CDS's scholarships page linked from the
confirmed programme page's navigation only. Each is pinned with
``AWARD_PAGE_EVIDENCE`` off (nothing changes) and on, next to the negatives
the rule must refuse.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageType, classify_page, proper_award_name
from app.adapters.scholarship import web_scholarships
from app.domain.enums import ClaimType, DegreeLevel
from tests.test_award_route import Provider
from tests.test_live_discovery import StubSite
from tests.test_scholarship_index_walk import _AWARD, _INDEX

FIXTURES = Path(__file__).parent / "fixtures" / "award_page_evidence"

IMPERIAL_AWARD = (
    "https://www.imperial.ac.uk/study/fees-and-funding/scholarships-search/"
    "imperial-inspires-scholarships-undergraduate-20272028.php"
)
IMPERIAL_INDEX = "https://www.imperial.ac.uk/study/fees-and-funding/scholarships-search"
UBC_INDEX = "https://you.ubc.ca/financial-planning/scholarships-awards-international-students"
TCD_E3 = "https://www.tcd.ie/e3/education/scholarships"
TCD_INDEX = "https://www.tcd.ie/study/international/scholarships"
HKU_PROGRAMME = (
    "https://www.cds.hku.hk/prospective-students/undergraduate-old-2026/"
    "6999-computing-and-data-science"
)
HKU_SCHOLARSHIPS = "https://www.cds.hku.hk/prospective-students/scholarships"
UNI = "https://uni.edu"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _index(title: str, links: tuple[str, ...] | list[str] = ()) -> str:
    items = "".join(
        f'<li><a href="{href}">Scholarship {i}</a></li>' for i, href in enumerate(links)
    )
    return _INDEX.format(title=title, items=items)


async def _find(
    tmp_path,
    monkeypatch,
    pages: dict[str, str],
    *,
    on: bool,
    domain: str,
    program_url: str | None = None,
    award_route: bool = False,
    allow_search: bool = True,
    program_name: str = "Computer Science",
    **candidate_kwargs,
):
    from app.adapters import search

    monkeypatch.setattr(page_classifier, "AWARD_PAGE_EVIDENCE", on)
    monkeypatch.setattr(web_scholarships, "AWARD_ROUTE", award_route)
    monkeypatch.setattr(search, "get_search_provider", lambda: Provider([]))
    site = StubSite(dict[str, bytes | str](pages))
    candidate = Candidate(
        name="Test University", country="Testland", city="Test", domain=domain, **candidate_kwargs
    )
    program = CandidateProgram(
        name=program_name,
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=program_url,
    )
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = web_scholarships.WebScholarshipAdapter(fetcher, "2027/28")
        awards, result = await adapter.find(candidate, program, None, allow_search=allow_search)
    return awards, result, site


def _claims(result, claim_type: ClaimType, subject: str) -> list:
    return [c for c in result.claims if c.claim_type is claim_type and c.subject_key == subject]


# --- proper award names ---------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("International Major Entrance Scholarship", "International Major Entrance Scholarship"),
        (
            "Imperial Inspires Scholarships (Undergraduate)",
            "Imperial Inspires Scholarships (Undergraduate)",
        ),
        (
            "1.School of Computing and Data Science Entrance Scholarship\xa0",
            "School of Computing and Data Science Entrance Scholarship",
        ),
        (
            "Undergraduate E3 Balanced Solutions for a Better World Scholarship",
            "Undergraduate E3 Balanced Solutions for a Better World Scholarship",
        ),
        ("Outstanding International Student Award", "Outstanding International Student Award"),
    ],
)
def test_a_proper_award_name_is_read_as_one(text, name):
    assert proper_award_name(text) == name


@pytest.mark.parametrize(
    "text",
    [
        # The UNSW shape: a marketing heading, not an award's name.
        "UNSW scholarships for international students",
        "Scholarships - HKU School of Computing and Data Science (HKUCDS)",
        "Scholarship Application Form",
        "Scholarship overview",
        "Merit-based awards",
        "UBC Vantage One scholarships and awards",
        "Entrance Scholarships for CDS undergraduate students",
        "International Undergraduate Scholarship",  # category words only
        "How to apply for the Riverside Scholarship",
        "About the Riverside Scholarship",
        "Is there a Riverside Scholarship?",
        "Scholarships",
        "",
    ],
)
def test_a_category_heading_is_not_an_award_name(text):
    assert proper_award_name(text) is None


# --- 1. classifier order: the named-award rule before the link count -------------


def test_off_the_imperial_award_page_is_an_index_as_before(monkeypatch):
    monkeypatch.setattr(page_classifier, "AWARD_PAGE_EVIDENCE", False)
    page = classify_page(url=IMPERIAL_AWARD, html=_fixture("imperial_inspires_award.html"))
    assert page.page_type is PageType.SCHOLARSHIP_INDEX


def test_on_the_imperial_award_page_is_that_award(monkeypatch):
    monkeypatch.setattr(page_classifier, "AWARD_PAGE_EVIDENCE", True)
    page = classify_page(url=IMPERIAL_AWARD, html=_fixture("imperial_inspires_award.html"))
    assert page.page_type is PageType.SCHOLARSHIP_AWARD
    assert page.subject == "Imperial Inspires Scholarships (Undergraduate)"


def _named_page(heading: str, links: list[tuple[str, str]]) -> str:
    anchors = "".join(f'<p><a href="{href}">{text}</a></p>' for href, text in links)
    return (
        f"<html><head><title>{heading}</title></head><body><main><h1>{heading}</h1>"
        "<p>Eligibility: open to international students. The award is worth EUR 5,000 "
        "per year and covers tuition. The deadline is 1 March 2027.</p>"
        f"{anchors}</main></body></html>"
    )


def test_on_a_named_page_filing_three_awards_below_itself_stays_an_index(monkeypatch):
    monkeypatch.setattr(page_classifier, "AWARD_PAGE_EVIDENCE", True)
    url = f"{UNI}/scholarships/riverside-scholarships"
    html = _named_page(
        "Riverside Scholarships",
        [(f"{url}/{slug}", f"{slug.title()} Scholarship") for slug in ("arts", "law", "science")],
    )
    assert classify_page(url=url, html=html).page_type is PageType.SCHOLARSHIP_INDEX


def test_on_a_marketing_heading_with_award_links_stays_an_index(monkeypatch):
    monkeypatch.setattr(page_classifier, "AWARD_PAGE_EVIDENCE", True)
    url = "https://www.unsw.edu.au/study/your-future/international-scholarships"
    html = _named_page(
        "UNSW scholarships for international students",
        [(f"{UNI}/a", "Global Academic Scholarship"), (f"{UNI}/b", "Merit Scholarship")],
    )
    assert classify_page(url=url, html=html).page_type is PageType.SCHOLARSHIP_INDEX


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_the_imperial_award_page_is_read_as_its_award_only_with_the_flag(
    tmp_path, monkeypatch, on
):
    awards, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {
            IMPERIAL_INDEX: _index("Search our scholarships", [IMPERIAL_AWARD]),
            IMPERIAL_AWARD: _fixture("imperial_inspires_award.html"),
        },
        on=on,
        domain="imperial.ac.uk",
        scholarships_url=IMPERIAL_INDEX,
    )
    name = "Imperial Inspires Scholarships (Undergraduate)"
    exists = _claims(result, ClaimType.SCHOLARSHIP_EXISTS, name)
    if not on:
        assert not exists and name not in [a.name for a in awards]
        return
    assert [c.normalized_value for c in exists] == [name]
    assert exists[0].source_url == IMPERIAL_AWARD
    international = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, name)
    assert [c.normalized_value for c in international] == [True]
    assert "international applicants" in international[0].original_text_excerpt
    # "(for MBBS, the UCAS application deadline is 15 October 2026.)" is
    # another route's deadline quoted in passing, not the award's.
    assert not _claims(result, ClaimType.SCHOLARSHIP_DEADLINE, name)


@pytest.mark.asyncio
async def test_on_with_ar1_the_imperial_evidence_is_one_eligibility_sentence(tmp_path, monkeypatch):
    _, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {
            IMPERIAL_INDEX: _index("Search our scholarships", [IMPERIAL_AWARD]),
            IMPERIAL_AWARD: _fixture("imperial_inspires_award.html"),
        },
        on=True,
        award_route=True,
        domain="imperial.ac.uk",
        scholarships_url=IMPERIAL_INDEX,
    )
    name = "Imperial Inspires Scholarships (Undergraduate)"
    international = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, name)
    assert [c.original_text_excerpt for c in international] == [
        "Scholarships are available to outstanding international applicants for "
        "undergraduate courses."
    ]


# --- 2. award sections on an index -----------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("award_route", [False, True])
async def test_on_ubc_imes_is_read_from_its_section_of_the_index(
    tmp_path, monkeypatch, award_route
):
    awards, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {UBC_INDEX: _fixture("ubc_international_scholarships_index.html")},
        on=True,
        award_route=award_route,
        domain="ubc.ca",
        scholarships_url=UBC_INDEX,
    )
    name = "International Major Entrance Scholarship"
    exists = _claims(result, ClaimType.SCHOLARSHIP_EXISTS, name)
    assert [c.normalized_value for c in exists] == [name], result.errors
    assert exists[0].source_url == UBC_INDEX
    assert "awarded to exceptional international students" in exists[0].original_text_excerpt
    international = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, name)
    assert [c.normalized_value for c in international] == [True]
    # Existence and international applicability only: the section's
    # "$10,000 – $25,000/year" and "renewable for up to three additional
    # years" are not read from an index.
    assert {c.claim_type for c in result.claims if c.subject_key == name} == {
        ClaimType.SCHOLARSHIP_EXISTS,
        ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE,
    }
    imes = next(a for a in awards if a.name == name)
    assert imes.coverage == [] and imes.amount is None
    # Its programme and campus scope are not verified, so never "eligible".
    assert imes.applicant_eligible == "unknown"
    # Sections with no eligibility sentence record nothing.
    assert not any(a.name.startswith("UBC Okanagan") for a in awards)


@pytest.mark.asyncio
async def test_off_the_ubc_index_records_no_award_from_its_own_text(tmp_path, monkeypatch):
    awards, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {UBC_INDEX: _fixture("ubc_international_scholarships_index.html")},
        on=False,
        domain="ubc.ca",
        scholarships_url=UBC_INDEX,
    )
    assert awards == []
    assert not [c for c in result.claims if c.claim_type is ClaimType.SCHOLARSHIP_EXISTS]


# --- AP-1b: a section award's scope ----------------------------------------------


@pytest.mark.asyncio
async def test_on_ubc_imes_carries_the_index_degree_and_no_related_programme(tmp_path, monkeypatch):
    # Paired run 39146095965: the confirmed programme page was UBC's related
    # BA ("Computer Science Vancouver Ba") for a BSc request, and the IMES
    # claims read off the international index inherited its name with no
    # degree -- wrong_scope against the gold {"degree": "bachelor",
    # "programme": null}. The index states the level itself: its title is
    # "... | Undergraduate Programs and Admissions" and IMES is for students
    # "entering undergraduate programs".
    ba = "https://you.ubc.ca/programs/computer-science-vancouver-ba"
    _, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {UBC_INDEX: _fixture("ubc_international_scholarships_index.html")},
        on=True,
        domain="ubc.ca",
        scholarships_url=UBC_INDEX,
        program_url=ba,
        program_name="Computer Science Vancouver Ba",
    )
    names = ("International Major Entrance Scholarship", "Outstanding International Student Award")
    claims = [
        c
        for name in names
        for kind in (ClaimType.SCHOLARSHIP_EXISTS, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE)
        for c in _claims(result, kind, name)
    ]
    kinds = {(c.subject_key, c.claim_type) for c in claims}
    assert {
        (names[0], ClaimType.SCHOLARSHIP_EXISTS),
        (names[0], ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE),
        (names[1], ClaimType.SCHOLARSHIP_EXISTS),
    } <= kinds, result.errors
    for claim in claims:
        assert claim.program is None
        assert claim.scope is not None
        assert claim.scope.programme is None
        assert claim.scope.degree == "bachelor"


_NEUTRAL_INDEX = """<html><head><title>Scholarships</title></head><body><main>
<h1>Scholarships</h1>
<p>Overview of scholarships available to our students, with links to each one.</p>
<h2>Riverside Global Scholarship</h2>
<p>The Riverside Global Scholarship is open to international students.</p>
</main></body></html>"""


@pytest.mark.parametrize(
    ("name", "statement", "degree"),
    [
        ("Riverside Entrance Scholarship", "It is open to international students.", "bachelor"),
        ("Riverside Global Award", "It is open to international undergraduates.", "bachelor"),
        (
            "Riverside Global Award",
            "It is open to undergraduate and graduate international students.",
            None,
        ),
        ("Graduate Entrance Scholarship", "It is open to international students.", "master"),
    ],
)
def test_a_sections_own_words_state_its_degree(name, statement, degree):
    section = web_scholarships.AwardSection(name, (statement,))
    assert web_scholarships._section_degree(section, _NEUTRAL_INDEX, None) == degree


def test_a_section_takes_the_index_title_degree_before_the_request():
    section = web_scholarships.AwardSection(
        "Riverside Global Scholarship", ("It is open to international students.",)
    )
    page = _NEUTRAL_INDEX.replace("<title>Scholarships", "<title>Postgraduate scholarships")
    assert web_scholarships._section_degree(section, page, "bachelor") == "master"
    assert web_scholarships._section_degree(section, _NEUTRAL_INDEX, "bachelor") == "bachelor"
    assert web_scholarships._section_degree(section, _NEUTRAL_INDEX, None) is None


@pytest.mark.asyncio
async def test_on_an_index_found_off_the_route_does_not_take_the_requests_degree(
    tmp_path, monkeypatch
):
    index = f"{UNI}/scholarships"
    _, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {index: _NEUTRAL_INDEX},
        on=True,
        domain="uni.edu",
        scholarships_url=index,
    )
    exists = _claims(result, ClaimType.SCHOLARSHIP_EXISTS, "Riverside Global Scholarship")
    assert len(exists) == 1, result.errors
    assert exists[0].program is None
    assert exists[0].scope is not None
    assert exists[0].scope.degree is None


@pytest.mark.asyncio
async def test_on_an_index_reached_from_the_confirmed_programme_takes_its_degree(
    tmp_path, monkeypatch
):
    programme = f"{UNI}/bachelors/computer-science"
    index = f"{UNI}/scholarships"
    _, result, site = await _find(
        tmp_path,
        monkeypatch,
        {programme: _programme_page((index, "Scholarships")), index: _NEUTRAL_INDEX},
        on=True,
        domain="uni.edu",
        program_url=programme,
    )
    assert index in site.requested
    exists = _claims(result, ClaimType.SCHOLARSHIP_EXISTS, "Riverside Global Scholarship")
    assert len(exists) == 1, result.errors
    assert exists[0].program is None
    assert exists[0].scope is not None
    assert (exists[0].scope.degree, exists[0].scope.programme) == ("bachelor", None)


def _tcd_pages(sub_indexes: int) -> dict[str, str]:
    subs = [f"{TCD_INDEX}/undergraduate-{i}" for i in range(sub_indexes)]
    pages = {TCD_INDEX: _index("Scholarships", [*subs, TCD_E3])}
    pages.update({sub: _index("Undergraduate Scholarships") for sub in subs})
    pages[TCD_E3] = _fixture("tcd_e3_scholarships_index.html")
    return pages


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_the_depth0_index_is_not_charged_to_the_index_budget(tmp_path, monkeypatch, on):
    # Off: the central index, two sub-indexes, and E3 is "beyond the index
    # budget". On: the depth-0 read is free, so E3 is the third index read.
    _, result, site = await _find(
        tmp_path, monkeypatch, _tcd_pages(2), on=on, domain="tcd.ie", scholarships_url=TCD_INDEX
    )
    assert TCD_E3 in site.requested
    refused = [
        o
        for o in result.page_outcomes
        if o.url == TCD_E3 and o.detail.startswith("index page beyond the index budget")
    ]
    assert bool(refused) is (not on)


@pytest.mark.asyncio
@pytest.mark.parametrize("sub_indexes", [2, 4])
async def test_on_tcd_e3_undergraduate_award_is_read_from_its_section(
    tmp_path, monkeypatch, sub_indexes
):
    # With four sub-indexes E3 is past the budget even on: its links are not
    # followed, but the awards it describes itself are already in hand.
    awards, result, _ = await _find(
        tmp_path,
        monkeypatch,
        _tcd_pages(sub_indexes),
        on=True,
        domain="tcd.ie",
        scholarships_url=TCD_INDEX,
    )
    name = "Undergraduate E3 Balanced Solutions for a Better World Scholarship"
    assert [c.normalized_value for c in _claims(result, ClaimType.SCHOLARSHIP_EXISTS, name)] == [
        name
    ], result.errors
    international = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, name)
    assert [c.normalized_value for c in international] == [True]
    assert international[0].original_text_excerpt.startswith(
        "Who can apply: Applicants who have non-EU status"
    )
    assert international[0].source_url == TCD_E3
    # The postgraduate award on the same page is not this request's level.
    assert [a.name for a in awards] == [name]
    assert any("Postgraduate E3" in e and "another degree level" in e for e in result.errors)


_SECTIONS_INDEX = """<html><head><title>Scholarships for international students</title></head>
<body><main>
<h1>Scholarships for international students</h1>
<p>Overview of scholarships available to our students, with links to each one.</p>
<h2>Bright Future Scholarship</h2>
<p>The Bright Future Scholarship is a full ride and is open to international students.</p>
<table><tr><td>Tuition</td><td>Covered</td></tr><tr><td>Housing</td><td>Covered</td></tr>
<tr><td>Meals</td><td>Covered</td></tr></table>
<p>The award is worth EUR 30,000 per year and the scholarship deadline is 1 March 2027.</p>
<h2>Kazakhstan Friendship Scholarship</h2>
<p>This scholarship is open to international students from Kazakhstan.</p>
<h2>Home Student Bursary</h2>
<p>The bursary is available to home students only.</p>
<h2>Faculty of Law Excellence Award</h2>
<p>The award is open only to students in the Faculty of Law.</p>
<h2>Scholarships for international students</h2>
<p>Several awards are open to international students.</p>
<h2>Riverside Merit Award</h2>
<p>A merit award of EUR 2,000 for strong applicants.</p>
<h2>Postgraduate Research Scholarship</h2>
<p>The award is open to international students starting a doctorate.</p>
</main></body></html>"""


@pytest.mark.asyncio
async def test_on_section_awards_keep_the_audit_invariants(tmp_path, monkeypatch):
    awards, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {f"{UNI}/scholarships": _SECTIONS_INDEX},
        on=True,
        domain="uni.edu",
        scholarships_url=f"{UNI}/scholarships",
    )
    by_name = {a.name: a for a in awards}

    # "Full ride" earns nothing: no coverage, amount or deadline from a section.
    bright = by_name["Bright Future Scholarship"]
    assert bright.coverage == [] and bright.amount is None and bright.deadline is None
    assert {c.claim_type for c in result.claims if c.subject_key == bright.name} == {
        ClaimType.SCHOLARSHIP_EXISTS,
        ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE,
    }

    # A named population is not "international applicants in general".
    friendship = "Kazakhstan Friendship Scholarship"
    assert friendship in by_name
    assert not _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, friendship)
    assert by_name[friendship].international_eligible == "unknown"

    # A domestic-only award is a no, and the applicant is not eligible.
    home = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, "Home Student Bursary")
    assert [c.normalized_value for c in home] == [False]
    assert by_name["Home Student Bursary"].applicant_eligible == "no"

    # Another faculty, another level, a category heading and a section with
    # no eligibility sentence claim nothing.
    for absent in (
        "Faculty of Law Excellence Award",
        "Postgraduate Research Scholarship",
        "Scholarships for international students",
        "Riverside Merit Award",
    ):
        assert absent not in by_name
        assert not [c for c in result.claims if c.subject_key == absent]
    assert set(by_name) == {"Bright Future Scholarship", friendship, "Home Student Bursary"}


@pytest.mark.asyncio
async def test_off_the_same_index_records_nothing(tmp_path, monkeypatch):
    awards, result, _ = await _find(
        tmp_path,
        monkeypatch,
        {f"{UNI}/scholarships": _SECTIONS_INDEX},
        on=False,
        domain="uni.edu",
        scholarships_url=f"{UNI}/scholarships",
    )
    assert awards == [] and result.claims == []


# --- 3. navigation "Scholarships" link of the confirmed programme page -----------


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_hku_cds_scholarships_are_reached_from_the_programme_pages_navigation(
    tmp_path, monkeypatch, on
):
    awards, result, site = await _find(
        tmp_path,
        monkeypatch,
        {
            HKU_PROGRAMME: _fixture("hku_cds_programme.html"),
            HKU_SCHOLARSHIPS: _fixture("hku_cds_scholarships.html"),
        },
        on=on,
        domain="hku.hk",
        program_url=HKU_PROGRAMME,
    )
    assert (HKU_SCHOLARSHIPS in site.requested) is on
    if not on:
        assert awards == []
        return
    name = "School of Computing and Data Science Entrance Scholarship"
    exists = _claims(result, ClaimType.SCHOLARSHIP_EXISTS, name)
    assert [c.normalized_value for c in exists] == [name], result.errors
    assert exists[0].source_url == HKU_SCHOLARSHIPS
    # The page is a page of awards, not one award named after its title.
    assert "Scholarships - HKU School of Computing and Data Science (HKUCDS)" not in [
        a.name for a in awards
    ]
    # "local and international students" is in the page's introduction, not
    # in this award's section: no eligibility sentence, no claim.
    assert not _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, name)
    # The master's awards on the same page are not this request's level.
    assert "CDS Master Programmes Entrance Scholarship" not in [a.name for a in awards]


def _programme_page(*links: tuple[str, str], content_link: str = "") -> str:
    nav = "".join(f'<li><a href="{href}">{text}</a></li>' for href, text in links)
    content = f'<p><a href="{content_link}">Riverside Scholarship</a></p>' if content_link else ""
    return (
        "<html><head><title>BSc Computer Science</title></head><body>"
        f"<nav><ul>{nav}</ul></nav><main><h1>BSc Computer Science</h1>"
        "<p>A three-year bachelor programme in computer science with a strong focus on "
        "software, systems and theory, taught in English on the main campus. Students take "
        "core modules in the first two years and choose electives in the final year.</p>"
        f"{content}</main></body></html>"
    )


@pytest.mark.asyncio
async def test_on_a_navigation_link_to_another_domain_is_not_followed(tmp_path, monkeypatch):
    programme = f"{UNI}/bachelors/computer-science"
    _, _, site = await _find(
        tmp_path,
        monkeypatch,
        {
            programme: _programme_page(
                ("https://scholarships.other.org/scholarships", "Scholarships")
            )
        },
        on=True,
        domain="uni.edu",
        program_url=programme,
    )
    assert site.requested == [programme]


@pytest.mark.asyncio
async def test_on_the_navigation_is_not_read_when_the_content_links_an_award(tmp_path, monkeypatch):
    programme = f"{UNI}/bachelors/computer-science"
    award = f"{UNI}/scholarships/riverside"
    _, _, site = await _find(
        tmp_path,
        monkeypatch,
        {programme: _programme_page((f"{UNI}/scholarships", "Scholarships"), content_link=award)},
        on=True,
        domain="uni.edu",
        program_url=programme,
    )
    assert award in site.requested
    assert f"{UNI}/scholarships" not in site.requested


@pytest.mark.asyncio
async def test_on_an_unconfirmed_programme_pages_navigation_is_not_followed(tmp_path, monkeypatch):
    programme = f"{UNI}/bachelors/computer-science"
    _, _, site = await _find(
        tmp_path,
        monkeypatch,
        {programme: _programme_page((f"{UNI}/scholarships", "Scholarships"))},
        on=True,
        domain="uni.edu",
        program_url=programme,
        allow_search=False,
    )
    assert site.requested == [programme]


def test_the_closest_navigation_scholarships_link_wins():
    candidate = Candidate(name="HKU", country="Hong Kong", city="Hong Kong", domain="hku.hk")
    html = _programme_page(
        ("https://www.hku.hk/scholarships/", "Scholarships"),
        ("https://www.cds.hku.hk/prospective-students/scholarships/", "Scholarships"),
        ("https://www.cds.hku.hk/prospective-students/fees", "Fees and scholarships"),
    )
    assert web_scholarships._navigation_scholarships_link(html, HKU_PROGRAMME, candidate) == (
        HKU_SCHOLARSHIPS
    )


def test_a_section_without_an_eligibility_sentence_records_nothing():
    adapter = web_scholarships.WebScholarshipAdapter(None, "2027/28")  # type: ignore[arg-type]
    section = web_scholarships.AwardSection(
        "Riverside Merit Award", ("A merit award of EUR 2,000 for strong applicants.",)
    )
    candidate = Candidate(name="Uni", country="Testland", city="Test", domain="uni.edu")
    program = CandidateProgram(name="CS", field="computer science", degree=DegreeLevel.BACHELOR)
    assert (
        adapter._parse_award_section(
            candidate, program, f"{UNI}/s", _SECTIONS_INDEX, datetime.now(UTC), section
        )
        is None
    )


@pytest.mark.asyncio
async def test_on_an_awards_own_page_replaces_its_section(tmp_path, monkeypatch):
    award = f"{UNI}/scholarships/riverside-global"
    index = (
        "<html><head><title>Scholarships</title></head><body><main><h1>Scholarships</h1>"
        "<p>Overview of scholarships available to our students, each with its own page.</p>"
        "<h2>Riverside Global Scholarship</h2>"
        "<p>The Riverside Global Scholarship is open to international students.</p>"
        f'<p><a href="{award}">Riverside Global Scholarship</a></p>'
        "</main></body></html>"
    )
    awards, result, site = await _find(
        tmp_path,
        monkeypatch,
        {f"{UNI}/scholarships": index, award: _AWARD.format(name="Riverside Global Scholarship")},
        on=True,
        domain="uni.edu",
        scholarships_url=f"{UNI}/scholarships",
    )
    assert award in site.requested
    assert [(a.name, a.source_urls) for a in awards] == [("Riverside Global Scholarship", [award])]
    # Both statements stay as evidence; only the record is the award page's.
    sources = {
        c.source_url
        for c in _claims(result, ClaimType.SCHOLARSHIP_EXISTS, "Riverside Global Scholarship")
    }
    assert sources == {f"{UNI}/scholarships", award}
