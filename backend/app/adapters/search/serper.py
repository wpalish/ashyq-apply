"""Serper (Google results) behind the V2-10 seam — the same contract as Exa.

Added 2026-09-25 when Tavily's free plan answered 432 on every query (runs
68-69): one provider's quota must not decide whether discovery has a search
layer. The rules are Exa's, unchanged.

**A search result is a discovery hint, never evidence.** Serper's
``snippet`` is carried only in ``SearchResult.snippet``, which nothing may
cite. The page is fetched through ``Fetcher`` before anything it says becomes
a claim.

**Fail closed and fail visibly.** Every transport error, timeout, quota
rejection and malformed body becomes :class:`SearchUnavailable`, with no
retries.

Serper has no domain parameter, so a domain filter is written into the query
with its own ``site:`` operator.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx

from app.adapters.network_policy import BlockedRequest, check_url
from app.adapters.search import intent as intent_module
from app.adapters.search.base import (
    SearchResponse,
    SearchResult,
    SearchUnavailable,
    error_body_excerpt,
)

SERPER_SEARCH_URL = "https://google.serper.dev/search"

DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_RESPONSE_BYTES = 1 * 1024 * 1024
#: Serper answers up to 100 a page; discovery never asks for more than 20.
MAX_RESULTS_PER_QUERY = 20
#: ``hl``/``gl`` as Google takes them: ``no``, ``zh-cn``, ``pt-BR``.
_LOCALE_CODE = re.compile(r"[a-z]{2}(?:-[A-Za-z]{2})?")


def _with_domains(query: str, domains: Sequence[str]) -> str:
    """The query restricted to ``domains`` with Google's ``site:`` operator.

    Under QA-1 a query that already carries ``site:`` for every one of the
    domains is sent as it is: discovery's operator families start with
    ``site:<domain>``, and appending the same operator again only duplicated
    it. Gated with QA-1 rather than unconditional because it changes the
    bytes Google is sent, and every measured Serper baseline carried the
    duplicate.
    """
    sites = [f"site:{d}" for d in domains if d]
    if not sites:
        return query
    if intent_module.ALIAS_QUERIES and all(site in query.split() for site in sites):
        return query
    scope = sites[0] if len(sites) == 1 else "(" + " OR ".join(sites) + ")"
    return f"{query} {scope}"


class SerperSearchProvider:
    """The Serper adapter. Construct it through ``get_search_provider``."""

    name = "serper"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError(
                "SerperSearchProvider needs an API key. It is read from the environment at "
                "startup and never stored in the repository."
            )
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._api_key, "content-type": "application/json"}

    async def search(
        self,
        *,
        query: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        return await self._search(query=query, domains=domains, max_results=max_results)

    async def search_localized(
        self,
        *,
        query: str,
        hl: str,
        gl: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        """``search`` with Serper's ``hl`` (interface language) and ``gl`` (country).

        Plan v3 M5 (ticket 07 Q2, shape d): the query-shape probe asks whether
        a local-language query does better when Google is also told the site's
        language and country. It did (5 of 6), so R5's ``local_language``
        family is sent through this while ``LOCAL_LANGUAGE_QUERIES`` is on, and
        nothing else is. Both values describe the *institution* (its country's
        language), never the applicant, and must be plain locale codes.
        """
        for name, value in (("hl", hl), ("gl", gl)):
            if not _LOCALE_CODE.fullmatch(value):
                raise ValueError(f"{name}={value!r} is not a locale code")
        return await self._search(
            query=query, domains=domains, max_results=max_results, locale={"hl": hl, "gl": gl}
        )

    async def _search(
        self,
        *,
        query: str,
        domains: Sequence[str],
        max_results: int,
        locale: dict[str, str] | None = None,
    ) -> SearchResponse:
        if not query.strip():
            raise ValueError("A search needs a query")
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1, got {max_results}")

        try:
            check_url(SERPER_SEARCH_URL)
        except BlockedRequest as exc:
            raise SearchUnavailable(
                f"The search endpoint is not reachable under policy: {exc}"
            ) from exc

        payload: dict[str, str | int] = {
            "q": _with_domains(query, domains),
            "num": min(max_results, MAX_RESULTS_PER_QUERY),
        }
        if locale:
            payload.update(locale)
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        try:
            response = await client.post(SERPER_SEARCH_URL, json=payload, headers=self._headers())
        except httpx.HTTPError as exc:
            raise SearchUnavailable(f"Serper did not answer: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code != httpx.codes.OK:
            # The body is external text and may echo the request, so the
            # message and every diagnostic built from it stay status-only. The
            # body goes to ``body_excerpt`` (an operator's log: one capped line,
            # the key masked) so that an exhausted account or a revoked key
            # reads as what it is, not as "no reason, http 400".
            raise SearchUnavailable(
                f"Serper answered {response.status_code}",
                http_status=response.status_code,
                body_excerpt=error_body_excerpt(response.content, secrets=(self._api_key,)),
            )
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise SearchUnavailable(
                f"Serper returned {len(response.content)} bytes, over the {MAX_RESPONSE_BYTES} cap"
            )
        try:
            body = response.json()
            # A query with no hits may have no "organic" block at all.
            rows = body.get("organic", [])
            if not isinstance(rows, list):
                raise TypeError("organic is not a list")
        except (ValueError, AttributeError, TypeError) as exc:
            raise SearchUnavailable(
                f"Serper returned a body this adapter cannot read: {exc}"
            ) from exc

        retrieved_at = datetime.now(UTC)
        results: list[SearchResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = row.get("link") or ""
            if not url:
                # One malformed row must not lose the other nine.
                continue
            description = row.get("snippet")
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
