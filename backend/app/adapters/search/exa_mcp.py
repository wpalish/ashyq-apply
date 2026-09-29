"""Official Exa MCP search behind the ordinary public discovery seam.

The keyless hosted endpoint is a supported, rate-limited mode. It is an
explicit alternative, never a way to retry or evade another provider's quota.
Only result URLs/titles/highlights enter discovery; remote page text is ignored.
Every claim still needs its own official-page read through Fetcher.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.adapters.network_policy import BlockedRequest, check_url
from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable

EXA_MCP_URL = "https://mcp.exa.ai/mcp?tools=web_search_advanced_exa"
PROTOCOL_VERSION = "2025-03-26"
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_RESULTS_PER_QUERY = 25
EMPTY_SEARCH_MESSAGE = (
    "No search results found. Please try a different query or adjust your filters."
)


def _rpc_message(body: bytes, request_id: int) -> dict[str, Any]:
    """Read one matching JSON-RPC result from JSON or a bounded SSE response."""
    try:
        text = body.decode("utf-8")
        try:
            messages = [json.loads(text)]
        except ValueError:
            # SSE may include comments, event names and progress notifications.
            # A blank line terminates an event; multi-line data is joined.
            frames = text.replace("\r\n", "\n").split("\n\n")
            messages = []
            for frame in frames:
                data = "\n".join(
                    line[5:].lstrip() for line in frame.splitlines() if line.startswith("data:")
                )
                if data:
                    messages.append(json.loads(data))
        for message in messages:
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if message.get("jsonrpc") != "2.0" or "error" in message:
                raise SearchUnavailable("Exa MCP refused the request")
            result = message.get("result")
            if not isinstance(result, dict):
                break
            return result
    except (UnicodeError, ValueError, TypeError) as exc:
        raise SearchUnavailable("Exa MCP returned an unreadable response") from exc
    raise SearchUnavailable("Exa MCP returned no matching result")


def _search_rows(result: dict[str, Any]) -> list[Any]:
    if result.get("isError"):
        raise SearchUnavailable("Exa MCP could not complete the search")
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and isinstance(structured.get("results"), list):
        return structured["results"]
    blocks = result.get("content")
    if isinstance(blocks, list):
        # The official advanced tool has a non-JSON empty-response branch.
        # Recognize only its exact single, non-error block; arbitrary vendor
        # text or mixed content must not silently masquerade as empty search.
        if (
            len(blocks) == 1
            and isinstance(blocks[0], dict)
            and blocks[0].get("type") == "text"
            and blocks[0].get("text") == EMPTY_SEARCH_MESSAGE
        ):
            return []
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            try:
                body = json.loads(block.get("text", ""))
            except (TypeError, ValueError):
                continue
            if isinstance(body, dict) and isinstance(body.get("results"), list):
                return body["results"]
    raise SearchUnavailable("Exa MCP returned no readable search results")


class ExaMcpSearchProvider:
    """Opt-in keyless search, with one bounded tool call and no retries."""

    name = "exa_mcp"

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._client = client
        self._initialized = False
        self._session_id: str | None = None
        self._initialization_lock = asyncio.Lock()
        self._next_request_id = 1

    def _request_id(self) -> int:
        request_id = self._next_request_id
        self._next_request_id += 1
        return request_id

    async def _post(self, client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        async with client.stream(
            "POST", EXA_MCP_URL, json=payload, headers=headers, follow_redirects=False
        ) as response:
            expected_status = 200 if "id" in payload else 202
            if response.status_code != expected_status:
                raise SearchUnavailable(
                    f"Exa MCP answered {response.status_code}", http_status=response.status_code
                )
            body = bytearray()
            async for chunk in response.aiter_bytes():
                if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise SearchUnavailable("Exa MCP response exceeded its byte limit")
                body.extend(chunk)
            if payload.get("method") == "initialize":
                session = response.headers.get("mcp-session-id")
                if session and len(session) <= 256:
                    self._session_id = session
            if "id" not in payload:
                return {}
            return _rpc_message(bytes(body), payload["id"])

    async def _initialize(self, client: httpx.AsyncClient) -> None:
        async with self._initialization_lock:
            if self._initialized:
                return
            result = await self._post(
                client,
                {
                    "jsonrpc": "2.0",
                    "id": self._request_id(),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "ashyq-apply", "version": "1"},
                    },
                },
            )
            if result.get("protocolVersion") != PROTOCOL_VERSION:
                raise SearchUnavailable("Exa MCP negotiated an unsupported protocol")
            await self._post(client, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            self._initialized = True

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
            raise ValueError("max_results must be at least 1")
        try:
            check_url(EXA_MCP_URL)
        except BlockedRequest as exc:
            raise SearchUnavailable("The Exa MCP endpoint is refused by network policy") from exc

        limit = min(max_results, MAX_RESULTS_PER_QUERY)
        wanted_domains = tuple(d.lower().strip().strip(".") for d in domains if d.strip())
        arguments: dict[str, Any] = {
            "query": query,
            "numResults": limit,
            "type": "auto",
            "enableHighlights": True,
            "highlightsMaxCharacters": 1000,
            "textMaxCharacters": 1,
        }
        if wanted_domains:
            arguments["includeDomains"] = list(wanted_domains)
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        try:
            # Includes initialization, notification and the one actual query.
            async with asyncio.timeout(self._timeout):
                await self._initialize(client)
                result = await self._post(
                    client,
                    {
                        "jsonrpc": "2.0",
                        "id": self._request_id(),
                        "method": "tools/call",
                        "params": {"name": "web_search_advanced_exa", "arguments": arguments},
                    },
                )
        except (httpx.HTTPError, TimeoutError) as exc:
            raise SearchUnavailable("Exa MCP did not answer within the search bounds") from exc
        finally:
            if owns_client:
                await client.aclose()

        retrieved_at = datetime.now(UTC)
        results: list[SearchResult] = []
        for row in _search_rows(result):
            if not isinstance(row, dict) or not isinstance(row.get("url"), str):
                continue
            url = row["url"]
            try:
                parsed = urlparse(url)
                host = (parsed.hostname or "").lower()
            except ValueError:
                continue
            if parsed.scheme not in {"http", "https"} or not host or parsed.username is not None:
                continue
            if wanted_domains and not any(
                host == domain or host.endswith("." + domain) for domain in wanted_domains
            ):
                continue
            highlights = row.get("highlights")
            snippet = (
                " ".join(item for item in highlights if isinstance(item, str))
                if isinstance(highlights, list)
                else ""
            )
            title = row.get("title")
            results.append(
                SearchResult(
                    url=url,
                    title=title[:300] if isinstance(title, str) else "",
                    snippet=snippet[:1000],
                    provider=self.name,
                    rank=len(results) + 1,
                    retrieved_at=retrieved_at,
                )
            )
            if len(results) == limit:
                break
        return SearchResponse(
            query=query, provider=self.name, retrieved_at=retrieved_at, results=tuple(results)
        )
