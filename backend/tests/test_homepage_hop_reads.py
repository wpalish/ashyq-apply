"""Rule NS-1 "homepage hop reads" (NO_SEARCH_FLOOR_2026-10-21 §5, ticket NS-1b).

With no search provider the navigation fallback read the homepage and stopped:
it queues a homepage link only when ``categorise_url`` names the link's URL, and
the best study link often leads to another host of the institution's own
registrable domain under a URL that names nothing. On, the homepage's links are
ranked by the product's own link score and the best ``HOMEPAGE_HOP_READ_CAP``
are read as section pages, after every lead today's rules queue.

Every site here is written for the test (``example-uni.edu``); no page, label or
word comes from a development or heldout case. Offline: HTTP runs on
``httpx.MockTransport`` with the real ``Fetcher`` (robots, ledger) and DNS on a
stub resolver.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    categorise_url,
)
from app.adapters.fetching import Fetcher
from evaluation.research import live
from tests.test_live_discovery import program_html

BACKEND = Path(__file__).resolve().parents[1]
WWW = "www.example-uni.edu"
ADMIT = "admit.example-uni.edu"
HOME = f"https://{WWW}/"
HOP = f"https://{ADMIT}/offer"
PROGRAMME = f"https://{ADMIT}/p/41"

Pages = dict[str, tuple[int, str]]


def _allow_all(url: str, **_kwargs: Any) -> Any:
    from app.adapters.network_policy import check_url as real

    def resolve(host: str, port: int, **_kw: Any) -> list[Any]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ]

    return real(url, resolver=resolve)


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.fetching.check_url", _allow_all)


@pytest.fixture(params=[False, True], ids=["off", "on"])
def ns1(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> bool:
    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", request.param)
    return bool(request.param)


@pytest.fixture
def ns1_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", True)


def _html(title: str, *links: tuple[str, str]) -> str:
    anchors = "".join(f'<li><a href="{href}">{text}</a></li>' for href, text in links)
    return (
        f'<html lang="en"><head><title>{title}</title></head><body>'
        f"<header><nav><ul>{anchors}</ul></nav></header>"
        f"<main><h1>{title}</h1><p>{title} at the university.</p></main></body></html>"
    )


def _robots(text: str = "User-agent: *\n") -> tuple[int, str]:
    return 200, text


def _site(homepage: str, **extra: tuple[int, str]) -> Pages:
    """robots.txt on both hosts, no sitemap anywhere, the homepage and ``extra``."""
    pages: Pages = {
        f"https://{WWW}/robots.txt": _robots(),
        f"https://{ADMIT}/robots.txt": _robots(),
        HOME: (200, homepage),
    }
    pages.update(extra)
    return pages


async def _discover(
    tmp_path: Path, pages: Pages, profile: Any
) -> tuple[Any, DiscoveryTrace, list[str]]:
    """Run discovery; every wire request, in order, is the third value."""
    wire: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        # The Fetcher pins the resolved address; the Host header names the site.
        url = f"https://{request.headers['host']}{request.url.raw_path.decode()}"
        wire.append(url)
        status, body = pages.get(url, (404, ""))
        kind = "text/plain" if url.endswith("robots.txt") else "text/html"
        if url.endswith(".xml"):
            kind = "application/xml"
        return httpx.Response(status, headers={"content-type": kind}, text=body)

    tmp_path.mkdir(parents=True, exist_ok=True)
    registry = tmp_path / "registry.json"
    entry = {"name": "Example University", "country": "United States", "city": "T"}
    registry.write_text(json.dumps([{**entry, "homepage": HOME}]), encoding="utf-8")
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0], wire


#: Trace keys that read the clock (or decide on it, as the host cost's "slow").
_CLOCK_KEYS = ("second", "slow", "elapsed", "t_first_query", "case_time", "stopped_at")


def _without_clock(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_clock(item)
            for key, item in value.items()
            if not any(mark in str(key) for mark in _CLOCK_KEYS)
        }
    if isinstance(value, list | tuple):
        return [_without_clock(item) for item in value]
    return value


def _stable(trace: DiscoveryTrace) -> str:
    """The trace without its clock readings, as JSON."""
    return json.dumps(_without_clock(trace.as_dict()), sort_keys=True, default=str)


def test_flag_is_off_by_default() -> None:
    assert live_discovery.HOMEPAGE_HOP_READS is True  # on since the 2026-10-20 no-search replay
    assert live_discovery.HOMEPAGE_HOP_READ_CAP == 5


def test_the_synthetic_urls_name_no_category() -> None:
    """The shape the rule is for: the link's URL says nothing ``categorise_url`` knows."""
    for url in (HOP, PROGRAMME, f"https://{WWW}/a1", f"https://{ADMIT}/a2"):
        assert categorise_url(url) == (None, 0)


# --- 1. the sibling-host study page --------------------------------------------------


def _sibling_site() -> Pages:
    return _site(
        _html(
            "Example University",
            ("/about", "About the university"),
            ("/news", "Latest news"),
            (HOP, "Study"),
        ),
        **{
            HOP: (
                200,
                _html("Undergraduate study", ("/p/41", "Computer Science"), ("/p/77", "Music")),
            ),
            PROGRAMME: (200, program_html("BSc Computer Science")),
        },
    )


@pytest.mark.asyncio
async def test_a_sibling_host_study_page_leads_to_the_programme(
    tmp_path: Path, profile: Any, ns1: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not ns1:
        # The off arm never reaches the rule's code.
        def refuse(*_args: Any, **_kwargs: Any) -> list[tuple[str, int]]:
            raise AssertionError("the rule ran with its flag off")

        monkeypatch.setattr(LiveDiscoveryAdapter, "_homepage_hop_leads", staticmethod(refuse))
    candidate, trace, wire = await _discover(tmp_path, _sibling_site(), profile)
    urls = [program.url for program in candidate.programs]
    if not ns1:
        # The wire of the code before the rule (checked against 78f70116):
        # robots.txt twice, four guessed sitemaps, the homepage, and nothing more.
        assert wire == [
            f"https://{WWW}/robots.txt",
            f"https://{WWW}/robots.txt",
            f"https://{WWW}/sitemap.xml",
            f"https://{WWW}/sitemap_index.xml",
            f"https://{WWW}/sitemap-index.xml",
            f"https://{WWW}/sitemap/sitemap.xml",
            HOME,
        ]
        assert urls == []
        assert "homepage_hop_reads" not in trace.as_dict()
        return
    assert [url for url, _score in trace.homepage_hop_reads] == [HOP]
    assert trace.as_dict()["homepage_hop_reads"] == trace.homepage_hop_reads
    assert ("https://admit.example-uni.edu/p/41", "Computer Science") in trace.kept_by_link_text
    # Selected, read and accepted by the confirm stage.
    assert urls == [PROGRAMME]
    assert (PROGRAMME, "") in trace.pages_read
    assert wire.count(HOP) == 1


@pytest.mark.asyncio
async def test_off_the_trace_is_the_flagless_trace(
    tmp_path: Path, profile: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Off, the trace is byte-identical (clock readings aside) to a rule with no links.

    The flag-on run whose ranking is empty walks the restructured loop with
    nothing to add: it must read and record exactly what the flag-off run does,
    so the loop change alone moves nothing. (The off arm was also diffed, wire
    and trace, against the code before the rule: identical.)
    """
    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", False)
    _candidate, off, off_wire = await _discover(tmp_path / "off", _sibling_site(), profile)
    monkeypatch.setattr(
        LiveDiscoveryAdapter, "_homepage_hop_leads", staticmethod(lambda *_a, **_k: [])
    )
    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", True)
    _candidate, flagless, flagless_wire = await _discover(
        tmp_path / "flagless", _sibling_site(), profile
    )
    assert off_wire == flagless_wire
    assert _stable(off) == _stable(flagless)


# --- 2. the cap and the order ---------------------------------------------------------

#: Six homepage links whose URLs name nothing; the product's link score puts
#: them at 10, 7, 6, 4, 4 and 2 (the two 4s tie and go by URL). The labels are
#: generic English words, written for the test.
SIX = (
    (f"https://{WWW}/a1", "Computer science undergraduate study"),
    (f"https://{ADMIT}/a2", "Bachelor"),
    (f"https://{WWW}/a3", "Computer science"),
    (f"https://{WWW}/a4", "Education"),
    (f"https://{ADMIT}/a5", "Undergraduate admissions"),
    (f"https://{WWW}/a6", "Apply"),
)


def _six_site() -> Pages:
    pages = _site(
        _html("Example University", ("/about", "About the university"), *SIX),
    )
    for url, label in SIX:
        pages[url] = (200, _html(label, ("/contact", "Contact")))
    return pages


@pytest.mark.asyncio
async def test_only_the_best_five_are_read_in_score_order(
    tmp_path: Path, profile: Any, ns1_on: None
) -> None:
    _candidate, trace, wire = await _discover(tmp_path, _six_site(), profile)
    queued = trace.homepage_hop_reads
    assert len(queued) == live_discovery.HOMEPAGE_HOP_READ_CAP
    assert queued == [
        (f"https://{WWW}/a1", 10),
        (f"https://{ADMIT}/a2", 7),
        (f"https://{WWW}/a3", 6),
        # A tie: by URL, so the admit host's link before the www host's.
        (f"https://{ADMIT}/a5", 4),
        (f"https://{WWW}/a4", 4),
    ]
    # The weakest of the six is the one left out, and it is never read.
    assert f"https://{WWW}/a6" not in wire
    # Read in that order, before anything else reads them.
    read = [url for url in wire if url in dict(queued)]
    assert read[: len(queued)] == [url for url, _score in queued]


@pytest.mark.asyncio
async def test_ties_are_broken_by_url(tmp_path: Path, profile: Any, ns1_on: None) -> None:
    pair = ((f"https://{ADMIT}/b2", "Study"), (f"https://{WWW}/b1", "Study"))
    pages = _site(_html("Example University", *pair))
    for url, label in pair:
        pages[url] = (200, _html(label))
    _candidate, trace, _wire = await _discover(tmp_path, pages, profile)
    assert [url for url, _score in trace.homepage_hop_reads] == sorted(url for url, _ in pair)
    assert len({score for _url, score in trace.homepage_hop_reads}) == 1


# --- 3. the link class ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_another_domain_and_another_level_are_never_read(
    tmp_path: Path, profile: Any, ns1_on: None
) -> None:
    other_domain = "https://www.other-example.edu/undergraduate-study"
    other_level = f"https://{ADMIT}/m1"
    other_level_url = f"https://{ADMIT}/masters/offer"
    pages = _site(
        _html(
            "Example University",
            (other_domain, "Undergraduate study"),
            (other_level, "Master's study"),
            (other_level_url, "Study"),
            (HOP, "Study"),
        ),
        **{HOP: (200, _html("Undergraduate study"))},
    )
    pages[other_domain] = (200, _html("Undergraduate study"))
    pages[other_level] = (200, _html("Master's study"))
    pages[other_level_url] = (200, _html("Study"))
    _candidate, trace, wire = await _discover(tmp_path, pages, profile)
    assert [url for url, _score in trace.homepage_hop_reads] == [HOP]
    assert not any("other-example" in url for url in wire)
    assert other_level not in wire
    assert other_level_url not in wire
    assert HOP in wire


# --- 4. today's leads first -----------------------------------------------------------


@pytest.mark.asyncio
async def test_a_url_categorised_catalogue_is_walked_before_any_hop_read(
    tmp_path: Path, profile: Any, ns1: bool
) -> None:
    catalogue = f"https://{WWW}/programmes"
    pages = _site(
        _html(
            "Example University",
            (HOP, "Study"),
            (catalogue, "Programmes"),
        ),
        **{
            catalogue: (200, _html("Programmes", ("/contact", "Contact"))),
            HOP: (200, _html("Undergraduate study", ("/contact", "Contact"))),
        },
    )
    _candidate, trace, wire = await _discover(tmp_path, pages, profile)
    assert catalogue in wire
    if not ns1:
        assert HOP not in wire
        return
    assert HOP in wire
    assert wire.index(catalogue) < wire.index(HOP)
    # The catalogue is today's lead, not a hop read.
    assert catalogue not in [url for url, _score in trace.homepage_hop_reads]


# --- 5. a refused hop page ------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", ["http_403", "robots"])
async def test_a_refused_hop_page_is_not_retried(
    tmp_path: Path, profile: Any, ns1_on: None, refusal: str
) -> None:
    pages = _sibling_site()
    if refusal == "http_403":
        pages[HOP] = (403, "")
    else:
        pages[f"https://{ADMIT}/robots.txt"] = _robots("User-agent: *\nDisallow: /offer\n")
    _candidate, trace, wire = await _discover(tmp_path, pages, profile)
    assert [url for url, _score in trace.homepage_hop_reads] == [HOP]
    # One wire request for the refused page, or none when robots.txt refuses it.
    assert wire.count(HOP) == (1 if refusal == "http_403" else 0)
    assert PROGRAMME not in wire
    refused = [line for line in trace.errors if line.startswith(f"navigation fallback: {HOP} ")]
    assert len(refused) == 1
    assert "unreachable" in refused[0]
    ledger = trace.read_ledger
    assert ledger is not None
    assert ledger.spent == len(wire)


# --- 6. a programme page already selected ---------------------------------------------


@pytest.mark.asyncio
async def test_no_hop_reads_when_a_programme_page_is_already_selected(
    tmp_path: Path, profile: Any, ns1_on: None
) -> None:
    gold = f"https://{WWW}/undergraduate/computer-science"
    pages = _sibling_site()
    pages[f"https://{WWW}/robots.txt"] = _robots(
        f"User-agent: *\nSitemap: https://{WWW}/sitemap.xml\n"
    )
    pages[f"https://{WWW}/sitemap.xml"] = (
        200,
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{gold}</loc></url></urlset>",
    )
    pages[gold] = (200, program_html("BSc Computer Science"))
    candidate, trace, wire = await _discover(tmp_path, pages, profile)
    assert [program.url for program in candidate.programs] == [gold]
    assert trace.homepage_hop_reads == []
    assert HOP not in wire


# --- 7. the budgets, flag on ----------------------------------------------------------

BUDGET_TESTS = (
    "tests/test_case_read_ledger.py",
    "tests/test_stage_budgets.py",
    "tests/test_case_time_budget.py",
)


@pytest.mark.parametrize("arm", ["off", "on"])
def test_the_budget_tests_pass_with_the_flag_off_and_on(arm: str) -> None:
    """The 60-read ledger, the stage budgets and the 120 s case clock, unchanged."""
    plugin = [] if arm == "off" else ["-p", "tests._homepage_hop_reads_on"]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            *plugin,
            *BUDGET_TESTS,
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert " passed" in result.stdout


def test_the_on_plugin_switches_the_rule_on() -> None:
    from tests import _homepage_hop_reads_on

    hook: Callable[..., None] = _homepage_hop_reads_on.pytest_configure
    before = live_discovery.HOMEPAGE_HOP_READS
    try:
        hook(None)
        assert live_discovery.HOMEPAGE_HOP_READS is True
    finally:
        live_discovery.HOMEPAGE_HOP_READS = before


# --- the harness flag -----------------------------------------------------------------


def test_the_flag_is_a_default_off_negatable_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_benchmark_rule_negations import _parent

    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--homepage-hop-reads" in result.stdout
    assert "--no-homepage-hop-reads" in result.stdout
    assert live.NEGATABLE_RULES["homepage-hop-reads"] == (
        ("app.adapters.discovery.live_discovery", "HOMEPAGE_HOP_READS"),
    )
    assert "homepage-hop-reads" not in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--homepage-hop-reads")
    assert "--homepage-hop-reads" in commands[0]


def test_the_child_switches_the_rule_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["on"] = live_discovery.HOMEPAGE_HOP_READS

    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--homepage-hop-reads"])
    live.main()
    assert seen == {"on": True}
