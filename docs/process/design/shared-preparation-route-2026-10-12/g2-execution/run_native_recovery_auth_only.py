import fcntl,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
lock=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock').open('r+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 for suite in ['auth']:
  print('START_NATIVE_'+suite.upper(),flush=True)
  result=subprocess.run([sys.executable,str(root/'e2e/run-native-recovery.py'),suite],cwd=root)
  print('END_NATIVE_'+suite.upper()+' '+str(result.returncode),flush=True)
  if result.returncode: raise SystemExit(result.returncode)
finally:
 fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
