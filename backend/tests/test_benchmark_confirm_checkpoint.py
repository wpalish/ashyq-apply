"""The confirm checkpoint persists what discovery had confirmed, and its trace.

Structural analysis 2026-10-18, section 4.2: UBC read and confirmed its
programme page, was killed by the wall clock in search, and reported
``programme_urls == []`` with no trace at all. A kill that skips the
``TimeoutError`` branch (the parent's SIGKILL) left nothing either.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, PageCategory
from app.config import get_settings
from evaluation.research import live
from evaluation.research.schema import Observation
from scripts import canary_discovery as canary

PROGRAMME = "https://you.ubc.ca/programs/computer-science/"
WALKED = "https://you.ubc.ca/programs/computer-science-bsc/"


@pytest.fixture(autouse=True)
def _offline_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _arrange(
    monkeypatch: pytest.MonkeyPatch, output: Path, *, finish: bool, seen: dict[str, Any]
) -> None:
    """Discovery confirms one page, the walker adds one, then the run stalls or finishes."""

    async def confirm(adapter: Any, selected: Any, ranked: Any, trace: Any, profile: Any) -> None:
        selected[PageCategory.PROGRAM_PAGE] = [PROGRAMME]

    async def walk(adapter: Any, entry: Any, selected: Any, trace: Any, profile: Any) -> None:
        selected[PageCategory.PROGRAM_PAGE].append(WALKED)

    monkeypatch.setattr(LiveDiscoveryAdapter, "_confirm_programs", confirm)
    monkeypatch.setattr(LiveDiscoveryAdapter, "_walk_catalogs", walk)

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        trace = DiscoveryTrace(institution="University of British Columbia", domain="ubc.ca")
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        selected[PageCategory.PROGRAM_PAGE] = ["https://you.ubc.ca/open-day/"]
        ranked: dict[str, list[tuple[int, str]]] = {PageCategory.PROGRAM_PAGE: []}
        await LiveDiscoveryAdapter._confirm_programs(None, selected, ranked, trace, None)  # type: ignore[arg-type]
        # What a SIGKILL right here would leave on disk.
        seen["after_confirm"] = Observation.model_validate_json(output.read_text())
        seen["trace_after_confirm"] = json.loads(output.with_suffix(".trace.json").read_text())
        await LiveDiscoveryAdapter._walk_catalogs(None, {}, selected, trace, None)  # type: ignore[arg-type]
        if not finish:
            await asyncio.sleep(5)
        return {"institutions": [{"programs": [PROGRAMME, WALKED]}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", run)


@pytest.mark.asyncio
async def test_a_kill_after_the_confirm_checkpoint_keeps_its_pages_and_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ubc.json"
    seen: dict[str, Any] = {}
    _arrange(monkeypatch, output, finish=False, seen=seen)
    await live.capture_one("ubc", output, 5, 0.3)

    # Already on disk at the confirm checkpoint, before any kill.
    assert [str(u) for u in seen["after_confirm"].programme_urls] == [PROGRAMME]
    assert seen["after_confirm"].error == "CAPTURE_IN_PROGRESS"
    assert seen["trace_after_confirm"]["checkpoint"] == "confirm"
    assert seen["trace_after_confirm"]["programme_urls"] == [PROGRAMME]

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert [str(u) for u in observation.programme_urls] == [PROGRAMME, WALKED]
    partial = json.loads(output.with_suffix(".trace.json").read_text())
    assert partial["partial"] is True
    assert partial["checkpoint"] == "timeout"
    assert partial["programme_urls"] == [PROGRAMME, WALKED]
    assert partial["discovery_trace"]["domain"] == "ubc.ca"
    assert not output.with_suffix(".raw.json").exists()


@pytest.mark.asyncio
async def test_a_completed_run_keeps_only_the_raw_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ubc.json"
    _arrange(monkeypatch, output, finish=True, seen={})
    await live.capture_one("ubc", output, 5, 5)

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error is None
    assert [str(u) for u in observation.programme_urls] == [PROGRAMME, WALKED]
    assert output.with_suffix(".raw.json").exists()
    assert not output.with_suffix(".trace.json").exists()


def test_the_checkpoint_pages_stand_in_only_when_the_runner_has_none() -> None:
    assert live.timeout_programme_urls([], [], [PROGRAMME]) == [PROGRAMME]
    assert live.timeout_programme_urls([], [], []) == []
