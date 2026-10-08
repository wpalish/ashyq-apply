from pathlib import Path
import json,hashlib,shutil,datetime
base=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
own=base/'work/local-round15/b-final-peer'
a=base/'work/local-round15/a-local-pilot-proposal'
repo=base/'work/ashyq-apply'
r=own/'runtime/backend'
def meta(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
m=a/'ready-manifest.json'
assert meta(m)['sha256']=='f4867ac3befe294c650e7e5e7e972470ddb9f491d82e2a1214d7d5cd6392196b'
files=json.loads(m.read_text())['files']
assert all(meta(a/k)==v for k,v in files.items())
for name in ('ruff.toml','mypy.ini','pytest.ini'):
 shutil.copyfile(repo/'backend'/name,r/name)
for group in ('app','evaluation/research'):
 for p in (repo/'backend'/group).rglob('*.py'):
  q=r/p.relative_to(repo/'backend');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
q=r/'app/adapters/discovery/institution_registry.json';q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/'backend/app/adapters/discovery/institution_registry.json',q)
(r/'scripts').mkdir(exist_ok=True);(r/'scripts/__init__.py').write_text('')
shutil.copyfile(repo/'backend/scripts/canary_discovery.py',r/'scripts/canary_discovery.py')
(r/'tests').mkdir(exist_ok=True);(r/'tests/__init__.py').write_text('')
q=r/'evaluation/research/data/identity_bindings.reviewed.json';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps({'version':'offline-owned-synthetic','bindings':[]})+'\n')
(r/'evaluation/__init__.py').write_text('')
final=json.loads((a/'source-manifest.json').read_text())
for p in (a/'proposed/backend').rglob('*.py'):
 q=r/p.relative_to(a/'proposed/backend');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
support=own/'support';support.mkdir(exist_ok=True)
(support/'sitecustomize.py').write_text('''import socket, subprocess\ndef denied(*args, **kwargs):\n    raise AssertionError("B offline peer denies network/DNS/CLI/process")\nsocket.create_connection=denied\nsocket.getaddrinfo=denied\nsocket.socket.connect=denied\nsocket.socket.connect_ex=denied\nsubprocess.run=denied\nsubprocess.Popen=denied\n''')
(own/'home').mkdir(exist_ok=True)
(own/'logs').mkdir(exist_ok=True)
(own/'tmp').mkdir(exist_ok=True)
(own/'author-history').mkdir(exist_ok=True)
for k in ['logs/attempt1.xml','logs/attempt1.result.json','logs/attempt1.execution.json','logs/attempt2.xml','logs/attempt3.xml','logs/attempt6.xml','logs/attempt7.xml','restoration-qualification.json']:
 if (a/k).exists():shutil.copyfile(a/k,own/'author-history'/Path(k).name)
primary={str(p.relative_to(repo)):meta(p) for p in [repo/'backend'/Path(k).relative_to('proposed/backend') for k in files if k.startswith('proposed/backend/') and (repo/'backend'/Path(k).relative_to('proposed/backend')).exists()]}
record={'time':datetime.datetime.now(datetime.UTC).isoformat(),'author_manifest':meta(m),'selected_files':len(files),'selected_bytes':sum(v['bytes'] for v in files.values()),'author_source_manifest':meta(a/'source-manifest.json'),'source_files':{str(p.relative_to(r)):meta(p) for p in (a/'proposed/backend').rglob('*.py') for p in [r/p.relative_to(a/'proposed/backend')]},'primary_before':primary,'stop_before':meta(base/'work/local-round7/provider-STOP.json'),'own_import_root':str(r),'no_private_namespace_content_copied':True,'socket_and_process_denial':meta(support/'sitecustomize.py')}
(own/'runtime-prepared.json').write_text(json.dumps(record,indent=2)+'\n')
(own/'setup-history.json').write_text(json.dumps({'prior_error':'FileNotFoundError: backend/pyproject.toml absent during source-copy preparation','phase':'pre-import setup','qualification':'no app/tests executed; actual ruff.toml/mypy.ini/pytest.ini used in subsequent preparation','prior_runtime_partial_preserved':True},indent=2)+'\n')
print(json.dumps({'selected':len(files),'bytes':record['selected_bytes'],'six_source_files':len(record['source_files']),'stop':record['stop_before']}))
