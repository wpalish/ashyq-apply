"""Wait for the shared local runner, then run authorized core/full sequentially."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import subprocess
import sys
import time

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
OUT = ROOT / 'work/product-round5/native-queue'
PINS = json.loads((ROOT / 'work/product-round5/applied-source-pins.json').read_text())
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'

def verify():
    for name, expected in PINS.items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected, name
    assert hashlib.sha256(STOP.read_bytes()).hexdigest() == STOP_SHA

def free():
    with (BUNDLE / '.run.lock').open('r') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

OUT.mkdir(exist_ok=False)
records = []
for suite in ['core', 'full']:
    verify()
    if not free():
        print('WAITING: existing local runner; no owned tests or ports started', flush=True)
    while not free():
        verify()
        time.sleep(10)
    verify()
    started = datetime.now(timezone.utc).isoformat()
    before = set((BUNDLE / 'runs').iterdir())
    command = ['python3', str(BUNDLE / 'run_local.py'), '--repo', str(REPO), 'check', '--suite', suite]
    print(f'START {suite} {started}', flush=True)
    with (OUT / f'{suite}-console-original.log').open('wb') as console:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b''):
            console.write(line)
            console.flush()
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        returncode = process.wait()
    after = set((BUNDLE / 'runs').iterdir())
    runs = []
    for folder in sorted(after - before):
        summary = folder / 'summary.json'
        if summary.exists():
            data = json.loads(summary.read_text())
            if data.get('source', {}).get('repository') == str(REPO):
                runs.append({'path': str(folder), 'summary_sha256': hashlib.sha256(summary.read_bytes()).hexdigest(),
                             'status': data.get('status')})
    verify()
    records.append({'suite': suite, 'command': command, 'started_at': started,
                    'finished_at': datetime.now(timezone.utc).isoformat(),
                    'exit_code': returncode, 'owned_runs': runs})
    (OUT / 'execution.json').write_text(json.dumps(records, indent=2)+'\n')
    print(f'END {suite} exit={returncode}', flush=True)
    if returncode:
        sys.exit(returncode)
