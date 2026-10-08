"""Read a terminal full and preserve finite original logs; no tests or app imports."""
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent
repo = root.parents[1] / "ashyq-apply"
run = Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T085213Z-check-97246db0")
old_run = run.parent / "20261008T053629Z-check-6693acd5"
destination = root / "corrected-full-raw"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


summary = json.loads((run / "summary.json").read_bytes())
assert summary["status"] == "passed" and len(summary["steps"]) == 13
assert all(step["exit_code"] == 0 for step in summary["steps"])
assert not summary["github_actions_started"] and not summary["live_network_capture_started"]
source = json.loads((root / "source-after-schema-1002.json").read_bytes())["file_sha256"]
manifest = json.loads((run / "source-manifest.json").read_bytes())
assert manifest["source_head"] == "eb81c127c8a2a5154dd0d6f7ac115d8dc4464288"
assert manifest["source_status"] == ""
for name, digest in source.items():
    assert sha(repo / name) == digest == sha(run / "source" / name)
    assert manifest["files"][name] == digest

cases = []
old_cases = []
for name in ("backend-sqlite.xml", "backend-postgresql.xml"):
    tree = ET.parse(run / name)
    current = tree.findall(".//testcase")
    identities = {(row.attrib["classname"], row.attrib["name"]) for row in current}
    assert len(current) == len(identities) == 4369
    assert all(not list(row) for row in current), name
    before = ET.parse(old_run / name).findall(".//testcase")
    previous = {(row.attrib["classname"], row.attrib["name"]) for row in before}
    assert len(before) == len(previous) == 4349 and previous <= identities
    added = identities - previous
    assert len(added) == 20 and all(row[0] == "tests.test_local_pilot" for row in added)
    cases.append(identities)
    old_cases.append(previous)
assert cases[0] == cases[1] and old_cases[0] == old_cases[1]
stop = repo.parent / "local-round7/provider-STOP.json"
assert sha(stop) == "65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d"

names = list(json.loads((root / "first-full-raw/ready-manifest.json").read_bytes())["files"])
assert len(names) == 17 and not destination.exists()
destination.mkdir()
files = {}
for name in names:
    original = run / name
    copied = destination / name
    assert original.is_file() and not original.is_symlink()
    shutil.copyfile(original, copied)
    assert sha(original) == sha(copied)
    files[name] = {"sha256": sha(copied), "bytes": copied.stat().st_size}
for name, digest in source.items():
    assert sha(repo / name) == digest
receipt = {
    "status": "CORRECTED_FULL_13_OF_13_PASS_NO_QUALITY_CLAIM",
    "time": datetime.now(timezone.utc).isoformat(),
    "full_run": str(run),
    "source_head": manifest["source_head"],
    "source_tree_sha256": manifest["source_tree_sha256"],
    "source1002_primary_frozen_exact": True,
    "both_backend_unique_cases": 4369,
    "same_original_cases_preserved": 4349,
    "new_unique_cases": 20,
    "selected_original_files": 17,
    "selected_original_bytes": sum(row["bytes"] for row in files.values()),
    "STOP_sha256": sha(stop),
    "files": files,
    "qualification": "Physical copies of this one terminal full; no new experiment, scoring, runtime admission, hosted check or production claim.",
}
p = destination / "ready-manifest.json"
p.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: value for key, value in receipt.items() if key != "files"}))
print("ready_manifest_sha256", sha(p))
