"""Brave Search behind the V2-10 seam — the same contract as Exa and Tavily.

Added 2026-09-25 when Tavily's free plan answered 432 on every query (runs
68-69): Brave keeps a monthly free allowance, and one provider's quota must not
decide whether discovery has a search layer. The rules are Exa's, unchanged.

**A search result is a discovery hint, never evidence.** Brave's
``description`` is carried only in ``SearchResult.snippet``, which nothing may
cite. The page is fetched through ``Fetcher`` before anything it says becomes
a claim.

**Fail closed and fail visibly.** Every transport error, timeout, quota
rejection and malformed body becomes :class:`SearchUnavailable`, with no
retries.

Brave has no domain parameter, so a domain filter is written into the query
with its own ``site:`` operator.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import httpx

from app.adapters.network_policy import BlockedRequest, check_url
from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_RESPONSE_BYTES = 1 * 1024 * 1024
#: Brave's own ceiling per query.
MAX_RESULTS_PER_QUERY = 20


def _with_domains(query: str, domains: Sequence[str]) -> str:
    """The query restricted to ``domains`` with Brave's ``site:`` operator."""
    sites = [f"site:{d}" for d in domains if d]
    if not sites:
        return query
    scope = sites[0] if len(sites) == 1 else "(" + " OR ".join(sites) + ")"
    return f"{query} {scope}"


class BraveSearchProvider:
    """The Brave adapter. Construct it through ``get_search_provider``."""

    name = "brave"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError(
                "BraveSearchProvider needs an API key. It is read from the environment at "
                "startup and never stored in the repository."
            )
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {"x-subscription-token": self._api_key, "accept": "application/json"}

    async def search(
        self,
        *,
        query: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        if not query.strip():
            raise ValueError("A search needs a query")
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1, got {max_results}")

        try:
            check_url(BRAVE_SEARCH_URL)
        except BlockedRequest as exc:
            raise SearchUnavailable(
                f"The search endpoint is not reachable under policy: {exc}"
            ) from exc

        params = {
            "q": _with_domains(query, domains),
            "count": str(min(max_results, MAX_RESULTS_PER_QUERY)),
        }
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        try:
            response = await client.get(BRAVE_SEARCH_URL, params=params, headers=self._headers())
        except httpx.HTTPError as exc:
            raise SearchUnavailable(f"Brave did not answer: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code != httpx.codes.OK:
            # The body is external text and may echo the request; not repeated.
            raise SearchUnavailable(f"Brave answered {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise SearchUnavailable(
                f"Brave returned {len(response.content)} bytes, over the {MAX_RESPONSE_BYTES} cap"
            )
        try:
            body = response.json()
            # A query with no web hits has no "web" block at all.
            rows = (body.get("web") or {}).get("results", [])
            if not isinstance(rows, list):
                raise TypeError("web.results is not a list")
        except (ValueError, AttributeError, TypeError) as exc:
            raise SearchUnavailable(
                f"Brave returned a body this adapter cannot read: {exc}"
            ) from exc

        retrieved_at = datetime.now(UTC)
        results: list[SearchResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = row.get("url") or ""
            if not url:
                # One malformed row must not lose the other nine.
                continue
            description = row.get("description")
            results.append(
                SearchResult(
                    url=url,
                    title=row.get("title") or "",
                    snippet=(description if isinstance(description, str) else "")[:1000],
                    provider=self.name,
                    rank=len(results) + 1,
                    retrieved_at=retrieved_at,
                )
            )
        return SearchResponse(
            query=query, provider=self.name, retrieved_at=retrieved_at, results=tuple(results)
        )
