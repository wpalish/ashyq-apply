"""The expert sees the learner's state, never the sealed answer fields."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.research.expert.models import ExpertTrace, validate_trace
from evaluation.research.expert.packet import build_packet, digest

ROOT = Path(__file__).resolve().parents[1] / "evaluation/research"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_packet_copies_only_public_case_fields_and_baseline_observation() -> None:
    dataset = load("data/ground_truth.reviewed.json")
    capture = load("baseline/capture.json")
    packet = build_packet(dataset, capture, ["kaist"])
    case = packet["cases"][0]

    assert set(case) == {"case_id", "university", "domain", "request", "baseline"}
    assert case["case_id"] == "kaist"
    assert case["request"]["field"] == "computer science"
    assert case["baseline"]["error"] is not None
    assert set(case["baseline"]) == {
        "ranked_urls",
        "programme_urls",
        "prediction_count",
        "error",
        "telemetry",
    }
    assert packet["baseline_budget"] == {
        "max_fetcher_calls": 60,
        "max_elapsed_ms": 90000,
        "browser_enabled": False,
    }
    serialized = json.dumps(packet)
    assert '"labels"' not in serialized
    assert '"programme_evidence"' not in serialized
    assert '"review"' not in serialized
    assert '"value"' not in serialized
    assert '"excerpt"' not in serialized


def test_packet_refuses_unknown_or_duplicate_case() -> None:
    dataset = load("data/ground_truth.reviewed.json")
    capture = load("baseline/capture.json")
    with pytest.raises(ValueError, match="Missing case"):
        build_packet(dataset, capture, ["missing"])
    with pytest.raises(ValueError, match="unique"):
        build_packet(dataset, capture, ["kaist", "kaist"])


def trace_for(packet: dict) -> dict:
    start = datetime(2026, 9, 27, tzinfo=UTC)
    return {
        "case_id": "kaist",
        "packet_sha256": digest(packet),
        "baseline_pipeline_sha": packet["baseline_pipeline_sha"],
        "max_fetcher_calls": packet["baseline_budget"]["max_fetcher_calls"],
        "max_elapsed_ms": packet["baseline_budget"]["max_elapsed_ms"],
        "initial_fetcher_calls": 0,
        "initial_elapsed_ms": 0,
        "started_at": start.isoformat(),
        "ended_at": (start + timedelta(seconds=10)).isoformat(),
        "actions": [
            {
                "step": 1,
                "at": (start + timedelta(seconds=3)).isoformat(),
                "observed_before": "The confirmation queue is empty after the bounded run.",
                "observed_from_step": None,
                "tool": "fetcher",
                "action": "Open the official department root",
                "outcome_status": "success",
                "outcome": "The page exposes a programme navigation link.",
                "stage": "candidate_generation",
                "policy_mode": "same_policy",
                "url": "https://cs.kaist.ac.kr/",
                "raw_log_path": "step-001.json",
                "raw_log_sha256": "a" * 64,
                "elapsed_ms": 850,
                "fetcher_calls_cumulative": 1,
                "elapsed_ms_cumulative": 850,
                "cost_usd": None,
            }
        ],
        "proposals": [],
        "review_status": "unreviewed",
    }


def test_trace_links_to_exact_packet_and_retains_unreviewed_status() -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    trace = validate_trace(trace_for(packet), packet)
    assert isinstance(trace, ExpertTrace)
    assert trace.actions[0].policy_mode == "same_policy"

    tampered = dict(packet, dataset_version="changed")
    with pytest.raises(ValueError, match="exact packet"):
        validate_trace(trace_for(packet), tampered)


def test_trace_refuses_post_hoc_or_unrecorded_evidence() -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    trace = trace_for(packet)
    trace["actions"][0]["observed_before"] = ""
    with pytest.raises(ValidationError):
        validate_trace(trace, packet)

    trace = trace_for(packet)
    trace["proposals"] = [
        {
            "claim_key": "ielts.overall",
            "value": 6.5,
            "source_url": "https://cs.kaist.ac.kr/",
            "excerpt": "IELTS 6.5",
            "accessed_on": "2026-09-27",
            "scope": {"university": "KAIST"},
            "supporting_steps": [2],
            "status": "unreviewed",
        }
    ]
    with pytest.raises(ValidationError, match="recorded actions"):
        validate_trace(trace, packet)

    trace["proposals"][0]["supporting_steps"] = [1]
    trace["proposals"][0]["status"] = "human_verified"
    with pytest.raises(ValidationError):
        validate_trace(trace, packet)

    trace["proposals"][0]["status"] = "unreviewed"
    trace["actions"][0]["tool"] = "search_provider"
    with pytest.raises(ValidationError, match="page read"):
        validate_trace(trace, packet)

    trace["actions"][0]["tool"] = "fetcher"
    trace["actions"][0]["outcome_status"] = "blocked"
    with pytest.raises(ValidationError, match="page read"):
        validate_trace(trace, packet)


def test_unlisted_tool_must_be_marked_outside_policy() -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    trace = trace_for(packet)
    trace["actions"][0]["tool"] = "other"
    with pytest.raises(ValidationError, match="outside_policy"):
        validate_trace(trace, packet)


def test_later_action_cites_an_earlier_observation() -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    trace = trace_for(packet)
    second = dict(trace["actions"][0])
    second["step"] = 2
    second["at"] = (datetime(2026, 9, 27, tzinfo=UTC) + timedelta(seconds=4)).isoformat()
    second["raw_log_path"] = "step-002.json"
    second["observed_from_step"] = None
    second["fetcher_calls_cumulative"] = 2
    second["elapsed_ms_cumulative"] = 1700
    trace["actions"].append(second)
    with pytest.raises(ValidationError, match="earlier observation"):
        validate_trace(trace, packet)

    second["observed_from_step"] = 1
    validate_trace(trace, packet)


def test_trace_checks_raw_tool_log_bytes_when_given(tmp_path: Path) -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    log = tmp_path / "step-001.json"
    log.write_text('{"status":"observed"}', encoding="utf-8")
    trace = trace_for(packet)
    trace["actions"][0]["raw_log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    validate_trace(trace, packet, logs_dir=tmp_path)

    log.write_text('{"status":"changed"}', encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_trace_rejects_budget_expansion_and_disabled_browser() -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    trace = trace_for(packet)
    trace["max_fetcher_calls"] = 100
    with pytest.raises(ValueError, match="budget differs"):
        validate_trace(trace, packet)

    trace = trace_for(packet)
    trace["actions"][0]["fetcher_calls_cumulative"] = 61
    with pytest.raises(ValidationError, match="budget"):
        validate_trace(trace, packet)

    trace = trace_for(packet)
    trace["actions"][0]["tool"] = "browser"
    with pytest.raises(ValueError, match="Browser action"):
        validate_trace(trace, packet)


def test_trace_preserves_start_state_in_cumulative_budget() -> None:
    packet = build_packet(
        load("data/ground_truth.reviewed.json"), load("baseline/capture.json"), ["kaist"]
    )
    trace = trace_for(packet)
    trace["initial_fetcher_calls"] = 38
    trace["initial_elapsed_ms"] = 89000
    trace["actions"][0]["fetcher_calls_cumulative"] = 39
    trace["actions"][0]["elapsed_ms_cumulative"] = 89850
    validate_trace(trace, packet)

    trace["actions"][0]["fetcher_calls_cumulative"] = 1
    with pytest.raises(ValidationError, match="must not decrease"):
        validate_trace(trace, packet)

    trace["actions"][0]["fetcher_calls_cumulative"] = 38
    with pytest.raises(ValidationError, match="must consume"):
        validate_trace(trace, packet)
