"""A JS catalogue is an empty source response, not absence of scholarships."""

from datetime import UTC, datetime

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.scholarship import web_scholarships
from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable
from app.domain.enums import DegreeLevel
from tests.test_live_discovery import StubSite
from tests.test_scholarship_index_walk import _AWARD


class Provider:
    name = "fake"

    def __init__(self, urls, fail=False):
        self.urls = urls
        self.calls = []
        self.fail = fail

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise SearchUnavailable("quota")
        now = datetime.now(UTC)
        return SearchResponse(
            kwargs["query"],
            self.name,
            now,
            tuple(
                SearchResult(
                    url,
                    "Global Scholarship",
                    self.name,
                    i + 1,
                    now,
                    snippet="Full tuition even if the page cannot be fetched",
                )
                for i, url in enumerate(self.urls)
            ),
        )


async def run(tmp_path, monkeypatch, provider, award_body=_AWARD.format(name="Global Scholarship")):
    from app.adapters import search

    monkeypatch.setattr(web_scholarships, "SEARCH_FUNDING_FALLBACK", True)
    monkeypatch.setattr(search, "get_search_provider", lambda: provider)
    index = "https://uni.edu/scholarships"
    award = "https://uni.edu/global-scholarship"
    site = StubSite(
        {index: "<h1>Scholarships</h1><form>JS results loading</form>", award: award_body}
    )
    candidate = Candidate(
        name="Test University",
        country="Testland",
        city="Test",
        domain="uni.edu",
        scholarships_url=index,
    )
    program = CandidateProgram(
        name="Computer Science", field="computer science", degree=DegreeLevel.BACHELOR
    )
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = web_scholarships.WebScholarshipAdapter(fetcher, "2026/27")
        awards, result = await adapter.find(candidate, program, None)
        await adapter.find(
            candidate,
            CandidateProgram(name="Mathematics", field="mathematics", degree=DegreeLevel.BACHELOR),
            None,
        )
    return awards, result, site


@pytest.mark.asyncio
async def test_a_js_index_reaches_the_official_award_by_search(tmp_path, monkeypatch):
    provider = Provider(["https://other.edu/award", "https://uni.edu/global-scholarship"])
    awards, result, site = await run(tmp_path, monkeypatch, provider)
    assert [a.name for a in awards] == ["Global Scholarship"], result.errors
    assert result.claims
    assert "https://other.edu/award" not in site.requested
    assert len(provider.calls) == 1
    assert provider.calls[0]["domains"] == ["uni.edu"]
    assert "international" in provider.calls[0]["query"]


@pytest.mark.asyncio
async def test_a_search_summary_cannot_verify_an_unreachable_award(tmp_path, monkeypatch):
    awards, result, _ = await run(
        tmp_path, monkeypatch, Provider(["https://uni.edu/global-scholarship"]), award_body=None
    )
    assert awards == []
    assert result.claims == []


@pytest.mark.asyncio
async def test_provider_failure_stays_unknown_and_does_not_retry(tmp_path, monkeypatch):
    provider = Provider([], fail=True)
    awards, result, _ = await run(tmp_path, monkeypatch, provider)
    assert awards == []
    assert result.claims == []
    assert len(provider.calls) == 1
    assert any("search unavailable" in e for e in result.errors)


def test_global_menu_awards_do_not_consume_the_content_budget(monkeypatch):
    monkeypatch.setattr(web_scholarships, "SEARCH_FUNDING_FALLBACK", True)
    html = (
        "<nav><a href='/research-award'>Research Award</a></nav>"
        "<main><h1>Scholarships</h1><p>"
        + "Public scholarship information. " * 10
        + "</p><a href='/global-scholarship'>Global Scholarship</a></main>"
    )
    assert web_scholarships._award_links(html, "https://uni.edu/scholarships") == [
        "https://uni.edu/global-scholarship"
    ]
