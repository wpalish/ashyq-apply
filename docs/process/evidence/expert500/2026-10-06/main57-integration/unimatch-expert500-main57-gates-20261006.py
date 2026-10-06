import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

repo = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply')
parser = argparse.ArgumentParser()
parser.add_argument('gate', choices=['static', 'backend', 'frontend'])
gate = parser.parse_args().gate
root = Path('/tmp/unimatch-expert500-main57-gates-20261006')
root.mkdir(exist_ok=True)
commands = {
    'static': [(['.venv/bin/python', '-m', 'ruff', 'check', 'app', 'tests', 'evaluation'], 'backend'), (['.venv/bin/python', '-m', 'ruff', 'format', '--check', 'app', 'tests', 'evaluation'], 'backend'), (['.venv/bin/python', '-m', 'mypy', 'app', 'tests', 'evaluation'], 'backend')],
    'backend': [(['.venv/bin/python', '-m', 'pytest', '--cov=app', '--cov-fail-under=92'], 'backend')],
    'frontend': [(['npm', 'ci'], 'frontend'), (['npm', 'run', 'typecheck'], 'frontend'), (['npm', 'run', 'lint'], 'frontend'), (['npm', 'test', '--', '--run'], 'frontend'), (['npm', 'run', 'build'], 'frontend')],
}[gate]
environment = dict(os.environ)
environment.update(UNIMATCH_EXA_API_KEY='', UNIMATCH_DATABASE_URL='sqlite:////tmp/unimatch-expert500-main57-gates-20261006/isolated.db')
started = datetime.now(UTC).isoformat()
results = []
for index, (argv, cwd) in enumerate(commands):
    log = root / f'{gate}-{index:02d}-original.log'
    with log.open('xb') as output:
        proc = subprocess.run(argv, cwd=repo / cwd, env=environment, stdout=output, stderr=subprocess.STDOUT, check=False)
    results.append({'argv': argv, 'cwd': cwd, 'returncode': proc.returncode, 'log': str(log), 'bytes': log.stat().st_size, 'sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    print(json.dumps({'gate': gate, 'step': index, 'returncode': proc.returncode, 'log': str(log)}), flush=True)
    if proc.returncode:
        break
receipt = {'started_at': started, 'finished_at': datetime.now(UTC).isoformat(), 'gate': gate, 'results': results, 'credential_environment_override_empty': True, 'measured_pilot': False}
with (root / f'{gate}-receipt.json').open('x') as output:
    output.write(json.dumps(receipt, indent=2) + '\n')
raise SystemExit(results[-1]['returncode'])
