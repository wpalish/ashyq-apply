"""Hash-pin reviewed external bytes; never generate or modify repository code."""
from __future__ import annotations

import difflib
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = Path("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend")
STOP = REPO.parent.parent / "development-STOP.json"
EXISTING = [
    "app/adapters/base.py", "app/pipeline/runner.py", "app/catalogue/discovery.py",
    "app/adapters/discovery/live_discovery.py", "app/adapters/discovery/catalog_walker.py",
]
NEW = ["app/pipeline/control.py", "app/pipeline/read_budget.py"]
DEPENDENCIES = [
    "app/adapters/fetching.py", "app/jobs/store.py", "app/jobs/worker.py",
    "app/models/jobs.py", "app/models/research.py", "app/db.py", "app/config.py",
    "app/adapters/requirements/web_requirements.py", "app/adapters/cost/web_costs.py",
    "app/adapters/government/web_government.py", "app/adapters/scholarship/web_scholarships.py",
    "app/pipeline/state.py",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble() -> dict:
    if not STOP.is_file():
        raise RuntimeError("Sticky STOP must remain present; no external execution authorized")
    originals = {path: digest(BASE / "original" / path) for path in EXISTING}
    current = {path: digest(REPO / path) for path in EXISTING}
    if originals != current:
        raise RuntimeError("Production source drift: do not mislabel the red baseline")
    for path in NEW:
        if (REPO / path).exists():
            raise RuntimeError(f"New proposed path now exists in production: {path}")
    patch = ""
    for path in EXISTING + NEW:
        before = (BASE / "original" / path).read_text() if path in EXISTING else ""
        after = (BASE / "proposed" / path).read_text()
        patch += "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/backend/" + path if path in EXISTING else "/dev/null",
            tofile="b/backend/" + path,
        ))
    (BASE / "readguard.patch").write_text(patch)
    return {
        "kind": "external_actual_production_path_readguard_prototype",
        "created_at": datetime.now(UTC).isoformat(),
        "applied_to_repository": False, "network_calls": 0,
        "default_flag": {"UNIVERSITY_READ_BUDGET": False},
        "contract": "60 committed pre-get reservations per stable university per fenced research Job.id decision episode",
        "original_source_sha256": originals,
        "current_repository_matches_originals": originals == current,
        "proposed_source_sha256": {path: digest(BASE / "proposed" / path) for path in EXISTING + NEW},
        "unchanged_dependency_sha256": {path: digest(REPO / path) for path in DEPENDENCIES},
        "sticky_stop_sha256": digest(STOP),
        "patch_sha256": digest(BASE / "readguard.patch"),
    }


if __name__ == "__main__":
    result = assemble()
    (BASE / "ready-source-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"patch_sha256": result["patch_sha256"],
                      "runner_sha256": result["proposed_source_sha256"]["app/pipeline/runner.py"]}))
