from pathlib import Path
import shutil,json,subprocess,hashlib,datetime,os
b=Path(__file__).resolve().parent;a=b.parent/'a-local-pilot-proposal';r=b/'runtime/backend';old=b/'legacy-runtime/backend'
for group in ('app','evaluation'):
 for p in (r/group).rglob('*.py'):
  q=old/p.relative_to(r);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
for name in ('controller','models','selector'):
 p=a/f'originals/{name}.py';q=old/f'evaluation/research/expert/{name}.py';shutil.copyfile(p,q)
shutil.copyfile(a/'parity.py',b/'parity_owned.py')
exe='/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python'
records=[]
for mode,root in [('original',old),('final',r)]:
 out=b/'parity'/mode
 env={'HOME':str(b/'home'),'PATH':'/usr/bin:/bin','TMPDIR':str(b/'tmp'),'PYTHONPATH':str(b/'support')+os.pathsep+str(root),'PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none'}
 argv=[exe,str(b/'parity_owned.py'),str(out)];start=datetime.datetime.now(datetime.UTC)
 with (b/f'logs/parity-{mode}.log').open('xb') as log:result=subprocess.run(argv,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=15,check=False)
 records.append({'argv':argv,'cwd':str(root),'environment':env,'exit_code':result.returncode,'started':start.isoformat(),'ended':datetime.datetime.now(datetime.UTC).isoformat()})
 assert result.returncode==0,(mode,(b/f'logs/parity-{mode}.log').read_text())
values=[(b/'parity'/m/'parity.original.json').read_bytes() for m in ('original','final')]
raws=[next((b/'parity'/m/'raw').glob('*.json')).read_bytes() for m in ('original','final')]
out={'executions':records,'whole_json_bytes_equal':values[0]==values[1],'raw_bytes_equal':raws[0]==raws[1],'bytes':len(values[0]),'sha256':hashlib.sha256(values[0]).hexdigest(),'raw_bytes':len(raws[0]),'raw_sha256':hashlib.sha256(raws[0]).hexdigest(),'fixture_source_sha256':hashlib.sha256((b/'parity_owned.py').read_bytes()).hexdigest(),'qualification':'one native original/final legacy synthetic fixture; fixed clock/synthetic Fetcher result; model_dump, canonical trace/packet digests, journal, raw/summary and legacy55 diagnostic; no runtime/model/network guarantee'}
(b/'logs/legacy-parity-owned.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='executions'}))
assert out['whole_json_bytes_equal'] and out['raw_bytes_equal']
