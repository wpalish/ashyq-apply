from pathlib import Path
import subprocess,json,datetime
b=Path(__file__).resolve().parent;r=b/'runtime/backend';exe='/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python'
files=['evaluation/research/expert/controller.py','evaluation/research/expert/models.py','evaluation/research/expert/selector.py','evaluation/research/local_pilot.py','evaluation/research/pilot_admission.py','tests/test_local_pilot.py']
env={'HOME':str(b/'home'),'PATH':'/usr/bin:/bin','TMPDIR':str(b/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','PYTHONPATH':str(b/'support')+':'+str(r)}
records=[]
for name,options in [('ruff',['ruff','check']),('format',['ruff','format','--check']),('mypy',['mypy','--config-file','mypy.ini','--cache-dir',str(b/'tmp/mypy-cache')])]:
 argv=[exe,'-m',*options,*files];start=datetime.datetime.now(datetime.UTC)
 with (b/f'logs/static-{name}.log').open('xb') as log:result=subprocess.run(argv,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,check=False)
 records.append({'name':name,'argv':argv,'cwd':str(r),'environment':env,'exit_code':result.returncode,'started':start.isoformat(),'ended':datetime.datetime.now(datetime.UTC).isoformat()})
 print(name,result.returncode,(b/f'logs/static-{name}.log').read_text())
(b/'logs/static.execution.json').write_text(json.dumps(records,indent=2)+'\n')
