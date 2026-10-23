from pathlib import Path
import subprocess,json,datetime,os
b=Path(__file__).resolve().parent;r=b/'runtime/backend';exe='/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python'
files=['evaluation/research/expert/controller.py','evaluation/research/expert/models.py','evaluation/research/expert/selector.py','evaluation/research/local_pilot.py','evaluation/research/pilot_admission.py','tests/test_local_pilot.py']
env={'HOME':str(b/'home'),'PATH':'/usr/bin:/bin','TMPDIR':str(b/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','PYTHONPATH':str(b/'support')+os.pathsep+str(r)}
commands=[('native21',['pytest','-q','-o','addopts=','-o','cache_dir='+str(b/'tmp/pytest-cache'),'--basetemp',str(b/'tmp/native21'),'--junitxml',str(b/'logs/native21.xml'),str(r/'tests/test_local_pilot.py'),str(r/'tests/test_expert_catalogue_trace.py')+'::test_complete_findings_are_unreviewed_and_match_the_saved_source']),('ruff',['ruff','check',*files]),('format',['ruff','format','--check',*files]),('mypy',['mypy','--config-file','mypy.ini','--cache-dir',str(b/'tmp/mypy-cache'),*files])]
results=[]
for name,cmd in commands:
 argv=[exe,'-m',*cmd];start=datetime.datetime.now(datetime.UTC)
 with (b/f'logs/{name}.log').open('xb') as log:result=subprocess.run(argv,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,check=False)
 results.append({'name':name,'argv':argv,'cwd':str(r),'environment':env,'exit_code':result.returncode,'started':start.isoformat(),'ended':datetime.datetime.now(datetime.UTC).isoformat()})
 print(name,result.returncode,(b/f'logs/{name}.log').read_text())
(b/'logs/peer.execution.json').write_text(json.dumps(results,indent=2)+'\n')
