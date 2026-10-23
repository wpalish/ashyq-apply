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
OUT = TASK / 'repaired-native-queue'
PINS = json.loads((TASK / 'repaired-source-pins.json').read_text())
RECEIPT_PATH = TASK / 'test-repair-application-receipt.json'
RECEIPT = json.loads(RECEIPT_PATH.read_text())
PINS_SHA = RECEIPT['source34_pins_sha256']
assert RECEIPT['status'] == 'EXACT_TEST_REPAIR_APPLIED_FULL_PENDING' and len(PINS) == 34
assert hashlib.sha256((TASK / 'repaired-source-pins.json').read_bytes()).hexdigest() == PINS_SHA
RECEIPT_SHA = hashlib.sha256(RECEIPT_PATH.read_bytes()).hexdigest()
HEAD = (TASK / 'repaired-head.txt').read_text().strip()
BRANCH = 'task/product-privacy-diagnostics'
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def verify():
    assert sha(TASK / 'repaired-source-pins.json') == PINS_SHA
    assert sha(RECEIPT_PATH) == RECEIPT_SHA
    assert subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip() == HEAD
    assert subprocess.check_output(['git', '-C', str(REPO), 'branch', '--show-current'], text=True).strip() == BRANCH
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
core_steps = ['ruff', 'ruff-format', 'mypy', 'backend-sqlite',
              'frontend-typecheck', 'frontend-lint', 'frontend-tests', 'frontend-build']
expected_steps = {
    'doctor': ['python-version', 'node-version', 'python-dependencies', 'node-dependencies', 'chromium-installed'],
    'core': core_steps,
    'full': core_steps + ['backend-postgresql', 'e2e', 'e2e-auth', 'pip-audit', 'npm-audit'],
}
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
    reported = set()
    with (OUT / f'{suite}-console-original.log').open('wb') as log:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b''):
            log.write(line)
            log.flush()
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
            decoded = line.decode('utf-8', errors='replace').strip()
            if decoded.startswith('Results: '):
                reported.add(Path(decoded.removeprefix('Results: ')).resolve())
        code = process.wait()
    owned = []
    for p in sorted(reported):
        assert p.name == 'summary.json' and p.parent.parent == BUNDLE / 'runs'
        assert p.parent not in before and p.is_file() and not p.is_symlink()
        data = json.loads(p.read_text())
        assert data.get('source', {}).get('repository') == str(REPO)
        assert data.get('source', {}).get('source_head') == HEAD
        assert data.get('source', {}).get('source_branch') == BRANCH
        owned.append({'path': str(p.parent), 'summary_sha256': sha(p),
                      'status': data.get('status'), 'reported_by_own_child_stdout': True,
                      'step_names': [r['name'] for r in data['steps']]})
        if code == 0:
            assert data['status'] == 'passed'
            assert [r['name'] for r in data['steps']] == expected_steps[suite]
            assert all(r['exit_code'] == 0 for r in data['steps'])
    records.append({'suite': suite, 'argv': argv, 'head': HEAD,
        'source_pins_sha256': sha(TASK / 'repaired-source-pins.json'),
        'started_at': start, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'exit_code': code, 'owned_runs': owned})
    (OUT / 'execution.json').write_text(json.dumps(records, indent=2) + '\n')
    verify()
    print(f'END {suite} exit={code}', flush=True)
    if code:
        sys.exit(code)
    assert len(owned) == 1, 'one actual own child-reported run required before next suite'
