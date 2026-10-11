"""Own one native webServer process group and retain its complete output."""
from __future__ import annotations

import json
import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NODE = Path('/Users/wpalish/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
mode, runtime_arg = sys.argv[1:]
runtime = Path(runtime_arg).resolve()
assert runtime.is_relative_to(ROOT / 'evidence' / 'e2e')
if mode == 'backend':
    cwd = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/backend')
    command = ['/bin/bash', str(cwd / 'run.sh'), '--with-worker']
    assert not (cwd / '.env').exists()
else:
    assert mode == 'frontend'
    cwd = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend')
    command = [str(NODE), str(cwd / 'node_modules/vite/bin/vite.js'),
               '--config', str(runtime / 'vite.config.ts'),
               '--host', '127.0.0.1', '--port', '5229', '--strictPort']
receipt_file = runtime / f'{mode}-process.json'
log_file = runtime / f'{mode}-server.log'
process = None


def stop(*_args: object) -> None:
    if process is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, stop)
with log_file.open('w') as log:
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    process = subprocess.Popen(command, cwd=cwd, env=os.environ, start_new_session=True,
                               stdout=log, stderr=subprocess.STDOUT)
    receipt = {'mode': mode, 'pid': process.pid, 'pgid': process.pid,
               'wrapper_pid': os.getpid(), 'command': command, 'cwd': str(cwd),
               'started_monotonic': time.monotonic(), 'started_utc': started_utc}
    receipt_file.write_text(json.dumps(receipt, indent=2) + '\n')
    try:
        code = process.wait()
    finally:
        stop()
        # run.sh execs uvicorn; the worker shares the owned child process group.
        # Explicit group cleanup also covers that worker after the API exits.
        time.sleep(0.2)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    receipt['exit_code'] = code
    receipt['cleanup'] = 'SIGTERM followed by SIGKILL to this owned child group'
    receipt_file.write_text(json.dumps(receipt, indent=2) + '\n')
sys.exit(code if code >= 0 else 128 - code)
