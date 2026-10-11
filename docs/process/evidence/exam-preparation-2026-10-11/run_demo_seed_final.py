import fcntl,hashlib,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
root=Path(__file__).resolve().parent;src=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source');out=root/'evidence/demo-seed-qualified';out.mkdir(parents=True,exist_ok=False)
lock=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
rt=Path(tempfile.mkdtemp(prefix='um-integrated-seed-'))
env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DATABASE_URL':'sqlite:///'+str(rt/'demo.db'),'UNIMATCH_CACHE_DIR':str(rt/'cache'),'UNIMATCH_EXPORT_DIR':str(rt/'exports'),'UNIMATCH_CORPUS_DIR':str(src/'backend/app/corpus/pages'),'UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','UNIMATCH_DECISION_PROVIDER':'none','UNIMATCH_AUTH_ENABLED':'false','UNIMATCH_PAYMENTS_ENABLED':'false','UNIMATCH_METRICS_ENABLED':'false','UNIMATCH_ENVIRONMENT':'development','UNIMATCH_EMAIL_SENDER':'console'}
base=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',str(src/'backend/.venv/bin/python')]
try:
 with (out/'migration.log').open('wb') as log:migration=subprocess.run(base+['-m','alembic','upgrade','head'],cwd=src/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
 assert migration.returncode==0,'Fresh synthetic database migration failed'
 with (out/'seed.log').open('wb') as log:r=subprocess.run(base+['seed_demo.py'],cwd=src/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 code="import json;from app.db import session_scope;from app.models import ProgramResultRow;\nwith session_scope() as s:\n rows=s.query(ProgramResultRow).order_by(ProgramResultRow.score_total.desc()).all();print(json.dumps([{'university':x.payload['university'],'bucket':x.bucket} for x in rows]))"
 q=subprocess.run(base+['-c',code],cwd=src/'backend',env=env,capture_output=True,text=True,timeout=30)
 (out/'portfolio-query.log').write_text(q.stdout+q.stderr)
 rows=json.loads(q.stdout) if q.returncode==0 else []
 good=bool(rows) and 'Groningen' in rows[0]['university'] and any(('British Columbia' in x['university'] or x['university']=='UBC') and x['bucket']=='OUT_OF_BUDGET' for x in rows)
 result={'migration_exit_code':migration.returncode,'seed_exit_code':r.returncode,'query_exit_code':q.returncode,'portfolio':rows,'order_and_bucket_pass':good,'providers':'none','external_network':'OS_DENIED','synthetic_db':True,'status':'PASS' if r.returncode==0 and q.returncode==0 and good else 'FAIL'}
finally:
 shutil.rmtree(rt);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
result['runtime_removed']=not rt.exists();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(0 if result['status']=='PASS' else 2)
