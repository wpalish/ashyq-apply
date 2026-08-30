#!/usr/bin/env python
"""Write the measured sections of the release documents from the artifact.

Hand-maintained numbers drift, and the ways they drift are not obvious. A
`sed` with an empty variable turned `**PASS** — 1858 passed` into
`**PASS** —  passed` in six rows at once, and the consistency test did not
notice because its rule was "if a number is here it must match" and a blank is
not a number. Elsewhere the README carried 768 tests and a recall of 1/10 for
weeks after both were false.

So the measured sections are generated. What a person writes is the prose
around them; what a machine measured, a machine writes.

    python scripts/render_release_docs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT = ROOT / "artifacts" / "release-evidence.json"
EVIDENCE = ROOT / "docs" / "evidence" / "RELEASE-EVIDENCE-2026-08-29.md"

BEGIN = "<!-- generated:gates:begin -->"
END = "<!-- generated:gates:end -->"

#: Gate key -> the row label a reader sees.
LABELS = {
    "backend_lint": "Lint (backend)",
    "backend_types": "Types (backend)",
    "backend_tests_sqlite": "Backend tests, SQLite",
    "backend_tests_postgres": "Backend tests, PostgreSQL",
    "crash_recovery": "Crash recovery",
    "python_dependencies": "Python dependencies",
    "frontend_types": "Frontend types",
    "frontend_lint": "Frontend lint",
    "frontend_tests": "Frontend unit tests",
    "frontend_build": "Frontend build",
    "node_dependencies": "Node dependencies",
    "container_runtime": "Container runtime",
}

RESULT_TEXT = {"pass": "**PASS**", "fail": "**FAIL**", "not_run": "**NOT RUN**"}


def gate_table(artifact: dict) -> str:
    lines = [
        "| Gate | Command | Exit | Result |",
        "|---|---|---|---|",
    ]
    for key, gate in sorted(artifact["gates"].items()):
        label = LABELS.get(key, key)
        exit_code = "—" if gate["exit_code"] is None else str(gate["exit_code"])
        detail = (gate.get("detail") or "").replace("|", "\\|")[:180]
        result = RESULT_TEXT.get(gate["result"], gate["result"])
        lines.append(
            f"| {label} | `{gate['command']}` | {exit_code} | {result} — {detail} |"
        )

    counts = artifact["counts"]
    lines += [
        "",
        "| Measured | Value |",
        "|---|---|",
        f"| Backend tests | {counts['backend_tests']} |",
        f"| Frontend unit tests | {counts['frontend_tests']} |",
        f"| Commit described | `{artifact['head'][:7]}` |",
        f"| Commits since `{artifact['base_commit']}` | {artifact['commits_since_base']} |",
        f"| Verdict | **{artifact['verdict']}** |",
    ]

    live = artifact.get("live_discovery")
    if live:
        runs = live["runs"]
        lines += [
            "",
            "| Live discovery | Value | Bar |",
            "|---|---|---|",
            f"| Programme pages per run | {', '.join(str(r['programme_pages']) for r in runs)} | — |",
            f"| Median programme pages | {live['median_programme_pages']} | ≥ 8 |",
            f"| Worst programme pages | {live['worst_programme_pages']} | ≥ 7 |",
            f"| Holdout programme pages | {live['holdout']['programme_pages']}/{live['holdout']['institutions']} | ≥ 4 |",
            f"| Zero-tolerance false positives | {sum(r['false_positives'] for r in runs)} | 0 |",
            f"| Mean decision-grade completeness | {sum(r['mean_completeness'] for r in runs) / len(runs):.1%} | ≥ 70% |",
            f"| Measured at | `{live.get('measured_at_commit', 'unknown')}` | — |",
        ]

    open_gates = artifact["open_gates"]
    lines += ["", "**Open:**"]
    if not any(open_gates.values()):
        lines.append("- nothing")
    for label, items in (
        ("failing gate", open_gates["failing"]),
        ("gate not run", open_gates["not_run"]),
        ("product threshold", open_gates.get("product_thresholds", [])),
    ):
        for item in items:
            lines.append(f"- {label}: {item}")
    return "\n".join(lines)


def main() -> int:
    if not ARTIFACT.exists():
        print(f"FAIL: {ARTIFACT} does not exist; nothing to render from")
        return 1
    artifact = json.loads(ARTIFACT.read_text())

    text = EVIDENCE.read_text()
    if BEGIN not in text or END not in text:
        print(f"FAIL: {EVIDENCE.name} has no generated block; add {BEGIN} / {END}")
        return 1
    rendered = f"{BEGIN}\n\n{gate_table(artifact)}\n\n{END}"
    text = re.sub(
        re.escape(BEGIN) + r".*?" + re.escape(END), rendered, text, flags=re.DOTALL
    )
    EVIDENCE.write_text(text)
    print(f"rendered {EVIDENCE.relative_to(ROOT)} from {ARTIFACT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
