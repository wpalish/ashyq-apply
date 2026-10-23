import fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parent;source=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source');out=root/'evidence/static-persistence12';out.mkdir(parents=True,exist_ok=False)
lock=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock').open('r+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def pins():
 dirs=['frontend/src','frontend/e2e','backend/app','backend/tests','backend/migrations']
 return {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for d in dirs for p in (source/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
before=pins();(out/'source-before.json').write_text(json.dumps(before,indent=2))
steps=[('ruff',['.venv/bin/python','-m','ruff','check','app','tests','evaluation'],'backend'),('format',['.venv/bin/python','-m','ruff','format','--check','app','tests','evaluation'],'backend'),('mypy',['.venv/bin/python','-m','mypy','app','tests'],'backend'),('typecheck',['npm','run','typecheck'],'frontend'),('lint',['npm','run','lint'],'frontend'),('unit',['npm','test','--','--run','--reporter=default','--reporter=junit','--outputFile='+str(out/'frontend-junit.xml')],'frontend'),('build',['npm','run','build'],'frontend')]
results=[]
for name,cmd,d in steps:
 print('START '+name,flush=True);t=time.monotonic()
 with (out/(name+'.log')).open('wb') as log:
  r=subprocess.run(['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',*cmd],cwd=source/d,stdout=log,stderr=subprocess.STDOUT,timeout=360)
 results.append({'step':name,'argv':cmd,'exit_code':r.returncode,'seconds':time.monotonic()-t});print('END '+name+' '+str(r.returncode),flush=True)
 if r.returncode:break
after=pins();(out/'source-after.json').write_text(json.dumps(after,indent=2));(out/'result.json').write_text(json.dumps({'steps':results,'before_after_equal':before==after,'status':'PASS' if len(results)==7 and all(r['exit_code']==0 for r in results) and before==after else 'FAIL_OR_INCOMPLETE'},indent=2));fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
raise SystemExit(0 if len(results)==7 and all(r['exit_code']==0 for r in results) and before==after else 2)
