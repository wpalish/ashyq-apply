"""Synthetic clock/cancellation checks for the optional baseline closing reserve."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import get_settings
from evaluation.research import live
from evaluation.research.schema import Capture, Observation
from scripts import canary_discovery as canary


@pytest.fixture(autouse=True)
def _synthetic_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    bindings = tmp_path / "synthetic-bindings.json"
    bindings.write_text(json.dumps({"version": "synthetic", "bindings": []}))
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _report() -> dict[str, Any]:
    return {"institutions": [{"programs": []}], "run_error": ""}


def _budget(output: Path) -> dict[str, Any]:
    return json.loads(output.with_suffix(".budget.json").read_text())


def test_reserve_uses_one_absolute_clock_without_clamping_the_full_budget() -> None:
    clock = _Clock()
    budget = live._ExpertBudget(60, 120, "exa_mcp", 0.0, clock=clock, finalization_reserve_ms=1000)
    assert budget.remaining() == 119
    clock.now = 118.5
    assert budget.remaining() == 0.5
    clock.now = 119
    for admission in (budget.before_fetch, lambda: budget.before_search("exa_mcp")):
        with pytest.raises(TimeoutError, match="WALL_CLOCK_BUDGET_EXHAUSTED"):
            admission()
    assert budget.fetcher_calls == budget.search_queries == 0
    clock.now = 120.005
    status = budget.snapshot()
    assert status["elapsed_ms"] == 120005
    assert status["max_active_seconds"] == 120
    assert status["max_fetcher_calls"] == 60
    assert status["max_search_queries"] == 6
    assert status["finalization_reserve_ms"] == 1000
    assert status["source_work_deadline_ms"] == 119000
    assert status["stop_reason"] == "source_work_deadline_exhausted"


def test_default_zero_reserve_preserves_the_full_existing_work_deadline() -> None:
    clock = _Clock()
    budget = live._ExpertBudget(60, 120, "exa_mcp", 0.0, clock=clock)
    clock.now = 119
    assert budget.remaining() == 1
    budget.before_fetch()
    budget.before_search("exa_mcp")
    assert budget.fetcher_calls == budget.search_queries == 1
    clock.now = 120
    with pytest.raises(TimeoutError):
        budget.remaining()
    assert budget.snapshot()["stop_reason"] == "wall_clock_budget_exhausted"


@pytest.mark.asyncio
async def test_pipeline_setup_consumes_the_same_source_work_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    monkeypatch.setattr(live, "time", SimpleNamespace(monotonic=clock))
    original_observation = live.Observation

    def observation(**kwargs: Any) -> Observation:
        clock.now += 3
        return original_observation(**kwargs)

    timeouts = []

    async def wait_for(awaitable: Any, timeout: float) -> Any:
        timeouts.append(timeout)
        return await awaitable

    async def run(*args: Any) -> dict[str, Any]:
        clock.now = 118
        return _report()

    monkeypatch.setattr(live, "Observation", observation)
    monkeypatch.setattr(live.asyncio, "wait_for", wait_for)
    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one(
        "groningen", output, 60, 120, strict_expert_budget=True, finalization_reserve_ms=1000
    )
    assert timeouts == [116]
    status = _budget(output)
    assert status["elapsed_ms"] == 118000
    assert status["source_work_deadline_ms"] == 119000


@pytest.mark.asyncio
async def test_cancellation_cleanup_overrun_remains_recorded_without_a_fresh_allowance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    monkeypatch.setattr(live, "time", SimpleNamespace(monotonic=clock))
    original_wait_for = asyncio.wait_for
    deadlines = []
    cleanup = []

    async def wait_for(awaitable: Any, timeout: float) -> Any:
        deadlines.append(timeout)
        return await original_wait_for(awaitable, timeout=0.001)

    async def run(*args: Any) -> dict[str, Any]:
        try:
            await asyncio.sleep(10)
        finally:
            clock.now = 120.005
            cleanup.append("finished")
        raise AssertionError("must be cancelled")

    monkeypatch.setattr(live.asyncio, "wait_for", wait_for)
    monkeypatch.setattr(canary, "run_canary", run)
    output = tmp_path / "groningen.json"
    await live.capture_one(
        "groningen", output, 60, 120, strict_expert_budget=True, finalization_reserve_ms=1000
    )
    assert cleanup == ["finished"]
    assert deadlines == [119]
    status = _budget(output)
    assert status["elapsed_ms"] == 120005
    assert status["max_active_seconds"] == 120
    assert status["source_work_deadline_ms"] == 119000
    assert status["fetcher_calls"] == status["search_queries"] == 0
    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.latency_seconds == 120.005
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"


@pytest.mark.asyncio
@pytest.mark.parametrize("seam", ["fetcher", "provider"])
async def test_slow_pre_call_checkpoint_cannot_start_io_after_the_source_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seam: str
) -> None:
    from app.adapters.search.exa_mcp import ExaMcpSearchProvider

    clock = _Clock()
    monkeypatch.setattr(live, "time", SimpleNamespace(monotonic=clock))
    entered = False
    actual_calls = []

    class Fetcher:
        def __init__(self) -> None:
            self.tier_counts = {"browser": 0}

        async def get(self, *args: Any, **kwargs: Any) -> Any:
            actual_calls.append("fetcher")
            pytest.fail("Fetcher must not start after its pre-call checkpoint crosses the deadline")

    async def search(*args: Any, **kwargs: Any) -> Any:
        actual_calls.append("provider")
        pytest.fail("Provider must not start after its pre-call checkpoint crosses the deadline")

    original_write = Path.write_text

    def write(path: Path, *args: Any, **kwargs: Any) -> int:
        result = original_write(path, *args, **kwargs)
        if entered and path.name == "groningen.pending":
            clock.now += 0.02
        return result

    async def run(*args: Any) -> dict[str, Any]:
        nonlocal entered
        clock.now = 118.99
        entered = True
        if seam == "fetcher":
            await object.__new__(canary.CanaryRunner)._make_fetcher().get("https://rug.nl/page")
        else:
            await object.__new__(ExaMcpSearchProvider).search(query="site:rug.nl public policy")
        raise AssertionError("must refuse after the checkpoint")

    monkeypatch.setattr(canary.CanaryRunner, "_make_fetcher", lambda self: Fetcher())
    monkeypatch.setattr(ExaMcpSearchProvider, "search", search)
    monkeypatch.setattr(canary, "run_canary", run)
    monkeypatch.setattr(Path, "write_text", write)
    output = tmp_path / "groningen.json"
    await live.capture_one(
        "groningen", output, 60, 120, strict_expert_budget=True, finalization_reserve_ms=1000
    )
    assert actual_calls == []
    status = _budget(output)
    assert status["stop_reason"] == "source_work_deadline_exhausted"
    assert status["elapsed_ms"] >= 119010


@pytest.mark.asyncio
async def test_successful_output_and_first_final_checkpoint_cost_remain_in_the_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    monkeypatch.setattr(live, "time", SimpleNamespace(monotonic=clock))
    finished = False

    async def run(*args: Any) -> dict[str, Any]:
        nonlocal finished
        clock.now = 118.8
        finished = True
        return _report()

    original_write = Path.write_text

    def write(path: Path, *args: Any, **kwargs: Any) -> int:
        result = original_write(path, *args, **kwargs)
        if finished:
            clock.now += {
                "groningen.json": 0.001,
                "groningen.raw.json": 0.200,
                "groningen.pending": 0.002,
                "groningen.budget.pending": 0.003,
            }.get(path.name, 0)
        return result

    monkeypatch.setattr(canary, "run_canary", run)
    monkeypatch.setattr(Path, "write_text", write)
    output = tmp_path / "groningen.json"
    await live.capture_one(
        "groningen", output, 60, 120, strict_expert_budget=True, finalization_reserve_ms=1000
    )
    status = _budget(output)
    assert status["elapsed_ms"] >= 119006
    assert status["elapsed_ms"] < 120000
    assert "final checkpoint" in status["active_time_basis"]
    assert output.with_suffix(".raw.json").is_file()


@pytest.mark.parametrize(
    "extra",
    [
        ["--finalization-reserve-ms", "1000"],
        ["--finalization-reserve-ms", "0"],
        ["--strict-expert-budget", "--finalization-reserve-ms", "-1"],
        ["--strict-expert-budget", "--finalization-reserve-ms", "120000"],
        ["--strict-expert-budget", "--finalization-reserve-ms", "120001"],
    ],
)
def test_invalid_reserve_is_rejected_before_any_parent_side_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: list[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--out", str(tmp_path), *extra])
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: pytest.fail("must not call git")
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("must not launch child")
    )
    with pytest.raises(SystemExit) as error:
        live.main()
    assert error.value.code == 2
    assert not list(tmp_path.glob("*/capture.json"))


def test_parent_forwards_reserve_and_advertises_the_unchanged_full_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(tmp_path),
            "--strict-expert-budget",
            "--finalization-reserve-ms",
            "1000",
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-source-sha")

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[command.index("--finalization-reserve-ms") + 1] == "1000"
        assert command[command.index("--seconds-per-case") + 1] == "120"
        assert command[command.index("--max-pages") + 1] == "60"
        assert kwargs["timeout"] == 135
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json())
        output.with_suffix(".budget.json").write_text(json.dumps({"elapsed_ms": 119004}))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    capture = Capture.model_validate_json(next(tmp_path.glob("*/capture.json")).read_text())
    assert capture.config["seconds_per_case"] == capture.config["child_active_seconds"] == 120
    assert capture.config["max_fetcher_calls_per_case"] == 60
    assert capture.config["max_search_queries_per_case"] == 6
    assert capture.config["finalization_reserve_ms"] == 1000
    assert capture.config["source_work_deadline_ms"] == 119000
    budgets = capture.config["case_budgets"]
    assert isinstance(budgets, dict) and isinstance(budgets["groningen"], dict)
    assert budgets["groningen"]["elapsed_ms"] == 119004


def test_child_receives_the_reserve_with_the_full_case_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = []

    async def capture(*args: Any, **kwargs: Any) -> None:
        called.append((args, kwargs))

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            "groningen",
            "--out",
            str(tmp_path),
            "--strict-expert-budget",
            "--finalization-reserve-ms",
            "1000",
        ],
    )
    live.main()
    assert called == [
        (
            ("groningen", tmp_path, 60, 120),
            {"strict_expert_budget": True, "finalization_reserve_ms": 1000},
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reserve,strict", [(1000, False), (-1, True), (120000, True), (True, True)]
)
async def test_capture_api_rejects_invalid_reserve_before_output(
    tmp_path: Path, reserve: Any, strict: bool
) -> None:
    output = tmp_path / "groningen.json"
    with pytest.raises(ValueError, match="reserve"):
        await live.capture_one(
            "groningen",
            output,
            60,
            120,
            strict_expert_budget=strict,
            finalization_reserve_ms=reserve,
        )
    assert not output.exists()
