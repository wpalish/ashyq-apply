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
from datetime import UTC, datetime

from app.adapters.fetching import Fetcher, FetchResult, assert_no_pii
from app.adapters.network_policy import BlockedRequest, check_url, is_allowed
from app.domain.enums import FetchOutcome

log = logging.getLogger("unimatch.browser")

RENDER_TIMEOUT_MS = 20_000


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
        """Allow or abort one request the rendered page is making."""
        allowed, reason = is_allowed(request.url)
        if not allowed:
            log.info("browser blocked %s: %s", request.url[:100], reason)
            await route.abort("blockedbyclient")
            return
        # Trackers, ads and media are neither needed nor wanted.
        if request.resource_type in ("media", "font", "websocket", "manifest"):
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

    async def render(self, url: str) -> FetchResult:
        assert_no_pii(url)
        try:
            check_url(url)
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

            context = await self._browser.new_context(
                user_agent=self.fetcher.user_agent,
                # No downloads, no credentials, no service workers.
                accept_downloads=False,
                java_script_enabled=True,
                bypass_csp=False,
                service_workers="block",
            )
            # Every request the page makes - navigations and subresources alike -
            # goes through the same policy. A page can otherwise fetch
            # http://169.254.169.254 from JavaScript and read the response.
            await context.route("**/*", self._gate_request)
            page = await context.new_page()
            # Never submit a form or accept a dialog on a page we are reading.
            page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))
            try:
                resp = await page.goto(
                    url, wait_until="domcontentloaded", timeout=RENDER_TIMEOUT_MS
                )
                await page.wait_for_timeout(1200)  # let late content settle
                html = await page.content()
                status = resp.status if resp else None
            except Exception as exc:
                log.info("browser render failed for %s: %s", url, exc)
                return FetchResult(url=url, outcome=FetchOutcome.TIMEOUT, error=str(exc)[:300])
            finally:
                await context.close()

        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=status,
            content=html.encode("utf-8"),
            text=html,
            content_type="text/html; charset=utf-8",
            fetched_at=datetime.now(UTC),
            final_url=url,
        )


# Escalation lives in Fetcher.attach_renderer / Fetcher._maybe_render so that
# every adapter goes through it. A separate helper that adapters had to
# remember to call is exactly how this tier ended up never being invoked.
