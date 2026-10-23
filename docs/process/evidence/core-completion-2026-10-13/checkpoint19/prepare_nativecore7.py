from pathlib import Path
import shutil,json,hashlib
s=Path(__file__).resolve().parent;b=s.parents[1];old=b/'product-platform/2026-10-12/g2-execution';new=s/'native-core7';new.mkdir(exist_ok=False);(new/'e2e').mkdir();files={}
for name in ['run-native-recovery.py','runtime-child.py','loopback-only.sb']:
 p=old/'e2e'/name;raw=p.read_bytes();t=raw.decode().replace('2026-10-12/g2-execution/source','2026-10-12/g3-execution/source').replace('5229','5237').replace('8139','8147')
 if name=='run-native-recovery.py':
  t=t.replace("assert suite in {'demo', 'auth', 'ux'}","assert suite in {'demo', 'auth'}")
  t=t.replace("before = source_pins()","before = source_pins()\nexpected=json.loads((ROOT/'expected-source-pins.json').read_text())\nassert before == expected, 'Sealed source drift: STOP'\nprimary=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials')\nassert all(hashlib.sha256((primary/p).read_bytes()).hexdigest()==sha for p,sha in expected.items()), 'Primary/lab source mismatch: STOP'")
  t=t.replace("' webServer: {json.dumps(webservers)},", "' webServer: {json.dumps(webservers)},")
  t=t.replace("f' outputDir:", "' testMatch: \"core-admissions.spec.ts\", testIgnore: [], projects: [native.projects[0]],\\n'\n    f' outputDir:")
  t=t.replace("'PORT': '8147',", "'PORT': '8147',\n    'CORE_NATIVE_AUTH': 'true' if suite == 'auth' else 'false',")
 (new/'e2e'/name).write_text(t);files[name]={'preimage':hashlib.sha256(raw).hexdigest(),'postimage':hashlib.sha256(t.encode()).hexdigest()}
p=old/'run_native_recovery_pair.py';shutil.copyfile(p,new/p.name)
(new/'PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','paths':files,'source':'g3-execution/source','ports':[5237,8147],'ownership':'Fresh runtimes, lock, no foreign reuse, primary/lab exact pins, allow only own loopback; native app/worker/migrations with providers none.','test_source':'native-core-journey-proposal.spec.ts external only; exact helper/native source write-ahead pending'},indent=2)+'\n')
print('Prepared own native7 harness; no runtime/source/Git changes.')
