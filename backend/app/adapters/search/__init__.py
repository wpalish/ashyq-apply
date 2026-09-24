"""Web search as a replaceable part.

Ask :func:`get_search_provider` for one; never import an adapter directly.
Read ``app.adapters.search.base`` before using a result: a search result is a
discovery hint, not evidence, and no applicant data may reach a provider.
"""

from __future__ import annotations

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
KNOWN_SEARCH_PROVIDERS = frozenset({"none", "fake", "exa", "tavily"})

__all__ = [
    "KNOWN_SEARCH_PROVIDERS",
    "SearchError",
    "SearchProvider",
    "SearchProviderNotConfigured",
    "SearchResponse",
    "SearchResult",
    "SearchUnavailable",
    "get_search_provider",
]


def get_search_provider() -> SearchProvider:
    """The configured provider, or an error saying there is none.

    Raises :class:`SearchProviderNotConfigured` when ``UNIMATCH_SEARCH_PROVIDER``
    is ``none``, which is the default. Discovery must therefore decide in the
    open whether it can run without a search layer; it cannot drift into
    treating "nobody configured search" as "search found nothing".
    """
    from app.config import get_settings

    settings = get_settings()
    if settings.search_provider == "exa":
        from app.adapters.search.exa import ExaSearchProvider

        return ExaSearchProvider(settings.exa_api_key.get_secret_value())

    if settings.search_provider == "tavily":
        from app.adapters.search.tavily import TavilySearchProvider

        return TavilySearchProvider(settings.tavily_api_key.get_secret_value())

    if settings.search_provider == "fake":
        from app.adapters.search.fake import FakeSearchProvider

        return FakeSearchProvider()

    raise SearchProviderNotConfigured(
        "UNIMATCH_SEARCH_PROVIDER is 'none', so this deployment has no web search layer. "
        "Discovery still has the registry, sitemaps, the catalogue walker and manual seeds. "
        "Set a provider to add search, and handle this error where search is optional."
    )
