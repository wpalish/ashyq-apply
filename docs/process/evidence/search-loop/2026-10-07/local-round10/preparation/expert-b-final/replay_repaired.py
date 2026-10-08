"""Normal actual driver import; no main/preflight/execute/network."""
from pathlib import Path
import hashlib
import importlib
import inspect
import json
import socket
import subprocess
import sys

OWN=Path(__file__).resolve().parent
PIN=json.loads((OWN/'replay-PIN.json').read_text())
DRIVER=Path(PIN['driver_path'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(DRIVER)==PIN['driver_sha256']
assert sha(OWN/'positive-fixtures.prepared.json')==PIN['positive_prepared_sha256']
prior=OWN.parent/'b-baseline-repaired-validator-review'
assert sha(prior/'controls.original.json')==PIN['original_controls_sha256']
assert not (OWN/'results.repaired.json').exists()
denied_calls=[]
def denied(*a,**k):
    denied_calls.append(True)
    raise AssertionError('Only offline validate/capture_kind allowed')
socket.getaddrinfo=socket.create_connection=denied
subprocess.run=subprocess.Popen=subprocess.check_output=denied
sys.path.insert(0,str(DRIVER.parent))
driver=importlib.import_module('execute_baseline')
assert Path(driver.__file__).resolve()==DRIVER.resolve()
assert inspect.signature(driver.validate).parameters['require_complete_job'].default is True
driver.main=driver.preflight=driver.write=denied
original=json.loads((prior/'controls.original.json').read_text())
positive=json.loads((OWN/'positive-fixtures.prepared.json').read_text())['controls']
rows=[]
for group,controls in [('original140',original),('positive5',positive)]:
    for control in controls:
        e=control['envelope'];modes={}
        for mode,kwargs in [('strict_default',{}),('bounded_partial',{'require_complete_job':False})]:
            expected=control['strict_accept'] if mode=='strict_default' else control['partial_accept']
            exception=None;kind=None
            try:
                errors=driver.validate(e['case'],e['capture'],e['observed'],e['budget'],e['raw'],**kwargs)
                closed=type(errors) is list and all(type(v) is str and bool(v) for v in errors)
                accepted=closed and not errors
                if accepted:kind=driver.capture_kind(e['observed'],e['budget'],e['raw'])
            except Exception as exc:errors=None;closed=False;accepted=False;exception=type(exc).__name__
            modes[mode]={'expected_accept':expected,'accepted':accepted,'closed':closed,'errors':errors,'exception':exception,'capture_kind':kind,'passed':closed and accepted is expected}
        rows.append({'group':group,**control,'modes':modes})
assert sha(DRIVER)==PIN['driver_sha256']
assert not denied_calls
results={'driver_sha256':PIN['driver_sha256'],'normal_driver_import':str(Path(driver.__file__).resolve()),'schema_path':str(Path(sys.modules['evaluation.research.schema'].__file__).resolve()),'source_identity_config_read':'Actual validator reads output IdentityMap config; no label/scorer/dataset loader called or identity contents printed.','network_provider_model_main_preflight_execute_calls':0,'groups':{},'results':rows}
for group in ['original140','positive5']:
    group_rows=[r for r in rows if r['group']==group]
    modes=[m for r in group_rows for m in r['modes'].values()]
    results['groups'][group]={'controls':len(group_rows),'assertions':len(modes),'pass':sum(m['passed'] for m in modes),'red':sum(not m['passed'] for m in modes),'exceptions':sum(m['exception'] is not None for m in modes)}
(OWN/'results.repaired.json').write_text(json.dumps(results,indent=2,allow_nan=True)+'\n')
print(json.dumps({k:v for k,v in results.items() if k!='results'},indent=2))
print('RED',[r['case'] for r in rows if any(not m['passed'] for m in r['modes'].values())])
