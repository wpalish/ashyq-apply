"""Prepared finite seed execution; requires a separately retained root-ready binding."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def store(path: Path, value: object) -> None:
    with path.open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--application-binding', type=Path, required=True)
    parser.add_argument('--application-binding-sha256', required=True)
    args = parser.parse_args()
    plan = json.loads((ROOT / 'PLAN.json').read_text())
    assert sha(args.application_binding) == args.application_binding_sha256
    binding = json.loads(args.application_binding.read_text())
    assert binding['application_ready'] is True and binding['source_head']
    primary = Path(plan['primary'])
    expected = json.loads((ROOT / 'candidate-source-pins.json').read_text())
    assert binding['primary_265'] == expected
    assert {rel: sha(primary / rel) for rel in expected} == expected
    assert {rel: sha(ROOT / 'candidate' / rel) for rel in expected} == expected
    for rel, pinned in binding['applied_six'].items():
        assert sha(primary / rel) == pinned['sha256']
        assert (primary / rel).stat().st_size == pinned['bytes']
    assert len(binding['applied_six']) == 6
    stop = Path(plan['retained_STOP']['path'])
    assert sha(stop) == plan['retained_STOP']['sha256']
    helper = Path(plan['safe_env_module'])
    assert sha(helper) == plan['safe_env_sha256']
    spec = importlib.util.spec_from_file_location('_prepared_safe_env_only', helper)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Only this nonsecret runtime directory is selected; never output config/key values.
    node_dir = Path(json.loads((helper.parent / 'config.json').read_text())['node_bin'])
    env = module.safe_env(node_dir, ROOT)
    env.update({
        'PYTHONDONTWRITEBYTECODE': '1',
        'UNIMATCH_DEMO_MODE': 'true',
        'UNIMATCH_ENABLE_BROWSER_TIER': 'false',
        'UNIMATCH_SEARCH_PROVIDER': 'none',
        'UNIMATCH_DATABASE_URL': f'sqlite:///{ROOT / "runtime/seed.db"}',
        'UNIMATCH_AUTO_MIGRATE': 'false',
    })
    assert not (ROOT / 'runtime/seed.db').exists()
    assert not (ROOT / 'candidate/backend/.env').exists()
    records = []
    for action in ('heads', 'migrate', 'seed', 'inspect'):
        assert sha(stop) == plan['retained_STOP']['sha256']
        assert {rel: sha(primary / rel) for rel in expected} == expected
        argv = [plan['python'], str(ROOT / 'guarded_child.py'), action]
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=ROOT / 'candidate/backend', env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, start_new_session=True)
        control = None
        try:
            stdout, stderr = child.communicate(timeout=60)
        except BaseException as original:
            control = type(original).__name__
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = child.communicate(timeout=1)
            except subprocess.TimeoutExpired as partial:
                stdout, stderr = partial.stdout or '', partial.stderr or ''
                if isinstance(stdout, bytes):
                    stdout = stdout.decode(errors='replace')
                if isinstance(stderr, bytes):
                    stderr = stderr.decode(errors='replace')
                for stream in (child.stdout, child.stderr):
                    if stream is not None:
                        stream.close()
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        for name, value in [('stdout', stdout), ('stderr', stderr)]:
            with (ROOT / f'{action}.{name}.original.log').open('x') as stream:
                stream.write(value)
        state_path = ROOT / f'{action}.execution.json'
        state = json.loads(state_path.read_text()) if state_path.is_file() else None
        record = {
            'action': action, 'argv': argv, 'cwd': str(ROOT / 'candidate/backend'),
            'exit_code': child.returncode, 'control': control,
            'seconds': time.monotonic() - started,
            'guard_sha256': sha(ROOT / 'guarded_child.py'),
            'application_binding_sha256': args.application_binding_sha256,
            'stdout_sha256': sha(ROOT / f'{action}.stdout.original.log'),
            'stderr_sha256': sha(ROOT / f'{action}.stderr.original.log'),
            'safe_flags': {'demo': True, 'browser': False, 'provider': 'none',
                           'auto_migrate': False},
            'primary_265_equal': {rel: sha(primary / rel) for rel in expected} == expected,
            'STOP_unchanged': sha(stop) == plan['retained_STOP']['sha256'],
        }
        records.append(record)
        store(ROOT / f'{action}.command.original.json', record)
        print(json.dumps(record), flush=True)
        if (control or child.returncode or state is None or state['network_attempts']
                or not state['candidate_pins_pre_post_equal']
                or not record['primary_265_equal'] or not record['STOP_unchanged']):
            store(ROOT / 'commands.original.json', records)
            return child.returncode or 1
    store(ROOT / 'commands.original.json', records)
    store(ROOT / 'primary-after-pins.json', {rel: sha(primary / rel) for rel in expected})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
