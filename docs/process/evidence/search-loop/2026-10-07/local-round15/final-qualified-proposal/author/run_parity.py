from pathlib import Path
import shutil,subprocess,json,hashlib
b=Path(__file__).resolve().parent;r=b/'runtime/backend';old=b/'legacy-runtime/backend';old.mkdir(parents=True,exist_ok=True)
for group in ('app','evaluation'):
 for p in (r/group).rglob('*.py'):
  q=old/p.relative_to(r);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
for name in ('controller','models','selector'):(old/f'evaluation/research/expert/{name}.py').write_bytes((b/f'originals/{name}.py').read_bytes())
exe='/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python';logs=b/'logs'
records=[]
for mode,path in [('original',old),('proposed',r)]:
 out=b/'parity-outputs'/mode;argv=[exe,str(b/'parity.py'),str(out)];env={'HOME':str(Path.home()),'PATH':'/usr/bin:/bin','PYTHONPATH':str(path),'PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false'}
 with (logs/f'parity-{mode}.log').open('xb') as log:result=subprocess.run(argv,cwd=path,env=env,stdout=log,stderr=subprocess.STDOUT,check=False)
 records.append(dict(argv=argv,cwd=str(path),environment=env,exit_code=result.returncode))
values=[(b/'parity-outputs'/mode/'parity.original.json').read_bytes() for mode in ('original','proposed')]
record={'executions':records,'whole_legacy_json_bytes_equal':values[0]==values[1],'bytes':len(values[0]),'sha256':hashlib.sha256(values[0]).hexdigest(),'qualification':'same synthetic legacy fixture on original and final proposed ordinary source modules; no model/CLI/provider/SQL'}
(logs/'legacy-parity.json').write_text(json.dumps(record,indent=2));print(record['whole_legacy_json_bytes_equal'],record['bytes'])
