#!/usr/bin/env python
"""Produce one machine-readable record of what was actually verified.

Three documents described this release and disagreed with each other and with
the repository: programme recall was written as 4/10 in one place and 8/10 in
another, claims as 27 and as 51, accepted pages as 12 and as 20, the test count
as 772 and as 977, the commit count as 33 when it was 34. Every number had been
true when it was written. None of them was checked again.

Prose cannot be checked. `artifacts/release-evidence.json` can, and
`tests/test_documentation_consistency.py` fails when a document disagrees with
it.

Gates are recorded only when this script ran them. Anything it did not run says
so — `not_run` is a result, and it is the only honest one for a command nobody
executed. The container gate has been `not_run` on this machine throughout,
because no container runtime is installed.

    python scripts/release_evidence.py            # run the fast gates
    python scripts/release_evidence.py --canary DIR   # also fold in a canary
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
ARTIFACT = ROOT / "artifacts" / "release-evidence.json"
BASE_COMMIT = "2ebcbc6"


def run(command: list[str], cwd: Path = BACKEND, timeout: int = 1800) -> dict[str, Any]:
    """Run a gate and record what it actually did."""
    try:
        proc = subprocess.run(
            command, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": " ".join(command),
            "exit_code": None,
            "result": "not_run",
            "detail": f"{type(exc).__name__}: {exc}"[:200],
        }
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "result": "pass" if proc.returncode == 0 else "fail",
        "detail": tail[-1][:300] if tail else "",
    }


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True
    ).stdout.strip()


def count_tests(detail: str) -> int | None:
    match = re.search(r"(\d+) passed", detail)
    return int(match.group(1)) if match else None


def canary_summary(directory: Path) -> dict[str, Any]:
    """Fold a canary run's own JSON into the record.

    Read rather than re-run: a live run takes half an hour and hits real
    university sites. The commit it was measured at is recorded alongside, so a
    number can never quietly outlive the code that produced it.
    """
    runs: list[dict[str, Any]] = []
    for path in sorted(directory.glob("run*/canary-*.json")):
        report = json.loads(path.read_text())
        rows = report if isinstance(report, list) else report.get("institutions", [])
        runs.append(
            {
                "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "institutions": len(rows),
                "programme_pages": sum(1 for r in rows if r.get("program_page_found")),
                "scholarship_pages": sum(1 for r in rows if r.get("scholarship_page_found")),
                "claims": sum(r.get("claims") or 0 for r in rows),
                "false_positives": sum(len(r.get("false_positives") or []) for r in rows),
                "mean_completeness": round(
                    sum(r.get("completeness") or 0 for r in rows) / max(len(rows), 1), 4
                ),
            }
        )
    holdout = None
    for path in sorted(directory.glob("holdout/canary-*.json")):
        report = json.loads(path.read_text())
        rows = report if isinstance(report, list) else report.get("institutions", [])
        holdout = {
            "institutions": len(rows),
            "programme_pages": sum(1 for r in rows if r.get("program_page_found")),
            "false_positives": sum(len(r.get("false_positives") or []) for r in rows),
        }
    programme = sorted(r["programme_pages"] for r in runs)
    # Which commit these numbers describe. Without it a measurement outlives
    # the code that produced it, which is how a document came to state 4/10
    # while the repository produced 8/10.
    head_file = directory / "HEAD.txt"
    return {
        "measured_at_commit": head_file.read_text().strip() if head_file.exists() else None,
        "runs": runs,
        "median_programme_pages": programme[len(programme) // 2] if programme else None,
        "worst_programme_pages": programme[0] if programme else None,
        "holdout": holdout,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary", type=Path, help="directory holding canary run output")
    parser.add_argument("--out", type=Path, default=ARTIFACT)
    args = parser.parse_args()

    py = str(BACKEND / ".venv" / "bin" / "python")
    gates: dict[str, dict[str, Any]] = {}

    gates["backend_lint"] = run([py, "-m", "ruff", "check", "."])
    gates["backend_types"] = run([py, "-m", "mypy", "app", "tests", "scripts"])
    gates["backend_tests_sqlite"] = run([py, "-m", "pytest"])
    gates["backend_tests_postgres"] = run(
        [py, str(BACKEND / "scripts" / "pg.py"), py, "-m", "pytest"]
    )
    gates["crash_recovery"] = run([py, str(BACKEND / "scripts" / "crash_test.py")])
    gates["python_dependencies"] = run([py, "-m", "pip_audit"])
    gates["frontend_types"] = run(["npm", "run", "typecheck"], cwd=ROOT / "frontend")
    gates["frontend_lint"] = run(["npm", "run", "lint"], cwd=ROOT / "frontend")
    gates["frontend_tests"] = run(["npx", "vitest", "run"], cwd=ROOT / "frontend")
    gates["frontend_build"] = run(["npm", "run", "build"], cwd=ROOT / "frontend")
    gates["node_dependencies"] = run(["npm", "audit"], cwd=ROOT / "frontend")

    # Never claimed, only ever recorded when it happened. No container runtime
    # is installed on this machine, so this has never been anything else.
    gates["container_runtime"] = {
        "command": "./scripts/compose_smoke.sh",
        "exit_code": None,
        "result": "not_run",
        "detail": (
            "no container runtime on this machine: docker, podman, colima, "
            "nerdctl, finch and lima are all absent"
        ),
    }

    artifact: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": git("rev-parse", "HEAD"),
        "base_commit": BASE_COMMIT,
        "commits_since_base": int(git("rev-list", "--count", f"{BASE_COMMIT}..HEAD") or 0),
        "working_tree_clean": git("status", "--porcelain") == "",
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
        "gates": gates,
        "counts": {
            "backend_tests": count_tests(gates["backend_tests_sqlite"]["detail"]),
            "frontend_tests": count_tests(gates["frontend_tests"]["detail"]),
        },
    }

    if args.canary:
        artifact["live_discovery"] = canary_summary(args.canary)

    failing = sorted(k for k, v in gates.items() if v["result"] == "fail")
    not_run = sorted(k for k, v in gates.items() if v["result"] == "not_run")
    artifact["open_gates"] = {"failing": failing, "not_run": not_run}
    # A verdict computed from the gates, so it cannot drift from them. READY is
    # not something a document gets to assert on its own.
    artifact["verdict"] = "READY" if not failing and not not_run else "NOT READY"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"verdict: {artifact['verdict']}")
    if failing:
        print(f"  failing: {', '.join(failing)}")
    if not_run:
        print(f"  not run: {', '.join(not_run)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
