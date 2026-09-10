"""Playwright tier for JavaScript-rendered pages.

Tier 3 of the fetch strategy, used only when a plain HTTP read produced a page
with no extractable content. It is a deliberate escalation, not a default: a
browser is slow, heavy, and easy to point at pages that should not be
automated.

The same politeness rules apply as to plain HTTP - robots.txt is honoured
before the browser is launched. The browser never authenticates, never fills a
form, and never touches a page behind a login.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.adapters.fetching import Fetcher, FetchResult, assert_no_pii
from app.adapters.network_policy import BlockedRequest, check_url, is_allowed
from app.adapters.offload import off_loop
from app.domain.enums import FetchOutcome

try:  # the real exception class when playwright is installed...
    from playwright.async_api import Error as PlaywrightError
except ImportError:  # pragma: no cover - ...a look-alike when it is not

    class PlaywrightError(RuntimeError):  # type: ignore[no-redef]
        """Offline stand-in for playwright.async_api.Error."""


log = logging.getLogger("unimatch.browser")

RENDER_TIMEOUT_MS = 20_000

#: JSON responses handed to a render's response listener, per page. Bounded
#: twice: no more than this many responses, none longer than this many
#: characters. A catalogue page talks to its own API, not to ours.
MAX_LISTENED_RESPONSES = 20
MAX_LISTENED_RESPONSE_CHARS = 1_000_000


def _json_response_listener(
    collected: list[tuple[str, str, str]],
    listener: Callable[[str, str, str], None],
) -> Callable[[Any], object]:
    """The page.on("response") handler for one render.

    Every JSON response the rendered page receives — by content type or by a
    .json URL — is read (while the context is still open) and handed to the
    listener as ``(response_url, content_type, body_text)``. A response that
    cannot be read and a listener that fails are diagnostics, never a failure
    of the page render they rode in on.
    """

    async def _on_response(response: Any) -> None:
        if len(collected) >= MAX_LISTENED_RESPONSES:
            return
        response_url = ""
        content_type = ""
        body = ""
        try:
            response_url = str(response.url)
            headers = response.headers or {}
            content_type = str(headers.get("content-type", ""))
            path = response_url.split("?", 1)[0].lower()
            if "json" not in content_type.lower() and not path.endswith(".json"):
                return
            body = await response.text()
            if len(body) > MAX_LISTENED_RESPONSE_CHARS:
                return
        except Exception as exc:
            log.info("browser tier could not read a response for %s: %s", response_url[:100], exc)
            return
        collected.append((response_url, content_type, body))
        try:
            listener(response_url, content_type, body)
        except Exception as exc:
            log.info("response listener failed for %s: %s", response_url[:100], exc)

    return _on_response


class BrowserUnavailable(RuntimeError):
    pass


class BrowserFetcher:
    """Renders a page with Chromium and returns its HTML."""

    def __init__(self, fetcher: Fetcher, *, enabled: bool = True) -> None:
        self.fetcher = fetcher
        self.enabled = enabled
        self._playwright = None
        self._browser = None
        self._lock = asyncio.Lock()

    async def _ensure(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover
            raise BrowserUnavailable("playwright is not installed") from exc
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.launch(headless=True)
        except Exception as exc:
            await self._playwright.stop()
            self._playwright = None
            raise BrowserUnavailable(
                "Chromium is not installed. Run: python -m playwright install chromium"
            ) from exc

    @staticmethod
    async def _gate_request(route, request) -> None:
        """Allow or abort one request the rendered page is making.

        The cheap refusal comes first. The policy check resolves DNS, which
        costs a thread from the shared pool, and a rendered page can ask for
        dozens of subresources at once — enough of them queued there would
        stall the document parsing that shares the pool. A resource type we
        refuse outright never needs its name looked up.
        """
        # Trackers, ads and media are neither needed nor wanted.
        if request.resource_type in ("media", "font", "websocket", "manifest"):
            await route.abort("blockedbyclient")
            return
        allowed, reason = await off_loop(is_allowed, request.url)
        if not allowed:
            log.info("browser blocked %s: %s", request.url[:100], reason)
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def render(
        self, url: str, *, response_listener: Callable[[str, str, str], None] | None = None
    ) -> FetchResult:
        assert_no_pii(url)
        try:
            await off_loop(check_url, url)
        except BlockedRequest as exc:
            log.warning("browser tier blocked by network policy: %s", exc)
            return FetchResult(url=url, outcome=FetchOutcome.BLOCKED, error=str(exc))
        if not self.enabled:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.UNPARSEABLE,
                error="Browser rendering is disabled by configuration.",
            )
        if self.fetcher.offline:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.NETWORK_UNAVAILABLE,
                error="Offline mode: cannot render a page.",
            )

        # robots.txt gates the browser exactly as it gates plain HTTP.
        if self.fetcher._client is not None:
            allowed, reason = await self.fetcher.robots.allowed(url, self.fetcher._client)
            if not allowed:
                return FetchResult(url=url, outcome=FetchOutcome.ROBOTS_DISALLOWED, error=reason)

        async with self._lock:
            try:
                await self._ensure()
            except BrowserUnavailable as exc:
                return FetchResult(url=url, outcome=FetchOutcome.UNPARSEABLE, error=str(exc))

            # Setting the context up can fail exactly like a navigation can -
            # the browser may have died between renders. A dead tier is a
            # diagnostic, not a crash out of the fetcher.
            try:
                context = await self._browser.new_context(
                    user_agent=self.fetcher.user_agent,
                    # No downloads, no credentials, no service workers.
                    accept_downloads=False,
                    java_script_enabled=True,
                    bypass_csp=False,
                    service_workers="block",
                )
                # Every request the page makes - navigations and subresources
                # alike - goes through the same policy. A page can otherwise
                # fetch http://169.254.169.254 from JavaScript and read the
                # response.
                await context.route("**/*", self._gate_request)
                page = await context.new_page()
            except Exception as exc:
                log.warning("browser tier unusable for %s: %s", url, exc)
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.UNPARSEABLE,
                    error=f"browser infrastructure failed: {exc}"[:300],
                )
            # Never submit a form or accept a dialog on a page we are reading.
            page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))
            # A catalogue page often builds itself from a JSON endpoint of the
            # site's own. When the caller hands us a listener, every JSON
            # response the page receives is handed over too — bodies are read
            # here, while the context is still open.
            collected: list[tuple[str, str, str]] = []
            if response_listener is not None:
                page.on("response", _json_response_listener(collected, response_listener))
            try:
                resp = await page.goto(
                    url, wait_until="domcontentloaded", timeout=RENDER_TIMEOUT_MS
                )
                try:
                    # A quiet network is the honest "the page has settled" —
                    # and it gives late responses their chance to be heard. It
                    # never settles on polling pages (a Playwright error), and
                    # a page double may not implement the wait at all; either
                    # way the fixed settle wait still runs.
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except (AttributeError, PlaywrightError):
                    await page.wait_for_timeout(1200)  # let late content settle
                html = await page.content()
            except Exception as exc:
                log.info("browser render failed for %s: %s", url, exc)
                return FetchResult(url=url, outcome=FetchOutcome.TIMEOUT, error=str(exc)[:300])
            finally:
                await context.close()

            # The status of the *final* navigation decides the outcome. A
            # rendered 404/403/429/5xx is an error page, not page content: it
            # must not come back as OK, or the escalation in the fetcher will
            # cache it and cite it as a verified claim.
            if resp is None:
                # goto() hands back None when no response was ever received.
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.UNPARSEABLE,
                    error="browser navigation returned no response (no status to trust)",
                )
            if resp.status >= 400:
                log.info("browser tier got HTTP %s for %s", resp.status, url)
                return FetchResult(
                    url=url,
                    outcome=FetchOutcome.HTTP_ERROR,
                    status_code=resp.status,
                    error=f"HTTP {resp.status} on the rendered page",
                    final_url=url,
                )

            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=resp.status,
                content=html.encode("utf-8"),
                text=html,
                content_type="text/html; charset=utf-8",
                fetched_at=datetime.now(UTC),
                final_url=url,
            )


# Escalation lives in Fetcher.attach_renderer / Fetcher._maybe_render so that
# every adapter goes through it. A separate helper that adapters had to
# remember to call is exactly how this tier ended up never being invoked.
