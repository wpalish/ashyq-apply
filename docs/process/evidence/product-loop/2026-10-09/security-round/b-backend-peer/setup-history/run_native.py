from pathlib import Path
import os,subprocess,json,hashlib,datetime
r=Path(__file__).resolve().parent;root=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply');python=root/'backend/.venv/bin/python'
env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(r/'runtime/backend')+os.pathsep+str(r/'guard'),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1','AUDIT_NETWORK_LOG':str(r/'network.json'),'UNIMATCH_DATABASE_URL':'sqlite:///'+str(r/'bootstrap.db'),'UNIMATCH_CACHE_DIR':str(r/'cache'),'UNIMATCH_EXPORT_DIR':str(r/'exports'),'UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','UNIMATCH_ENVIRONMENT':'development'}
argv=[str(python),'-m','pytest','-q','tests/test_social_moderation.py','tests/test_security.py','tests/test_security_peer.py','--basetemp='+str(r/'owned-tmp/pytest'),'--junitxml='+str(r/'junit.xml')]
(r/'execution-before.json').write_text(json.dumps({'argv':argv,'env':env,'cwd':str(r/'runtime/backend'),'executable_sha':hashlib.sha256(python.resolve().read_bytes()).hexdigest(),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
with (r/'stdout.log').open('wb') as out,(r/'stderr.log').open('wb') as err:result=subprocess.run(argv,env=env,cwd=r/'runtime/backend',stdout=out,stderr=err,timeout=120)
(r/'execution-after.json').write_text(json.dumps({'exit_code':result.returncode},indent=2)+'\n');print(result.returncode)
