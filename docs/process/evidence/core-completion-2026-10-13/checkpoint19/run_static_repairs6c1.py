from pathlib import Path
import fcntl,subprocess,json,hashlib
stage=Path(__file__).resolve().parent;base=stage.parents[1];lab=base/'product-platform/2026-10-12/g3-execution/source';out=stage/'evidence/repairs-static6c1';out.mkdir();lock=(base/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def pins():return {str(p.relative_to(lab)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['backend/app','backend/tests','backend/migrations'] for p in (lab/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
before=pins();(out/'source-before.json').write_text(json.dumps(before,indent=2));results=[]
for name,args in [('heads',['alembic','heads']),('ruff',['python','-m','ruff','check','app','tests']),('format',['python','-m','ruff','format','--check','app','tests']),('mypy',['python','-m','mypy','app','tests'])]:
 args[0]=str(lab/'backend/.venv/bin'/args[0]);log=(out/(name+'.log')).open('wb');r=subprocess.run(['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',*args],cwd=lab/'backend',stdout=log,stderr=subprocess.STDOUT);log.close();results.append({'step':name,'exit_code':r.returncode});print(name+': '+str(r.returncode),flush=True)
 if r.returncode:break
after=pins();(out/'source-after.json').write_text(json.dumps(after,indent=2));good=len(results)==4 and not any(x['exit_code'] for x in results) and before==after;(out/'result.json').write_text(json.dumps({'steps':results,'source_equal':before==after,'status':'PASS' if good else 'FAIL'},indent=2));fcntl.flock(lock,fcntl.LOCK_UN);raise SystemExit(0 if good else 2)
