"""Prepared external native seed gate; never import app in the parent."""
from pathlib import Path
import fcntl,json,hashlib,subprocess,os,shutil,datetime,sqlite3
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';lab=b/'product-platform/2026-10-12/g3-execution/source';lock=(b/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
# Must be invoked only after terminal current full gate and root write-ahead.
assert json.loads((s/'CORE_FINAL_24_QUALIFICATION.json').read_text())['status']=='CONNECTED_CORE_LOCALLY_QUALIFIED_FULL_AND_NATIVE_NOT_DEPLOYED'
out=s/'evidence/seed-final25';out.mkdir(parents=True,exist_ok=False);runtime=out/'owned-runtime';runtime.mkdir();shutil.copytree(lab/'backend/app/corpus/pages',runtime/'corpus');(runtime/'cache').mkdir();(runtime/'exports').mkdir();(runtime/'tmp').mkdir()
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def pins():
 paths=[p for prefix in ['backend/app','backend/migrations','frontend/src','frontend/e2e'] for p in (lab/prefix).rglob('*') if p.is_file() and '__pycache__' not in p.parts];paths += [lab/'backend/seed_demo.py',lab/'backend/alembic.ini']
 return {str(p.relative_to(lab)):h(p) for p in paths}
before=pins();assert all(h(r/p)==sha for p,sha in before.items());(out/'source-before.json').write_text(json.dumps(before,indent=2)+'\n')
env={'PATH':str(lab/'backend/.venv/bin')+':/usr/bin:/bin:/usr/sbin:/sbin','LANG':'en_US.UTF-8','TMPDIR':str(runtime/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','UNIMATCH_DATABASE_URL':'sqlite:///'+str(runtime/'synthetic.db'),'UNIMATCH_CORPUS_DIR':str(runtime/'corpus'),'UNIMATCH_CACHE_DIR':str(runtime/'cache'),'UNIMATCH_EXPORT_DIR':str(runtime/'exports'),'UNIMATCH_ENVIRONMENT':'development','UNIMATCH_AUTO_MIGRATE':'false','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_AUTH_ENABLED':'false','UNIMATCH_SEARCH_PROVIDER':'none','UNIMATCH_DECISION_PROVIDER':'none','UNIMATCH_METRICS_ENABLED':'false','UNIMATCH_PAYMENTS_ENABLED':'false','UNIMATCH_EMAIL_SENDER':'console'}
(out/'synthetic-environment.json').write_text(json.dumps(env,indent=2)+'\n');python=lab/'backend/.venv/bin/python';steps=[]
for name,args in [('migrate',['-m','alembic','upgrade','head']),('seed',['seed_demo.py'])]:
 cmd=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',str(python),*args]
 with (out/(name+'.log')).open('wb') as log:v=subprocess.run(cmd,cwd=lab/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 steps.append({'step':name,'argv':cmd,'exit_code':v.returncode})
 if v.returncode:break
qualified=False;rows=[]
if len(steps)==2 and all(v['exit_code']==0 for v in steps):
 c=sqlite3.connect('file:'+str(runtime/'synthetic.db')+'?mode=ro',uri=True)
 rows=[{'university':name,'score':score,'bucket':json.loads(payload).get('ranking',{}).get('bucket') if json.loads(payload).get('ranking') else None} for name,score,payload in c.execute('select university,score_total,payload from program_results order by score_total desc')];c.close()
 qualified=bool(rows) and rows[0]['university']=='University of Groningen' and any('British Columbia' in row['university'] and row['bucket']=='OUT_OF_BUDGET' for row in rows)
after=pins();(out/'source-after.json').write_text(json.dumps(after,indent=2)+'\n');q={'status':'PASS' if qualified and before==after else 'FAIL_OR_INCOMPLETE','steps':steps,'rows':rows,'source_before_after_equal':before==after,'source_count':len(before),'own_synthetic_db':str(runtime/'synthetic.db'),'scope':'Native seed_demo order, no live/model/provider/production/quality metric; OS denies all IP network. Corpus copied before execution to owned mutable directory.','historical_unknown_input_namespace':'Direct seed is not API pending marker; legacy unknown retained.'};(out/'result.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2));fcntl.flock(lock,fcntl.LOCK_UN);lock.close();raise SystemExit(0 if q['status']=='PASS' else 2)
