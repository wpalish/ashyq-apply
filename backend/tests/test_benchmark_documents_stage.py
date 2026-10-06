"""D7: the benchmark's documents stage runs on its own clock after the decision stage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.adapters.fetching import FetchResult
from app.config import get_settings
from app.domain.enums import FetchOutcome, UserDecision
from evaluation.research import live
from evaluation.research.schema import Observation
from scripts import canary_discovery as canary


@pytest.fixture(autouse=True)
def _public_strict_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "exa_mcp")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    monkeypatch.setenv("UNIMATCH_RESPECT_ROBOTS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _Fetcher:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.tier_counts = {"browser": 0}

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.calls.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.CACHED, from_cache=True)


class _Query:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def filter(self, *args: Any) -> _Query:
        return self

    def __iter__(self) -> Any:
        return iter(self.rows)


class _Session:
    def __init__(self, results: list[Any]) -> None:
        self.results = results
        self.flushed = False

    def query(self, model: Any) -> _Query:
        return _Query(self.results if model.__name__ == "ProgramResultRow" else [])

    def flush(self) -> None:
        self.flushed = True


def _arrange(
    monkeypatch: pytest.MonkeyPatch, documents: Any
) -> tuple[list[str], list[Any], _Session]:
    calls: list[str] = []
    rows = [SimpleNamespace(user_decision=None)]
    session = _Session(rows)
    monkeypatch.setattr(canary.CanaryRunner, "_make_fetcher", lambda self: _Fetcher(calls))
    monkeypatch.setattr(canary, "page_outcomes", lambda run: [])

    async def decide(self: Any) -> None:
        await self._make_fetcher().get("https://rug.nl/decision")

    monkeypatch.setattr(canary.CanaryRunner, "run_to_decision", decide)
    monkeypatch.setattr(canary.CanaryRunner, "collect_documents", documents)

    async def run(*args: Any) -> dict[str, Any]:
        runner = object.__new__(canary.CanaryRunner)
        runner.session = session  # type: ignore[assignment]
        runner.run = SimpleNamespace(id="run")  # type: ignore[assignment]
        runner._candidates = []
        await runner.run_to_decision()
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", run)
    return calls, rows, session


@pytest.mark.asyncio
async def test_documents_stage_reads_outside_the_decision_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def documents(self: Any) -> int:
        await self._make_fetcher().get("https://rug.nl/documents")
        return 1

    calls, rows, session = _arrange(monkeypatch, documents)
    monkeypatch.setattr(live, "DOCUMENT_SECONDS", 30.0)
    output = tmp_path / "groningen.json"
    # A one-page decision budget the decision stage spends in full: the
    # documents read must not be refused by it, nor counted against it.
    await live.capture_one("groningen", output, 1, 120, strict_expert_budget=True)
    assert calls == ["https://rug.nl/decision", "https://rug.nl/documents"]
    assert rows[0].user_decision == UserDecision.APPROVED.value
    assert session.flushed
    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.http_fetches == 1
    assert observation.telemetry.document_reads == 1
    assert observation.telemetry.document_stop == "completed"
    budget = json.loads(output.with_suffix(".budget.json").read_text())
    assert budget["fetcher_calls"] == 1


@pytest.mark.asyncio
async def test_documents_stage_stops_on_its_own_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def documents(self: Any) -> int:
        await asyncio.sleep(5)
        return 0

    _arrange(monkeypatch, documents)
    monkeypatch.setattr(live, "DOCUMENT_SECONDS", 0.05)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 5, 120, strict_expert_budget=True)
    observation = Observation.model_validate_json(output.read_text())
    assert observation.telemetry.document_stop == "document_seconds_exhausted"
    assert observation.error is None


@pytest.mark.asyncio
async def test_no_documents_stage_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def documents(self: Any) -> int:
        raise AssertionError("the documents stage is off by default")

    _calls, rows, _session = _arrange(monkeypatch, documents)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 5, 120, strict_expert_budget=True)
    assert rows[0].user_decision is None
    assert Observation.model_validate_json(output.read_text()).telemetry.document_stop is None


@pytest.mark.asyncio
async def test_documents_stage_runs_after_the_decision_stage_runs_out_of_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def documents(self: Any) -> int:
        await self._make_fetcher().get("https://rug.nl/documents")
        return 1

    calls, rows, _session = _arrange(monkeypatch, documents)

    async def slow_decide(self: Any) -> None:
        await self._make_fetcher().get("https://rug.nl/decision")
        await asyncio.sleep(5)

    monkeypatch.setattr(canary.CanaryRunner, "run_to_decision", slow_decide)
    monkeypatch.setattr(live, "DOCUMENT_SECONDS", 30.0)
    output = tmp_path / "groningen.json"
    await live.capture_one("groningen", output, 5, 0.2)
    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert observation.telemetry.document_stop == "completed"
    assert "https://rug.nl/documents" in calls
    assert rows[0].user_decision == UserDecision.APPROVED.value
