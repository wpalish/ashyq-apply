"""Plan rule SO-1: on a slow host, search before the reads that cost the clock.

METU (discovery analysis 2026-10-17 §1.4) answers every read in ~10 s under
``Crawl-delay: 10``; the stage order spent the case's clock on sitemaps,
navigation and confirm and never reached search, which costs no page read.
Offline: a fake clock advances by a fixed cost per read, and search and the
walker are recorders.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    SLOW_HOST_SITEMAP_DOCUMENTS,
    HostCost,
    LiveDiscoveryAdapter,
)
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

HOME = "https://uni.edu/"
CATALOGUE = "https://uni.edu/study/catalogue"
PROGRAMME = "https://uni.edu/programmes/bachelors/computer-science"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _entry() -> dict:
    return {
        "name": "U",
        "country": "Turkey",
        "city": "X",
        "homepage": HOME,
        "seeds": {"program_catalog": CATALOGUE},
    }


def _site(*, programme_in_sitemap: bool) -> StubSite:
    children = [f"https://uni.edu/s{i}.xml" for i in range(1, 6)]
    pages: dict[str, bytes | str] = {
        "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/index.xml\n",
        "https://uni.edu/index.xml": sitemap_index_xml(*children),
    }
    for i, child in enumerate(children):
        pages[child] = sitemap_xml(f"https://uni.edu/about-{i}")
    if programme_in_sitemap:
        pages["https://uni.edu/s1.xml"] = sitemap_xml(PROGRAMME)
    return StubSite(pages)


async def _run(
    tmp_path, profile, monkeypatch, *, flag, seconds_per_read, programme, crawl_delay=None
):
    monkeypatch.setattr(live_discovery, "COST_AWARE_SEARCH_ORDER", flag)
    clock = FakeClock()
    monkeypatch.setattr(live_discovery, "_clock", clock)
    events: list[tuple[str, int]] = []
    site = _site(programme_in_sitemap=programme)

    async def fake_search(self, entry, domain, selected, trace, profile):
        events.append(("search", len(site.requested)))

    async def fake_walk(self, entry, selected, trace, profile):
        events.append(("walker", len(site.requested)))

    monkeypatch.setattr(LiveDiscoveryAdapter, "_add_search_results", fake_search)
    monkeypatch.setattr(LiveDiscoveryAdapter, "_walk_catalogs", fake_walk)

    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([_entry()]))
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        stub_get = fetcher.get

        async def slow_get(url, **kwargs):
            clock.now += seconds_per_read
            return await stub_get(url, **kwargs)

        fetcher.get = slow_get  # type: ignore[method-assign]
        if crawl_delay is not None:

            async def asked(url):
                return crawl_delay

            monkeypatch.setattr(fetcher.robots, "crawl_delay", asked)
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        await adapter.discover(profile)
    return adapter.traces[0], site, events


@pytest.fixture
def cs_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


class TestHostCost:
    def test_two_slow_reads_make_a_slow_host(self):
        cost = HostCost()
        cost.read_seconds = [1.0, 10.2]
        assert cost.median_read_seconds == pytest.approx(5.6)
        assert cost.slow
        assert cost.document_cap() == SLOW_HOST_SITEMAP_DOCUMENTS

    def test_one_read_says_nothing(self):
        cost = HostCost()
        cost.read_seconds = [30.0]
        assert not cost.slow

    def test_a_crawl_delay_alone_makes_a_slow_host(self):
        cost = HostCost()
        cost.crawl_delay = 5.0
        assert cost.slow


class TestCostAwareSearchOrder:
    @pytest.mark.asyncio
    async def test_slow_host_searches_before_navigation_and_skips_the_walker(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        programme = False
        trace, site, events = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            programme=programme,
            flag=True,
            seconds_per_read=10.0,
        )
        sitemap_documents = [u for u in site.requested if u.endswith(".xml")]
        assert len(sitemap_documents) == SLOW_HOST_SITEMAP_DOCUMENTS
        assert [name for name, _ in events] == ["search"], "walker skipped, search once"
        navigation_reads = [u for u in site.requested if not u.endswith((".xml", ".txt"))]
        assert navigation_reads, "navigation still runs when search found nothing"
        # Search ran when exactly the reads before the first navigation read were done.
        assert events[0][1] == site.requested.index(navigation_reads[0])
        assert trace.stage_order == [
            "seeds",
            "sitemaps",
            "search",
            "navigation",
            "confirm",
            "walker_skipped",
        ]
        assert trace.as_dict()["host_cost"] == {
            "crawl_delay": None,
            "median_read_seconds": 10.0,
            "slow": True,
        }

    @pytest.mark.asyncio
    async def test_a_crawl_delay_moves_search_before_confirm(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        programme = True
        trace, site, events = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            programme=programme,
            flag=True,
            seconds_per_read=0.1,
            crawl_delay=10.0,
        )
        assert [name for name, _ in events] == ["search"]
        assert PROGRAMME not in site.requested[: events[0][1]], "searched before confirm read"
        assert PROGRAMME in site.requested
        assert trace.stage_order == ["seeds", "sitemaps", "search", "confirm", "walker_skipped"]

    @pytest.mark.asyncio
    async def test_fast_host_with_a_programme_keeps_todays_order(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        programme = True
        trace, site, events = await _run(
            tmp_path, cs_bachelor, monkeypatch, programme=programme, flag=True, seconds_per_read=1.0
        )
        assert [name for name, _ in events] == ["walker", "search"]
        assert len([u for u in site.requested if u.endswith(".xml")]) == 6
        assert trace.stage_order == ["seeds", "sitemaps", "confirm", "walker", "search"]
        assert trace.as_dict()["host_cost"]["slow"] is False

    @pytest.mark.asyncio
    async def test_fast_host_without_a_programme_searches_first(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        programme = False
        trace, _, events = await _run(
            tmp_path, cs_bachelor, monkeypatch, programme=programme, flag=True, seconds_per_read=1.0
        )
        assert [name for name, _ in events] == ["search", "walker"]
        assert trace.stage_order == [
            "seeds",
            "sitemaps",
            "search",
            "navigation",
            "confirm",
            "walker",
        ]

    @pytest.mark.asyncio
    async def test_off_slow_host_keeps_todays_order_and_trace(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        programme = False
        trace, site, events = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            programme=programme,
            flag=False,
            seconds_per_read=10.0,
        )
        assert [name for name, _ in events] == ["walker", "search"]
        assert len([u for u in site.requested if u.endswith(".xml")]) == 6
        assert trace.stage_order == []
        assert "stage_order" not in trace.as_dict()
        assert "host_cost" not in trace.as_dict()
