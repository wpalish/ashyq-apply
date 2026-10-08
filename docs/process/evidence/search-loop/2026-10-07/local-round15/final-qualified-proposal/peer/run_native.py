from pathlib import Path
import os,json,subprocess,datetime,hashlib
b=Path(__file__).resolve().parent;r=b/'runtime/backend';exe=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python')
env={'HOME':str(b/'home'),'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':str(b/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONPATH':str(b/'support')+os.pathsep+str(r)}
argv=[str(exe),'-m','pytest','-q','-o','addopts=','-o','cache_dir='+str(b/'tmp/pytest-cache'),'--basetemp',str(b/'tmp/native20'),'--junitxml',str(b/'logs/native20.xml'),str(r/'tests/test_local_pilot.py')]
start=datetime.datetime.now(datetime.UTC)
with (b/'logs/native20.log').open('xb') as log:
 result=subprocess.run(argv,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,check=False)
rec={'argv':argv,'cwd':str(r),'environment':env,'started':start.isoformat(),'ended':datetime.datetime.now(datetime.UTC).isoformat(),'exit_code':result.returncode,'qualification':'final exact copied six files; normal package imports, no A conftest, synthetic namespace/transport/model/isolation only; import-time socket/DNS/process denied'}
(b/'logs/native20.execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(result.returncode);print((b/'logs/native20.log').read_text())
