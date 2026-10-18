"""Plan rule SB-1: discovery gets a deadline, a read cap and a stop condition.

Structural analysis 2026-10-18 §2 F3: discovery had no stage budget, so the
first stages consumed whatever they could. UBC spent 78 s on navigation before
its first query, Imperial and UNSW never queried, and after the walker
confirmed Groningen's and TCD's pages the run kept reading. Offline: a fake
clock advances by a fixed cost per read; search goes to a fake provider.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import CatalogWalker
from app.adapters.discovery.live_discovery import (
    DISCOVERY_DEADLINE_SECONDS,
    SLOW_HOST_SITEMAP_DOCUMENTS,
    LiveDiscoveryAdapter,
    StageBudget,
)
from app.adapters.fetching import Fetcher
from app.adapters.search import retrieval
from app.adapters.search.base import SearchResponse, SearchResult
from tests.test_live_discovery import (
    StubSite,
    _catalogue_html,
    program_html,
    sitemap_index_xml,
    sitemap_xml,
)

HOME = "https://uni.edu/"
CATALOGUE = "https://uni.edu/study/catalogue"
PROGRAMME = "https://uni.edu/programmes/bachelors/computer-science"
TWIN = "https://uni.edu/programmes/bachelors/computer-science-and-engineering"
CHILDREN = [f"https://uni.edu/s{i}.xml" for i in range(1, 6)]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Provider:
    """Returns ``answers`` for every query and counts the queries."""

    name = "fake"

    def __init__(self, answers: list[str], clock: FakeClock) -> None:
        self.answers = answers
        self.clock = clock
        self.sent_at: list[float] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.sent_at.append(self.clock.now)
        now = datetime.now(UTC)
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=now,
            results=tuple(
                SearchResult(
                    url=url,
                    title="BSc Computer Science",
                    provider=self.name,
                    rank=i + 1,
                    retrieved_at=now,
                )
                for i, url in enumerate(self.answers)
            ),
        )


def _junk(n: int) -> list[str]:
    """Programme-shaped sitemap leads that do not exist (404)."""
    return [f"https://uni.edu/programmes/bachelors/computer-science-{i}" for i in range(n)]


def _pages(*, programme_in: str | None = "s1", junk: int = 0) -> dict[str, bytes | str]:
    pages: dict[str, bytes | str] = {
        "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/index.xml\n",
        "https://uni.edu/index.xml": sitemap_index_xml(*CHILDREN),
        PROGRAMME: program_html(),
        TWIN: program_html("BSc Computer Science and Engineering"),
    }
    for i, child in enumerate(CHILDREN):
        pages[child] = sitemap_xml(f"https://uni.edu/about-{i}")
    if programme_in is not None:
        pages[f"https://uni.edu/{programme_in}.xml"] = sitemap_xml(PROGRAMME, *_junk(junk))
    elif junk:
        pages["https://uni.edu/s1.xml"] = sitemap_xml(*_junk(junk))
    return pages


async def _run(
    tmp_path,
    profile,
    monkeypatch,
    *,
    flag: bool,
    seconds_per_read: float,
    pages: dict[str, bytes | str],
    seeds: dict | None = None,
    answers: list[str] | None = None,
):
    monkeypatch.setattr(live_discovery, "STAGE_BUDGETS", flag)
    clock = FakeClock()
    monkeypatch.setattr(live_discovery, "_clock", clock)
    site = StubSite(pages)
    entry: dict[str, object] = {"name": "U", "country": "Turkey", "city": "X", "homepage": HOME}
    if seeds:
        entry["seeds"] = seeds
    tmp_path.mkdir(parents=True, exist_ok=True)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([entry]))
    provider = Provider(answers, clock) if answers is not None else None
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        stub_get = fetcher.get

        async def timed_get(url, **kwargs):
            clock.now += seconds_per_read
            return await stub_get(url, **kwargs)

        fetcher.get = timed_get  # type: ignore[method-assign]
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        adapter._search_provider = provider  # type: ignore[assignment]
        adapter._search_provider_resolved = True
        candidates = await adapter.discover(profile)
        assert adapter.fetcher is fetcher, "the budgeted wrapper is removed after discovery"
    return candidates[0], adapter.traces[0], site, provider, clock


@pytest.fixture
def cs_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


class TestStageBudget:
    def test_deadline_and_read_cap_latch(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget(deadline_seconds=10, read_cap=2)
        assert not budget.exhausted()
        clock.now = 10.0
        assert budget.exhausted()
        assert budget.stopped_by == "deadline"
        clock.now = 0.0
        assert budget.exhausted(), "a spent budget stays spent"

    def test_seconds_go_to_the_stage_that_spent_them(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget()
        clock.now = 3.0
        budget.enter("confirm")
        clock.now = 7.0
        budget.query_sent()
        report = budget.as_dict()
        assert report["stage_seconds"]["sitemap"] == 3.0
        assert report["stage_seconds"]["confirm"] == 4.0
        assert report["t_first_query"] == 7.0
        assert report["deadline_seconds"] == DISCOVERY_DEADLINE_SECONDS


class TestDeadline:
    @pytest.mark.asyncio
    async def test_deadline_ends_discovery_and_keeps_the_confirmed_page(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        candidate, trace, site, _, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=4.0,
            pages=_pages(junk=8),
        )
        report = trace.as_dict()["stage_budget"]
        assert report["stopped_by"] == "deadline"
        assert report["stopped_in"] == "confirm"
        # No read starts after the deadline; the last one may end past it.
        assert clock.now < DISCOVERY_DEADLINE_SECONDS + 4.0
        assert report["refused_reads"] == 0, "stages check before they read"
        # The verify stage's input: the confirmed programme page.
        assert [program.url for program in candidate.programs] == [PROGRAMME]
        assert trace.stage_order[-2:] == ["walker_skipped", "search_skipped"]
        assert any("not read: the discovery stage budget is spent" in r for _, r in trace.rejected)

    @pytest.mark.asyncio
    async def test_read_cap_ends_discovery(self, tmp_path, cs_bachelor, monkeypatch):
        monkeypatch.setattr(live_discovery, "DISCOVERY_READ_CAP", 9)
        candidate, trace, site, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=_pages(junk=8),
        )
        assert len(site.requested) == 9
        assert trace.stage_budget["stopped_by"] == "read_cap"
        assert [program.url for program in candidate.programs] == [PROGRAMME]

    @pytest.mark.asyncio
    async def test_flag_off_reads_past_the_deadline(self, tmp_path, cs_bachelor, monkeypatch):
        candidate, trace, site, _, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=4.0,
            pages=_pages(junk=8),
        )
        assert clock.now > DISCOVERY_DEADLINE_SECONDS
        assert len([u for u in site.requested if "computer-science" in u]) == 8
        assert "stage_budget" not in trace.as_dict()
        assert "stage_order" not in trace.as_dict()
        assert [program.url for program in candidate.programs] == [PROGRAMME]


class TestStopWhenConfirmed:
    @pytest.mark.asyncio
    async def test_a_confirmed_page_skips_the_walker(self, tmp_path, cs_bachelor, monkeypatch):
        seeds = {"program_catalog": CATALOGUE}
        pages = {**_pages(), CATALOGUE: _catalogue_html((TWIN, "Computer Science and Eng"))}
        _, off_trace, off_site, _, _ = await _run(
            tmp_path / "off",
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=0.1,
            pages=pages,
            seeds=seeds,
        )
        assert CATALOGUE in off_site.requested, "today the walker reads the catalogue"
        _, trace, site, _, _ = await _run(
            tmp_path / "on",
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=pages,
            seeds=seeds,
        )
        assert CATALOGUE not in site.requested
        assert "walker_skipped" in trace.stage_order
        assert trace.walker["catalogs_walked"] == 0

    @pytest.mark.asyncio
    async def test_walker_reads_no_lead_after_a_confirmation(self, tmp_path):
        site = StubSite(
            {
                CATALOGUE: _catalogue_html(
                    (PROGRAMME, "Computer Science"),
                    (TWIN, "Computer Science and Engineering"),
                ),
                PROGRAMME: program_html(),
                TWIN: program_html("BSc Computer Science and Engineering"),
            }
        )

        async def walk(stop_when_confirmed: bool) -> list[str]:
            site.requested.clear()
            async with Fetcher(tmp_path / f"c{stop_when_confirmed}", offline=True) as fetcher:
                site.install(fetcher)
                walker = CatalogWalker(
                    fetcher=fetcher,
                    domain="uni.edu",
                    degree="bachelor",
                    fields=["computer science"],
                    stop_when_confirmed=stop_when_confirmed,
                )
                walks = await walker.walk([CATALOGUE])
            return walks[0].confirmed

        assert sorted(await walk(False)) == sorted([PROGRAMME, TWIN])
        assert len(await walk(True)) == 1
        assert len(site.requested) == 2, "the catalogue and one lead"

    @pytest.mark.asyncio
    async def test_recovery_stops_at_its_first_confirmation_and_no_second_pass(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        pages = _pages(programme_in=None)
        _, off_trace, off_site, off_provider, _ = await _run(
            tmp_path / "off",
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=0.1,
            pages=pages,
            answers=[PROGRAMME, TWIN],
        )
        assert TWIN in off_site.requested
        _, trace, site, provider, _ = await _run(
            tmp_path / "on",
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=pages,
            answers=[PROGRAMME, TWIN],
        )
        assert PROGRAMME in site.requested
        assert TWIN not in site.requested
        assert trace.selected["program_page"] == [PROGRAMME]
        assert trace.discovery_query_passes == [3], "no second pass after a confirmation"
        assert provider is not None and len(provider.sent_at) == 3

    @pytest.mark.asyncio
    async def test_hop_roots_are_skipped_when_a_candidate_exists(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        hops: list[int] = []
        real = retrieval.discover_candidates

        async def spy(*args, **kwargs):
            hops.append(kwargs.get("hop_entry_points", retrieval.DEFAULT_HOP_ENTRY_POINTS))
            return await real(*args, **kwargs)

        monkeypatch.setattr(retrieval, "discover_candidates", spy)
        # The sitemap offers programme leads, none of which exists.
        pages = _pages(programme_in=None, junk=2)
        _, trace, site, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=pages,
            answers=[PROGRAMME],
        )
        assert hops and hops[0] == 0
        assert HOME not in site.requested
        assert any("SB-1: no entry-point hop" in line for line in trace.errors)


class TestSlowHost:
    @pytest.mark.asyncio
    async def test_slow_host_searches_after_the_first_sitemap_document(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        candidate, trace, site, provider, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=10.0,
            pages=_pages(programme_in=None),
            answers=[PROGRAMME],
        )
        assert provider is not None
        # robots.txt and the index, then the first query.
        assert provider.sent_at[0] == 20.0
        assert trace.stage_budget["t_first_query"] == 20.0
        # Search confirmed the page, so no further sitemap document is read.
        assert not any(child in site.requested for child in CHILDREN)
        assert site.requested.count(PROGRAMME) == 1, "confirm trusts recovery's read"
        assert [program.url for program in candidate.programs] == [PROGRAMME]
        assert trace.stage_order == ["sitemaps", "search", "confirm", "walker_skipped"]
        assert trace.host_cost["slow"] is True

    @pytest.mark.asyncio
    async def test_slow_host_without_a_search_page_reads_three_sitemap_documents(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        _, trace, site, provider, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=6.0,
            pages=_pages(programme_in="s1"),
            answers=[],
        )
        sitemap_documents = [u for u in site.requested if u.endswith(".xml")]
        assert len(sitemap_documents) == SLOW_HOST_SITEMAP_DOCUMENTS
        assert provider is not None and provider.sent_at[0] == 12.0
        assert trace.stage_order[:2] == ["sitemaps", "search"]
        assert "walker_skipped" in trace.stage_order
        assert trace.stage_order.count("search") == 1

    @pytest.mark.asyncio
    async def test_fast_host_keeps_todays_order(self, tmp_path, cs_bachelor, monkeypatch):
        _, trace, site, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=1.0,
            pages=_pages(programme_in="s1"),
            answers=[],
        )
        assert len([u for u in site.requested if u.endswith(".xml")]) == 6
        assert trace.stage_order == ["sitemaps", "confirm", "walker_skipped", "search"]
        assert trace.host_cost["slow"] is False


class TestTrace:
    @pytest.mark.asyncio
    async def test_trace_has_seconds_and_reads_per_stage(self, tmp_path, cs_bachelor, monkeypatch):
        _, trace, site, _, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=1.0,
            pages=_pages(programme_in="s1"),
            answers=[TWIN],
        )
        report = trace.as_dict()["stage_budget"]
        assert set(report["stage_seconds"]) == {
            "sitemap",
            "navigation",
            "walker",
            "confirm",
            "search",
            "recovery",
        }
        assert report["stage_reads"]["sitemap"] == 7  # robots, index, five children
        assert report["stage_reads"]["confirm"] == 1
        assert report["reads"] == len(site.requested)
        assert sum(report["stage_seconds"].values()) == pytest.approx(clock.now)
        assert report["seconds"] == pytest.approx(clock.now)
        assert report["t_first_query"] == 8.0
        assert report["stopped_by"] is None
