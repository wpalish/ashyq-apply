"""Per-stage clock and the first query's time reach the capture's telemetry.

Structural analysis 2026-10-18, section 4.1: the funnel had to be rebuilt from
the case log because the capture said nothing about where the clock went.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.config import get_settings
from evaluation.research import scorecard
from evaluation.research.live import capture_one, trace_stage_telemetry
from evaluation.research.schema import Capture, Observation


@pytest.fixture(autouse=True)
def _offline_configuration(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _patch_canary(monkeypatch: pytest.MonkeyPatch, trace: dict[str, Any] | None, search: bool):
    from app.adapters.search.exa import ExaSearchProvider
    from scripts import canary_discovery as canary

    async def quiet_search(provider: Any, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    monkeypatch.setattr(ExaSearchProvider, "search", quiet_search)

    async def fake_canary(selector: Any, verbose: bool) -> dict[str, Any]:
        await asyncio.sleep(0.15)
        if search:
            await ExaSearchProvider.search(None, query="computer science")  # type: ignore[arg-type]
        row: dict[str, Any] = {"programs": []}
        if trace is not None:
            row["discovery_trace"] = trace
        return {"institutions": [row], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)


@pytest.mark.asyncio
async def test_the_trace_stage_clock_and_the_first_query_are_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trace = {
        "stage_seconds": {"sitemaps": 8.04, "confirm": 0.0, "search": 10.2},
        "stage_reads": {"sitemaps": 3, "confirm": 0, "search": 3},
        "t_first_query": 99.0,
    }
    _patch_canary(monkeypatch, trace, search=True)
    output = tmp_path / "groningen.json"
    await capture_one("groningen", output, 4)

    telemetry = Observation.model_validate_json(output.read_text()).telemetry
    assert telemetry.stage_seconds == {"sitemaps": 8.0, "confirm": 0.0, "search": 10.2}
    assert telemetry.stage_reads == {"sitemaps": 3, "confirm": 0, "search": 3}
    # The harness's own clock wins over the trace's: it is the case clock.
    assert telemetry.t_first_query is not None
    assert 0.1 <= telemetry.t_first_query < 5


@pytest.mark.asyncio
async def test_absent_stage_fields_stay_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_canary(monkeypatch, {"selected": {}}, search=False)
    output = tmp_path / "groningen.json"
    await capture_one("groningen", output, 4)

    telemetry = Observation.model_validate_json(output.read_text()).telemetry
    assert telemetry.t_first_query is None
    assert telemetry.stage_seconds is None
    assert telemetry.stage_reads is None


def test_a_malformed_trace_field_is_dropped_not_guessed() -> None:
    assert trace_stage_telemetry(None) == {}
    assert trace_stage_telemetry({"stage_seconds": {"search": -1}}) == {}
    assert trace_stage_telemetry({"stage_reads": {"search": 2.5}}) == {}
    assert trace_stage_telemetry({"stage_reads": {"search": True}}) == {}
    assert trace_stage_telemetry({"t_first_query": "12"}) == {}
    assert trace_stage_telemetry({"t_first_query": 12.04, "stage_reads": {"walker": 7}}) == {
        "t_first_query": 12.0,
        "stage_reads": {"walker": 7},
    }


def _capture(telemetry: dict[str, Any]) -> Capture:
    return Capture.model_validate(
        {
            "pipeline_sha": "abc",
            "captured_at": "20261018T000000Z",
            "mode": "live",
            "config": {},
            "observations": [{"case_id": "uni", "telemetry": telemetry}],
        }
    )


def test_the_scorecard_shows_the_first_query_only_where_it_was_recorded() -> None:
    base = {"search_calls": 3, "http_fetches": 20, "latency_seconds": 30.0}
    assert "t_first_query" not in scorecard.cost(_capture(base))["uni"]
    assert scorecard.cost(_capture({**base, "t_first_query": 60.0}))["uni"]["t_first_query"] == 60.0

    def per_case_header(capture: Capture) -> str:
        rep = {
            "metrics": {
                m: {"numerator": 0, "denominator": 0, "value": None} for m in scorecard._SHOWN
            },
            "outcomes": {"labels": [], "wrong_claims": []},
            "core": {"uni": []},
            "core_known": {"uni": {"answered": 0, "known": 0}},
            "cost": scorecard.cost(capture),
        }
        card = {"dataset_version": "t", "arms": {"run": {"repetitions": [rep], "access": {}}}}
        card["targets"] = []
        text = scorecard.render(card)
        return text.split("## Per case")[1]

    assert "1st query s" not in per_case_header(_capture(base))
    shown = per_case_header(_capture({**base, "t_first_query": 60.0}))
    assert "1st query s" in shown
    assert "| 30.0 | 60.0 |" in shown
