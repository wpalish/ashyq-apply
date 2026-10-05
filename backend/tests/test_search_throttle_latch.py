"""One HTTP 429 stops every caller in the process, without another request.

V6b (2026-10-04): the keyless Exa MCP endpoint answered 429 and discovery, the
scholarship fallback and the catalogue identity check kept sending, each from
its own adapter instance, and the run reported planned queries as sent.
"""

from datetime import UTC, datetime

import pytest

from app.adapters.search import (
    THROTTLE_COOLDOWN_SECONDS,
    SearchResponse,
    SearchUnavailable,
    _ThrottleLatch,
    reset_search_throttle,
)


class Refusing:
    name = "exa_mcp"

    def __init__(self, status: int | None = 429) -> None:
        self.calls = 0
        self.status = status

    async def search(self, *, query, domains=(), max_results=10):
        self.calls += 1
        raise SearchUnavailable("refused", http_status=self.status)


class Answering:
    name = "exa_mcp"

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, *, query, domains=(), max_results=10):
        self.calls += 1
        return SearchResponse(query=query, provider=self.name, retrieved_at=datetime.now(UTC))


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [402, 429])
async def test_account_refusal_is_shared_by_a_second_adapter_instance(status):
    first, second = Refusing(status=status), Answering()
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(first).search(query="q")
    with pytest.raises(SearchUnavailable) as stopped:
        await _ThrottleLatch(second).search(query="q")
    assert stopped.value.http_status == status
    assert second.calls == 0


@pytest.mark.asyncio
async def test_other_failures_do_not_latch():
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(status=500)).search(query="q")
    answering = Answering()
    await _ThrottleLatch(answering).search(query="q")
    assert answering.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [402, 429])
async def test_the_latch_is_per_provider_and_expires(monkeypatch, status):
    import app.adapters.search as search

    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(status=status)).search(query="q")
    other = Answering()
    other.name = "tavily"
    await _ThrottleLatch(other).search(query="q")
    assert other.calls == 1

    later = search.time.monotonic() + THROTTLE_COOLDOWN_SECONDS + 1
    monkeypatch.setattr(search.time, "monotonic", lambda: later)
    again = Answering()
    await _ThrottleLatch(again).search(query="q")
    assert again.calls == 1


def test_reset_forgets_the_refusal():
    import app.adapters.search as search

    search._THROTTLED_UNTIL["exa_mcp"] = search.time.monotonic() + 999
    reset_search_throttle()
    assert search._THROTTLED_UNTIL == {}
