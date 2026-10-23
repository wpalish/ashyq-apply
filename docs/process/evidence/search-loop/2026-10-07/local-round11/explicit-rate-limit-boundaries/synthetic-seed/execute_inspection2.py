"""Only safe_env import and four finite child commands; no local-runner main."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

B=Path(__file__).resolve().parent
P=json.loads((B/'PLAN.json').read_text())
helper=Path(P['safe_env_module'])
assert hashlib.sha256(helper.read_bytes()).hexdigest()==P['safe_env_module_sha256']
spec=importlib.util.spec_from_file_location('_read_only_local_runner',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
# Only nonsecret Node path is read; no main, snapshot, doctor, ports or run methods.
node=Path(json.loads((helper.parent/'config.json').read_text())['node_bin'])
env=module.safe_env(node,B)
env.update({'PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','UNIMATCH_DATABASE_URL':f'sqlite:///{B/"runtime/seed.db"}','UNIMATCH_AUTO_MIGRATE':'false'})
assert not (Path(P['snapshot'])/'backend/.env').exists()
commands=[]
(B/'safe-environment-inspection2.json').write_text(json.dumps({'helper_sha256':P['safe_env_module_sha256'],'flags':{k:v for k,v in env.items() if k.startswith('UNIMATCH_') or k in ['CI','PYTHONUNBUFFERED','PYTHONDONTWRITEBYTECODE']},'omitted_full_environment':True},indent=2)+'\n')
for action in ['inspect2']:
    command=[sys.executable,str(B/'guarded_inspection2.py'),action]
    start=time.monotonic()
    process=subprocess.run(command,cwd=Path(P['snapshot'])/'backend',env=env,capture_output=True,text=True,timeout=90)
    log=B/(action+'.raw.log');assert not log.exists();log.write_text(process.stdout+process.stderr)
    record={'action':action,'command':command,'cwd':str(Path(P['snapshot'])/'backend'),'exit':process.returncode,'seconds':round(time.monotonic()-start,3),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
    commands.append(record);print(json.dumps(record),flush=True)
    state=json.loads((B/(action+'.execution.json')).read_text())
    if process.returncode or state['network_attempts'] or not state['snapshot_prefix_999_before_after_equal']:
        (B/'commands-inspection2.original.json').write_text(json.dumps(commands,indent=2)+'\n')
        raise SystemExit(process.returncode or 1)
(B/'commands-inspection2.original.json').write_text(json.dumps(commands,indent=2)+'\n')
