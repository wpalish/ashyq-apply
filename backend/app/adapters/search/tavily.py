"""Tavily behind the V2-10 seam — the same contract as Exa.

Added 2026-09-24 when the Exa account answered 402 on every query (run 48):
one provider's billing must not decide whether discovery has a search layer.
The rules are Exa's, unchanged.

**A search result is a discovery hint, never evidence.** Tavily's ``content``
is a page extract; it is carried only in ``SearchResult.snippet``, which
nothing may cite. The page is fetched through ``Fetcher`` before anything it
says becomes a claim.

**Fail closed and fail visibly.** Every transport error, timeout, quota
rejection and malformed body becomes :class:`SearchUnavailable`, with no
retries.

**Record wide, rank narrow (SR-WIDE, the record path only).** A ``basic``
search costs one credit whatever ``max_results`` is (up to 20), so built with
``record_wide=True`` (``UNIMATCH_SEARCH_RECORD_WIDE``) the adapter asks for 20
results, ``basic`` depth and the request's credit usage; the caller still gets
exactly the head it asked for, and the full page travels in
``SearchResponse.page`` for the capture's search log only. The product default
is narrow and unchanged.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from app.adapters.network_policy import BlockedRequest, check_url
from app.adapters.search.base import (
    ProviderPage,
    SearchResponse,
    SearchResult,
    SearchUnavailable,
    reported_cost,
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

#: ``basic`` costs one credit a query; ``advanced`` costs two for extraction
#: this seam does not use.
DEFAULT_SEARCH_DEPTH = "basic"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_RESPONSE_BYTES = 1 * 1024 * 1024
#: Tavily's own ceiling per query.
MAX_RESULTS_PER_QUERY = 20
#: Characters of a result's ``content`` kept as its snippet.
SNIPPET_CHARS = 1000


class TavilySearchProvider:
    """The Tavily adapter. Construct it through ``get_search_provider``."""

    name = "tavily"

    def __init__(
        self,
        api_key: str,
        *,
        search_depth: str = DEFAULT_SEARCH_DEPTH,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
        record_wide: bool = False,
    ) -> None:
        if not api_key:
            raise ValueError(
                "TavilySearchProvider needs an API key. It is read from the environment at "
                "startup and never stored in the repository."
            )
        if record_wide and search_depth != DEFAULT_SEARCH_DEPTH:
            # The wide page is free only at one credit a query.
            raise ValueError("record_wide asks for basic search depth only")
        self._api_key = api_key
        self._search_depth = search_depth
        self._timeout = timeout_seconds
        self._client = client
        self._record_wide = record_wide

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self._api_key}", "content-type": "application/json"}

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
            check_url(TAVILY_SEARCH_URL)
        except BlockedRequest as exc:
            raise SearchUnavailable(
                f"The search endpoint is not reachable under policy: {exc}"
            ) from exc

        payload: dict[str, Any] = {
            "query": query,
            "search_depth": self._search_depth,
            "max_results": min(max_results, MAX_RESULTS_PER_QUERY),
        }
        if self._record_wide:
            # SR-WIDE: the same one credit buys 20 results; the caller still
            # ranks only the head it asked for (below).
            payload["max_results"] = MAX_RESULTS_PER_QUERY
            payload["include_usage"] = True
        if domains:
            payload["include_domains"] = list(domains)

        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        try:
            response = await client.post(TAVILY_SEARCH_URL, json=payload, headers=self._headers())
        except httpx.HTTPError as exc:
            raise SearchUnavailable(f"Tavily did not answer: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code != httpx.codes.OK:
            # The body is external text and may echo the request; not repeated.
            raise SearchUnavailable(
                f"Tavily answered {response.status_code}", http_status=response.status_code
            )
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise SearchUnavailable(
                f"Tavily returned {len(response.content)} bytes, over the {MAX_RESPONSE_BYTES} cap"
            )
        try:
            body = response.json()
            rows = body["results"]
            if not isinstance(rows, list):
                raise TypeError("results is not a list")
        except (ValueError, KeyError, TypeError) as exc:
            raise SearchUnavailable(
                f"Tavily returned a body this adapter cannot read: {exc}"
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
            content = row.get("content")
            results.append(
                SearchResult(
                    url=url,
                    title=row.get("title") or "",
                    snippet=(content if isinstance(content, str) else "")[:SNIPPET_CHARS],
                    provider=self.name,
                    rank=len(results) + 1,
                    retrieved_at=retrieved_at,
                )
            )
        if not self._record_wide:
            return SearchResponse(
                query=query, provider=self.name, retrieved_at=retrieved_at, results=tuple(results)
            )
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=retrieved_at,
            # Rank narrow: exactly the head the caller asked for.
            results=tuple(results[:max_results]),
            page=ProviderPage(
                results=tuple(results),
                requested=MAX_RESULTS_PER_QUERY,
                parameters=(
                    ("search_depth", self._search_depth),
                    ("max_results", MAX_RESULTS_PER_QUERY),
                    ("include_usage", True),
                ),
                cost=reported_cost(body.get("usage"), "credits"),
                cost_unit="credits",
            ),
        )
