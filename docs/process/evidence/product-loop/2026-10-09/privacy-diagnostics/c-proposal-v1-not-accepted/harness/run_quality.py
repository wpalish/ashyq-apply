"""Record exact finite local static-tool argv/output; no project runner."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

p = Path(__file__).resolve().parents[1]
tool = Path("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin")
job = sys.argv[1]
jobs = {
    "lint-before": [str(tool / "ruff"), "check", "--config", "config/ruff.toml", "--no-cache", "proposed/backend/app", "proposed/backend/tests"],
    "imports-literals": [str(tool / "ruff"), "check", "--config", "config/ruff.toml", "--no-cache", "--select", "I,C408", "--fix", "--unsafe-fixes", "proposed/backend/app", "proposed/backend/tests"],
    "format": [str(tool / "ruff"), "format", "--config", "config/ruff.toml", "--no-cache", "proposed/backend/app", "proposed/backend/tests"],
    "lint-final": [str(tool / "ruff"), "check", "--config", "config/ruff.toml", "--no-cache", "proposed/backend/app", "proposed/backend/tests"],
    "format-final": [str(tool / "ruff"), "format", "--config", "config/ruff.toml", "--no-cache", "--check", "proposed/backend/app", "proposed/backend/tests"],
    "mypy-final": [str(tool / "mypy"), "--config-file", str(p / "config/mypy.ini"), "--cache-dir", str(p / "runtime/mypy-cache"), "app"],
}
argv = jobs[job]
cwd = p / "runtime/on/backend" if job == "mypy-final" else p
env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
       "UNIMATCH_SEARCH_PROVIDER": "none", "UNIMATCH_DECISION_PROVIDER": "none",
       "UNIMATCH_DATABASE_URL": "sqlite:///:memory:", "UNIMATCH_DEMO_MODE": "true"}
start = time.monotonic()
r = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, text=True, timeout=90)
raw = r.stdout.encode()
assert not (p / "logs" / (job + ".log")).exists()
(p / "logs" / (job + ".log")).write_bytes(raw)
(p / "logs" / (job + "-execution.json")).write_text(json.dumps(dict(
    argv=argv, cwd=str(cwd), env_allowlist=env, returncode=r.returncode,
    seconds=time.monotonic()-start, utc=datetime.now(timezone.utc).isoformat(),
    log_sha256=hashlib.sha256(raw).hexdigest()), indent=2)+"\n")
print(r.stdout)
sys.exit(r.returncode)
