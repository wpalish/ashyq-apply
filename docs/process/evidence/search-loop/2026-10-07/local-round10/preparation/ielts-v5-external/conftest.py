"""Author cases preserved; current-app offline support, no author writer import."""
import json,sys,types
from pathlib import Path
OWN=Path(__file__).resolve().parent
sys.path.insert(0,str(OWN))
import replay_proposal as replay
for name in ['replay_v3_boundaries','replay_variant_decline']:
 source=(replay.ORIGIN/(name+'.py')).read_text()
 module=types.ModuleType(name)
 # Only immutable CASES/IELTS literals; no imports/writers/source loader.
 import ast
 tree=ast.parse(source)
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'CASES','IELTS'} for t in node.targets):
   for target in node.targets:
    if isinstance(target,ast.Name):setattr(module,target.id,ast.literal_eval(node.value))
 sys.modules[name]=module
parent=types.ModuleType('replay_parent15')
parent.CASES=json.loads((replay.ORIGIN/'root-v2-red-receipt/original-controls.json').read_text())['results']
parent.IELTS={'ielts_min_overall','ielts_min_subscore','ielts_accepted_types'}
sys.modules[parent.__name__]=parent

def pytest_sessionfinish(session,exitstatus):
 import hashlib,importlib
 records=[]
 for name in ['app.adapters.page_classifier','app.adapters.html_parse','app.adapters.scope_reader','app.adapters.requirements.section_scope','app.adapters.document_ir','app.domain.claim_verifier','app.adapters.fetching']:
  m=importlib.import_module(name);p=Path(m.__file__).resolve();assert p.is_relative_to(replay.REPO)
  records.append({'name':name,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 (OWN/(Path(session.config.getoption('basetemp')).name+'.imports.json')).write_text(json.dumps({'normal_current_app_dependencies':records,'diagnostic_classifier_overrides':replay.DIAGNOSTIC_OVERRIDES,'production_permission_overrides':0,'flag_default_in_source':False},indent=2)+'\n')
