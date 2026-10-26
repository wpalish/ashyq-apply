"""Exa behind the V2-10 seam.

Chosen because its index is neural rather than keyword-based, and the
benchmark says keyword-shaped retrieval is exactly what this project already
does well and still fails with: sitemaps and the catalogue walker are
structural, and they found the correct programme page for one university in
ten. A generator is only worth adding if it is wrong in a *different* way.

Two rules from the phase guide shape everything here.

**A search result is a discovery hint, never evidence.** Exa can return page
text and highlights. Highlights are requested because they help ranking, and
they are carried only in ``SearchResult.snippet``, which nothing may cite. The
page still has to be fetched through ``Fetcher`` before anything it says
becomes a claim. Never pass a highlight to an extractor.

**Fail closed and fail visibly.** Every transport error, timeout, quota
rejection and malformed body becomes :class:`SearchUnavailable`. There are no
retries: a provider that answered 429 once will answer it three times, and a
degraded run must look degraded rather than like a run that found less.

**Record wide, rank narrow (SR-WIDE, the record path only).** Built with
``record_wide=True`` (``UNIMATCH_SEARCH_RECORD_WIDE``, which a record run sets
through ``evaluation.research.live --record-wide``), the adapter asks Exa for
the whole page one request is billed for: ``numResults`` 25 and highlights of
up to :data:`SNIPPET_CHARS` characters. The caller still gets exactly the head
it asked for (``max_results``), so ranking sees the same number of results as
always; the full page travels in ``SearchResponse.page`` for the capture's
search log and the recorded-search store only. The product default is narrow
and unchanged. Every result of the page is a hint under the first rule.
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

EXA_SEARCH_URL = "https://api.exa.ai/search"

#: Balanced relevance and latency. ``deep`` costs several seconds and several
#: times the price per query for synthesis this seam does not want: fusion and
#: the identity check do the reasoning, and they need candidates, not prose.
DEFAULT_SEARCH_TYPE = "auto"

#: A provider is allowed one slow answer, not an open-ended one.
DEFAULT_TIMEOUT_SECONDS = 15.0

#: Most bytes to read from one response. Ten results with highlights is a few
#: tens of kilobytes; anything near this cap is a response worth refusing.
MAX_RESPONSE_BYTES = 1 * 1024 * 1024

#: Hard ceiling per query, whatever a caller asks for. Cost is per result.
MAX_RESULTS_PER_QUERY = 25

#: Characters of joined highlights one result keeps as its snippet. A record
#: run asks Exa for highlights of exactly this length (``maxCharacters``), so
#: what the store keeps is what ranking saw, uncut.
SNIPPET_CHARS = 1000


class ExaSearchProvider:
    """The Exa adapter. Construct it through ``get_search_provider``."""

    name = "exa"

    def __init__(
        self,
        api_key: str,
        *,
        search_type: str = DEFAULT_SEARCH_TYPE,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
        record_wide: bool = False,
    ) -> None:
        if not api_key:
            raise ValueError(
                "ExaSearchProvider needs an API key. It is read from the environment at "
                "startup and never stored in the repository."
            )
        self._api_key = api_key
        self._search_type = search_type
        self._timeout = timeout_seconds
        self._client = client
        self._record_wide = record_wide

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._api_key, "content-type": "application/json"}

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
            # The same egress policy the rest of the service uses. The host is
            # fixed, so this is cheap; it is here so that a future change of
            # endpoint cannot quietly become a request to somewhere else.
            check_url(EXA_SEARCH_URL)
        except BlockedRequest as exc:
            raise SearchUnavailable(
                f"The search endpoint is not reachable under policy: {exc}"
            ) from exc

        payload: dict[str, Any] = {
            "query": query,
            "type": self._search_type,
            "numResults": min(max_results, MAX_RESULTS_PER_QUERY),
            "contents": {"highlights": True},
        }
        if self._record_wide:
            # SR-WIDE: the whole page one request is billed for, with
            # highlights long enough to read offline. The caller still ranks
            # only the head it asked for (below).
            payload["numResults"] = MAX_RESULTS_PER_QUERY
            payload["contents"] = {"highlights": {"maxCharacters": SNIPPET_CHARS}}
        if domains:
            payload["includeDomains"] = list(domains)

        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        try:
            response = await client.post(EXA_SEARCH_URL, json=payload, headers=self._headers())
        except httpx.HTTPError as exc:
            raise SearchUnavailable(f"Exa did not answer: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code != httpx.codes.OK:
            # The body may carry the provider's own explanation; the key never
            # appears in it, but it is not echoed either — a provider message
            # is external text and belongs in a log, not in an exception that
            # may reach a user.
            raise SearchUnavailable(
                f"Exa answered {response.status_code}", http_status=response.status_code
            )

        if len(response.content) > MAX_RESPONSE_BYTES:
            raise SearchUnavailable(
                f"Exa returned {len(response.content)} bytes, over the {MAX_RESPONSE_BYTES} cap"
            )

        try:
            body = response.json()
            rows = body["results"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SearchUnavailable(f"Exa returned a body this adapter cannot read: {exc}") from exc

        retrieved_at = datetime.now(UTC)
        results: list[SearchResult] = []
        for row in rows:
            url = (row or {}).get("url") or ""
            if not url:
                # A result with no URL is not a candidate. Dropped rather than
                # raised: one malformed row should not lose the other nine.
                continue
            highlights = row.get("highlights") or []
            results.append(
                SearchResult(
                    url=url,
                    title=row.get("title") or "",
                    # Joined, truncated, and never cited. See the module docstring.
                    snippet=" ".join(h for h in highlights if isinstance(h, str))[:SNIPPET_CHARS],
                    provider=self.name,
                    rank=len(results) + 1,
                    retrieved_at=retrieved_at,
                )
            )

        if not self._record_wide:
            return SearchResponse(
                query=query,
                provider=self.name,
                retrieved_at=retrieved_at,
                results=tuple(results),
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
                    ("type", self._search_type),
                    ("numResults", MAX_RESULTS_PER_QUERY),
                    ("highlights.maxCharacters", SNIPPET_CHARS),
                ),
                cost=reported_cost(body.get("costDollars"), "total"),
                cost_unit="usd",
            ),
        )
