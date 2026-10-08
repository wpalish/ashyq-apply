"""Prepare only: no university/provider/model calls or process dispatch."""
import hashlib
import json
from pathlib import Path

own = Path(__file__).resolve().parent
repo = own.parent.parent / "ashyq-apply"
full_run = Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T000741Z-check-0aa9ad4d")
manifest = json.loads((full_run / "source-manifest.json").read_text())
assert manifest["source_head"] == "f0c8fece0b59de3e964d20a1a4daf131e92c4ef8"
assert manifest["source_status"] == ""
dest = own.parent / "genuine-baseline"
dest.mkdir(exist_ok=False)
cases = ["groningen", "delft", "aalto", "vienna", "warsaw", "ubc", "toronto", "hku", "ntu", "kaist"]
plan = {
    "status": "PREPARED_ONLY_FULL_GATES_PENDING_NO_LIVE",
    "scope": "Fresh terminal bounded original10 baseline under accepted genuine-Job harness; not a paired gain or blind expert pilot",
    "source_head": manifest["source_head"], "source_tree_sha256": manifest["source_tree_sha256"],
    "source_snapshot": manifest["snapshot"], "full_gate_run": str(full_run),
    "required_before_execution": ["full summary passed13/13 exact source", "all backend/app/tests/evaluation/scripts/frontend source bytes still equal manifest", "genuine protocol199 controls/static gates accepted", "historicalSTOP unchanged and shared providerSTOP absent", "Handoff records execution plan; no accepted prototype is silently enabled"],
    "cases": cases, "selection": "same original ten; one explicit case per isolated child sequentially",
    "provider": "exa_mcp", "keys": "keyless configured app seam; no key files copied/read/printed by controller",
    "caps": {"fetcher_get_attempts": 60, "provider_search_attempts": 6, "full_active_seconds": 120, "finalization_reserve_ms": 1000, "separate_process_cleanup_reserve_seconds": 15},
    "protocol": {"fenced_research_job": True, "university_read_budget": False, "shared_query_budget": True, "browser": False, "robots": True, "documents": False, "experimental_heuristics": "all current source defaults unchanged/False; no IELTSv1/v2/v3"},
    "stop_file": str(own.parent.parent / "local-round7/provider-STOP.json"),
    "historical_stop": {"path": str(own.parent.parent / "development-STOP.json"), "sha256": "dd669c6d73d89ba2586676b46b120e4c8af2ea95e4e15cd7ae75c554f9557cad"},
    "global_stop": "First new provider/model/auth/quota refusal stops all remaining live actions; preserve complete refusal and UNSCORED; no retry/substitution/reset/purchase",
    "capture_validation": ["actual Job/claim provenance and heartbeat cleanup", "real observed counters <=60/6/120; missing remains null/unknown", "raw+observation+budget+batch capture self-consistent", "partial/timeout/source errors kept exactly; cannot invent completed Job or native ledger", "all10 attempted and terminal before any complete-cohort metric"],
    "score_policy": "Only after admissible complete terminal captures, strict existing scorer against separately pinned reviewed62 and reviewed9-73; rates retain adjudication/scope/support coverage and never count unanswered as success. Do not relabel old UNSCORED attempts. This is algorithm DEV evidence, not accepted40/62 expert pilot or launch acceptance.",
    "no_execution_in_this_file": True,
}
(dest / "PLAN.json").write_text(json.dumps(plan, indent=2) + "\n")
print(json.dumps({"path": str(dest / "PLAN.json"), "sha256": hashlib.sha256((dest / "PLAN.json").read_bytes()).hexdigest(), "status": plan["status"]}))
