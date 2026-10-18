"""Plan rule QR-1: question-routed evidence (structural analysis 2026-10-18, §3 change 2).

F1: the evidence stage routed a page by its type, not by the question it was
fetched for — TCD's and UCT's English pages were fetched and rejected as
``unknown``, and every fee page the fees query returned was rejected as
``costs``. F2: the programme page links most of the missing answers ("Fees",
"Selection procedure", "English language requirements … here.") and nothing
followed them. The pages below are minimal reconstructions of those shapes
(same link texts and URL shapes), not copies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

import app.adapters.search as search_pkg
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.extraction import readable_text
from app.adapters.fetching import FetchResult
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter, _question_links
from app.adapters.scope_reader import read_scope
from app.adapters.search import SearchResponse, SearchResult
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome

TCD = "https://www.tcd.ie"
COURSE_URL = f"{TCD}/courses/undergraduate/computer-science/"
ENGLISH_URL = f"{TCD}/study/apply/english-language-requirements/"
FEES_URL = f"{TCD}/courses/undergraduate/fees/"
PG_FEES_URL = f"{TCD}/courses/postgraduate/fees/"
SELECTION_URL = f"{TCD}/study/apply/selection-procedure/"
QUERY_FEES_URL = f"{TCD}/study/fees-finances/undergraduate/"

COURSE = f"""<html><head><title>Computer Science - Courses | Trinity College Dublin</title></head>
<body><nav><a href="{FEES_URL}">Fees</a> <a href="{PG_FEES_URL}">Fees</a></nav>
<h1>Computer Science</h1><h2>Overview</h2>
<p>Computer Science at Trinity is a four-year course.</p>
<ul><li><a href="{TCD}/courses/a/">Engineering</a></li>
<li><a href="{TCD}/courses/b/">Mathematics</a></li>
<li><a href="{TCD}/courses/c/">Physics</a></li>
<li><a href="{TCD}/courses/d/">Computer Engineering</a></li>
<li><a href="{TCD}/courses/e/">Data Science</a></li></ul>
<h2>Admission Requirements</h2>
<p>Applicants whose first language is not English: see the English language requirements
<a href="{ENGLISH_URL}">here.</a></p>
<p><a href="{SELECTION_URL}">Selection procedure</a></p>
</body></html>"""

#: Classifies as ``unknown``: no title, heading or signal names a requirements page.
ENGLISH = """<html><head><title>Trinity College Dublin</title></head><body>
<p>Applicants who are not native speakers of English must present one of the following.</p>
<p>IELTS (Academic): an overall band score of 6.5, with no individual band below 6.0.</p>
</body></html>"""

SELECTION = """<html><head><title>Selection procedure | Trinity College Dublin</title></head>
<body><h1>Selection procedure</h1>
<p>Non-EU applicants apply online. The application deadline is 1 February 2027.</p>
</body></html>"""

FEES = """<html><head><title>Undergraduate fees | Trinity College Dublin</title></head><body>
<h1>Undergraduate tuition fees for non-EU students</h1>
<p>Tuition fee for non-EU students: €24,000 per year.</p></body></html>"""


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


class _Provider:
    """Answers each topic query with the URL mapped to a word in it."""

    name = "fake"

    def __init__(self, answers: dict[str, str]) -> None:
        self.answers = answers
        self.queries: list[str] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.queries.append(query)
        urls = [url for word, url in self.answers.items() if word in query]
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=datetime.now(UTC),
            results=tuple(
                SearchResult(
                    url=u, title="t", provider=self.name, rank=i + 1, retrieved_at=datetime.now(UTC)
                )
                for i, u in enumerate(urls)
            ),
        )


@pytest.fixture
def provider(monkeypatch):
    def install(answers: dict[str, str]) -> _Provider:
        built = _Provider(answers)
        monkeypatch.setattr(search_pkg, "get_search_provider", lambda: built)
        return built

    return install


@pytest.fixture
def routing(monkeypatch):
    monkeypatch.setattr(web_requirements, "QUESTION_ROUTED_EVIDENCE", True)


def _tcd(costs_url: str | None = None) -> tuple[Candidate, CandidateProgram]:
    candidate = Candidate(
        name="Trinity College Dublin",
        country="Ireland",
        city="Dublin",
        domain="www.tcd.ie",
        costs_url=costs_url,
    )
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=COURSE_URL,
    )
    return candidate, program


async def _verify(pages: dict[str, str], candidate: Candidate, program: CandidateProgram):
    fetcher = _Fetcher(pages)
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    return await adapter.verify(candidate, program, "fall 2027"), fetcher


def _pages() -> dict[str, str]:
    return {
        COURSE_URL: COURSE,
        ENGLISH_URL: ENGLISH,
        SELECTION_URL: SELECTION,
        FEES_URL: FEES,
        PG_FEES_URL: FEES,
        QUERY_FEES_URL: FEES,
    }


def test_the_rule_is_off_by_default():
    assert web_requirements.QUESTION_ROUTED_EVIDENCE is False


def test_the_english_fixture_reads_as_unknown():
    """The precondition of the TCD case: the classifier rejects the English page."""
    page = classify_page(url=ENGLISH_URL, html=ENGLISH, text=readable_text(ENGLISH))
    assert page.page_type is PageType.UNKNOWN
    assert not page.accepts("requirements")


def test_question_links_by_text_and_url_with_the_level_guards():
    links = _question_links(COURSE, COURSE_URL, "www.tcd.ie", degree=DegreeLevel.BACHELOR)
    # "here." is named by its URL, "Fees" and "Selection procedure" by their
    # text; the postgraduate fee link names another level and is dropped.
    assert links == [("fees", FEES_URL), ("english", ENGLISH_URL), ("deadline", SELECTION_URL)]
    master_page = (
        '<a href="https://studies.ku.dk/masters/language-requirements/">Language requirements</a>'
        '<a href="https://studies.ku.dk/bachelor/language/">Master\'s language requirements</a>'
        '<a href="https://studies.ku.dk/apply/application-fee/">Application fee</a>'
        '<a href="https://studies.ku.dk/scholarships/deadlines/">Scholarship deadlines</a>'
    )
    assert (
        _question_links(
            master_page,
            "https://studies.ku.dk/bachelor/computer-science/",
            "studies.ku.dk",
            degree=DegreeLevel.BACHELOR,
        )
        == []
    )


async def test_off_the_english_page_is_fetched_and_rejected_as_unknown(provider):
    """Today's TCD capture: the language link is followed and the page refused."""
    built = provider({})
    candidate, program = _tcd()
    result, fetcher = await _verify(_pages(), candidate, program)
    # Topic search runs before any page is read, all three topics, as before.
    assert len(built.queries) == 3
    assert fetcher.calls == [COURSE_URL, ENGLISH_URL]
    outcomes = {o.url: o for o in result.page_outcomes}
    assert outcomes[ENGLISH_URL].category == "classifier-rejected"
    assert not [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert candidate.question_fee_urls == []


async def test_programme_links_are_followed_by_text_and_routed_by_question(routing, provider):
    built = provider({})
    candidate, program = _tcd()
    result, fetcher = await _verify(_pages(), candidate, program)
    outcomes = {o.url: o for o in result.page_outcomes}
    assert {c.claim_type for c in result.claims if c.source_url == COURSE_URL} == {
        ClaimType.PROGRAM_EXISTS
    }
    # The English page classifies as unknown and is read because it was
    # reached for the English question.
    ielts = [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert [(c.normalized_value, c.source_url) for c in ielts] == [(6.5, ENGLISH_URL)]
    assert outcomes[ENGLISH_URL].page_type == PageType.UNKNOWN.value
    assert outcomes[ENGLISH_URL].category == "fetched-ok"
    # Nothing but the English question is answered from it.
    assert {c.claim_type for c in result.claims if c.source_url == ENGLISH_URL} <= (
        web_requirements._QUESTION_CLAIMS["english"]
    )
    # "Selection procedure" is read by the deadline reader.
    deadlines = [c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE]
    assert deadlines and deadlines[0].source_url == SELECTION_URL
    # The fee link goes to the cost adapter, not read here; the postgraduate one never.
    assert candidate.question_fee_urls == [FEES_URL]
    assert FEES_URL not in fetcher.calls and PG_FEES_URL not in fetcher.calls
    # Every question was answered or handed on, so no topic query was sent.
    assert built.queries == []


async def test_fee_page_from_the_fees_query_yields_cost_claims(routing, provider):
    built = provider({"tuition fees": QUERY_FEES_URL})
    candidate, program = _tcd(costs_url=f"{TCD}/about/feedback/")
    pages = _pages()
    pages[COURSE_URL] = COURSE.replace(f'<a href="{FEES_URL}">Fees</a>', "")
    pages[f"{TCD}/about/feedback/"] = "<html><body><h1>Feedback</h1><p>Tell us.</p></body></html>"
    result, fetcher = await _verify(pages, candidate, program)
    # English and deadline are answered by links; only the fees question is asked.
    assert len(built.queries) == 1 and "tuition fees" in built.queries[0]
    assert candidate.question_fee_urls == [QUERY_FEES_URL]
    assert QUERY_FEES_URL not in fetcher.calls
    costs = WebCostAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    breakdown, out = await costs.fetch(candidate)
    # The discovered cost page is read first, as before; the fee page after it.
    assert fetcher.calls[-2:] == [f"{TCD}/about/feedback/", QUERY_FEES_URL]
    tuition = [c for c in out.claims if c.claim_type is ClaimType.TUITION]
    assert tuition and tuition[0].source_url == QUERY_FEES_URL
    assert QUERY_FEES_URL in breakdown.source_urls


async def test_cost_adapter_off_ignores_question_fee_pages(provider):
    candidate, _ = _tcd(costs_url=f"{TCD}/about/feedback/")
    candidate.question_fee_urls.append(QUERY_FEES_URL)
    fetcher = _Fetcher({f"{TCD}/about/feedback/": "<html><body><p>Tell us.</p></body></html>"})
    _, out = await WebCostAdapter(fetcher, "2027/28").fetch(candidate)  # type: ignore[arg-type]
    assert fetcher.calls == [f"{TCD}/about/feedback/"]
    assert out.pages_checked == 1


UCPH = "https://studies.ku.dk"
UCPH_PROGRAMME = f"{UCPH}/bachelor/computer-science/"
UCPH_LANGUAGE = f"{UCPH}/language-requirements/"
UCPH_PROGRAMME_PAGE = f"""<html><head><title>Computer Science | University of Copenhagen</title>
</head><body><h1>Computer Science</h1>
<p><a href="{UCPH_LANGUAGE}">Language requirements</a></p></body></html>"""
#: Reached by a neutral link, but its own words scope it to master's programmes.
UCPH_LANGUAGE_PAGE = """<html><head><title>Language requirements for Master's programmes</title>
</head><body><h1>English language requirements</h1>
<p>Applicants to a master's programme must document English at this level.</p>
<table><tr><th>Test</th><th>Overall score</th></tr>
<tr><td>IELTS Academic</td><td>6.5</td></tr></table></body></html>"""


async def test_master_scope_claim_is_withheld_for_a_bachelor_request(routing, provider):
    provider({})
    candidate = Candidate(
        name="University of Copenhagen", country="Denmark", city="", domain="studies.ku.dk"
    )
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=UCPH_PROGRAMME,
    )
    pages = {UCPH_PROGRAMME: UCPH_PROGRAMME_PAGE, UCPH_LANGUAGE: UCPH_LANGUAGE_PAGE}
    result, fetcher = await _verify(pages, candidate, program)
    assert UCPH_LANGUAGE in fetcher.calls
    assert not [c for c in result.claims if c.source_url == UCPH_LANGUAGE]
    assert any(UCPH_LANGUAGE in e and "QR-1" in e for e in result.errors)


async def test_off_the_master_scope_claim_is_filed(provider):
    """The defect QR-1 removes: today the master's page answers for a bachelor."""
    provider({})
    candidate = Candidate(
        name="University of Copenhagen", country="Denmark", city="", domain="studies.ku.dk"
    )
    program = CandidateProgram(
        name="Computer Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=UCPH_PROGRAMME,
    )
    pages = {UCPH_PROGRAMME: UCPH_PROGRAMME_PAGE, UCPH_LANGUAGE: UCPH_LANGUAGE_PAGE}
    result, _ = await _verify(pages, candidate, program)
    ielts = [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert ielts and ielts[0].source_url == UCPH_LANGUAGE


UCT = "https://www.uct.ac.za"
UCT_HOME = f"{UCT}/"
UCT_ENGLISH = f"{UCT}/apply/english-language-requirements/"
UCT_HOME_PAGE = f"""<html><head><title>University of Cape Town</title></head><body>
<h1>Welcome to UCT</h1><a href="{UCT_ENGLISH}">English language requirements</a>
<a href="{UCT}/postgraduate/english-language/">Postgraduate English language</a></body></html>"""
UCT_DEADLINE = f"{UCT}/apply/undergraduate/dates/"


def _no_programme() -> tuple[Candidate, CandidateProgram]:
    candidate = Candidate(
        name="University of Cape Town", country="South Africa", city="", domain="www.uct.ac.za"
    )
    program = CandidateProgram(
        name="Computer Science (bachelor)",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=None,
    )
    return candidate, program


async def test_no_programme_page_still_runs_the_university_level_questions(routing, provider):
    built = provider({"application deadline": UCT_DEADLINE})
    candidate, program = _no_programme()
    pages = {UCT_HOME: UCT_HOME_PAGE, UCT_ENGLISH: ENGLISH, UCT_DEADLINE: SELECTION}
    result, fetcher = await _verify(pages, candidate, program)
    # The home page is a link source only; nothing on it is claimed.
    assert fetcher.calls[0] == UCT_HOME
    assert not [c for c in result.claims if c.source_url == UCT_HOME]
    assert f"{UCT}/postgraduate/english-language/" not in fetcher.calls
    ielts = [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert [(c.normalized_value, c.source_url) for c in ielts] == [(6.5, UCT_ENGLISH)]
    # English is answered; fees and the deadline are asked, the deadline included.
    assert len(built.queries) == 2
    assert "tuition fees" in built.queries[0] and "application deadline" in built.queries[1]
    deadlines = [c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE]
    assert deadlines and deadlines[0].source_url == UCT_DEADLINE


async def test_off_no_programme_page_reads_nothing(provider):
    built = provider({"application deadline": UCT_DEADLINE})
    candidate, program = _no_programme()
    pages = {UCT_HOME: UCT_HOME_PAGE, UCT_ENGLISH: ENGLISH, UCT_DEADLINE: SELECTION}
    result, fetcher = await _verify(pages, candidate, program)
    assert fetcher.calls == []
    assert built.queries == []
    assert result.pages_checked == 0


# --- QR-1b: scope by route, one read per institution, every question page routed ---

UCT_BSC = f"{UCT}/study/undergraduate/bsc-computer-science/"
UCT_BSC_DS = f"{UCT}/study/undergraduate/bsc-data-science/"
UCT_LANGUAGE = f"{UCT}/students/applications-admission-requirements/language-requirements"


def _uct_programme_page(title: str, link: bool = True) -> str:
    lead = f'<p>See the <a href="{UCT_LANGUAGE}">language requirements</a>.</p>' if link else ""
    return f"""<html><head><title>{title} | University of Cape Town</title></head><body>
<h1>{title}</h1><p>The {title} is a three-year undergraduate programme in the Faculty of
Science.</p><h2>Admission requirements</h2>{lead}</body></html>"""


#: UCT's language page names no degree at all (the gold URL of dev2's UCT case).
UCT_LANGUAGE_PAGE = """<html><head><title>Language requirements | University of Cape Town</title>
</head><body><h1>Language requirements</h1>
<p>All applicants must demonstrate proficiency in English.</p>
<p>IELTS: A valid (no more than 2 years old) IELTS Academic Test Report Form with an overall
score of band 6.5 or above, with at least 6.0 in each component.</p></body></html>"""
#: The same shape, but its own words scope it to master's programmes.
UCT_MASTER_LANGUAGE_PAGE = UCT_LANGUAGE_PAGE.replace(
    "All applicants must", "Applicants to a master's programme must"
)


def _uct(url: str = UCT_BSC, name: str = "Computer Science") -> tuple[Candidate, CandidateProgram]:
    candidate = Candidate(
        name="University of Cape Town", country="South Africa", city="", domain="www.uct.ac.za"
    )
    program = CandidateProgram(
        name=name, field="computer science", degree=DegreeLevel.BACHELOR, url=url
    )
    return candidate, program


def _uct_pages(language: str = UCT_LANGUAGE_PAGE, link: bool = True) -> dict[str, str]:
    return {
        UCT_BSC: _uct_programme_page("Bachelor of Science in Computer Science", link),
        UCT_BSC_DS: _uct_programme_page("Bachelor of Science in Data Science", link),
        UCT_LANGUAGE: language,
    }


def _ielts(result: Any) -> list[Any]:
    return [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]


def test_the_uct_fixtures_are_degree_silent_and_unknown():
    """Preconditions: the language page states no degree and reads as unknown."""
    text = readable_text(UCT_LANGUAGE_PAGE)
    assert read_scope(text, title="Language requirements").degree is None
    page = classify_page(url=UCT_LANGUAGE, html=UCT_LANGUAGE_PAGE, text=text)
    assert not page.accepts("requirements")


async def test_degree_silent_page_linked_from_the_programme_takes_its_degree(routing, provider):
    provider({})
    candidate, program = _uct()
    result, _ = await _verify(_uct_pages(), candidate, program)
    ielts = _ielts(result)
    assert [(c.normalized_value, c.source_url) for c in ielts] == [(6.5, UCT_LANGUAGE)]
    scope = ielts[0].scope
    assert scope is not None and scope.degree == "bachelor"
    assert scope.programme == "Computer Science"
    assert "degree from the linking programme page" in ielts[0].notes
    assert UCT_BSC in ielts[0].notes


async def test_the_same_page_from_topic_search_inherits_nothing(routing, provider):
    built = provider({"English language": UCT_LANGUAGE})
    candidate, program = _uct()
    result, _ = await _verify(_uct_pages(link=False), candidate, program)
    assert any("English language" in q for q in built.queries)
    ielts = _ielts(result)
    assert [c.source_url for c in ielts] == [UCT_LANGUAGE]
    scope = ielts[0].scope
    assert scope is not None and scope.degree is None and scope.programme is None
    assert "linking programme page" not in ielts[0].notes


async def test_a_linked_page_stating_master_is_still_withheld(routing, provider):
    provider({})
    candidate, program = _uct()
    result, fetcher = await _verify(_uct_pages(UCT_MASTER_LANGUAGE_PAGE), candidate, program)
    assert UCT_LANGUAGE in fetcher.calls
    assert not [c for c in result.claims if c.source_url == UCT_LANGUAGE]
    assert any(UCT_LANGUAGE in e and "QR-1" in e for e in result.errors)


async def test_a_question_page_is_read_once_per_institution(routing, provider):
    provider({})
    fetcher = _Fetcher(_uct_pages())
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    candidate, first = _uct()
    _, second = _uct(UCT_BSC_DS, "Data Science")
    one = await adapter.verify(candidate, first, "fall 2027")
    two = await adapter.verify(candidate, second, "fall 2027")
    assert fetcher.calls.count(UCT_LANGUAGE) == 1
    assert fetcher.calls.count(UCT_BSC_DS) == 1
    # The second programme reuses the first read's claims, unchanged.
    assert _ielts(two) and _ielts(two) == _ielts(one)
    reused = [o for o in two.page_outcomes if o.url == UCT_LANGUAGE]
    assert len(reused) == 1 and "QR-1b" in reused[0].detail
    assert two.pages_checked == 1


async def test_off_two_programmes_read_the_page_twice_with_no_inherited_scope(provider):
    provider({})
    tabled = UCT_LANGUAGE_PAGE.replace(
        "</body>",
        "<table><tr><th>Test</th><th>Overall score</th></tr>"
        "<tr><td>IELTS Academic</td><td>6.5</td></tr></table></body>",
    )
    fetcher = _Fetcher(_uct_pages(tabled))
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    candidate, first = _uct()
    _, second = _uct(UCT_BSC_DS, "Data Science")
    one = await adapter.verify(candidate, first, "fall 2027")
    await adapter.verify(candidate, second, "fall 2027")
    # Today's behaviour: the language link is followed for each programme.
    assert fetcher.calls.count(UCT_LANGUAGE) == 2
    ielts = _ielts(one)
    assert ielts and all(c.scope is not None and c.scope.degree is None for c in ielts)
    assert all("linking programme page" not in c.notes for c in one.claims)


IMPERIAL = "https://www.imperial.ac.uk"
IMPERIAL_PROGRAMME = f"{IMPERIAL}/study/courses/undergraduate/computing/"
IMPERIAL_DEADLINES = f"{IMPERIAL}/study/apply/undergraduate/process/deadlines/"
IMPERIAL_PROGRAMME_PAGE = f"""<html><head><title>Computing BEng | Imperial College London</title>
</head><body><h1>Computing BEng</h1><p>A three-year undergraduate programme.</p>
<p><a href="{IMPERIAL_DEADLINES}">Deadlines</a></p></body></html>"""
#: Classifies as program_detail (subject "Deadlines"), as Imperial's real page did.
IMPERIAL_DEADLINES_PAGE = """<html><head><title>Deadlines | Study | Imperial College London</title>
</head><body><h1>Deadlines</h1>
<p>Undergraduate applications for 2027 entry to our bachelor degree programmes are made through
UCAS.</p><p>The application deadline is 13 January 2027 for all courses.</p>
<p>Courses start in October 2027 for the fall 2027 intake.</p></body></html>"""


def _imperial() -> tuple[Candidate, CandidateProgram]:
    candidate = Candidate(
        name="Imperial College London",
        country="United Kingdom",
        city="",
        domain="www.imperial.ac.uk",
    )
    program = CandidateProgram(
        name="Computing", field="computing", degree=DegreeLevel.BACHELOR, url=IMPERIAL_PROGRAMME
    )
    return candidate, program


def test_the_deadlines_fixture_classifies_as_a_programme_page():
    text = readable_text(IMPERIAL_DEADLINES_PAGE)
    page = classify_page(url=IMPERIAL_DEADLINES, html=IMPERIAL_DEADLINES_PAGE, text=text)
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.accepts("requirements")


async def test_an_accepted_question_page_is_read_for_its_question_only(
    routing, provider, monkeypatch
):
    provider({})
    read: list[str] = []
    original = WebRequirementsAdapter._read_for_question

    def spy(self, question, res, page_url, text, builder):
        read.append(page_url)
        return original(self, question, res, page_url, text, builder)

    monkeypatch.setattr(WebRequirementsAdapter, "_read_for_question", spy)
    candidate, program = _imperial()
    pages = {
        IMPERIAL_PROGRAMME: IMPERIAL_PROGRAMME_PAGE,
        IMPERIAL_DEADLINES: IMPERIAL_DEADLINES_PAGE,
    }
    result, fetcher = await _verify(pages, candidate, program)
    assert IMPERIAL_DEADLINES in fetcher.calls
    assert read == [IMPERIAL_DEADLINES]
    from_deadlines = {c.claim_type for c in result.claims if c.source_url == IMPERIAL_DEADLINES}
    assert from_deadlines == {ClaimType.ADMISSION_DEADLINE}
    outcome = next(o for o in result.page_outcomes if o.url == IMPERIAL_DEADLINES)
    assert outcome.detail.startswith("deadline page:")


# --- QR-1c: the admissions page read beside the programme page carries its degree ---

UCT_ADMISSIONS = f"{UCT}/students/applications/international-applicants"


def _uct_admissions_page(lead: str = "") -> str:
    """UCT's "International applicants": degree-silent, links the language page."""
    return f"""<html><head><title>International applicants | Applicants &amp; Students</title>
</head><body><h1>International applicants</h1>{lead}<p>International applicants apply online.
See the <a href="{UCT_LANGUAGE}">language requirements</a> and the
<a href="{UCT}/students/applications/key-dates">key dates</a>.</p></body></html>"""


def _uct_with_admissions(
    url: str = UCT_BSC, name: str = "Computer Science"
) -> tuple[Candidate, CandidateProgram]:
    candidate, program = _uct(url, name)
    candidate.admissions_url = UCT_ADMISSIONS
    return candidate, program


def _uct_admissions_pages(admissions: str | None = None) -> dict[str, str]:
    return {
        # The programme page links no English page, as UCT's does not.
        **_uct_pages(link=False),
        UCT_ADMISSIONS: admissions or _uct_admissions_page(),
    }


def test_the_uct_admissions_fixture_is_degree_silent():
    text = readable_text(_uct_admissions_page())
    assert read_scope(text, title="International applicants").degree is None


async def test_a_page_linked_from_the_admissions_page_takes_the_programme_degree(routing, provider):
    provider({})
    candidate, program = _uct_with_admissions()
    result, fetcher = await _verify(_uct_admissions_pages(), candidate, program)
    assert fetcher.calls[:3] == [UCT_BSC, UCT_ADMISSIONS, UCT_LANGUAGE]
    ielts = _ielts(result)
    assert [(c.normalized_value, c.source_url) for c in ielts] == [(6.5, UCT_LANGUAGE)]
    scope = ielts[0].scope
    assert scope is not None and scope.degree == "bachelor"
    assert scope.programme == "Computer Science"
    assert "linked through the admissions page" in ielts[0].notes
    assert UCT_BSC in ielts[0].notes and UCT_ADMISSIONS in ielts[0].notes


async def test_an_admissions_page_stating_master_passes_on_nothing(routing, provider):
    provider({})
    candidate, program = _uct_with_admissions()
    admissions = _uct_admissions_page("<p>For applicants to a master's programme.</p>")
    assert read_scope(readable_text(admissions), title="International applicants").degree
    result, _ = await _verify(_uct_admissions_pages(admissions), candidate, program)
    ielts = _ielts(result)
    assert [c.source_url for c in ielts] == [UCT_LANGUAGE]
    scope = ielts[0].scope
    assert scope is not None and scope.degree is None
    assert "admissions page" not in ielts[0].notes


async def test_without_a_programme_page_the_admissions_page_passes_on_nothing(routing, provider):
    provider({})
    candidate, program = _uct_with_admissions()
    pages = _uct_admissions_pages()
    del pages[UCT_BSC]  # the programme page cannot be read
    result, _ = await _verify(pages, candidate, program)
    ielts = _ielts(result)
    assert [c.source_url for c in ielts] == [UCT_LANGUAGE]
    assert ielts[0].scope is not None and ielts[0].scope.degree is None


async def test_reused_claims_take_the_degree_of_the_route_that_reached_them(routing, provider):
    """A first programme reaches the page by topic search (no degree); the
    second links it from its own programme page and so reads it as bachelor."""
    provider({"English language": UCT_LANGUAGE})
    pages = {
        UCT_BSC: _uct_programme_page("Bachelor of Science in Computer Science", link=False),
        UCT_BSC_DS: _uct_programme_page("Bachelor of Science in Data Science", link=True),
        UCT_LANGUAGE: UCT_LANGUAGE_PAGE,
    }
    fetcher = _Fetcher(pages)
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    candidate, first = _uct()
    _, second = _uct(UCT_BSC_DS, "Data Science")
    one = await adapter.verify(candidate, first, "fall 2027")
    two = await adapter.verify(candidate, second, "fall 2027")
    assert fetcher.calls.count(UCT_LANGUAGE) == 1
    [topic] = _ielts(one)
    [linked] = _ielts(two)
    assert topic.scope is not None and topic.scope.degree is None
    assert linked.scope is not None and linked.scope.degree == "bachelor"
    assert UCT_BSC_DS in linked.notes
    # The first programme's claim is not changed by the second's route.
    assert "linking programme page" not in topic.notes


async def test_off_the_admissions_linked_page_is_rejected_as_unknown(provider):
    provider({})
    candidate, program = _uct_with_admissions()
    result, _ = await _verify(_uct_admissions_pages(), candidate, program)
    assert not [c for c in result.claims if c.source_url == UCT_LANGUAGE]
