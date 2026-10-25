"""scripts/pre_merge.sh runs exactly the CI gates (GATE-1).

Three red CI stretches on 2026-10-25 were each a gate that exists in ``ci.yml`` and was not run
before the push. The script is the one command that runs them locally; these tests hold it to
``ci.yml`` so the two cannot drift apart without a red test. Everything here goes through
``--dry-run``, which prints every command and runs none.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/pre_merge.sh"
CI = ROOT / ".github/workflows/ci.yml"
PACKAGE = ROOT / "frontend/package.json"

# CI lines that build the machine rather than gate the code: a local tree has them already
# (link_worktree_env.sh links the venv and node_modules in).
SETUP = (
    re.compile(r"^python -m venv "),
    re.compile(r"^(\S*/)?pip install "),
    re.compile(r"^npm ci\b"),
    re.compile(r"^npx .*playwright install\b"),
)
ENV = re.compile(r"^([A-Z_][A-Z0-9_]*)=\S+\s+")
COMMAND = re.compile(r"^\+ \(([^)]*)\) (.*)$")


def ci_commands(job: str) -> list[str]:
    document: dict[Any, Any] = yaml.safe_load(CI.read_text())
    commands = []
    for step in document["jobs"][job]["steps"]:
        for line in str(step.get("run", "")).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)
    return commands


def normalise_ci(command: str) -> tuple[str, list[str]]:
    """CI's form → the script's: no ``--prefix frontend``, the suite through run_suite.sh."""
    env = []
    while found := ENV.match(command):
        env.append(found.group(1))
        command = command[found.end() :]
    command = re.sub(r"\s+--prefix frontend\b", "", command)
    if command.startswith(".venv/bin/pytest"):
        command = "scripts/run_suite.sh" + command[len(".venv/bin/pytest") :]
    return command, env


def dry_run(*args: str, changed: list[str] | None = None, tmp_path: Path | None = None) -> str:
    argv = ["bash", str(SCRIPT), "--dry-run", "--base", "HEAD", *args]
    if changed is not None:
        assert tmp_path is not None
        listing = tmp_path / "changed.txt"
        listing.write_text("".join(f"{p}\n" for p in changed))
        argv += ["--changed", str(listing)]
    done = subprocess.run(argv, capture_output=True, text=True, check=False, cwd=ROOT)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def commands_of(output: str) -> list[tuple[str, str, list[str]]]:
    """(directory, command without its env assignments, env names) of every printed command."""
    found = []
    for line in output.splitlines():
        match = COMMAND.match(line)
        if not match:
            continue
        command = match.group(2)
        if command.startswith("env "):
            command = command[len("env ") :]
        env = []
        while assignment := ENV.match(command):
            env.append(assignment.group(1))
            command = command[assignment.end() :]
        found.append((match.group(1), command, env))
    return found


def test_the_script_parses() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


@pytest.mark.parametrize("job", ["backend", "frontend"])
def test_every_ci_gate_command_is_run_by_the_script(job: str, tmp_path: Path) -> None:
    printed = commands_of(dry_run("--scope", "all", "--pg", "--e2e", "always"))
    gates = [c for c in ci_commands(job) if not any(p.search(c) for p in SETUP)]
    assert gates, f"ci.yml job {job} has no gate commands left - the allow-list ate them"
    for raw in gates:
        want, env = normalise_ci(raw)
        hits = [p for p in printed if p[1] == want or p[1].startswith(want + " ")]
        assert hits, f"ci.yml ({job}) runs {raw!r}; pre_merge.sh does not run {want!r}"
        assert any(set(env) <= set(p[2]) for p in hits), f"{raw!r}: env {env} not passed"
        if want.startswith("npm "):
            assert all(p[0] == "frontend" for p in hits), f"{want!r} not run in frontend/"
        if want.startswith(".venv/bin/") and "pg.py" not in want:
            assert all(p[0] == "backend" for p in hits), f"{want!r} not run in backend/"


def test_the_script_runs_the_three_browser_suites_of_package_json_in_ci_order() -> None:
    scripts = json.loads(PACKAGE.read_text())["scripts"]
    suites = [
        name
        for name, body in scripts.items()
        if name.startswith("e2e") and "playwright test" in body
    ]
    assert len(suites) == 3, suites
    printed = [c for _, c, _ in commands_of(dry_run("--scope", "all", "--e2e", "always"))]
    ran = [c.removeprefix("npm run ") for c in printed if re.match(r"npm run e2e", c)]
    assert sorted(ran) == sorted(suites)
    ci_order = [
        normalise_ci(c)[0].removeprefix("npm run ")
        for c in ci_commands("frontend")
        if c.startswith("npm run e2e")
    ]
    assert ran == ci_order


BACKEND_GATES = [
    ".venv/bin/ruff check app tests evaluation",
    ".venv/bin/ruff format --check app tests evaluation",
    ".venv/bin/mypy app tests evaluation",
    "scripts/run_suite.sh --cov=app --cov-fail-under=92 -n 4 tests",
    ".venv/bin/python seed_demo.py",
]
FRONTEND_GATES = [
    "npm run typecheck",
    "npm run lint",
    "npm test -- --run",
    "npm run build",
    "npm run e2e",
    "npm run e2e:auth",
    "npm run e2e:kb",
]


def test_a_docs_only_diff_runs_the_commit_check_alone(tmp_path: Path) -> None:
    output = dry_run(changed=["docs/process/HANDOFF.md", "AGENTS.md"], tmp_path=tmp_path)
    assert commands_of(output) == []
    assert re.findall(r"^\+ check: (.*)$", output, re.M) == ["commits: Agent: trailer, no wip:"]
    assert "docs only" in output


def test_a_backend_diff_runs_the_four_backend_gates_and_the_demo(tmp_path: Path) -> None:
    printed = [
        c for _, c, _ in commands_of(dry_run(changed=["backend/app/x.py"], tmp_path=tmp_path))
    ]
    for gate in BACKEND_GATES:
        assert gate in printed, gate
    assert not any(c.startswith("npm ") for c in printed)
    assert ".venv/bin/python scripts/pg.py .venv/bin/pytest -q -n 4 tests" not in printed


def test_a_frontend_diff_runs_the_four_frontend_gates_and_the_three_suites(tmp_path: Path) -> None:
    output = dry_run(changed=["frontend/src/App.tsx"], tmp_path=tmp_path)
    printed = [c for _, c, _ in commands_of(output)]
    assert [c for c in printed if c.startswith("npm ")] == FRONTEND_GATES
    assert not any(c.startswith(".venv/bin/") for c in printed)
    assert "precondition: ports 5173/8099 free" in output


def test_e2e_never_turns_a_frontend_diff_red(tmp_path: Path) -> None:
    listing = tmp_path / "changed.txt"
    listing.write_text("frontend/src/App.tsx\n")
    argv = ["bash", str(SCRIPT), "--dry-run", "--base", "HEAD", "--e2e", "never"]
    done = subprocess.run(
        [*argv, "--changed", str(listing)], capture_output=True, text=True, check=False, cwd=ROOT
    )
    assert done.returncode == 1
    assert "SKIPPED" in done.stdout
    assert "npm run e2e" not in done.stdout


def test_a_workflow_diff_parses_it_and_runs_the_workflow_tests(tmp_path: Path) -> None:
    output = dry_run(
        changed=[".github/workflows/ci.yml", "scripts/run_suite.sh"], tmp_path=tmp_path
    )
    printed = [c for _, c, _ in commands_of(output)]
    assert any("yaml.safe_load" in c and c.endswith(".github/workflows/ci.yml") for c in printed)
    assert "bash -n scripts/run_suite.sh" in printed
    suite = [c for c in printed if c.startswith("scripts/run_suite.sh ")]
    assert suite and "tests/test_workflow_runners.py" in suite[0]
    assert "tests/test_expert_workflow.py" in suite[0]


def test_shellcheck_finds_nothing() -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed; bash -n above is the only static check run")
    subprocess.run(["shellcheck", "-S", "warning", str(SCRIPT)], check=True)
