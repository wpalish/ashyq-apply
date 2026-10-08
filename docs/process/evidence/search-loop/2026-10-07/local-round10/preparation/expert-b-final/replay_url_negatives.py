"""Normal-file import only. Exact URL mapping must retain wrong/order/shape guards."""
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib
import json
import socket
import subprocess
import sys

OWN=Path(__file__).resolve().parent;pin=json.loads((OWN/'replay-PIN.json').read_text());path=Path(pin['driver_path'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(path)==pin['driver_sha256']
def denied(*a,**k):raise AssertionError('No main/preflight/process/network')
socket.getaddrinfo=socket.create_connection=denied;subprocess.run=subprocess.Popen=subprocess.check_output=denied
sys.path.insert(0,str(path.parent));driver=importlib.import_module('execute_baseline')
driver.main=driver.preflight=driver.write=denied
base=json.loads((OWN.parent/'b-baseline-repaired-validator-review/controls.original.json').read_text())[0]['envelope']
first='https://example.edu/programme/computer-science';second='https://example.edu/programme/mathematics'
cases=[('wrong_programme_url',[first],[second],False),('wrong_order',[first,second],[second,first],False),('missing_raw_programmes',None,[first],False),('extra_observed_programme',[first],[first,second],False),('invalid_raw_HttpUrl',['https://'],[],False),('invalid_observed_HttpUrl',[first],['https://'],False),('raw_integer_programme',[123],[first],False),('raw_null_programme',[None],[first],False),('observed_normalized_model_representation',[first],['https://EXAMPLE.edu:443/programme/computer-science'],True)]
results=[]
for name,rawurls,obsurls,expected in cases:
    e=deepcopy(base);inst=e['raw']['canary']['institutions'][0]
    if rawurls is None:del inst['programs']
    else:inst['programs']=rawurls
    e['observed']['programme_urls']=obsurls;e['capture']['observations']=[deepcopy(e['observed'])]
    modes={}
    for lane,kwargs in [('strict_default',{}),('bounded_partial',{'require_complete_job':False})]:
        exception=None;kind=None
        try:
            errors=driver.validate(e['case'],e['capture'],e['observed'],e['budget'],e['raw'],**kwargs)
            closed=type(errors) is list and all(type(v) is str and v for v in errors);accepted=closed and not errors
            if accepted:kind=driver.capture_kind(e['observed'],e['budget'],e['raw'])
        except Exception as exc:errors=None;closed=False;accepted=False;exception=type(exc).__name__
        modes[lane]={'expected_accept':expected,'accepted':accepted,'errors':errors,'exception':exception,'kind':kind,'passed':closed and accepted is expected}
    results.append({'case':name,'envelope':e,'modes':modes})
assert sha(path)==pin['driver_sha256']
out={'driver_sha256':pin['driver_sha256'],'normal_import':True,'network_main_preflight_calls':0,'controls':len(results),'pass':sum(m['passed'] for r in results for m in r['modes'].values()),'red':sum(not m['passed'] for r in results for m in r['modes'].values()),'exceptions':sum(m['exception'] is not None for r in results for m in r['modes'].values()),'results':results}
assert not(OWN/'url-negatives.original.json').exists();(OWN/'url-negatives.original.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
