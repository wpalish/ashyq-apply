"""Plan rule DL-6 (``INTERNATIONAL_ROUND_DEADLINE``), owner-signed gold 02-Q5.

Uppsala's programme page says "Application deadline 15 April 2027" with no
population words; that is the Swedish/EU round. The international round closes
on 15 January 2027, stated on the bachelor level's application page
(uu.se/en/study/bachelors-studies/application) beside "International admission
round" and "Swedish admission round". No base2 run read that page.

The pages below are the real ones, hand-fetched 2026-10-18, trimmed to the
markup that decides (the programme page is ``test_intake_section_deadline``'s).
"""

from __future__ import annotations

from typing import Any

import pytest

import app.adapters.extraction as extraction
import app.adapters.search as search_pkg
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import ClaimBuilder, extract_requirements, readable_text
from app.adapters.fetching import FetchResult
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import (
    WebRequirementsAdapter,
    _application_page_link,
)
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome
from tests.test_intake_section_deadline import UPPSALA_HTML, UPPSALA_URL

UU = "https://www.uu.se"
UU_APPLICATION = f"{UU}/en/study/bachelors-studies/application"
UU_ENTRY = f"{UU}/en/study/bachelors-studies/application/entry-requirements"

#: https://www.uu.se/en/study/bachelors-studies/application (trimmed).
UU_APPLICATION_HTML = (
    "<html><head><title>Application – Uppsala University</title></head><body><main>"
    '<h1 class="uu-heading">Apply to a Bachelor&#39;s programme at Uppsala University</h1>'
    '<p class="uu-text">Interested in studying for a Bachelor’s degree at Uppsala University? '
    "Applications are made through the Swedish national portal University Admissions.</p>"
    '<h2 class="uu-subheading">Next application period</h2><p class="uu-text">The next '
    "application will open <strong>16 October 2026 and close 15 January 2027</strong>.</p>"
    "<h2>Useful information</h2><h3>Application rounds</h3>"
    '<h4 class="uu-subheading4">International admission round</h4><p class="uu-text">We '
    "strongly encourage all international students to apply in the international admission "
    "round, which runs from mid-October to mid-January.</p>"
    '<h4 class="uu-subheading4">Swedish admission round</h4><p class="uu-text">If you are an '
    "EU/EEA citizen (or already have a residence permit in Sweden or the EU/EEA) and missed "
    "the international round, you may be able to apply for a few programmes or courses in "
    'the Swedish admission round. Apply through <a href="https://www.antagning.se" '
    'rel="external">Antagning.se</a> (website in Swedish).</p>'
    "</main></body></html>"
)
#: The entry-requirements page's navigation (trimmed): its "Application" link.
UU_ENTRY_HTML = (
    "<html><head><title>Entry requirements – Uppsala University</title></head><body>"
    '<nav><a class="nav-link" href="/en/study/bachelors-studies/application">Application</a>'
    '<a class="nav-link" href="/en/study/bachelors-studies/application/application-guide">'
    "Application guide</a>"
    '<a class="nav-link" aria-current="page" '
    'href="/en/study/bachelors-studies/application/entry-requirements">Entry requirements</a>'
    '<a class="nav-link" href="/en/study/masters-studies/application">Application</a></nav>'
    "<main><h1>Entry requirements</h1><p>To be admitted to a Bachelor's programme you need "
    "to meet the general entry requirements.</p></main></body></html>"
)
#: A page naming both rounds and stating only an unlabelled date.
TWO_ROUNDS_NO_WINDOW = (
    "<html><body><h1>Application</h1><h2>International admission round</h2>"
    "<p>For international students.</p><h2>National admission round</h2>"
    "<p>Application deadline 15 April 2027</p></body></html>"
)


def _deadlines(claims) -> list[tuple[object, str | None]]:
    return [
        (c.normalized_value, c.scope.population if c.scope else None)
        for c in claims
        if c.claim_type is ClaimType.ADMISSION_DEADLINE
    ]


def _read(html: str, url: str, population: str | None) -> list[tuple[object, str | None]]:
    text = readable_text(html)
    builder = ClaimBuilder(source_url=url, official_domain=True, intake="fall 2027", page_text=text)
    builder.requested_population = population
    extract_requirements(text, builder)
    return _deadlines(builder.claims)


@pytest.fixture
def dl6(monkeypatch):
    monkeypatch.setattr(extraction, "INTERNATIONAL_ROUND_DEADLINE", True)


@pytest.fixture
def no_dl6(monkeypatch):
    monkeypatch.setattr(extraction, "INTERNATIONAL_ROUND_DEADLINE", False)


def test_on_by_default():
    assert extraction.INTERNATIONAL_ROUND_DEADLINE is True


class TestReader:
    def test_off_the_window_is_read_without_a_population(self, no_dl6):
        assert _read(UU_APPLICATION_HTML, UU_APPLICATION, "international") == [("2027-01-15", None)]

    def test_on_the_window_is_the_international_round(self, dl6):
        assert _read(UU_APPLICATION_HTML, UU_APPLICATION, "international") == [
            ("2027-01-15", "international")
        ]

    @pytest.mark.parametrize("population", ["domestic", None])
    def test_on_only_for_an_international_applicant(self, dl6, population):
        assert _read(UU_APPLICATION_HTML, UU_APPLICATION, population) == [("2027-01-15", None)]

    def test_on_the_programme_page_names_no_round_and_is_unchanged(self, dl6):
        assert _read(UPPSALA_HTML, UPPSALA_URL, "international") == [("2027-04-15", None)]

    def test_on_two_rounds_and_no_window_abstain(self, dl6):
        assert _read(TWO_ROUNDS_NO_WINDOW, UU_APPLICATION, "international") == []

    def test_off_two_rounds_and_no_window_unchanged(self, no_dl6):
        assert _read(TWO_ROUNDS_NO_WINDOW, UU_APPLICATION, "international") == [
            ("2027-04-15", None)
        ]


def test_application_page_link_is_the_levels_bare_application_link():
    link = _application_page_link(UU_ENTRY_HTML, UU_ENTRY, "www.uu.se", degree="bachelor")
    assert link == UU_APPLICATION
    assert _application_page_link(UPPSALA_HTML, UPPSALA_URL, "www.uu.se") is None
    housing = '<a href="/life/accommodation/undergraduate-housing/application">Application</a>'
    assert _application_page_link(housing, f"{UU}/x", "www.uu.se") is None


class _Fetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.calls.append(url)
        if url not in self.pages:
            return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=404)
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            text=self.pages[url],
            content_type="text/html",
            final_url=url,
        )


class _NoSearch:
    name = "none"

    async def search(self, **kwargs: Any) -> Any:
        raise AssertionError("no topic query is expected here")


@pytest.fixture(autouse=True)
def no_search(monkeypatch):
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: _NoSearch())
    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH", False)


async def _uppsala(citizenship: str):
    candidate = Candidate(
        name="Uppsala University",
        country="Sweden",
        city="Uppsala",
        domain="www.uu.se",
        admissions_url=UU_ENTRY,
    )
    program = CandidateProgram(
        name="Bachelor's Programme in Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=UPPSALA_URL,
    )
    fetcher = _Fetcher(
        {UPPSALA_URL: UPPSALA_HTML, UU_ENTRY: UU_ENTRY_HTML, UU_APPLICATION: UU_APPLICATION_HTML}
    )
    adapter = WebRequirementsAdapter(fetcher, "2027/28", (citizenship,))  # type: ignore[arg-type]
    return await adapter.verify(candidate, program, "fall 2027"), fetcher


class TestAdapter:
    async def test_off_the_programme_pages_national_round_is_claimed(self, no_dl6):
        result, fetcher = await _uppsala("Kazakhstan")
        assert _deadlines(result.claims) == [("2027-04-15", None)]
        assert UU_APPLICATION not in fetcher.calls

    async def test_on_an_international_applicant_gets_the_international_round(self, dl6):
        result, fetcher = await _uppsala("Kazakhstan")
        assert UU_APPLICATION in fetcher.calls
        assert _deadlines(result.claims) == [("2027-01-15", "international")]
        claim = next(c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE)
        assert claim.source_url == UU_APPLICATION
        assert "close 15 January 2027" in claim.original_text_excerpt
        assert any("DL-6" in e and UPPSALA_URL in e for e in result.errors)

    async def test_on_a_domestic_applicant_is_unchanged(self, dl6):
        result, fetcher = await _uppsala("Sweden")
        assert _deadlines(result.claims) == [("2027-04-15", None)]
        assert UU_APPLICATION not in fetcher.calls
