"""``--count-timeouts-over-budget``: a case the clock ended is over the latency budget.

Read budget analysis 2026-10-18 §1: the harness kills a case at its wall clock,
so ``latency_seconds`` never exceeds 120 and Imperial, UNSW, USP and UCT ended
at 115-120 s "within budget" while unfinished. The owner has not decided
whether that counts; the option is off by default and changes nothing then.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.research import scorecard
from evaluation.research.schema import Capture
from tests.test_scorecard import DEADLINE, capture, dataset, write_run


def _killed(
    predictions: list[dict],
    *,
    seconds: float = 115.0,
    error: str = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED",
) -> dict:
    raw = capture(predictions)
    observation = raw["observations"][0]
    observation["error"] = error
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


# --- HC-1: an older capture's case the parent's kill left in progress ---------


def test_a_case_left_in_progress_is_killed_by_the_clock() -> None:
    cap = Capture.model_validate(_killed([], seconds=119.0, error="CAPTURE_IN_PROGRESS"))
    row = scorecard.cost(cap)["uni"]
    assert row["killed_by_clock"] == 1
    assert row["over_budget"] == 1
    assert row["capture_in_progress"] == 1


def test_off_a_case_left_in_progress_is_still_marked_but_not_over_budget() -> None:
    cap = Capture.model_validate(_killed([], seconds=119.0, error="CAPTURE_IN_PROGRESS"))
    row = scorecard.cost(cap, count_timeouts=False)["uni"]
    assert row["over_budget"] == 0
    assert "killed_by_clock" not in row
    assert row["capture_in_progress"] == 1


def test_a_case_the_child_stopped_is_not_marked_in_progress() -> None:
    row = scorecard.cost(Capture.model_validate(_killed([DEADLINE])))["uni"]
    assert "capture_in_progress" not in row


def test_the_summary_says_how_many_cases_were_left_in_progress(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    left = _killed([], seconds=119.0, error="CAPTURE_IN_PROGRESS")
    run = write_run(tmp_path / "run", {"off": [capture([DEADLINE])], "on": [left]})
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())

    def card(*extra: str) -> tuple[dict, str]:
        out = tmp_path / f"card{len(extra)}.json"
        capsys.readouterr()
        assert scorecard.main([str(run), "--dataset", str(corpus), "--out", str(out), *extra]) == 0
        return json.loads(out.read_text()), capsys.readouterr().out

    full, full_text = card()
    assert scorecard.IN_PROGRESS_LABEL in full_text
    assert f"| {scorecard.IN_PROGRESS_LABEL} | 0 | 1 |" in full_text
    over = {r["arm"]: r["worst"] for r in full["targets"] if r["metric"] == "cases_over_budget"}
    assert over == {"off": 0, "on": 1}

    summary, summary_text = card("--summary-only")
    reps = {name: arm["repetitions"][0] for name, arm in summary["arms"].items()}
    assert reps["on"]["cases_left_in_progress"] == 1
    assert "cases_left_in_progress" not in reps["off"]
    assert f"| {scorecard.IN_PROGRESS_LABEL} | 0 | 1 |" in summary_text


def test_a_run_with_no_case_left_in_progress_keeps_its_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = write_run(tmp_path / "run", {"off": [capture([DEADLINE])], "on": [_killed([DEADLINE])]})
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())
    for extra in ([], ["--summary-only"]):
        out = tmp_path / f"card{len(extra)}.json"
        capsys.readouterr()
        assert scorecard.main([str(run), "--dataset", str(corpus), "--out", str(out), *extra]) == 0
        assert scorecard.IN_PROGRESS_LABEL not in capsys.readouterr().out
        assert "in_progress" not in out.read_text()
