"""The Brave adapter: same contract as Exa and Tavily, no network (mock transport)."""

from __future__ import annotations

import httpx
import pytest

from app.adapters.search.base import SearchUnavailable
from app.adapters.search.brave import (
    BRAVE_SEARCH_URL,
    MAX_RESPONSE_BYTES,
    MAX_RESULTS_PER_QUERY,
    BraveSearchProvider,
)
from app.config import Settings

A_BODY = {
    "web": {
        "results": [
            {"url": "https://uni.edu/bachelors/cs", "title": "BSc CS", "description": "Entry 2027"},
            {"url": "", "title": "no url"},
            "not a row",
            {"url": "https://uni.edu/faq", "title": "FAQ"},
        ]
    }
}


def provider(handler) -> BraveSearchProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return BraveSearchProvider("test-key-not-a-real-one", client=client)


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
    assert response.provider == "brave"


async def test_the_request_carries_key_site_filter_and_a_capped_count():
    handler = answering()
    await provider(handler).search(query="bsc cs", domains=["uni.edu"], max_results=99)
    request = handler.calls[0]
    assert str(request.url).startswith(BRAVE_SEARCH_URL)
    assert request.method == "GET"
    assert request.headers["x-subscription-token"] == "test-key-not-a-real-one"
    assert request.url.params["q"] == "bsc cs site:uni.edu"
    assert request.url.params["count"] == str(MAX_RESULTS_PER_QUERY)


async def test_several_domains_are_one_or_group():
    handler = answering()
    await provider(handler).search(query="cs", domains=["a.edu", "b.edu"])
    assert handler.calls[0].url.params["q"] == "cs (site:a.edu OR site:b.edu)"


async def test_no_web_block_means_no_results():
    response = await provider(answering(body={"query": {}})).search(query="q")
    assert response.results == ()


@pytest.mark.parametrize("status", [401, 402, 422, 429, 500])
async def test_any_non_200_is_unavailable_without_retry(status):
    handler = answering(status=status, body={"error": "no"})
    with pytest.raises(SearchUnavailable, match=str(status)):
        await provider(handler).search(query="q")
    assert len(handler.calls) == 1


async def test_an_unreadable_or_oversized_body_is_unavailable():
    with pytest.raises(SearchUnavailable, match="cannot read"):
        await provider(answering(body={"web": {"results": "x"}})).search(query="q")
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
        BraveSearchProvider("")
    with pytest.raises(ValueError):
        await provider(answering()).search(query="  ")
    with pytest.raises(ValueError):
        await provider(answering()).search(query="q", max_results=0)


def test_settings_refuse_brave_without_a_key():
    settings = Settings(search_provider="brave")
    with pytest.raises(RuntimeError, match="UNIMATCH_BRAVE_API_KEY"):
        settings.validate_runtime()
    assert "k-secret" not in repr(Settings(search_provider="brave", brave_api_key="k-secret"))


def test_the_factory_builds_brave(monkeypatch):
    from app.adapters.search import get_search_provider
    from app.config import get_settings

    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "brave")
    monkeypatch.setenv("UNIMATCH_BRAVE_API_KEY", "k-test")
    get_settings.cache_clear()
    try:
        assert get_search_provider().name == "brave"
    finally:
        get_settings.cache_clear()
