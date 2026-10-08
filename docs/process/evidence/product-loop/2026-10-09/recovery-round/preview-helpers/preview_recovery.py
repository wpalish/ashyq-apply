"""Owned synthetic preview; use the approved runner's snapshot and safe env."""
import fcntl
import hashlib
import sqlite3
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
spec = importlib.util.spec_from_file_location('local_runner', BUNDLE / 'run_local.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok='--resume' in sys.argv)
preview_lock = (BUNDLE / '.run.lock').open('r')
fcntl.flock(preview_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
runner.check_ports()
if '--source-manifest' in sys.argv:
    manifest = json.loads(Path(sys.argv[sys.argv.index('--source-manifest') + 1]).read_text())
    source = Path(manifest['snapshot'])
    import hashlib
    assert all(hashlib.sha256((source / n).read_bytes()).hexdigest() == h
               for n, h in manifest['files'].items())
elif '--resume' in sys.argv:
    import hashlib
    manifest = json.loads((out / 'source-manifest.json').read_text())
    source = Path(manifest['snapshot'])
    assert all(hashlib.sha256((REPO / n).read_bytes()).hexdigest() == h
               and hashlib.sha256((source / n).read_bytes()).hexdigest() == h
               for n, h in manifest['files'].items())
else:
    source, manifest = runner.snapshot(REPO, out)
runner.write_json(out / 'source-manifest.json', manifest)
config = json.loads((BUNDLE / 'config.json').read_text())
env = runner.safe_env(Path(config['node_bin']), out)
env.update({'UNIMATCH_DEMO_MODE': 'true', 'UNIMATCH_AUTH_ENABLED': 'false',
            'UNIMATCH_ENABLE_BROWSER_TIER': 'false', 'UNIMATCH_SEARCH_PROVIDER': 'none'})
if '--seed-db' in sys.argv:
    import shutil
    seed = Path(sys.argv[sys.argv.index('--seed-db') + 1]).resolve()
    owned_root = Path(__file__).resolve().parents[2]
    allowed_seeds = {
        owned_root / 'work/product-round1/preview-before/runtime/checks.db',
        owned_root / 'work/product-round2/preview-after/runtime/checks.db',
    }
    assert seed in allowed_seeds
    receipt = json.loads((seed.parent.parent / 'preview-processes.json').read_text())
    assert receipt['synthetic'] is True and receipt['provider'] == 'none'
    shutil.copy2(seed, out / 'runtime' / 'checks.db')
# Mutate only the newly cloned, owned synthetic preview database.
if '--partial-stopped' in sys.argv:
    db = out / 'runtime/checks.db'
    before_sha = hashlib.sha256(db.read_bytes()).hexdigest()
    connection = sqlite3.connect(str(db))
    runs = connection.execute('SELECT id,demo_mode FROM research_runs').fetchall()
    assert runs and all(row[1] == 1 for row in runs)
    count = connection.execute('SELECT count(*) FROM program_results').fetchone()[0]
    assert count == 20
    connection.execute("UPDATE research_runs SET stage='cancelled',cancelled=1,worker_id=NULL,heartbeat_at=NULL,errors=?",
                       (json.dumps(['Synthetic preview: research stopped; remaining sources were not checked.']),))
    connection.commit()
    connection.close()
    runner.write_json(out / 'synthetic-fixture-receipt.json', {
        'synthetic': True, 'owned_cloned_database': str(db), 'provider': 'none',
        'auth_enabled': False, 'worker_started': False, 'stage': 'cancelled',
        'cancelled': True, 'result_count': count, 'seed_before_sha256': before_sha,
        'database_after_sha256': hashlib.sha256(db.read_bytes()).hexdigest(),
        'source_head': manifest['source_head'], 'source_tree_sha256': manifest['source_tree_sha256'],
    })
children = []
try:
    for name, cmd, cwd in [
        ('api', ['bash', 'run.sh'], source / 'backend'),
        ('frontend', ['npm', 'run', 'dev'], source / 'frontend'),
    ]:
        log = (out / f'{name}.log').open('wb')
        process = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        children.append((process, log))
    runner.write_json(out / 'preview-processes.json', {
        'head': manifest['source_head'], 'snapshot_sha256': manifest['source_tree_sha256'],
        'pids': [p.pid for p, _ in children], 'synthetic': True,
        'database': env['UNIMATCH_DATABASE_URL'], 'provider': 'none',
    })
    print(f'PREVIEW {source} HEAD {manifest["source_head"]} SHA256 {manifest["source_tree_sha256"]}', flush=True)
    while all(p.poll() is None for p, _ in children):
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    for process, log in children:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        log.close()
