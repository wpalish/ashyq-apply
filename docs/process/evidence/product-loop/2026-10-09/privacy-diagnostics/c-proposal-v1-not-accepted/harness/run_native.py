"""Run one issued command in an isolated source copy, never the shared runner."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

packet = Path(__file__).resolve().parents[1]
mode = sys.argv[1]
assert mode in {"off", "on"}
python = "/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python"
argv = [python, str(packet / "harness/guarded_pytest.py"), mode]
env = {
    "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "UNIMATCH_DATABASE_URL": "sqlite:///:memory:",
    "UNIMATCH_SEARCH_PROVIDER": "none", "UNIMATCH_DECISION_PROVIDER": "none",
    "UNIMATCH_DEMO_MODE": "true", "UNIMATCH_ENABLE_BROWSER_TIER": "false",
    "UNIMATCH_AUTH_ENABLED": "false", "UNIMATCH_AUTO_MIGRATE": "false",
}
start = time.monotonic()
out = subprocess.run(argv, cwd=packet / "runtime" / mode, env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
raw = out.stdout.encode()
(packet / "logs" / (mode + "-issued.log")).write_bytes(raw)
receipt = dict(argv=argv, cwd=str(packet / "runtime" / mode), env_allowlist=env,
               returncode=out.returncode, seconds=time.monotonic() - start,
               utc=datetime.now(timezone.utc).isoformat(),
               log_sha256=hashlib.sha256(raw).hexdigest())
(packet / "logs" / (mode + "-execution.json")).write_text(json.dumps(receipt, indent=2) + "\n")
print(out.stdout)
print(json.dumps(receipt, indent=2))
sys.exit(out.returncode)
