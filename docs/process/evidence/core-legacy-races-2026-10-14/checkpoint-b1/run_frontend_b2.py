import fcntl,hashlib,json,os,subprocess,time,sys
from pathlib import Path
root=Path(__file__).resolve().parent
repo=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials')
mode=sys.argv[1]; assert mode in ['off','on','full']
out=root/'evidence'/('frontend-b-'+mode+'2');out.mkdir(parents=True,exist_ok=False)
lock=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def pins():
 dirs=['frontend/src','frontend/e2e','backend/app','backend/tests','backend/migrations']
 return {str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for d in dirs for p in (repo/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
before=pins();(out/'source-before.json').write_text(json.dumps(before,indent=2))
node=Path('/Users/wpalish/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node');env=os.environ.copy();env['PATH']=str(node.parent)+':'+env['PATH']
unit=['npm','test','--','--run']
if mode!='full':unit+=['src/screens/ProfileScreen.context.test.tsx','src/lib/store.profileValidation.test.tsx']
unit+=['--reporter=default','--reporter=junit','--outputFile='+str(out/'frontend-junit.xml')]
steps=[('unit',unit)] if mode!='full' else [('typecheck',['npm','run','typecheck']),('lint',['npm','run','lint']),('unit',unit),('build',['npm','run','build'])]
results=[]
try:
 for name,cmd in steps:
  print('START '+name,flush=True);t=time.monotonic()
  with (out/(name+'.log')).open('wb') as log:
   r=subprocess.run(['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',*cmd],cwd=repo/'frontend',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360)
  results.append({'step':name,'argv':cmd,'exit_code':r.returncode,'seconds':time.monotonic()-t});print('END '+name+' '+str(r.returncode),flush=True)
  if r.returncode:break
finally:
 after=pins();(out/'source-after.json').write_text(json.dumps(after,indent=2));result={'mode':mode,'source':str(repo),'steps':results,'before_after_equal':before==after,'status':'PASS' if len(results)==len(steps) and all(r['exit_code']==0 for r in results) and before==after else 'FAIL_OR_INCOMPLETE'}
 (out/'result.json').write_text(json.dumps(result,indent=2));fcntl.flock(lock,fcntl.LOCK_UN);lock.close();print(json.dumps(result),flush=True)
raise SystemExit(0 if result['status']=='PASS' else 2)
