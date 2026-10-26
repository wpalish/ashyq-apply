"""F5: a TOEFL iBT or Duolingo minimum is scored under the corpus's own key.

Until 2026-10-18 ``toefl_min_total`` and ``duolingo_min`` mapped to
``unmapped.*`` and could never meet ``english_evidence.toefl_ibt.minimum`` /
``english_evidence.duolingo.minimum``: UM's correct TOEFL 46 was a miss.
"""

from __future__ import annotations

from typing import Any

from evaluation.research import scorecard
from evaluation.research.mapping import normalize_claim
from evaluation.research.schema import Capture, Dataset

SCOPE = {"university": "Example University"}


def _evidence(excerpt: str) -> dict[str, Any]:
    return {
        "url": "https://uni.edu/english",
        "excerpt": excerpt,
        "scope": SCOPE,
        "accessed_on": "2026-10-18",
        "source_type": "official",
    }


def _dataset(labels: list[dict[str, Any]]) -> Dataset:
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
                    "programme_evidence": [_evidence("BSc Computer Science")],
                    "labels": labels,
                    "review": {
                        "status": "human_verified",
                        "prepared_by": "test",
                        "reviewer": "test",
                        "verified_on": "2026-10-18",
                        "notes": "test",
                    },
                }
            ],
        }
    )


def _capture(predictions: list[dict[str, Any]]) -> Capture:
    return Capture.model_validate(
        {
            "pipeline_sha": "abc",
            "captured_at": "20261018T000000Z",
            "mode": "live",
            "config": {},
            "observations": [{"case_id": "uni", "predictions": predictions}],
        }
    )


def test_toefl_and_duolingo_minimums_map_to_the_english_evidence_keys():
    raw: dict[str, Any] = {"normalized_value": 46}
    assert normalize_claim("toefl_min_total", raw)[:2] == ("english_evidence.toefl_ibt.minimum", 46)
    raw = {"normalized_value": 105}
    assert normalize_claim("duolingo_min", raw)[:2] == ("english_evidence.duolingo.minimum", 105)
    # IELTS keeps its own keys; nothing else moved.
    assert normalize_claim("ielts_min_overall", {"normalized_value": 6.5})[0] == "ielts.overall"


def test_a_correct_toefl_minimum_answers_the_english_core_question():
    """The DoD's english question is "English test minimum", whichever test states it."""
    labels = [
        {"key": "ielts.overall", "status": "unknown"},
        {
            "key": "english_evidence.toefl_ibt.minimum",
            "status": "known",
            "value": 46,
            "evidence": [_evidence("TOEFL iBT 46")],
        },
    ]
    key, value, _programme, _degree = normalize_claim("toefl_min_total", {"normalized_value": 46})
    capture = _capture([{"key": key, "value": value, "evidence": _evidence("TOEFL iBT 46")}])
    dataset = _dataset(labels)

    outcomes = scorecard.label_outcomes(dataset, capture)
    assert [(x["key"], x["outcome"]) for x in outcomes["labels"]] == [
        ("english_evidence.toefl_ibt.minimum", "hit")
    ]
    assert outcomes["unlabelled"] == []
    assert scorecard.core_known(dataset, outcomes) == {"uni": {"answered": 1, "known": 1}}
    assert scorecard.core_coverage(capture) == {"uni": ["english"]}
