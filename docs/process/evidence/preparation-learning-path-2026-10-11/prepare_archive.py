"""Root-only finite archive builder. Execute only after all terminal gates and reviews."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent
S=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source')
D=S/'docs/process/evidence/preparation-learning-path-2026-10-11'
assert not D.exists(),'Never overwrite an existing archive'
items={}
def add(rel):
 p=R/rel;assert p.is_file(),rel
 assert '..' not in Path(rel).parts
 items[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
inv=json.loads((R/'audits/archive-inventory-recommendation.json').read_text())
for rel,v in inv['explicit_current_recommendations'].items():
 p=R/rel
 if p.is_file():
  if v.get('sha256'):assert hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'],rel
  add(rel)
 # Future proof names are separately admitted only from closed gate directories below.
for rel in ['audits/archive-inventory-recommendation.md','audits/archive-inventory-recommendation.json','audits/navigation-fixture-correction-review.md','audits/navigation-fixture-correction-review-seal.json','audits/primary-static-root-check.json','audits/display-correction-review.md','audits/display-correction-review-seal.json','audits/backend-sqlite-terminal-review.md','audits/backend-sqlite-terminal-review-pins.json','audits/prepared-report-product-review.md','audits/prepared-report-product-review-seal.json','audits/report-precision-correction.json','audits/deadline-learning-follow-through.md','audits/deadline-learning-follow-through-source-pins.json','REPORT.prepared.md','REPORT.corrected-prepared.md','REPORT.final.md','FINAL_SOURCE_PINS_navigation-aligned.json','FINAL_SOURCE_PINS_table-readable.json','run_static_frontend_corrected.py','run_static_frontend_readable.py','prepare_archive.py']:
 add(rel)
for folder in ['navigation-fixture-correction','evidence/static-frontend-accepted','evidence/static-frontend-corrected','evidence/static-frontend-readable','evidence/demo-seed-qualified','table-readability-correction']:
 for p in (R/folder).iterdir():
  assert p.is_file(),p
  add(str(p.relative_to(R)))
full=R/'evidence/backend-full/20261011T163856052464Z'
assert json.loads((full/'result.json').read_text())['status']=='PASS'
for p in full.iterdir():
 if p.is_file(): add(str(p.relative_to(R)))
for phase in ['sqlite','postgres']:
 assert json.loads((full/phase/'result.json').read_text())['status']=='PASS'
 for p in (full/phase).iterdir():
  assert p.is_file(),p
  if p.name=='.coverage':continue # Coverage JSON/XML retain the measured tool result.
  assert p.suffix in {'.json','.xml','.log','.sb'},p
  add(str(p.relative_to(R)))
terminal=json.loads((R/'audits/PRIMARY_FINAL_RUNS.json').read_text())
for rel in terminal['native_roots']:
 f=R/rel
 assert json.loads((f/'run.json').read_text())['exit_code']==0
 # Exact saved top-level receipts/logs/config/environment and finite synthetic PNGs only.
 for p in f.iterdir():
  if p.is_file() and p.suffix in {'.json','.xml','.log','.py','.sb','.mts','.ts'}:
   add(str(p.relative_to(R)))
 for p in (f/'harness').iterdir():
  assert p.is_file(),p
  add(str(p.relative_to(R)))
 for folder in [f/'docs/screenshots',f/'docs/screenshots/mobile']:
  if not folder.exists():continue
  for p in folder.iterdir():
   if p.is_dir():
    assert p.name=='mobile' and folder==f/'docs/screenshots',p
    continue
   assert p.is_file() and p.suffix=='.png',p
   add(str(p.relative_to(R)))
 # Keep first-failure safe text evidence if explicitly declared; no raw auth dumps/traces.
for rel in terminal['additional_final_evidence']:add(rel)
D.mkdir(parents=True)
for rel,v in items.items():
 p=D/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,p)
 assert p.stat().st_size==v['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256']
index={'schema':'finite-original-proof-archive-v1','executable_head':terminal['executable_head'],'status':'LOCAL_ACCEPTED_NOT_MAIN_OR_PRODUCTION','entries':dict(sorted(items.items())),'original_file_count':len(items),'original_bytes':sum(v['bytes'] for v in items.values()),'index_self_excluded':True,'qualifications':['Author proposals and targeted tests are not primary gates','First failed runs retained','No DB/dependencies/private/auth state/traces/HTML reports','Original practice, not calibrated diagnosis/full course/official score/search quality']}
(D/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
assert {str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}==set(items)|{'INDEX.json'}
print(json.dumps({k:index[k] for k in ['status','executable_head','original_file_count','original_bytes']}))
