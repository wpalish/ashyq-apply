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
from app.domain.enums import FetchOutcome

log = logging.getLogger("unimatch.browser")

RENDER_TIMEOUT_MS = 20_000
#: Below this, a "successful" HTML fetch is treated as an empty shell worth
#: escalating to the browser.
MIN_USEFUL_TEXT = 400


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

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def render(self, url: str) -> FetchResult:
        assert_no_pii(url)
        if not self.enabled:
            return FetchResult(url=url, outcome=FetchOutcome.UNPARSEABLE,
                               error="Browser rendering is disabled by configuration.")
        if self.fetcher.offline:
            return FetchResult(url=url, outcome=FetchOutcome.NETWORK_UNAVAILABLE,
                               error="Offline mode: cannot render a page.")

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

            context = await self._browser.new_context(user_agent=self.fetcher.user_agent)
            page = await context.new_page()
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=RENDER_TIMEOUT_MS)
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


async def fetch_with_escalation(
    fetcher: Fetcher, browser: BrowserFetcher | None, url: str
) -> tuple[FetchResult, bool]:
    """Plain HTTP first; escalate to a browser only if the page came back empty.

    Returns the result and whether the browser tier was used, so callers can
    record which tier produced a claim.
    """
    from app.adapters.extraction import html_to_text

    result = await fetcher.get(url)
    if not result.ok or result.is_pdf or browser is None:
        return result, False
    if len(html_to_text(result.text)) >= MIN_USEFUL_TEXT:
        return result, False

    rendered = await browser.render(url)
    if rendered.ok and len(html_to_text(rendered.text)) > len(html_to_text(result.text)):
        return rendered, True
    return result, False
