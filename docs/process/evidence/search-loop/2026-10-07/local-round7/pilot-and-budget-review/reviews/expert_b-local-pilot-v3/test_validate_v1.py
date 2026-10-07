"""Offline contract controls against preserved LOCAL controller v1; never main."""

from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import socket
import subprocess

import pytest

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "local_pilot.v1.py"
spec = importlib.util.spec_from_file_location("local_pilot_offline_review", SOURCE)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


@pytest.fixture(autouse=True)
def no_external_actions(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("Review attempted a forbidden external action")

    monkeypatch.setattr(socket, "getaddrinfo", refused)
    monkeypatch.setattr(socket, "create_connection", refused)
    monkeypatch.setattr(subprocess, "Popen", refused)
    monkeypatch.setattr(subprocess, "run", refused)
    monkeypatch.setattr(subprocess, "check_output", refused)
    monkeypatch.setattr(pilot, "main", refused)


def envelope():
    cfg = {
        "strict_expert_budget": True, "seconds_per_case": 120,
        "max_fetcher_calls_per_case": 60, "max_search_queries_per_case": 6,
        "finalization_reserve_ms": 3000, "source_work_deadline_ms": 117000,
        "search_provider": "exa_mcp", "browser_enabled": False,
        "site_branding_identity": False, "subject_phrase_match": False,
        "programme_identity_before_funding": False, "shared_query_budget": True,
        "cohort": ["groningen"], "batch_stop_reason": None,
        "harness_sha256": "synthetic-harness", "mapping_sha256": "synthetic-mapping",
    }
    budget = {
        "strict_expert_budget": True, "provider": "exa_mcp",
        "max_fetcher_calls": 60, "max_search_queries": 6, "max_active_seconds": 120,
        "finalization_reserve_ms": 3000, "source_work_deadline_ms": 117000,
        "fetcher_calls": 2, "search_queries": 1, "blocked_search_queries": 0,
        "network_http_requests": 3, "elapsed_ms": 1000, "stop_reason": None,
        "provider_failure": None, "process_error": None,
        "active_checkpoint_available": True,
        "parent_process_elapsed_seconds": 1.1,
        "active_time_basis": "synthetic terminal checkpoint",
    }
    cfg["case_budgets"] = {"groningen": budget}
    return {
        "pipeline_sha": pilot.EXPECTED_HEAD, "mode": "live",
        "captured_at": "2026-10-08T00:00:00Z", "config": cfg,
        "observations": [{"case_id": "groningen", "error": None,
                          "telemetry": {"browser_fetches": 0, "latency_seconds": 1.0}}],
    }


def raw(case="groningen"):
    return {
        "canary": {
            "accessed_at": "2026-10-08T00:00:00Z", "duration_seconds": 1.0,
            "run_error": "", "batch": [case],
            "institutions": [{"institution": case, "country": "synthetic",
                              "domain": "example.edu", "catalogue_id": None}],
            "totals": {"institutions": 1, "fetch_tiers": {"browser": 0}},
        },
        "claims": [],
    }


def write_evidence(tmp_path, capture, payload=None):
    (tmp_path / "groningen.raw.json").write_text(json.dumps(raw() if payload is None else payload))
    checkpoint = deepcopy(capture["config"]["case_budgets"]["groningen"])
    for k in ("parent_process_elapsed_seconds", "process_error", "active_checkpoint_available"):
        checkpoint.pop(k, None)
    (tmp_path / "groningen.budget.json").write_text(json.dumps(checkpoint))


def rejected(capture, tmp_path):
    result = pilot.validate(capture, "groningen", tmp_path)
    assert result["errors"], result


def test_valid_envelope(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    assert pilot.validate(c, "groningen", tmp_path)["errors"] == []


def test_bounded_timeout_has_honest_missing_raw_marker(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    (tmp_path / "groningen.raw.json").unlink()
    c["observations"][0]["error"] = "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    c["config"]["case_budgets"]["groningen"]["stop_reason"] = "source_work_deadline_exhausted"
    (tmp_path / "groningen.budget.json").write_text(json.dumps(c["config"]["case_budgets"]["groningen"]))
    result = pilot.validate(c, "groningen", tmp_path)
    assert result["errors"] == [] and result["bounded_timeout_without_full_raw"] is True


@pytest.mark.parametrize("key,value", [("fetcher_calls", True), ("search_queries", -1),
                                      ("elapsed_ms", 120001), ("fetcher_calls", 61),
                                      ("search_queries", 7)])
def test_invalid_counters_rejected(tmp_path, key, value):
    c = envelope()
    write_evidence(tmp_path, c)
    c["config"]["case_budgets"]["groningen"][key] = value
    rejected(c, tmp_path)


def test_missing_completed_raw_rejected(tmp_path):
    c = envelope()
    rejected(c, tmp_path)


@pytest.mark.parametrize("text", ["", "not-json", "{}", "[]"])
def test_malformed_completed_raw_must_reject(tmp_path, text):
    c = envelope()
    write_evidence(tmp_path, c)
    (tmp_path / "groningen.raw.json").write_text(text)
    rejected(c, tmp_path)


def test_wrong_case_raw_must_reject(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c, raw("foreign-case"))
    rejected(c, tmp_path)


def test_missing_physical_checkpoint_must_reject(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    (tmp_path / "groningen.budget.json").unlink()
    rejected(c, tmp_path)


def test_conflicting_terminal_checkpoint_must_reject(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    b = c["config"]["case_budgets"]["groningen"].copy()
    b["fetcher_calls"] = 61
    (tmp_path / "groningen.budget.json").write_text(json.dumps(b))
    rejected(c, tmp_path)


@pytest.mark.parametrize("key", ["max_fetcher_calls", "max_search_queries", "max_active_seconds",
                                "strict_expert_budget", "finalization_reserve_ms",
                                "source_work_deadline_ms", "network_http_requests",
                                "process_error", "provider_failure"])
def test_missing_budget_audit_fields_must_reject(tmp_path, key):
    c = envelope()
    write_evidence(tmp_path, c)
    c["config"]["case_budgets"]["groningen"].pop(key)
    rejected(c, tmp_path)


def test_http429_stop_reason_without_failure_envelope_must_reject(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    c["config"]["case_budgets"]["groningen"]["stop_reason"] = "http_429"
    rejected(c, tmp_path)


@pytest.mark.parametrize("part,value", [("config", None), ("config", []),
                                      ("observations", [None]), ("observations", None)])
def test_malformed_envelope_is_structured_protocol_error(tmp_path, part, value):
    c = envelope()
    write_evidence(tmp_path, c)
    c[part] = value
    rejected(c, tmp_path)


def test_wrong_capture_mode_must_reject(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    c["mode"] = "fixture"
    rejected(c, tmp_path)


def test_missing_telemetry_must_reject(tmp_path):
    c = envelope()
    write_evidence(tmp_path, c)
    c["observations"][0].pop("telemetry")
    rejected(c, tmp_path)
