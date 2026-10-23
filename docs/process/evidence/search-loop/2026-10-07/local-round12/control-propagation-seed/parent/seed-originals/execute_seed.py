"""Import only prepared safe_env; execute finite owned, denied-network children."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN = json.loads((ROOT / 'PLAN.json').read_text())
helper = Path(PLAN['safe_env_module'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(helper) == PLAN['safe_env_sha256']
spec = importlib.util.spec_from_file_location('_prepared_runner_safe_env_only', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
node = Path(json.loads((helper.parent / 'config.json').read_text())['node_bin'])
env = module.safe_env(node, ROOT)
env.update({'PYTHONDONTWRITEBYTECODE': '1', 'UNIMATCH_DEMO_MODE': 'true',
            'UNIMATCH_ENABLE_BROWSER_TIER': 'false', 'UNIMATCH_SEARCH_PROVIDER': 'none',
            'UNIMATCH_DATABASE_URL': f'sqlite:///{ROOT / "runtime/seed.db"}',
            'UNIMATCH_AUTO_MIGRATE': 'false'})
assert not (ROOT / 'candidate/backend/.env').exists()
records = []
for action in ('heads', 'migrate', 'seed', 'inspect'):
    args = [sys.executable, str(ROOT / 'guarded_child.py'), action]
    start = time.monotonic()
    child = subprocess.run(args, cwd=ROOT / 'candidate/backend', env=env,
                           capture_output=True, text=True, timeout=60)
    target = ROOT / f'{action}.raw.log'
    assert not target.exists()
    target.write_text(child.stdout + child.stderr)
    record = {'action': action, 'argv': args, 'cwd': str(ROOT / 'candidate/backend'),
              'exit_code': child.returncode, 'seconds': time.monotonic() - start,
              'child_guard_sha256': sha(ROOT / 'guarded_child.py'),
              'log_sha256': sha(target)}
    records.append(record)
    print(json.dumps(record), flush=True)
    state = json.loads((ROOT / f'{action}.execution.json').read_text())
    if child.returncode or state['network_attempts'] or not state['candidate_pins_pre_post_equal']:
        (ROOT / 'commands.original.json').write_text(json.dumps(records, indent=2)+'\n')
        raise SystemExit(child.returncode or 1)
(ROOT / 'commands.original.json').write_text(json.dumps(records, indent=2)+'\n')
