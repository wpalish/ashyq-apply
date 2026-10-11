from pathlib import Path
import datetime, hashlib, json, subprocess
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def check(p,record):
 assert p.is_file() and not p.is_symlink(),str(p)
 assert sha(p)==record['sha256'] and p.stat().st_size==record['bytes'],str(p)
backend=ROOT/'proposals/backend';ui=ROOT/'proposals/ui'
expected={'backend':'ecbd6f5946b64371023d5ab42739d3d8cbe876471f6ed025457f1cc6af772ba1','ui':'a38c543e38976434476950dfdcdbab8fe219898d6d0633204cb98d9d0434739c'}
for name,packet in [('backend',backend),('ui',ui)]:
 ready=load(packet/'READY.json');assert ready['manifest_sha256']==expected[name] and sha(packet/'MANIFEST.json')==expected[name]
 manifest=load(packet/'MANIFEST.json'); entries=manifest['entries'] if name=='backend' else [dict(path=k,**v) for k,v in manifest.items()]
 for record in entries:
  p=(packet/record['path']).resolve();assert p.is_relative_to(packet);check(p,record)
 assert ready.get('contract_sha256',ready.get('backend_contract_sha256'))==sha(backend/'CONTRACT.md')
for name,sealname in [('backend','backend-learning-pack-review-seal.json'),('ui','frontend-learning-path-review-seal.json')]:
 seal=load(ROOT/'audits'/sealname);assert seal['status']=='QUALIFIED_STATIC_ACCEPT' and seal['manifest_sha256']==expected[name] and not seal['final_recheck_issues']
changes=[];bp=load(backend/'source-pins.json')
for relative,value in bp['preserved_source_dependencies'].items(): assert sha(SOURCE/relative)==value,relative
for relative,value in bp['content_inputs'].items(): assert sha(Path(relative))==value,relative
for row in bp['files']:
 changes.append(dict(path=row['path'],before=row['before_sha256'],after=row['after_sha256'],bytes=row['after_bytes'],proposed=backend/'files'/row['path']))
for relative,row in load(ui/'PROPOSED_PINS.json').items():
 changes.append(dict(path=relative,before=None if row['original'] is None else row['original']['sha256'],after=row['proposed']['sha256'],bytes=row['proposed']['bytes'],proposed=ui/'files'/relative))
# Initial read snapshots are historical. Explicit root-owned appended auth controls
# are the only original UI source-input drift; verify the whole original prefix.
ui_inputs=load(ui/'INPUT_PINS.json');exceptions=[]
for relative,row in ui_inputs['paths'].items():
 p=SOURCE/relative
 if relative=='frontend/e2e/auth-journey.spec.ts':
  base=subprocess.check_output(['git','show','c8bd72045574aabd9b2833bb8ba0f34055211c0f:'+relative],cwd=SOURCE)
  assert hashlib.sha256(base).hexdigest()==row['sha256'] and len(base)==row['bytes'] and p.read_bytes().startswith(base)
  exceptions.append({'path':relative,'reason':'exact original prefix plus separately reviewed root control','before':row['sha256'],'current':sha(p)})
 else: check(p,row)
check(ui/'BACKEND_CONTRACT_INPUT.md',ui_inputs['backend_contract'])
assert sha(ui/'BACKEND_CONTRACT_FINAL.md')==sha(backend/'CONTRACT.md')
assert len(changes)==15 and len({r['path'] for r in changes})==15
for row in changes:
 p=SOURCE/row['path'];assert p.resolve().is_relative_to(SOURCE)
 assert (not p.exists()) if row['before'] is None else sha(p)==row['before'],row['path']
 check(row['proposed'],{'sha256':row['after'],'bytes':row['bytes']})
# Hold exact native/spec source bytes through application.
native={r:sha(SOURCE/r) for r in ['frontend/e2e/learning-path.spec.ts','frontend/e2e/auth-journey.spec.ts']}
seal=load(ROOT/'audits/frontend-learning-path-review-seal.json')
assert seal['current_native_spec_sha256']==native['frontend/e2e/learning-path.spec.ts']
assert seal['current_auth_spec_sha256']==native['frontend/e2e/auth-journey.spec.ts']
out=ROOT/'APPLICATION.json';assert not out.exists()
for row in changes:
 p=SOURCE/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(row['proposed'].read_bytes());assert sha(p)==row['after']
assert native=={r:sha(SOURCE/r) for r in native}
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
receipt={'status':'APPLIED_PENDING_WHOLE_GATES','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_head':head,'source':str(SOURCE),'manifests':expected,'changes':[{k:v for k,v in r.items() if k!='proposed'} for r in changes],'native_source':native,'explicit_initial_input_exceptions':exceptions,'runtime_claim':False}
out.write_text(json.dumps(receipt,indent=2)+'\n');print('APPLIED15: '+str(out))
