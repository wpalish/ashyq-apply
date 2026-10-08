"""Source-derived normalized programme-URL fixture only, no live main."""
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib
import json
import socket
import subprocess
import sys

OWN=Path(__file__).resolve().parent
pin=json.loads((OWN/'replay-PIN.json').read_text());driver_path=Path(pin['driver_path'])
assert hashlib.sha256(driver_path.read_bytes()).hexdigest()==pin['driver_sha256']
def denied(*a,**k):raise AssertionError('No main/preflight/process/network')
socket.getaddrinfo=socket.create_connection=denied
subprocess.run=subprocess.Popen=subprocess.check_output=denied
sys.path.insert(0,str(driver_path.parent))
driver=importlib.import_module('execute_baseline')
driver.main=driver.preflight=driver.write=denied
from app.adapters.base import CandidateProgram
from app.domain.enums import DegreeLevel
from evaluation.research.schema import Observation
from pydantic import HttpUrl
base=json.loads((OWN.parent/'b-baseline-repaired-validator-review/controls.original.json').read_text())[0]['envelope']
rows=[]
for url in ['https://example.edu?programme=cs','https://EXAMPLE.edu:443/programme/computer-science','https://example.edu/programme/computer%20science']:
    e=deepcopy(base)
    programme=CandidateProgram(name='Synthetic Computer Science',field='Computer Science',degree=DegreeLevel.BACHELOR,url=url)
    # Native _gather_report preserves programme.url; live.py applies HttpUrl.
    e['raw']['canary']['institutions'][0]['programs']=[programme.url]
    e['raw']['canary']['institutions'][0]['program_page_found']=True
    e['raw']['canary']['totals']['program_pages_found']=1
    obs=Observation.model_validate(e['observed']);obs.programme_urls=[HttpUrl(programme.url)]
    e['observed']=obs.model_dump(mode='json');e['capture']['observations']=[deepcopy(e['observed'])]
    modes={}
    for lane,kwargs in [('strict_default',{}),('bounded_partial',{'require_complete_job':False})]:
        errors=driver.validate(e['case'],e['capture'],e['observed'],e['budget'],e['raw'],**kwargs)
        modes[lane]={'expected_accept':True,'errors':errors,'accepted':not errors,'passed':not errors}
    rows.append({'raw_url':url,'observed_urls':e['observed']['programme_urls'],'envelope':e,'modes':modes})
assert hashlib.sha256(driver_path.read_bytes()).hexdigest()==pin['driver_sha256']
out={'driver_sha256':pin['driver_sha256'],'source_actual_normal_imports':True,'synthetic_source_representation_control':True,'network_main_preflight_calls':0,'results':rows,'assertions':6,'pass':sum(m['passed'] for r in rows for m in r['modes'].values()),'red':sum(not m['passed'] for r in rows for m in r['modes'].values())}
assert not (OWN/'url-seam.original.json').exists()
(OWN/'url-seam.original.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
for r in rows:print(r['raw_url'],r['observed_urls'],r['modes'])
