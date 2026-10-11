import fcntl,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
lock=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock').open('r+')
try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: print('QUEUE_BUSY: no native browser execution started');sys.exit(75)
rows=[]
for suite in ['demo','auth']:
 r=subprocess.run(['/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/backend/.venv/bin/python',str(root/'e2e/run-native.py'),suite])
 rows.append({'suite':suite,'exit_code':r.returncode})
 if r.returncode: break
(root/'evidence/e2e-terminal.json').write_text(json.dumps({'phases':rows,'status':'PASS' if len(rows)==2 and all(r['exit_code']==0 for r in rows) else 'FAIL_OR_INCOMPLETE'},indent=2)+'\n')
fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
raise SystemExit(0 if len(rows)==2 and all(r['exit_code']==0 for r in rows) else 2)
