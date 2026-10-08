"""Archive a successful exact-source full run; never runs checks/live itself."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

OWN = Path(__file__).resolve().parent
REPO = OWN.parent.parent / "ashyq-apply"
RUN = Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T000741Z-check-0aa9ad4d")
DEST = REPO / "docs/process/evidence/search-loop/2026-10-07/local-round9/full-local"
SOURCE = "f0c8fece0b59de3e964d20a1a4daf131e92c4ef8"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
summary = json.loads((RUN / "summary.json").read_text())
assert summary["status"] == "passed" and len(summary["steps"]) == 13
assert all(step["exit_code"] == 0 for step in summary["steps"])
assert summary["source"]["source_head"] == SOURCE and summary["source"]["source_status"] == ""
assert summary["source"]["source_tree_sha256"] == "3489f8fa072386f0ee4a74fb24bf6e502aea6a93490ba8840826c321b5e60dde"
code_paths = [name for name in summary["source"]["files"] if name.startswith(("backend/app/", "backend/tests/", "backend/evaluation/", "backend/scripts/", "frontend/"))]
for name in code_paths:
    assert sha(REPO / name) == summary["source"]["files"][name], name
previous = json.loads((REPO / "docs/process/evidence/search-loop/2026-10-07/local-round8/full-local/package/source-manifest.json").read_text())
for name, digest in previous["files"].items():
    if name.startswith("backend/app/"):
        assert sha(REPO / name) == digest, name
counts = {}
case_keys = {}
for mode in ["backend-sqlite", "backend-postgresql"]:
    cases = list(ET.parse(RUN / (mode + ".xml")).getroot().iter("testcase"))
    assert len(cases) == 4261
    assert not any(c.find("failure") is not None or c.find("error") is not None or c.find("skipped") is not None for c in cases)
    counts[mode] = len(cases)
    case_keys[mode] = {(c.get("classname"), c.get("name")) for c in cases}
assert case_keys["backend-sqlite"] == case_keys["backend-postgresql"] and len(case_keys["backend-sqlite"]) == 4261
sqlite_log = (RUN / "backend-sqlite.log").read_text()
coverage = float(re.search(r"Total coverage: ([0-9.]+)%", sqlite_log)[1])
assert coverage >= 92
assert "79 passed" in (RUN / "e2e.log").read_text() and "1 skipped" in (RUN / "e2e.log").read_text()
assert "6 passed" in (RUN / "e2e-auth.log").read_text()
assert "232 passed" in (RUN / "frontend-tests.log").read_text()
assert "383 source files" in (RUN / "mypy.log").read_text()
secrets = []
for line in (REPO / "backend/.env").read_text().splitlines():
    match = re.match(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
    if match and re.search("KEY|TOKEN|SECRET|PASSWORD", match[1]):
        value = match[2].strip().strip("\"'")
        if len(value) >= 12 and not value.startswith(("#", "${")):
            secrets.append(value.encode())
DEST.mkdir(parents=True, exist_ok=False)
files = {}
def copy(original, name):
    body = original.read_bytes()
    assert not any(secret in body for secret in secrets), "Configured secret detected"
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    files[name] = {"original": str(original), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
for name in ["summary.json", "source-manifest.json", "backend-sqlite.xml", "backend-postgresql.xml", *[step["name"] + ".log" for step in summary["steps"]]]:
    copy(RUN / name, "package/" + name)
for name in ["actual-module-provenance.json", "code-freeze.json", "checkpoint.log", "finalize_full.py", "prepare_baseline.py"]:
    copy(OWN / name, "parent/" + name)
ielts = OWN.parent / "a-ielts-v3-independent"
assert sha(ielts / "receipt.json") == "68ff75c91d077f79e9b29b879aef1a397675f5039de9a08c248a65512244d457"
for name in ["PLAN.json", "receipt.json", "review.ru.md", "review_controls.py", "review_controls.attempt1.py", "controls.original.log", "controls.attempt2.json", "controls.attempt2.log", "classified-findings.json"]:
    copy(ielts / name, "parallel-ielts-v3-rejected/" + name)
v3 = OWN.parent.parent / "local-round8/b-ielts-section-proposal-v3"
assert sha(v3 / "manifest.json") == "6c1b368f41ef349a796db8f5d96e5a016d4a964e5c5961114a790ca9ae01d990"
for name in ["manifest.json", "PLAN.json", "review.ru.md", "results.receipt.json", "implementation.proposed.diff", "pytest-sealed.log", "test_owned_ielts.py", "test_parent15.py", "test_v3_boundaries.py", "test_variant_decline.py", "proposed/app/adapters/extraction.py", "proposed/app/adapters/requirements/web_requirements.py", "proposed/app/adapters/requirements/ielts_sections.py"]:
    copy(v3 / name, "parallel-ielts-v3-rejected/author-originals/" + name)
baseline = OWN.parent / "genuine-baseline"
for name in ["PLAN.json", "execute_baseline.py", "offline-validator-controls.json"]:
    copy(baseline / name, "baseline-prepared-only/" + name)
old_demo = OWN.parent.parent / "local-round8/root-demo/receipt.json"
demo = json.loads(old_demo.read_text())
copy(old_demo, "retained-unchanged-app-demo/receipt.json")
receipt = {"at_utc": datetime.now(UTC).isoformat(), "status": "EXACT_SOURCE_FULL_LOCAL_PASS",
           "source_head": SOURCE, "source_tree_sha256": summary["source"]["source_tree_sha256"],
           "started_at": summary["started_at"], "finished_at": summary["finished_at"],
           "full_gates_passed": 13, "full_gates_failed": 0, "backend": counts,
           "unique_backend_cases": 4261, "backend_executions_two_primary_modes": 8522,
           "coverage_percent_sqlite": coverage, "frontend_tests": 232, "mypy_files": 383,
           "demo_e2e_passed": 79, "demo_e2e_skipped": 1, "auth_e2e_passed": 6,
           "focused_actual_module_passed": 199, "source_code_paths_unchanged_during_full": len(code_paths),
           "native_default": False, "provider_model_university_calls": 0, "configured_secret_matches": 0,
           "app_modules_unchanged_from_budget3b3a": True,
           "demo_evidence": "Retained previous isolated seed_demo20/order/count evidence on unchanged app; current full browser demo is fresh. Harness/test changes only; no new seed run claimed.",
           "retained_demo_sha256": demo["stable_output_sha256"], "one_alembic_head": "d8e412c6a901",
           "limits": ["Two whole suite PRIMARY database modes; canary intentionally uses its own SQLite in both", "No PG canary protocol support claimed", "Hosted CI/containers/production E2E NOT PERFORMED", "Docker absent", "No fresh search quality or paired gain", "IELTSv3 rejected8NEW blockers+5 inherited errors+1 accepted ambiguity; no apply", "Fresh original10 genuine baseline PREPARED ONLY at archive time", "No default/gold/STOP/merge/deploy/purchase change", "Runtime databases/cache/PGDATA/env/private Git/browser storage/traces excluded"],
           "files": files}
(DEST / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
(DEST / "README.md").write_text(f"# Genuine-Job harness exact-source full local gates\n\nSource{SOURCE}, snapshot3489f8fa, full13/13. Same4261 unique backend cases pass in two primary database modes (8522 executions); dedicated canary uses isolated SQLite in both. Coverage{coverage}%, frontend232, demoE2E79PASS/1skip, auth6, mypy383. Focused actual-module199PASS. Native flagFalse. App source remains budget3b3a; retained seed-demo evidence is explicitly historical unchanged-app proof.\n\nNo hosted CI/containers/production gate or search precision/recall is claimed. IELTSv3 independently rejected; exact source/logs preserved without changing tests. Fresh original10 plan remains prepared only at archive time. Secrets, runtime databases, caches and browser traces excluded.\n")
print(json.dumps({"receipt_sha256": sha(DEST / "receipt.json"), "selected_files": len(files), "selected_bytes": sum(f["bytes"] for f in files.values()), "coverage": coverage, "backend_unique": 4261, "full_passed": 13}))
