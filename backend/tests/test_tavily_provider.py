"""The Tavily adapter: same contract as Exa, no network (mock transport)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.search.base import SearchUnavailable
from app.adapters.search.tavily import (
    MAX_RESPONSE_BYTES,
    MAX_RESULTS_PER_QUERY,
    TAVILY_SEARCH_URL,
    TavilySearchProvider,
)
from app.config import Settings

A_BODY = {
    "results": [
        {"url": "https://uni.edu/bachelors/cs", "title": "BSc CS", "content": "Entry 2027"},
        {"url": "", "title": "no url"},
        "not a row",
        {"url": "https://uni.edu/faq", "title": "FAQ"},
    ]
}


def provider(handler) -> TavilySearchProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TavilySearchProvider("test-key-not-a-real-one", client=client)


def answering(status: int = 200, body: object = A_BODY, raw: bytes | None = None):
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if raw is not None:
            return httpx.Response(status, content=raw)
        return httpx.Response(status, json=body)

    handler.calls = calls  # type: ignore[attr-defined]
    return handler


async def test_results_become_ranked_hints_and_bad_rows_are_dropped():
    response = await provider(answering()).search(query="bsc cs")
    assert [r.url for r in response.results] == [
        "https://uni.edu/bachelors/cs",
        "https://uni.edu/faq",
    ]
    assert [r.rank for r in response.results] == [1, 2]
    assert response.results[0].snippet == "Entry 2027"
    assert response.provider == "tavily"


async def test_the_request_carries_key_query_domains_and_a_capped_count():
    handler = answering()
    await provider(handler).search(query="bsc cs", domains=["uni.edu"], max_results=99)
    request = handler.calls[0]
    payload = json.loads(request.content)
    assert str(request.url) == TAVILY_SEARCH_URL
    assert request.headers["authorization"] == "Bearer test-key-not-a-real-one"
    assert payload["include_domains"] == ["uni.edu"]
    assert payload["max_results"] == MAX_RESULTS_PER_QUERY


@pytest.mark.parametrize("status", [401, 402, 429, 500])
async def test_any_non_200_is_unavailable_without_retry(status):
    handler = answering(status=status, body={"detail": "no"})
    with pytest.raises(SearchUnavailable, match=str(status)):
        await provider(handler).search(query="q")
    assert len(handler.calls) == 1


async def test_an_unreadable_or_oversized_body_is_unavailable():
    with pytest.raises(SearchUnavailable, match="cannot read"):
        await provider(answering(body={"answer": "x"})).search(query="q")
    with pytest.raises(SearchUnavailable, match="cannot read"):
        await provider(answering(body={"results": "x"})).search(query="q")
    with pytest.raises(SearchUnavailable, match="cap"):
        await provider(answering(raw=b"x" * (MAX_RESPONSE_BYTES + 1))).search(query="q")


async def test_a_transport_error_is_unavailable():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(SearchUnavailable, match="did not answer"):
        await provider(boom).search(query="q")


async def test_arguments_and_key_are_validated():
    with pytest.raises(ValueError):
        TavilySearchProvider("")
    with pytest.raises(ValueError):
        await provider(answering()).search(query="  ")
    with pytest.raises(ValueError):
        await provider(answering()).search(query="q", max_results=0)


def test_settings_refuse_tavily_without_a_key():
    settings = Settings(search_provider="tavily")
    with pytest.raises(RuntimeError, match="UNIMATCH_TAVILY_API_KEY"):
        settings.validate_runtime()
    assert "k-secret" not in repr(Settings(search_provider="tavily", tavily_api_key="k-secret"))
