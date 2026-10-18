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
    assert rep["programme"] == {"ctu": "hit", "itu": "miss"}
    assert rep["metrics"]["programme_page_recall"]["numerator"] == 1
    assert "| ctu | unknown (0/0 failed) | hit | 0/1 |" in scorecard.render(card)
