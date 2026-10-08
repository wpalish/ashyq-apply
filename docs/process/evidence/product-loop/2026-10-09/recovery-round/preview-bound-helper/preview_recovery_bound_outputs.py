"""Finite owned DEMO preview, bound to this task's passed native full."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import time

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
TASK = ROOT / 'work/product-round5'
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
SEED = ROOT / 'work/product-round2/preview-after/runtime/checks.db'

def stop_guard():
    assert hashlib.sha256(STOP.read_bytes()).hexdigest() == STOP_SHA

def finish_child(process):
    # Kill only the groups this preview created, then wait before releasing flock.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=4)
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    # A group can outlive its leader; wait for live members as well.
    for _ in range(40):
        rows = subprocess.check_output(['ps', '-axo', 'pgid=,stat='], text=True).splitlines()
        live = any(len(parts := row.split()) == 2 and int(parts[0]) == process.pid
                   and not parts[1].startswith('Z') for row in rows)
        if not live:
            return
        time.sleep(0.1)
    raise RuntimeError(f'Owned preview group {process.pid} still live after cleanup')

parser = argparse.ArgumentParser()
parser.add_argument('out', type=Path)
args = parser.parse_args()
out = args.out.resolve()
assert out.parent == TASK and out.name.startswith('preview-final') and not out.exists()
stop_guard()
execution = json.loads((TASK / 'native-queue/execution.json').read_text())
assert [r['suite'] for r in execution] == ['core', 'full']
assert all(r['exit_code'] == 0 for r in execution)
assert len(execution[-1]['owned_runs']) == 1
full = execution[-1]['owned_runs'][0]
assert full['status'] == 'passed'
run = Path(full['path']).resolve()
assert run.parent == BUNDLE / 'runs'
assert hashlib.sha256((run / 'summary.json').read_bytes()).hexdigest() == full['summary_sha256']
manifest = json.loads((run / 'source-manifest.json').read_text())
summary = json.loads((run / 'summary.json').read_text())
assert summary['status'] == 'passed' and len(summary['steps']) == 13
assert all(step['exit_code'] == 0 for step in summary['steps'])
assert summary['source'] == manifest
assert manifest['repository'] == str(REPO)
assert manifest['source_branch'] == 'task/product-research-recovery'
assert manifest['source_head'] == (TASK / 'applied-head.txt').read_text().strip()
source = Path(manifest['snapshot']).resolve()
assert source == run / 'source'
# Native E2E regenerates only explicitly captured PNG outputs in its snapshot.
# Preserve the initial full manifest; account for exact output deltas separately.
delta_path = TASK / 'preview-first-source-mismatch.json'
assert hashlib.sha256(delta_path.read_bytes()).hexdigest() == '3f645d11211c5866ae312337a3d2d711b78b7518e9312c004bfece08c84f5fb9'
delta = json.loads(delta_path.read_text())
assert delta['status'] == 'PREVIEW_NOT_STARTED'
assert delta['source_head'] == manifest['source_head']
assert delta['source_tree_sha256'] == manifest['source_tree_sha256']
overrides = {row['path']: row for row in delta['mismatches']}
assert len(overrides) == len(delta['mismatches']) == 38
for name, row in overrides.items():
    assert name.startswith('docs/screenshots/') and name.endswith('.png')
    assert '..' not in Path(name).parts and not Path(name).is_absolute()
    assert row['before_sha256'] == manifest['files'][name]
for name, initial_hash in manifest['files'].items():
    expected = overrides[name]['after_sha256'] if name in overrides else initial_hash
    assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, name
pins = json.loads((TASK / 'applied-source-pins.json').read_text())
for name, expected in pins.items():
    assert manifest['files'][name] == expected
    assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected
receipt = json.loads((SEED.parent.parent / 'preview-processes.json').read_text())
assert receipt['synthetic'] is True and receipt['provider'] == 'none'
assert SEED.is_file()
spec = importlib.util.spec_from_file_location('approved_local_runner', BUNDLE / 'run_local.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
children = []
with (BUNDLE / '.run.lock').open('r') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    runner.check_ports()
    stop_guard()
    out.mkdir(exist_ok=False)
    config = json.loads((BUNDLE / 'config.json').read_text())
    env = runner.safe_env(Path(config['node_bin']), out)
    env.update({'UNIMATCH_DEMO_MODE': 'true', 'UNIMATCH_AUTH_ENABLED': 'false',
                'UNIMATCH_ENABLE_BROWSER_TIER': 'false', 'UNIMATCH_SEARCH_PROVIDER': 'none'})
    database = out / 'runtime/checks.db'
    seed_sha = hashlib.sha256(SEED.read_bytes()).hexdigest()
    shutil.copy2(SEED, database)
    connection = sqlite3.connect(str(database))
    rows = connection.execute('SELECT id,demo_mode FROM research_runs').fetchall()
    assert rows and all(row[1] == 1 for row in rows)
    count = connection.execute('SELECT count(*) FROM program_results').fetchone()[0]
    assert count == 20
    connection.execute("UPDATE research_runs SET stage='cancelled',cancelled=1,worker_id=NULL,heartbeat_at=NULL,errors=?",
        (json.dumps(['Synthetic preview: research stopped; remaining sources were not checked.']),))
    connection.commit()
    connection.close()
    assert hashlib.sha256(SEED.read_bytes()).hexdigest() == seed_sha
    runner.write_json(out / 'source-manifest.json', manifest)
    runner.write_json(out / 'generated-test-output-delta.json', delta)
    runner.write_json(out / 'synthetic-fixture-receipt.json', {
        'synthetic': True, 'owned_fresh_clone': str(database), 'seed': str(SEED),
        'seed_sha256': seed_sha, 'database_after_sha256': hashlib.sha256(database.read_bytes()).hexdigest(),
        'provider': 'none', 'auth_enabled': False, 'worker_started': False,
        'stage': 'cancelled', 'cancelled': True, 'result_count': count,
        'source_head': manifest['source_head'], 'source_tree_sha256': manifest['source_tree_sha256'],
        'applied_source_pins': pins, 'STOP_sha256': STOP_SHA,
        'snapshot_SHA_qualification': 'Initial pre-check manifest SHA; E2E regenerated exact38 PNG outputs, separately bound. All other declared bytes unchanged.',
        'generated_test_output_delta_sha256': hashlib.sha256(delta_path.read_bytes()).hexdigest(),
    })
    try:
        for name, command, cwd in [
            ('api', ['bash', 'run.sh'], source / 'backend'),
            ('frontend', ['npm', 'run', 'dev'], source / 'frontend'),
        ]:
            log = (out / f'{name}.log').open('wb')
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            children.append((process, log))
        runner.write_json(out / 'preview-processes.json', {
            'pids': [p.pid for p,_ in children], 'head': manifest['source_head'],
            'snapshot_sha256': manifest['source_tree_sha256'], 'synthetic': True,
            'database': env['UNIMATCH_DATABASE_URL'], 'provider': 'none',
            'auth_enabled': False, 'worker_started': False,
        })
        print(f'PREVIEW http://127.0.0.1:5173/#/shortlist HEAD {manifest["source_head"]}', flush=True)
        while all(p.poll() is None for p,_ in children):
            stop_guard()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_errors = []
        for process, log in children:
            try:
                finish_child(process)
            except BaseException as error:
                cleanup_errors.append({'pid': process.pid, 'type': type(error).__name__, 'message': str(error)})
            finally:
                log.close()
        runner.write_json(out / 'cleanup-receipt.json', {
            'owned_pids': [p.pid for p,_ in children], 'errors': cleanup_errors,
            'all_owned_cleanup_attempts_complete': True, 'lock_held_during_cleanup': True,
        })
        stop_guard()
        assert not cleanup_errors, cleanup_errors
        runner.check_ports()
