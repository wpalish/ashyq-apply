"""Plan rule SM-1: programme sitemaps before news, and no probing after a hit.

Shapes from the discovery analysis of 2026-10-17 (§1.3–§1.5): NU's index lists
post-sitemap1..24 before page-sitemap and sprogram-sitemap; Charles and METU
probed three conventional locations after /sitemap.xml had already answered.
Offline: every document comes from a stub.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    MAX_SITEMAP_DOCUMENTS,
    SITEMAP_FALLBACK_PATHS,
    DiscoveryTrace,
    SitemapReader,
    _child_priority,
)
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

PROGRAMME = "https://nu.edu.kz/programs/bsc-computer-science"


def _nu_site() -> StubSite:
    posts = [f"https://nu.edu.kz/post-sitemap{i}.xml" for i in range(1, 25)]
    pages: dict[str, bytes | str] = {
        "https://nu.edu.kz/robots.txt": "Sitemap: https://nu.edu.kz/sitemap_index.xml\n",
        "https://nu.edu.kz/sitemap_index.xml": sitemap_index_xml(
            *posts,
            "https://nu.edu.kz/page-sitemap1.xml",
            "https://nu.edu.kz/sprogram-sitemap1.xml",
        ),
        "https://nu.edu.kz/page-sitemap1.xml": sitemap_xml("https://nu.edu.kz/about"),
        "https://nu.edu.kz/sprogram-sitemap1.xml": sitemap_xml(PROGRAMME),
    }
    for i, post in enumerate(posts):
        pages[post] = sitemap_xml(f"https://nu.edu.kz/news/item-{i}")
    return StubSite(pages)


async def _collect(tmp_path, site: StubSite, homepage: str, domain: str):
    trace = DiscoveryTrace(institution="test", domain=domain)
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        pages = await SitemapReader(fetcher).collect(homepage, domain, trace)
    return pages, trace


class TestChildPriority:
    @pytest.mark.parametrize(
        ("url", "group"),
        [
            ("https://u.edu/sprogram-sitemap1.xml", 0),
            ("https://u.edu/page-sitemap2.xml", 0),
            ("https://u.edu/sitemap.xml?sitemap=studycourse&cHash=1", 0),
            ("https://u.edu/post-sitemap7.xml", 2),
            ("https://u.edu/sitemap.xml?sitemap=news&cHash=2", 2),
            ("https://u.edu/event-sitemap.xml", 2),
            ("https://u.edu/postgraduate-sitemap.xml", 1),
            ("https://u.edu/sitemap-0.xml", 1),
        ],
    )
    def test_names_sort_into_three_groups(self, url, group):
        assert _child_priority(url) == group


class TestSitemapChildPriority:
    @pytest.mark.asyncio
    async def test_on_the_programme_sitemap_is_read_within_the_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", True)
        site = _nu_site()
        pages, trace = await _collect(tmp_path, site, "https://nu.edu.kz/", "nu.edu.kz")

        documents = [u for u in site.requested if u.endswith(".xml")]
        assert len(documents) <= MAX_SITEMAP_DOCUMENTS
        assert "https://nu.edu.kz/sprogram-sitemap1.xml" in documents
        assert documents.index("https://nu.edu.kz/sprogram-sitemap1.xml") <= 2
        assert PROGRAMME in pages
        assert trace.sitemaps_read[1:3] == [
            "https://nu.edu.kz/page-sitemap1.xml",
            "https://nu.edu.kz/sprogram-sitemap1.xml",
        ]

    @pytest.mark.asyncio
    async def test_off_file_order_spends_the_cap_on_posts(self, tmp_path, monkeypatch):
        # The baseline SM-1 was measured against: SM-2 (on by default) also off.
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", False)
        monkeypatch.setattr(live_discovery, "SITEMAP_TRIM", False)
        site = _nu_site()
        pages, _ = await _collect(tmp_path, site, "https://nu.edu.kz/", "nu.edu.kz")
        assert "https://nu.edu.kz/sprogram-sitemap1.xml" not in site.requested
        assert PROGRAMME not in pages

    @pytest.mark.asyncio
    async def test_off_with_the_default_trim_the_posts_are_not_read(self, tmp_path, monkeypatch):
        """SM-2 alone (the shipped default) also reaches NU's programme sitemap."""
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", False)
        monkeypatch.setattr(live_discovery, "SITEMAP_TRIM", True)
        site = _nu_site()
        pages, trace = await _collect(tmp_path, site, "https://nu.edu.kz/", "nu.edu.kz")
        assert not any("post-sitemap" in u for u in site.requested)
        assert "https://nu.edu.kz/sprogram-sitemap1.xml" in site.requested
        assert PROGRAMME in pages
        assert sum(reason.startswith("SM-2") for _, reason in trace.rejected) == 24

    @pytest.mark.asyncio
    async def test_on_news_is_skipped_when_programme_sitemaps_fill_the_cap(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", True)
        programmes = [f"https://u.edu/program-sitemap{i}.xml" for i in range(MAX_SITEMAP_DOCUMENTS)]
        news = "https://u.edu/news-sitemap.xml"
        site = StubSite(
            {
                "https://u.edu/robots.txt": "Sitemap: https://u.edu/index.xml\n",
                "https://u.edu/index.xml": sitemap_index_xml(news, *programmes),
                **{p: sitemap_xml("https://u.edu/programs/x") for p in programmes},
            }
        )
        _, trace = await _collect(tmp_path, site, "https://u.edu/", "u.edu")
        assert news not in site.requested
        assert any(url == news and "news/post" in reason for url, reason in trace.rejected)

    @pytest.mark.asyncio
    async def test_on_a_conventional_hit_stops_the_probing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", True)
        site = StubSite(
            {
                "https://u.edu/robots.txt": "",
                "https://u.edu/sitemap.xml": sitemap_xml("https://u.edu/programs/cs"),
            }
        )
        pages, _ = await _collect(tmp_path, site, "https://u.edu/", "u.edu")
        assert pages == ["https://u.edu/programs/cs"]
        for path in SITEMAP_FALLBACK_PATHS[1:]:
            assert f"https://u.edu{path}" not in site.requested

    @pytest.mark.asyncio
    async def test_on_an_empty_answer_keeps_probing(self, tmp_path, monkeypatch):
        """A soft-404 HTML page at /sitemap.xml is not a sitemap."""
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", True)
        site = StubSite(
            {
                "https://u.edu/robots.txt": "",
                "https://u.edu/sitemap.xml": "<html><body>Not found</body></html>",
                "https://u.edu/sitemap_index.xml": sitemap_xml("https://u.edu/programs/cs"),
            }
        )
        pages, _ = await _collect(tmp_path, site, "https://u.edu/", "u.edu")
        assert pages == ["https://u.edu/programs/cs"]
        assert "https://u.edu/sitemap-index.xml" not in site.requested

    @pytest.mark.asyncio
    async def test_off_every_conventional_location_is_probed(self, tmp_path, monkeypatch):
        # SM-2 shares SM-1's stop-after-a-hit rule, so the baseline pins both off.
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", False)
        monkeypatch.setattr(live_discovery, "SITEMAP_TRIM", False)
        site = StubSite(
            {
                "https://u.edu/robots.txt": "",
                "https://u.edu/sitemap.xml": sitemap_xml("https://u.edu/programs/cs"),
            }
        )
        await _collect(tmp_path, site, "https://u.edu/", "u.edu")
        for path in SITEMAP_FALLBACK_PATHS:
            assert f"https://u.edu{path}" in site.requested
