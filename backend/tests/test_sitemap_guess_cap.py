"""Ticket SG-1: sitemap guesses on a crawl-delay host (NEXT_CYCLES_2026-10-22 §3).

When robots.txt names no sitemap, discovery guesses the conventional locations,
one read each. On a host that asks a crawl delay every guess costs that delay.
On (``SITEMAP_GUESS_RULE``): a host whose crawl delay is at least
``SLOW_HOST_SECONDS`` has only ``/sitemap.xml`` guessed, and on any host guessing
stops after two consecutive 404s. Off, the four guesses are read as before.

Every site here is written for the test (``example-uni.edu``); no page, label or
word comes from a development or heldout case. Offline: a fake fetcher counts
the reads.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    SITEMAP_FALLBACK_PATHS,
    SLOW_HOST_SECONDS,
    SLOW_HOST_SITEMAP_DOCUMENTS,
    DiscoveryTrace,
    HostCost,
    SitemapReader,
)
from app.adapters.fetching import Fetcher, FetchResult
from app.domain.enums import FetchOutcome
from evaluation.research import live
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

ORIGIN = "https://www.example-uni.edu"
HOME = f"{ORIGIN}/"
PROGRAMME = f"{ORIGIN}/study/bsc-computer-science"
GUESSES = [f"{ORIGIN}{path}" for path in SITEMAP_FALLBACK_PATHS]
NO_SITEMAP_ROBOTS = "User-agent: *\nDisallow: /private/\n"


class StatusSite(StubSite):
    """A ``StubSite`` that answers chosen URLs with a chosen error status."""

    def __init__(self, pages: dict[str, bytes | str], statuses: dict[str, int]) -> None:
        super().__init__(pages)
        self.statuses = statuses

    def install(self, fetcher: Fetcher) -> Fetcher:
        super().install(fetcher)
        stub_get = fetcher.get

        async def get(url: str, **kwargs: object) -> FetchResult:
            status = self.statuses.get(url)
            if status is None:
                return await stub_get(url, **kwargs)  # type: ignore[arg-type]
            self.requested.append(url)
            return FetchResult(
                url=url,
                outcome=FetchOutcome.HTTP_ERROR,
                status_code=status,
                error=f"HTTP {status}",
                final_url=url,
            )

        fetcher.get = get  # type: ignore[method-assign]
        return fetcher


@pytest.fixture(params=[False, True], ids=["off", "on"])
def sg1(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> bool:
    monkeypatch.setattr(live_discovery, "SITEMAP_GUESS_RULE", request.param)
    return bool(request.param)


async def _collect(
    tmp_path: Path,
    site: StubSite,
    monkeypatch: pytest.MonkeyPatch,
    *,
    crawl_delay: float | None = None,
    cost: HostCost | None = None,
) -> tuple[list[str], DiscoveryTrace]:
    trace = DiscoveryTrace(institution="test", domain="www.example-uni.edu")
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)

        async def asked(url: str) -> float | None:
            return crawl_delay

        monkeypatch.setattr(fetcher.robots, "crawl_delay", asked)
        pages = await SitemapReader(fetcher).collect(HOME, "example-uni.edu", trace, cost=cost)
    return pages, trace


def _documents(site: StubSite) -> list[str]:
    return [url for url in site.requested if not url.endswith("/robots.txt")]


def _sg1_lines(trace: DiscoveryTrace) -> list[str]:
    return [line for line in trace.errors if line.startswith("SG-1")]


# --- the constants ---------------------------------------------------------------------


def test_the_rule_is_off_by_default_and_the_cap_is_todays_four() -> None:
    assert live_discovery.SITEMAP_GUESS_RULE is False
    assert live_discovery.SITEMAP_GUESS_CAP == 4 == len(SITEMAP_FALLBACK_PATHS)
    assert SITEMAP_FALLBACK_PATHS[0] == "/sitemap.xml"
    assert live_discovery.SITEMAP_GUESS_SLOW_HOST_CAP == 1
    assert live_discovery.SITEMAP_GUESS_MAX_404 == 2


# --- a crawl-delay host ----------------------------------------------------------------


@pytest.mark.parametrize("via_cost", [False, True], ids=["robots", "host-cost"])
async def test_a_crawl_delay_host_has_one_location_guessed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sg1: bool, via_cost: bool
) -> None:
    site = StubSite({f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS})
    cost = HostCost() if via_cost else None
    pages, trace = await _collect(tmp_path, site, monkeypatch, crawl_delay=10.0, cost=cost)
    assert pages == []
    if sg1:
        assert _documents(site) == [f"{ORIGIN}/sitemap.xml"]
        assert _sg1_lines(trace) == [
            "SG-1: crawl delay 10 s and no declared sitemap; 1 location guessed"
        ]
    else:
        # Off, a slow host's document cap (SO-1/SB-1) is the only bound.
        assert _documents(site) == (GUESSES[:SLOW_HOST_SITEMAP_DOCUMENTS] if via_cost else GUESSES)
        assert _sg1_lines(trace) == []


async def test_a_crawl_delay_at_the_threshold_counts_and_below_it_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(live_discovery, "SITEMAP_GUESS_RULE", True)
    at = StubSite({f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS})
    await _collect(tmp_path / "at", at, monkeypatch, crawl_delay=SLOW_HOST_SECONDS)
    assert _documents(at) == GUESSES[:1]
    # Below the threshold the host is not slow; the 404 rule alone applies.
    below = StubSite({f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS})
    _pages, trace = await _collect(
        tmp_path / "below", below, monkeypatch, crawl_delay=SLOW_HOST_SECONDS - 1
    )
    assert _documents(below) == GUESSES[:2]
    assert _sg1_lines(trace) == [
        "SG-1: 2 guessed sitemap locations answered 404; 2 more not guessed"
    ]


async def test_the_one_guess_that_answers_is_read_with_its_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sg1: bool
) -> None:
    child = f"{ORIGIN}/page-sitemap.xml"
    site = StubSite(
        {
            f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS,
            f"{ORIGIN}/sitemap.xml": sitemap_index_xml(child),
            child: sitemap_xml(PROGRAMME),
        }
    )
    pages, trace = await _collect(tmp_path, site, monkeypatch, crawl_delay=10.0)
    assert pages == [PROGRAMME]
    # SM-1 already drops the other guesses once one answers: on and off agree.
    assert _documents(site) == [f"{ORIGIN}/sitemap.xml", child]
    assert trace.sitemaps_read == [f"{ORIGIN}/sitemap.xml", child]


async def test_a_declared_sitemap_on_a_crawl_delay_host_is_read_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sg1: bool
) -> None:
    declared = [f"{ORIGIN}/a.xml", f"{ORIGIN}/b.xml", f"{ORIGIN}/c.xml"]
    site = StubSite(
        {
            f"{ORIGIN}/robots.txt": "".join(f"Sitemap: {url}\n" for url in declared),
            f"{ORIGIN}/c.xml": sitemap_xml(PROGRAMME),
        }
    )
    pages, trace = await _collect(tmp_path, site, monkeypatch, crawl_delay=10.0)
    # Declared documents are not guesses: two 404s among them stop nothing.
    assert _documents(site) == declared
    assert pages == [PROGRAMME]
    assert _sg1_lines(trace) == []


# --- a 404-everything host -------------------------------------------------------------


async def test_a_404_everything_host_stops_after_two_guesses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sg1: bool
) -> None:
    site = StubSite({f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS})
    pages, trace = await _collect(tmp_path, site, monkeypatch)
    assert pages == []
    if sg1:
        assert _documents(site) == GUESSES[:2]
        assert _sg1_lines(trace) == [
            "SG-1: 2 guessed sitemap locations answered 404; 2 more not guessed"
        ]
    else:
        assert _documents(site) == GUESSES
        assert _sg1_lines(trace) == []


async def test_only_consecutive_404s_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live_discovery, "SITEMAP_GUESS_RULE", True)
    # 404, 500, 404, then a sitemap: the 500 breaks the run, so every guess is read.
    site = StatusSite(
        {
            f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS,
            GUESSES[3]: sitemap_xml(PROGRAMME),
        },
        {GUESSES[1]: 500},
    )
    pages, trace = await _collect(tmp_path, site, monkeypatch)
    assert _documents(site) == GUESSES
    assert pages == [PROGRAMME]
    assert _sg1_lines(trace) == []


async def test_a_refused_guess_is_not_a_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(live_discovery, "SITEMAP_GUESS_RULE", True)
    site = StatusSite({f"{ORIGIN}/robots.txt": NO_SITEMAP_ROBOTS}, dict.fromkeys(GUESSES, 403))
    await _collect(tmp_path, site, monkeypatch)
    assert _documents(site) == GUESSES


async def test_no_robots_txt_still_guesses_and_stops_after_two_404s(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sg1: bool
) -> None:
    site = StubSite({})
    await _collect(tmp_path, site, monkeypatch)
    assert _documents(site) == (GUESSES[:2] if sg1 else GUESSES)


# --- the harness flag ------------------------------------------------------------------


def test_the_flag_is_a_default_off_negatable_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_benchmark_rule_negations import _parent

    assert live.NEGATABLE_RULES["sitemap-guess-cap"] == (
        ("app.adapters.discovery.live_discovery", "SITEMAP_GUESS_RULE"),
    )
    assert "sitemap-guess-cap" in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--sitemap-guess-cap")
    assert "--sitemap-guess-cap" in commands[0]


def test_the_child_switches_the_rule_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):  # type: ignore[no-untyped-def]
        seen["on"] = live_discovery.SITEMAP_GUESS_RULE

    monkeypatch.setattr(live_discovery, "SITEMAP_GUESS_RULE", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--sitemap-guess-cap"])
    live.main()
    assert seen == {"on": True}
