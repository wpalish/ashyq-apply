"""ER-08: one public query per topic finds the official page that publishes it.

Expert traces (2026-10-04): Groningen, NTU and HKU state the English minimum,
the international fee and the deadline on pages the requirements adapter never
opened; one query each put that page first among the institution's results.
"""

from datetime import UTC, datetime

import pytest

import app.adapters.search as search_pkg
from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.search import SearchResponse, SearchResult, SearchUnavailable
from app.domain.enums import DegreeLevel


class Provider:
    name = "fake"

    def __init__(self, urls: list[str], fail: int | None = None) -> None:
        self.urls = urls
        self.fail = fail
        self.queries: list[str] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.queries.append(query)
        if self.fail is not None and len(self.queries) >= self.fail:
            raise SearchUnavailable("refused", http_status=429)
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=datetime.now(UTC),
            results=tuple(
                SearchResult(
                    url=u,
                    title="t",
                    provider=self.name,
                    rank=i + 1,
                    retrieved_at=datetime.now(UTC),
                )
                for i, u in enumerate(self.urls)
            ),
        )


def candidate() -> Candidate:
    return Candidate(
        name="University of Groningen", country="Netherlands", city="", domain="www.rug.nl"
    )


def program() -> CandidateProgram:
    return CandidateProgram(
        name="Computing Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="https://www.rug.nl/bachelors/computing-science/",
    )


@pytest.fixture
def provider(monkeypatch):
    def install(urls, fail=None):
        built = Provider(urls, fail)
        monkeypatch.setattr(search_pkg, "get_search_provider", lambda: built)
        return built

    return install


def test_the_rule_is_on_by_default():
    """On since the 10-case paired run 37279746829 (owner approved 2026-10-05)."""
    assert web_requirements.TOPIC_SEARCH is True


async def test_one_official_page_per_topic_and_off_site_pages_are_skipped(provider):
    built = provider(
        [
            "https://www.studyportals.com/groningen-fees",
            "https://www.rug.nl/masters/computing-science/",
            "https://www.rug.nl/news/2026/fees-rise",
            "https://www.rug.nl/education/tuition-fee/bachelor",
        ]
    )
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    pages = await adapter._find_topic_pages(candidate(), program(), AdapterResult())
    assert pages == (("english", "https://www.rug.nl/education/tuition-fee/bachelor"),)
    assert len(built.queries) == 3
    assert all("Groningen" in q for q in built.queries)


async def test_queries_are_sent_once_per_institution(provider):
    built = provider(["https://www.rug.nl/a", "https://www.rug.nl/b", "https://www.rug.nl/c"])
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    first = await adapter._find_topic_pages(candidate(), program(), AdapterResult())
    again = await adapter._find_topic_pages(candidate(), program(), AdapterResult())
    assert first == again
    assert [t for t, _ in first] == ["english", "fees", "deadline"]
    assert len(built.queries) == 3


async def test_a_refusal_stops_the_topic_search_and_is_recorded(provider):
    built = provider(["https://www.rug.nl/a"], fail=2)
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    out = AdapterResult()
    pages = await adapter._find_topic_pages(candidate(), program(), out)
    assert pages == (("english", "https://www.rug.nl/a"),)
    assert len(built.queries) == 2
    assert any("Topic search (fees)" in e for e in out.errors)


async def test_topic_search_spends_only_what_discovery_left(provider, monkeypatch):
    """One institution gets six queries in all, discovery's included.

    Pinned to the reader before BL-1; under BL-1 (default since 2026-10-06)
    the last query is the scholarship search's, which
    test_shared_query_budget covers.
    """
    from app.adapters.search import intent

    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", False)
    built = provider(["https://www.rug.nl/a", "https://www.rug.nl/b", "https://www.rug.nl/c"])
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    spent = candidate()
    spent.search_queries_used = 5
    pages = await adapter._find_topic_pages(spent, program(), AdapterResult())
    assert [t for t, _ in pages] == ["english"]
    assert len(built.queries) == 1


async def test_no_topic_query_once_discovery_spent_the_budget(provider):
    built = provider(["https://www.rug.nl/a"])
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    spent = candidate()
    spent.search_queries_used = 6
    out = AdapterResult()
    assert await adapter._find_topic_pages(spent, program(), out) == ()
    assert built.queries == []
    assert any("Topic search not run" in e for e in out.errors)


class _FailsOnce(Provider):
    """The first topic query fails without a 429; the rest answer."""

    async def search(self, *, query, domains=(), max_results=10):
        if not self.queries:
            self.queries.append(query)
            raise SearchUnavailable("transient")
        return await super().search(query=query, domains=domains, max_results=max_results)


def _install(monkeypatch, built):
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: built)
    return built


async def test_ts2_off_one_failed_topic_ends_topic_search(monkeypatch):
    built = _install(monkeypatch, _FailsOnce(["https://www.rug.nl/a", "https://www.rug.nl/b"]))
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    pages = await adapter._find_topic_pages(candidate(), program(), AdapterResult())
    assert pages == ()
    assert len(built.queries) == 1


async def test_ts2_on_the_other_topics_are_still_asked(monkeypatch):
    from app.adapters.requirements import web_requirements

    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH_CONTINUE", True)
    built = _install(monkeypatch, _FailsOnce(["https://www.rug.nl/a", "https://www.rug.nl/b"]))
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    out = AdapterResult()
    pages = await adapter._find_topic_pages(candidate(), program(), out)
    assert [t for t, _ in pages] == ["fees", "deadline"]
    assert len(built.queries) == 3
    assert any("Topic search (english)" in e for e in out.errors)


async def test_ts2_on_a_429_still_stops(monkeypatch, provider):
    from app.adapters.requirements import web_requirements

    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH_CONTINUE", True)
    built = provider(["https://www.rug.nl/a"], fail=1)
    adapter = WebRequirementsAdapter(None, "2027/28")  # type: ignore[arg-type]
    assert await adapter._find_topic_pages(candidate(), program(), AdapterResult()) == ()
    assert len(built.queries) == 1
