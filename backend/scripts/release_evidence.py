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
import hashlib
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


def portable_command(command: list[str]) -> str:
    """The command, without this machine's paths in it.

    `.venv/bin/python` was recorded as `/Users/<someone>/projects/...`, which
    tells a reader nothing they can run and names the machine into the bargain.
    Tokens that point inside the repository are recorded relative to it.
    """
    return " ".join(
        portable_path(Path(token)) if "/" in token else token for token in command
    )


def run(command: list[str], cwd: Path = BACKEND, timeout: int = 1800) -> dict[str, Any]:
    """Run a gate and record what it actually did."""
    try:
        proc = subprocess.run(
            command, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": portable_command(command),
            "exit_code": None,
            "result": "not_run",
            "detail": f"{type(exc).__name__}: {exc}"[:200],
        }
    combined = (proc.stdout + proc.stderr).strip()
    tail = combined.splitlines()[-25:]
    return {
        "command": portable_command(command),
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


#: What generating this record writes. A tree is "dirty" the moment the
#: generator runs, because the artifact and the documents rendered from it are
#: themselves tracked files — so a bare `working_tree_clean: false` said nothing
#: and quietly cast doubt on every gate beside it.
GENERATED_OUTPUTS = (
    "artifacts/release-evidence.json",
    "artifacts/accepted-pages.json",
    "artifacts/canary",
    "docs/evidence/RELEASE-EVIDENCE-2026-08-29.md",
)


#: Porcelain's status field is two columns and then a space. Slicing at a fixed
#: offset was wrong, because `git()` strips the whole output and that eats the
#: leading space of the *first* line only: " M path" arrived as "M path", so
#: the slice removed the path's first character and the artifact recorded
#: "rtifacts/release-evidence.json" — a filename that does not exist, in the
#: field whose entire job is to say precisely which files differed.
_PORCELAIN_STATUS = re.compile(r"^\s*[A-Z?!]{1,2}\s+")


def working_tree_state() -> dict[str, Any]:
    """What differed from HEAD while the gates above were being measured.

    The distinction that matters to a reader is not clean-or-not. It is whether
    the *sources* differed: a modified artifact is this run writing its own
    output, and a modified `app/` means the gates measured something that is
    not in any commit.
    """
    porcelain = git("status", "--porcelain")
    paths = sorted(
        _PORCELAIN_STATUS.sub("", line).strip().strip('"')
        for line in porcelain.splitlines()
        if line.strip()
    )
    generated = [p for p in paths if p.startswith(GENERATED_OUTPUTS)]
    other = [p for p in paths if p not in generated]
    return {
        "clean": not paths,
        "clean_ignoring_generated_outputs": not other,
        "uncommitted_paths": other,
        "generated_outputs_modified": generated,
    }


def canary_summary(directory: Path) -> dict[str, Any]:
    """Fold a canary run's own JSON into the record.

    Read rather than re-run: a live run takes half an hour and hits real
    university sites. The commit it was measured at is recorded alongside, so a
    number can never quietly outlive the code that produced it.
    """
    runs: list[dict[str, Any]] = []
    for path in sorted(directory.glob("run*/canary-*.json")):
        raw = path.read_bytes()
        report = json.loads(raw)
        rows = report if isinstance(report, list) else report.get("institutions", [])
        runs.append(
            {
                # Relative to the canary directory, not the basename.
                #
                # `portable_path` reduced `run1/canary-2026-08-29.json` and
                # `run2/canary-2026-08-29.json` to the same string, so three
                # runs appeared in the artifact as three identical rows —
                # indistinguishable from one file counted three times, which is
                # precisely what "three independent runs" has to rule out.
                "file": str(path.relative_to(directory)),
                # And the bytes behind the row. Two runs that genuinely agree
                # have different digests; a file read twice has one.
                "sha256": hashlib.sha256(raw).hexdigest(),
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
        raw = path.read_bytes()
        report = json.loads(raw)
        rows = report if isinstance(report, list) else report.get("institutions", [])
        holdout = {
            "file": str(path.relative_to(directory)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "institutions": len(rows),
            "programme_pages": sum(1 for r in rows if r.get("program_page_found")),
            "false_positives": sum(len(r.get("false_positives") or []) for r in rows),
        }
    programme = sorted(r["programme_pages"] for r in runs)
    # Which commit these numbers describe. Without it a measurement outlives
    # the code that produced it, which is how a document came to state 4/10
    # while the repository produced 8/10.
    head_file = directory / "HEAD.txt"
    distinct = {r["sha256"] for r in runs}
    return {
        "measured_at_commit": head_file.read_text().strip() if head_file.exists() else None,
        "runs": runs,
        #: How many of the runs are actually different bytes. A reader
        #: comparing this with `len(runs)` can see at once whether "three
        #: independent runs" describes three runs.
        "distinct_run_files": len(distinct),
        "runs_supplied": len(runs),
        "median_programme_pages": programme[len(programme) // 2] if programme else None,
        "worst_programme_pages": programme[0] if programme else None,
        "holdout": holdout,
    }


#: Fields an attestation must carry to be evidence of anything.
REQUIRED_ATTESTATION_FIELDS = (
    "result",
    "tested_sha",
    "head_sha",
    "head_tree",
    "run_url",
)


def check_run_gate(observation: dict[str, Any], *, head_sha: str) -> dict[str, Any]:
    """Record what GitHub publicly reported for the container gate.

    Weaker than the attestation and labelled so. The attestation is the bytes
    CI wrote, carrying the trees; this is the conclusion the public API reports
    for a commit, which is all that can be read without repository
    credentials. It is enough to say "CI ran this and it passed at this
    commit", and it is not enough to say what tree was tested — so it never
    claims to.
    """
    required = ("head_sha", "conclusion", "run_url")
    missing = [f for f in required if not observation.get(f)]
    base: dict[str, Any] = {
        "command": "./scripts/compose_smoke.sh",
        "evidence": "github check-run conclusion (public API)",
        "raw_observation": observation,
    }
    if missing:
        return {
            **base,
            "exit_code": None,
            "result": "not_run",
            "detail": f"observation is missing required field(s): {', '.join(missing)}",
        }
    if observation["head_sha"] != head_sha:
        return {
            **base,
            "exit_code": None,
            "result": "not_run",
            "detail": (
                f"observation is for {observation['head_sha'][:7]}, "
                f"not for {head_sha[:7]}"
            ),
        }
    passed = observation["conclusion"] == "success"
    return {
        **base,
        "exit_code": 0 if passed else 1,
        "result": "pass" if passed else "fail",
        "detail": (
            f"CI reported {observation['conclusion']} for this commit: "
            f"{observation['run_url']}"
        ),
        "head_sha": observation["head_sha"],
        "measured_by": "github-actions",
        "attestation_artifact": (
            "uploaded by the container-runtime job; downloading it needs "
            "repository credentials, so the full attestation is not embedded here"
        ),
    }


def attestation_gate(
    attestation: dict[str, Any], *, head_sha: str, head_tree: str
) -> dict[str, Any]:
    """Turn a CI attestation into a gate result, or refuse it.

    The previous version accepted any JSON whose `sha` matched HEAD. That
    trusted a hand-written file as though CI had produced it, and matched
    against `github.sha` — which on a `pull_request` is a synthetic merge
    commit, not the branch head. An artifact named for `ba15bbb` was in fact
    built from merge commit `6a95c5bd`.

    The tree is what is checked, not only the SHA. A commit id can be copied
    into a file; the tree is what the code actually was, and `head_tree` is the
    one identifier in the attestation that also exists outside CI's checkout.

    The raw attestation is stored verbatim with a digest. This function decides
    whether to *believe* it; it never rewrites it.
    """
    missing = [f for f in REQUIRED_ATTESTATION_FIELDS if not attestation.get(f)]
    digest = hashlib.sha256(
        json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    base: dict[str, Any] = {
        "command": attestation.get("command", "./scripts/compose_smoke.sh"),
        "raw_attestation": attestation,
        "attestation_sha256": digest,
    }

    def refuse(reason: str) -> dict[str, Any]:
        return {**base, "exit_code": None, "result": "not_run", "detail": reason}

    if missing:
        return refuse(f"attestation is missing required field(s): {', '.join(missing)}")
    if attestation["head_sha"] != head_sha:
        return refuse(
            f"attestation is for head {attestation['head_sha'][:7]}, "
            f"not for {head_sha[:7]}"
        )
    if attestation["head_tree"] != head_tree:
        return refuse(
            f"attestation is for tree {attestation['head_tree'][:7]}, "
            f"but this working copy is {head_tree[:7]}"
        )
    passed = attestation["result"] == "success"
    return {
        **base,
        "exit_code": 0 if passed else 1,
        "result": "pass" if passed else "fail",
        "detail": f"measured by CI: {attestation['run_url']}",
        "tested_sha": attestation["tested_sha"],
        "head_sha": attestation["head_sha"],
        "head_tree": attestation["head_tree"],
        "measured_by": "github-actions",
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
        "--container-check-run",
        type=Path,
        help=(
            "JSON naming the head SHA and the conclusion GitHub published for "
            "the container-runtime check. Weaker evidence than the full "
            "attestation — it is the public API's verdict, not the bytes CI "
            "wrote — and it is recorded as such, because downloading the "
            "attestation artifact needs repository credentials this machine "
            "does not have."
        ),
    )
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
    if args.container_check_run and args.container_check_run.exists():
        gates["container_runtime"] = check_run_gate(
            json.loads(args.container_check_run.read_text()),
            head_sha=git("rev-parse", "HEAD"),
        )
    if args.container_attestation and args.container_attestation.exists():
        gates["container_runtime"] = attestation_gate(
            json.loads(args.container_attestation.read_text()),
            head_sha=git("rev-parse", "HEAD"),
            head_tree=git("rev-parse", "HEAD^{tree}"),
        )

    artifact: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": git("rev-parse", "HEAD"),
        "base_commit": BASE_COMMIT,
        "commits_since_base": int(git("rev-list", "--count", f"{BASE_COMMIT}..HEAD") or 0),
        "working_tree": working_tree_state(),
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
