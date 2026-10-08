"""Use installed package safe_env; only finite own replay subprocesses."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PYTHON = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python')
HELPER = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/run_local.py')
p = argparse.ArgumentParser()
p.add_argument('mode', choices=('off','on'))
p.add_argument('lane', choices=('pytest','A','B','ruff','format'))
a = p.parse_args()
run_dir = HERE / 'executions' / (a.mode+'-'+a.lane)
run_dir.mkdir(parents=True, exist_ok=False)
spec = importlib.util.spec_from_file_location('read_only_local_runner', HELPER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
env = mod.safe_env(Path('/usr/bin'), run_dir)
env.update({'PYTHONPATH': str(HERE/'replay'/a.mode/'backend'), 'PYTHONDONTWRITEBYTECODE': '1',
            'UNIMATCH_DEMO_MODE': 'true', 'UNIMATCH_ENABLE_BROWSER_TIER': 'false',
            'UNIMATCH_SEARCH_PROVIDER': 'none', 'CONTROL_RUNTIME': str(run_dir),
            'SOURCE_ROOT': str(HERE/'replay'/a.mode), 'CONTROL_OUTPUT_DIR': str(run_dir),
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
cwd = HERE/'replay'/a.mode/'backend'
if a.lane == 'pytest':
    argv = [str(PYTHON), str(HERE/'bootstrap_pytest.py'), '-p', 'pytest_asyncio.plugin',
            'tests/test_hybrid_retrieval.py', 'tests/test_search_layer_budget_fixes.py',
            '--junitxml='+str(run_dir/'junit.original.xml')]
elif a.lane in {'ruff','format'}:
    argv = [str(PYTHON), '-m', 'ruff', 'check' if a.lane == 'ruff' else 'format']
    if a.lane == 'format': argv.append('--check')
    argv += ['app/adapters/search/retrieval.py','tests/test_hybrid_retrieval.py','tests/test_search_layer_budget_fixes.py']
else:
    argv = [str(PYTHON),str(HERE/('proof-A.py' if a.lane=='A' else 'proof-B.py'))]
    if a.lane == 'B':
        originals=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/local-round12/b-control-propagation-boundaries/PLAN.json')
        cfg=json.loads(originals.read_text())
        for rel,row in cfg['sources'].items():
            row['sha256']=hashlib.sha256((HERE/'replay'/a.mode/rel).read_bytes()).hexdigest()
        (run_dir/'PLAN.json').write_text(json.dumps(cfg,indent=2)+'\n')
record={'argv':argv,'cwd':str(cwd),'environment_safe_flags':{k:env[k] for k in (
 'PYTHONPATH','PYTHONDONTWRITEBYTECODE','UNIMATCH_DEMO_MODE','UNIMATCH_ENABLE_BROWSER_TIER',
 'UNIMATCH_SEARCH_PROVIDER','UNIMATCH_DATABASE_URL','UNIMATCH_CACHE_DIR','UNIMATCH_EXPORT_DIR',
 'CONTROL_RUNTIME','SOURCE_ROOT','CONTROL_OUTPUT_DIR','PYTEST_DISABLE_PLUGIN_AUTOLOAD')},
 'read_only_safe_env_source':str(HELPER),'safe_env_source_sha256':hashlib.sha256(HELPER.read_bytes()).hexdigest()}
(run_dir/'execution.before.json').write_text(json.dumps(record,indent=2)+'\n')
with (run_dir/'stdout.original.log').open('w') as out, (run_dir/'stderr.original.log').open('w') as err:
    result=subprocess.run(argv,cwd=cwd,env=env,stdout=out,stderr=err)
record['exit_code']=result.returncode
(run_dir/'execution.after.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'lane':a.lane,'mode':a.mode,'exit_code':result.returncode,'run_dir':str(run_dir)}))
sys.exit(result.returncode)
