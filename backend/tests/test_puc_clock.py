"""Ticket PC-1: the sitemap stage's clock with no search provider (menu entry (D)).

The mechanism, read from the dev3 no-search captures: the homepage host's one
declared sitemap document ran up against the fetcher's exchange deadline; when
it overran, the fetcher's stall memory closed the whole host for the run, so the
navigation fallback's homepage read was refused without a request and the case
ended with nearly all of its reads unused. With no provider configured nothing
else ends the sitemap stage either. On (``SITEMAP_STAGE_CAP``, no provider):
no sitemap document starts after ``SITEMAP_STAGE_MAX_SECONDS`` of discovery, and
a stalled sitemap document ends the stage and is skipped alone.

Every site here is written for the test (``example-uni.edu``); no page, label or
word comes from a development or heldout case. Offline: HTTP runs on
``httpx.MockTransport`` with the real ``Fetcher`` (robots, stall memory, ledger)
and DNS on a stub resolver.
"""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters import search
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    SEARCH_LATEST_START_SECONDS,
    SITEMAP_STALL_LINE,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
)
from app.adapters.fetching import Fetcher
from app.domain.enums import FetchOutcome
from evaluation.research import live
from tests.test_award_route import Provider
from tests.test_live_discovery import program_html

BACKEND = Path(__file__).resolve().parents[1]
WWW = "www.example-uni.edu"
ADMIT = "admit.example-uni.edu"
HOME = f"https://{WWW}/"
SITEMAP = f"https://{WWW}/sitemap.xml"
HOP = f"https://{ADMIT}/offer"
PROGRAMME = f"https://{ADMIT}/p/41"
#: The fetcher's exchange deadline in these tests, and how long a stalled
#: sitemap document makes it wait (longer, so the exchange overruns).
DEADLINE = 0.3
STALL = 2.0

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
def pc1(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> bool:
    monkeypatch.setattr(live_discovery, "SITEMAP_STAGE_CAP", request.param)
    return bool(request.param)


def _html(title: str, *links: tuple[str, str]) -> str:
    anchors = "".join(f'<li><a href="{href}">{text}</a></li>' for href, text in links)
    return (
        f'<html lang="en"><head><title>{title}</title></head><body>'
        f"<header><nav><ul>{anchors}</ul></nav></header>"
        f"<main><h1>{title}</h1><p>{title} at the university.</p></main></body></html>"
    )


def _urlset(*locs: str) -> str:
    entries = "".join(f"<url><loc>{loc}</loc></url>" for loc in locs)
    return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'


def _index(*locs: str) -> str:
    entries = "".join(f"<sitemap><loc>{loc}</loc></sitemap>" for loc in locs)
    return (
        f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}'
        "</sitemapindex>"
    )


def _stalled_sitemap_site() -> Pages:
    """robots.txt declares one sitemap, which stalls; the homepage links a sibling study page.

    The study page (on another host of the same registrable domain, under a URL
    that names nothing) links the programme page by its field's name.
    """
    return {
        f"https://{WWW}/robots.txt": (200, f"User-agent: *\nSitemap: {SITEMAP}\n"),
        f"https://{ADMIT}/robots.txt": (200, "User-agent: *\n"),
        SITEMAP: (200, _urlset(f"https://{WWW}/about")),
        HOME: (
            200,
            _html(
                "Example University",
                ("/about", "About the university"),
                ("/news", "Latest news"),
                (HOP, "Study"),
            ),
        ),
        HOP: (
            200,
            _html("Undergraduate study", ("/p/41", "Computer Science"), ("/p/77", "Music")),
        ),
        PROGRAMME: (200, program_html("BSc Computer Science")),
    }


async def _discover(
    tmp_path: Path,
    pages: Pages,
    profile: Any,
    *,
    stalls: frozenset[str] = frozenset(),
    on_read: Callable[[str], None] | None = None,
) -> tuple[Any, DiscoveryTrace, list[str]]:
    """Run discovery; every wire request, in order, is the third value.

    A URL in ``stalls`` answers only after ``STALL`` seconds, past the fetcher's
    ``DEADLINE``; ``on_read`` sees every URL as it is requested.
    """
    wire: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        # The Fetcher pins the resolved address; the Host header names the site.
        url = f"https://{request.headers['host']}{request.url.raw_path.decode()}"
        wire.append(url)
        if on_read is not None:
            on_read(url)
        if url in stalls:
            await asyncio.sleep(STALL)
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
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, timeout=DEADLINE) as fetcher:
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
    assert live_discovery.SITEMAP_STAGE_CAP is False
    # The time SB-1b ends the sitemap stage when a provider is configured.
    assert live_discovery.SITEMAP_STAGE_MAX_SECONDS == SEARCH_LATEST_START_SECONDS == 33.0


# --- the fetcher seam -----------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("local", [False, True], ids=["today", "stall-local"])
async def test_a_stall_local_url_leaves_its_host_open(tmp_path: Path, local: bool) -> None:
    """Today a stall closes the host; a stall-local URL's stall skips that URL only."""
    wire: list[str] = []
    slow = f"https://{WWW}/slow.xml"

    async def handler(request: httpx.Request) -> httpx.Response:
        url = f"https://{request.headers['host']}{request.url.raw_path.decode()}"
        wire.append(url)
        if url == slow:
            await asyncio.sleep(STALL)
        if url.endswith("robots.txt"):
            return httpx.Response(200, headers={"content-type": "text/plain"}, text="")
        return httpx.Response(200, headers={"content-type": "text/html"}, text=_html("Home"))

    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, timeout=DEADLINE) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        if local:
            fetcher.mark_stall_local(slow)
        stalled = await fetcher.get(slow)
        after = await fetcher.get(HOME)
    assert stalled.outcome is FetchOutcome.TIMEOUT
    if local:
        assert after.ok
        assert HOME in wire
    else:
        assert after.outcome is FetchOutcome.TIMEOUT
        assert "not waited on again" in after.error
        assert HOME not in wire


# --- the mechanism: a stalled sitemap document and the homepage ------------------------


@pytest.mark.asyncio
async def test_a_stalled_sitemap_no_longer_closes_the_host_to_navigation(
    tmp_path: Path, profile: Any, pc1: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With hop reads on: off, the homepage is never requested; on, the programme is found."""
    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", True)
    if not pc1:

        def refuse(self: Fetcher, url: str) -> None:
            raise AssertionError("the rule ran with its flag off")

        monkeypatch.setattr(Fetcher, "mark_stall_local", refuse)
    candidate, trace, wire = await _discover(
        tmp_path, _stalled_sitemap_site(), profile, stalls=frozenset({SITEMAP})
    )
    urls = [program.url for program in candidate.programs]
    assert wire.count(SITEMAP) == 1
    assert any(error.startswith(f"{SITEMAP}: timeout") for error in trace.errors)
    if not pc1:
        # Today's shape: the stall closed the host, the homepage read was
        # refused without a request, and nothing else was read.
        assert wire == [f"https://{WWW}/robots.txt", f"https://{WWW}/robots.txt", SITEMAP]
        assert urls == []
        assert SITEMAP_STALL_LINE not in trace.errors
        assert "navigation fallback: https://www.example-uni.edu/ unreachable (timeout)" in (
            trace.errors
        )
        return
    assert SITEMAP_STALL_LINE in trace.errors
    assert wire.count(HOME) == 1
    assert wire.index(HOME) > wire.index(SITEMAP)
    assert [url for url, _score in trace.homepage_hop_reads] == [HOP]
    assert urls == [PROGRAMME]
    assert (PROGRAMME, "") in trace.pages_read


@pytest.mark.asyncio
async def test_a_stalled_document_ends_the_sitemap_stage(
    tmp_path: Path, profile: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On, the stall is the stage's verdict: no further document of the stage is read."""
    monkeypatch.setattr(live_discovery, "SITEMAP_STAGE_CAP", True)
    children = [f"https://{WWW}/sitemap-{n}.xml" for n in (1, 2, 3)]
    pages = _stalled_sitemap_site()
    pages[SITEMAP] = (200, _index(*children))
    for child in children:
        pages[child] = (200, _urlset(f"https://{WWW}/about"))
    _candidate, trace, wire = await _discover(
        tmp_path, pages, profile, stalls=frozenset({children[0]})
    )
    assert wire.count(children[0]) == 1
    assert children[1] not in wire
    assert children[2] not in wire
    assert SITEMAP_STALL_LINE in trace.errors
    assert HOME in wire


@pytest.mark.asyncio
async def test_with_a_provider_configured_nothing_changes(
    tmp_path: Path, profile: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule is for the no-provider regime: with one, on reads and records what off does."""
    monkeypatch.setattr(live_discovery, "HOMEPAGE_HOP_READS", True)
    traces: dict[bool, str] = {}
    wires: dict[bool, list[str]] = {}
    for flag in (False, True):
        provider = Provider([])
        monkeypatch.setattr(search, "get_search_provider", lambda provider=provider: provider)
        monkeypatch.setattr(live_discovery, "SITEMAP_STAGE_CAP", flag)
        _candidate, trace, wire = await _discover(
            tmp_path / str(flag), _stalled_sitemap_site(), profile, stalls=frozenset({SITEMAP})
        )
        assert provider.calls, "the provider was asked"
        traces[flag], wires[flag] = _stable(trace), wire
    assert wires[True] == wires[False]
    assert traces[True] == traces[False]
    assert HOME not in wires[True]


# --- the stage's end in time -------------------------------------------------------------


def _many_documents_site() -> tuple[Pages, list[str]]:
    children = [f"https://{WWW}/sitemap-{n}.xml" for n in (1, 2, 3, 4)]
    pages = _stalled_sitemap_site()
    pages[SITEMAP] = (200, _index(*children))
    for n, child in enumerate(children):
        pages[child] = (200, _urlset(f"https://{WWW}/a{n}"))
    return pages, children


@pytest.mark.asyncio
async def test_no_sitemap_document_starts_after_the_stage_time(
    tmp_path: Path, profile: Any, pc1: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each child document advances discovery's clock 12 s: on, the fourth never starts."""
    pages, children = _many_documents_site()
    now = [1000.0]
    monkeypatch.setattr(live_discovery, "_clock", lambda: now[0])

    def advance(url: str) -> None:
        if url in children:
            now[0] += 12.0

    _candidate, trace, wire = await _discover(tmp_path, pages, profile, on_read=advance)
    assert all(child in wire for child in children[:3])
    stage_lines = [line for line in trace.errors if line.startswith("PC-1: sitemap stage ended")]
    if not pc1:
        assert children[3] in wire
        assert stage_lines == []
        return
    # 36 s had gone when the fourth document was due (36 >= 33).
    assert children[3] not in wire
    assert stage_lines == ["PC-1: sitemap stage ended at 36.0 s (33 s with no search provider)"]
    assert trace.sitemaps_read == [SITEMAP, *children[:3]]
    # Navigation still starts after the stage.
    assert HOME in wire


@pytest.mark.asyncio
async def test_off_the_trace_is_the_flagless_trace(
    tmp_path: Path, profile: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Off, the trace and the wire equal those of the rule with nothing to act on.

    On but with a provider configured the rule is inert by construction; off and
    with no stall, on and off read and record the same (clock readings aside).
    """
    pages, _children = _many_documents_site()
    results: dict[bool, tuple[str, list[str]]] = {}
    for flag in (False, True):
        monkeypatch.setattr(live_discovery, "SITEMAP_STAGE_CAP", flag)
        _candidate, trace, wire = await _discover(tmp_path / str(flag), pages, profile)
        results[flag] = (_stable(trace), wire)
    assert results[True] == results[False]


# --- the budgets, flag on ----------------------------------------------------------------

BUDGET_TESTS = (
    "tests/test_case_read_ledger.py",
    "tests/test_stage_budgets.py",
    "tests/test_case_time_budget.py",
    "tests/test_homepage_hop_reads.py",
)


@pytest.mark.parametrize("arm", ["off", "on"])
def test_the_budget_tests_pass_with_the_flag_off_and_on(arm: str) -> None:
    """The 60-read ledger, the stage budgets, the 120 s case clock and NS-1, unchanged."""
    plugin = [] if arm == "off" else ["-p", "tests._sitemap_stage_cap_on"]
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
            # NS-1's own subprocess run of the budget files is the one above.
            "-k",
            "not test_the_budget_tests_pass_with_the_flag_off_and_on",
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert " passed" in result.stdout


def test_the_on_plugin_switches_the_rule_on() -> None:
    from tests import _sitemap_stage_cap_on

    hook: Callable[..., None] = _sitemap_stage_cap_on.pytest_configure
    before = live_discovery.SITEMAP_STAGE_CAP
    try:
        hook(None)
        assert live_discovery.SITEMAP_STAGE_CAP is True
    finally:
        live_discovery.SITEMAP_STAGE_CAP = before


# --- the harness flag --------------------------------------------------------------------


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
    assert "--sitemap-stage-cap" in result.stdout
    assert "--no-sitemap-stage-cap" in result.stdout
    assert live.NEGATABLE_RULES["sitemap-stage-cap"] == (
        ("app.adapters.discovery.live_discovery", "SITEMAP_STAGE_CAP"),
    )
    assert "sitemap-stage-cap" in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--sitemap-stage-cap")
    assert "--sitemap-stage-cap" in commands[0]


def test_the_child_switches_the_rule_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["on"] = live_discovery.SITEMAP_STAGE_CAP

    monkeypatch.setattr(live_discovery, "SITEMAP_STAGE_CAP", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--sitemap-stage-cap"])
    live.main()
    assert seen == {"on": True}
