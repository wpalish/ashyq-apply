from pathlib import Path
import os,subprocess,json,hashlib,sys
B=Path(__file__).resolve().parent;C=B/'runtime/backend';L=B/'logs';L.mkdir(exist_ok=True)
name=sys.argv[1];python='/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python'
argv=[python,'-m','pytest','tests/test_local_pilot.py','-q','--junitxml='+str(L/(name+'.xml'))]
env={'HOME':str(Path.home()),'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(C),'UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
def pins():return {str(p.relative_to(C)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in (B/'proposed/backend').rglob('*.py') for p in [C/p.relative_to(B/'proposed/backend')]}
receipt={'argv':argv,'cwd':str(C),'environment':env,'source_before':pins(),'qualification':'denied network with mock source/processes; not actual OS/runtime admission'}
(L/(name+'.execution.json')).write_text(json.dumps(receipt,indent=2))
with (L/(name+'.log')).open('xb') as out:result=subprocess.run(argv,cwd=C,env=env,stdout=out,stderr=subprocess.STDOUT,check=False)
receipt.update(exit_code=result.returncode,source_after=pins());(L/(name+'.result.json')).write_text(json.dumps(receipt,indent=2));print(name,result.returncode)
