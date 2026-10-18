"""Sitemaps in the https namespace and relative ``loc`` values are read.

Shapes from the dev3 discovery analysis of 2026-10-18: UNSW's
``study/undergraduate.sitemap.xml`` declares
``xmlns="https://www.sitemaps.org/schemas/sitemap/0.9"`` (0 of 210 URLs were
read), and UiO's ``sitemapindex.xml`` lists its children as
``<loc>/sitemap-www.uio.no-0.xml</loc>`` (all rejected as off-domain).
Offline: every document comes from a stub.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery.live_discovery import DiscoveryTrace, SitemapReader, parse_sitemap
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

HTTPS_NS = "https://www.sitemaps.org/schemas/sitemap/0.9"
HTTP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _urlset(namespace: str | None, *locations: str) -> str:
    xmlns = f' xmlns="{namespace}"' if namespace else ""
    entries = "".join(
        f"<url><loc>{loc}</loc><lastmod>2026-10-14</lastmod></url>" for loc in locations
    )
    return f'<?xml version="1.0"?><urlset{xmlns}>{entries}</urlset>'


def _index(namespace: str | None, *locations: str) -> str:
    xmlns = f' xmlns="{namespace}"' if namespace else ""
    entries = "".join(f"<sitemap><loc>{loc}</loc></sitemap>" for loc in locations)
    return f'<?xml version="1.0"?><sitemapindex{xmlns}>{entries}</sitemapindex>'


async def _collect(tmp_path, site: StubSite, homepage: str, domain: str):
    trace = DiscoveryTrace(institution="test", domain=domain)
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        pages = await SitemapReader(fetcher).collect(homepage, domain, trace)
    return pages, trace


class TestNamespaces:
    def test_an_https_namespace_urlset_yields_pages(self):
        text = (
            f'<?xml version="1.0"?><urlset xmlns="{HTTPS_NS}" '
            'xmlns:xhtml="https://www.w3.org/1999/xhtml">'
            "<url><loc>https://www.unsw.edu.au/study/undergraduate</loc>"
            "<lastmod>2026-09-05</lastmod></url>"
            "<url><loc>https://www.unsw.edu.au/study/undergraduate/"
            "bachelor-of-computer-science</loc></url></urlset>"
        )
        children, pages = parse_sitemap(text)
        assert children == []
        assert pages == [
            "https://www.unsw.edu.au/study/undergraduate",
            "https://www.unsw.edu.au/study/undergraduate/bachelor-of-computer-science",
        ]

    def test_an_https_namespace_index_yields_children(self):
        children, pages = parse_sitemap(
            _index(HTTPS_NS, "https://u.edu/s1.xml", "https://u.edu/s2.xml")
        )
        assert children == ["https://u.edu/s1.xml", "https://u.edu/s2.xml"]
        assert pages == []

    def test_no_namespace_urlset_and_index_parse(self):
        assert parse_sitemap(_urlset(None, "https://u.edu/a")) == ([], ["https://u.edu/a"])
        assert parse_sitemap(_index(None, "https://u.edu/s.xml")) == (["https://u.edu/s.xml"], [])

    def test_the_http_namespace_is_unchanged(self):
        assert parse_sitemap(sitemap_xml("https://u.edu/a", "https://u.edu/b")) == (
            [],
            ["https://u.edu/a", "https://u.edu/b"],
        )
        assert parse_sitemap(sitemap_index_xml("https://u.edu/s1.xml")) == (
            ["https://u.edu/s1.xml"],
            [],
        )

    def test_an_image_extension_loc_is_not_a_page(self):
        text = (
            f'<urlset xmlns="{HTTPS_NS}" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
            "<url><loc>https://u.edu/a</loc>"
            "<image:image><image:loc>https://u.edu/a.jpg</image:loc></image:image>"
            "</url></urlset>"
        )
        assert parse_sitemap(text) == ([], ["https://u.edu/a"])


class TestRelativeLocations:
    @pytest.mark.asyncio
    async def test_relative_children_and_pages_are_resolved(self, tmp_path):
        site = StubSite(
            {
                "https://www.uio.no/robots.txt": "Sitemap: https://www.uio.no/sitemapindex.xml\n",
                "https://www.uio.no/sitemapindex.xml": _index(HTTP_NS, "/sitemap-www.uio.no-0.xml"),
                "https://www.uio.no/sitemap-www.uio.no-0.xml": _urlset(
                    HTTPS_NS,
                    "/studier/program/informatikk-programmering/",
                    "https://www.uio.no/om/",
                ),
            }
        )
        pages, trace = await _collect(tmp_path, site, "https://www.uio.no/", "uio.no")

        assert "https://www.uio.no/sitemap-www.uio.no-0.xml" in trace.sitemaps_read
        assert pages == [
            "https://www.uio.no/studier/program/informatikk-programmering",
            "https://www.uio.no/om",
        ]
        assert not any("off the institution" in reason for _, reason in trace.rejected)

    @pytest.mark.asyncio
    async def test_a_relative_child_resolving_off_domain_is_still_rejected(self, tmp_path):
        site = StubSite(
            {
                "https://u.edu/robots.txt": "Sitemap: https://u.edu/sitemap.xml\n",
                "https://u.edu/sitemap.xml": _index(HTTPS_NS, "//evil.example/sitemap.xml"),
            }
        )
        pages, trace = await _collect(tmp_path, site, "https://u.edu/", "u.edu")

        assert pages == []
        assert "https://evil.example/sitemap.xml" not in site.requested
        assert (
            "https://evil.example/sitemap.xml",
            "sitemap is off the institution's domain",
        ) in trace.rejected

    @pytest.mark.asyncio
    async def test_a_relative_page_loc_resolving_off_domain_is_rejected(self, tmp_path):
        site = StubSite(
            {
                "https://u.edu/robots.txt": "Sitemap: https://u.edu/pages.xml\n",
                "https://u.edu/pages.xml": _urlset(HTTPS_NS, "//evil.example/page", "/ok"),
            }
        )
        pages, trace = await _collect(tmp_path, site, "https://u.edu/", "u.edu")

        assert pages == ["https://u.edu/ok"]
        assert ("https://evil.example/page", "off the institution's domain") in trace.rejected
