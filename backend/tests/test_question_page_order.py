"""Plan rules QP-1 and QR-2 (core-gap analysis 2026-10-18 §3 changes 5 and 6).

QP-1 (``QUESTION_PAGE_ORDER``): UBC's deadline page was queued behind an
English page, a "How to apply" page and a route lead, and TB-1 refused it in 2
of 4 repetitions with English long answered. On, after the link sources, the
next page read is one for the unanswered question with the fewest pages read.

QR-2 (``PARENT_DEGREE_LINK``): Auckland confirms the Computer Science major's
page, which says "You can study Computer Science as a major in the Bachelor of
Science (BSc)" and links that degree page, where the application closing dates
live. On, that link is read as a deadline/English source and handed to the cost
adapter as a fees page.

The UBC pages are minimal reconstructions of the captured shapes (same link
texts and URL shapes); the Auckland pages are the real ones, hand-fetched
2026-10-18, trimmed to the markup that decides.
"""

from __future__ import annotations

from typing import Any

import pytest

import app.adapters.extraction as extraction
import app.adapters.search as search_pkg
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import FetchResult
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import (
    WebRequirementsAdapter,
    _parent_degree_link,
)
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome
from tests.test_intake_section_deadline import AUCKLAND_HTML, AUCKLAND_URL

UBC = "https://you.ubc.ca"
UBC_COURSE = f"{UBC}/programs/computer-science-vancouver-bsc/"
UBC_ADMISSIONS = f"{UBC}/applying-ubc/"
UBC_ENGLISH = f"{UBC}/applying-ubc/requirements/english-language-competency/"
UBC_HOW_TO = f"{UBC}/applying-ubc/how-to-apply/"
UBC_ROUTE = f"{UBC}/applying-ubc/requirements/international-high-schools/"
UBC_DATES = f"{UBC}/applying-ubc/dates-deadlines/"

UBC_COURSE_HTML = f"""<html><head><title>Computer Science | UBC Undergraduate Programs</title>
</head><body><h1>Computer Science</h1><p>Bachelor of Science, Vancouver campus.</p>
<p>Check the <a href="{UBC_ENGLISH}">English language requirements</a>.</p>
<p><a href="{UBC_HOW_TO}">How to apply</a></p>
<p>Applying from abroad? See <a href="{UBC_ROUTE}">International high schools</a>.</p>
</body></html>"""
UBC_ADMISSIONS_HTML = f"""<html><head><title>Applying to UBC | UBC Undergraduate Programs</title>
</head><body><h1>Applying to UBC</h1>
<p>See the <a href="{UBC_DATES}">Dates and deadlines</a> for your application.</p>
</body></html>"""
UBC_ENGLISH_HTML = """<html><head><title>English language competency</title></head><body>
<h1>English language competency</h1>
<p>IELTS Academic: an overall band score of 6.5, with no part less than 6.0.</p>
</body></html>"""
UBC_HOW_TO_HTML = """<html><head><title>How to apply</title></head><body><h1>How to apply</h1>
<p>Create an account and fill in the online application.</p></body></html>"""
UBC_ROUTE_HTML = """<html><head><title>International high schools</title></head><body>
<h1>International high schools</h1><p>Requirements by country.</p></body></html>"""
UBC_DATES_HTML = """<html><head><title>Dates and deadlines</title></head><body>
<h1>Dates and deadlines</h1><p>January 15, 2027 (11:59 p.m. PST) Applications due</p>
</body></html>"""

AUCKLAND = "https://www.auckland.ac.nz"
AUCKLAND_COURSE = (
    f"{AUCKLAND}/en/study/study-options/find-a-study-option/computer-science/undergraduate.html"
)
#: The confirmed page, trimmed (h1, the sentence linking the degree, a listing).
AUCKLAND_COURSE_HTML = f"""<html><head>
<title>Undergraduate study in Computer Science – University of Auckland</title></head><body>
<main><h1 data-page-title="Undergraduate study in Computer Science">Undergraduate study in
Computer Science</h1>
<h2>What can you study in Computer Science?</h2>
<p>You can study Computer Science as a major in the <a target="_blank"
href="{AUCKLAND_URL}" rel="noopener noreferrer">Bachelor of Science (BSc)</a>.</p>
<p>Computing technology permeates our lives, and with that comes the demand for specialists.</p>
<ul><li><a href="/en/study/study-options/find-a-study-option/bachelor-of-science-bsc.html"
class="listing-item__link">Bachelor of Science</a></li>
<li><a href="/en/study/study-options/find-a-study-option/bachelor-of-arts-ba.html"
class="listing-item__link">Bachelor of Arts</a></li></ul>
<p><a href="/en/study/international-students/master-of-science.html">Master of Science</a></p>
</main></body></html>"""


class _Fetcher:
    """Serves ``pages``; with ``cap``, refuses every read past it as TB-1 does."""

    def __init__(self, pages: dict[str, str], cap: int | None = None) -> None:
        self.pages = pages
        self.cap = cap
        self.calls: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.calls.append(url)
        if self.cap is not None and len(self.calls) > self.cap:
            return FetchResult(
                url=url, outcome=FetchOutcome.BLOCKED, error="TB-1: no time left for this read"
            )
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


@pytest.fixture
def qp1(monkeypatch):
    monkeypatch.setattr(web_requirements, "QUESTION_PAGE_ORDER", True)


@pytest.fixture
def qr2(monkeypatch):
    monkeypatch.setattr(web_requirements, "PARENT_DEGREE_LINK", True)


def _ubc_pages() -> dict[str, str]:
    return {
        UBC_COURSE: UBC_COURSE_HTML,
        UBC_ADMISSIONS: UBC_ADMISSIONS_HTML,
        UBC_ENGLISH: UBC_ENGLISH_HTML,
        UBC_HOW_TO: UBC_HOW_TO_HTML,
        UBC_ROUTE: UBC_ROUTE_HTML,
        UBC_DATES: UBC_DATES_HTML,
    }


async def _ubc(cap: int | None = None):
    candidate = Candidate(
        name="University of British Columbia",
        country="Canada",
        city="Vancouver",
        domain="you.ubc.ca",
        admissions_url=UBC_ADMISSIONS,
    )
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=UBC_COURSE,
    )
    fetcher = _Fetcher(_ubc_pages(), cap)
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    return await adapter.verify(candidate, program, "fall 2027"), fetcher


def _deadlines(result) -> list[object]:
    return [
        c.normalized_value for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE
    ]


class TestQuestionPageOrder:
    async def test_on_by_default(self):
        assert web_requirements.QUESTION_PAGE_ORDER is True
        result, fetcher = await _ubc()
        assert fetcher.calls[-2:] == [UBC_DATES, UBC_ROUTE]
        assert _deadlines(result) == ["2027-01-15"]

    async def test_off_the_deadline_page_waits_behind_a_route_lead(self, monkeypatch):
        monkeypatch.setattr(web_requirements, "QUESTION_PAGE_ORDER", False)
        _, fetcher = await _ubc()
        assert fetcher.calls == [
            UBC_COURSE,
            UBC_ADMISSIONS,
            UBC_ENGLISH,
            UBC_HOW_TO,
            UBC_ROUTE,
            UBC_DATES,
        ]

    async def test_on_the_unanswered_questions_second_page_comes_first(self, qp1):
        result, fetcher = await _ubc()
        assert fetcher.calls == [
            UBC_COURSE,
            UBC_ADMISSIONS,
            UBC_ENGLISH,
            UBC_HOW_TO,
            UBC_DATES,
            UBC_ROUTE,
        ]
        assert _deadlines(result) == ["2027-01-15"]

    async def test_under_a_read_budget_off_loses_the_deadline_and_on_keeps_it(self, monkeypatch):
        monkeypatch.setattr(web_requirements, "QUESTION_PAGE_ORDER", False)
        off, _ = await _ubc(cap=5)
        assert _deadlines(off) == []
        monkeypatch.setattr(web_requirements, "QUESTION_PAGE_ORDER", True)
        on, fetcher = await _ubc(cap=5)
        assert _deadlines(on) == ["2027-01-15"]
        ielts = [
            c.normalized_value for c in on.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL
        ]
        assert ielts == [6.5]
        assert fetcher.calls[-1] == UBC_ROUTE

    async def test_one_page_per_question_before_a_second_of_any(self, qp1):
        pages = _ubc_pages()
        # The English page answers nothing: English and the deadline alternate.
        second_english = f"{UBC}/applying-ubc/requirements/english-language-requirements/"
        pages[UBC_ENGLISH] = UBC_HOW_TO_HTML
        pages[second_english] = UBC_ENGLISH_HTML
        pages[UBC_COURSE] = UBC_COURSE_HTML.replace(
            "</body>", f'<p><a href="{second_english}">English language requirements</a></p></body>'
        )
        candidate = Candidate(
            name="University of British Columbia",
            country="Canada",
            city="Vancouver",
            domain="you.ubc.ca",
            admissions_url=UBC_ADMISSIONS,
        )
        program = CandidateProgram(
            name="Computer Science",
            field="computer science",
            degree=DegreeLevel.BACHELOR,
            url=UBC_COURSE,
        )
        fetcher = _Fetcher(pages)
        adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
        await adapter.verify(candidate, program, "fall 2027")
        assert fetcher.calls[2:6] == [UBC_ENGLISH, UBC_HOW_TO, second_english, UBC_DATES]


async def _auckland(dl5: bool, monkeypatch):
    monkeypatch.setattr(extraction, "INTAKE_SECTION_DEADLINE", dl5)
    candidate = Candidate(
        name="The University of Auckland",
        country="New Zealand",
        city="Auckland",
        domain="www.auckland.ac.nz",
    )
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=AUCKLAND_COURSE,
    )
    fetcher = _Fetcher({AUCKLAND_COURSE: AUCKLAND_COURSE_HTML, AUCKLAND_URL: AUCKLAND_HTML})
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    return await adapter.verify(candidate, program, "fall 2027"), fetcher, candidate


class TestParentDegreeLink:
    async def test_on_by_default(self, monkeypatch):
        assert web_requirements.PARENT_DEGREE_LINK is True
        # DL-5 is on by default too: the degree page's closing-date row is read.
        assert extraction.INTAKE_SECTION_DEADLINE is True
        result, fetcher, candidate = await _auckland(True, monkeypatch)
        assert fetcher.calls == [AUCKLAND_COURSE, AUCKLAND_URL]
        assert _deadlines(result) == ["2026-12-08"]
        assert candidate.question_fee_urls == [AUCKLAND_URL]

    def test_the_link_the_programme_page_names_as_its_degree(self):
        found = _parent_degree_link(
            AUCKLAND_COURSE_HTML, AUCKLAND_COURSE, "auckland.ac.nz", degree=DegreeLevel.BACHELOR
        )
        assert found == AUCKLAND_URL

    def test_no_link_of_another_level_or_a_degree_the_page_does_not_name(self):
        assert (
            _parent_degree_link(
                AUCKLAND_COURSE_HTML, AUCKLAND_COURSE, "auckland.ac.nz", degree=DegreeLevel.MASTER
            )
            is None
        )
        unnamed = AUCKLAND_COURSE_HTML.replace("as a major in the", "alongside the")
        assert (
            _parent_degree_link(
                unnamed, AUCKLAND_COURSE, "auckland.ac.nz", degree=DegreeLevel.BACHELOR
            )
            is None
        )
        # A programme title with its subject is a programme, not a parent degree.
        programme = AUCKLAND_COURSE_HTML.replace(
            ">Bachelor of Science (BSc)</a>", ">Bachelor of Science in Computer Science</a>"
        )
        assert (
            _parent_degree_link(
                programme, AUCKLAND_COURSE, "auckland.ac.nz", degree=DegreeLevel.BACHELOR
            )
            is None
        )

    def test_the_page_title_naming_the_degree_is_enough(self):
        titled = AUCKLAND_COURSE_HTML.replace(
            "<title>Undergraduate study in Computer Science",
            "<title>Bachelor of Science (BSc) – Computer Science major",
        ).replace("as a major in the", "alongside the")
        assert (
            _parent_degree_link(
                titled, AUCKLAND_COURSE, "auckland.ac.nz", degree=DegreeLevel.BACHELOR
            )
            == AUCKLAND_URL
        )

    async def test_off_the_degree_page_is_never_read(self, monkeypatch):
        monkeypatch.setattr(web_requirements, "PARENT_DEGREE_LINK", False)
        result, fetcher, candidate = await _auckland(True, monkeypatch)
        assert AUCKLAND_URL not in fetcher.calls
        assert _deadlines(result) == []
        assert AUCKLAND_URL not in candidate.question_fee_urls

    async def test_on_with_dl5_the_closing_date_row_is_read(self, qr2, monkeypatch):
        result, fetcher, candidate = await _auckland(True, monkeypatch)
        assert fetcher.calls == [AUCKLAND_COURSE, AUCKLAND_URL]
        assert _deadlines(result) == ["2026-12-08"]
        (claim,) = [c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE]
        assert claim.source_url == AUCKLAND_URL
        # The degree page keeps its own scope: no programme name from the link.
        assert claim.scope is not None and claim.scope.programme != "Computer Science"
        # Fees: handed to the cost adapter, not read here.
        assert candidate.question_fee_urls == [AUCKLAND_URL]

    async def test_on_without_dl5_the_page_is_read_and_claims_no_deadline(self, qr2, monkeypatch):
        result, fetcher, _ = await _auckland(False, monkeypatch)
        assert AUCKLAND_URL in fetcher.calls
        assert _deadlines(result) == []

    async def test_english_is_read_only_while_the_programme_states_none(self, qr2, monkeypatch):
        html = AUCKLAND_HTML.replace(
            "<h2>Key dates</h2>",
            "<h2>English language requirements</h2><p>IELTS Academic: an overall band score "
            "of 6.0, with no band less than 5.5.</p><h2>Key dates</h2>",
        )
        monkeypatch.setattr(extraction, "INTAKE_SECTION_DEADLINE", True)
        candidate = Candidate(
            name="The University of Auckland",
            country="New Zealand",
            city="Auckland",
            domain="www.auckland.ac.nz",
        )
        program = CandidateProgram(
            name="Computer Science",
            field="computer science",
            degree=DegreeLevel.BACHELOR,
            url=AUCKLAND_COURSE,
        )
        fetcher = _Fetcher({AUCKLAND_COURSE: AUCKLAND_COURSE_HTML, AUCKLAND_URL: html})
        adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
        result = await adapter.verify(candidate, program, "fall 2027")
        ielts = [
            (c.normalized_value, c.source_url)
            for c in result.claims
            if c.claim_type is ClaimType.IELTS_MIN_OVERALL
        ]
        assert ielts == [(6.0, AUCKLAND_URL)]
        stricter = AUCKLAND_COURSE_HTML.replace(
            "</main>", "<p>IELTS Academic: an overall band score of 6.5.</p></main>"
        )
        fetcher = _Fetcher({AUCKLAND_COURSE: stricter, AUCKLAND_URL: html})
        adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
        result = await adapter.verify(candidate, program, "fall 2027")
        ielts = [
            (c.normalized_value, c.source_url)
            for c in result.claims
            if c.claim_type is ClaimType.IELTS_MIN_OVERALL
        ]
        assert ielts == [(6.5, AUCKLAND_COURSE)]
