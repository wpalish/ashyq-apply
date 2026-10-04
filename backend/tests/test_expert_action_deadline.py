"""Mock-only navigation deadlines preserve time for an expert's final submission."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO

import pytest

from app.adapters.fetching import FetchResult
from app.domain.enums import FetchOutcome
from evaluation.research.expert import controller
from evaluation.research.expert.controller import execute


def _plan(**extra: Any) -> dict[str, Any]:
    return {
        "case_id": "deadline",
        "strict_budget": True,
        "max_calls": 60,
        "max_ms": 120_000,
        "max_search_queries": 6,
        "official_domains": ["u.edu"],
        "action_deadline_ms": 75_000,
        **extra,
    }


async def _get(url: str) -> FetchResult:
    return FetchResult(
        url=url,
        outcome=FetchOutcome.OK,
        final_url=url,
        status_code=200,
        content_type="text/html",
        content=b"<p>Official programme information.</p>",
    )


def _execute(tmp_path: Path, plan: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(
        execute(
            plan,
            tmp_path,
            get=kwargs.pop("get", _get),
            search=kwargs.pop("search", None),
            provider_name="exa_mcp",
            monotonic=kwargs.pop("monotonic", lambda: 0.0),
            **kwargs,
        )
    )


def _record(tmp_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    data = (tmp_path / entry["raw_log_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["raw_log_sha256"]
    return json.loads(data)


@pytest.mark.parametrize(
    "action",
    ["https://u.edu/programme", {"tool": "search_provider", "query": "programmes"}],
)
@pytest.mark.parametrize("start_ms", [75_000, 80_000])
def test_navigation_refuses_first_action_at_or_after_its_deadline(
    tmp_path: Path, action: str | dict[str, Any], start_ms: int
) -> None:
    async def get(url: str) -> FetchResult:
        raise AssertionError("deadline must refuse before Fetcher.get")

    async def search(**kwargs: Any) -> Any:
        raise AssertionError("deadline must refuse before a provider query")

    summary = _execute(tmp_path, _plan(start_ms=start_ms, actions=[action]), get=get, search=search)
    entry = summary["actions"][0]
    record = _record(tmp_path, entry)
    assert entry["executed"] is False
    assert entry["outcome"] == "action_deadline_exhausted"
    assert entry["outcome_status"] == "blocked"
    assert summary["final"]["fetcher_calls"] == summary["final"]["search_queries"] == 0
    assert summary["final"]["elapsed_ms"] == start_ms
    assert summary["final"]["stop_reason"] == "action_deadline_exhausted"
    assert record["tool_policy"]["action_deadline_ms"] == summary["action_deadline_ms"] == 75_000
    assert record["budgets"]["max_ms"] == summary["tool_policy"]["max_elapsed_ms"] == 120_000


def test_pending_fetch_is_cancelled_charged_and_saved_before_reserved_final_time(
    tmp_path: Path,
) -> None:
    called: list[str] = []
    cancelled = False

    async def get(url: str) -> FetchResult:
        nonlocal cancelled
        called.append(url)
        pending = json.loads((tmp_path / "deadline-001.json").read_bytes())
        assert pending["outcome"] == "pending"
        assert pending["tool_policy"]["action_deadline_ms"] == 75_000
        try:
            await asyncio.Event().wait()
        finally:
            cancelled = True
        raise AssertionError("the navigation deadline must cancel this pending fetch")

    summary = _execute(
        tmp_path,
        _plan(start_ms=74_995, actions=["https://u.edu/programme", "https://u.edu/next"]),
        get=get,
    )
    assert called == ["https://u.edu/programme"] and cancelled
    first, second = summary["actions"]
    record = _record(tmp_path, first)
    assert first["executed"] is True and first["outcome"] == "action_timeout"
    assert first["outcome_status"] == "failure"
    assert record["response"]["outcome_status"] == "failure"
    assert record["elapsed_ms_before"] == 74_995
    assert record["charged_elapsed_ms"] == 5
    assert first["elapsed_ms_cumulative"] == 75_000
    assert first["fetcher_calls_cumulative"] == 1
    assert second["outcome"] == "action_deadline_exhausted" and not second["executed"]
    _record(tmp_path, second)
    assert summary["final"]["elapsed_ms"] == 75_000
    assert summary["final"]["fetcher_calls"] == 1
    assert summary["final"]["stop_reason"] == "action_deadline_exhausted"
    assert summary["tool_policy"]["max_elapsed_ms"] == 120_000

    # A later final submission can resume the charged state without any tool I/O.
    final = _execute(tmp_path, _plan(resume_summary=summary, actions=[]), get=get)
    assert final["initial"]["start_ms"] == final["final"]["elapsed_ms"] == 75_000
    assert final["final"]["fetcher_calls"] == 1
    assert final["final"]["stop_reason"] == "action_deadline_exhausted"
    assert final["actions"] == [] and len(called) == 1
    assert final["raw_logs"] == summary["raw_logs"]


def test_reserving_log_cannot_delay_a_call_start_beyond_navigation_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [0.0]
    reserve = controller._reserve_log

    @contextmanager
    def delayed_reservation(
        logs_dir: Path, name: str, record: dict[str, Any]
    ) -> Iterator[BinaryIO]:
        with reserve(logs_dir, name, record) as output:
            clock[0] += 0.006
            yield output

    monkeypatch.setattr(controller, "_reserve_log", delayed_reservation)

    async def get(url: str) -> FetchResult:
        raise AssertionError("active log reservation crossed the navigation deadline")

    summary = _execute(
        tmp_path,
        _plan(start_ms=74_995, actions=["https://u.edu/programme"]),
        get=get,
        monotonic=lambda: clock[0],
    )
    entry = summary["actions"][0]
    record = _record(tmp_path, entry)
    assert entry["outcome"] == "action_deadline_exhausted" and not entry["executed"]
    assert entry["fetcher_calls_cumulative"] == 0
    assert entry["elapsed_ms_cumulative"] == 75_001
    assert record["elapsed_ms_before"] == 74_995 and record["charged_elapsed_ms"] == 6


@pytest.mark.parametrize("deadline", [0, -1, True, 1.5, "75000", 120_001])
def test_navigation_deadline_must_be_an_integer_within_full_budget(
    tmp_path: Path, deadline: Any
) -> None:
    with pytest.raises(ValueError, match="action_deadline_ms"):
        _execute(tmp_path, _plan(action_deadline_ms=deadline, actions=["https://u.edu/"]))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("changed", [None, 74_000, 80_000])
@pytest.mark.parametrize("recorded_actions", [[], ["https://u.edu/programme"]])
def test_resume_cannot_change_or_remove_its_recorded_navigation_deadline(
    tmp_path: Path, changed: int | None, recorded_actions: list[str]
) -> None:
    summary = _execute(tmp_path, _plan(actions=recorded_actions))
    plan = _plan(action_deadline_ms=changed, resume_summary=summary, actions=["https://u.edu/next"])
    if changed is None:
        plan.pop("action_deadline_ms")
    before = list(tmp_path.iterdir())
    with pytest.raises(ValueError, match="action_deadline_ms"):
        _execute(tmp_path, plan)
    assert list(tmp_path.iterdir()) == before


def test_raw_policy_alone_pins_deadline_and_resume_retains_counters(tmp_path: Path) -> None:
    first = _execute(tmp_path, _plan(start_ms=74_999, actions=["https://u.edu/programme"]))
    resumed = _execute(tmp_path, _plan(start_ms=75_000, actions=["https://u.edu/next"]))
    assert first["final"]["fetcher_calls"] == resumed["initial"]["start_calls"] == 1
    assert resumed["actions"][0]["outcome"] == "action_deadline_exhausted"
    assert resumed["actions"][0]["raw_log_path"] == "deadline-002.json"
    before = list(tmp_path.iterdir())
    with pytest.raises(ValueError, match="action_deadline_ms"):
        _execute(tmp_path, _plan(action_deadline_ms=80_000, actions=["https://u.edu/next"]))
    assert list(tmp_path.iterdir()) == before


def test_explicit_outside_policy_does_not_spend_the_reserved_final_time(tmp_path: Path) -> None:
    summary = _execute(
        tmp_path,
        _plan(start_ms=75_000, exploration_mode="outside_policy", actions=["https://u.edu/"]),
    )
    assert summary["actions"][0]["executed"] is False
    assert summary["actions"][0]["outcome"] == "action_deadline_exhausted"
    assert summary["actions"][0]["policy_mode"] == "outside_policy"


def test_removing_full_budget_deadline_cannot_enable_diagnostic_overflow(tmp_path: Path) -> None:
    summary = _execute(tmp_path, _plan(action_deadline_ms=120_000, actions=[]))
    plan = _plan(
        resume_summary=summary,
        start_ms=120_000,
        exploration_mode="outside_policy",
        actions=["https://u.edu/programme"],
    )
    plan.pop("action_deadline_ms")
    with pytest.raises(ValueError, match="action_deadline_ms"):
        _execute(tmp_path, plan)
    assert not list(tmp_path.iterdir())


def test_default_strict_plan_keeps_full_navigation_budget(tmp_path: Path) -> None:
    plan = _plan(start_ms=80_000, actions=["https://u.edu/programme"])
    plan.pop("action_deadline_ms")
    summary = _execute(tmp_path, plan)
    assert summary["actions"][0]["executed"] is True
    assert summary["actions"][0]["outcome_status"] == "success"
    assert summary["final"]["fetcher_calls"] == 1
    assert summary["final"]["elapsed_ms"] == 80_000
    assert summary["final"]["stop_reason"] is None
    assert "action_deadline_ms" not in summary["tool_policy"]


def test_legacy_plan_remains_unbounded_by_optional_navigation_deadline(tmp_path: Path) -> None:
    summary = _execute(
        tmp_path,
        _plan(strict_budget=False, start_ms=80_000, actions=["https://u.edu/programme"]),
    )
    assert summary["actions"][0]["executed"] is True
    assert summary["actions"][0]["outcome_status"] == "success"
    assert summary["final"]["elapsed_ms"] == 80_000
    assert summary["final"]["stop_reason"] is None
