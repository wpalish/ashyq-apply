"""Plan rule DI-1: an admissions domain the institution's own homepage names.

Shape from the evidence analysis of 2026-10-17 (§0 #5, §1 Tsinghua, §4 rank
5): Tsinghua's international undergraduate admissions run on
``international.join-tsinghua.edu.cn``, a registrable domain of its own, which
``www.tsinghua.edu.cn`` links from its admissions navigation. Offline: every
document comes from a stub; no page body is a copy of the real site.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.base import Candidate
from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import extract_links
from app.adapters.discovery.live_discovery import (
    LiveDiscoveryAdapter,
    _harvest_links,
    admissions_host_from_homepage,
)
from app.adapters.extraction import ClaimBuilder, is_official_domain, verification_domains
from app.adapters.fetching import Fetcher
from app.domain.enums import ClaimType, SourceSpecificity
from tests.test_live_discovery import StubSite

HOMEPAGE = "https://www.tsinghua.edu.cn/en/"
JOIN = "https://international.join-tsinghua.edu.cn/en/admissions/international-students"
JOIN_PAGE = "https://international.join-tsinghua.edu.cn/en/admissions/schedule"


def homepage(*nav_links: tuple[str, str], body_links: tuple[tuple[str, str], ...] = ()) -> str:
    nav = "".join(f'<li><a href="{href}">{text}</a></li>' for href, text in nav_links)
    body = "".join(f'<p><a href="{href}">{text}</a></p>' for href, text in body_links)
    return (
        "<html><head><title>Tsinghua University</title></head><body>"
        f'<header><nav class="main-nav"><ul>{nav}</ul></nav></header>'
        f"<main><h1>Tsinghua University</h1>{body}</main></body></html>"
    )


TSINGHUA_NAV = (
    ("https://www.tsinghua.edu.cn/en/About.htm", "About"),
    (JOIN, "Undergraduate Admissions"),
)


class TestHomepageReading:
    def test_one_admissions_domain_in_the_navigation_is_named(self):
        record = admissions_host_from_homepage(
            homepage(*TSINGHUA_NAV), HOMEPAGE, "www.tsinghua.edu.cn"
        )
        assert record == {
            "domain": "join-tsinghua.edu.cn",
            "link": JOIN,
            "text": "Undergraduate Admissions",
        }

    def test_local_admissions_words_count(self):
        html = homepage(("https://zs.join-tsinghua.edu.cn/", "本科招生"))
        record = admissions_host_from_homepage(html, HOMEPAGE, "www.tsinghua.edu.cn")
        assert record["domain"] == "join-tsinghua.edu.cn"

    @pytest.mark.parametrize(
        ("href", "text"),
        [
            ("https://www.uni-assist.de/en/", "Apply via uni-assist"),
            ("https://www.facebook.com/tsinghua", "Admissions on Facebook"),
            ("https://www.google.com.hk/search?q=admissions", "Admissions"),
            ("https://bit.ly/3apply", "Apply now"),
            ("https://www.commonapp.org/", "Apply"),
        ],
    )
    def test_a_third_party_is_never_added(self, href, text):
        record = admissions_host_from_homepage(
            homepage((href, text)), HOMEPAGE, "www.tsinghua.edu.cn"
        )
        assert record == {}

    def test_two_admissions_domains_are_ambiguous_and_add_none(self):
        html = homepage(*TSINGHUA_NAV, ("https://apply.other-portal.cn/", "International Students"))
        record = admissions_host_from_homepage(html, HOMEPAGE, "www.tsinghua.edu.cn")
        assert "domain" not in record
        assert record["domains"] == ["join-tsinghua.edu.cn", "other-portal.cn"]

    def test_a_link_outside_the_navigation_or_without_admissions_text_is_ignored(self):
        html = homepage(
            ("https://news.partner.cn/", "News"),
            body_links=((JOIN, "Undergraduate Admissions"),),
        )
        assert admissions_host_from_homepage(html, HOMEPAGE, "www.tsinghua.edu.cn") == {}

    def test_a_government_portal_only_when_the_text_names_the_university(self):
        portal = "https://study.moe.gov.cn/apply"
        assert (
            admissions_host_from_homepage(
                homepage((portal, "Apply")), HOMEPAGE, "www.tsinghua.edu.cn"
            )
            == {}
        )
        named = homepage((portal, "Tsinghua University admissions"))
        record = admissions_host_from_homepage(named, HOMEPAGE, "www.tsinghua.edu.cn")
        assert record["domain"] == "moe.gov.cn"

    def test_the_extra_domain_widens_link_harvesting(self):
        html = homepage(*TSINGHUA_NAV)
        assert JOIN not in [u for u, _ in _harvest_links(html, HOMEPAGE, "www.tsinghua.edu.cn")]
        harvested = _harvest_links(html, HOMEPAGE, "www.tsinghua.edu.cn", ["join-tsinghua.edu.cn"])
        assert JOIN in [u for u, _ in harvested]
        drops: list[tuple[str, str]] = []
        extract_links(html, HOMEPAGE, "www.tsinghua.edu.cn", drops, ["join-tsinghua.edu.cn"])
        assert JOIN not in [u for u, _ in drops]


def _registry(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": "Tsinghua University",
                    "country": "China",
                    "city": "Beijing",
                    "homepage": HOMEPAGE,
                }
            ]
        )
    )
    return path


async def _discover(tmp_path, html: str, profile):
    site = StubSite({HOMEPAGE: html})
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, _registry(tmp_path))
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0]


class TestDiscovery:
    @pytest.mark.asyncio
    async def test_on_the_admissions_domain_is_official_for_the_run(
        self, tmp_path, monkeypatch, profile
    ):
        monkeypatch.setattr(live_discovery, "ADMISSIONS_HOST_FROM_HOMEPAGE", True)
        candidate, trace = await _discover(tmp_path, homepage(*TSINGHUA_NAV), profile)

        assert candidate.extra_domains == ["join-tsinghua.edu.cn"]
        assert candidate.official_domains == ("www.tsinghua.edu.cn", "join-tsinghua.edu.cn")
        # Discovery keeps the page on the added domain (navigation fallback).
        assert candidate.admissions_url == JOIN
        assert trace.as_dict()["admissions_host"] == {
            "domain": "join-tsinghua.edu.cn",
            "link": JOIN,
            "text": "Undergraduate Admissions",
        }

    @pytest.mark.asyncio
    async def test_off_nothing_changes(self, tmp_path, monkeypatch, profile):
        monkeypatch.setattr(live_discovery, "ADMISSIONS_HOST_FROM_HOMEPAGE", False)
        candidate, trace = await _discover(tmp_path, homepage(*TSINGHUA_NAV), profile)

        assert candidate.extra_domains == []
        assert candidate.official_domains == ("www.tsinghua.edu.cn",)
        assert candidate.admissions_url != JOIN
        assert "admissions_host" not in trace.as_dict()

    @pytest.mark.asyncio
    async def test_on_a_third_party_or_two_domains_add_nothing(
        self, tmp_path, monkeypatch, profile
    ):
        monkeypatch.setattr(live_discovery, "ADMISSIONS_HOST_FROM_HOMEPAGE", True)
        third = homepage(("https://www.facebook.com/tsinghua", "Admissions on Facebook"))
        candidate, trace = await _discover(tmp_path, third, profile)
        assert candidate.extra_domains == []
        assert "admissions_host" not in trace.as_dict()

        two = homepage(*TSINGHUA_NAV, ("https://apply.other-portal.cn/", "Apply"))
        candidate, trace = await _discover(tmp_path / "two", two, profile)
        assert candidate.extra_domains == []
        assert candidate.admissions_url != JOIN
        assert trace.as_dict()["admissions_host"]["domains"] == [
            "join-tsinghua.edu.cn",
            "other-portal.cn",
        ]


def _ielts_claim(candidate: Candidate):
    text = "Applicants must hold IELTS (academic) with an overall band score of 6.5."
    builder = ClaimBuilder(
        source_url=JOIN_PAGE,
        specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
        official_domain=is_official_domain(JOIN_PAGE, candidate.official_domains),
        page_text=text,
        page_type="general_admissions",
        allowed_domains=verification_domains(JOIN_PAGE, candidate.domain, candidate.extra_domains),
    )
    claim = builder.add(ClaimType.IELTS_MIN_OVERALL, 6.5, text)
    return claim, builder


def test_a_claim_from_the_added_domain_passes_the_official_domain_check():
    candidate = Candidate(
        name="Tsinghua University",
        country="China",
        city="Beijing",
        domain="www.tsinghua.edu.cn",
        extra_domains=["join-tsinghua.edu.cn"],
    )
    claim, builder = _ielts_claim(candidate)
    assert claim is not None, builder.rejected
    assert claim.official_domain is True


def test_without_the_added_domain_the_same_claim_is_refused():
    candidate = Candidate(
        name="Tsinghua University", country="China", city="Beijing", domain="www.tsinghua.edu.cn"
    )
    assert verification_domains(JOIN_PAGE, candidate.domain, candidate.extra_domains) == (
        "www.tsinghua.edu.cn",
    )
    claim, _builder = _ielts_claim(candidate)
    # Not official: kept, but never as an official-domain claim.
    assert claim is not None
    assert claim.official_domain is False
    # And asserted official against the domain alone, the verifier refuses it.
    text = "Applicants must hold IELTS (academic) with an overall band score of 6.5."
    strict = ClaimBuilder(
        source_url=JOIN_PAGE,
        specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
        official_domain=True,
        page_text=text,
        page_type="general_admissions",
        allowed_domains=verification_domains(JOIN_PAGE, candidate.domain, candidate.extra_domains),
    )
    assert strict.add(ClaimType.IELTS_MIN_OVERALL, 6.5, text) is None
    assert [reason.value for _, _, reason in strict.rejected] == ["domain_not_official"]
