"""RS-1 and RS-2: a known redirect and a URL variant cost no second chain of reads.

Read budget analysis 2026-10-18 §4 step 1: Imperial's ``/2027/`` course URLs
answer 301 and take two or three hops, and Chula read its tuition page as
``http://`` and ``https://``. Offline: HTTP runs on ``httpx.MockTransport`` and
DNS on a stub resolver (the seam of tests/test_guessed_url_stall.py). Wire
requests are counted where the scorecard counts them, ``_pinned_request``.
"""

from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.adapters import fetching
from app.adapters.fetching import Fetcher, variant_key
from app.domain.enums import FetchOutcome

HOST = "www.uni.example.edu"
SOURCE = f"https://{HOST}/study/courses/2027/maths-beng"
MIDDLE = f"https://{HOST}/study/courses/maths-beng"
FINAL = f"https://{HOST}/study/courses/maths-beng/"
REDIRECTS = {"/study/courses/2027/maths-beng": MIDDLE, "/study/courses/maths-beng": FINAL}
PAGE = "<html><body>" + "Mathematics BEng. " * 40 + "</body></html>"


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


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every wire request, counted the way the benchmark harness counts them."""
    sent: list[str] = []
    original = fetching._pinned_request

    def counted(client: httpx.AsyncClient, target: Any, **kwargs: Any) -> httpx.Request:
        sent.append(target.url)
        return original(client, target, **kwargs)

    monkeypatch.setattr(fetching, "_pinned_request", counted)
    return sent


def _client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in REDIRECTS:
            return httpx.Response(301, headers={"location": REDIRECTS[path]})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGE)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


def _fetcher(tmp_path: Any) -> Fetcher:
    return Fetcher(tmp_path / "cache", delay_seconds=0.0, respect_robots=False)


class TestVariantKey:
    @pytest.mark.parametrize(
        ("url", "key"),
        [
            ("http://h.edu/a/", "https://h.edu/a"),
            ("https://h.edu/a", "https://h.edu/a"),
            ("https://h.edu/", "https://h.edu/"),
            ("https://h.edu", "https://h.edu/"),
            ("http://h.edu/a/?x=1", "https://h.edu/a?x=1"),
            ("https://h.edu/a#top", "https://h.edu/a"),
        ],
    )
    def test_variants_share_a_key(self, url: str, key: str) -> None:
        assert variant_key(url) == key

    def test_hosts_and_paths_stay_distinct(self) -> None:
        assert variant_key("https://a.h.edu/x") != variant_key("https://b.h.edu/x")
        assert variant_key("https://h.edu/X") != variant_key("https://h.edu/x")
        assert variant_key("https://h.edu:8443/x") != variant_key("https://h.edu/x")
        assert variant_key("fixture://uni/page.html") == "fixture://uni/page.html"

    def test_both_rules_are_off_by_default(self) -> None:
        assert fetching.REDIRECT_MEMORY is False
        assert fetching.URL_VARIANT_DEDUPE is False


class TestRedirectMemory:
    async def test_on_a_second_read_of_the_source_goes_straight_to_the_final_url(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "REDIRECT_MEMORY", True)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            first = await fetcher.get(SOURCE)
            assert len(wire) == 3
            again = await fetcher.get(SOURCE, use_cache=False)
        assert first.outcome is FetchOutcome.OK and again.outcome is FetchOutcome.OK
        assert wire[3:] == [FINAL]
        # Still labelled with the URL the caller asked for.
        assert again.url == SOURCE
        assert again.final_url == FINAL

    async def test_on_a_hop_of_a_known_chain_and_the_final_url_are_cache_hits(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "REDIRECT_MEMORY", True)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            await fetcher.get(SOURCE)
            middle = await fetcher.get(MIDDLE)
            final = await fetcher.get(FINAL)
        assert len(wire) == 3
        assert middle.from_cache and middle.url == MIDDLE and middle.final_url == FINAL
        assert final.from_cache and final.url == FINAL

    async def test_off_every_read_pays_the_chain(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "REDIRECT_MEMORY", False)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            await fetcher.get(SOURCE)
            await fetcher.get(SOURCE, use_cache=False)
            middle = await fetcher.get(MIDDLE)
        assert len(wire) == 3 + 3 + 2
        assert not middle.from_cache

    async def test_on_a_chain_that_ends_in_an_error_is_not_remembered(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "REDIRECT_MEMORY", True)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/old":
                return httpx.Response(301, headers={"location": f"https://{HOST}/gone"})
            return httpx.Response(404)

        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            await fetcher.get(f"https://{HOST}/old")
            await fetcher.get(f"https://{HOST}/old")
        assert len(wire) == 4
        assert fetcher._redirect_memory == {}

    async def test_on_a_cross_site_redirect_is_refused_and_not_remembered(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "REDIRECT_MEMORY", True)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(301, headers={"location": "https://elsewhere.example/x"})

        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            result = await fetcher.get(SOURCE)
        assert result.outcome is FetchOutcome.BLOCKED
        assert fetcher._redirect_memory == {}


class TestUrlVariantDedupe:
    async def test_on_http_and_trailing_slash_variants_are_one_read(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "URL_VARIANT_DEDUPE", True)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            first = await fetcher.get(f"http://{HOST}/fees/")
            second = await fetcher.get(f"https://{HOST}/fees")
            third = await fetcher.get(f"https://{HOST}/fees/")
        assert len(wire) == 1
        assert first.outcome is FetchOutcome.OK
        assert second.from_cache and second.url == f"https://{HOST}/fees"
        assert third.from_cache and third.url == f"https://{HOST}/fees/"

    async def test_off_each_variant_is_its_own_read(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "URL_VARIANT_DEDUPE", False)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            await fetcher.get(f"http://{HOST}/fees/")
            await fetcher.get(f"https://{HOST}/fees")
        assert len(wire) == 2

    async def test_on_different_queries_stay_different_reads(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "URL_VARIANT_DEDUPE", True)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            await fetcher.get(f"https://{HOST}/fees?year=2026")
            await fetcher.get(f"https://{HOST}/fees?year=2027")
        assert len(wire) == 2

    async def test_both_on_a_variant_of_a_hop_is_a_cache_hit(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, wire: list[str]
    ) -> None:
        monkeypatch.setattr(fetching, "REDIRECT_MEMORY", True)
        monkeypatch.setattr(fetching, "URL_VARIANT_DEDUPE", True)
        async with _fetcher(tmp_path) as fetcher:
            fetcher._client = _client()
            await fetcher.get(SOURCE)
            variant = await fetcher.get(SOURCE.replace("https://", "http://") + "/")
        assert variant.from_cache
        assert len(wire) == 3


BACKEND = Path(__file__).resolve().parents[1]


def test_harness_exposes_and_forwards_both_flags() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--redirect-memory" in result.stdout
    assert "--url-variant-dedupe" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "rs1_module.REDIRECT_MEMORY = True" in source
    assert "rs2_module.URL_VARIANT_DEDUPE = True" in source
    assert '*(["--redirect-memory"] if args.redirect_memory else [])' in source
    assert '*(["--url-variant-dedupe"] if args.url_variant_dedupe else [])' in source
