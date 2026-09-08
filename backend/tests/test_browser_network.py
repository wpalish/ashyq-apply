"""The browser tier and the egress boundary must fail closed.

Regressions for T16 / H02, authored RED-first on baseline 4d2125c. Every
scenario here is offline: the Playwright layer is faked at the
``BrowserFetcher._browser`` seam (``_ensure`` short-circuits when a browser is
already attached, so nothing ever imports or launches Chromium), and the HTTP
tier runs on ``httpx.MockTransport``. No real DNS, no sockets.

Scenarios R1-R5 are RED on the baseline and must turn GREEN with the fix:

- R1  a rendered 404 (or a navigation that returns no response) must not come
      back as ``OK`` - browser.py reported OK regardless of HTTP status.
- R2  the escalation in ``Fetcher._maybe_render`` must not accept or cache an
      error render just because its outcome says OK - fetching.py:459-464.
- R3  a redirect hop's streamed response must be closed before the next hop -
      fetching.py:358-371 leaked one stream per hop.
- R4  a browser-infrastructure exception must surface as a non-OK
      ``FetchResult``, never as a crash out of ``Fetcher.get`` - fetching.py:619.
- R5  6to4 relay and AS112 ranges must be blocked by the network policy -
      network_policy.py:27-37 lacked them.

R6 is a justified-GREEN negative control: the route gate already aborts
metadata addresses and the policy already refuses them. It exists so a later
change to the gate cannot silently drop the abort branch.
"""

from __future__ import annotations

import socket

import httpx
import pytest

from app.adapters.browser import BrowserFetcher
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.network_policy import is_allowed, is_blocked_address
from app.domain.enums import FetchOutcome

try:  # the real exception class when playwright is installed...
    from playwright.async_api import Error as PlaywrightError
except ImportError:  # pragma: no cover - ...a look-alike when it is not

    class PlaywrightError(RuntimeError):  # type: ignore[no-redef]
        """Offline stand-in for playwright.async_api.Error."""


def resolver_returning(*addresses: str):
    """A stand-in for getaddrinfo, so DNS behaviour is testable offline."""

    def resolve(host, port, **_kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
            for a in addresses
        ]

    return resolve


def _allow_example(url: str, **_kwargs):
    """The real policy, with example.com pinned to a public address."""
    from app.adapters.network_policy import check_url as real

    return real(url, resolver=resolver_returning("93.184.216.34"))


#: A 200 whose extractable text is under MIN_USEFUL_TEXT, so a fetcher with a
#: renderer escalates it to the browser tier.
THIN_SHELL_HTML = (
    '<html><head><title>Example University</title></head><body><div id="root"></div></body></html>'
)

#: What Chromium renders for a missing document: real, extractable text on a
#: page whose navigation status is an error.
ERROR_MARKER = "we could not find that page"
ERROR_PAGE_HTML = (
    "<html><head><title>404 Not Found</title></head><body>"
    f"<h1>404 - {ERROR_MARKER}</h1>"
    "<p>The document you requested has moved or never existed.</p>"
    "<p>" + "Nothing lives at this address any more. " * 12 + "</p>"
    "</body></html>"
)

PUBLIC_URL = "http://93.184.216.34/programme"  # literal IP: no DNS, policy-clean
EXAMPLE_URL = "https://ok.example.com/programme"


# --- Fake Playwright layer -------------------------------------------------


class FakePlaywrightResponse:
    """Just the attribute browser.py reads off a navigation response."""

    def __init__(self, status: int) -> None:
        self.status = status


class FakePage:
    """A rendered page: whatever goto() returns and content() hands back."""

    def __init__(
        self,
        goto_result: FakePlaywrightResponse | None = None,
        content: str = "",
    ) -> None:
        self.goto_result = goto_result
        self.content_html = content
        self.handlers: list[tuple[str, object]] = []

    def on(self, event, handler) -> None:
        self.handlers.append((event, handler))

    async def goto(self, url, wait_until=None, timeout=None):
        return self.goto_result

    async def wait_for_timeout(self, ms) -> None:
        return None  # a fake must not actually sit still for 1.2 seconds

    async def content(self) -> str:
        return self.content_html


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.routes: list[tuple[str, object]] = []
        self.closed = False

    async def route(self, pattern, handler) -> None:
        self.routes.append((pattern, handler))

    async def new_page(self) -> FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    """Stands in for the Chromium handle browser.py drives."""

    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.contexts: list[FakeContext] = []

    async def new_context(self, **kwargs) -> FakeContext:
        context = FakeContext(self.page)
        self.contexts.append(context)
        return context


def browser_with(page: FakePage, tmp_path) -> BrowserFetcher:
    """A BrowserFetcher whose Playwright layer is the given fake page.

    ``_ensure`` returns immediately when ``_browser`` is already set, so
    injecting the handle here never touches the real library. The Fetcher is
    never entered as a context manager, so its ``_client`` stays None and the
    robots gate is skipped without any network.
    """
    fetcher = Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False)
    renderer = BrowserFetcher(fetcher)
    renderer._browser = FakeBrowser(page)  # type: ignore[assignment]
    return renderer


class FakeRoute:
    """Records which way the gate decided to go."""

    def __init__(self) -> None:
        self.aborted: str | None = None
        self.continued = False

    async def abort(self, reason: str = "") -> None:
        self.aborted = reason

    async def continue_(self) -> None:
        self.continued = True


class FakeRequest:
    def __init__(self, url: str, resource_type: str = "document") -> None:
        self.url = url
        self.resource_type = resource_type


# --- R1: a rendered error page is not a successful fetch -------------------


class TestRenderedStatusReporting:
    async def test_browser_error_page_is_not_ok(self, tmp_path):
        """A Chromium-rendered 404 must come back as an HTTP error, not OK.

        Baseline: browser.py:141-150 built an OK result for whatever the
        render produced, so a 404/403/429/5xx error page sailed through with
        outcome=OK and the page's text attached.
        """
        page = FakePage(FakePlaywrightResponse(404), ERROR_PAGE_HTML)
        result = await browser_with(page, tmp_path).render(PUBLIC_URL)

        assert result.outcome is FetchOutcome.HTTP_ERROR
        assert result.status_code == 404
        assert result.text == ""

    async def test_render_with_no_response_is_not_ok(self, tmp_path):
        """goto() returning None must not become OK with status_code None.

        Baseline: browser.py:134 stored status=None and still returned OK, a
        fail-open on the one value that says "we never saw a status".
        """
        page = FakePage(None, ERROR_PAGE_HTML)
        result = await browser_with(page, tmp_path).render(PUBLIC_URL)

        assert result.ok is False
        assert result.outcome is FetchOutcome.UNPARSEABLE
        assert result.status_code is None
        assert result.error != ""


# --- R2: the escalation must not launder an error render into the cache -----


class TestEscalationGuard:
    async def test_error_rendering_is_not_escalated_or_cached(self, tmp_path, monkeypatch):
        """A render carrying an error status must not be returned or cached.

        Baseline: fetching.py:459 accepted on ``rendered.ok`` alone, so a
        browser that reported OK for its 404 page was written into the disk
        cache (:463) and returned as the fetch of record.
        """
        monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, headers={"content-type": "text/html"}, text=THIN_SHELL_HTML)

        class BuggyRenderer:
            """Returns exactly what the baseline browser tier returned."""

            async def render(self, url: str) -> FetchResult:
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.OK,
                    status_code=404,
                    content=ERROR_PAGE_HTML.encode("utf-8"),
                    text=ERROR_PAGE_HTML,
                    content_type="text/html; charset=utf-8",
                    final_url=url,
                )

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            fetcher.attach_renderer(BuggyRenderer())
            result = await fetcher.get(EXAMPLE_URL)
            cached = fetcher.cache.get(EXAMPLE_URL)

        # An OK result must never carry an error status: the escalation either
        # keeps the original 200 or comes back as a diagnostic non-OK.
        assert not (result.outcome is FetchOutcome.OK and result.status_code == 404)
        assert ERROR_MARKER not in result.text
        # And the error page must not have been written into the cache.
        assert cached is not None
        assert cached.status_code != 404
        assert ERROR_MARKER not in cached.text


# --- R3: redirect hops must not leak their streamed responses --------------


class ObservableStream(httpx.AsyncByteStream):
    """A stream whose aclose() can be observed by the test."""

    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload
        self.closed = False

    async def __aiter__(self):
        yield self.payload

    async def aclose(self) -> None:
        self.closed = True


class TestRedirectStreamHygiene:
    async def test_redirect_hop_response_is_closed(self, tmp_path, monkeypatch):
        """The streamed 302 must be closed before the fetcher moves on.

        Baseline: fetching.py:358-371 sent every hop with stream=True and
        ``continue``d past redirects without aclose(), leaking one open
        response per hop.
        """
        monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)

        hop_stream = ObservableStream()
        final_stream = ObservableStream(b"<html>final page</html>")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/redirect":
                return httpx.Response(
                    302, headers={"location": "https://ok.example.com/final"}, stream=hop_stream
                )
            return httpx.Response(200, headers={"content-type": "text/html"}, stream=final_stream)

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            result = await fetcher.get("https://ok.example.com/redirect")

        assert result.outcome is FetchOutcome.OK  # the chain itself still completes
        assert hop_stream.closed is True
        assert final_stream.closed is True


# --- R4: infrastructure failures are results, not crashes ------------------


class TestBrowserInfraFailure:
    async def test_browser_infra_failure_is_a_result_not_a_crash(self, tmp_path, monkeypatch):
        """A renderer that raises must become a non-OK result from get().

        Baseline: the escalation call sat in the else-branch of fetching.py's
        retry statement (:619), where none of the excepts above it apply, so a
        playwright error propagated straight out of ``Fetcher.get``.
        """
        monkeypatch.setattr("app.adapters.fetching.check_url", _allow_example)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, headers={"content-type": "text/html"}, text=THIN_SHELL_HTML)

        class CrashingRenderer:
            async def render(self, url: str) -> FetchResult:
                raise PlaywrightError("Target page, context or browser has been closed")

        async with Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False) as fetcher:
            fetcher._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=False
            )
            fetcher.attach_renderer(CrashingRenderer())
            result = await fetcher.get(EXAMPLE_URL)  # must not raise

        assert result.ok is False
        assert result.error != ""

    async def test_render_infra_exception_does_not_crash_the_fetcher(self, tmp_path):
        """new_context/route/new_page blow-ups must surface as a result too.

        Baseline: browser.py:113-125 sat outside the inner try (which only
        wrapped goto/content), so the exception escaped ``BrowserFetcher.render``
        itself. Same frozen contract, one seam earlier.
        """
        fetcher = Fetcher(tmp_path / "c", delay_seconds=0.0, respect_robots=False)
        renderer = BrowserFetcher(fetcher)

        class ExplodingBrowser:
            async def new_context(self, **kwargs):
                raise PlaywrightError("Browser has been closed")

        renderer._browser = ExplodingBrowser()  # type: ignore[assignment]
        result = await renderer.render(PUBLIC_URL)  # must not raise

        assert result.ok is False
        assert result.error != ""


# --- R5: 6to4 relay and AS112 anycast must be unreachable ------------------


class TestSpecialPurposeRanges:
    @pytest.mark.parametrize(
        "address",
        [
            "192.88.99.1",  # 6to4 relay anycast (RFC 7526 retired it)
            "192.31.196.1",  # AS112 blackhole
            "192.52.193.1",  # AS112 blackhole
            "192.175.48.1",  # AS112 blackhole
        ],
    )
    def test_as112_and_6to4_ranges_are_blocked(self, address):
        """ipaddress alone lets these through; the extra blocklist must not."""
        blocked, reason = is_blocked_address(address)
        assert blocked, f"{address} was allowed by the network policy"
        assert reason

    @pytest.mark.parametrize("host", ["192.88.99.1", "192.175.48.1"])
    def test_6to4_relay_and_as112_urls_are_refused(self, host):
        allowed, reason = is_allowed(f"http://{host}/")
        assert not allowed
        assert reason


# --- R6: justified-GREEN negative control ----------------------------------


class TestRouteGateNegativeControl:
    """The gate that routes every request a rendered page makes.

    Already correct on the baseline; recorded so the browser-tier fix cannot
    quietly drop the abort branch while touching this code.
    """

    async def test_route_gate_blocks_metadata(self):
        """The cloud metadata address is refused before a request is made."""
        allowed, reason = is_allowed("http://169.254.169.254/latest/meta-data/")
        assert not allowed
        assert reason

        route, request = FakeRoute(), FakeRequest("http://169.254.169.254/latest/meta-data/")
        await BrowserFetcher._gate_request(route, request)

        assert route.aborted is not None
        assert route.continued is False

    async def test_route_gate_continues_allowed_public_requests(self, monkeypatch):
        """An allowed, non-media request goes through, not into the void."""
        monkeypatch.setattr("app.adapters.browser.is_allowed", lambda url, **k: (True, ""))

        route, request = FakeRoute(), FakeRequest("https://ok.example.com/styles.css", "stylesheet")
        await BrowserFetcher._gate_request(route, request)

        assert route.continued is True
        assert route.aborted is None
