"""Synthetic malformed-href regressions prepared for root's RED baseline.

These cases preserve a valid lead on the same page and retain site/outcome
boundaries. They read no historical payload, call no vendor and score nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.discovery.live_discovery import _harvest_links
from app.adapters.fetching import Fetcher, FetchResult, same_source_site
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.navigation import links_from
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel, FetchOutcome
from tests.test_search_audit_regressions import (
    _deny_outbound_network as _deny_outbound_network,
)

BASE = "https://cs.example.edu/"
DOMAIN = "cs.example.edu"
GOOD_NAVIGATION = "https://cs.example.edu/content?menu=188"
SEARCH_PROGRAMME = "https://cs.example.edu/programmes/bachelor/computer-science"
NOW = datetime(2026, 10, 9, tzinfo=UTC)


def test_navigation_bad_ipv6_href_preserves_good_same_site_link():
    html = (
        '<a href="https://[">Broken Computer Science programme</a>'
        '<a href="https://attacker.example.net/content?menu=188">Computer Science</a>'
        '<a href="javascript:void(0)">Computer Science</a>'
        '<a href="/content?menu=188#entry">Computer Science bachelor</a>'
    )

    links = links_from(html, BASE)

    assert [(link.url, link.text, link.parent_url) for link in links] == [
        (GOOD_NAVIGATION, "Computer Science bachelor", BASE)
    ]


def test_live_harvester_bad_nfkc_href_preserves_canonical_good_link():
    html = (
        '<a href="https://cs.example.edu／evil/programmes">Malformed authority</a>'
        '<a href="https://attacker.example.net/content?menu=188">Off-site programme</a>'
        '<a href="mailto:admissions@example.edu">Contact</a>'
        '<a href="/content?menu=188&amp;utm_source=test#entry">Computer Science bachelor</a>'
        '<a href="/content?menu=188">Duplicate programme</a>'
    )

    links = _harvest_links(html, BASE, DOMAIN)

    assert links == [(GOOD_NAVIGATION, "Computer Science bachelor")]


@pytest.mark.asyncio
async def test_retrieval_hop_survives_bad_href_and_does_not_use_refused_body(monkeypatch, tmp_path):
    intent = DiscoveryIntent(
        institution="Synthetic University",
        domain=DOMAIN,
        degree=DegreeLevel.BACHELOR,
        field="Computer Science",
    )
    provider = FakeSearchProvider(
        {
            query.text: [(SEARCH_PROGRAMME, "Computer Science bachelor", "")]
            for query in queries_for(intent, budget=1)
        },
        now=NOW,
    )
    html = (
        '<a href="https://[">Broken Computer Science programme</a>'
        '<a href="/content?menu=188">Computer Science bachelor</a>'
        '<a href="https://attacker.example.net/">Computer Science bachelor</a>'
    )
    requests: list[str] = []
    refuse = False

    async def get(url: str, **kwargs) -> FetchResult:
        requests.append(url)
        assert url == BASE, "The hop must read only its one authorized site entry point"
        return FetchResult(
            url=url,
            outcome=FetchOutcome.ROBOTS_DISALLOWED if refuse else FetchOutcome.OK,
            text=html,
            content=html.encode(),
            final_url=url,
        )

    async with Fetcher(tmp_path / "html-link-cache", offline=True) as fetcher:
        monkeypatch.setattr(fetcher, "get", get)

        async def read(url: str) -> str:
            result = await fetcher.get(url)
            return (
                result.text if result.ok and same_source_site(url, result.final_url or url) else ""
            )

        report = await discover_candidates(
            provider, intent, fetch=read, query_budget=1, hop_entry_points=1, top_k=1
        )
        assert [candidate.url for candidate in report.candidates] == [
            SEARCH_PROGRAMME,
            GOOD_NAVIGATION,
        ]
        assert report.hop_entry_points == (BASE,)
        assert report.candidates[1].provider == "navigation"
        assert "found_by_navigation_hop" in report.candidates[1].signals

        # A refused FetchResult carrying the same body must not contribute
        # navigation leads. This tests the reader/outcome contract; it does
        # not claim to exercise the real robots HTTP transport.
        refuse = True
        blocked = await discover_candidates(
            provider, intent, fetch=read, query_budget=1, hop_entry_points=1, top_k=1
        )

    assert [candidate.url for candidate in blocked.candidates] == [SEARCH_PROGRAMME]
    assert blocked.hop_entry_points == ()
    assert requests == [BASE, BASE]
    assert len(provider.calls) == 2
