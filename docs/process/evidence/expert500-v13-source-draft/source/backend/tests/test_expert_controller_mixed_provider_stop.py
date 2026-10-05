"""Offline mixed-provider STOP regressions for the actual controller.

All source callbacks and clocks are synthetic. No provider or Fetcher
instance is constructed, and the imported controller is never replaced.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.adapters.fetching import FetchResult
from app.adapters.search.base import SearchUnavailable
from app.domain.enums import FetchOutcome
from evaluation.research.expert.controller import execute
from evaluation.research.expert.network_budget import BUDGET_MODEL, NETWORK_COMPARISON_MODE

START = datetime(2026, 10, 1, tzinfo=UTC)
URL = "https://u.edu/synthetic"
QUERY = {"tool": "search_provider", "query": "synthetic official programme"}
MODES = ("strict_120", "network_900", "network_diagnostic", "legacy")


@dataclass
class _Clock:
    wall: datetime = START
    mono: float = 0.0

    def advance(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


def _plan(mode: str, **changes: Any) -> dict[str, Any]:
    value = {
        "case_id": "synthetic_mixed",
        "provider": "exa",
        "log_prefix": "mixed",
        "strict_budget": mode != "legacy",
        "official_domains": ["u.edu"],
        "max_calls": 60,
        "max_search_queries": 6,
        "max_ms": 120_000,
        "budget_origin": "independent_full_budget",
    }
    if mode.startswith("network"):
        value.update(
            budget_origin=NETWORK_COMPARISON_MODE,
            budget_model=BUDGET_MODEL,
            max_ms=900_000,
            wall_started_at=START.isoformat(),
            wall_deadline_at=(START + timedelta(seconds=900)).isoformat(),
        )
    if mode == "network_diagnostic":
        value["exploration_mode"] = "outside_policy"
    return {**value, **changes}


def _page(url: str, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url,
        final_url=url,
        outcome=FetchOutcome.OK if status == 200 else FetchOutcome.HTTP_ERROR,
        status_code=status,
        content_type="text/html",
        content=b"<p>Synthetic public source.</p>" if status == 200 else b"",
        error="" if status == 200 else "Synthetic university HTTP error.",
    )


def _execute(
    folder: Path,
    plan: dict[str, Any],
    clock: _Clock,
    *,
    get: Any,
    search: Any,
) -> dict[str, Any]:
    return asyncio.run(
        execute(
            plan,
            folder,
            get=get,
            search=search,
            provider_name="exa",
            now=lambda: clock.wall,
            monotonic=lambda: clock.mono,
        )
    )


def _record(folder: Path, entry: dict[str, Any]) -> dict[str, Any]:
    data = (folder / entry["raw_log_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["raw_log_sha256"]
    return json.loads(data)


def _assert_stopped(
    folder: Path, entries: list[dict[str, Any]], status: int, elapsed_ms: int
) -> None:
    for entry in entries:
        record = _record(folder, entry)
        assert entry["outcome"] == record["outcome"] == f"stopped_after_http_{status}"
        assert entry["outcome_status"] == record["outcome_status"] == "blocked"
        assert entry["executed"] is record["executed"] is False
        assert "response" not in record
        assert record["elapsed_ms"] == record["charged_elapsed_ms"] == 0
        assert record["elapsed_ms_before"] == record["elapsed_ms_cumulative"] == elapsed_ms
        assert record["fetcher_calls_cumulative"] == 0
        assert record["search_queries_cumulative"] == 1
        assert record["stop_reason"] == f"http_{status}"
        assert record["policy_mode"] == "outside_policy"
        if "dispatch_at" in record:
            assert record["dispatch_at"] is None


@pytest.mark.parametrize("status", [402, 429])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("split_replay", [False, True])
def test_provider_stop_prevents_every_following_source_tool(
    tmp_path: Path,
    status: int,
    mode: str,
    split_replay: bool,
) -> None:
    clock = _Clock()
    get_calls: list[str] = []
    search_calls: list[int] = []

    async def get(url: str) -> FetchResult:
        get_calls.append(url)
        clock.advance(0.125)
        return _page(url)

    async def search(**kwargs: Any) -> Any:
        search_calls.append(len(search_calls) + 1)
        clock.advance(0.25)
        # A later vendor refusal must never replace the first original cause.
        later_status = 429 if status == 402 else 402
        raise SearchUnavailable(
            "Synthetic provider account refusal.",
            http_status=status if len(search_calls) == 1 else later_status,
        )

    later = [URL, dict(QUERY), {"tool": "fetcher", "url": URL}]
    plan = (
        _plan(mode, actions=later, replay=[dict(QUERY)])
        if split_replay
        else _plan(mode, actions=[dict(QUERY), *later])
    )
    logs = tmp_path / "logs"
    summary = _execute(logs, plan, clock, get=get, search=search)
    assert get_calls == []
    assert search_calls == [1]
    first = summary["replay"][0] if split_replay else summary["actions"][0]
    original = _record(logs, first)
    assert original["response"]["http_status"] == original["response"]["status_code"] == status
    assert original["executed"] is True and original["outcome_status"] == "failure"
    assert summary["final"]["stop_reason"] == f"http_{status}"
    assert summary["final"]["fetcher_calls"] == 0
    assert summary["final"]["search_queries"] == 1
    assert summary["final"]["elapsed_ms"] == 250
    refused = summary["actions"] if split_replay else summary["actions"][1:]
    assert len(refused) == 3
    _assert_stopped(logs, refused, status, 250)


@pytest.mark.parametrize("status", [402, 429])
@pytest.mark.parametrize("mode", MODES)
def test_sticky_provider_stop_blocks_fetch_and_search_after_exact_resume(
    tmp_path: Path, status: int, mode: str
) -> None:
    clock = _Clock()
    get_calls = search_calls = 0

    async def get(url: str) -> FetchResult:
        nonlocal get_calls
        get_calls += 1
        return _page(url)

    async def search(**kwargs: Any) -> Any:
        nonlocal search_calls
        search_calls += 1
        clock.advance(0.25)
        raise SearchUnavailable("Synthetic refusal.", http_status=status)

    logs = tmp_path / "logs"
    first = _execute(logs, _plan(mode, actions=[dict(QUERY)]), clock, get=get, search=search)
    resumed = _execute(
        logs,
        _plan(
            mode,
            actions=[URL, dict(QUERY)],
            resume_summary=first,
            start_ms=first["final"]["elapsed_ms"],
            start_calls=first["final"]["fetcher_calls"],
            start_search_queries=first["final"]["search_queries"],
            stop_reason=None,
        ),
        clock,
        get=get,
        search=search,
    )
    assert get_calls == 0 and search_calls == 1
    assert resumed["final"]["stop_reason"] == f"http_{status}"
    assert resumed["final"]["fetcher_calls"] == 0
    assert resumed["final"]["search_queries"] == 1
    assert resumed["final"]["elapsed_ms"] == first["final"]["elapsed_ms"] == 250
    _assert_stopped(logs, resumed["actions"], status, 250)


@pytest.mark.parametrize("status", [402, 429])
@pytest.mark.parametrize("mode", MODES)
def test_university_http_refusal_remains_an_ordinary_fetcher_outcome(
    tmp_path: Path, status: int, mode: str
) -> None:
    clock = _Clock()
    get_calls = search_calls = 0

    async def get(url: str) -> FetchResult:
        nonlocal get_calls
        get_calls += 1
        clock.advance(0.125)
        return _page(url, status if get_calls == 1 else 200)

    async def search(**kwargs: Any) -> Any:
        nonlocal search_calls
        search_calls += 1
        clock.advance(0.25)
        return SimpleNamespace(results=())

    logs = tmp_path / "logs"
    summary = _execute(
        logs,
        _plan(mode, actions=[URL, dict(QUERY), URL]),
        clock,
        get=get,
        search=search,
    )
    assert get_calls == 2 and search_calls == 1
    assert summary["final"]["stop_reason"] is None
    assert summary["final"]["fetcher_calls"] == 2
    assert summary["final"]["search_queries"] == 1
    records = [_record(logs, entry) for entry in summary["actions"]]
    assert records[0]["response"]["status_code"] == status
    assert records[0]["outcome_status"] == "failure"
    assert [record["outcome_status"] for record in records[1:]] == ["success", "success"]
    assert all(record["executed"] is True for record in records)
