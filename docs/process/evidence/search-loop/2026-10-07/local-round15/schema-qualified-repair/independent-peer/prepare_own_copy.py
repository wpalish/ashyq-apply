from pathlib import Path
import json,hashlib,shutil,datetime
b=Path(__file__).resolve().parent;base=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');prior=base/'work/local-round15/b-final-peer';repo=base/'work/ashyq-apply';r=b/'runtime/backend';r.mkdir(parents=True,exist_ok=True)
def meta(p):
 data=p.read_bytes();return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
for group in ('app','evaluation','scripts'):
 for p in (prior/'runtime/backend'/group).rglob('*.py'):
  q=r/p.relative_to(prior/'runtime/backend');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
for name in ('ruff.toml','mypy.ini','pytest.ini'):
 shutil.copyfile(prior/'runtime/backend'/name,r/name)
for k in ['app/adapters/discovery/institution_registry.json','evaluation/research/data/identity_bindings.reviewed.json']:
 q=r/k;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/'runtime/backend'/k,q)
(r/'tests').mkdir(exist_ok=True);(r/'tests/__init__.py').write_text('')
for k in ['backend/tests/test_local_pilot.py','backend/tests/test_expert_catalogue_trace.py','backend/evaluation/research/expert/data/trace.schema.json']:
 q=r/Path(k).relative_to('backend');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/k,q)
(b/'support').mkdir(exist_ok=True);shutil.copyfile(prior/'support/sitecustomize.py',b/'support/sitecustomize.py')
for name in ('home','tmp','logs'):(b/name).mkdir(exist_ok=True)
source=[repo/'backend/evaluation/research/expert/models.py',repo/'backend/tests/test_local_pilot.py',repo/'backend/tests/test_expert_catalogue_trace.py',repo/'backend/evaluation/research/expert/data/trace.schema.json']
record={'time_utc':datetime.datetime.now(datetime.UTC).isoformat(),'status':'OWN_COPY_PREPARED_NO_IMPORTS_AWAIT_EXACT_REPAIR','base_is_prior_f486_accepted_copy':True,'current_source_before':{str(p.relative_to(repo)):meta(p) for p in source},'schema_fixture_copy':meta(r/'evaluation/research/expert/data/trace.schema.json'),'old_test_copy':meta(r/'tests/test_expert_catalogue_trace.py'),'guard':meta(b/'support/sitecustomize.py'),'namespace':'owned synthetic empty identity map only','original_tests_and_fixture_unmodified':True,'app_imports_tests_so_far':0}
(b/'copy-prepared.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
