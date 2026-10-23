"""Finite hash/AST audit only. No app imports, test execution, DB or Git."""
from pathlib import Path
from datetime import datetime, UTC
import ast
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
BASE=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO=BASE/'work/ashyq-apply'
ROUND=BASE/'work/local-round12'
A=ROUND/'a-control-propagation-proposal'
B=ROUND/'b-control-propagation-demo-seed'
ROOT=ROUND/'root-control-propagation'
RUN=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T043357Z-check-0d98eeb3')
STOP=BASE/'work/local-round7/provider-STOP.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):return json.loads(p.read_text())


assert sha(A/'ready-manifest.json')=='6776d1ccedabd3d668b167cd1d8184b2cd179e01989e73a778e6081c642589ab'
assert sha(B/'ready-manifest.json')=='511fb556d71eaf4d08efc7de44883e13e85ba167042ba66f9046fc8838e712fc'
a=load(A/'ready-manifest.json');seed=load(B/'ready-manifest.json')
for origin,obj in ((A,a),(B,seed)):
 for rel,row in obj['files'].items():
  f=origin/rel
  assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'],str(f)
before=load(ROOT/'source-before-999.json')['file_sha256']
after=load(ROOT/'source-after-999.json')['file_sha256']
assert len(before)==len(after)==999 and set(before)==set(after)
changed=set(a['source_hashes'])
assert len(changed)==3
applied={};observed={};other=[]
for rel,expected in before.items():
 f=REPO/rel;h=sha(f);observed[rel]=h
 assert h==after[rel],rel+' does not match root after'
 if rel in changed:
  row=a['source_hashes'][rel]
  assert h==row['sha256'] and f.stat().st_size==row['bytes'],rel
  assert f.read_bytes()==(A/'proposed'/rel).read_bytes(),rel+' differs from proposed exact bytes'
  applied[rel]={'sha256':h,'bytes':f.stat().st_size,'A_exact_bytes':True,'root_after_match':True}
 else:
  assert h==expected,rel+' unexpected source modification'
  other.append(rel)
assert len(other)==996
assert {r for r in before if before[r]!=after[r]}==changed
bpins=load(B/'candidate-app-pins.json')
assert len(bpins)==242
for rel,h in bpins.items():assert sha(REPO/rel)==h,rel+' seed binding differs'
root_record=load(ROOT/'source-integration.json')
assert root_record['applied']=={r:{'sha256':row['sha256'],'bytes':row['bytes']} for r,row in applied.items()}
assert root_record['other_selected_unchanged']==996 and root_record['seed_app_binding']==242
assert root_record['proposed_sha256']==sha(A/'ready-manifest.json')
assert root_record['seed_sha256']==sha(B/'ready-manifest.json')
assert sha(STOP)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'

rel='backend/app/adapters/search/retrieval.py'
old=ast.parse((A/'original'/rel).read_text());new=ast.parse((REPO/rel).read_text())
imports=[n for n in new.body if isinstance(n,ast.ImportFrom) and n.module=='app.pipeline.control']
assert len(imports)==1 and [n.name for n in imports[0].names]==['LeaseLost','RunCancelled','UniversityReadStopped']
new.body.remove(imports[0]);handlers=0
for n in ast.walk(new):
 if not isinstance(n,ast.Try):continue
 for h in list(n.handlers):
  if isinstance(h.type,ast.Tuple) and [getattr(x,'id',None) for x in h.type.elts]==['UniversityReadStopped','RunCancelled','LeaseLost']:
   assert len(h.body)==1 and isinstance(h.body[0],ast.Raise) and h.body[0].exc is None and h.body[0].cause is None
   n.handlers.remove(h);handlers+=1
assert handlers==1 and ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
root_ast=load(ROOT/'source-ast-delta.json')
assert root_ast['removed_new_imports']==1 and root_ast['removed_new_handlers']==1 and root_ast['other_native_AST_equal'] is True
body={}
for rel in changed-{'backend/app/adapters/search/retrieval.py'}:
 orig=ast.parse((A/'original'/rel).read_text());current=ast.parse((REPO/rel).read_text())
 defs=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
 od,nd=defs(orig),defs(current)
 assert all(nd.get(k)==v for k,v in od.items())
 body[rel]={'existing_top_level_definitions_preserved':len(od),'appended_top_level_definitions':list(nd.keys()-od.keys()),'all_original_bodies_and_expectations_AST_equal':True}
full=load(RUN/'source-manifest.json');snapshot=Path(full['snapshot'])
assert full['source_head']=='d076e435cb1a6247f171ffb2411c6ab79a0ba857'
assert full['source_branch']=='task/search-control-propagation'
for rel,h in observed.items():
 assert full['files'][rel]==h,rel+' fresh full snapshot manifest differs'
 # Hash opaque bytes only; never parse corpus/gold semantics.
 assert sha(snapshot/rel)==h,rel+' physical snapshot differs'
inputs={
 'A-ready':A/'ready-manifest.json',
 'B-seed-ready':B/'ready-manifest.json',
 'root-before999':ROOT/'source-before-999.json',
 'root-after999':ROOT/'source-after-999.json',
 'root-integration':ROOT/'source-integration.json',
 'root-AST':ROOT/'source-ast-delta.json',
 'B-app242':B/'candidate-app-pins.json',
 'full-source-manifest':RUN/'source-manifest.json',
 'provider-STOP':STOP,
}
input_pins={k:{'path':str(v),'sha256':sha(v),'bytes':v.stat().st_size} for k,v in inputs.items()}
# Selected small metadata originals only. Full 8754-entry source manifest remains
# referenced by hash, not duplicated; no source/corpus bodies or runtime DB copy.
for name in ('root-before999','root-after999','root-integration','root-AST','B-app242'):
 f=inputs[name];dest=HERE/'inputs'/(name+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(f,dest)
result={
 'status':'PASS_EXACT_PRIMARY_INTEGRATION_FRESH_FULL_PENDING',
 'checked_utc':datetime.now(UTC).isoformat(),
 'applied3':applied,'other_selected_unchanged':996,'current_source999_match':True,
 'B_seed_app242_matches_primary':True,'A_selected78_and_B_seed_selected_files_hash_size_verified':True,
 'native_AST_delta':{'added_imports':1,'added_bare_reraise_handlers':1,'everything_else_equal':True,'root_AST_metadata_agrees':True,'root_AST_source_application_false_is_preserved_preapplication_metadata':root_ast['source_application'] is False},
 'test_body_compatibility':body,
 'fresh_full_source':{'run_id':RUN.name,'source_head':full['source_head'],'source_branch':full['source_branch'],'source_tree_sha256':full['source_tree_sha256'],'source_manifest_sha256':sha(RUN/'source-manifest.json'),'physical_snapshot999_matches_current_primary':True,'source_3_exact_proposal':True,'qualification':'Fresh full is underway as reported by parent; source binding only, no gate/result acceptance inferred.'},
 'input_pins':input_pins,'STOP_unchanged':True,
 'actions':{'app_imports':0,'tests_replayed':0,'DB_access':0,'Git_actions':0,'network_provider_model_calls':0,'repo_source_writes':0,'corpus_gold_semantic_reads':0},
 'qualification':'Operational source integration evidence only; source_application false on root AST record refers to the retained preapplication structural check; exact actual files/root integration record prove current application. No full-gate completion/live/quality/launch claim.'
}
(HERE/'audit-results.original.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'source999-observed.json').write_text(json.dumps({'file_sha256':observed,'changed_paths':sorted(changed),'STOP_sha256':sha(STOP)},indent=2)+'\n')
print(json.dumps({'status':result['status'],'applied3_exact':True,'other996_unchanged':True,'B242_matches':True,'snapshot999_matches':True,'native_AST_minimal':True,'STOP_unchanged':True,'run_id':RUN.name,'source_head':full['source_head'],'source_tree_sha256':full['source_tree_sha256']}))
