"""Web search as a replaceable part.

Ask :func:`get_search_provider` for one; never import an adapter directly.
Read ``app.adapters.search.base`` before using a result: a search result is a
discovery hint, not evidence, and no applicant data may reach a provider.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from app.adapters.search.base import (
    SearchError,
    SearchFailureReason,
    SearchProvider,
    SearchProviderNotConfigured,
    SearchResponse,
    SearchResult,
    SearchUnavailable,
)

#: Every provider name this build accepts. A name outside it is refused at
#: startup rather than at the first search.
KNOWN_SEARCH_PROVIDERS = frozenset({"none", "fake", "exa", "exa_mcp", "tavily", "brave", "serper"})

__all__ = [
    "KNOWN_SEARCH_PROVIDERS",
    "SearchError",
    "SearchProvider",
    "SearchProviderNotConfigured",
    "SearchResponse",
    "SearchResult",
    "SearchUnavailable",
    "get_search_provider",
    "reset_search_throttle",
]

#: How long a provider that reported a rate limit is left alone, in seconds. The
#: refusal is about the account's window, not one query: every later request
#: in that window would be refused too and only spends the quota further.
THROTTLE_COOLDOWN_SECONDS = 300.0
#: Provider name to the monotonic time until which it is known to refuse.
#: Process-wide on purpose: discovery, the scholarship fallback and the
#: catalogue identity check each build their own adapter, and a run used to
#: send more than a hundred requests into a refused endpoint (V6b, 2026-10-04).
_THROTTLED_UNTIL: dict[str, float] = {}
#: Deadline-stamped typed provenance. The existing float map remains compatible
#: with deliberately injected legacy HTTP-429 state; a stale record is ignored.
_THROTTLED_ORIGIN: dict[str, tuple[float, int | None, SearchFailureReason | None]] = {}


def _is_explicit_rate_limit(exc: SearchUnavailable) -> bool:
    """Only an HTTP 429 or the fixed typed reason proves a rate limit."""
    return exc.http_status == 429 or exc.reason is SearchFailureReason.RATE_LIMITED


def reset_search_throttle() -> None:
    """Forget recorded rate limits. Tests and a deliberate operator retry only."""
    _THROTTLED_UNTIL.clear()
    _THROTTLED_ORIGIN.clear()


class _ThrottleLatch:
    """Stop later callers after an explicit rate-limit failure escapes.

    The inner provider keeps its existing retry behavior. Once it raises,
    later callers receive a local :class:`SearchUnavailable` until cooldown,
    preserving the original HTTP status and fixed typed reason.
    """

    def __init__(self, inner: SearchProvider) -> None:
        self._inner = inner
        self.name = inner.name

    @property
    def inner(self) -> SearchProvider:
        """The adapter this latch guards (for type checks and diagnostics)."""
        return self._inner

    def __getattr__(self, attr: str) -> object:
        return getattr(self._inner, attr)

    async def search(
        self, *, query: str, domains: Sequence[str] = (), max_results: int = 10
    ) -> SearchResponse:
        until = _THROTTLED_UNTIL.get(self.name, 0.0)
        if time.monotonic() < until:
            origin = _THROTTLED_ORIGIN.get(self.name)
            # A float-only entry is the pre-existing HTTP-429 state contract.
            # It does not establish an HTTP status for a recorded typed failure.
            status, reason = (
                (origin[1], origin[2]) if origin and origin[0] == until else (429, None)
            )
            message = (
                f"{self.name} refused an earlier request with HTTP 429; this request was not sent"
                if status == 429
                else f"{self.name} reported an earlier rate limit; this request was not sent"
            )
            raise SearchUnavailable(message, http_status=status, reason=reason)
        try:
            return await self._inner.search(query=query, domains=domains, max_results=max_results)
        except SearchUnavailable as exc:
            if _is_explicit_rate_limit(exc):
                until = time.monotonic() + THROTTLE_COOLDOWN_SECONDS
                _THROTTLED_UNTIL[self.name] = until
                reason = exc.reason if isinstance(exc.reason, SearchFailureReason) else None
                _THROTTLED_ORIGIN[self.name] = (until, exc.http_status, reason)
            raise


def get_search_provider() -> SearchProvider:
    """The configured provider, or an error saying there is none.

    Raises :class:`SearchProviderNotConfigured` when ``UNIMATCH_SEARCH_PROVIDER``
    is ``none``, which is the default. Discovery must therefore decide in the
    open whether it can run without a search layer; it cannot drift into
    treating "nobody configured search" as "search found nothing".
    """
    from app.config import get_settings

    settings = get_settings()
    if settings.search_provider == "exa_mcp":
        from app.adapters.search.exa_mcp import ExaMcpSearchProvider

        return _ThrottleLatch(ExaMcpSearchProvider())

    if settings.search_provider == "exa":
        from app.adapters.search.exa import ExaSearchProvider

        return _ThrottleLatch(ExaSearchProvider(settings.exa_api_key.get_secret_value()))

    if settings.search_provider == "tavily":
        from app.adapters.search.tavily import TavilySearchProvider

        return _ThrottleLatch(TavilySearchProvider(settings.tavily_api_key.get_secret_value()))

    if settings.search_provider == "brave":
        from app.adapters.search.brave import BraveSearchProvider

        return _ThrottleLatch(BraveSearchProvider(settings.brave_api_key.get_secret_value()))

    if settings.search_provider == "serper":
        from app.adapters.search.serper import SerperSearchProvider

        return _ThrottleLatch(SerperSearchProvider(settings.serper_api_key.get_secret_value()))

    if settings.search_provider == "fake":
        from app.adapters.search.fake import FakeSearchProvider

        return _ThrottleLatch(FakeSearchProvider())

    raise SearchProviderNotConfigured(
        "UNIMATCH_SEARCH_PROVIDER is 'none', so this deployment has no web search layer. "
        "Discovery still has the registry, sitemaps, the catalogue walker and manual seeds. "
        "Set a provider to add search, and handle this error where search is optional."
    )
