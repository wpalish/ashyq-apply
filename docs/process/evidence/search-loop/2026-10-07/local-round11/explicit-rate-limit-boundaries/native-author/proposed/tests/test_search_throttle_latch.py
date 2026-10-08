"""One HTTP 429 stops every caller in the process, without another request.

V6b (2026-10-04): the keyless Exa MCP endpoint answered 429 and discovery, the
scholarship fallback and the catalogue identity check kept sending, each from
its own adapter instance, and the run reported planned queries as sent.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from app.adapters.search import (
    THROTTLE_COOLDOWN_SECONDS,
    SearchResponse,
    SearchUnavailable,
    _ThrottleLatch,
    reset_search_throttle,
)
from app.adapters.search.base import SearchFailureReason


class Refusing:
    name = "exa_mcp"

    def __init__(self, status: int | None = 429, reason: SearchFailureReason | None = None) -> None:
        self.calls = 0
        self.status = status
        self.error = SearchUnavailable("refused", http_status=status, reason=reason)

    async def search(self, *, query, domains=(), max_results=10):
        self.calls += 1
        raise self.error


class Answering:
    name = "exa_mcp"

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, *, query, domains=(), max_results=10):
        self.calls += 1
        return SearchResponse(query=query, provider=self.name, retrieved_at=datetime.now(UTC))


@pytest.mark.asyncio
async def test_a_429_is_shared_by_a_second_adapter_instance():
    first, second = Refusing(), Answering()
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(first).search(query="q")
    with pytest.raises(SearchUnavailable) as stopped:
        await _ThrottleLatch(second).search(query="q")
    assert stopped.value.http_status == 429
    assert second.calls == 0


@pytest.mark.asyncio
async def test_other_failures_do_not_latch():
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(status=500)).search(query="q")
    answering = Answering()
    await _ThrottleLatch(answering).search(query="q")
    assert answering.calls == 1


@pytest.mark.asyncio
async def test_the_latch_is_per_provider_and_expires(monkeypatch):
    import app.adapters.search as search

    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing()).search(query="q")
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
    assert getattr(search, "_THROTTLED_ORIGIN", {}) == {}


async def test_typed_status_none_is_shared_without_status_or_message_invention():
    first, second = Refusing(None, SearchFailureReason.RATE_LIMITED), Answering()
    with pytest.raises(SearchUnavailable) as initial:
        await _ThrottleLatch(first).search(query="first")
    assert initial.value is first.error
    with pytest.raises(SearchUnavailable) as local:
        await _ThrottleLatch(second).search(query="other adapter")
    assert first.calls == 1 and second.calls == 0
    assert local.value.http_status is None
    assert local.value.reason is SearchFailureReason.RATE_LIMITED
    assert "429" not in str(local.value)
    assert "quota" not in str(local.value)
    assert "request was not sent" in str(local.value)


@pytest.mark.parametrize("reason", [None, "rate limited"])
async def test_vendor_text_and_untyped_reason_do_not_latch(reason):
    import app.adapters.search as search

    # RATE_LIMITED is a StrEnum: equality to this string is true; identity is not.
    first = Refusing(None, cast(SearchFailureReason | None, reason))
    first.error = SearchUnavailable(
        "rate limited vendor text", reason=cast(SearchFailureReason | None, reason)
    )
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(first).search(query="first")
    second = Answering()
    await _ThrottleLatch(second).search(query="second")
    assert second.calls == 1
    assert search._THROTTLED_UNTIL == {}
    assert getattr(search, "_THROTTLED_ORIGIN", {}) == {}


async def test_typed_origin_uses_one_deadline_with_a_ticking_clock(monkeypatch):
    import app.adapters.search as search

    ticks = iter((100.0, 101.0, 102.0))
    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    assert search._THROTTLED_UNTIL["exa_mcp"] == 101.0 + THROTTLE_COOLDOWN_SECONDS
    origin = getattr(search, "_THROTTLED_ORIGIN", {})
    assert origin["exa_mcp"] == (
        search._THROTTLED_UNTIL["exa_mcp"],
        None,
        SearchFailureReason.RATE_LIMITED,
    )
    next_provider = Answering()
    with pytest.raises(SearchUnavailable) as local:
        await _ThrottleLatch(next_provider).search(query="later")
    assert next_provider.calls == 0
    assert local.value.http_status is None
    assert local.value.reason is SearchFailureReason.RATE_LIMITED


async def test_exact_typed_cooldown_expiry_and_provider_isolation(monkeypatch):
    import app.adapters.search as search

    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=lambda: clock.now))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    other = Answering()
    other.name = "tavily"
    await _ThrottleLatch(other).search(query="different provider")
    assert other.calls == 1
    deadline = search._THROTTLED_UNTIL["exa_mcp"]
    clock.now = deadline - 0.001
    before = Answering()
    with pytest.raises(SearchUnavailable) as local:
        await _ThrottleLatch(before).search(query="before expiry")
    assert before.calls == 0 and local.value.http_status is None
    clock.now = deadline
    after = Answering()
    await _ThrottleLatch(after).search(query="exact expiry")
    assert after.calls == 1


async def test_stale_origin_does_not_relabel_a_deliberately_injected_legacy_float(monkeypatch):
    import app.adapters.search as search

    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=lambda: 100.0))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    origin = getattr(search, "_THROTTLED_ORIGIN", {})
    assert origin["exa_mcp"] == (400.0, None, SearchFailureReason.RATE_LIMITED)
    # Only a test/operator legacy float injection changes the recorded deadline.
    # This is not evidence that current metadata None should become HTTP429.
    search._THROTTLED_UNTIL["exa_mcp"] = 900.0
    other = Answering()
    with pytest.raises(SearchUnavailable) as legacy:
        await _ThrottleLatch(other).search(query="legacy injected state")
    assert other.calls == 0
    assert legacy.value.http_status == 429 and legacy.value.reason is None
    assert origin["exa_mcp"] == (400.0, None, SearchFailureReason.RATE_LIMITED)


async def test_reset_clears_actual_typed_origin_before_a_new_query():
    import app.adapters.search as search

    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    assert search._THROTTLED_UNTIL
    assert getattr(search, "_THROTTLED_ORIGIN", {})
    reset_search_throttle()
    assert search._THROTTLED_UNTIL == {}
    assert search._THROTTLED_ORIGIN == {}
    answering = Answering()
    await _ThrottleLatch(answering).search(query="after deliberate reset")
    assert answering.calls == 1
