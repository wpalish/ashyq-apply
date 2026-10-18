"""``--count-timeouts-over-budget``: a case the clock ended is over the latency budget.

Read budget analysis 2026-10-18 §1: the harness kills a case at its wall clock,
so ``latency_seconds`` never exceeds 120 and Imperial, UNSW, USP and UCT ended
at 115-120 s "within budget" while unfinished. The owner has not decided
whether that counts; the option is off by default and changes nothing then.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.research import scorecard
from evaluation.research.schema import Capture
from tests.test_scorecard import DEADLINE, capture, dataset, write_run


def _killed(predictions: list[dict], *, seconds: float = 115.0) -> dict:
    raw = capture(predictions)
    observation = raw["observations"][0]
    observation["error"] = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    observation["telemetry"]["latency_seconds"] = seconds
    return raw


def test_off_a_clock_killed_case_stays_within_budget() -> None:
    row = scorecard.cost(Capture.model_validate(_killed([DEADLINE])), count_timeouts=False)["uni"]
    assert row["over_budget"] == 0
    assert "killed_by_clock" not in row


def test_on_a_clock_killed_case_is_over_the_latency_budget() -> None:
    cap = Capture.model_validate(_killed([DEADLINE]))
    row = scorecard.cost(cap, count_timeouts=True)["uni"]
    assert row["over_budget"] == 1
    assert row["killed_by_clock"] == 1


def test_on_a_finished_case_is_unchanged() -> None:
    cap = Capture.model_validate(capture([DEADLINE]))
    assert scorecard.cost(cap, count_timeouts=True) == scorecard.cost(cap)


def test_on_a_killed_case_already_over_on_reads_counts_each_limit_once() -> None:
    raw = _killed([DEADLINE], seconds=120.5)
    raw["observations"][0]["telemetry"]["http_fetches"] = 66
    row = scorecard.cost(Capture.model_validate(raw), count_timeouts=True)["uni"]
    assert row["over_budget"] == 2


def test_the_option_reaches_the_target_through_the_cli(tmp_path: Path) -> None:
    run = write_run(tmp_path / "run", {"off": [capture([DEADLINE])], "on": [_killed([DEADLINE])]})
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())

    def over(*extra: str) -> dict[str, int]:
        out = tmp_path / f"card{len(extra)}.json"
        assert scorecard.main([str(run), "--dataset", str(corpus), "--out", str(out), *extra]) == 0
        card = json.loads(out.read_text())
        return {r["arm"]: r["worst"] for r in card["targets"] if r["metric"] == "cases_over_budget"}

    assert over("--no-count-timeouts-over-budget") == {"off": 0, "on": 0}
    assert over() == {"off": 0, "on": 1}
