"""Exa MCP discovery contract, exercised entirely through mock HTTP transport."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest

import app.adapters.search.exa_mcp as module
from app.adapters.network_policy import BlockedRequest
from app.adapters.search.base import SearchUnavailable, search_failure_diagnostic
from app.adapters.search.exa_mcp import (
    EXA_MCP_URL,
    MAX_RESPONSE_BYTES,
    MAX_RESULTS_PER_QUERY,
    PROTOCOL_VERSION,
    ExaMcpSearchProvider,
)
from app.config import Settings

ROWS = [
    {
        "url": "https://uni.edu/bachelors/cs",
        "title": "BSc Computer Science",
        "highlights": ["Programme information", "Application requirements"],
        "text": "REMOTE PAGE TEXT IS NOT FETCHED EVIDENCE",
    },
    {"url": "https://uni.edu/faq", "title": "FAQ"},
]
PRIVATE_MARKER = "private-query-and-provider-secret"
EMPTY_RESULT_MARKER = (
    "No search results found. Please try a different query or adjust your filters."
)
Reply = Callable[[httpx.Request], httpx.Response]


def rpc_response(request_id: int, result: object, *, sse: bool = False) -> httpx.Response:
    message = {"jsonrpc": "2.0", "id": request_id, "result": result}
    if not sse:
        return httpx.Response(200, json=message)
    # Notifications and unrelated results precede a multi-line matching event.
    payload = "\n".join("data: " + line for line in json.dumps(message, indent=2).splitlines())
    body = (
        ": keepalive\r\n\r\n"
        'event: message\r\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}'
        "\r\n\r\n"
        'data: {"jsonrpc":"2.0","id":999,"result":{}}\r\n\r\n'
        + "event: message\n"
        + payload
        + "\n\n"
    )
    return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})


def tool_result(rows: list[Any], *, structured: bool = False) -> dict[str, Any]:
    if structured:
        return {"structuredContent": {"results": rows}, "content": []}
    return {"content": [{"type": "text", "text": json.dumps({"results": rows})}]}


async def test_official_single_text_empty_marker_is_legitimate_empty(make_provider):
    server = McpServer(result={"content": [{"type": "text", "text": EMPTY_RESULT_MARKER}]})
    response = await make_provider(server).search(query="public programme query")

    assert response.provider == "exa_mcp"
    assert response.results == ()
    assert server.methods == ["initialize", "notifications/initialized", "tools/call"]


async def test_error_flag_keeps_empty_marker_unavailable(make_provider):
    server = McpServer(
        result={"isError": True, "content": [{"type": "text", "text": EMPTY_RESULT_MARKER}]}
    )
    with pytest.raises(SearchUnavailable):
        await make_provider(server).search(query="public programme query")

    assert server.methods == ["initialize", "notifications/initialized", "tools/call"]


async def test_empty_marker_does_not_hide_unknown_mixed_content(make_provider):
    server = McpServer(
        result={
            "content": [
                {"type": "text", "text": EMPTY_RESULT_MARKER},
                {"type": "text", "text": PRIVATE_MARKER},
            ]
        }
    )
    with pytest.raises(SearchUnavailable) as caught:
        await make_provider(server).search(query="public programme query")

    assert PRIVATE_MARKER not in str(caught.value)
    assert server.methods == ["initialize", "notifications/initialized", "tools/call"]


class McpServer:
    def __init__(
        self,
        *,
        result: dict[str, Any] | None = None,
        sse: bool = False,
        session_id: str | None = "mock-session",
        overrides: dict[str, Reply] | None = None,
    ) -> None:
        self.calls: list[httpx.Request] = []
        self.result = result if result is not None else tool_result(ROWS)
        self.sse = sse
        self.session_id = session_id
        self.overrides = overrides or {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        payload = json.loads(request.content)
        method = payload["method"]
        if method in self.overrides:
            return self.overrides[method](request)
        if method == "initialize":
            response = rpc_response(
                payload["id"], {"protocolVersion": PROTOCOL_VERSION}, sse=self.sse
            )
            if self.session_id:
                response.headers["mcp-session-id"] = self.session_id
            return response
        if method == "notifications/initialized":
            return httpx.Response(202)
        assert method == "tools/call"
        return rpc_response(payload["id"], self.result, sse=self.sse)

    @property
    def methods(self) -> list[str]:
        return [json.loads(request.content)["method"] for request in self.calls]

    @property
    def request_ids(self) -> list[int]:
        payloads = [json.loads(request.content) for request in self.calls]
        return [payload["id"] for payload in payloads if "id" in payload]


@pytest.fixture(autouse=True)
def no_dns(monkeypatch):
    # MockTransport does not intercept network_policy's synchronous DNS lookup.
    monkeypatch.setattr(module, "check_url", lambda url: None)


@pytest.fixture
async def make_provider():
    clients: list[httpx.AsyncClient] = []

    def make(handler, *, timeout_seconds: float = 15.0) -> ExaMcpSearchProvider:
        # Deliberately enable redirects here; the adapter must override this.
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)
        clients.append(client)
        return ExaMcpSearchProvider(client=client, timeout_seconds=timeout_seconds)

    yield make
    for client in clients:
        await client.aclose()


@pytest.mark.parametrize("sse,structured", [(False, False), (True, True)])
async def test_json_and_sse_become_ranked_hints_with_shared_timestamp(
    make_provider, sse, structured
):
    server = McpServer(result=tool_result(ROWS, structured=structured), sse=sse)
    response = await make_provider(server).search(query="bachelor computer science")

    assert [row.url for row in response.results] == [row["url"] for row in ROWS]
    assert [row.rank for row in response.results] == [1, 2]
    assert response.provider == "exa_mcp"
    assert all(row.provider == "exa_mcp" for row in response.results)
    assert all(row.retrieved_at == response.retrieved_at for row in response.results)
    assert response.retrieved_at.utcoffset().total_seconds() == 0
    assert response.results[0].snippet == "Programme information Application requirements"
    assert PRIVATE_MARKER not in repr(response)
    assert "REMOTE PAGE TEXT" not in repr(response)
    assert not {"value", "scope", "excerpt"} & set(type(response.results[0]).__dataclass_fields__)


async def test_protocol_session_and_query_use_only_the_fixed_keyless_endpoint(make_provider):
    server = McpServer()
    await make_provider(server).search(
        query="bsc cs", domains=[" .UNI.EDU. ", "", "admissions.other.edu"], max_results=4
    )

    assert server.methods == ["initialize", "notifications/initialized", "tools/call"]
    assert all(
        request.method == "POST" and str(request.url) == EXA_MCP_URL for request in server.calls
    )
    assert all("authorization" not in request.headers for request in server.calls)
    assert all("x-api-key" not in request.headers for request in server.calls)
    assert all(
        request.headers["mcp-protocol-version"] == PROTOCOL_VERSION for request in server.calls
    )
    assert "mcp-session-id" not in server.calls[0].headers
    assert [request.headers["mcp-session-id"] for request in server.calls[1:]] == [
        "mock-session",
        "mock-session",
    ]
    initialize = json.loads(server.calls[0].content)
    assert initialize["params"]["protocolVersion"] == PROTOCOL_VERSION
    notification = json.loads(server.calls[1].content)
    assert "id" not in notification
    call = json.loads(server.calls[2].content)
    assert call["params"]["name"] == "web_search_advanced_exa"
    arguments = call["params"]["arguments"]
    assert arguments["query"] == "bsc cs"
    assert arguments["includeDomains"] == ["uni.edu", "admissions.other.edu"]
    assert arguments["numResults"] == 4
    assert arguments["enableHighlights"] is True
    assert arguments["textMaxCharacters"] == 1


async def test_second_search_reuses_session_with_unique_increasing_request_ids(make_provider):
    server = McpServer(sse=True)
    provider = make_provider(server)
    first = await provider.search(query="first query")
    second = await provider.search(query="second query")

    assert first.query == "first query" and second.query == "second query"
    assert server.methods == ["initialize", "notifications/initialized", "tools/call", "tools/call"]
    assert server.request_ids == [1, 2, 3]
    assert server.calls[-1].headers["mcp-session-id"] == "mock-session"
    assert "includeDomains" not in json.loads(server.calls[-1].content)["params"]["arguments"]


@pytest.mark.parametrize("failed_method", ["initialize", "tools/call"])
async def test_explicit_new_search_after_failure_never_reuses_request_ids(
    make_provider, failed_method
):
    server = McpServer(
        overrides={failed_method: lambda request: httpx.Response(429, text=PRIVATE_MARKER)}
    )
    provider = make_provider(server)
    with pytest.raises(SearchUnavailable) as caught:
        await provider.search(query="first query")
    assert caught.value.http_status == 429
    # The failed call performs exactly one request at the failed stage.
    assert server.methods.count(failed_method) == 1
    assert server.methods == (
        ["initialize"]
        if failed_method == "initialize"
        else ["initialize", "notifications/initialized", "tools/call"]
    )

    del server.overrides[failed_method]
    response = await provider.search(query="explicit second query")
    assert response.query == "explicit second query"
    assert response.results
    assert server.request_ids == [1, 2, 3]
    assert server.methods == (
        ["initialize", "initialize", "notifications/initialized", "tools/call"]
        if failed_method == "initialize"
        else ["initialize", "notifications/initialized", "tools/call", "tools/call"]
    )


async def test_unsupported_protocol_stops_before_notification_or_query(make_provider):
    server = McpServer(
        overrides={
            "initialize": lambda request: rpc_response(
                json.loads(request.content)["id"], {"protocolVersion": "1999-01-01"}
            )
        }
    )
    with pytest.raises(SearchUnavailable, match="unsupported protocol"):
        await make_provider(server).search(query="q")
    assert server.methods == ["initialize"]


@pytest.mark.parametrize("status", [302, 400, 401, 402, 429, 500, 503])
async def test_http_failure_is_safe_and_never_retried_or_redirected(make_provider, status):
    server = McpServer(
        overrides={
            "tools/call": lambda request: httpx.Response(
                status,
                text=PRIVATE_MARKER,
                headers={"location": "https://private.invalid/"},
            )
        }
    )
    with pytest.raises(SearchUnavailable) as caught:
        await make_provider(server).search(query="q")
    assert caught.value.http_status == status
    assert PRIVATE_MARKER not in str(caught.value)
    assert search_failure_diagnostic("exa_mcp", caught.value) == (
        f"Search service unavailable (exa_mcp; HTTP {status})."
    )
    assert server.methods == ["initialize", "notifications/initialized", "tools/call"]
    assert all(str(request.url) == EXA_MCP_URL for request in server.calls)


async def test_initialization_http_failure_never_sends_search(make_provider):
    server = McpServer(
        overrides={"initialize": lambda request: httpx.Response(429, text=PRIVATE_MARKER)}
    )
    with pytest.raises(SearchUnavailable) as caught:
        await make_provider(server).search(query="q")
    assert caught.value.http_status == 429
    assert server.methods == ["initialize"]


async def test_initialized_notification_requires_accepted_status(make_provider):
    server = McpServer(overrides={"notifications/initialized": lambda request: httpx.Response(200)})
    with pytest.raises(SearchUnavailable) as caught:
        await make_provider(server).search(query="q")
    assert caught.value.http_status == 200
    assert server.methods == ["initialize", "notifications/initialized"]


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
async def test_transport_failure_has_no_vendor_text_or_retry(make_provider, method):
    def failed(request):
        raise httpx.ConnectError(PRIVATE_MARKER, request=request)

    server = McpServer(overrides={method: failed})
    with pytest.raises(SearchUnavailable, match="did not answer") as caught:
        await make_provider(server).search(query="q")
    assert PRIVATE_MARKER not in str(caught.value)
    assert search_failure_diagnostic("exa_mcp", caught.value) == (
        "Search service unavailable (exa_mcp)."
    )
    assert server.methods.count(method) == 1


@pytest.mark.parametrize(
    "body",
    [
        b"\xff",
        b"not JSON or SSE",
        b"data: {broken}\n\n",
        b"[]",
        b'{"jsonrpc":"2.0","id":999,"result":{}}',
        b'{"jsonrpc":"1.0","id":2,"result":{}}',
        b'{"jsonrpc":"2.0","id":2,"result":[]}',
        json.dumps({"jsonrpc": "2.0", "id": 2, "error": {"message": PRIVATE_MARKER}}).encode(),
    ],
)
async def test_malformed_or_rpc_failure_is_unavailable_not_empty(make_provider, body):
    server = McpServer(overrides={"tools/call": lambda request: httpx.Response(200, content=body)})
    with pytest.raises(SearchUnavailable) as caught:
        await make_provider(server).search(query="q")
    assert caught.value.http_status is None
    assert PRIVATE_MARKER not in str(caught.value)
    assert server.methods.count("tools/call") == 1


@pytest.mark.parametrize(
    "result",
    [
        {"isError": True, "content": [{"type": "text", "text": PRIVATE_MARKER}]},
        {"structuredContent": {"results": "not a list"}},
        {"content": [{"type": "text", "text": PRIVATE_MARKER}]},
        {"content": [{"type": "text", "text": "[]"}]},
        {"content": [{"type": "image", "text": '{"results":[]}'}]},
    ],
)
async def test_tool_errors_or_unreadable_results_are_not_legitimate_empty(make_provider, result):
    server = McpServer(result=result)
    with pytest.raises(SearchUnavailable) as caught:
        await make_provider(server).search(query="q")
    assert PRIVATE_MARKER not in str(caught.value)


@pytest.mark.parametrize("structured", [False, True])
async def test_explicit_empty_result_is_a_success(make_provider, structured):
    response = await make_provider(McpServer(result=tool_result([], structured=structured))).search(
        query="no matching official page"
    )
    assert response.results == ()
    assert response.provider == "exa_mcp"


async def test_domain_filter_rejects_lookalikes_and_bad_rows_without_losing_valid_rows(
    make_provider,
):
    rows = [
        None,
        "not an object",
        {"title": "missing URL"},
        {"url": 123},
        {"url": "javascript:alert(1)"},
        {"url": "/relative/path"},
        {"url": "https://[malformed/path"},
        {"url": "https://uni.edu.attacker.invalid/path"},
        {"url": "https://attackeruni.edu/path"},
        {"url": "https://user:password@uni.edu/path"},
        {"url": "https://:password@uni.edu/path"},
        {"url": "https://uni.edu/path", "title": "Official"},
        {"url": "https://ADMISSIONS.UNI.EDU/path", "title": 123, "highlights": "not a list"},
    ]
    response = await make_provider(McpServer(result=tool_result(rows))).search(
        query="q", domains=["UNI.EDU"]
    )
    assert [row.url for row in response.results] == [
        "https://uni.edu/path",
        "https://ADMISSIONS.UNI.EDU/path",
    ]
    assert [row.rank for row in response.results] == [1, 2]
    assert response.results[1].title == "" and response.results[1].snippet == ""


async def test_valid_result_count_title_and_highlights_are_bounded(make_provider):
    rows = [
        {
            "url": f"https://uni.edu/{index}",
            "title": "t" * 500,
            "highlights": ["h" * 1500, None, 42, "tail"],
            "text": PRIVATE_MARKER,
        }
        for index in range(MAX_RESULTS_PER_QUERY + 10)
    ]
    server = McpServer(result=tool_result(rows))
    response = await make_provider(server).search(query="q", max_results=1000)
    assert len(response.results) == MAX_RESULTS_PER_QUERY
    assert [row.rank for row in response.results] == list(range(1, MAX_RESULTS_PER_QUERY + 1))
    assert all(len(row.title) == 300 and len(row.snippet) == 1000 for row in response.results)
    assert PRIVATE_MARKER not in repr(response)
    assert json.loads(server.calls[-1].content)["params"]["arguments"]["numResults"] == (
        MAX_RESULTS_PER_QUERY
    )


async def test_caller_limit_applies_after_invalid_rows_are_filtered(make_provider):
    rows = [{"url": "invalid"}, *ROWS, {"url": "https://uni.edu/third"}]
    response = await make_provider(McpServer(result=tool_result(rows))).search(
        query="q", max_results=1
    )
    assert [row.url for row in response.results] == [ROWS[0]["url"]]


async def test_blocked_endpoint_never_reaches_transport(make_provider, monkeypatch):
    checked: list[str] = []

    def blocked(url):
        checked.append(url)
        raise BlockedRequest(PRIVATE_MARKER)

    monkeypatch.setattr(module, "check_url", blocked)
    server = McpServer()
    with pytest.raises(SearchUnavailable, match="network policy") as caught:
        await make_provider(server).search(query="q")
    assert checked == [EXA_MCP_URL]
    assert server.calls == []
    assert PRIVATE_MARKER not in str(caught.value)


async def test_timeout_bounds_the_entire_handshake_not_each_post(make_provider):
    calls: list[str] = []
    server = McpServer()

    async def delayed(request):
        calls.append(json.loads(request.content)["method"])
        # Each individual post fits the timeout; their combined duration does not.
        await asyncio.sleep(0.03)
        return server(request)

    with pytest.raises(SearchUnavailable, match="did not answer"):
        await make_provider(delayed, timeout_seconds=0.05).search(query="q")
    assert calls == ["initialize", "notifications/initialized"]


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.reads = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in [b"x" * MAX_RESPONSE_BYTES, b"y", b"never consumed"]:
            self.reads += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("method", ["initialize", "tools/call"])
async def test_streamed_byte_limit_stops_reading_and_closes_response(make_provider, method):
    stream = ChunkStream()
    server = McpServer(overrides={method: lambda request: httpx.Response(200, stream=stream)})
    with pytest.raises(SearchUnavailable, match="byte limit"):
        await make_provider(server).search(query="q")
    assert stream.reads == 2
    assert stream.closed is True
    assert server.methods.count(method) == 1


@pytest.mark.parametrize("query,max_results", [("  ", 10), ("q", 0), ("q", -1)])
async def test_invalid_arguments_fail_before_egress(make_provider, monkeypatch, query, max_results):
    checked: list[str] = []
    monkeypatch.setattr(module, "check_url", checked.append)
    server = McpServer()
    with pytest.raises(ValueError):
        await make_provider(server).search(query=query, max_results=max_results)
    assert checked == [] and server.calls == []


def test_configuration_and_factory_allow_keyless_mcp_in_production(monkeypatch):
    from app.adapters.search import KNOWN_SEARCH_PROVIDERS, get_search_provider
    from app.config import get_settings

    settings = Settings(
        _env_file=None,
        search_provider="exa_mcp",
        environment="production",
        auth_enabled=True,
        cookie_secure=True,
        database_url="postgresql+psycopg://user:password@db.example/ashyq",
        cors_origins="https://apply.example",
        public_base_url="https://apply.example",
        email_sender="smtp",
        smtp_host="smtp.example",
        smtp_from="no-reply@example.test",
        metrics_enabled=False,
        payments_enabled=False,
    )
    settings.validate_runtime()
    assert "exa_mcp" in KNOWN_SEARCH_PROVIDERS
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    assert isinstance(get_search_provider(), ExaMcpSearchProvider)
    get_settings.cache_clear()
