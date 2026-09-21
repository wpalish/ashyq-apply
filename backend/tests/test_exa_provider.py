"""V2-10b — the Exa adapter.

No test here touches the network: every call goes through a mock transport,
as AGENTS.md §6 requires. What is tested is mostly what the adapter refuses to
do — retry a quota error, trust an oversized body, or let a highlight escape
into anything that could cite it.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.search.base import SearchUnavailable
from app.adapters.search.exa import (
    EXA_SEARCH_URL,
    MAX_RESPONSE_BYTES,
    MAX_RESULTS_PER_QUERY,
    ExaSearchProvider,
)
from app.config import Settings

A_BODY = {
    "results": [
        {
            "url": "https://nu.edu.kz/programmes/bsc-computer-science",
            "title": "BSc Computer Science",
            "highlights": ["Entry requirements for 2027", "Four-year programme"],
        },
        {"url": "https://nu.edu.kz/programmes/cs-faq", "title": "FAQ", "highlights": []},
    ]
}


def provider(handler, **kw) -> ExaSearchProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ExaSearchProvider("test-key-not-a-real-one", client=client, **kw)


def ok(body=None):
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=body if body is not None else A_BODY)

    handler.calls = calls  # type: ignore[attr-defined]
    return handler


class TestTheHappyPath:
    async def test_results_become_ranked_search_results(self):
        response = await provider(ok()).search(query="bsc computer science")

        assert [r.url for r in response.results] == [
            "https://nu.edu.kz/programmes/bsc-computer-science",
            "https://nu.edu.kz/programmes/cs-faq",
        ]
        assert [r.rank for r in response.results] == [1, 2]
        assert all(r.provider == "exa" for r in response.results)
        assert response.provider == "exa"

    async def test_highlights_land_in_the_snippet_and_nowhere_else(self):
        """A highlight is a hint. Nothing may cite one, so it has one home."""
        response = await provider(ok()).search(query="q")

        first = response.results[0]
        assert "Entry requirements for 2027" in first.snippet
        assert not {"value", "scope", "excerpt"} & set(type(first).__dataclass_fields__)

    async def test_the_request_carries_the_key_the_query_and_the_domain_filter(self):
        handler = ok()

        await provider(handler).search(query="bsc cs", domains=["nu.edu.kz"], max_results=5)

        request = handler.calls[0]
        payload = json.loads(request.content)
        assert str(request.url) == EXA_SEARCH_URL
        assert request.headers["x-api-key"] == "test-key-not-a-real-one"
        assert payload["query"] == "bsc cs"
        assert payload["includeDomains"] == ["nu.edu.kz"]
        assert payload["numResults"] == 5
        assert payload["contents"] == {"highlights": True}

    async def test_no_domain_filter_is_sent_when_none_was_asked_for(self):
        handler = ok()

        await provider(handler).search(query="q")

        assert "includeDomains" not in json.loads(handler.calls[0].content)

    async def test_the_search_type_is_configurable_and_defaults_to_auto(self):
        handler = ok()
        await provider(handler).search(query="q")
        assert json.loads(handler.calls[0].content)["type"] == "auto"

        handler = ok()
        await provider(handler, search_type="fast").search(query="q")
        assert json.loads(handler.calls[0].content)["type"] == "fast"


class TestItFailsClosedAndVisibly:
    @pytest.mark.parametrize("status", [401, 402, 429, 500, 503])
    async def test_every_error_status_becomes_search_unavailable(self, status):
        def handler(request):
            return httpx.Response(status, json={"error": "nope"})

        with pytest.raises(SearchUnavailable, match=str(status)):
            await provider(handler).search(query="q")

    async def test_a_transport_failure_becomes_search_unavailable(self):
        def handler(request):
            raise httpx.ConnectError("no route to host")

        with pytest.raises(SearchUnavailable, match="did not answer"):
            await provider(handler).search(query="q")

    async def test_a_quota_error_is_not_retried(self):
        """Three 429s cost three times as much and tell us the same thing."""
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(429, json={"error": "quota"})

        with pytest.raises(SearchUnavailable):
            await provider(handler).search(query="q")

        assert len(calls) == 1

    async def test_the_providers_own_error_text_is_not_echoed(self):
        """External text does not belong in an exception a user might see."""

        def handler(request):
            return httpx.Response(400, json={"error": "<script>alert(1)</script>"})

        with pytest.raises(SearchUnavailable) as caught:
            await provider(handler).search(query="q")

        assert "script" not in str(caught.value)

    async def test_an_unreadable_body_becomes_search_unavailable(self):
        def handler(request):
            return httpx.Response(200, content=b"not json at all")

        with pytest.raises(SearchUnavailable, match="cannot read"):
            await provider(handler).search(query="q")

    async def test_a_body_without_results_becomes_search_unavailable(self):
        def handler(request):
            return httpx.Response(200, json={"output": {"content": "synthesised prose"}})

        with pytest.raises(SearchUnavailable, match="cannot read"):
            await provider(handler).search(query="q")

    async def test_an_oversized_body_is_refused(self):
        def handler(request):
            return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))

        with pytest.raises(SearchUnavailable, match="cap"):
            await provider(handler).search(query="q")

    async def test_one_malformed_row_does_not_lose_the_others(self):
        body = {"results": [{"title": "no url here"}, A_BODY["results"][0]]}

        response = await provider(ok(body)).search(query="q")

        assert len(response.results) == 1
        assert response.results[0].rank == 1


class TestItsOwnLimits:
    async def test_the_per_query_result_count_is_capped(self):
        """Cost is per result, so a caller cannot ask for a thousand."""
        handler = ok()

        await provider(handler).search(query="q", max_results=1000)

        assert json.loads(handler.calls[0].content)["numResults"] == MAX_RESULTS_PER_QUERY

    async def test_an_empty_query_is_refused_before_any_request(self):
        handler = ok()

        with pytest.raises(ValueError, match="needs a query"):
            await provider(handler).search(query="  ")

        assert handler.calls == []

    async def test_max_results_below_one_is_refused(self):
        with pytest.raises(ValueError, match="max_results"):
            await provider(ok()).search(query="q", max_results=0)

    def test_it_refuses_to_be_built_without_a_key(self):
        with pytest.raises(ValueError, match="needs an API key"):
            ExaSearchProvider("")


class TestConfiguration:
    def test_selecting_exa_without_a_key_refuses_to_start(self):
        """Better than reporting every search as finding nothing."""
        settings = Settings(search_provider="exa")

        with pytest.raises(RuntimeError, match="UNIMATCH_EXA_API_KEY"):
            settings.validate_runtime()

    def test_the_key_is_a_secret_and_does_not_render_itself(self):
        settings = Settings(search_provider="exa", exa_api_key="super-secret")

        assert "super-secret" not in repr(settings)
        assert settings.exa_api_key.get_secret_value() == "super-secret"

    def test_exa_is_a_known_provider_and_none_is_still_the_default(self):
        from app.adapters.search import KNOWN_SEARCH_PROVIDERS

        assert "exa" in KNOWN_SEARCH_PROVIDERS
        assert Settings().search_provider == "none"

    def test_the_factory_builds_it_from_configuration(self, monkeypatch):
        from app.adapters.search import get_search_provider
        from app.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa")
        monkeypatch.setenv("UNIMATCH_EXA_API_KEY", "k")
        try:
            assert isinstance(get_search_provider(), ExaSearchProvider)
        finally:
            get_settings.cache_clear()


class TestTheEgressPolicyAndClientLifecycle:
    async def test_a_blocked_endpoint_never_becomes_a_request(self, monkeypatch):
        """The host is fixed today; this guards a future change of endpoint."""
        import app.adapters.search.exa as module
        from app.adapters.network_policy import BlockedRequest

        def blocked(url):
            raise BlockedRequest("resolves to a private address")

        monkeypatch.setattr(module, "check_url", blocked)
        handler = ok()

        with pytest.raises(SearchUnavailable, match="not reachable under policy"):
            await provider(handler).search(query="q")

        assert handler.calls == []

    async def test_it_builds_and_closes_its_own_client_when_given_none(self, monkeypatch):
        """The ordinary path: nothing injects a client in production."""
        import app.adapters.search.exa as module

        closed: list[bool] = []
        calls: list[httpx.Request] = []

        class RecordingClient(httpx.AsyncClient):
            async def post(self, *args, **kwargs):  # type: ignore[override]
                calls.append(args)
                return httpx.Response(
                    200, json=A_BODY, request=httpx.Request("POST", EXA_SEARCH_URL)
                )

            async def aclose(self) -> None:
                closed.append(True)

        monkeypatch.setattr(module.httpx, "AsyncClient", RecordingClient)

        response = await ExaSearchProvider("k").search(query="q")

        assert len(response.results) == 2
        assert calls and closed == [True]
