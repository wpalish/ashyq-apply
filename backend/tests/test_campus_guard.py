"""Plan rule CG-1: a branch campus abroad is not the programme asked about.

Shape from the wrong-claims analysis of 2026-10-18 (R-D2): UNSW's identity
recovery confirmed "Bachelor of Science in Computer Science (Bengaluru)"
(``…/bachelor-of-science-in-computer-science-bengaluru``) for a request that
names no campus. Every page here is written for the test. Offline.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import CatalogWalk, CatalogWalker, WalkerLink
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    foreign_campus_named,
    profile_rejects,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, program_html

BACKEND = Path(__file__).resolve().parents[1]

SYDNEY = "https://www.unsw.edu.au/study/undergraduate/bachelor-of-computer-science"
BENGALURU = (
    "https://www.unsw.edu.au/study/undergraduate/bachelor-of-science-in-computer-science-bengaluru"
)


@pytest.fixture
def guard(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CAMPUS_GUARD", True)


@pytest.fixture
def unguarded(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CAMPUS_GUARD", False)


def test_flag_is_on_by_default() -> None:
    assert live_discovery.CAMPUS_GUARD is True


@pytest.mark.parametrize(
    ("title", "url", "country", "place"),
    [
        ("Bachelor of Science in Computer Science (Bengaluru)", "", "Australia", "bengaluru"),
        ("Bachelor of Science in Computer Science", BENGALURU, "Australia", "bengaluru"),
        ("BSc Computer Science - Malaysia campus", "", "United Kingdom", "malaysia"),
        ("Computer Science BSc – Dubai", "", "United Kingdom", "dubai"),
        ("Computer Science (campus Abu Dhabi)", "", "United States", "abu dhabi"),
        ("BSc Computer Science", "https://u.ac.uk/study/china-campus/cs", "UK", "china"),
    ],
)
def test_a_branch_campus_abroad_is_named(title: str, url: str, country: str, place: str) -> None:
    assert foreign_campus_named(title, url, country) == place


@pytest.mark.parametrize(
    ("title", "url", "country"),
    [
        # A domestic second campus: both UBC campuses are in Canada.
        ("Computer Science (Okanagan)", "https://okanagan.calendar.ubc.ca/cs", "Canada"),
        (
            "Computer Science BSc",
            "https://you.ubc.ca/programs/computer-science-vancouver/",
            "Canada",
        ),
        # The place is the institution's own country.
        ("Bachelor of Computer Science (Malaysia)", "", "Malaysia"),
        ("Bachelor of Computer Science", "https://www.ntu.edu.sg/cs-singapore", "Singapore"),
        # Not a campus qualifier.
        ("Bachelor of Computer Science (Hons)", SYDNEY + "-hons", "Australia"),
        ("Computer Science (International)", "", "Netherlands"),
        ("Computer Science with Chinese studies", "https://u.ac.uk/cs-chinese", "UK"),
        ("Computer Science", "https://u.edu/en/indiana/cs", "United States"),
        # Unknown country: nothing is refused.
        ("Computer Science (Bengaluru)", BENGALURU, ""),
    ],
)
def test_a_domestic_or_unqualified_page_is_not_named(title: str, url: str, country: str) -> None:
    assert foreign_campus_named(title, url, country) is None


def test_profile_rejects_only_with_the_flag(monkeypatch) -> None:
    page = classify_page(
        url=BENGALURU, html=program_html("Bachelor of Science in Computer Science (Bengaluru)")
    )
    fields = ["computer science"]
    monkeypatch.setattr(live_discovery, "CAMPUS_GUARD", False)
    assert profile_rejects(page, "bachelor", fields, url=BENGALURU, country="Australia") is None
    monkeypatch.setattr(live_discovery, "CAMPUS_GUARD", True)
    reason = profile_rejects(page, "bachelor", fields, url=BENGALURU, country="Australia")
    assert reason == "page names a campus abroad (bengaluru), not the institution's own"
    # A call site that passes no country refuses nothing.
    assert profile_rejects(page, "bachelor", fields, url=BENGALURU) is None


def test_the_trace_does_not_serialise_the_country() -> None:
    trace = DiscoveryTrace(institution="U", domain="uni.edu", country="Australia")
    assert "country" not in trace.as_dict()


async def recover(tmp_path, profile, pages_by_url):
    profile.context.intended_fields = ["computer science"]
    site = StubSite(dict(pages_by_url))
    pages: list[str] = []
    trace = DiscoveryTrace(institution="UNSW", domain="unsw.edu.au", country="Australia")
    candidates = [RankedCandidate(u, "Computer Science", 1, "fake") for u in pages_by_url]
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(candidates, pages, trace, profile)
    return pages, trace


BENGALURU_HTML = program_html("Bachelor of Science in Computer Science (Bengaluru)")
SYDNEY_HTML = program_html("Bachelor of Science (Computer Science)")


@pytest.mark.asyncio
async def test_off_recovery_confirms_the_branch_campus(tmp_path, profile, unguarded) -> None:
    pages, _ = await recover(tmp_path, profile, {BENGALURU: BENGALURU_HTML})
    assert pages == [BENGALURU]


@pytest.mark.asyncio
async def test_on_recovery_refuses_the_branch_campus(tmp_path, profile, guard) -> None:
    pages, trace = await recover(tmp_path, profile, {BENGALURU: BENGALURU_HTML})
    assert pages == []
    assert (BENGALURU, "page names a campus abroad (bengaluru), not the institution's own") in (
        trace.rejected
    )


@pytest.mark.asyncio
async def test_on_recovery_confirms_the_home_campus_beside_it(tmp_path, profile, guard) -> None:
    pages, _ = await recover(tmp_path, profile, {BENGALURU: BENGALURU_HTML, SYDNEY: SYDNEY_HTML})
    assert pages == [SYDNEY]


@pytest.mark.asyncio
async def test_on_a_domestic_second_campus_is_still_confirmed(tmp_path, profile, guard) -> None:
    url = "https://okanagan.calendar.ubc.ca/faculties-schools-and-colleges/computer-science-bsc"
    profile.context.intended_fields = ["computer science"]
    site = StubSite({url: program_html("Computer Science (Okanagan) BSc")})
    pages: list[str] = []
    trace = DiscoveryTrace(institution="UBC", domain="ubc.ca", country="Canada")
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(
            [RankedCandidate(url, "Computer Science", 1, "fake")], pages, trace, profile
        )
    assert pages == [url]


@pytest.mark.asyncio
async def test_on_the_walker_refuses_the_branch_campus(tmp_path, guard) -> None:
    site = StubSite({BENGALURU: BENGALURU_HTML, SYDNEY: SYDNEY_HTML})
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        walker = CatalogWalker(
            fetcher=fetcher,
            domain="unsw.edu.au",
            degree="bachelor",
            fields=["computer science"],
            country="Australia",
        )
        walk = CatalogWalk(catalogue_url="https://www.unsw.edu.au/study")
        for url in (BENGALURU, SYDNEY):
            await walker._read_lead(
                WalkerLink(url=url, label="Computer Science", score=1, source="html"), walk
            )
    assert walk.confirmed == [SYDNEY]


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--campus-guard" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "cg1_module.CAMPUS_GUARD = True" in source
    assert '*(["--campus-guard"] if args.campus_guard else [])' in source
