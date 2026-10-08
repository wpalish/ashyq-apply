"""Sequential genuine-Job DEV baseline; --execute required, no retry."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

OWN = Path(__file__).resolve().parent
PLAN = json.loads((OWN / "PLAN.json").read_text())
FULL = Path(PLAN["full_gate_run"])
REPO = OWN.parent.parent / "ashyq-apply"
PACKAGE = FULL.parent.parent
STOP = Path(PLAN["stop_file"])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


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


def validate(case, capture, observed, budget, raw):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    config = capture.get("config", {})
    require(config.get("cohort") == [case], "wrong case/cohort")
    require(config.get("search_provider") == "exa_mcp", "provider mismatch")
    require(config.get("fenced_research_job") is True, "not fenced")
    require(config.get("university_read_budget") is False, "native flag mismatch")
    require(config.get("research_job_protocol") == "genuine-research-job", "wrong Job protocol")
    rows = capture.get("observations", [])
    require(len(rows) == 1 and rows[0] == observed, "capture/observation mismatch")
    require(observed.get("case_id") == case, "wrong observation identity")
    require(observed.get("error") != "CAPTURE_IN_PROGRESS", "unfinished observation")
    protocol = (raw.get("canary") or {}).get("job_protocol", {})
    require(protocol.get("kind") == "genuine-research-job", "wrong raw protocol")
    require(protocol.get("started") is True, "Job never started")
    require(bool(protocol.get("job_id") and protocol.get("run_id") and protocol.get("worker_id")), "missing actual Job provenance")
    require(protocol.get("claim_token") == 1 and protocol.get("lease_token") == 1, "nonfresh claim token")
    require(protocol.get("native_enabled") is False and protocol.get("native_ledger") is None, "OFF ledger fabricated")
    require(protocol.get("observation_available") is True, "raw reporting unavailable")
    require(protocol.get("heartbeat_tasks") == 1 and protocol.get("heartbeat_done") == [True], "heartbeat not joined")
    require(protocol.get("job_status") in {"succeeded", "queued", "running", "failed"}, "unknown actual Job state")
    for name, limit in [("fetcher_calls", 60), ("search_queries", 6), ("elapsed_ms", 120000)]:
        value = budget.get(name)
        require(type(value) in (int, float) and 0 <= value <= limit, "missing/over-budget " + name)
    require(budget.get("max_fetcher_calls") == 60 and budget.get("max_search_queries") == 6 and budget.get("max_active_seconds") == 120, "caps changed")
    require(budget.get("finalization_reserve_ms") == 1000, "reserve changed")
    telemetry = observed.get("telemetry", {})
    require(telemetry.get("http_fetches") == budget.get("fetcher_calls"), "Fetcher counter mismatch")
    require(telemetry.get("search_calls") == budget.get("search_queries"), "search counter mismatch")
    require(telemetry.get("browser_fetches") == 0, "browser tier used/missing")
    require(telemetry.get("model_input_tokens") == 0 and telemetry.get("jev_input_tokens") == 0, "model counters used/missing")
    require(budget.get("provider_failure") is None, "provider refusal")
    require(budget.get("protocol_persistence_error") is None, "artifact persistence failed")
    return errors


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
    execution = {"status": "RUNNING_UNSCORED", "source_head": PLAN["source_head"], "source_tree_sha256": PLAN["source_tree_sha256"], "source_paths_verified": checked, "plan_sha256": sha(OWN / "PLAN.json"), "controller_sha256": sha(Path(__file__)), "package_sha256": sha(PACKAGE / "run_local.py"), "attempted": [], "remaining": PLAN["cases"], "validation_errors": {}, "network_location": "local Mac", "expert_pilot": False}
    write("execution-receipt.json", execution)
    run = runner.Run(OWN, env, source)
    run.summary["live_network_capture_started"] = True
    for case in PLAN["cases"]:
        if STOP.exists():
            execution["status"] = "GLOBAL_PROVIDER_STOP_UNSCORED"
            break
        historical = PLAN["historical_stop"]
        assert sha(Path(historical["path"])) == historical["sha256"]
        directory = OWN / case
        command = [str(snapshot / "backend/.venv/bin/python"), "-m", "evaluation.research.live", "--live", "--case", case, "--search-provider", "exa_mcp", "--strict-expert-budget", "--shared-query-budget", "--fenced-research-job", "--no-university-read-budget", "--seconds-per-case", "120", "--max-pages", "60", "--finalization-reserve-ms", "1000", "--stop-file", str(STOP), "--out", str(directory)]
        execution["attempted"].append(case)
        execution["remaining"] = [c for c in PLAN["cases"] if c not in execution["attempted"]]
        write("execution-receipt.json", execution)
        code = run.step(case, command, snapshot / "backend")
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
                errors = validate(case, json.loads(captures[0].read_text()), json.loads((folder / (case + ".json")).read_text()), json.loads((folder / (case + ".budget.json")).read_text()), json.loads((folder / (case + ".raw.json")).read_text()))
            except (OSError, ValueError, TypeError, KeyError) as exc:
                errors = ["artifact validation " + type(exc).__name__]
        if errors:
            execution["status"] = "PROTOCOL_PARTIAL_UNSCORED"
            execution["validation_errors"][case] = errors
            break
        write("execution-receipt.json", execution)
    else:
        execution["status"] = "TERMINAL_ORIGINAL10_CAPTURE_COMPLETE_AWAIT_OFFLINE_SCORING"
    write("execution-receipt.json", execution)
    run.summary["baseline_execution"] = execution
    run.finish(execution["status"].lower())
    print(execution["status"])
    return 0 if execution["status"] == "TERMINAL_ORIGINAL10_CAPTURE_COMPLETE_AWAIT_OFFLINE_SCORING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
