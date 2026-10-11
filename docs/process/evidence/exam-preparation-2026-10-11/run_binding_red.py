from pathlib import Path
import fcntl, hashlib, json, os, subprocess, tempfile, shutil
root=Path(__file__).resolve().parent
src=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source')
out=root/'evidence/binding-baseline-red';out.mkdir(parents=True,exist_ok=False)
lock=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
paths=['backend/app/domain/preparation.py','backend/tests/test_preparation_domain.py','backend/tests/test_preparation_api.py']
def pins(): return {p:hashlib.sha256((src/p).read_bytes()).hexdigest() for p in paths}
before=pins();(out/'source-before.json').write_text(json.dumps(before,indent=2))
rt=Path(tempfile.mkdtemp(prefix='um-binding-red-'))
try:
 test=rt/'test_preparation_domain.py';test.write_bytes((root/'proposals/evidence-binding/files/backend/tests/test_preparation_domain.py').read_bytes())
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(src/'backend'),'UNIMATCH_SEARCH_PROVIDER':'none','UNIMATCH_DECISION_PROVIDER':'none','UNIMATCH_DATABASE_URL':'sqlite:///'+str(rt/'unused.db'),'UNIMATCH_CACHE_DIR':str(rt/'cache'),'UNIMATCH_EXPORT_DIR':str(rt/'exports')}
 argv=['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',str(src/'backend/.venv/bin/python'),'-m','pytest','-c',str(src/'backend/pytest.ini'),str(test),'--junitxml='+str(out/'junit.xml')]
 with (out/'pytest.log').open('wb') as log: result=subprocess.run(argv,cwd=src/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 after=pins();(out/'source-after.json').write_text(json.dumps(after,indent=2))
 receipt={'exit_code':result.returncode,'source_unchanged':before==after,'scope':'proposed pure controls against unchanged native app; not API/full gate','network':'OS_DENIED','argv':argv}
finally:
 shutil.rmtree(rt);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
receipt['runtime_removed']=not rt.exists();(out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
