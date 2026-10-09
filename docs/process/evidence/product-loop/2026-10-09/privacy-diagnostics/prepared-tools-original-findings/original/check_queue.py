"""Run the authorized doctor/core/full sequence on one frozen privacy source."""
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
TASK = ROOT / 'work/security-round2'
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
OUT = TASK / 'native-queue'
PINS = json.loads((TASK / 'applied-source-pins.json').read_text())
HEAD = (TASK / 'applied-head.txt').read_text().strip()
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    assert subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip() == HEAD
    assert not subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain'], text=True).strip()
    assert all(sha(REPO / n) == h for n, h in PINS.items())
    assert sha(STOP) == STOP_SHA

def free():
    with (BUNDLE / '.run.lock').open('r') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

verify()
OUT.mkdir(exist_ok=False)
records = []
for suite in ['doctor', 'core', 'full']:
    verify()
    if not free():
        print('WAITING: existing shared runner; no owned checks or ports started', flush=True)
    while not free():
        verify()
        time.sleep(10)
    verify()
    start = datetime.now(timezone.utc).isoformat()
    before = set((BUNDLE / 'runs').iterdir())
    argv = ['python3', str(BUNDLE / 'run_local.py'), '--repo', str(REPO)]
    argv += ['doctor'] if suite == 'doctor' else ['check', '--suite', suite]
    print(f'START {suite} {start} HEAD={HEAD}', flush=True)
    with (OUT / f'{suite}-console-original.log').open('wb') as log:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b''):
            log.write(line)
            log.flush()
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        code = process.wait()
    owned = []
    for folder in sorted(set((BUNDLE / 'runs').iterdir()) - before):
        p = folder / 'summary.json'
        if p.exists():
            data = json.loads(p.read_text())
            if (data.get('source', {}).get('repository') == str(REPO)
                    and data.get('source', {}).get('source_head') == HEAD):
                owned.append({'path': str(folder), 'summary_sha256': sha(p), 'status': data.get('status')})
    records.append({'suite': suite, 'argv': argv, 'head': HEAD,
        'source_pins_sha256': sha(TASK / 'applied-source-pins.json'),
        'started_at': start, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'exit_code': code, 'owned_runs': owned})
    (OUT / 'execution.json').write_text(json.dumps(records, indent=2) + '\n')
    verify()
    print(f'END {suite} exit={code}', flush=True)
    if code:
        sys.exit(code)
