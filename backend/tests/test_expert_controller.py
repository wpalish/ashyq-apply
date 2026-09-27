"""The expert run controller logs every call itself and keeps one budget."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from evaluation.research.expert.controller import blocked, execute, expert_view


@dataclass
class _Outcome:
    value: str


@dataclass
class _Result:
    url: str
    content: bytes
    ok: bool = True
    status_code: int = 200
    final_url: str = ""
    content_type: str = "text/html"
    from_cache: bool = False
    fetch_tier: str = "http"
    error: str = ""
    fetched_at: datetime = datetime(2026, 9, 27, tzinfo=UTC)
    outcome: _Outcome = field(default_factory=lambda: _Outcome("ok"))


def _plan(**extra: object) -> dict[str, object]:
    return {"case_id": "x", "max_calls": 2, "max_ms": 60_000, **extra}


def test_replay_then_actions_share_one_budget_and_overflow_is_outside_policy(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    async def get(url: str) -> _Result:
        calls.append(url)
        return _Result(url, b"<html><body><p>Hi</p><a href='https://u.edu/b'>B</a></body></html>")

    plan = _plan(
        replay=["https://u.edu/"],
        actions=[{"tool": "fetcher", "url": "https://u.edu/a"}, "https://u.edu/c"],
    )
    summary = asyncio.run(execute(plan, tmp_path, get=get, search=None, provider_name="none"))
    assert calls == ["https://u.edu/", "https://u.edu/a", "https://u.edu/c"]
    modes = [a["policy_mode"] for a in summary["replay"] + summary["actions"]]
    assert modes == ["same_policy", "same_policy", "outside_policy"]
    assert summary["final"]["fetcher_calls"] == 3
    for entry in summary["replay"] + summary["actions"]:
        data = (tmp_path / entry["raw_log_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["raw_log_sha256"]
    record = json.loads((tmp_path / summary["actions"][0]["raw_log_path"]).read_text())
    view = expert_view(record)
    assert view["text"].split() == ["Hi", "B"]
    assert view["links"] == [{"url": "https://u.edu/b", "text": "B"}]


def test_repository_hosts_are_refused_without_a_request(tmp_path: Path) -> None:
    async def get(url: str) -> _Result:
        raise AssertionError("must not be called")

    plan = _plan(actions=["https://github.com/wpalish/ashyq-apply"])
    summary = asyncio.run(execute(plan, tmp_path, get=get, search=None, provider_name="none"))
    assert summary["actions"][0]["outcome"] == "blocked_by_tool_policy"
    assert summary["final"]["fetcher_calls"] == 0
    assert blocked("https://raw.githubusercontent.com/a") and not blocked("https://kaist.ac.kr")


def test_search_results_on_blocked_hosts_are_dropped(tmp_path: Path) -> None:
    @dataclass
    class _Hit:
        rank: int
        url: str
        title: str = ""
        snippet: str = ""

    @dataclass
    class _Answer:
        results: tuple[_Hit, ...]

    async def search(**kwargs: object) -> _Answer:
        return _Answer((_Hit(1, "https://github.com/x"), _Hit(2, "https://u.edu/p")))

    async def get(url: str) -> _Result:
        raise AssertionError

    plan = _plan(actions=[{"tool": "search_provider", "query": "q", "domains": ["u.edu"]}])
    summary = asyncio.run(execute(plan, tmp_path, get=get, search=search, provider_name="fake"))
    record = json.loads((tmp_path / summary["actions"][0]["raw_log_path"]).read_text())
    assert [r["url"] for r in record["response"]["results"]] == ["https://u.edu/p"]
    assert record["response"]["dropped_by_tool_policy"] == 1
    assert summary["actions"][0]["fetcher_calls_cumulative"] == 0
