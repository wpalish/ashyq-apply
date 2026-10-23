"""Pinned normal external validator import; synthetic envelopes only."""
from pathlib import Path
from copy import deepcopy
import ast
import hashlib
import importlib
import inspect
import json
import socket
import subprocess
import sys
import httpx

OWN=Path(__file__).resolve().parent
PLAN=json.loads((OWN/'PLAN.json').read_text())
DRIVER=Path(PLAN['inputs']['driver']['path'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(DRIVER)==PLAN['inputs']['driver']['sha256']
inputs={}
for name,pin in PLAN['inputs'].items():
 p=Path(pin['path']);assert sha(p)==pin['sha256']
 q=OWN/'inputs'/p.parent.name/p.name;q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():
  assert sha(q)==pin['sha256']
 else:
  q.write_bytes(p.read_bytes())
 if name!='driver':inputs[name]=json.loads(p.read_text())
# Bind approved asset only from actual pinned protocol, never other researchdata.
protocol_plan=json.loads((DRIVER.parent/'PLAN.json').read_text())
source_root=Path(protocol_plan['source_snapshot'])
identity_file=(source_root/'backend/evaluation/research/data/identity_bindings.reviewed.json').resolve()
allowed_mapping_read=identity_file
reads=[]
original_read_text=Path.read_text

def checked_read_text(p,*a,**kw):
 resolved=p.resolve()
 if '/evaluation/research/data/' in str(resolved):
  assert resolved==allowed_mapping_read, 'unapproved research data read denied'
  reads.append(str(resolved))
 if any(x.lower() in {'gold','labels','heldout','held-out'} for x in resolved.parts):
  raise AssertionError('labels/gold reads denied')
 return original_read_text(p,*a,**kw)
Path.read_text=checked_read_text

def denied(*a,**kw):raise AssertionError('review denies main/preflight/process/DNS/HTTP/provider/model')
socket.getaddrinfo=socket.create_connection=socket.socket.connect=denied
subprocess.run=subprocess.Popen=subprocess.check_output=subprocess.call=denied
httpx.Client.request=httpx.AsyncClient.request=denied
sys.dont_write_bytecode=True
sys.path.insert(0,str(DRIVER.parent))
driver=importlib.import_module('execute_baseline')
assert Path(driver.__file__).resolve()==DRIVER.resolve() and sha(DRIVER)==PLAN['inputs']['driver']['sha256']
assert inspect.signature(driver.validate).parameters['require_complete_job'].default is True
driver.main=driver.preflight=driver.write=denied
main_node=next(n for n in ast.parse(DRIVER.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
explicit_false=any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='validate' and any(k.arg=='require_complete_job' and isinstance(k.value,ast.Constant) and k.value.value is False for k in n.keywords) for n in ast.walk(main_node))

def evaluate(group,rows,old134=False):
 results=[]
 for row in rows:
  e=row['envelope'];before=json.dumps(e,sort_keys=True,allow_nan=True)
  modes={}
  lanes=[('strict_default',{})] if old134 else [('strict_default',{}),('bounded_partial',{'require_complete_job':False})]
  for lane,kwargs in lanes:
   expected=(row['expectation']=='accept') if old134 else row['strict_accept'] if lane=='strict_default' else row['partial_accept']
   current=deepcopy(e);exception=None
   try:
    errors=driver.validate(current['case'],current['capture'],current['observed'],current['budget'],current['raw'],**kwargs)
   except Exception as exc:errors=None;exception={'type':type(exc).__name__,'message':str(exc)}
   closed=type(errors) is list and all(type(t) is str and t for t in errors)
   accept=closed and not errors
   kind=None;kind_exception=None
   if lane=='bounded_partial' and accept:
    try:kind=driver.capture_kind(current['observed'],current['budget'],current['raw'])
    except Exception as exc:kind_exception=type(exc).__name__
   expected_kind=None
   if lane=='bounded_partial' and accept:
    p=current['raw']['canary']['job_protocol']
    partial=bool(current['observed']['error'] or current['raw']['canary']['run_error'] or current['budget']['stop_reason'] or p['job_status']!='succeeded')
    expected_kind='BOUNDED_TERMINAL_PARTIAL_JOB_'+p['job_status'] if partial else 'COMPLETED_JOB_CAPTURE'
   modes[lane]={'expected_accept':expected,'accepted':accept,'passed':None if expected is None else closed and accept is expected,'closed_diagnostics':closed,'errors':errors,'exception':exception,'capture_kind':kind,'expected_kind_if_accepted':expected_kind,'capture_kind_passed':None if lane!='bounded_partial' or not accept else kind_exception is None and kind==expected_kind,'capture_kind_exception':kind_exception,'input_unchanged':before==json.dumps(current,sort_keys=True,allow_nan=True)}
  results.append({'case':row['case'],'note':row.get('note'),'envelope':e,'original_expectation':row.get('expectation'),'modes':modes})
 summary={'controls':len(results),'definite_lane_assertions':sum(m['passed'] is not None for r in results for m in r['modes'].values()),'pass':sum(m['passed'] is True for r in results for m in r['modes'].values()),'red':sum(m['passed'] is False for r in results for m in r['modes'].values()),'policy':sum(m['passed'] is None for r in results for m in r['modes'].values()),'exceptions':sum(m['exception'] is not None for r in results for m in r['modes'].values()),'capture_kind_checks':sum(m['capture_kind_passed'] is not None for r in results for m in r['modes'].values()),'capture_kind_red':sum(m['capture_kind_passed'] is False for r in results for m in r['modes'].values()),'input_mutation':sum(not m['input_unchanged'] for r in results for m in r['modes'].values())}
 return {'summary':summary,'results':results}

own_urls=json.loads((OWN/'url-controls.original.json').read_text())
peer_urls=[{'case':'exact_B3URL_'+str(i+1),'envelope':row['envelope'],'strict_accept':row['modes']['strict_default']['expected_accept'],'partial_accept':row['modes']['bounded_partial']['expected_accept'],'note':row['raw_url']} for i,row in enumerate(inputs['B3URL']['results'])]
groups={
 'A134':evaluate('A134',inputs['A134']['results'],old134=True),
 'A46':evaluate('A46',inputs['A46']['controls']),
 'B140':evaluate('B140',inputs['B140']),
 'B18_original_red_subset':evaluate('B18',inputs['B18']['results']),
 'B5':evaluate('B5',inputs['B5']['controls']),
 'B3URL':evaluate('B3URL',peer_urls),
 'own6URL':evaluate('own6URL',own_urls),
}
modules=[]
for name in ['evaluation.research.schema','evaluation.research.mapping','evaluation.research.identities','app.schemas.claim','app.domain.enums']:
 m=importlib.import_module(name);p=Path(m.__file__).resolve();assert p.is_relative_to(source_root/'backend');modules.append({'name':name,'path':str(p),'sha256':sha(p)})
for name,pin in PLAN['inputs'].items():assert sha(Path(pin['path']))==pin['sha256']
assert sha(DRIVER)==PLAN['inputs']['driver']['sha256']
result={'own_url_input_sha256':sha(OWN/'url-controls.original.json'),'driver_sha256':sha(DRIVER),'normal_driver_import':str(Path(driver.__file__).resolve()),'strict_default_true':True,'static_main_explicit_partial_false':explicit_false,'original_inputs_unchanged':True,'mapping_read_allowlist':[str(allowed_mapping_read)],'actual_mapping_asset_sha256':sha(identity_file),'approved_mapping_reads':len(reads),'actual_dependency_modules':modules,'normal_import_only':True,'main_preflight_process_network_provider_model_calls':0,'groups':groups}
target=OWN/'controls.offline.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=True)+'\n')
print(json.dumps({name:group['summary'] for name,group in groups.items()},indent=2))
print('REDS='+json.dumps({name:[r['case'] for r in group['results'] if any(m['passed'] is False for m in r['modes'].values())] for name,group in groups.items()}))
