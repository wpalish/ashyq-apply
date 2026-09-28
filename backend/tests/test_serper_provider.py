"""The Serper adapter: same contract as Exa and Tavily, no network (mock transport)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.search.base import SearchUnavailable
from app.adapters.search.serper import (
    MAX_RESPONSE_BYTES,
    MAX_RESULTS_PER_QUERY,
    SERPER_SEARCH_URL,
    SerperSearchProvider,
)
from app.config import Settings

A_BODY = {
    "organic": [
        {"link": "https://uni.edu/bachelors/cs", "title": "BSc CS", "snippet": "Entry 2027"},
        {"link": "", "title": "no url"},
        "not a row",
        {"link": "https://uni.edu/faq", "title": "FAQ"},
    ]
}


def provider(handler) -> SerperSearchProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SerperSearchProvider("test-key-not-a-real-one", client=client)


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
    assert response.provider == "serper"


async def test_the_request_carries_key_site_filter_and_a_capped_count():
    handler = answering()
    await provider(handler).search(query="bsc cs", domains=["uni.edu"], max_results=99)
    request = handler.calls[0]
    payload = json.loads(request.content)
    assert str(request.url) == SERPER_SEARCH_URL
    assert request.method == "POST"
    assert request.headers["x-api-key"] == "test-key-not-a-real-one"
    assert payload["q"] == "bsc cs site:uni.edu"
    assert payload["num"] == MAX_RESULTS_PER_QUERY


async def test_several_domains_are_one_or_group():
    handler = answering()
    await provider(handler).search(query="cs", domains=["a.edu", "b.edu"])
    assert json.loads(handler.calls[0].content)["q"] == "cs (site:a.edu OR site:b.edu)"


async def test_no_organic_block_means_no_results():
    response = await provider(answering(body={"searchParameters": {}})).search(query="q")
    assert response.results == ()


@pytest.mark.parametrize("status", [401, 402, 422, 429, 500])
async def test_any_non_200_is_unavailable_without_retry(status):
    handler = answering(status=status, body={"error": "no"})
    with pytest.raises(SearchUnavailable, match=str(status)):
        await provider(handler).search(query="q")
    assert len(handler.calls) == 1


async def test_an_unreadable_or_oversized_body_is_unavailable():
    with pytest.raises(SearchUnavailable, match="cannot read"):
        await provider(answering(body={"organic": "x"})).search(query="q")
    with pytest.raises(SearchUnavailable, match="cannot read"):
        await provider(answering(body=["not", "a", "map"])).search(query="q")
    with pytest.raises(SearchUnavailable, match="cap"):
        await provider(answering(raw=b"x" * (MAX_RESPONSE_BYTES + 1))).search(query="q")


async def test_a_transport_error_is_unavailable():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(SearchUnavailable, match="did not answer"):
        await provider(boom).search(query="q")


async def test_arguments_and_key_are_validated():
    with pytest.raises(ValueError):
        SerperSearchProvider("")
    with pytest.raises(ValueError):
        await provider(answering()).search(query="  ")
    with pytest.raises(ValueError):
        await provider(answering()).search(query="q", max_results=0)


def test_settings_refuse_serper_without_a_key():
    settings = Settings(search_provider="serper")
    with pytest.raises(RuntimeError, match="UNIMATCH_SERPER_API_KEY"):
        settings.validate_runtime()
    assert "k-secret" not in repr(Settings(search_provider="serper", serper_api_key="k-secret"))


def test_the_factory_builds_serper(monkeypatch):
    from app.adapters.search import get_search_provider
    from app.config import get_settings

    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("UNIMATCH_SERPER_API_KEY", "k-test")
    get_settings.cache_clear()
    try:
        assert get_search_provider().name == "serper"
    finally:
        get_settings.cache_clear()
