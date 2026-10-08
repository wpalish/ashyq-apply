"""Pin, write ahead, then port exactly the accepted capture files."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

own = Path(__file__).parent
repo = own.parent.parent / "ashyq-apply"
proposal = own.parent.parent / "local-round8/a-genuine-canary/revision2-final"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt_path = proposal / "receipt.json"
assert sha(receipt_path) == "3fd85544292165d6b886ce2d9d2a65bc576bb75d3e601a37d27626c310259245"
receipt = json.loads(receipt_path.read_text())
assert sha(proposal / "genuine-canary-revision2-final.patch") == receipt["patch_sha256"]
for path, digest in receipt["source_originals"].items():
    assert sha(repo / "backend" / path) == digest, path
pins = receipt["source_proposals"] | receipt["future_tests"]
for path, digest in pins.items():
    assert sha(proposal / "proposed" / path) == digest, path
    if path.startswith("tests/"):
        assert not (repo / "backend" / path).exists(), path
for entry in receipt["actual_module_imports"]["actual_modules"]:
    assert sha(Path(entry["path"])) == entry["sha256"], entry["name"]
assert "UNIVERSITY_READ_BUDGET = False" in (repo / "backend/app/pipeline/read_budget.py").read_text()
plan_path = own / "PLAN.json"
plan = json.loads(plan_path.read_text())
assert plan["status"] == "PREPARED_ONLY_AWAIT_FINAL_PIN"
plan.update(status="ACCEPTED_FOR_ACTUAL_MODULE_TRANSFER", receipt_sha256=sha(receipt_path),
            final_file_pins=pins, accepted_at=datetime.now(timezone.utc).isoformat())
plan_path.write_text(json.dumps(plan, indent=2) + "\n")
handoff_path = repo / "docs/process/HANDOFF.md"
handoff = handoff_path.read_text()
anchor = "## 5. NEXT STEP — exact and executable\n"
assert handoff.count(anchor) == 1
writeahead = (
    "\n**2026-10-08 accepted [search-fenced-capture] exact write-ahead:** parent inspected final genuine-Job "
    "enqueue/claim/unmodified Worker dispatch, post-cleanup report, fixed safe causes, original typed controls, "
    "raw/output clock and engine/heartbeat cleanup. Sealed receipt3fd85544292165d6b886ce2d9d2a65bc576bb75d3e601a37d27626c310259245; "
    "patch6128ad638fd156c703046348c7c60c5b58350d71b26a08eab364408fb4dfd57a. "
    "Now port ONLY canary9a05edec, live89633925, normal-import tests0336048d/dd41ddf3 from revision2-final, "
    "against originals37f60bcf/3d14e350 and six actual app pins. External conftest/loader is excluded. "
    "Run actual repository protocol+legacy controls and relevant native guard tests; preserve first failures, "
    "fix integration only without weakening assertions, then exact-source full LOCAL gates. Final external50PASS "
    "is focused synthetic SQLite evidence, not a parent/full/live score. Strict outer6/60/120 unchanged; "
    "native flagFalse, final meter cannot measure its own last byte, arbitrary existing app errors/logs unchanged. "
    "No source/default/gold/STOP/live promotion. A independently reviews IELTSv3; B external narrow language routing.\n"
)
handoff_path.write_text(handoff.replace(anchor, anchor + writeahead, 1))
for path in pins:
    target = repo / "backend" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((proposal / "proposed" / path).read_bytes())
result = {"status": "APPLIED_UNVERIFIED", "receipt_sha256": sha(receipt_path),
          "files": {path: sha(repo / "backend" / path) for path in pins},
          "plan_sha256": sha(plan_path), "network_calls": 0}
(own / "apply.receipt.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
