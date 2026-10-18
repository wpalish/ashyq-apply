"""AR-1: scholarship discovery as its own route (structural analysis 2026-10-18, change 3).

Each of the four parts is pinned twice: with ``AWARD_ROUTE`` on, and with it
off, where the walk must behave exactly as before.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.scholarship import web_scholarships
from app.adapters.search.base import SearchResponse, SearchResult
from app.domain.enums import ClaimType, DegreeLevel
from tests.test_live_discovery import StubSite
from tests.test_scholarship_index_walk import _AWARD, _INDEX

UNI = "https://uni.edu"
PROGRAMME = f"{UNI}/bachelors/computer-science"
INDEX = f"{UNI}/funding"


class Provider:
    name = "fake"

    def __init__(self, urls: list[str]) -> None:
        self.urls = urls
        self.calls: list[dict] = []

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        now = datetime.now(UTC)
        return SearchResponse(
            kwargs["query"],
            self.name,
            now,
            tuple(
                SearchResult(url, "Scholarship", self.name, i + 1, now)
                for i, url in enumerate(self.urls)
            ),
        )


def _index(title: str, links: list[tuple[str, str]]) -> str:
    items = "".join(f'<li><a href="{href}">{text}</a></li>' for href, text in links)
    return _INDEX.format(title=title, items=items)


def _award_page(name: str, *paragraphs: str) -> str:
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return (
        f"<html><head><title>{name}</title></head><body><main><h1>{name}</h1>"
        f"<p>The {name} covers full tuition for the first year of study.</p>{body}"
        "<p>The award is worth EUR 12,000 per year and the deadline is 1 March 2027.</p>"
        "</main></body></html>"
    )


async def _run(
    tmp_path,
    monkeypatch,
    pages: dict[str, str],
    *,
    on: bool,
    provider: Provider | None = None,
    allow_search: bool = True,
    program: CandidateProgram | None = None,
    **candidate_kwargs,
):
    from app.adapters import search

    monkeypatch.setattr(web_scholarships, "AWARD_ROUTE", on)
    monkeypatch.setattr(web_scholarships, "SEARCH_FUNDING_FALLBACK", True)
    monkeypatch.setattr(search, "get_search_provider", lambda: provider or Provider([]))
    site = StubSite(dict[str, bytes | str](pages))
    candidate = Candidate(
        name="Test University",
        country="Testland",
        city="Test",
        domain="uni.edu",
        **candidate_kwargs,
    )
    program = program or CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=PROGRAMME,
    )
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = web_scholarships.WebScholarshipAdapter(fetcher, "2026/27")
        awards, result = await adapter.find(candidate, program, None, allow_search=allow_search)
    return awards, result, site


# --- 1. index from the programme page's official links first -----------------

_PROGRAMME_HTML = (
    "<html><head><title>BSc Computer Science</title></head><body><main>"
    "<h1>BSc Computer Science</h1><p>A three-year bachelor programme.</p>"
    f'<a href="{UNI}/postgraduate/scholarships">Postgraduate scholarships</a>'
    '<a href="https://other.org/scholarships">External scholarships</a>'
    f'<a href="{UNI}/scholarships/international-entrance">'
    "Scholarships and awards for international students</a>"
    "</main></body></html>"
)
_ROUTE_PAGES = {
    PROGRAMME: _PROGRAMME_HTML,
    INDEX: _index("Scholarships", []),
    f"{UNI}/scholarships/international-entrance": _AWARD.format(
        name="International Entrance Scholarship"
    ),
    f"{UNI}/postgraduate/scholarships": _AWARD.format(name="Postgraduate Scholarship"),
}


@pytest.mark.asyncio
async def test_on_the_programme_pages_funding_link_is_read_first(tmp_path, monkeypatch):
    awards, result, site = await _run(
        tmp_path, monkeypatch, dict(_ROUTE_PAGES), on=True, scholarships_url=INDEX
    )
    assert site.requested[:2] == [PROGRAMME, f"{UNI}/scholarships/international-entrance"]
    assert [a.name for a in awards] == ["International Entrance Scholarship"], result.errors
    # Degree-level guard and the official-domain rule.
    assert f"{UNI}/postgraduate/scholarships" not in site.requested
    assert "https://other.org/scholarships" not in site.requested


@pytest.mark.asyncio
async def test_off_the_scholarships_url_is_read_first_as_before(tmp_path, monkeypatch):
    _, _, site = await _run(
        tmp_path, monkeypatch, dict(_ROUTE_PAGES), on=False, scholarships_url=INDEX
    )
    assert site.requested[0] == INDEX


@pytest.mark.asyncio
async def test_on_an_unconfirmed_programme_page_is_not_a_route(tmp_path, monkeypatch):
    _, _, site = await _run(
        tmp_path,
        monkeypatch,
        dict(_ROUTE_PAGES),
        on=True,
        allow_search=False,
        scholarships_url=INDEX,
    )
    assert site.requested[0] == INDEX


@pytest.mark.asyncio
async def test_on_the_admissions_hub_supplies_the_route_when_the_programme_page_does_not(
    tmp_path, monkeypatch
):
    hub = f"{UNI}/admissions"
    pages = {
        PROGRAMME: "<html><body><main><h1>BSc Computer Science</h1></main></body></html>",
        hub: (
            "<html><body><main><h1>Admissions</h1>"
            '<a href="/financial-aid/undergraduate">Financial aid</a></main></body></html>'
        ),
        f"{UNI}/financial-aid/undergraduate": _index(
            "Financial aid", [("/scholarships/global", "Global Scholarship")]
        ),
        f"{UNI}/scholarships/global": _AWARD.format(name="Global Scholarship"),
    }
    awards, result, site = await _run(tmp_path, monkeypatch, pages, on=True, admissions_url=hub)
    assert site.requested[:3] == [PROGRAMME, hub, f"{UNI}/financial-aid/undergraduate"]
    assert [a.name for a in awards] == ["Global Scholarship"], result.errors


def test_route_links_skip_other_levels_tracking_and_third_parties():
    candidate = Candidate(name="T", country="X", city="Y", domain="uni.edu")
    html = (
        "<main>"
        '<a href="/news/scholarship-winners">Scholarship winners announced</a>'
        '<a href="https://massmailer.uni.edu/c/123">Scholarships</a>'
        '<a href="/masters/funding">Funding</a>'
        '<a href="/funding">Funding your studies</a>'
        '<a href="/undergraduate/scholarships">Undergraduate scholarships</a>'
        "</main>"
    )
    links = web_scholarships._funding_route_links(html, PROGRAMME, candidate, "bachelor")
    assert links == [f"{UNI}/undergraduate/scholarships", f"{UNI}/funding"]


# --- 2. index budget by shape ------------------------------------------------

_SUBS = ("alpha", "beta", "gamma", "international", "undergraduate")


def _budget_pages() -> dict[str, str]:
    pages = {
        PROGRAMME: "<html><body><main><h1>BSc Computer Science</h1></main></body></html>",
        INDEX: _index(
            "Scholarships",
            [(f"/funding/{s}-scholarships", f"{s.title()} scholarships") for s in _SUBS],
        ),
    }
    for sub in _SUBS:
        own = f"/funding/{sub}-scholarships"
        names = [f"{sub.title()} Prize {n}" for n in ("One", "Two", "Three")]
        pages[UNI + own] = _index(
            f"{sub.title()} scholarships",
            [(f"{own}/{n.lower().replace(' ', '-')}-scholarship", n) for n in names],
        )
        for n in names:
            pages[f"{UNI}{own}/{n.lower().replace(' ', '-')}-scholarship"] = _AWARD.format(name=n)
    return pages


def _indexes_read(result) -> list[str]:
    """Sub-indexes read as funding indexes (fetched and followed), in order."""
    return [
        o.url.rsplit("/", 1)[1]
        for o in result.page_outcomes
        if o.url.endswith("-scholarships") and o.detail.startswith("read as a funding index")
    ]


@pytest.mark.asyncio
async def test_on_shaped_sub_indexes_first_and_five_productive_reads(tmp_path, monkeypatch):
    _, result, _ = await _run(
        tmp_path, monkeypatch, _budget_pages(), on=True, scholarships_url=INDEX
    )
    read = _indexes_read(result)
    assert read[:2] == ["international-scholarships", "undergraduate-scholarships"], result.errors
    # The main index plus four sub-indexes: five index reads.
    assert len(read) == 4


@pytest.mark.asyncio
async def test_off_three_index_reads_in_link_order(tmp_path, monkeypatch):
    _, result, _ = await _run(
        tmp_path, monkeypatch, _budget_pages(), on=False, scholarships_url=INDEX
    )
    assert _indexes_read(result) == ["alpha-scholarships", "beta-scholarships"]


@pytest.mark.asyncio
async def test_on_an_unproductive_index_keeps_the_old_budget(tmp_path, monkeypatch):
    pages = _budget_pages()
    # The first shaped sub-index links nothing new.
    pages[f"{UNI}/funding/international-scholarships"] = _index(
        "International scholarships", [("/funding", "All scholarships")]
    )
    _, result, _ = await _run(tmp_path, monkeypatch, pages, on=True, scholarships_url=INDEX)
    # The main index and two sub-indexes: the old budget of three.
    assert len(_indexes_read(result)) == 2


# --- 3. award query rewrite and shape filter ---------------------------------

_SEARCH_RESULTS = [
    "https://massmailer.uni.edu/c/scholarship-newsletter",
    f"{UNI}/news/2026/scholarship-winners",
    f"{UNI}/study/country/lesotho",
    f"{UNI}/files/brochure.pdf",
    f"{UNI}/scholarships/guide.pdf",
    f"{UNI}/global-scholarship",
]


def _search_pages() -> dict[str, str]:
    return {
        PROGRAMME: "<html><body><main><h1>BSc Computer Science</h1></main></body></html>",
        INDEX: "<h1>Scholarships</h1><form>JS results loading</form>",
        f"{UNI}/global-scholarship": _AWARD.format(name="Global Scholarship"),
    }


@pytest.mark.asyncio
async def test_on_the_award_query_names_the_institution_and_drops_off_shape_results(
    tmp_path, monkeypatch
):
    provider = Provider(list(_SEARCH_RESULTS))
    awards, result, site = await _run(
        tmp_path, monkeypatch, _search_pages(), on=True, provider=provider, scholarships_url=INDEX
    )
    assert [c["query"] for c in provider.calls] == [
        "Test University scholarships international undergraduate students"
    ]
    for junk in _SEARCH_RESULTS[:4]:
        assert junk not in site.requested
    assert f"{UNI}/scholarships/guide.pdf" in site.requested
    assert [a.name for a in awards] == ["Global Scholarship"], result.errors


@pytest.mark.asyncio
async def test_off_the_award_query_and_its_results_are_unchanged(tmp_path, monkeypatch):
    provider = Provider(list(_SEARCH_RESULTS))
    awards, _, site = await _run(
        tmp_path, monkeypatch, _search_pages(), on=False, provider=provider, scholarships_url=INDEX
    )
    query = provider.calls[0]["query"]
    assert query.startswith("site:uni.edu scholarship international")
    assert _SEARCH_RESULTS[0] in site.requested
    assert awards == []


def test_shape_filter_keeps_an_official_scholarships_pdf_only():
    candidate = Candidate(name="T", country="X", city="Y", domain="uni.edu")
    shape = web_scholarships._off_award_shape
    assert shape("https://massmailer.uni.edu/x", candidate) == "a mail-tracking link"
    assert shape(f"{UNI}/posts/award", candidate) == "a news item or post"
    assert shape(f"{UNI}/study/country/lesotho", candidate) == "a country page"
    assert shape(f"{UNI}/files/a.pdf", candidate)
    assert shape("https://other.org/scholarships/a.pdf", candidate)
    assert shape(f"{UNI}/scholarships/a.pdf", candidate) == ""
    assert shape(f"{UNI}/scholarships/global", candidate) == ""


# --- 4. exists and international applicability from eligibility sentences ----

_POPULATION = _award_page(
    "Belarus Scholarship",
    "International students are eligible for many of our programmes.",
    "Eligibility: the scholarship is open to international students from Belarus.",
)
_DOMESTIC = _award_page(
    "Home Scholarship",
    "This scholarship is open to domestic students who are permanent residents.",
    "International students may apply for many other scholarships.",
)
_NO_ELIGIBILITY = _award_page("Quiet Scholarship", "A long tradition of excellence.")
_OTHER_LEVEL = _award_page(
    "Research Scholarship",
    "This scholarship is for Master's students. Applications are open to international students.",
)
_OTHER_FACULTY = _award_page(
    "Law Scholarship",
    "Eligibility: open only to students in the Faculty of Law and Justice.",
    "Applications are open to international students.",
)
_OPEN = _award_page(
    "Open Scholarship",
    "Eligibility: the Open Scholarship is open to international students holding an offer.",
)


async def _one_award(tmp_path, monkeypatch, body: str, *, on: bool):
    pages = {
        PROGRAMME: "<html><body><main><h1>BSc Computer Science</h1></main></body></html>",
        INDEX: _index("Scholarships", [("/scholarships/the-award", "The award")]),
        f"{UNI}/scholarships/the-award": body,
    }
    awards, result, _ = await _run(tmp_path, monkeypatch, pages, on=on, scholarships_url=INDEX)
    return awards, result


def _claims(result, claim_type: ClaimType):
    return [c for c in result.claims if c.claim_type is claim_type]


@pytest.mark.asyncio
async def test_on_exists_and_international_come_from_the_eligibility_sentence(
    tmp_path, monkeypatch
):
    awards, result = await _one_award(tmp_path, monkeypatch, _OPEN, on=True)
    assert awards[0].international_eligible == "yes", result.errors
    (exists,) = _claims(result, ClaimType.SCHOLARSHIP_EXISTS)
    assert exists.original_text_excerpt.startswith(
        "Eligibility: the Open Scholarship is open to international"
    )


@pytest.mark.asyncio
async def test_on_an_award_without_an_eligibility_sentence_claims_no_existence(
    tmp_path, monkeypatch
):
    _, on = await _one_award(tmp_path, monkeypatch, _NO_ELIGIBILITY, on=True)
    _, off = await _one_award(tmp_path, monkeypatch, _NO_ELIGIBILITY, on=False)
    assert _claims(on, ClaimType.SCHOLARSHIP_EXISTS) == []
    assert len(_claims(off, ClaimType.SCHOLARSHIP_EXISTS)) == 1


@pytest.mark.asyncio
async def test_a_population_restricted_award_never_counts_as_international(tmp_path, monkeypatch):
    on, _ = await _one_award(tmp_path, monkeypatch, _POPULATION, on=True)
    off, _ = await _one_award(tmp_path, monkeypatch, _POPULATION, on=False)
    assert on[0].international_eligible == "unknown"
    assert off[0].international_eligible == "yes"


@pytest.mark.asyncio
async def test_a_domestic_only_award_never_counts_as_international(tmp_path, monkeypatch):
    on, result = await _one_award(tmp_path, monkeypatch, _DOMESTIC, on=True)
    off, _ = await _one_award(tmp_path, monkeypatch, _DOMESTIC, on=False)
    assert on[0].international_eligible == "no"
    (claim,) = _claims(result, ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE)
    assert claim.normalized_value is False
    assert off[0].international_eligible == "yes"


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [_OTHER_LEVEL, _OTHER_FACULTY], ids=["level", "faculty"])
async def test_an_award_for_another_level_or_faculty_claims_nothing(tmp_path, monkeypatch, body):
    on, on_result = await _one_award(tmp_path, monkeypatch, body, on=True)
    off, _ = await _one_award(tmp_path, monkeypatch, body, on=False)
    assert on == []
    assert on_result.claims == []
    assert any(o.detail.startswith("award out of scope") for o in on_result.page_outcomes)
    assert len(off) == 1


def test_a_faculty_of_science_award_is_in_scope_for_computer_science():
    program = CandidateProgram(
        name="Computer Science", field="computer science", degree=DegreeLevel.BACHELOR
    )
    body = _award_page("Science Scholarship", "Open only to students in the Faculty of Science.")
    assert web_scholarships._award_out_of_scope(body, f"{UNI}/s", program) == ""
    assert "faculty site" in web_scholarships._award_out_of_scope(
        body, "https://arts.uni.edu/s", program
    )


def test_the_flag_is_off_by_default():
    assert web_scholarships.AWARD_ROUTE is False
