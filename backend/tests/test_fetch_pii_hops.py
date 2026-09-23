"""The privacy guard must follow the crawler through every redirect hop, and
conditional requests must stay polite.

Regressions for T28 / L01 and the audit finding "find_pii is not called on
redirect hops", authored RED-first on baseline 28d729ca76cd (branch
ai/c2/t28/qa). On that baseline ``Fetcher.get`` runs ``find_pii`` only on the
caller's URL (fetching.py:564); the hop loop in ``_request_with_redirects``
(fetching.py:339-385) re-validates every hop with ``check_url`` but never with
``find_pii``, so ``first.example -> 302 -> second.example/jump?token=...`` is
fetched today and the credential lands in a third party's access log.

Every scenario is offline: HTTP runs on ``httpx.MockTransport`` and DNS on a
stub resolver (the technique of tests/test_ssrf.py, copied not imported), so
no real network is touched.

Scenario status on the baseline:

- 1, 2, 3   RED (assertion): a poisoned hop is requested today.
- 4, 5, 6   RED (missing API): ``FetchResult`` has no etag/last_modified/
            content_hash and ``get()`` takes no conditional-GET arguments.
- 7         justified GREEN: the politeness constants are pinned so the T28
            work cannot quietly loosen them.
- stream pin justified GREEN: T16 already closes hop streams
            (fetching.py:363, 374); pinned so the T28 edit cannot drop it.
"""

from __future__ import annotations

import asyncio
import hashlib
import socket
import unicodedata

import httpx
import pytest

from app.adapters.fetching import (
    DEFAULT_DELAY_SECONDS,
    MAX_ATTEMPTS,
    MAX_PER_HOST_CONCURRENCY,
    Fetcher,
    FetchResult,
)
from app.adapters.network_policy import MAX_REDIRECTS
from app.domain.enums import FetchOutcome

PUBLIC_ADDRESS = "93.184.216.34"
FIRST_HOST = "ok.example.com"
SECOND_HOST = "other.example.com"
ENTRY_URL = f"https://{FIRST_HOST}/start"


def resolver_returning(*addresses: str):
    """A stand-in for getaddrinfo, so DNS behaviour is testable offline."""

    def resolve(host, port, **_kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
            for a in addresses
        ]

    return resolve


def allow_all(url: str, **_kwargs):
    """The real network policy with every name pinned to a public address."""
    from app.adapters.network_policy import check_url as real

    return real(url, resolver=resolver_returning(PUBLIC_ADDRESS))


def counted_chain_handler(counts: dict[str, int], hop_url: str):
    """A 302 from the first host to ``hop_url`` (a second host), then a 200.

    Requests are pinned to a literal IP, so the original host travels in the
    Host header — that is what the handler keys and counts on.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"].split(":")[0]
        counts[host] = counts.get(host, 0) + 1
        if host == FIRST_HOST:
            return httpx.Response(302, headers={"location": hop_url})
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<html>leaky landing page</html>"
        )

    return handler


# --- 1-3: a poisoned redirect hop must be refused, not fetched -------------


class TestPoisonedRedirectHops:
    """find_pii runs on the caller's URL only; the hops it discovers on the
    way are re-validated for SSRF but never for privacy. RED on baseline."""

    async def test_a_credential_in_a_hop_query_is_refused_not_fetched(self, tmp_path, monkeypatch):
        """A hop carrying ``?token=...`` must end the chain before a request."""
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
        hop = f"https://{SECOND_HOST}/jump?token=abc123"
        counts = {FIRST_HOST: 0, SECOND_HOST: 0}

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(counted_chain_handler(counts, hop)),
                follow_redirects=False,
            )
            result = await fetcher.get(ENTRY_URL)

        assert result.outcome is FetchOutcome.REFUSED_PRIVACY
        assert counts[SECOND_HOST] == 0, "the poisoned hop was requested"
        assert fetcher.stats[FetchOutcome.REFUSED_PRIVACY.value] == 1
        assert result.content == b""
        assert result.final_url == hop
        assert "credential-like parameter" in result.error

    async def test_a_long_digit_run_in_a_hop_query_is_refused_not_fetched(
        self, tmp_path, monkeypatch
    ):
        """Nine or more digits in a hop's query string are treated exactly like
        one on the entry URL: a passport/ID/card number must not travel."""
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
        hop = f"https://{SECOND_HOST}/lookup?id=123456789"
        counts = {FIRST_HOST: 0, SECOND_HOST: 0}

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(counted_chain_handler(counts, hop)),
                follow_redirects=False,
            )
            result = await fetcher.get(ENTRY_URL)

        assert result.outcome is FetchOutcome.REFUSED_PRIVACY
        assert counts[SECOND_HOST] == 0, "the poisoned hop was requested"
        assert fetcher.stats[FetchOutcome.REFUSED_PRIVACY.value] == 1
        assert result.content == b""

    async def test_a_poisoned_hop_never_reaches_the_url_policy_or_dns(self, tmp_path, monkeypatch):
        """The privacy refusal must happen before the hop is even validated.

        ``check_url`` is the network stack's front door (it is where DNS
        resolution happens); if a poisoned hop reaches it, the URL has already
        been handed over. This pins the ordering seam: find_pii first, then
        check_url.
        """
        hop = f"https://{SECOND_HOST}/jump?token=abc123"
        seen: list[str] = []

        def recording_check(url: str, **kwargs):
            seen.append(url)
            return allow_all(url, **kwargs)

        monkeypatch.setattr("app.adapters.fetching.check_url", recording_check)
        counts = {FIRST_HOST: 0, SECOND_HOST: 0}

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(counted_chain_handler(counts, hop)),
                follow_redirects=False,
            )
            result = await fetcher.get(ENTRY_URL)

        assert all("token=" not in url for url in seen), f"poisoned hop reached check_url: {seen}"
        assert result.outcome is FetchOutcome.REFUSED_PRIVACY
        assert counts[SECOND_HOST] == 0


# --- 4-5: conditional GET ---------------------------------------------------


class TestConditionalGet:
    """Validators are passed by the caller (from source_pages); a validated
    304 is a terminal success. RED on baseline: get() takes no etag argument
    and FetchResult carries no validators."""

    async def test_a_validated_304_comes_back_as_cached_with_no_body(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
        requests: list[httpx.Request] = []
        url = "https://ok.example.com/page"

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.headers.get("if-none-match") == '"v1"':
                return httpx.Response(304)
            return httpx.Response(
                200,
                headers={"content-type": "text/html", "etag": '"v1"'},
                text="<html>programme page</html>",
            )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            first = await fetcher.get(url)
            second = await fetcher.get(url, etag=first.etag)

        assert second.outcome is FetchOutcome.CACHED
        assert second.status_code == 304
        assert second.text == ""
        assert second.content == b""
        assert second.from_cache is True
        assert second.error == "not modified (304)"
        # Validators present -> the disk cache is skipped and the network is
        # asked, so exactly one request per get() call.
        assert len(requests) == 2
        # The 304 must not have replaced the stored copy with an empty body.
        cached = fetcher.cache.get(url)
        assert cached is not None
        assert b"programme page" in cached.content


class TestConditionalPoliteness:
    async def test_a_conditional_request_still_pays_robots_and_spacing(self, tmp_path, monkeypatch):
        """A 304 is not free: robots.txt is consulted and requests stay spaced.

        RED on baseline for the missing etag parameter; once the parameter
        exists this guards that the conditional path runs through the same
        robots gate and request spacing as an unconditional one.
        """
        slept: list[float] = []

        async def fake_sleep(seconds):
            slept.append(seconds)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
        url = "https://ok.example.com/page"
        robots_requests = 0
        page_requests = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal robots_requests, page_requests
            if request.url.path == "/robots.txt":
                robots_requests += 1
                return httpx.Response(200, text="User-agent: *\nCrawl-delay: 2.5\nAllow: /\n")
            page_requests += 1
            if request.headers.get("if-none-match") == '"v1"':
                return httpx.Response(304)
            return httpx.Response(
                200, headers={"content-type": "text/html", "etag": '"v1"'}, text="<html>page</html>"
            )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=True) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            first = await fetcher.get(url, etag='"v1"')
            second = await fetcher.get(url, etag='"v1"')

        assert robots_requests == 1, "robots.txt must be consulted on the conditional path"
        assert page_requests == 2, "both conditional calls must reach the network"
        assert first.outcome is FetchOutcome.CACHED
        assert second.outcome is FetchOutcome.CACHED
        # The crawl-delay (2.5s), not the configured default (0.0), spaced the
        # second request: one sleep, of the crawl-delay's size.
        assert len(slept) == 1
        assert 2.0 < slept[0] <= 2.5


# --- 6: validators and content hash are recorded ----------------------------


def _content_hash(text: str) -> str:
    """The contract C4 formula: sha256 over NFKC + whitespace-collapsed text."""
    from app.adapters.extraction import html_to_text

    extracted = " ".join(html_to_text(text).split())
    return hashlib.sha256(unicodedata.normalize("NFKC", extracted).encode("utf-8")).hexdigest()


PROGRAMME_BODY = (
    "<html><head><title>MSc Computer Science</title></head><body>"
    "<h1>MSc Computer Science</h1>"
    "<p>Applications close 1 May 2027. Tuition for 2027/28 is published in the fee table.</p>"
    "<p>International applicants submit certified transcripts and proof of English.</p>"
    "</body></html>"
)


class TestValidatorRecording:
    async def test_a_200_records_the_http_validators_and_the_content_hash(
        self, tmp_path, monkeypatch
    ):
        """The values source_pages will store for the next conditional visit.

        RED on baseline: FetchResult has no etag/last_modified/content_hash.
        The content_hash assertion pins the documented formula over a fixed
        body, so a silent change of normalization fails here.
        """
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "content-type": "text/html; charset=utf-8",
                    "etag": '"v1"',
                    "last-modified": "Tue, 01 Sep 2026 00:00:00 GMT",
                },
                text=PROGRAMME_BODY,
            )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            result = await fetcher.get("https://ok.example.com/page")

        assert result.etag == '"v1"'
        assert result.last_modified == "Tue, 01 Sep 2026 00:00:00 GMT"
        assert result.content_hash == _content_hash(PROGRAMME_BODY)

    async def test_an_escalated_result_carries_no_stale_validators(self, tmp_path, monkeypatch):
        """Browser output has no HTTP validators: whatever a renderer claims is
        reset, and the content hash is recomputed from the rendered text.

        RED on baseline (the renderer's FetchResult cannot even carry etag —
        the failure surfaces as a contained browser-tier error, so the first
        assertion below fails on outcome).
        """
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
        thin_shell = (
            '<html><head><title>Example</title></head><body><div id="root"></div></body></html>'
        )
        rendered_html = (
            "<html><body><p>" + "Rendered programme details. " * 60 + "</p></body></html>"
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, headers={"content-type": "text/html", "etag": '"v1"'}, text=thin_shell
            )

        class StaleRenderingTier:
            """A browser tier that (wrongly) echoes the HTTP tier's validators."""

            async def render(self, url: str) -> FetchResult:
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.OK,
                    status_code=200,
                    content=rendered_html.encode("utf-8"),
                    text=rendered_html,
                    content_type="text/html; charset=utf-8",
                    final_url=url,
                    etag='"stale-from-http"',
                    last_modified="Tue, 01 Sep 2026 00:00:00 GMT",
                )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            fetcher.attach_renderer(StaleRenderingTier())
            result = await fetcher.get("https://ok.example.com/page")

        assert result.outcome is FetchOutcome.OK
        assert result.fetch_tier == "browser"
        assert result.etag == ""
        assert result.last_modified == ""
        assert result.content_hash == _content_hash(rendered_html)


# --- 7: politeness constants tripwire (justified GREEN) ---------------------


class TestPolitenessConstants:
    """The T28 work sits inside the politeness machinery; the planner contract
    requires it byte-identical. Already correct on the baseline — recorded so
    a refactor cannot quietly move a dial."""

    def test_the_politeness_dials_keep_their_contract_values(self):
        assert MAX_PER_HOST_CONCURRENCY == 2
        assert DEFAULT_DELAY_SECONDS == 1.5
        assert MAX_REDIRECTS == 5
        assert MAX_ATTEMPTS == 3


# --- stream pin: hop responses stay closed (justified GREEN, T16) -----------


class RecordingStream(httpx.AsyncByteStream):
    """A stream whose aclose() can be observed by the test."""

    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload
        self.closed = False

    async def __aiter__(self):
        yield self.payload

    async def aclose(self) -> None:
        self.closed = True


class TestHopStreamHygiene:
    """Justified GREEN: T16 already closes each redirect hop's streamed
    response (fetching.py:363, 374). Pinned so the T28 hop-guard edit — which
    adds an early return inside this exact loop — cannot drop the aclose."""

    async def test_redirect_hop_streams_stay_closed(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
        hop_stream = RecordingStream()
        final_stream = RecordingStream(b"<html>final page</html>")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.headers["host"].split(":")[0] == FIRST_HOST:
                return httpx.Response(
                    302, headers={"location": f"https://{SECOND_HOST}/final"}, stream=hop_stream
                )
            return httpx.Response(200, headers={"content-type": "text/html"}, stream=final_stream)

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            result = await fetcher.get(f"https://{FIRST_HOST}/redirect")

        assert result.outcome is FetchOutcome.OK  # the chain itself still completes
        assert hop_stream.closed is True
        assert final_stream.closed is True


async def test_a_crawl_delay_too_long_to_wait_is_honoured_by_not_reading(tmp_path, monkeypatch):
    """Run 18: Aalto stalled its whole budget after two requests. A crawl
    delay longer than the run will wait is refused at once — never waited out,
    never ignored by reading faster."""
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    page_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal page_requests
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 120\nAllow: /\n")
        page_requests += 1
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>p</html>")

    async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=True) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        result = await fetcher.get("https://slow.example.com/page")

    assert result.outcome is FetchOutcome.ROBOTS_CRAWL_DELAY
    assert "120s crawl delay" in (result.error or "")
    assert page_requests == 0
    assert slept == []


async def test_a_fetcher_without_a_ceiling_waits_the_delay_out(tmp_path, monkeypatch):
    """The background source scan has no applicant waiting: it reads the page,
    spacing requests by exactly what robots.txt asks."""
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 120\nAllow: /\n")
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>p</html>")

    async with Fetcher(
        tmp_path / "c", delay_seconds=0.0, respect_robots=True, max_crawl_delay=None
    ) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        first = await fetcher.get("https://slow.example.com/a", use_cache=False)
        second = await fetcher.get("https://slow.example.com/b", use_cache=False)

    assert first.outcome is FetchOutcome.OK and second.outcome is FetchOutcome.OK
    assert slept and max(slept) > 100


class _Trickle(httpx.AsyncByteStream):
    """A body that starts and never finishes: each read is well inside
    httpx's per-read timeout, so only a whole-exchange deadline ends it."""

    async def __aiter__(self):
        while True:
            await asyncio.sleep(0.01)
            yield b"#"

    async def aclose(self) -> None:
        return None


async def test_a_robots_txt_that_never_finishes_does_not_hold_the_host(tmp_path, monkeypatch):
    """Run 19: Aalto's robots.txt started and never ended; the case lost 90 s."""
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    monkeypatch.setattr("app.adapters.fetching.ROBOTS_DEADLINE_SECONDS", 0.2)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, stream=_Trickle())
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>p</html>")

    async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=True) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        result = await asyncio.wait_for(fetcher.get("https://slow.example.com/page"), 5)

    # A host whose robots.txt never arrives is not waited on for its pages either.
    assert result.outcome is FetchOutcome.TIMEOUT
    assert "robots.txt never finished" in (result.error or "")


async def test_a_page_that_never_finishes_is_a_timeout_not_a_hang(tmp_path, monkeypatch):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, headers={"content-type": "text/html"}, stream=_Trickle())

    async with Fetcher(
        tmp_path / "c", delay_seconds=0.0, respect_robots=False, timeout=0.05
    ) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        result = await asyncio.wait_for(fetcher.get("https://slow.example.com/page"), 5)

    assert result.outcome is FetchOutcome.TIMEOUT
    assert result.error
    assert calls == 1, "a stalled exchange is not retried"

    async with Fetcher(
        tmp_path / "c2", delay_seconds=0.0, respect_robots=False, timeout=0.05
    ) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        await fetcher.get("https://slow.example.com/a")
        again = await fetcher.get("https://slow.example.com/b")
    assert again.outcome is FetchOutcome.TIMEOUT
    assert "earlier in this run" in (again.error or "")
    assert calls == 2, "the second page of a stalled host is never requested"


async def test_a_slow_resolver_does_not_freeze_the_event_loop(tmp_path, monkeypatch):
    """Name resolution is a blocking call. On the loop, it stopped every
    deadline from firing; off it, the fetch gives up and other work runs."""
    import time as _time

    def slow_check(url):
        _time.sleep(1.0)
        raise AssertionError("should have been abandoned")

    monkeypatch.setattr("app.adapters.fetching.check_url", slow_check)
    monkeypatch.setattr("app.adapters.fetching.DNS_DEADLINE_SECONDS", 0.1)
    ticks = 0

    async def ticker():
        nonlocal ticks
        for _ in range(5):
            await asyncio.sleep(0.01)
            ticks += 1

    async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
        result, _ = await asyncio.gather(fetcher.get("https://slow-dns.example.com/p"), ticker())
        again = await fetcher.get("https://slow-dns.example.com/q")

    assert result.outcome is FetchOutcome.TIMEOUT
    assert "name resolution" in (result.error or "")
    assert ticks == 5
    assert "earlier in this run" in (again.error or "")


@pytest.mark.parametrize(
    ("robots_status", "expected"),
    [
        (503, FetchOutcome.ROBOTS_DISALLOWED),  # unreachable: complete disallow
        (500, FetchOutcome.ROBOTS_DISALLOWED),
        (404, FetchOutcome.OK),  # unavailable: no restrictions
        (403, FetchOutcome.OK),
    ],
)
async def test_robots_txt_status_follows_rfc_9309(tmp_path, monkeypatch, robots_status, expected):
    """RFC 9309 §2.3.1.3–4: a 4xx robots.txt means no restrictions; a 5xx or a
    network failure means the crawler MUST assume the whole site is off limits.
    Until 2026-09-23 both were read as "allowed"."""
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(robots_status, text="")
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>p</html>")

    async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=True) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        result = await fetcher.get("https://site.example.com/page")

    assert result.outcome is expected
    if expected is FetchOutcome.ROBOTS_DISALLOWED:
        assert "RFC 9309" in (result.error or "")


async def test_a_robots_txt_network_failure_disallows_the_site(tmp_path, monkeypatch):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    pages = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal pages
        if request.url.path == "/robots.txt":
            raise httpx.ConnectError("refused")
        pages += 1
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>p</html>")

    async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=True) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        result = await fetcher.get("https://site.example.com/page")

    assert result.outcome is FetchOutcome.ROBOTS_DISALLOWED
    assert pages == 0
