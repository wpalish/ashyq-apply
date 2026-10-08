"""Archive only the actual repaired-source full result; no execution or network."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

OWN = Path(__file__).resolve().parent
REPO = OWN.parent.parent / "ashyq-apply"
RUN = Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T004040Z-check-bc90e5dc")
DEST = REPO / "docs/process/evidence/search-loop/2026-10-07/local-round9/strict-first-refusal-full"
SOURCE = "7c74a12d71bd00228014c11d194928d223e110be"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
summary = json.loads((RUN / "summary.json").read_text())
assert summary["status"] == "passed" and len(summary["steps"]) == 13
assert all(step["exit_code"] == 0 for step in summary["steps"])
source = summary["source"]
assert source["source_head"] == SOURCE and source["source_status"] == ""
assert source["source_tree_sha256"] == "19f349a0a242478e13f95e1905e8f41662a769b579833b004cafb03b73825c9a"
code_paths = {n: digest for n, digest in source["files"].items() if n.startswith(("backend/app/", "backend/tests/", "backend/evaluation/", "backend/scripts/", "frontend/"))}
assert all(sha(REPO / name) == digest for name, digest in code_paths.items())
cases = {}
for mode in ("backend-sqlite", "backend-postgresql"):
    rows = list(ET.parse(RUN / (mode + ".xml")).getroot().iter("testcase"))
    assert len(rows) == 4292
    assert not any(any(row.find(kind) is not None for kind in ("failure", "error", "skipped")) for row in rows)
    cases[mode] = {(row.get("classname"), row.get("name")) for row in rows}
assert cases["backend-sqlite"] == cases["backend-postgresql"] and len(cases["backend-sqlite"]) == 4292
coverage = float(re.search(r"Total coverage: ([0-9.]+)%", (RUN / "backend-sqlite.log").read_text())[1])
assert coverage >= 92
assert "232 passed" in (RUN / "frontend-tests.log").read_text()
assert "79 passed" in (RUN / "e2e.log").read_text() and "1 skipped" in (RUN / "e2e.log").read_text()
assert "6 passed" in (RUN / "e2e-auth.log").read_text()
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
def copy(path, name):
    body = path.read_bytes()
    assert not any(secret in body for secret in secrets), "Configured secret detected"
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    files[name] = {"original": str(path), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
for name in ("summary.json", "source-manifest.json", "backend-sqlite.xml", "backend-postgresql.xml", *[step["name"] + ".log" for step in summary["steps"]]):
    copy(RUN / name, "package/" + name)
copy(Path(__file__), "parent/finalize_retry_full.py")
peer = OWN.parent / "b-ielts-v4-review"
for name in ("MANIFEST.json", "review.ru.md", "receipt.json", "independent-controls.offline.json", "replay.py"):
    if (peer / name).is_file():
        copy(peer / name, "parallel-rejected-ielts-v4/" + name)
receipt = {
    "at_utc": datetime.now(UTC).isoformat(), "status": "EXACT_REPAIRED_SOURCE_FULL_LOCAL_PASS",
    "source_head": SOURCE, "source_tree_sha256": source["source_tree_sha256"],
    "started_at": summary["started_at"], "finished_at": summary["finished_at"],
    "gates_passed": 13, "gates_failed": 0, "backend_unique_cases": 4292,
    "backend_two_primary_mode_executions": 8584, "coverage_percent_sqlite": coverage,
    "frontend_tests": 232, "demo_e2e": {"passed": 79, "skipped": 1}, "auth_e2e_passed": 6,
    "mypy_files": 383, "source_paths_verified_unchanged": len(code_paths),
    "strict_first_refusal_mock_tests_added": 31, "provider_source_unchanged": True,
    "native_budget_default": False, "live_provider_model_university_calls": 0,
    "configured_secret_matches": 0,
    "limits": ["Canary deliberately uses isolated SQLite in both PRIMARY database suite modes", "No PostgreSQL canary protocol support", "Final metering envelope cannot time its own last byte", "No live quality/gain/default/launch proof", "No hosted workflows or fake checks", "Containers/Docker and production E2E not performed", "IELTSv4 independently rejected4newfalseminima+3newcorrectfactlosses; no apply", "Runtime databases/cache/PGDATA/env/private Git/browser storage excluded"],
    "files": files,
}
(DEST / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"receipt_sha256": sha(DEST / "receipt.json"), "selected_files": len(files), "selected_bytes": sum(v["bytes"] for v in files.values()), "gates": 13, "backend_unique": 4292, "coverage": coverage}))
