"""Local checks and bounded captures; no GitHub workflow or deployment commands."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
COHORT = ("groningen", "delft", "aalto", "vienna", "warsaw", "ubc", "toronto", "hku", "ntu", "kaist")
PROVIDER_KEYS = {
    "exa": "UNIMATCH_EXA_API_KEY",
    "serper": "UNIMATCH_SERPER_API_KEY",
    "brave": "UNIMATCH_BRAVE_API_KEY",
    "tavily": "UNIMATCH_TAVILY_API_KEY",
}
REDACT_ENV = {
    "DATABASE_URL", "GH_TOKEN", "GITHUB_TOKEN", "FLY_API_TOKEN",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PYTHONPATH", "VIRTUAL_ENV",
    "NODE_OPTIONS", "PORT",
}


def write_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def skip_source(name: str) -> bool:
    parts = Path(name).parts
    return (
        any(p.startswith(".env") for p in parts)
        or name.startswith(("backend/data/", "artifacts/"))
        or any(p in {".git", ".venv", "node_modules", "__pycache__"} for p in parts)
    )


def snapshot(repo: Path, run_dir: Path) -> tuple[Path, dict[str, object]]:
    """Copy the current tracked and nonignored source, with a private local Git index."""
    root = run_dir / "source"
    subprocess.run(
        ["git", "clone", "--shared", "--no-checkout", "--quiet", "--", str(repo), str(root)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", "/dev/null"], check=True)
    names = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    ).decode().split("\0")
    hashes: dict[str, str] = {}
    excluded: list[str] = []
    for name in sorted(set(names) - {""}):
        if skip_source(name):
            excluded.append(name)
            continue
        source = repo / name
        if not source.is_file():
            continue
        if source.is_symlink():
            raise RuntimeError(f"Source symlink needs explicit review: {name}")
        body = source.read_bytes()
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        shutil.copymode(source, target)
        hashes[name] = hashlib.sha256(body).hexdigest()
    for name, digest in hashes.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Source changed during snapshot; no checks started")
    subprocess.run(
        ["git", "-C", str(root), "reset", "--mixed", "--quiet", "HEAD"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    original_python = repo / "backend/.venv"
    if original_python.exists():
        (root / "backend/.venv").symlink_to(original_python, target_is_directory=True)
    original_node = repo / "frontend/node_modules"
    if original_node.exists():
        # Vite rejects assets whose real path is outside its workspace. A link
        # to the checkout's node_modules causes font 403s in console-error E2E.
        shutil.copytree(original_node, root / "frontend/node_modules", symlinks=True)
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    receipt = {
        "repository": str(repo),
        "source_head": git(repo, "rev-parse", "HEAD"),
        "source_branch": git(repo, "branch", "--show-current"),
        "source_status": git(repo, "status", "--porcelain=v1"),
        "source_tree_sha256": digest,
        "files": hashes,
        "excluded_paths": excluded,
        "snapshot": str(root),
        "note": "Checks use this source snapshot. Python dependencies are linked; Node dependencies are copied locally.",
    }
    write_json(run_dir / "source-manifest.json", receipt)
    return root, receipt


def safe_env(node_bin: Path, run_dir: Path) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith("UNIMATCH_") and k not in REDACT_ENV
    }
    env["PATH"] = str(node_bin) + os.pathsep + env.get("PATH", "")
    env.update({
        "CI": "true",
        "PYTHONUNBUFFERED": "1",
        "UNIMATCH_ENVIRONMENT": "development",
        "UNIMATCH_DATABASE_URL": f"sqlite:///{run_dir / 'runtime' / 'checks.db'}",
        "UNIMATCH_PGDATA": str(run_dir / "runtime" / "pgdata"),
        "UNIMATCH_CACHE_DIR": str(run_dir / "runtime" / "httpcache"),
        "UNIMATCH_EXPORT_DIR": str(run_dir / "runtime" / "exports"),
    })
    (run_dir / "runtime").mkdir(exist_ok=True)
    return env


def check_ports() -> None:
    for port in (5173, 8099):
        with socket.socket() as probe:
            probe.settimeout(0.3)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Port {port} is busy. Close that local server before E2E.")


def save_browser_artifacts(root: Path, run_dir: Path, step_name: str) -> None:
    # Playwright clears test-results at its next invocation. Preserve this
    # step's evidence before starting the auth configuration on the same ports.
    destination = run_dir / f"{step_name}-artifacts"
    report = "playwright-report-auth" if step_name == "e2e-auth" else "playwright-report"
    for folder in (report, "test-results"):
        source = root / "frontend" / folder
        if source.exists():
            shutil.copytree(source, destination / folder)


class Run:
    def __init__(self, directory: Path, env: dict[str, str], manifest: dict[str, object]):
        self.directory, self.env = directory, env
        self.summary: dict[str, object] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "source": manifest,
            "steps": [],
            "github_actions_started": False,
            "live_network_capture_started": False,
            "status": "running",
        }
        self.save()

    def save(self) -> None:
        write_json(self.directory / "summary.json", self.summary)

    def step(self, name: str, command: list[str], cwd: Path, env_extra: dict[str, str] | None = None) -> int:
        log = self.directory / f"{name}.log"
        print(f"\n[{name}] log: {log}", flush=True)
        record = {"name": name, "command": command, "cwd": str(cwd), "log": str(log)}
        self.summary["steps"].append(record)
        self.save()
        started = time.monotonic()
        process = None
        code = 1
        try:
            with log.open("w") as output:
                process = subprocess.Popen(
                    command, cwd=cwd, env={**self.env, **(env_extra or {})},
                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                )
                code = process.wait()
        except (OSError, KeyboardInterrupt) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            with log.open("a") as output:
                output.write(f"\n{record['error']}\n")
            code = 130 if isinstance(exc, KeyboardInterrupt) else 127
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        finally:
            if process is not None:
                # Clean only the process group created by this step, including any orphan worker.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    time.sleep(0.4)
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            record.update(exit_code=code, seconds=round(time.monotonic() - started, 2))
            self.save()
        print(f"[{name}] {'PASS' if code == 0 else 'FAIL'} (exit {code})", flush=True)
        if code != 0 and log.exists():
            print("\n".join(log.read_text(errors="replace").splitlines()[-18:]), flush=True)
        return code

    def finish(self, status: str) -> None:
        self.summary["status"] = status
        self.summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.save()
        print(f"\nStatus: {status}\nResults: {self.directory / 'summary.json'}", flush=True)


def checks(root: Path, python: Path, suite: str, run_dir: Path) -> list[tuple[str, list[str], Path]]:
    backend, frontend = root / "backend", root / "frontend"
    p = str(python)
    sqlite = [
        ("ruff", [p, "-m", "ruff", "check", "app", "tests", "evaluation"], backend),
        ("ruff-format", [p, "-m", "ruff", "format", "--check", "app", "tests", "evaluation"], backend),
        ("mypy", [p, "-m", "mypy", "app", "tests", "evaluation"], backend),
        ("backend-sqlite", [p, "-m", "pytest", "--cov=app", "--cov-fail-under=92",
                            f"--junitxml={run_dir / 'backend-sqlite.xml'}"], backend),
    ]
    front = [
        (f"frontend-{task}", ["npm", "run", task], frontend)
        for task in ("typecheck", "lint")
    ] + [
        ("frontend-tests", ["npm", "test", "--", "--run"], frontend),
        ("frontend-build", ["npm", "run", "build"], frontend),
    ]
    postgres = [
        ("backend-postgresql", [p, "scripts/pg.py", p, "-m", "pytest",
                                f"--junitxml={run_dir / 'backend-postgresql.xml'}"], backend),
    ]
    e2e = [(name.replace(":", "-"), ["npm", "run", name], frontend) for name in ("e2e", "e2e:auth")]
    security = [
        ("pip-audit", [p, "-m", "pip_audit", "-r", "requirements.txt"], backend),
        ("npm-audit", ["npm", "audit", "--audit-level=high"], frontend),
    ]
    containers = [
        ("compose-config", ["docker", "compose", "config", "--quiet"], root),
        ("compose-build", ["docker", "compose", "build"], root),
    ]
    groups = {
        "core": sqlite + front, "backend": sqlite, "frontend": front,
        "postgres": postgres, "e2e": e2e, "security": security, "containers": containers,
        "full": sqlite + front + postgres + e2e + security,
        "all": sqlite + front + postgres + e2e + security + containers,
    }
    return groups[suite]


def main() -> int:
    config = json.loads((BUNDLE / "config.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(config["repo"]))
    parser.add_argument("command", choices=("doctor", "setup", "check", "live"))
    parser.add_argument("--suite", choices=("core", "backend", "frontend", "postgres", "e2e", "security", "containers", "full", "all"), default="core")
    parser.add_argument("--provider", choices=("exa", "exa_mcp", "serper", "brave", "tavily", "none"))
    parser.add_argument("--case", choices=COHORT)
    parser.add_argument("--execute", action="store_true", help="Actually dispatch live reads; otherwise print the prepared command.")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "backend/requirements-dev.txt").is_file():
        parser.error("The selected repository is not an ASHYQ Apply checkout")
    node_bin = Path(config["node_bin"])
    python = repo / "backend/.venv/bin/python"
    launch_python = Path(config["python"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = BUNDLE / "runs" / f"{stamp}-{args.command}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True)
    env = safe_env(node_bin, run_dir)
    with (BUNDLE / ".run.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another local run is active; do not overlap the E2E servers")
        lock.write(str(os.getpid()))
        lock.flush()
        run = Run(run_dir, env, {"repository": str(repo), "source_head": git(repo, "rev-parse", "HEAD")})
        try:
            if args.command == "setup":
                if not python.exists():
                    if run.step("create-venv", [str(launch_python), "-m", "venv", "backend/.venv"], repo):
                        run.finish("failed")
                        return 1
                steps = [
                    ("install-python", [str(python), "-m", "pip", "install", "-r", "requirements-dev.txt"], repo / "backend"),
                    ("install-node", ["npm", "ci"], repo / "frontend"),
                    ("install-chromium", ["npm", "exec", "--", "playwright", "install", "chromium"], repo / "frontend"),
                ]
                for name, cmd, cwd in steps:
                    if run.step(name, cmd, cwd):
                        run.finish("failed")
                        return 1
                run.finish("passed")
                return 0
            if args.command == "doctor":
                version_steps = [
                    ("python-version", [str(python), "-c", "import sys; print(sys.version); assert sys.version_info[:2] == (3,12)"], repo),
                    ("node-version", ["node", "-e", "console.log(process.version); if (process.versions.node.split('.')[0] !== '22') process.exit(1)"], repo),
                    ("python-dependencies", [str(python), "-c", "import importlib.util; names=['pytest','pytest_cov','ruff','mypy','respx','pgserver','playwright','pip_audit']; missing=[n for n in names if importlib.util.find_spec(n) is None]; print('Missing:', missing); raise SystemExit(bool(missing))"], repo),
                    ("node-dependencies", ["npm", "ls", "--depth=0"], repo / "frontend"),
                    ("chromium-installed", ["node", "--input-type=module", "-e",
                        "import {chromium} from '@playwright/test'; import fs from 'node:fs'; const p=chromium.executablePath(); console.log(p); if (!fs.existsSync(p)) process.exit(1);"], repo / "frontend"),
                ]
                failed = any([run.step(*step) != 0 for step in version_steps])
                run.summary["docker_available"] = bool(shutil.which("docker", path=env["PATH"]))
                run.summary["ci_runtime_target"] = {"python": "3.12", "node": "22", "github_os": "Linux", "local_os": platform.system()}
                run.finish("failed" if failed else "passed")
                return int(failed)
            if not python.exists() or not (repo / "frontend/node_modules").exists():
                raise RuntimeError("Dependencies are missing. Run local.sh setup first.")
            root, manifest = snapshot(repo, run_dir)
            run.summary["source"] = manifest
            run.save()
            backend_python = root / "backend/.venv/bin/python"
            if args.command == "check":
                failed = False
                for name, cmd, cwd in checks(root, backend_python, args.suite, run_dir):
                    if name in ("e2e", "e2e-auth"):
                        check_ports()
                    extra = {"POSTGRES_PASSWORD": "ci-only-not-a-secret"} if name.startswith("compose-") else None
                    code = run.step(name, cmd, cwd, extra)
                    if name in ("e2e", "e2e-auth"):
                        save_browser_artifacts(root, run_dir, name)
                    failed |= code != 0
                    if code == 130:
                        run.finish("interrupted")
                        return 130
                run.summary["suite"] = args.suite
                run.summary["includes_container_gates"] = args.suite in ("containers", "all")
                run.finish("failed" if failed else "passed")
                return int(failed)
            if not args.provider or not args.case:
                raise RuntimeError("live requires an explicit provider and one pilot case")
            command = [
                str(backend_python), "-m", "evaluation.research.live", "--live",
                "--case", args.case, "--seconds-per-case", "120", "--max-pages", "60",
                "--search-provider", args.provider, "--shared-query-budget",
                "--out", str(run_dir / "capture"),
            ]
            if args.provider in ("exa", "exa_mcp"):
                command.append("--strict-expert-budget")
            run.summary["live_plan"] = {
                "command": command, "provider": args.provider, "case": args.case,
                "seconds": 120, "page_reads": 60, "shared_search_budget": 6,
                "strict_action_ledger": args.provider in ("exa", "exa_mcp"),
                "comparison_eligible": False,
                "network_location": "local computer", "expert_evaluation": False,
                "no_automatic_scoring": True,
            }
            if not args.execute:
                write_json(run_dir / "live-plan.json", run.summary["live_plan"])
                run.finish("prepared_not_executed")
                return 0
            key = PROVIDER_KEYS.get(args.provider)
            if key and not os.environ.get(key):
                raise RuntimeError(f"Set {key} in the process environment; no key file is read or printed")
            key_names = [key] if key else []
            live_env = {name: os.environ[name] for name in key_names}
            run.summary["live_network_capture_started"] = True
            code = run.step("live-capture", command, root / "backend", live_env)
            run.finish("capture_finished_unscored" if code == 0 else "capture_failed_unscored")
            return code
        except KeyboardInterrupt:
            run.finish("interrupted")
            return 130
        except Exception as exc:
            run.summary["error"] = str(exc)
            run.finish("failed")
            print(f"Error: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
