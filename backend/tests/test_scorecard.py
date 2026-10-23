"""The paired-run scorecard: per-label outcomes, stable changes, core, budget."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.research import scorecard
from evaluation.research.metrics import score
from evaluation.research.schema import Capture, Dataset

SCOPE = {"university": "Example University"}


def evidence(url: str, excerpt: str) -> dict:
    return {
        "url": url,
        "excerpt": excerpt,
        "scope": SCOPE,
        "accessed_on": "2026-10-05",
        "source_type": "official",
    }


def dataset() -> Dataset:
    return Dataset.model_validate(
        {
            "version": "test",
            "split": "development",
            "cases": [
                {
                    "id": "uni",
                    "dataset_version": "test",
                    "university": "Example University",
                    "domain": "uni.edu",
                    "country": "Nowhere",
                    "site_types": ["static"],
                    "request": SCOPE,
                    "programme_urls": ["https://uni.edu/cs"],
                    "programme_status": "known",
                    "programme_evidence": [evidence("https://uni.edu/cs", "BSc Computer Science")],
                    "labels": [
                        {
                            "key": "deadline",
                            "status": "known",
                            "value": "2027-05-01",
                            "evidence": [evidence("https://uni.edu/apply", "Deadline 1 May 2027")],
                        },
                        {
                            "key": "tuition",
                            "status": "known",
                            "value": {"amount": 100, "currency": "EUR"},
                            "evidence": [evidence("https://uni.edu/fees", "EUR 100 per year")],
                        },
                        {"key": "ielts.overall", "status": "unknown"},
                    ],
                    "review": {
                        "status": "human_verified",
                        "prepared_by": "test",
                        "reviewer": "test",
                        "verified_on": "2026-10-05",
                        "notes": "test",
                    },
                }
            ],
        }
    )


DEADLINE = {
    "key": "deadline",
    "value": "2027-05-01",
    "evidence": evidence("https://uni.edu/apply", "Deadline 1 May 2027"),
}
TUITION_RIGHT = {
    "key": "tuition",
    "value": {"amount": 100, "currency": "EUR"},
    "evidence": evidence("https://uni.edu/fees", "EUR 100 per year"),
}
TUITION_WRONG = {
    "key": "tuition",
    "value": {"amount": 200, "currency": "EUR"},
    "evidence": evidence("https://uni.edu/fees", "EUR 200 per year"),
}
TOEFL = {
    "key": "unmapped.toefl_min_total",
    "value": 90,
    "evidence": evidence("https://uni.edu/english", "TOEFL iBT 90"),
}


def capture(predictions: list[dict], *, queries: int = 3, reads: int = 20) -> dict:
    return {
        "pipeline_sha": "abc",
        "captured_at": "20261005T000000Z",
        "mode": "live",
        "config": {},
        "observations": [
            {
                "case_id": "uni",
                "programme_urls": ["https://uni.edu/cs"],
                "predictions": predictions,
                "telemetry": {
                    "search_calls": queries,
                    "http_fetches": reads,
                    "latency_seconds": 30.0,
                },
            }
        ],
    }


def write_run(root: Path, arms: dict[str, list[dict]]) -> Path:
    for arm, reps in arms.items():
        for i, rep in enumerate(reps, 1):
            target = root / f"uni-{arm}" / f"20261005T00000{i}Z"
            target.mkdir(parents=True)
            (target / "capture.json").write_text(json.dumps(rep))
    return root


def test_label_outcomes_name_hit_missed_wrong_and_unlabelled():
    cap = Capture.model_validate(capture([DEADLINE, TUITION_WRONG, TOEFL]))
    out = scorecard.label_outcomes(dataset(), cap)
    outcomes = {x["key"]: x["outcome"] for x in out["labels"]}
    assert outcomes == {"deadline": "hit", "tuition": "wrong_value"}
    assert [w["key"] for w in out["wrong_claims"]] == ["tuition"]
    assert out["wrong_claims"][0]["why"] == "wrong_value"
    assert [u["key"] for u in out["unlabelled"]] == ["unmapped.toefl_min_total"]


def test_outcomes_agree_with_the_official_scorer():
    """A label is a hit exactly when the scorer credits it."""
    cap = Capture.model_validate(capture([DEADLINE, TUITION_WRONG, TOEFL]))
    hits = sum(
        1 for x in scorecard.label_outcomes(dataset(), cap)["labels"] if x["outcome"] == "hit"
    )
    assert score(dataset(), cap)["metrics"]["claim_recall"]["numerator"] == hits


def test_core_questions_count_unmapped_answers():
    cap = Capture.model_validate(capture([DEADLINE, TOEFL]))
    assert scorecard.core_coverage(cap) == {"uni": ["english", "deadline"]}


def test_a_label_is_gained_only_when_every_repetition_agrees(tmp_path):
    run = write_run(
        tmp_path,
        {
            "off": [capture([TUITION_RIGHT]), capture([])],
            "on": [capture([DEADLINE]), capture([DEADLINE])],
        },
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert card["changes"]["gained"] == ["uni:deadline"]
    assert card["changes"]["lost"] == []
    # Tuition was found by one off repetition only: not a loss, unstable.
    assert card["changes"]["unstable"] == ["uni:tuition"]


def test_budget_and_targets_are_judged_on_the_worst_repetition(tmp_path):
    run = write_run(
        tmp_path,
        {
            "off": [capture([DEADLINE]), capture([DEADLINE])],
            "on": [capture([DEADLINE], queries=7), capture([DEADLINE, TUITION_WRONG])],
        },
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    rows = {(r["arm"], r["metric"]): r for r in card["targets"]}
    assert rows[("off", "cases_over_budget")]["met"] is True
    assert rows[("on", "cases_over_budget")]["worst"] == 1
    assert rows[("on", "claim_precision")]["worst"] == 0.5
    assert rows[("on", "claim_precision")]["met"] is False
    text = scorecard.render(card)
    assert "| claim_recall | 1/2 | 1/2 | 1/2 | 1/2 |" in text
    assert "tuition" in text


def test_a_single_capture_is_scored_as_one_arm(tmp_path):
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(capture([DEADLINE])))
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())
    out = tmp_path / "card.json"
    assert scorecard.main([str(path), "--dataset", str(corpus), "--out", str(out)]) == 0
    card = json.loads(out.read_text())
    assert list(card["arms"]) == ["run"]


def test_budget_checks_do_not_round_an_overrun_into_a_pass():
    data = capture([])
    data["observations"][0]["telemetry"]["latency_seconds"] = 120.004
    cap = Capture.model_validate(data)
    card = scorecard.build(dataset(), {"run": scorecard.Arm("run", [cap])})
    assert card["arms"]["run"]["repetitions"][0]["cost"]["uni"]["latency_seconds"] == 120.004
    budget = next(r for r in card["targets"] if r["metric"] == "cases_over_budget")
    assert budget["worst"] == 1
    assert budget["met"] is False


def test_missing_telemetry_cannot_establish_a_pass_but_zero_can():
    data = capture([], queries=0, reads=0)
    data["observations"][0]["telemetry"]["latency_seconds"] = 0.0
    cap = Capture.model_validate(data)
    assert scorecard.cost(cap)["uni"]["missing_telemetry"] == []
    assert scorecard.cost(cap)["uni"]["latency_seconds"] == 0.0
    cap.observations[0].telemetry.search_calls = None
    card = scorecard.build(dataset(), {"run": scorecard.Arm("run", [cap])})
    budget = next(r for r in card["targets"] if r["metric"] == "cases_over_budget")
    assert budget["met"] is None
    assert budget["unknown_cases"] == 1
    assert "| cases_over_budget | 0 | == 0 | unknown |" in scorecard.render(card)


def test_a_missing_repetition_cannot_establish_a_stable_gain(tmp_path):
    run = write_run(tmp_path, {"off": [capture([])], "on": [capture([DEADLINE])] * 2})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert card["measurement_status"] == "incomplete"
    assert card["arms"]["off"]["completeness"]["missing"] == [{"case": "uni", "repetition": 2}]
    assert card["changes"]["gained"] == []
    assert card["changes"]["unassessed_cases"] == ["uni"]
    assert "off#2 uni: missing" in scorecard.render(card)


def test_a_wholly_missing_arm_is_visible_and_renderable(tmp_path):
    run = write_run(tmp_path, {"off": [capture([DEADLINE])] * 2})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert len(card["arms"]["on"]["completeness"]["missing"]) == 2
    assert card["changes"]["lost"] == []
    assert "on#1 uni: missing" in scorecard.render(card)


def test_an_unfinished_capture_is_not_a_measured_zero(tmp_path):
    pending = capture([])
    pending["observations"][0]["error"] = "CAPTURE_IN_PROGRESS"
    run = write_run(tmp_path, {"off": [capture([]), pending], "on": [capture([DEADLINE])] * 2})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert card["changes"]["gained"] == []
    assert card["arms"]["off"]["completeness"]["unfinished"] == [{"case": "uni", "repetition": 2}]
    assert card["measurement_status"] == "incomplete"


def test_a_finalized_budget_stop_remains_a_measured_outcome(tmp_path):
    stopped = capture([])
    stopped["observations"][0]["error"] = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    run = write_run(tmp_path, {"off": [stopped] * 2, "on": [capture([DEADLINE])] * 2})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert card["measurement_status"] == "complete"
    assert card["changes"]["gained"] == ["uni:deadline"]


def test_a_requested_case_with_no_files_is_still_unobserved(tmp_path):
    run = write_run(tmp_path, {"off": [capture([])] * 2, "on": [capture([DEADLINE])] * 2})
    card = scorecard.build(dataset(), scorecard.load_run(run, expected_cases={"uni", "absent"}))
    assert card["arms"]["on"]["completeness"]["missing"] == [
        {"case": "absent", "repetition": 1},
        {"case": "absent", "repetition": 2},
    ]
    assert card["measurement_status"] == "incomplete"
    # The fully observed case still has its valid per-case stable gain.
    assert card["changes"]["gained"] == ["uni:deadline"]


def test_an_empty_case_directory_is_not_omitted(tmp_path):
    run = write_run(tmp_path, {"off": [capture([])] * 2, "on": [capture([])] * 2})
    (run / "absent-on").mkdir()
    assert "absent" in scorecard.load_run(run)["off"].expected_cases


def test_swapped_or_duplicated_case_rows_cannot_be_scored(tmp_path):
    wrong_case = capture([DEADLINE])
    wrong_case["observations"][0]["case_id"] = "another"
    run = write_run(tmp_path, {"off": [capture([])] * 2, "on": [wrong_case] * 2})
    with pytest.raises(ValueError, match="do not match directory case"):
        scorecard.load_run(run)
    with pytest.raises(ValueError, match="outside the requested cohort"):
        scorecard.load_run(run, expected_cases={"another"})
