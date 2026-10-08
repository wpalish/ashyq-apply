from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET,ast,datetime
b=Path(__file__).resolve().parent;base=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');repo=base/'work/ashyq-apply';run=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T082019Z-check-b4a62808');old=run.parent/'20261008T053629Z-check-6693acd5'
def meta(p):
 d=p.read_bytes();return {'sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d)}
def ids(p):
 r=ET.parse(p);cs=r.findall('.//testcase');values={(c.attrib['classname'],c.attrib['name']) for c in cs};assert len(values)==len(cs);assert not r.findall('.//failure')+r.findall('.//error');return values
m=json.loads((run/'source-manifest.json').read_text());expected=json.loads((base/'work/local-round15/root-orchestrator/source-after-1002.json').read_text())['file_sha256'];assert m['source_head']=='c8c9dfcd9fb810a13a80e983f8d16754a1e3fde2';assert m['source_status']=='';assert m['source_tree_sha256']=='7b1bf63c3f5e6234bb2bb99e138d0aa390e2cf8ef93c179a75de2585fbb199a9';assert hashlib.sha256(json.dumps(m['files'],sort_keys=True).encode()).hexdigest()==m['source_tree_sha256'];assert len(m['files'])==9656
snapshot=Path(m.get('snapshot',run/'source'))
for k,v in expected.items():assert m['files'][k]==v==meta(repo/k)['sha256']==meta(snapshot/k)['sha256']
o1,o2=ids(old/'backend-sqlite.xml'),ids(old/'backend-postgresql.xml');assert o1==o2 and len(o1)==4349
names=[n.name for n in ast.parse((repo/'backend/tests/test_local_pilot.py').read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')];assert len(names)==20
out={'time_utc':datetime.datetime.now(datetime.UTC).isoformat(),'status':'FROZEN_SOURCE_AND_OLD_IDENTITIES_BOUND_TERMINAL_PENDING','run':str(run),'source_manifest':meta(run/'source-manifest.json'),'source_head':m['source_head'],'source_tree_sha256':m['source_tree_sha256'],'snapshot':str(snapshot),'source_status':m['source_status'],'frozen_metadata_paths':len(m['files']),'selected_physical_source_current_snapshot_equal':len(expected),'old_run':str(old),'old_JUnit':{db:meta(old/f'backend-{db}.xml') for db in ('sqlite','postgresql')},'old_case_identities':len(o1),'old_identity_set_sha256':hashlib.sha256(json.dumps(sorted(o1)).encode()).hexdigest(),'expected_new_case_names':names,'STOP':meta(base/'work/local-round7/provider-STOP.json'),'terminal_full_verdict':'PENDING'}
(b/'full-start.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='expected_new_case_names'},indent=2))
