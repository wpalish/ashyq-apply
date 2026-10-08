"""Sequential genuine-Job DEV baseline; --execute required, no retry."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

OWN = Path(__file__).resolve().parent
PLAN = json.loads((OWN / "PLAN.json").read_text())
FULL = Path(PLAN["full_gate_run"])
REPO = OWN.parent.parent / "ashyq-apply"
PACKAGE = FULL.parent.parent
STOP = Path(PLAN["stop_file"])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
# Ordinary schema imports use the explicitly pinned local source snapshot.
sys.path.insert(0, str(Path(PLAN["source_snapshot"]) / "backend"))


def write(name, value):
    target = OWN / name
    temporary = target.with_suffix(target.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(target)


def preflight():
    full = json.loads((FULL / "summary.json").read_text())
    assert full["status"] == "passed" and len(full["steps"]) == 13
    assert all(step["exit_code"] == 0 for step in full["steps"])
    source = full["source"]
    assert source["source_head"] == PLAN["source_head"]
    assert source["source_tree_sha256"] == PLAN["source_tree_sha256"]
    assert source["source_status"] == ""
    assert PLAN["protocol"].get("strict_provider_first_refusal") is True
    assert source["files"]["backend/evaluation/research/live.py"] == PLAN["strict_retry_harness_sha256"]
    snapshot = Path(source["snapshot"])
    checked = 0
    for name, digest in source["files"].items():
        if name.startswith(("backend/app/", "backend/tests/", "backend/evaluation/", "backend/scripts/", "frontend/")):
            assert sha(REPO / name) == digest and sha(snapshot / name) == digest, name
            checked += 1
    historical = PLAN["historical_stop"]
    assert sha(Path(historical["path"])) == historical["sha256"]
    assert not STOP.exists(), "Global provider STOP already exists"
    assert "UNIVERSITY_READ_BUDGET = False" in (snapshot / "backend/app/pipeline/read_budget.py").read_text()
    assert not (snapshot / "backend/.env").exists()
    return source, snapshot, checked


def validate(case, capture, observed, budget, raw, *, require_complete_job=True):
    """Admit evidence, never infer a completed Job from a terminal capture.

    Raw JSON types are checked before equality or schema coercion. The optional
    partial lane retains an honest bounded stop without calling it Job success.
    """
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    def number(value):
        if type(value) not in (int, float):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False
    def text(value):
        return type(value) is str and bool(value.strip())
    def objects(value):
        return type(value) is list and all(type(row) is dict for row in value)
    for name, value in [("capture", capture), ("observation", observed), ("budget", budget), ("raw", raw)]:
        require(type(value) is dict, "invalid object " + name)
    if errors:
        return errors
    config = capture.get("config", {})
    canary = raw.get("canary")
    require(type(config) is dict, "invalid capture config")
    require(type(canary) is dict, "invalid raw canary")
    telemetry = observed.get("telemetry")
    require(type(telemetry) is dict, "invalid telemetry")
    require(objects(capture.get("observations")), "invalid observation rows")
    require(objects(raw.get("claims")), "invalid raw claims")
    if errors:
        return errors
    protocol = canary.get("job_protocol")
    case_budgets = config.get("case_budgets")
    require(type(protocol) is dict, "invalid Job protocol")
    require(type(case_budgets) is dict, "invalid capture budgets")
    require(objects(canary.get("institutions")) and len(canary.get("institutions", [])) == 1, "missing/invalid institution")
    if errors:
        return errors
    require({"case_id", "programme_urls", "ranked_urls", "predictions", "telemetry", "page_outcomes", "error"} <= set(observed), "missing explicit observation fields")
    require({"schema_version", "pipeline_sha", "captured_at", "mode", "config", "observations"} <= set(capture), "missing explicit capture fields")
    require({"native_ledger", "control_error", "control_message", "run_unknowns", "run_errors"} <= set(protocol), "missing explicit Job reporting fields")
    for name in ("run_unknowns", "run_errors"):
        require(type(protocol.get(name)) is list and all(type(row) is str for row in protocol[name]), "invalid Job reporting " + name)
    copied_budget = case_budgets.get(case)
    require(type(copied_budget) is dict, "missing/invalid physical budget copy")
    require(objects(protocol.get("claim_records")), "invalid claim records")
    require(objects(protocol.get("page_outcomes")), "invalid page outcomes")
    if errors:
        return errors
    # Schema validation rejects malformed predictions/URLs/extra fields. Raw
    # counters below still require exact ints, rather than coerced booleans.
    try:
        from evaluation.research.schema import Capture, Observation
        Capture.model_validate(capture)
        Observation.model_validate(observed)
    except (ValueError, TypeError):
        errors.append("capture/observation schema invalid")
    require(capture.get("schema_version") == "1", "schema version mismatch")
    require(capture.get("mode") == "live", "capture mode mismatch")
    require(capture.get("pipeline_sha") == PLAN["source_head"], "pipeline source mismatch")
    require(text(capture.get("captured_at")), "missing capture timestamp")
    manifest = json.loads((FULL / "source-manifest.json").read_text())
    for name, path in [("harness_sha256", "backend/evaluation/research/live.py"), ("mapping_sha256", "backend/evaluation/research/mapping.py")]:
        require(config.get(name) == manifest["files"][path], name + " mismatch")
    require(config.get("cohort") == [case], "wrong case/cohort")
    require(config.get("search_provider") == "exa_mcp", "provider mismatch")
    require(config.get("fenced_research_job") is True, "not fenced")
    require(config.get("university_read_budget") is False, "native flag mismatch")
    require(config.get("research_job_protocol") == "genuine-research-job", "wrong Job protocol")
    for name, expected in {"strict_expert_budget": True, "shared_query_budget": True, "browser_enabled": False, "cold_fetcher_reads": True, "site_branding_identity": False, "subject_phrase_match": False, "programme_identity_before_funding": False}.items():
        require(config.get(name) is expected, "config flag mismatch " + name)
    for name, expected in {"seconds_per_case": 120, "child_active_seconds": 120, "max_fetcher_calls_per_case": 60, "max_search_queries_per_case": 6, "finalization_reserve_ms": 1000, "source_work_deadline_ms": 119000, "parent_process_reserve_seconds": 15, "parent_process_timeout_seconds": 135}.items():
        require(number(config.get(name)) and config[name] == expected, "config cap mismatch " + name)
    require(config.get("page_budget_counts") == "every Fetcher.get invocation; cache hits consume a call", "wrong physical read semantics")
    for name, expected in {"batch_attempted_case_ids": [case], "batch_completed_case_ids": [case], "batch_remaining_case_ids": [], "batch_stop_reason": None}.items():
        require(name in config and config[name] == expected, "batch mismatch " + name)
    rows = capture.get("observations", [])
    require(len(rows) == 1 and rows[0] == observed, "capture/observation mismatch")
    require(observed.get("case_id") == case, "wrong observation identity")
    require(observed.get("error") != "CAPTURE_IN_PROGRESS", "unfinished observation")
    require(protocol.get("kind") == "genuine-research-job", "wrong raw protocol")
    require(protocol.get("started") is True, "Job never started")
    require(all(text(protocol.get(name)) for name in ("job_id", "run_id", "worker_id", "sqlite_case_database")), "missing actual Job provenance")
    require(all(type(protocol.get(name)) is int and protocol[name] == 1 for name in ("claim_token", "lease_token")), "nonfresh claim token")
    require(protocol.get("native_enabled") is False and protocol.get("native_ledger") is None, "OFF ledger fabricated")
    require(protocol.get("observation_available") is True, "raw reporting unavailable")
    require(raw.get("protocol_observation_available") is True, "raw observation unavailable")
    require(type(protocol.get("heartbeat_tasks")) is int and protocol["heartbeat_tasks"] == 1, "invalid heartbeat count")
    require(type(protocol.get("heartbeat_done")) is list and len(protocol["heartbeat_done"]) == 1 and protocol["heartbeat_done"][0] is True, "heartbeat not joined")
    require(type(protocol.get("heartbeat_cancelled")) is list and len(protocol["heartbeat_cancelled"]) == 1 and type(protocol["heartbeat_cancelled"][0]) is bool, "invalid heartbeat cancellation")
    job_status = protocol.get("job_status")
    require(type(job_status) is str and job_status in {"succeeded", "queued", "running", "failed", "dead", "cancelled"}, "unknown actual Job state")
    for name in ("worker_jobs_done", "worker_jobs_failed"):
        require(type(protocol.get(name)) is int and 0 <= protocol[name] <= 1, "invalid worker outcome " + name)
    require("recorded_worker_id" in protocol and (protocol["recorded_worker_id"] is None or text(protocol["recorded_worker_id"])), "invalid recorded worker identity")
    for name, limit in [("fetcher_calls", 60), ("search_queries", 6), ("elapsed_ms", 120000)]:
        value = budget.get(name)
        require(type(value) is int and 0 <= value <= limit, "missing/over-budget " + name)
    for name in ("blocked_search_queries", "network_http_requests"):
        require(type(budget.get(name)) is int and budget[name] >= 0, "invalid physical counter " + name)
    for name, expected in {"max_fetcher_calls": 60, "max_search_queries": 6, "max_active_seconds": 120, "finalization_reserve_ms": 1000, "source_work_deadline_ms": 119000}.items():
        require(number(budget.get(name)) and budget[name] == expected, "physical cap mismatch " + name)
    require(budget.get("strict_expert_budget") is True and budget.get("provider") == "exa_mcp", "physical protocol mismatch")
    active_basis = "capture_one entry; includes canary setup and all pipeline stages, cancellation cleanup, output/raw persistence and final checkpoint work; final metering-envelope persistence is audit only"
    require(budget.get("active_time_basis") == active_basis and config.get("active_time_basis") == active_basis, "clock basis mismatch")
    for physical_name in budget:
        require(physical_name in copied_budget and type(copied_budget[physical_name]) is type(budget[physical_name]) and copied_budget[physical_name] == budget[physical_name], "physical copy mismatch " + physical_name)
    expected_parent = {"parent_process_elapsed_seconds", "process_error", "active_checkpoint_available"}
    require(set(copied_budget) == set(budget) | expected_parent, "missing/extra physical copied fields")
    require(copied_budget.get("active_checkpoint_available") is True, "physical checkpoint missing")
    require("process_error" in copied_budget and copied_budget["process_error"] is None, "parent process error")
    require(number(copied_budget.get("parent_process_elapsed_seconds")) and 0 <= copied_budget["parent_process_elapsed_seconds"] <= 135, "parent process ceiling exceeded/missing")
    for name, expected in {"http_fetches": budget.get("fetcher_calls"), "search_calls": budget.get("search_queries"), "browser_fetches": 0, "model_input_tokens": 0, "jev_input_tokens": 0}.items():
        require(type(telemetry.get(name)) is int and telemetry[name] == expected, "telemetry mismatch " + name)
    require(number(telemetry.get("latency_seconds")) and 0 <= telemetry["latency_seconds"] <= 120, "active telemetry missing/over-budget")
    require("provider_failure" in budget and budget["provider_failure"] is None, "provider refusal/missing proof")
    require(budget.get("protocol_persistence_error") is None, "artifact persistence failed")
    require("stop_reason" in budget and (budget["stop_reason"] is None or type(budget["stop_reason"]) is str), "invalid stop reason")
    stop_reason = budget.get("stop_reason")
    require(stop_reason in (None, "page_budget_exhausted", "search_budget_exhausted", "source_work_deadline_exhausted", "wall_clock_budget_exhausted"), "refusal/unrecognized stop reason")
    if stop_reason == "page_budget_exhausted":
        require(budget.get("fetcher_calls") == 60, "page stop before actual cap")
    if stop_reason == "search_budget_exhausted":
        require(budget.get("search_queries") == 6, "search stop before actual cap")
    claim_records = protocol["claim_records"]
    require(all(type(record.get("payload")) is dict for record in claim_records), "invalid actual claim payload")
    require(raw["claims"] == [record.get("payload") for record in claim_records], "raw/actual claims mismatch")
    if not raw["claims"]:
        require(observed.get("predictions") == [], "predictions without raw claims")
    raw_error = canary.get("run_error")
    control_error = protocol.get("control_error")
    error = observed.get("error")
    require("run_error" in canary and type(raw_error) is str, "invalid raw terminal error")
    require("control_error" in protocol and (control_error is None or type(control_error) is str), "invalid raw control error")
    require((raw_error or None) == (control_error or None), "raw/control error mismatch")
    if raw_error:
        control_type = protocol.get("control_type")
        reason = protocol.get("control_reason")
        message = protocol.get("control_message")
        require(text(control_type) and (reason is None or text(reason)) and (message is None or text(message)), "invalid typed partial cause")
        if text(control_type) and (reason is None or text(reason)) and (message is None or text(message)):
            detail = reason or message
            require(raw_error == control_type + (": " + detail if detail else ""), "original typed partial cause mismatch")
    if require_complete_job:
        require(job_status == "succeeded" and raw_error in (None, "") and control_error is None and error is None and stop_reason is None, "partial is not a completed Job result")
    elif raw_error or error or job_status != "succeeded" or stop_reason:
        control_type = protocol.get("control_type")
        reason = protocol.get("control_reason")
        require(control_type in (None, "CancelledError", "RunCancelled", "TimeoutError", "RuntimeError", "LeaseLost", "UniversityReadStopped"), "unsupported partial control")
        if control_type == "UniversityReadStopped":
            require(reason == "checkpoint_busy", "native-OFF readguard anomaly")
        if control_type == "RuntimeError":
            require(raw_error == "RuntimeError: BENCHMARK_PAGE_BUDGET_EXHAUSTED" and stop_reason == "page_budget_exhausted", "unsupported RuntimeError partial")
        if control_type == "RunCancelled":
            require(job_status == "cancelled" and raw_error == "RunCancelled", "cancellation state mismatch")
        if stop_reason in ("source_work_deadline_exhausted", "wall_clock_budget_exhausted"):
            require(type(budget.get("elapsed_ms")) is int and budget["elapsed_ms"] >= 119000, "deadline before source clock")
            require(error in ("BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED", "TimeoutError: BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"), "deadline missing original diagnostic")
        else:
            require(error == (raw_error or None), "partial observation/raw error mismatch")
        require(bool(raw_error or stop_reason), "silent unfinished Job")
    else:
        require(error is None and control_error is None, "silent observation/control error")
    if job_status == "succeeded":
        require(protocol.get("worker_jobs_done") == 1 and protocol.get("worker_jobs_failed") == 0 and protocol.get("recorded_worker_id") is None, "completed Job state inconsistency")
    return errors


def capture_kind(observed, budget, raw):
    protocol = raw["canary"]["job_protocol"]
    if observed["error"] or raw["canary"]["run_error"] or budget["stop_reason"] or protocol["job_status"] != "succeeded":
        return "BOUNDED_TERMINAL_PARTIAL_JOB_" + protocol["job_status"]
    return "COMPLETED_JOB_CAPTURE"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print("PREPARED_ONLY_NO_LIVE " + str(OWN / "PLAN.json"))
        return 0
    assert not (OWN / "execution-receipt.json").exists(), "This exact cohort attempt cannot be resumed/retried"
    source, snapshot, checked = preflight()
    spec = importlib.util.spec_from_file_location("authorized_local_runner", PACKAGE / "run_local.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    env = runner.safe_env(PACKAGE / "tools/node-v22.23.3-darwin-arm64/bin", OWN)
    env.update(UNIMATCH_DEMO_MODE="false", UNIMATCH_ENABLE_BROWSER_TIER="false", UNIMATCH_RESPECT_ROBOTS="true", UNIMATCH_SEARCH_PROVIDER="exa_mcp", UNIMATCH_FETCH_CONTACT="https://github.com/wpalish/ashyq-apply", PYTHONDONTWRITEBYTECODE="1")
    execution = {"status": "RUNNING_UNSCORED", "source_head": PLAN["source_head"], "source_tree_sha256": PLAN["source_tree_sha256"], "source_paths_verified": checked, "plan_sha256": sha(OWN / "PLAN.json"), "controller_sha256": sha(Path(__file__)), "package_sha256": sha(PACKAGE / "run_local.py"), "attempted": [], "remaining": PLAN["cases"], "validation_errors": {}, "capture_kinds": {}, "network_location": "local Mac", "expert_pilot": False}
    write("execution-receipt.json", execution)
    run = runner.Run(OWN, env, source)
    run.summary["live_network_capture_started"] = True
    for case in PLAN["cases"]:
        if STOP.exists():
            execution["status"] = "GLOBAL_PROVIDER_STOP_UNSCORED"
            break
        try:
            # Revalidate the exact snapshot, current source and STOP before
            # every child. No same-cohort source drift or automatic resume.
            preflight()
        except Exception as exc:
            execution["status"] = "GLOBAL_PROVIDER_STOP_UNSCORED" if STOP.exists() else "PREFLIGHT_CHANGED_UNSCORED"
            execution["validation_errors"][case] = ["preflight " + type(exc).__name__]
            break
        directory = OWN / case
        command = [str(snapshot / "backend/.venv/bin/python"), "-m", "evaluation.research.live", "--live", "--case", case, "--search-provider", "exa_mcp", "--strict-expert-budget", "--shared-query-budget", "--fenced-research-job", "--no-university-read-budget", "--seconds-per-case", "120", "--max-pages", "60", "--finalization-reserve-ms", "1000", "--stop-file", str(STOP), "--out", str(directory)]
        execution["attempted"].append(case)
        execution["remaining"] = [c for c in PLAN["cases"] if c not in execution["attempted"]]
        write("execution-receipt.json", execution)
        try:
            code = run.step(case, command, snapshot / "backend")
        except Exception as exc:
            execution["status"] = "CAPTURE_PROCESS_FAILED_UNSCORED"
            execution["validation_errors"][case] = ["process " + type(exc).__name__]
            break
        if STOP.exists():
            execution["status"] = "GLOBAL_PROVIDER_STOP_UNSCORED"
            break
        if code != 0:
            execution["status"] = "CAPTURE_PROCESS_FAILED_UNSCORED"
            execution["validation_errors"][case] = ["process exit " + str(code)]
            break
        captures = list(directory.glob("*/capture.json"))
        if len(captures) != 1:
            errors = ["missing/ambiguous capture"]
        else:
            folder = captures[0].parent
            try:
                capture = json.loads(captures[0].read_text())
                observed = json.loads((folder / (case + ".json")).read_text())
                budget = json.loads((folder / (case + ".budget.json")).read_text())
                raw = json.loads((folder / (case + ".raw.json")).read_text())
                if type(budget) is dict and (budget.get("provider_failure") is not None or budget.get("stop_reason") in ("http_429", "provider_failure", "external_provider_failure")):
                    execution["status"] = "GLOBAL_PROVIDER_STOP_UNSCORED"
                    execution["validation_errors"][case] = ["recorded provider refusal; no further child"]
                    break
                errors = validate(case, capture, observed, budget, raw, require_complete_job=False)
                if not errors:
                    execution["capture_kinds"][case] = capture_kind(observed, budget, raw)
            except Exception as exc:
                errors = ["artifact validation " + type(exc).__name__]
        if errors:
            execution["status"] = "PROTOCOL_PARTIAL_UNSCORED"
            execution["validation_errors"][case] = errors
            break
        write("execution-receipt.json", execution)
    else:
        execution["status"] = "TERMINAL_ORIGINAL10_CAPTURE_COMPLETE_AWAIT_OFFLINE_SCORING"
        execution["partial_cases"] = [case for case, kind in execution["capture_kinds"].items() if kind != "COMPLETED_JOB_CAPTURE"]
        execution["scoring_note"] = "Complete collection of ten bounded terminal captures; partial Jobs remain explicitly partial and all missing/unknown facts remain in completeness denominator. This status does not assert ten succeeded Jobs or launch readiness."
    write("execution-receipt.json", execution)
    run.summary["baseline_execution"] = execution
    run.finish(execution["status"].lower())
    print(execution["status"])
    return 0 if execution["status"] == "TERMINAL_ORIGINAL10_CAPTURE_COMPLETE_AWAIT_OFFLINE_SCORING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
