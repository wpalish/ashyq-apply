"""HS-1: one hung guessed URL must not black out its whole host.

dev3, Universitat de Barcelona: the guessed ``www.ub.edu/sitemap/sitemap.xml``
ran 21 s, so ``Fetcher._stalled_hosts`` refused every later ``www.ub.edu``
read in the run although the host answers its other pages in 0.5 s. With
``GUESSED_URL_STALL_EXEMPT`` on, a guess's stall skips only that URL and a
guess waits at most ``GUESSED_URL_TIMEOUT_SECONDS``. Offline: HTTP runs on
``httpx.MockTransport`` and DNS on a stub resolver (the seam of
tests/test_fetch_pii_hops.py).
"""

from __future__ import annotations

import asyncio
import socket
import time
from typing import Any

import httpx
import pytest

from app.adapters import fetching
from app.adapters.discovery.live_discovery import DiscoveryTrace, SitemapReader
from app.adapters.fetching import Fetcher, FetchResult
from app.domain.enums import FetchOutcome

HOST = "www.ub.example.edu"
GUESS = f"https://{HOST}/sitemap/sitemap.xml"
FOUND = f"https://{HOST}/en/hung-programme-page"
HOMEPAGE = f"https://{HOST}/en/"
HUNG_PATHS = {"/sitemap/sitemap.xml", "/en/hung-programme-page"}


def _allow_all(url: str, **_kwargs: Any) -> Any:
    from app.adapters.network_policy import check_url as real

    def resolve(host: str, port: int, **_kw: Any) -> list[Any]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ]

    return real(url, resolver=resolve)


def _client(hung_paths: set[str], hang_seconds: float = 30.0) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in hung_paths:
            await asyncio.sleep(hang_seconds)
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<html>" + "x" * 500 + "</html>"
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.adapters.fetching.check_url", _allow_all)


async def _hang_then_homepage(
    tmp_path: Any, url: str, *, guessed: bool
) -> tuple[Fetcher, FetchResult, FetchResult]:
    async with Fetcher(
        tmp_path / "c", delay_seconds=0.0, respect_robots=False, timeout=0.2
    ) as fetcher:
        fetcher._client = _client(HUNG_PATHS)
        if guessed:
            fetcher.mark_guessed(url)
        hung = await fetcher.get(url)
        after = await fetcher.get(HOMEPAGE)
    return fetcher, hung, after


class TestGuessedUrlStall:
    async def test_flag_on_a_guessed_probe_timeout_leaves_the_host_usable(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetching, "GUESSED_URL_STALL_EXEMPT", True)
        fetcher, hung, after = await _hang_then_homepage(tmp_path, GUESS, guessed=True)
        assert hung.outcome is FetchOutcome.TIMEOUT
        assert HOST not in fetcher._stalled_hosts
        assert after.outcome is FetchOutcome.OK
        assert HOST not in fetcher.refused_hosts

    async def test_flag_off_a_guessed_probe_timeout_stalls_the_host(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetching, "GUESSED_URL_STALL_EXEMPT", False)
        fetcher, hung, after = await _hang_then_homepage(tmp_path, GUESS, guessed=True)
        assert hung.outcome is FetchOutcome.TIMEOUT
        assert HOST in fetcher._stalled_hosts
        assert after.outcome is FetchOutcome.TIMEOUT
        assert "not waited on again" in after.error

    @pytest.mark.parametrize("flag", [True, False])
    async def test_a_discovered_url_timeout_stalls_the_host_either_way(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, flag: bool
    ) -> None:
        monkeypatch.setattr(fetching, "GUESSED_URL_STALL_EXEMPT", flag)
        fetcher, hung, after = await _hang_then_homepage(tmp_path, FOUND, guessed=False)
        assert hung.outcome is FetchOutcome.TIMEOUT
        assert HOST in fetcher._stalled_hosts
        assert after.outcome is FetchOutcome.TIMEOUT

    async def test_flag_on_a_guessed_probe_waits_only_the_capped_timeout(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetching, "GUESSED_URL_STALL_EXEMPT", True)
        monkeypatch.setattr(fetching, "GUESSED_URL_TIMEOUT_SECONDS", 0.2)
        async with Fetcher(
            tmp_path / "c", delay_seconds=0.0, respect_robots=False, timeout=20.0
        ) as fetcher:
            fetcher._client = _client({"/sitemap/sitemap.xml"}, hang_seconds=5.0)
            fetcher.mark_guessed(GUESS)
            started = time.monotonic()
            hung = await fetcher.get(GUESS)
            elapsed = time.monotonic() - started
        assert hung.outcome is FetchOutcome.TIMEOUT
        assert elapsed < 2.0

    def test_the_default_cap_is_short_and_the_flag_is_off(self) -> None:
        assert fetching.GUESSED_URL_TIMEOUT_SECONDS <= 6.0
        assert fetching.GUESSED_URL_STALL_EXEMPT is False


class _RecordingFetcher:
    def __init__(self) -> None:
        self.marked: list[str] = []
        self.robots = None

    def mark_guessed(self, url: str) -> None:
        self.marked.append(url)

    async def get(self, url: str, **_kw: Any) -> FetchResult:
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=404)


class TestSitemapReaderMarksOnlyGuesses:
    async def _collect(self, declared: list[str]) -> list[str]:
        fetcher = _RecordingFetcher()
        reader = SitemapReader(fetcher)  # type: ignore[arg-type]

        async def declared_sitemaps(*_a: Any, **_kw: Any) -> list[str]:
            return declared

        reader._declared_sitemaps = declared_sitemaps  # type: ignore[method-assign]
        await reader.collect(HOMEPAGE, "ub.example.edu", DiscoveryTrace("UB", "ub.example.edu"))
        return fetcher.marked

    async def test_conventional_locations_are_marked_as_guesses(self) -> None:
        assert GUESS in await self._collect([])

    async def test_a_robots_listed_sitemap_is_not_a_guess(self) -> None:
        assert await self._collect([f"https://{HOST}/declared-sitemap.xml"]) == []
