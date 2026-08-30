#!/usr/bin/env python
"""Produce one machine-readable record of what was actually verified.

`artifacts/release-evidence.json` is a **dated historical snapshot**, and only
that. A file checked into a repository can only ever describe a commit before
itself — the commit that records a count is itself a commit — so it is not, and
cannot be, proof about the HEAD it sits on. The commit it describes is written
into it, and the consistency test compares documents against *that* commit
rather than against whatever HEAD happens to be.

The authority for a given commit is the CI attestation, produced by the
container-runtime job and keyed by `GITHUB_SHA`, which nobody can edit after
the fact.

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
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
ARTIFACT = ROOT / "artifacts" / "release-evidence.json"
BASE_COMMIT = "2ebcbc6"

#: Product thresholds, stated here rather than in prose so the verdict is
#: computed against them. Set before the results were seen; changing one after
#: reading a number is how a bar stops meaning anything.
HOLDOUT_PROGRAMME_PAGES_BAR = 4
MEDIAN_PROGRAMME_PAGES_BAR = 8
EXTRACTION_COMPLETENESS_BAR = 0.70


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
    combined = (proc.stdout + proc.stderr).strip()
    tail = combined.splitlines()[-25:]
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "result": "pass" if proc.returncode == 0 else "fail",
        # The last line alone lost the numbers: vitest prints a duration after
        # its count. A bounded tail keeps them and still cannot grow unbounded.
        "detail": tail[-1][:300] if tail else "",
        "output_tail": "\n".join(tail)[:4000],
    }


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True, text=True
    ).stdout.strip()


def count_tests(output: str) -> int | None:
    """How many tests passed, from whatever the tool printed.

    Searches the whole captured tail rather than one line. `run()` used to keep
    only the last, and vitest ends with "Duration 779ms (...)" — the count is
    three lines above it — so `frontend_tests` came out `null`, which reads as
    "not measured" when it had been measured perfectly well.

    Returns None when anything failed: a partial count is worse than no count,
    because it looks like a result.
    """
    if re.search(r"\d+ (failed|error)", output):
        return None
    matches = re.findall(r"(\d+) passed", output)
    return int(matches[-1]) if matches else None


def portable_path(path: Path) -> str:
    """A reference to a file that means something on another machine.

    Canary provenance was an absolute path into a per-session scratch
    directory: real for one machine for one afternoon, and unverifiable by
    anyone else. Inside the repository it becomes a relative path; outside, the
    basename, which is the part that still identifies the file.
    """
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


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
                "file": portable_path(path),
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


def container_gate() -> dict[str, Any]:
    """Run the container smoke test if a runtime exists; say so if not."""
    runtimes = ("docker", "podman", "nerdctl", "finch")
    available = [r for r in runtimes if shutil.which(r)]
    if not available:
        return {
            "command": "./scripts/compose_smoke.sh",
            "exit_code": None,
            "result": "not_run",
            "detail": (
                "no container runtime found on this machine (looked for "
                + ", ".join(runtimes)
                + "); this gate is measured by the container-runtime CI job"
            ),
        }
    return run(["./scripts/compose_smoke.sh"], cwd=ROOT, timeout=2400)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary", type=Path, help="directory holding canary run output")
    parser.add_argument("--out", type=Path, default=ARTIFACT)
    parser.add_argument(
        "--container-attestation",
        type=Path,
        help=(
            "JSON recording what CI observed for the container gate. This "
            "machine has no container runtime, so the gate cannot be measured "
            "here; the attestation carries the SHA that was tested, the run "
            "URL and the conclusion, and is only honoured when its SHA matches "
            "the commit this artifact describes."
        ),
    )
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

    # Observed, not asserted.
    #
    # This was hardcoded to `not_run` with a note about no container runtime
    # being installed. That was true when it was written and false the moment
    # CI ran the gate — an artifact stating a result it never observed is
    # precisely what this file exists to prevent. It runs the smoke test when a
    # runtime exists, and otherwise records that it could not, naming what it
    # looked for.
    gates["container_runtime"] = container_gate()
    if args.container_attestation and args.container_attestation.exists():
        attested = json.loads(args.container_attestation.read_text())
        head = git("rev-parse", "HEAD")
        if attested.get("sha") == head:
            gates["container_runtime"] = {
                "command": attested.get("command", "./scripts/compose_smoke.sh"),
                "exit_code": 0 if attested.get("result") == "success" else 1,
                "result": "pass" if attested.get("result") == "success" else "fail",
                "detail": f"measured by CI: {attested.get('run_url', 'unknown run')}",
                "attested_sha": attested["sha"],
                "measured_by": "github-actions",
            }
        else:
            gates["container_runtime"]["detail"] += (
                f"; an attestation was supplied for {str(attested.get('sha'))[:7]}, "
                f"which is not this commit ({head[:7]})"
            )

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
            "backend_tests": count_tests(gates["backend_tests_sqlite"]["output_tail"]),
            "frontend_tests": count_tests(gates["frontend_tests"]["output_tail"]),
        },
    }

    if args.canary:
        artifact["live_discovery"] = canary_summary(args.canary)

    failing = sorted(k for k, v in gates.items() if v["result"] == "fail")
    not_run = sorted(k for k, v in gates.items() if v["result"] == "not_run")

    # Product thresholds, which no amount of green technical gates substitutes
    # for. A release that builds, tests and deploys perfectly and cannot answer
    # an applicant's questions is not ready; it is only shippable.
    product: list[str] = []
    live = artifact.get("live_discovery")
    if live:
        holdout = live.get("holdout") or {}
        found, total = holdout.get("programme_pages"), holdout.get("institutions")
        if found is not None and found < HOLDOUT_PROGRAMME_PAGES_BAR:
            product.append(
                f"holdout programme pages {found}/{total} against a bar of "
                f"{HOLDOUT_PROGRAMME_PAGES_BAR}"
            )
        median = live.get("median_programme_pages")
        if median is not None and median < MEDIAN_PROGRAMME_PAGES_BAR:
            product.append(
                f"median programme pages {median} against a bar of "
                f"{MEDIAN_PROGRAMME_PAGES_BAR}"
            )
        completeness = [r["mean_completeness"] for r in live.get("runs", [])]
        if completeness:
            mean = sum(completeness) / len(completeness)
            if mean < EXTRACTION_COMPLETENESS_BAR:
                product.append(
                    f"decision-grade extraction completeness {mean:.1%} against "
                    f"a bar of {EXTRACTION_COMPLETENESS_BAR:.0%}"
                )
        if any(r["false_positives"] for r in live.get("runs", [])):
            product.append("a zero-tolerance false positive was recorded")
    else:
        product.append("no live discovery measurement was supplied")

    artifact["open_gates"] = {
        "failing": failing,
        "not_run": not_run,
        "product_thresholds": product,
    }
    # Computed, never asserted. READY is not something a document gets to
    # claim on its own, and technical gates alone do not earn it.
    artifact["verdict"] = (
        "READY" if not failing and not not_run and not product else "NOT READY"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"verdict: {artifact['verdict']}")
    if failing:
        print(f"  failing: {', '.join(failing)}")
    if not_run:
        print(f"  not run: {', '.join(not_run)}")
    for item in product:
        print(f"  product: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
