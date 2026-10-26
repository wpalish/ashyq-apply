"""SM-2: no read on a guaranteed-404 probe or a news/events/media sitemap.

Shape from the read budget analysis of 2026-10-18 (§2, §3): Chula's robots.txt
names no sitemap; /sitemap.xml answers with an index, yet /sitemap_index.xml,
/sitemap-index.xml and /sitemap/sitemap.xml were still probed (two 404s), and
the index's clipping x2, event-calendar, gallery and highlight children were
read: 13 sitemap reads, seven of them waste. Offline: every document is a stub.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import DiscoveryTrace, SitemapReader, _trimmed_sitemap
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

ORIGIN = "https://www.chula.example.ac.th"
PROGRAMME = f"{ORIGIN}/en/academics/programs/bsc-computer-science"
WANTED = ("page", "cuinside", "departments")
WASTE = ("clipping", "clipping2", "event-calendar", "gallery", "highlight")


def _chula_site() -> StubSite:
    children = [f"{ORIGIN}/{name}-sitemap.xml" for name in (*WANTED[:2], *WASTE[:2])]
    children += [f"{ORIGIN}/{name}-sitemap.xml" for name in (WANTED[2], *WASTE[2:])]
    pages: dict[str, bytes | str] = {
        f"{ORIGIN}/robots.txt": "User-agent: *\nDisallow: /wp-admin/\n",
        f"{ORIGIN}/sitemap.xml": sitemap_index_xml(*children),
        f"{ORIGIN}/sitemap_index.xml": sitemap_index_xml(*children),
        f"{ORIGIN}/page-sitemap.xml": sitemap_xml(PROGRAMME),
    }
    for child in children:
        pages.setdefault(child, sitemap_xml(f"{child.removesuffix('-sitemap.xml')}/item-1"))
    return StubSite(pages)


async def _collect(tmp_path, site: StubSite) -> tuple[list[str], DiscoveryTrace]:
    trace = DiscoveryTrace(institution="test", domain="www.chula.example.ac.th")
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        pages = await SitemapReader(fetcher).collect(f"{ORIGIN}/", "chula.example.ac.th", trace)
    return pages, trace


def _documents(site: StubSite) -> list[str]:
    return [url for url in site.requested if url.endswith(".xml")]


class TestTrimmedNames:
    @pytest.mark.parametrize(
        "url",
        [
            f"{ORIGIN}/clipping-sitemap2.xml",
            f"{ORIGIN}/event-calendar-sitemap.xml",
            f"{ORIGIN}/gallery-sitemap.xml",
            f"{ORIGIN}/highlight-sitemap.xml",
            f"{ORIGIN}/post-sitemap7.xml",
            f"{ORIGIN}/sitemap.xml?sitemap=news&cHash=2",
            f"{ORIGIN}/en/newsroom/sitemap.xml",
            f"{ORIGIN}/media-sitemap.xml",
            f"{ORIGIN}/blog-sitemap.xml",
            f"{ORIGIN}/press-releases-sitemap.xml",
        ],
    )
    def test_news_events_and_media_documents_are_trimmed(self, url: str) -> None:
        assert _trimmed_sitemap(url)

    @pytest.mark.parametrize(
        "url",
        [
            f"{ORIGIN}/sitemap.xml",
            f"{ORIGIN}/page-sitemap.xml",
            f"{ORIGIN}/departments-sitemap.xml",
            f"{ORIGIN}/postgraduate-sitemap.xml",
            f"{ORIGIN}/cuinside-sitemap.xml",
            # A programme word wins over a news word.
            f"{ORIGIN}/programme-events-sitemap.xml",
            f"{ORIGIN}/sitemap.xml?sitemap=studycourse",
        ],
    )
    def test_programme_and_neutral_documents_are_kept(self, url: str) -> None:
        assert not _trimmed_sitemap(url)

    def test_the_rule_is_on_by_default(self) -> None:
        assert live_discovery.SITEMAP_TRIM is True


class TestSitemapTrim:
    async def test_on_no_probe_after_a_hit_and_no_waste_child_is_read(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(live_discovery, "SITEMAP_TRIM", True)
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", False)
        site = _chula_site()
        pages, trace = await _collect(tmp_path, site)

        documents = _documents(site)
        assert documents[0] == f"{ORIGIN}/sitemap.xml"
        assert f"{ORIGIN}/sitemap_index.xml" not in documents
        assert f"{ORIGIN}/sitemap-index.xml" not in documents
        assert f"{ORIGIN}/sitemap/sitemap.xml" not in documents
        assert not any(name in url for url in documents for name in WASTE)
        assert sorted(documents[1:]) == sorted(f"{ORIGIN}/{n}-sitemap.xml" for n in WANTED)
        assert PROGRAMME in pages
        reasons = dict(trace.rejected)
        assert reasons[f"{ORIGIN}/gallery-sitemap.xml"].startswith("SM-2")
        # robots.txt, the index and the three wanted children: 5 reads, was 13.
        assert len(site.requested) == 5

    async def test_off_the_reads_are_unchanged(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(live_discovery, "SITEMAP_TRIM", False)
        monkeypatch.setattr(live_discovery, "SITEMAP_CHILD_PRIORITY", False)
        site = _chula_site()
        await _collect(tmp_path, site)
        documents = _documents(site)
        # All four conventional locations, then the index's eight children.
        assert documents[:4] == [f"{ORIGIN}{p}" for p in live_discovery.SITEMAP_FALLBACK_PATHS]
        assert all(any(name in url for url in documents) for name in WASTE)
        assert len(site.requested) == 13

    async def test_on_a_declared_news_sitemap_is_not_read(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(live_discovery, "SITEMAP_TRIM", True)
        site = StubSite(
            {
                f"{ORIGIN}/robots.txt": (
                    f"Sitemap: {ORIGIN}/news-sitemap.xml\nSitemap: {ORIGIN}/page-sitemap.xml\n"
                ),
                f"{ORIGIN}/news-sitemap.xml": sitemap_xml(f"{ORIGIN}/news/1"),
                f"{ORIGIN}/page-sitemap.xml": sitemap_xml(PROGRAMME),
            }
        )
        pages, _trace = await _collect(tmp_path, site)
        assert _documents(site) == [f"{ORIGIN}/page-sitemap.xml"]
        assert PROGRAMME in pages


BACKEND = Path(__file__).resolve().parents[1]


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--sitemap-trim" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "sm2_module.SITEMAP_TRIM = True" in source
    assert '*(["--sitemap-trim"] if args.sitemap_trim else [])' in source
