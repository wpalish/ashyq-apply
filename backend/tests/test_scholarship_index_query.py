"""Plan rule SQ-1 (core-gap analysis 2026-10-18 §3 change 8): one scholarship-index
query when the site offered no index that links an award.

Uppsala's funding walk starts from the programme page (no scholarships page was
selected; it links only the fee page) and the award query returned a faculty
page, though ``/en/study/bachelors-studies/scholarships`` lists the gold award
first. Groningen's ``/education/scholarships`` renders its list client-side, so
its markup links no award. The Uppsala programme page and both indexes are the
real pages, hand-fetched 2026-10-18 and trimmed to the markup that decides; the
award pages are minimal reconstructions with the gold's eligibility sentence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.adapters import search
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.scholarship import web_scholarships
from app.adapters.search import intent as intent_module
from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable
from app.domain.enums import DegreeLevel
from tests.test_intake_section_deadline import UPPSALA_HTML, UPPSALA_URL
from tests.test_live_discovery import StubSite

UU = "https://www.uu.se"
UU_INDEX = f"{UU}/en/study/bachelors-studies/scholarships"
UU_AWARD = f"{UU}/en/study/bachelors-studies/scholarships/uppsala-university-scholarships"
UU_FACULTY = f"{UU}/en/department/earth-sciences/environmental-scholarships"
#: https://www.uu.se/en/study/bachelors-studies/scholarships, trimmed.
UU_INDEX_HTML = f"""<html><head><title>Scholarships for prospective Bachelor's students -
Uppsala University</title></head><body><main>
<h1>Scholarships for prospective Bachelor's students</h1>
<p>Uppsala University has a very limited number of scholarships that will cover tuition fees
for international students admitted to our Bachelor’s programmes, and only students from a
select number of countries can apply.</p>
<div class="card"><h2 class="card-title"><a href="{UU_AWARD}">Uppsala University's
scholarships</a></h2><p>Read about the scholarships offered by Uppsala University to
fee-paying students.</p></div>
<div class="card"><h2 class="card-title"><a
href="/en/study/bachelors-studies/scholarships/application-guide">How to apply?</a></h2>
<p>Complete your scholarship application online with this step-by-step application guide.</p>
</div>
<h3>Further resources</h3><ul>
<li><a href="/en/students/student-life/student-finance/scholarships">Scholarships for current
students</a></li><li><a href="/en/study/fees">Application and tuition fees</a></li></ul>
</main></body></html>"""
UU_AWARD_HTML = """<html><head><title>Anders Wall Scholarship</title></head><body>
<h1>Anders Wall Scholarship</h1>
<p>The Anders Wall Scholarship covers full tuition for fee-paying students.</p>
<p>Eligibility: open to international students admitted to a Bachelor's programme.</p>
<p>The award is worth SEK 150,000 per year and the deadline is 1 February 2027.</p>
</body></html>"""

RUG = "https://www.rug.nl"
RUG_INDEX = f"{RUG}/education/scholarships"
RUG_AWARD = f"{RUG}/education/scholarships/nl-scholarship"
RUG_PROGRAMME = f"{RUG}/bachelors/computing-science/"
#: https://www.rug.nl/education/scholarships, trimmed: the award list is
#: rendered client-side, so the markup links none.
RUG_INDEX_HTML = """<html><head><title>Financial matters | Education | University of
Groningen</title></head><body><main><h1>Financial matters</h1><h2>Value for money</h2>
<p>Higher education in the Netherlands is subsidized to uphold its high academic standards.
This means tuition fees are relatively low.</p>
<p>The university is committed to recognizing excellence in academic achievement through
offering a number of scholarships for international students and researchers. Several
scholarships are available for international students who are motivated to study Bachelor’s
programmes, Master’s programmes or PhD programmes.</p>
<p>Please use the menu on the left for more detailed information.</p>
<div id="scholarship-finder" data-src="/api/scholarships"></div></main></body></html>"""
RUG_AWARD_HTML = """<html><head><title>NL Scholarship</title></head><body>
<h1>NL Scholarship</h1>
<p>The NL Scholarship covers EUR 5,000 of tuition in the first year of study.</p>
<p>Eligibility: open to international students from outside the EEA.</p>
<p>Selection criteria | Purposes: Master (MSc/MA/LL.M.), Bachelor (BSc/BA/LL.B) |
Programmes: All | Countries of Origin: All</p>
<p>The deadline is 1 February 2027.</p></body></html>"""
RUG_PROGRAMME_HTML = """<html><head><title>Computing Science | University of Groningen</title>
</head><body><h1>Computing Science</h1><p>Bachelor of Science, three years.</p></body></html>"""


class Provider:
    name = "fake"

    def __init__(self, answers: dict[str, list[str]]) -> None:
        self.answers = answers
        self.calls: list[dict[str, Any]] = []

    async def search(self, **kwargs: Any) -> SearchResponse:
        self.calls.append(kwargs)
        now = datetime.now(UTC)
        urls = next((u for word, u in self.answers.items() if word in kwargs["query"]), [])
        return SearchResponse(
            kwargs["query"],
            self.name,
            now,
            tuple(SearchResult(u, "t", self.name, i + 1, now) for i, u in enumerate(urls)),
        )


@pytest.fixture
def sq1(monkeypatch):
    monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_INDEX_QUERY", True)


def _program(url: str) -> CandidateProgram:
    return CandidateProgram(
        name="Computer Science", field="computer science", degree=DegreeLevel.BACHELOR, url=url
    )


async def _find(
    tmp_path, monkeypatch, provider, pages, candidate, program
) -> tuple[list[Any], Any, StubSite]:
    monkeypatch.setattr(search, "get_search_provider", lambda: provider)
    site = StubSite(pages)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = web_scholarships.WebScholarshipAdapter(fetcher, "2027/28")
        awards, result = await adapter.find(candidate, program, None)
    return awards, result, site


def _uppsala(used: int = 0) -> Candidate:
    candidate = Candidate(
        name="Uppsala University", country="Sweden", city="Uppsala", domain="uu.se"
    )
    candidate.search_queries_used = used
    return candidate


def _uppsala_pages() -> dict[str, str]:
    return {UPPSALA_URL: UPPSALA_HTML, UU_INDEX: UU_INDEX_HTML, UU_AWARD: UU_AWARD_HTML}


def _uppsala_provider() -> Provider:
    return Provider(
        {
            # The index family returns the index first; the award family a faculty page.
            "scholarships for international": [UU_INDEX, UU_FACULTY],
            "eligibility benefits": [UU_FACULTY],
        }
    )


def _families(provider: Provider) -> list[str]:
    return [
        "index" if "scholarships for international" in c["query"] else "award"
        for c in provider.calls
    ]


def test_on_by_default():
    assert web_scholarships.SCHOLARSHIP_INDEX_QUERY is True


async def test_off_uppsala_sends_the_award_query_only(tmp_path, monkeypatch):
    monkeypatch.setattr(web_scholarships, "SCHOLARSHIP_INDEX_QUERY", False)
    provider = _uppsala_provider()
    awards, _, site = await _find(
        tmp_path, monkeypatch, provider, _uppsala_pages(), _uppsala(), _program(UPPSALA_URL)
    )
    assert _families(provider) == ["award"]
    assert awards == []
    assert UU_INDEX not in site.requested


async def test_on_uppsala_reads_the_index_the_query_returns(tmp_path, monkeypatch, sq1):
    provider = _uppsala_provider()
    candidate = _uppsala(used=3)
    awards, _, site = await _find(
        tmp_path, monkeypatch, provider, _uppsala_pages(), candidate, _program(UPPSALA_URL)
    )
    assert _families(provider) == ["index"]
    query = provider.calls[0]
    assert query["query"] == (
        "Uppsala University scholarships for international bachelor's students"
    )
    assert query["domains"] == ["uu.se"]
    assert "computer science" not in query["query"].lower()
    # Only the top result is a lead; the index is read as one and its award parsed.
    assert UU_FACULTY not in site.requested
    assert [a.name for a in awards] == ["Anders Wall Scholarship"]
    assert candidate.search_queries_used == 4


async def test_the_shared_budget_is_never_exceeded(tmp_path, monkeypatch, sq1):
    provider = _uppsala_provider()
    full = _uppsala(used=intent_module.DEFAULT_QUERY_BUDGET)
    awards, result, _ = await _find(
        tmp_path, monkeypatch, provider, _uppsala_pages(), full, _program(UPPSALA_URL)
    )
    assert provider.calls == [] and awards == []
    assert full.search_queries_used == intent_module.DEFAULT_QUERY_BUDGET
    assert any("6-query budget" in e for e in result.errors)


async def test_with_one_query_left_the_index_query_takes_it(tmp_path, monkeypatch, sq1):
    provider = Provider({"scholarships for international": [UU_FACULTY]})
    last = _uppsala(used=intent_module.DEFAULT_QUERY_BUDGET - 1)
    await _find(tmp_path, monkeypatch, provider, _uppsala_pages(), last, _program(UPPSALA_URL))
    # The index query finds nothing; the award query is refused, not a 7th.
    assert _families(provider) == ["index"]
    assert last.search_queries_used == intent_module.DEFAULT_QUERY_BUDGET


async def test_both_queries_inside_the_budget_when_the_index_finds_nothing(
    tmp_path, monkeypatch, sq1
):
    provider = Provider({"scholarships for international": [UU_FACULTY]})
    candidate = _uppsala(used=2)
    await _find(tmp_path, monkeypatch, provider, _uppsala_pages(), candidate, _program(UPPSALA_URL))
    assert _families(provider) == ["index", "award"]
    assert candidate.search_queries_used == 4


async def test_not_sent_without_the_shared_budget(tmp_path, monkeypatch, sq1):
    monkeypatch.setattr(intent_module, "SHARED_QUERY_BUDGET", False)
    provider = _uppsala_provider()
    await _find(
        tmp_path, monkeypatch, provider, _uppsala_pages(), _uppsala(), _program(UPPSALA_URL)
    )
    assert _families(provider) == ["award"]


async def test_not_sent_when_the_site_index_linked_an_award(tmp_path, monkeypatch, sq1):
    provider = _uppsala_provider()
    candidate = _uppsala()
    candidate.scholarships_url = UU_INDEX
    awards, _, _ = await _find(
        tmp_path, monkeypatch, provider, _uppsala_pages(), candidate, _program(UPPSALA_URL)
    )
    assert [a.name for a in awards] == ["Anders Wall Scholarship"]
    assert provider.calls == []


async def test_groningen_reads_the_award_the_query_returns(tmp_path, monkeypatch, sq1):
    provider = Provider({"scholarships for international": [RUG_AWARD]})
    candidate = Candidate(
        name="University of Groningen",
        country="Netherlands",
        city="Groningen",
        domain="rug.nl",
        scholarships_url=RUG_INDEX,
    )
    awards, result, site = await _find(
        tmp_path,
        monkeypatch,
        provider,
        {RUG_INDEX: RUG_INDEX_HTML, RUG_AWARD: RUG_AWARD_HTML, RUG_PROGRAMME: RUG_PROGRAMME_HTML},
        candidate,
        _program(RUG_PROGRAMME),
    )
    assert _families(provider) == ["index"]
    # One award page, read as that award (not as an index that records nothing).
    assert [a.name for a in awards] == ["NL Scholarship"]
    assert any(c.source_url == RUG_AWARD for c in result.claims)


@pytest.mark.parametrize("status", [400, 429])
async def test_a_failed_index_query_is_not_followed_by_the_award_query(
    tmp_path, monkeypatch, sq1, status
):
    class Failing(Provider):
        async def search(self, **kwargs: Any) -> SearchResponse:
            self.calls.append(kwargs)
            raise SearchUnavailable("quota", http_status=status)

    provider = Failing({})
    candidate = _uppsala(used=2)
    awards, result, _ = await _find(
        tmp_path, monkeypatch, provider, _uppsala_pages(), candidate, _program(UPPSALA_URL)
    )
    # One failure, one query spent: the award family is not a retry in disguise.
    assert _families(provider) == ["index"]
    assert awards == [] and result.claims == []
    assert candidate.search_queries_used == 3
    assert sum("Official scholarship search:" in e for e in result.errors) == 1
