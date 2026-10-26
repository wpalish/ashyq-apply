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
    SearchProvider,
    SearchProviderNotConfigured,
    SearchResponse,
    SearchResult,
    SearchUnavailable,
)

#: Every provider name this build accepts. A name outside it is refused at
#: startup rather than at the first search.
KNOWN_SEARCH_PROVIDERS = frozenset(
    {"none", "fake", "recorded", "exa", "exa_mcp", "tavily", "brave", "serper"}
)

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

#: How long a provider that answered HTTP 429 is left alone, in seconds. The
#: refusal is about the account's window, not one query: every later request
#: in that window would be refused too and only spends the quota further.
THROTTLE_COOLDOWN_SECONDS = 300.0
#: Provider name to the monotonic time until which it is known to refuse.
#: Process-wide on purpose: discovery, the scholarship fallback and the
#: catalogue identity check each build their own adapter, and a run used to
#: send more than a hundred requests into a refused endpoint (V6b, 2026-10-04).
_THROTTLED_UNTIL: dict[str, float] = {}


def reset_search_throttle() -> None:
    """Forget every recorded 429. Tests and a deliberate operator retry only."""
    _THROTTLED_UNTIL.clear()


class _ThrottleLatch:
    """A provider that stops asking once its endpoint has said HTTP 429.

    No retry and no backoff loop: after one refusal every caller in this
    process gets the same refusal locally, without a request, until the
    cool-down passes. The caller sees an ordinary :class:`SearchUnavailable`
    with ``http_status=429``, so every existing quota-stop path still applies.
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
        if time.monotonic() < _THROTTLED_UNTIL.get(self.name, 0.0):
            raise SearchUnavailable(
                f"{self.name} refused an earlier request with HTTP 429; this request was not sent",
                http_status=429,
            )
        try:
            return await self._inner.search(query=query, domains=domains, max_results=max_results)
        except SearchUnavailable as exc:
            if exc.http_status == 429:
                _THROTTLED_UNTIL[self.name] = time.monotonic() + THROTTLE_COOLDOWN_SECONDS
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

        return _ThrottleLatch(
            ExaSearchProvider(
                settings.exa_api_key.get_secret_value(),
                record_wide=settings.search_record_wide,
            )
        )

    if settings.search_provider == "tavily":
        from app.adapters.search.tavily import TavilySearchProvider

        return _ThrottleLatch(
            TavilySearchProvider(
                settings.tavily_api_key.get_secret_value(),
                record_wide=settings.search_record_wide,
            )
        )

    if settings.search_provider == "brave":
        from app.adapters.search.brave import BraveSearchProvider

        return _ThrottleLatch(BraveSearchProvider(settings.brave_api_key.get_secret_value()))

    if settings.search_provider == "serper":
        from app.adapters.search.serper import SerperSearchProvider

        return _ThrottleLatch(SerperSearchProvider(settings.serper_api_key.get_secret_value()))

    if settings.search_provider == "fake":
        from app.adapters.search.fake import FakeSearchProvider

        return _ThrottleLatch(FakeSearchProvider())

    if settings.search_provider == "recorded":
        # Replay only: built from the store and nothing else, so no key and no
        # other provider can be reached from here (recorded.py).
        from app.adapters.search.recorded import RecordedSearchProvider, load_store

        if settings.recorded_search_store is None:
            raise SearchProviderNotConfigured(
                "UNIMATCH_SEARCH_PROVIDER is 'recorded' but UNIMATCH_RECORDED_SEARCH_STORE is unset"
            )
        return _ThrottleLatch(RecordedSearchProvider(load_store(settings.recorded_search_store)))

    raise SearchProviderNotConfigured(
        "UNIMATCH_SEARCH_PROVIDER is 'none', so this deployment has no web search layer. "
        "Discovery still has the registry, sitemaps, the catalogue walker and manual seeds. "
        "Set a provider to add search, and handle this error where search is optional."
    )
