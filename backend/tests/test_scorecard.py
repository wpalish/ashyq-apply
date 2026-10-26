"""The paired-run scorecard: per-label outcomes, stable changes, core, budget."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_known_core_counts_only_questions_the_corpus_knows():
    """Target 4: English is answered but unlabelled, tuition is known but missed."""
    cap = Capture.model_validate(capture([DEADLINE, TOEFL]))
    outcomes = scorecard.label_outcomes(dataset(), cap)
    assert scorecard.core_known(dataset(), outcomes) == {"uni": {"answered": 1, "known": 2}}


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


def test_the_dev4_draft_is_scored_per_case_by_its_programme_page(tmp_path):
    """dev4 labels only the programme page: a twin counts, and each case row says so."""
    data = Path(scorecard.__file__).parent / "data" / "dev4.draft1.json"
    cap = capture([])
    cap["observations"][0]["case_id"] = "ctu"
    cap["observations"][0]["programme_urls"] = [
        "https://fit.cvut.cz/en/study-programs/bachelor-study/informatics"
    ]
    cap["observations"].append(
        {"case_id": "itu", "programme_urls": ["https://www.itu.edu.tr/"], "telemetry": {}}
    )
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(cap))
    out = tmp_path / "card.json"
    args = [str(path), "--dataset", str(data), "--allow-drafts", "--out", str(out)]
    assert scorecard.main(args) == 0
    card = json.loads(out.read_text())
    rep = card["arms"]["run"]["repetitions"][0]
    # itu is a related programme (owner 2026-10-18): no exact gold page.
    assert rep["programme"] == {"ctu": "hit", "itu": "unlabelled"}
    assert rep["metrics"]["programme_page_recall"]["numerator"] == 1
    assert "| ctu | unknown (0/0 failed) | hit | 0/1 |" in scorecard.render(card)


# --- H-1: the replay target is judged on discovery's misses -------------------


def replayed(total: int, discovery: int | None = None, *, knockout: bool = False) -> dict:
    """A one-case replay capture; ``discovery=None`` is a capture made before H-1."""
    cap = capture([DEADLINE])
    cap["config"]["search_provider"] = "recorded"
    telemetry = cap["observations"][0]["telemetry"]
    telemetry.update(recorded_search_hits=4, recorded_search_misses=total)
    if discovery is not None:
        rest = total - discovery
        telemetry.update(
            recorded_search_misses_discovery=discovery,
            recorded_search_misses_topic=rest // 2,
            recorded_search_misses_scholarship=rest - rest // 2,
            recorded_search_misses_identity=0,
        )
    if knockout:
        telemetry.update(knockout_gold_urls=1, knockout_refused=1)
    return cap


def replay_rows(card: dict) -> dict:
    return {r["arm"]: r for r in card["targets"] if r["metric"] == "recorded_search_misses"}


def test_scholarship_and_topic_misses_do_not_read_as_changed_queries(tmp_path):
    # dev3's A/A: 24 -> 26 in the total from reads, not from a discovery query.
    run = write_run(
        tmp_path / "run",
        {"off": [replayed(24, 3), replayed(23, 3)], "on": [replayed(26, 3), replayed(23, 3)]},
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    rep = card["arms"]["on"]["repetitions"][0]["recorded_search"]
    assert rep == {
        "hits": 4,
        "misses": 26,
        "cases_with_miss": 1,
        "misses_discovery": 3,
        "misses_topic": 11,
        "misses_scholarship": 12,
        "misses_identity": 0,
    }
    assert replay_rows(card)["on"] == {
        "arm": "on",
        "metric": "recorded_search_misses",
        "worst": 3,
        "target": "<= 3 discovery",
        "met": True,
    }
    text = scorecard.render(card)
    assert "WARNING" not in text
    assert "on#1 26 (discovery 3, topic 11, scholarship 12, identity 0)" in text
    assert "Judged on discovery's misses only" in text
    summary = scorecard.render_summary(scorecard.summarize(card))
    assert "recorded search answered/missed | 4/24 | 4/23 | 4/26 | 4/23" in summary
    assert "discovery/topic/scholarship/identity | 3/10/11/0 | 3/10/10/0 | 3/11/12/0" in summary


def test_one_more_discovery_miss_than_the_off_arm_is_a_changed_query(tmp_path, capsys):
    run = write_run(
        tmp_path / "run",
        {"off": [replayed(9, 0), replayed(9, 0)], "on": [replayed(9, 0), replayed(9, 1)]},
    )
    corpus = tmp_path / "corpus.json"
    corpus.write_text(dataset().model_dump_json())
    out = tmp_path / "c.json"
    assert scorecard.main([str(run), "--dataset", str(corpus), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "WARNING: THE QUERIES CHANGED" in printed
    assert "on#2 sent discovery requests" in printed
    assert "| on | recorded_search_misses | 1 | <= 0 discovery | NO |" in printed
    rows = replay_rows(json.loads(out.read_text()))
    assert rows["off"]["met"] is True and rows["on"]["met"] is False


def test_the_knockout_arm_notes_its_unrecorded_second_pass(tmp_path):
    run = write_run(
        tmp_path / "run",
        {"off": [replayed(9, 0)], "on": [replayed(12, 3, knockout=True)]},
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    on = card["arms"]["on"]["repetitions"][0]["recorded_search"]
    off = card["arms"]["off"]["repetitions"][0]["recorded_search"]
    assert on["knockout_cases_discovery_miss"] == 1
    assert "knockout_cases_discovery_miss" not in off
    for text in (scorecard.render(card), scorecard.render_summary(scorecard.summarize(card))):
        assert "on#1 knockout: second pass unrecorded on 1 cases" in text
        assert "on#1 sent discovery requests" in text
    assert replay_rows(card)["on"]["worst"] == 3


def test_captures_made_before_h1_still_score_on_the_total(tmp_path):
    run = write_run(
        tmp_path / "run",
        {"off": [replayed(9), replayed(9)], "on": [replayed(9), replayed(10)]},
    )
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert card["arms"]["on"]["repetitions"][0]["recorded_search"] == {
        "hits": 4,
        "misses": 9,
        "cases_with_miss": 1,
    }
    assert replay_rows(card)["on"] == {
        "arm": "on",
        "metric": "recorded_search_misses",
        "worst": 10,
        "target": "<= 9",
        "met": False,
    }
    text = scorecard.render(card)
    assert "Judged on discovery" not in text and "on#2 sent requests" in text
    assert "discovery/topic" not in scorecard.render_summary(scorecard.summarize(card))


def test_a_run_mixing_old_and_new_captures_is_judged_on_the_total(tmp_path):
    # Never compare an old column's total with a new column's discovery count.
    run = write_run(tmp_path / "run", {"off": [replayed(9)], "on": [replayed(9, 0)]})
    card = scorecard.build(dataset(), scorecard.load_run(run))
    assert scorecard.recorded_judged_on(card["arms"]) == "misses"
    assert replay_rows(card)["on"] == {
        "arm": "on",
        "metric": "recorded_search_misses",
        "worst": 9,
        "target": "<= 9",
        "met": True,
    }
