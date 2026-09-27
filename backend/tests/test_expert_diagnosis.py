"""Do not infer later pipeline stages from a retrieval rank."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.research.expert.diagnose import diagnose
from evaluation.research.expert.hypotheses import validate_hypotheses

ROOT = Path(__file__).resolve().parents[1] / "evaluation/research"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def real_report() -> dict:
    return diagnose(
        load("data/ground_truth.reviewed.json"),
        load("baseline/capture.json"),
        load("baseline/search_probe.exa.hop.json"),
    )


def test_pilot_cases_distinguish_legacy_failure_from_new_probe_rank() -> None:
    records = {item["case_id"]: item for item in real_report()["records"]}
    assert len(records) == 10
    assert records["kaist"]["legacy_stage"] == "legacy_gold_absent_with_failure"
    assert records["kaist"]["probe_gold_position"] == 30
    assert records["aalto"]["legacy_stage"] == "legacy_gold_absent_with_failure"
    assert records["aalto"]["probe_gold_position"] == 17
    assert records["toronto"]["probe_gold_position"] == 4
    assert records["toronto"]["probe_top_identity"] == "needs_review"
    assert all("does not prove a fetch" in item["note"] for item in records.values())


def test_published_diagnosis_is_reproducible_from_frozen_inputs() -> None:
    assert real_report() == load("expert/data/diagnosis.2026-09-21.json")


def test_missing_rank_list_remains_unmeasured() -> None:
    dataset = {
        "version": "x",
        "cases": [{"id": "x", "programme_urls": ["https://u.test/cs"], "labels": []}],
    }
    capture = {"pipeline_sha": "abc1234", "observations": [{"case_id": "x", "ranked_urls": None}]}
    probe = {"probed_at": "now", "cases": []}
    record = diagnose(dataset, capture, probe)["records"][0]
    assert record["legacy_stage"] == "legacy_queue_unmeasured"
    assert record["probe_gold_position"] is None


def test_absent_signed_programme_is_not_a_retrieval_failure() -> None:
    dataset = {"version": "x", "cases": [{"id": "x", "programme_urls": [], "labels": []}]}
    capture = {"pipeline_sha": "abc1234", "observations": [{"case_id": "x", "ranked_urls": []}]}
    probe = {"probed_at": "now", "cases": []}
    record = diagnose(dataset, capture, probe)["records"][0]
    assert record["legacy_stage"] == "programme_truth_unadjudicable"


def test_registry_needs_case_provenance_and_cannot_self_promote() -> None:
    registry = load("expert/data/hypotheses.json")
    validate_hypotheses(registry, real_report())
    assert {item["status"] for item in registry["hypotheses"]} == {"candidate"}

    registry["hypotheses"][0]["status"] = "promoted"
    with pytest.raises(ValueError, match="validation artifact"):
        validate_hypotheses(registry, real_report())
