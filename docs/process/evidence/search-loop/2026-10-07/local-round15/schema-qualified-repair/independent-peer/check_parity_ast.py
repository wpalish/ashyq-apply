from pathlib import Path
import json,subprocess,hashlib,ast,shutil,datetime,os
b=Path(__file__).resolve().parent;prior=b.parent/'b-final-peer';a=b.parent/'a-schema-compatibility';r=b/'runtime/backend';exe='/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python'
def meta(p):
 d=p.read_bytes();return {'sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d)}
shutil.copyfile(prior/'parity_owned.py',b/'parity_owned.py')
env={'HOME':str(b/'home'),'PATH':'/usr/bin:/bin','TMPDIR':str(b/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','UNIMATCH_DEMO_MODE':'true','UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none','PYTHONPATH':str(b/'support')+os.pathsep+str(r)}
argv=[exe,str(b/'parity_owned.py'),str(b/'parity-repaired')];began=datetime.datetime.now(datetime.UTC)
with (b/'logs/parity-repaired.log').open('xb') as log:result=subprocess.run(argv,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=15,check=False)
assert result.returncode==0
old=prior/'parity/original/parity.original.json';new=b/'parity-repaired/parity.original.json';assert old.read_bytes()==new.read_bytes();assert meta(new)['bytes']==3905
oldraw=next((prior/'parity/original/raw').glob('*.json'));newraw=next((b/'parity-repaired/raw').glob('*.json'));assert oldraw.read_bytes()==newraw.read_bytes()
preserved=a/'originals/evaluation/research/expert/models.py';changed=r/'evaluation/research/expert/models.py'
def tree(p):return ast.parse(p.read_text())
ot,nt=tree(preserved),tree(changed);cl=next(x for x in nt.body if isinstance(x,ast.ClassDef) and x.name=='ExpertTrace');added=[n for n in cl.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ['model_json_schema','expert_wall_only_json_schema']];assert len(added)==2
cl.body=[n for n in cl.body if n not in added];assert ast.dump(ot,include_attributes=False)==ast.dump(nt,include_attributes=False)
oldtests=tree(a/'originals/tests/test_local_pilot.py');newtests=tree(r/'tests/test_local_pilot.py');oldnodes={n.name:n for n in oldtests.body if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef))};newnodes={n.name:n for n in newtests.body if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef))};assert oldnodes.keys()==newnodes.keys();delta=[name for name in oldnodes if ast.dump(oldnodes[name],include_attributes=False)!=ast.dump(newnodes[name],include_attributes=False)];assert delta==['test_legacy_default_raw_output_shape'];assert len([n for n in oldnodes if n.startswith('test_')])==20
record={'argv':argv,'cwd':str(r),'environment':env,'exit_code':result.returncode,'started':began.isoformat(),'ended':datetime.datetime.now(datetime.UTC).isoformat(),'repaired_whole3905_equal_original':True,'legacy_json':meta(new),'raw_equal_original':True,'legacy_raw':meta(newraw),'only_two_class_methods_added_ast_all_else_equal':True,'same20test_names':True,'19test_bodies_and_all_helpers_unchanged_ast':True,'only_extended_test':delta[0],'original_reference':str(old),'qualification':'single synthetic legacy fixture; no real runtime/model/SQL/network admission'}
(b/'logs/parity-ast.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in ['environment','argv','cwd']},indent=2))
