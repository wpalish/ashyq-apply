from pathlib import Path
import json,hashlib,fcntl,ast,datetime
stage=Path(__file__).resolve().parent;base=stage.parents[1];repo=base/'work/unimatch-calendar-materials';lab=base/'product-platform/2026-10-12/g3-execution/source';grant=json.loads((stage/'APPLICATIONS_4A_GRANT.json').read_text());proposal=stage/'applications4a-proposal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
with (base/'local-runner/.run.lock').open('r+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for path,pre in grant['paths'].items():
  assert sha(repo/path)==pre,(path,'primary drift')
  assert sha(lab/path)==pre,(path,'lab drift')
 old=ast.parse((stage/'applications4a-preimages/backend/app/schemas/admissions_actions.py').read_text());new=ast.parse((proposal/'backend/app/schemas/admissions_actions.py').read_text());oldclasses={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,ast.ClassDef)};newclasses={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,ast.ClassDef)}
 for name,node in oldclasses.items():
  if name!='TodayProjectionV1':assert newclasses[name]==node,('frozen V1 class changed',name)
 rows={}
 for path,pre in grant['paths'].items():
  p=proposal/path
  if not p.exists():continue
  raw=p.read_bytes()
  for target in (repo,lab):q=target/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
  rows[path]={'preimage':pre,'postimage':sha(p)}
 (stage/'APPLICATIONS_4A_APPLICATION.json').write_text(json.dumps({'status':'APPLIED_NOT_EXECUTED','baseline':'b4377de3','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unchanged_frozen_classes':list(oldclasses.keys()-{'TodayProjectionV1'}),'paths':rows},indent=2)+'\n')
print('Applied six paths; every original V1 class AST unchanged except additive Today record union.')
