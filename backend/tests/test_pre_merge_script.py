"""scripts/pre_merge.sh runs exactly the CI gates (GATE-1) and the container jobs (GATE-2).

Three red CI stretches on 2026-10-25 were each a gate that exists in ``ci.yml`` and was not run
before the push. The script is the one command that runs them locally; these tests hold it to
``ci.yml`` so the two cannot drift apart without a red test. A fourth (``146a4e8e``) was the web
image's ``npm run build`` failing on a file its ``.dockerignore`` dropped while the script, which ran
the build in ``frontend/``, said GREEN: the container jobs are now mirrored when a Docker daemon
answers and approximated by ``scripts/image_context.py`` without one, and the tests below fail when
``ci.yml`` or a Dockerfile gains a step the script neither mirrors nor approximates. Almost
everything here goes through ``--dry-run``, which prints every command and runs none; ``--docker
never`` is the default, so the printed list does not depend on the machine.
"""

from __future__ import annotations

import importlib.util
import json
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/pre_merge.sh"
CI = ROOT / ".github/workflows/ci.yml"
PACKAGE = ROOT / "frontend/package.json"
COMPOSE_FILE = ROOT / "docker-compose.yml"
IMAGE_CONTEXT = ROOT / "scripts/image_context.py"

# CI lines that build the machine rather than gate the code: a local tree has them already
# (link_worktree_env.sh links the venv and node_modules in).
SETUP = (
    re.compile(r"^python -m venv "),
    re.compile(r"^(\S*/)?pip install "),
    re.compile(r"^python -m pip install "),
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
    if "--docker" not in args:
        argv += ["--docker", "never"]
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
            # The image's own `npm run build` runs in its staged context as well (GATE-2).
            in_repo = [p for p in hits if not p[0].endswith("/image-web")]
            assert in_repo and all(p[0] == "frontend" for p in in_repo), (
                f"{want!r} not run in frontend/"
            )
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
    printed = [c for d, c, _ in commands_of(output) if d == "frontend"]
    assert [c for c in printed if c.startswith("npm ")] == FRONTEND_GATES
    assert not any(c.startswith(".venv/bin/") for c in printed)
    assert "precondition: ports 5173/8099 free" in output


def test_e2e_never_turns_a_frontend_diff_red(tmp_path: Path) -> None:
    listing = tmp_path / "changed.txt"
    listing.write_text("frontend/src/App.tsx\n")
    argv = [
        "bash",
        str(SCRIPT),
        "--dry-run",
        "--base",
        "HEAD",
        "--e2e",
        "never",
        "--docker",
        "never",
    ]
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


# --- GATE-2: the container jobs -------------------------------------------------------------------

GATE_JOBS = ("backend", "frontend")  # held command for command by the tests above
CONTAINER = re.compile(r"\bdocker\b|\bcompose\b|\$COMPOSE\b|verify_compose|\bpodman\b|\bbuildx\b")
# Every container step of ci.yml outside the gate jobs -> the command pre_merge.sh runs for it when a
# daemon answers (`--docker always`), or None when it is no gate. A step missing here is one the
# script neither mirrors nor approximates: add it to the script (block 6), then here.
CONTAINER_STEPS: dict[str, str | None] = {
    "POSTGRES_PASSWORD=ci-only-not-a-secret docker compose config --quiet": (
        "docker compose config --quiet"
    ),
    "POSTGRES_PASSWORD=ci-only-not-a-secret docker compose build": "docker compose build",
    "bash scripts/verify_compose.sh": "bash scripts/verify_compose.sh",
    # if: failure() diagnostics, uploaded as an artefact; not a gate.
    "$COMPOSE ps --all > compose-ps.txt 2>&1 || true": None,
    "$COMPOSE logs --no-color --timestamps > compose-logs.txt 2>&1 || true": None,
    # if: always() teardown; finish() takes the stack down (asserted below).
    "$COMPOSE down -v --remove-orphans || true": None,
}
# What the script runs for each mirrored step without a daemon (`--docker never`): (directory
# suffix, text of the command) pairs that must all be printed; an empty suffix is the repo root.
OFFLINE: dict[str, list[tuple[str, str]]] = {
    "docker compose config --quiet": [("", "docker compose config --quiet")],
    "docker compose build": [
        ("", "backend/.venv/bin/python scripts/image_context.py stage frontend "),
        ("/image-web", "npm run build"),
        ("", "backend/.venv/bin/python scripts/image_context.py stage backend "),
    ],
    "bash scripts/verify_compose.sh": [
        ("/image-api", "-c import os, app.main, app.jobs.worker, app.corpus.demo_profile"),
        ("/image-api", "-m alembic upgrade head"),
    ],
}
# Non-container steps of those jobs that the script deliberately does not run.
NOT_MIRRORED = {
    "pip-audit -r backend/requirements.txt": "needs the network (the PyPI advisory database)",
    "npm audit --prefix frontend --audit-level=high": "needs the network (the npm registry)",
}


def container_jobs() -> dict[str, dict[str, Any]]:
    document: dict[Any, Any] = yaml.safe_load(CI.read_text())
    return {name: job for name, job in document["jobs"].items() if name not in GATE_JOBS}


def step_lines(job: dict[str, Any]) -> list[str]:
    lines = []
    for step in job["steps"]:
        for line in str(step.get("run", "")).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def raw_commands(output: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in map(COMMAND.match, output.splitlines()) if m]


def test_every_step_of_the_container_jobs_is_mirrored_approximated_or_explained() -> None:
    unknown = []
    for name, job in container_jobs().items():
        for line in step_lines(job):
            if (
                any(p.search(line) for p in SETUP)
                or line in CONTAINER_STEPS
                or line in NOT_MIRRORED
            ):
                continue
            kind = "container step" if CONTAINER.search(line) else "step"
            unknown.append(f"ci.yml job {name!r} gained the {kind} {line!r}")
    assert not unknown, (
        "pre_merge.sh neither mirrors nor approximates: "
        + "; ".join(unknown)
        + " - add it to scripts/pre_merge.sh (block 6) and to CONTAINER_STEPS / OFFLINE here"
    )


def test_with_a_daemon_the_script_runs_the_ci_container_steps_with_ci_env() -> None:
    printed = raw_commands(dry_run("--scope", "all", "--docker", "always", "--e2e", "always"))
    for name, job in container_jobs().items():
        job_env = {k: str(v) for k, v in (job.get("env") or {}).items()}
        for line in step_lines(job):
            want = CONTAINER_STEPS.get(line)
            if want is None:
                continue
            env = dict(job_env)
            prefix = ENV.match(line)
            while prefix:
                key, _, value = prefix.group(0).strip().partition("=")
                env[key] = value
                line = line[prefix.end() :]
                prefix = ENV.match(line)
            hits = [c for d, c in printed if d == "." and c.endswith(want)]
            assert hits, f"ci.yml ({name}) runs {want!r}; pre_merge.sh does not"
            for key, value in env.items():
                if key == "COMPOSE" and "verify_compose" not in want:
                    continue  # the job's override; config and build run on the plain file, as CI's do
                assert any(f"{key}={value}" in c for c in hits), (
                    f"{want!r}: {key}={value} not passed"
                )
    assert "down -v --remove-orphans" in SCRIPT.read_text()


def test_without_a_daemon_the_script_approximates_each_container_step() -> None:
    printed = raw_commands(dry_run("--scope", "all", "--docker", "never", "--e2e", "always"))
    assert not any(c.endswith("docker compose build") for _, c in printed)
    assert not any("verify_compose.sh" in c and not c.startswith("bash -n") for _, c in printed)
    for mirrored, steps in OFFLINE.items():
        for suffix, text in steps:
            ok = any((d.endswith(suffix) if suffix else d == ".") and text in c for d, c in printed)
            assert ok, f"no offline stand-in for {mirrored!r}: want {text!r} in *{suffix or '.'}"


def load_image_context() -> Any:
    """scripts/image_context.py as a module (registered first: its dataclass resolves its module)."""
    if "image_context" in sys.modules:
        return sys.modules["image_context"]
    spec = importlib.util.spec_from_file_location("image_context", IMAGE_CONTEXT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["image_context"] = module
    spec.loader.exec_module(module)
    return module


# Every RUN of every image docker-compose.yml builds -> how the offline approximation covers it:
# "printed" = the script runs it in the staged context; anything else is why it is substituted.
DOCKERFILE_RUNS: dict[str, dict[str, str]] = {
    "frontend": {
        "npm ci": "node_modules is linked into the staged context (installed from the same lockfile)",
        "npm run build": "printed",
    },
    "backend": {
        "python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt": (
            "backend/.venv runs the staged tree (requirements-dev.txt includes requirements.txt)"
        ),
        "apt-get update && apt-get install -y --no-install-recommends curl"
        " && rm -rf /var/lib/apt/lists/* && groupadd --system --gid 10001 ashyq"
        " && useradd --system --uid 10001 --gid ashyq --home /app --shell /usr/sbin/nologin ashyq": (
            "curl for the healthcheck and the service user; nothing the code imports"
        ),
        "playwright install --with-deps chromium && chmod -R a+rX /ms-playwright": (
            "the browser tier; the stack's demo and kb-mode runs read no page"
        ),
        "mkdir -p /app/data && chown -R ashyq:ashyq /app/data": (
            "Settings.ensure_dirs() creates data/ when app.main is imported"
        ),
    },
}
STAGED_DIR = {"frontend": "/image-web", "backend": "/image-api"}


def compose_contexts() -> set[str]:
    services = yaml.safe_load(COMPOSE_FILE.read_text())["services"]
    contexts = set()
    for spec in services.values():
        build = spec.get("build")
        if build is not None:
            context = build if isinstance(build, str) else build.get("context", ".")
            contexts.add(context.removeprefix("./").rstrip("/"))
    return contexts


def test_every_compose_image_is_staged_and_every_run_step_is_covered() -> None:
    image_context = load_image_context()
    assert compose_contexts() == set(DOCKERFILE_RUNS), (
        f"docker-compose.yml builds {sorted(compose_contexts())};"
        f" pre_merge.sh stages {sorted(DOCKERFILE_RUNS)}"
    )
    printed = raw_commands(dry_run("--scope", "all", "--docker", "never", "--e2e", "always"))
    for context, known in DOCKERFILE_RUNS.items():
        assert any(f"image_context.py stage {context} " in c for _, c in printed), context
        runs = image_context.run_steps((ROOT / context / "Dockerfile").read_text())
        unknown = [r for r in runs if r not in known]
        assert not unknown, (
            f"{context}/Dockerfile gained RUN {unknown}; pre_merge.sh does not cover it"
        )
        for run, how in known.items():
            assert run in runs, f"{context}/Dockerfile no longer runs {run!r}; drop it here"
            if how == "printed":
                staged = [c for d, c in printed if d.endswith(STAGED_DIR[context])]
                assert run in staged, f"{run!r} is not run in the staged {context}/ context"


@pytest.mark.parametrize(
    ("rules", "path", "excluded"),
    [
        ("e2e/\n", "e2e/demo-env/paths.ts", True),
        ("e2e/\n", "src/e2e/x.ts", False),  # anchored at the context root
        ("playwright.config.ts\n", "playwright.kb.config.ts", False),
        ("*.py[cod]\n", "app/x.pyc", False),  # `*` does not cross a slash
        ("*.py[cod]\n", "x.pyc", True),
        ("**/node_modules/\n", "a/b/node_modules/x/y.js", True),
        ("**/node_modules/\n", "node_modules/y.js", True),
        ("**/.env.*\n", "deep/.env.local", True),
        ("tests/\n!tests/keep.py\n", "tests/keep.py", False),
        ("tests/\n!tests/keep.py\n", "tests/drop.py", True),
        ("/data/\n", "data/x.json", True),
        ("# comment\n\n*.db\n", "unimatch.db", True),
    ],
)
def test_dockerignore_matching_follows_docker(rules: str, path: str, excluded: bool) -> None:
    image_context = load_image_context()
    assert image_context.excluded(path, image_context.parse_dockerignore(rules)) is excluded


IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|\bimport\s+)['"](\.{1,2}/[^'"]+)['"]""")


def unresolved_imports(files: set[str]) -> list[str]:
    """Relative imports of the type-checked frontend files that do not resolve inside ``files``."""
    roots = json.loads((ROOT / "frontend/tsconfig.json").read_text())["include"]
    missing = []
    for rel in sorted(files):
        in_build = any(rel == r or rel.startswith(r.rstrip("/") + "/") for r in roots)
        if not rel.endswith((".ts", ".tsx")) or not in_build:
            continue
        for target in IMPORT.findall((ROOT / "frontend" / rel).read_text(encoding="utf-8")):
            norm = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
            candidates = [norm] + [
                norm + e for e in (".ts", ".tsx", ".d.ts", "/index.ts", "/index.tsx")
            ]
            if norm.endswith(".js"):
                candidates += [norm[:-3] + ".ts", norm[:-3] + ".tsx"]
            if not any(c in files for c in candidates):
                missing.append(f"{rel} imports {target}")
    return missing


def staged_frontend(dockerignore: str) -> set[str]:
    image_context = load_image_context()
    rules = image_context.parse_dockerignore(dockerignore)
    tracked = image_context.tracked(ROOT / "frontend")
    return {p for p in tracked if not image_context.excluded(p, rules)}


def test_the_web_image_context_holds_every_file_its_type_check_imports() -> None:
    assert unresolved_imports(staged_frontend((ROOT / "frontend/.dockerignore").read_text())) == []


def test_146a4e8es_dockerignore_is_caught_without_docker() -> None:
    """The two lines 7de2c169 added, removed again: the configs stay in the image, e2e/ does not."""
    current = (ROOT / "frontend/.dockerignore").read_text()
    old = "".join(
        line
        for line in current.splitlines(keepends=True)
        if line.strip() not in ("playwright.config.ts", "playwright.auth.config.ts")
    )
    assert old != current
    assert sorted(unresolved_imports(staged_frontend(old))) == [
        "playwright.auth.config.ts imports ./e2e/demo-env/paths",
        "playwright.config.ts imports ./e2e/demo-env/paths",
    ]


# --- the verdict cannot be lost -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "changed", "code"),
    [
        (("--dry-run", "--base", "HEAD", "--docker", "never"), ["backend/app/x.py"], 0),
        (
            ("--dry-run", "--base", "HEAD", "--e2e", "never", "--docker", "never"),
            ["frontend/x.ts"],
            1,
        ),
        # Real runs: a docs-only diff runs the commit check alone, so these stay quick.
        (("--base", "HEAD"), ["docs/x.md"], 0),
        (("--base", "no-such-ref-gate-2"), ["docs/x.md"], 1),
        (("--docker", "sometimes"), None, 2),
        (("--e2e",), None, 2),
    ],
)
def test_the_last_line_is_the_verdict_and_the_exit_status_matches_it(
    args: tuple[str, ...], changed: list[str] | None, code: int, tmp_path: Path
) -> None:
    argv = ["bash", str(SCRIPT), *args]
    if changed is not None:
        listing = tmp_path / "changed.txt"
        listing.write_text("".join(f"{p}\n" for p in changed))
        argv += ["--changed", str(listing)]
    done = subprocess.run(argv, capture_output=True, text=True, check=False, cwd=ROOT)
    last = done.stdout.rstrip("\n").splitlines()[-1]
    assert done.returncode == code, done.stdout + done.stderr
    assert last == ("pre_merge: GREEN" if code == 0 else "pre_merge: RED"), done.stdout
