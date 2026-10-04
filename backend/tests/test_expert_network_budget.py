"""Offline proof for V7's source ledger and immutable overall hang guard."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO

import pytest

from app.adapters.fetching import FetchResult
from app.adapters.search.base import SearchUnavailable
from app.domain.enums import FetchOutcome
from evaluation.research.expert import controller
from evaluation.research.expert.controller import execute
from evaluation.research.expert.models import validate_trace
from evaluation.research.expert.network_budget import (
    BUDGET_MODEL,
    NETWORK_COMPARISON_MODE,
    WALL_GUARD_MS,
    WallGuard,
    expert_budget,
    parse_wall_guard,
    validate_expert_budget,
)
from evaluation.research.expert.packet import digest

START = datetime(2026, 10, 4, tzinfo=UTC)
URL = "https://u.edu/admissions"


@dataclass
class _Clock:
    wall: datetime = START
    mono: float = 0.0

    def advance(self, seconds: int) -> None:
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


def _plan(**extra: Any) -> dict[str, Any]:
    return {
        "case_id": "network",
        "strict_budget": True,
        "max_calls": 60,
        "max_ms": WALL_GUARD_MS,
        "max_search_queries": 6,
        "budget_origin": NETWORK_COMPARISON_MODE,
        "budget_model": BUDGET_MODEL,
        "official_domains": ["u.edu"],
        "wall_started_at": START.isoformat(),
        "wall_deadline_at": (START + timedelta(milliseconds=WALL_GUARD_MS)).isoformat(),
        **extra,
    }


async def _get(url: str) -> FetchResult:
    return FetchResult(
        url=url,
        outcome=FetchOutcome.OK,
        final_url=url,
        status_code=200,
        content_type="text/html",
        content=b"<h1>International bachelor admissions</h1><p>Official programme information.</p>",
    )


async def _search(**kwargs: Any) -> Any:
    return SimpleNamespace(results=())


def _execute(tmp_path: Path, plan: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(
        execute(
            plan,
            tmp_path,
            get=kwargs.pop("get", _get),
            search=kwargs.pop("search", _search),
            provider_name=kwargs.pop("provider_name", "exa_mcp"),
            now=kwargs.pop("now", lambda: START),
            monotonic=kwargs.pop("monotonic", lambda: 0.0),
            **kwargs,
        )
    )


def _record(tmp_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    data = (tmp_path / entry["raw_log_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["raw_log_sha256"]
    return json.loads(data)


def _packet() -> dict[str, Any]:
    return {
        "baseline_pipeline_sha": "abcdef0123456789",
        "comparison_mode": NETWORK_COMPARISON_MODE,
        "expert_budget": expert_budget(),
        "baseline_budget": {
            "max_fetcher_calls": 60,
            "max_elapsed_ms": 120_000,
            "max_search_queries": 6,
            "browser_enabled": False,
        },
        "cases": [{"case_id": "network", "domain": "u.edu", "request": {}}],
    }


def _trace(packet: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    actions = []
    for index, entry in enumerate(summary["actions"], 1):
        actions.append(
            {
                key: entry[key]
                for key in (
                    "at",
                    "tool",
                    "request",
                    "outcome",
                    "outcome_status",
                    "policy_mode",
                    "final_url",
                    "raw_log_path",
                    "raw_log_sha256",
                    "elapsed_ms",
                    "fetcher_calls_cumulative",
                    "elapsed_ms_cumulative",
                    "search_queries_cumulative",
                )
            }
            | {
                "step": index,
                "observed_before": "The public request or previous source observation.",
                "observed_from_step": None if index == 1 else index - 1,
                "action": "Controlled source action.",
                "stage": "candidate_generation",
                "url": entry["request"].get("url"),
            }
        )
    return {
        "case_id": "network",
        "packet_sha256": digest(packet),
        "baseline_pipeline_sha": packet["baseline_pipeline_sha"],
        "max_fetcher_calls": 60,
        "max_elapsed_ms": WALL_GUARD_MS,
        "max_search_queries": 6,
        "initial_fetcher_calls": 0,
        "initial_elapsed_ms": 0,
        "initial_search_queries": 0,
        "budget_model": BUDGET_MODEL,
        "wall_started_at": summary["wall_started_at"],
        "wall_deadline_at": summary["wall_deadline_at"],
        "started_at": summary["wall_started_at"],
        "ended_at": summary["final"]["completed_at"],
        "actions": actions,
        "proposals": [],
    }


def _rewrite(tmp_path: Path, trace: dict[str, Any], record: dict[str, Any], step: int = 0) -> None:
    action = trace["actions"][step]
    data = json.dumps(record).encode()
    (tmp_path / action["raw_log_path"]).write_bytes(data)
    action["raw_log_sha256"] = hashlib.sha256(data).hexdigest()


def test_packet_keeps_baseline_120s_and_returns_fresh_expert_hang_guard_metadata() -> None:
    packet = _packet()
    budget = validate_expert_budget(packet)
    assert budget["max_elapsed_ms"] == WALL_GUARD_MS
    assert budget["max_elapsed_ms_purpose"] == "hang_guard_only"
    assert budget["elapsed_time_basis"] == "controller_actions_only"
    assert budget["model_thinking_included"] is False
    budget["max_fetcher_calls"] = 1
    assert (
        expert_budget()["max_fetcher_calls"] == packet["baseline_budget"]["max_fetcher_calls"] == 60
    )
    assert packet["baseline_budget"]["max_elapsed_ms"] == 120_000


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("expert_budget", "max_fetcher_calls", 61),
        ("expert_budget", "max_search_queries", 7),
        ("expert_budget", "max_elapsed_ms", 120_000),
        ("expert_budget", "wall_guard_ms", 900_001),
        ("expert_budget", "browser_enabled", True),
        ("expert_budget", "model_thinking_included", True),
        ("expert_budget", "model_thinking_included", 0),
        ("expert_budget", "budget_model", "other"),
        ("expert_budget", "elapsed_time_basis", "thinking_inclusive"),
        ("baseline_budget", "max_fetcher_calls", 59),
        ("baseline_budget", "max_search_queries", 5),
        ("baseline_budget", "max_elapsed_ms", 900_000),
        ("baseline_budget", "browser_enabled", True),
    ],
)
def test_packet_rejects_changed_or_ambiguous_comparison_caps(
    section: str, key: str, value: Any
) -> None:
    packet = _packet()
    packet[section][key] = value
    with pytest.raises(ValueError):
        validate_expert_budget(packet)


@pytest.mark.parametrize("span_ms", [0, 899_999, 900_001, 1_800_000])
def test_wall_guard_rejects_any_fresh_or_rounded_allowance(span_ms: int) -> None:
    with pytest.raises(ValueError, match="exactly"):
        parse_wall_guard(
            wall_started_at=START.isoformat(),
            wall_deadline_at=(START + timedelta(milliseconds=span_ms)).isoformat(),
        )


@pytest.mark.parametrize("value", [None, 1, "2026-10-04", "2026-10-04T00:00:00", "invalid"])
def test_wall_timestamps_require_timezone_aware_strings(value: Any) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_wall_guard(wall_started_at=value, wall_deadline_at=_plan()["wall_deadline_at"])


def test_wall_guard_normalizes_utc_and_floors_submillisecond_window() -> None:
    local = START.astimezone(timezone(timedelta(hours=6)))
    guard = parse_wall_guard(
        wall_started_at=local.isoformat(),
        wall_deadline_at=(local + timedelta(seconds=900)).isoformat(),
    )
    assert isinstance(guard, WallGuard)
    assert guard.as_dict() == {
        "wall_started_at": START.isoformat(),
        "wall_deadline_at": (START + timedelta(seconds=900)).isoformat(),
    }
    almost = guard.deadline_at - timedelta(microseconds=999)
    assert guard.remaining_ms(now=almost) == 0
    assert guard.remaining_seconds(now=almost) == 0.000999
    assert guard.remaining_ms(now=guard.deadline_at + timedelta(seconds=10)) == 0
    with pytest.raises(ValueError, match="precedes"):
        guard.remaining_ms(now=START - timedelta(microseconds=1))
    with pytest.raises(ValueError, match="timezone-aware"):
        guard.remaining_ms(now=START.replace(tzinfo=None))


@pytest.mark.parametrize(
    "change",
    [
        {"max_calls": 59},
        {"max_search_queries": 5},
        {"max_ms": 120_000},
        {"strict_budget": False},
        {"budget_model": "other"},
        {"wall_guard_ms": 900_001},
        {"model_thinking_included": True},
        {"browser_enabled": True},
        {"action_deadline_ms": 49_000},
        {"start_ms": 1},
        {"start_calls": 1},
        {"start_search_queries": 1},
    ],
)
def test_network_plan_requires_exact_declared_contract_and_real_fresh_counters(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        _execute(tmp_path, _plan(actions=[URL], **change))
    assert not list(tmp_path.iterdir())


def test_model_time_is_outside_source_ledger_and_cannot_be_injected_on_resume(
    tmp_path: Path,
) -> None:
    clock = _Clock(wall=START + timedelta(seconds=200))

    async def get(url: str) -> FetchResult:
        clock.advance(1)
        return await _get(url)

    first = _execute(
        tmp_path,
        _plan(actions=[URL]),
        get=get,
        now=lambda: clock.wall,
        monotonic=lambda: clock.mono,
    )
    assert first["final"]["elapsed_ms"] == 1_000
    assert first["final"]["wall_elapsed_ms"] == 201_000
    clock.advance(300)  # Model reasoning has no source call and no source-time debit.
    with pytest.raises(ValueError, match="measured"):
        _execute(
            tmp_path,
            _plan(resume_summary=first, start_ms=301_000, actions=[URL]),
            get=get,
            now=lambda: clock.wall,
            monotonic=lambda: clock.mono,
        )
    resumed = _execute(
        tmp_path,
        _plan(resume_summary=first, start_ms=1_000, actions=[URL]),
        get=get,
        now=lambda: clock.wall,
        monotonic=lambda: clock.mono,
    )
    assert resumed["initial"]["start_ms"] == 1_000
    assert resumed["final"]["elapsed_ms"] == 2_000
    assert resumed["final"]["wall_elapsed_ms"] == 502_000
    assert resumed["final"]["fetcher_calls"] == 2
    record = _record(tmp_path, resumed["actions"][0])
    assert record["elapsed_ms_before"] == record["charged_elapsed_ms"] == 1_000
    assert record["tool_policy"]["model_thinking_included"] is False
    assert record["dispatch_at"] == (START + timedelta(seconds=501)).isoformat()
    combined = {**resumed, "actions": [*first["actions"], *resumed["actions"]]}
    parsed = validate_trace(_trace(_packet(), combined), _packet(), logs_dir=tmp_path)
    assert parsed.actions[-1].elapsed_ms_cumulative == 2_000


@pytest.mark.parametrize("tool", ["fetcher", "search_provider"])
def test_network_read_and_query_caps_refuse_before_real_call(tmp_path: Path, tool: str) -> None:
    calls = 0

    async def get(url: str) -> FetchResult:
        nonlocal calls
        calls += 1
        return await _get(url)

    async def search(**kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return await _search(**kwargs)

    cap = 60 if tool == "fetcher" else 6
    action = URL if tool == "fetcher" else {"tool": tool, "query": "official programme"}
    summary = _execute(tmp_path, _plan(actions=[action] * (cap + 1)), get=get, search=search)
    assert calls == cap
    assert summary["actions"][-1]["outcome"] == "budget_exhausted"
    assert summary["actions"][-1]["executed"] is False
    assert _record(tmp_path, summary["actions"][-1])["dispatch_at"] is None
    resumed = _execute(
        tmp_path, _plan(resume_summary=summary, actions=[action]), get=get, search=search
    )
    assert calls == cap
    assert resumed["actions"][0]["outcome"] == "budget_exhausted"


@pytest.mark.parametrize("offset_seconds", [900, 901])
@pytest.mark.parametrize("exploration", ["same_policy", "outside_policy"])
def test_expired_guard_refuses_all_queued_tools_even_diagnostics(
    tmp_path: Path, offset_seconds: int, exploration: str
) -> None:
    async def get(url: str) -> FetchResult:
        raise AssertionError("No cold read after the wall deadline")

    async def search(**kwargs: Any) -> Any:
        raise AssertionError("No provider work after the wall deadline")

    summary = _execute(
        tmp_path,
        _plan(
            exploration_mode=exploration,
            actions=[URL, {"tool": "search_provider", "query": "programme"}],
        ),
        get=get,
        search=search,
        now=lambda: START + timedelta(seconds=offset_seconds),
    )
    assert all(entry["outcome"] == "wall_guard_exhausted" for entry in summary["actions"])
    assert summary["final"]["fetcher_calls"] == summary["final"]["search_queries"] == 0
    assert summary["final"]["elapsed_ms"] == 0
    assert summary["final"]["wall_elapsed_ms"] == offset_seconds * 1_000
    assert summary["final"]["wall_guard_exhausted"] is True


def test_log_reservation_crossing_wall_guard_is_rechecked_before_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock(wall=START + timedelta(seconds=899, milliseconds=999))
    reserve = controller._reserve_log

    @contextmanager
    def delayed_reserve(logs: Path, name: str, record: dict[str, Any]) -> Iterator[BinaryIO]:
        with reserve(logs, name, record) as output:
            clock.wall += timedelta(milliseconds=1)
            yield output

    monkeypatch.setattr(controller, "_reserve_log", delayed_reserve)

    async def get(url: str) -> FetchResult:
        raise AssertionError("Reservation consumed the final wall millisecond")

    summary = _execute(tmp_path, _plan(actions=[URL]), get=get, now=lambda: clock.wall)
    assert summary["actions"][0]["executed"] is False
    assert summary["actions"][0]["outcome"] == "wall_guard_exhausted"


@pytest.mark.parametrize("suppress_cancel", [False, True])
def test_absolute_wall_timeout_cancels_pending_action_without_fresh_source_allowance(
    tmp_path: Path, suppress_cancel: bool
) -> None:
    wall_start = datetime.now(UTC) - timedelta(seconds=899, milliseconds=970)
    cancelled = False
    calls = 0

    async def get(url: str) -> FetchResult:
        nonlocal cancelled, calls
        calls += 1
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled = True
            await asyncio.sleep(0.005)  # Cancellation cleanup is retained, never clamped.
            if suppress_cancel:
                return await _get(url)
            raise
        raise AssertionError("unreachable")

    summary = _execute(
        tmp_path,
        _plan(
            wall_started_at=wall_start.isoformat(),
            wall_deadline_at=(wall_start + timedelta(seconds=900)).isoformat(),
            actions=[URL, URL],
        ),
        get=get,
        now=lambda: datetime.now(UTC),
        monotonic=time.monotonic,
    )
    assert cancelled and calls == 1
    assert summary["actions"][0]["outcome"] == "action_timeout"
    assert summary["actions"][0]["outcome_status"] == "failure"
    assert summary["actions"][1]["outcome"] == "wall_guard_exhausted"
    assert summary["final"]["fetcher_calls"] == 1
    assert 5 <= summary["final"]["elapsed_ms"] < 1_000
    assert summary["final"]["wall_elapsed_ms"] > WALL_GUARD_MS
    assert summary["final"]["stop_reason"] == "wall_guard_exhausted"


def test_success_returned_after_guard_is_not_retained_as_source_evidence(tmp_path: Path) -> None:
    clock = _Clock(wall=START + timedelta(seconds=899))

    async def get(url: str) -> FetchResult:
        clock.advance(2)
        return await _get(url)

    summary = _execute(
        tmp_path,
        _plan(actions=[URL, URL]),
        get=get,
        now=lambda: clock.wall,
        monotonic=lambda: clock.mono,
    )
    assert summary["actions"][0]["outcome"] == "action_timeout"
    assert summary["actions"][0]["outcome_status"] == "failure"
    record = _record(tmp_path, summary["actions"][0])
    assert record["response"]["content_b64"] == ""
    assert record["response"]["content_sha256"]
    assert summary["final"]["elapsed_ms"] == 2_000
    assert summary["final"]["wall_elapsed_ms"] == 901_000
    assert summary["actions"][1]["executed"] is False


@pytest.mark.parametrize("resume_summary", [False, True])
def test_resume_cannot_reset_case_wall_even_with_a_full_new_900s_interval(
    tmp_path: Path, resume_summary: bool
) -> None:
    first = _execute(tmp_path, _plan(actions=[URL]))
    with pytest.raises(ValueError, match="wall guard"):
        _execute(
            tmp_path,
            _plan(
                wall_started_at=(START + timedelta(seconds=1)).isoformat(),
                wall_deadline_at=(START + timedelta(seconds=901)).isoformat(),
                resume_summary=first if resume_summary else None,
                actions=[URL],
            ),
            now=lambda: START + timedelta(seconds=2),
        )
    assert len(list(tmp_path.iterdir())) == 1


def test_empty_initial_summary_still_binds_wall_guard(tmp_path: Path) -> None:
    first = _execute(tmp_path, _plan())
    with pytest.raises(ValueError, match="wall guard"):
        _execute(
            tmp_path,
            _plan(
                wall_started_at=(START + timedelta(seconds=1)).isoformat(),
                wall_deadline_at=(START + timedelta(seconds=901)).isoformat(),
                resume_summary=first,
                actions=[URL],
            ),
            now=lambda: START + timedelta(seconds=2),
        )


def test_network_429_is_sanitized_sticky_and_cannot_be_cleared_by_prefix_or_resume(
    tmp_path: Path,
) -> None:
    calls = 0

    async def search(**kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise SearchUnavailable("secret api_key=do-not-echo", http_status=429)

    action = {"tool": "search_provider", "query": "programme"}
    first = _execute(tmp_path, _plan(actions=[action, action]), search=search)
    assert calls == 1 and first["final"]["search_queries"] == 1
    assert "do-not-echo" not in json.dumps(_record(tmp_path, first["actions"][0]))
    resumed = _execute(
        tmp_path, _plan(resume_summary=first, stop_reason=None, actions=[action]), search=search
    )
    assert calls == 1 and resumed["final"]["stop_reason"] == "http_429"
    assert resumed["actions"][0]["outcome"] == "stopped_after_http_429"
    with pytest.raises(ValueError, match="log_prefix"):
        _execute(
            tmp_path,
            _plan(resume_summary=resumed, log_prefix="new", actions=[action]),
            search=search,
        )
    assert calls == 1


def test_university_429_is_a_source_failure_and_does_not_latch_provider_quota(tmp_path: Path) -> None:
    calls = 0

    async def get(url: str) -> FetchResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SearchUnavailable("University response detail withheld", http_status=429)
        return await _get(url)

    summary = _execute(tmp_path, _plan(actions=[URL, URL]), get=get)
    assert calls == 2 and summary["final"]["stop_reason"] is None
    assert summary["actions"][0]["outcome_status"] == "failure"
    assert summary["actions"][1]["outcome_status"] == "success"
    validate_trace(_trace(_packet(), summary), _packet(), logs_dir=tmp_path)


def test_same_case_directory_cannot_reset_budget_or_wall_via_new_prefix_without_summary(
    tmp_path: Path,
) -> None:
    first = _execute(tmp_path, _plan(actions=[URL]))
    with pytest.raises(ValueError, match="log_prefix"):
        _execute(
            tmp_path,
            _plan(
                log_prefix="fresh",
                wall_started_at=(START + timedelta(seconds=200)).isoformat(),
                wall_deadline_at=(START + timedelta(seconds=1100)).isoformat(),
                actions=[URL],
            ),
            now=lambda: START + timedelta(seconds=200),
        )
    assert len(list(tmp_path.iterdir())) == len(first["actions"])


def test_explicit_diagnostics_can_overflow_counts_but_never_become_same_policy(
    tmp_path: Path,
) -> None:
    summary = _execute(tmp_path, _plan(exploration_mode="outside_policy", actions=[URL] * 61))
    assert summary["final"]["fetcher_calls"] == 61
    assert all(entry["policy_mode"] == "outside_policy" for entry in summary["actions"])
    assert summary["tool_policy"]["exploration_mode"] == "outside_policy"


def test_legacy_strict_120s_still_debits_model_time_and_rejects_900s_cap(tmp_path: Path) -> None:
    legacy = {
        "case_id": "legacy",
        "strict_budget": True,
        "max_calls": 60,
        "max_ms": 120_000,
        "max_search_queries": 6,
        "official_domains": ["u.edu"],
        "start_ms": 120_000,
        "actions": [URL],
    }
    summary = _execute(tmp_path, legacy)
    assert summary["actions"][0]["outcome"] == "budget_exhausted"
    assert summary["final"]["elapsed_ms"] == 120_000
    assert "wall_started_at" not in summary
    with pytest.raises(ValueError, match="120 seconds"):
        _execute(tmp_path, {**legacy, "case_id": "legacy900", "max_ms": 900_000})


def test_network_run_keeps_production_fetcher_safeguards_and_cold_read_wrapper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.adapters.fetching
    import app.adapters.search
    import app.config

    calls: list[tuple[str, bool]] = []
    constructions: list[dict[str, Any]] = []

    class Fetcher:
        def __init__(self, cache_dir: Path, **kwargs: Any) -> None:
            constructions.append(kwargs)

        async def __aenter__(self) -> Fetcher:
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        async def get(self, url: str, *, use_cache: bool = True) -> FetchResult:
            calls.append((url, use_cache))
            return await _get(url)

    monkeypatch.setattr(app.adapters.fetching, "Fetcher", Fetcher)
    monkeypatch.setattr(
        app.adapters.search,
        "get_search_provider",
        lambda: SimpleNamespace(name="exa_mcp", search=_search),
    )
    monkeypatch.setattr(
        app.config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa_mcp",
            respect_robots=False,
            fetch_delay_seconds=1.5,
            fetch_timeout_seconds=20,
            fetch_contact="Public contact",
        ),
    )
    started = datetime.now(UTC)
    plan = _plan(
        wall_started_at=started.isoformat(),
        wall_deadline_at=(started + timedelta(seconds=900)).isoformat(),
        actions=[URL],
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    summary = asyncio.run(controller.run(plan_path, tmp_path / "logs", tmp_path / "cache"))
    assert calls == [(URL, False)]
    assert constructions[0]["respect_robots"] is True
    assert "browser_enabled" not in constructions[0]
    assert summary["final"]["fetcher_calls"] == 1
    assert summary["tool_policy"]["browser_enabled"] is False
    assert summary["budget_model"] == BUDGET_MODEL


def test_real_controller_network_trace_uses_expert_budget_and_retains_exact_saved_source(
    tmp_path: Path,
) -> None:
    packet = _packet()
    summary = _execute(
        tmp_path, _plan(actions=[URL, {"tool": "search_provider", "query": "programme"}])
    )
    trace = _trace(packet, summary)
    parsed = validate_trace(trace, packet, logs_dir=tmp_path)
    assert parsed.max_elapsed_ms == WALL_GUARD_MS
    assert parsed.max_fetcher_calls == packet["baseline_budget"]["max_fetcher_calls"]
    assert parsed.max_search_queries == packet["baseline_budget"]["max_search_queries"]
    trace["proposals"] = [
        {
            "claim_key": "programme.note",
            "value": "Official programme information.",
            "source_url": URL,
            "excerpt": "Official programme information.",
            "accessed_on": START.date().isoformat(),
            "scope": {},
            "supporting_steps": [1],
        }
    ]
    validate_trace(trace, packet, logs_dir=tmp_path)
    trace["proposals"][0]["excerpt"] = "Invented exact quotation."
    with pytest.raises(ValueError, match="Proposed quote"):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize("field", ["budget_model", "wall_started_at", "wall_deadline_at"])
def test_network_trace_requires_explicit_wall_and_model_fields(tmp_path: Path, field: str) -> None:
    packet = _packet()
    trace = _trace(packet, _execute(tmp_path, _plan(actions=[URL])))
    del trace[field]
    with pytest.raises(ValueError):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(wall_deadline_at=(START + timedelta(seconds=901)).isoformat()),
        lambda r: r["tool_policy"].update(model_thinking_included=True),
        lambda r: r["tool_policy"].update(budget_model="legacy"),
        lambda r: r.update(dispatch_at=None),
        lambda r: r.update(dispatch_at=(START + timedelta(seconds=900)).isoformat()),
        lambda r: r.update(completed_at=(START + timedelta(seconds=901)).isoformat()),
        lambda r: r.update(wall_elapsed_ms=200_000),
        lambda r: r.update(case_id="foreign"),
        lambda r: r["tool_policy"].update(official_domains=["foreign.edu"]),
        lambda r: r.update(charged_elapsed_ms=200_000, elapsed_ms_cumulative=200_000),
    ],
)
def test_trace_rejects_hash_recomputed_wall_identity_policy_and_model_time_tampering(
    tmp_path: Path, mutate: Callable[[dict[str, Any]], Any]
) -> None:
    packet = _packet()
    summary = _execute(tmp_path, _plan(actions=[URL]))
    trace = _trace(packet, summary)
    record = _record(tmp_path, summary["actions"][0])
    mutate(record)
    if record["elapsed_ms_cumulative"]:
        trace["actions"][0]["elapsed_ms_cumulative"] = record["elapsed_ms_cumulative"]
    _rewrite(tmp_path, trace, record)
    with pytest.raises(ValueError):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_network_trace_cannot_use_unstructured_hash_only_logs_or_symlink(tmp_path: Path) -> None:
    packet = _packet()
    summary = _execute(tmp_path, _plan(actions=[URL]))
    trace = _trace(packet, summary)
    path = tmp_path / trace["actions"][0]["raw_log_path"]
    original = path.read_bytes()
    _rewrite(tmp_path, trace, {"hash_only": "opaque"})
    with pytest.raises(ValueError, match="structured"):
        validate_trace(trace, packet, logs_dir=tmp_path)
    path.write_bytes(original)
    trace = _trace(packet, summary)
    real = tmp_path / "real.json"
    path.rename(real)
    path.symlink_to(real)
    with pytest.raises(ValueError, match="regular"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_network_trace_requires_raw_logs_and_does_not_relabel_old_packet(tmp_path: Path) -> None:
    packet = _packet()
    trace = _trace(packet, _execute(tmp_path, _plan(actions=[URL])))
    with pytest.raises(ValueError, match="raw logs"):
        validate_trace(trace, packet)
    legacy_packet = deepcopy(packet)
    legacy_packet["comparison_mode"] = "independent_full_budget"
    del legacy_packet["expert_budget"]
    trace["packet_sha256"] = digest(legacy_packet)
    with pytest.raises(ValueError, match="network packet"):
        validate_trace(trace, legacy_packet, logs_dir=tmp_path)


def test_trace_cannot_relabel_model_time_as_a_measured_source_action(tmp_path: Path) -> None:
    packet = _packet()
    summary = _execute(tmp_path, _plan(actions=[URL]))
    trace = _trace(packet, summary)
    record = _record(tmp_path, summary["actions"][0])
    for key in ("elapsed_ms", "charged_elapsed_ms", "elapsed_ms_cumulative"):
        record[key] = 200_000
    trace["actions"][0]["elapsed_ms"] = trace["actions"][0]["elapsed_ms_cumulative"] = 200_000
    _rewrite(tmp_path, trace, record)
    with pytest.raises(ValueError, match="source elapsed"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_network_trace_cannot_promote_explicit_diagnostic_action(tmp_path: Path) -> None:
    packet = _packet()
    summary = _execute(tmp_path, _plan(exploration_mode="outside_policy", actions=[URL]))
    trace = _trace(packet, summary)
    validate_trace(trace, packet, logs_dir=tmp_path)
    record = _record(tmp_path, summary["actions"][0])
    record["policy_mode"] = trace["actions"][0]["policy_mode"] = "same_policy"
    _rewrite(tmp_path, trace, record)
    with pytest.raises(ValueError, match="Diagnostic"):
        validate_trace(trace, packet, logs_dir=tmp_path)
