from pathlib import Path
import copy,hashlib,importlib.util,json,socket,subprocess,sys
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply'); OLD=R.parent/'local-round9/genuine-baseline';P=R.parent/'local-round10/genuine-baseline'
old=(P/'execute_baseline.py').read_bytes();(P/'execute_baseline.prepared-before-url.original.py').write_bytes(old)
b=(OLD/'execute_baseline.py').read_bytes();assert hashlib.sha256(b).hexdigest()=='4fa670fb54d6f62c296b68e682c2f46417cf02ba0daf75deb69f329be32f269b'
(P/'execute_baseline.py').write_bytes(b)
x=json.loads((P/'PLAN.json').read_text());(P/'PLAN.prepared-before-url.original.json').write_text(json.dumps(x,indent=2)+'\n');x['driver_sha256']=hashlib.sha256(b).hexdigest();(P/'PLAN.json').write_text(json.dumps(x,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('fresh_round10_controller',P/'execute_baseline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def denied(*a,**k):raise AssertionError('transfer smoke: no main/preflight/network/process')
socket.getaddrinfo=socket.create_connection=denied;subprocess.run=subprocess.Popen=subprocess.check_output=denied
m.main=m.preflight=denied
full=json.loads((Path(x['full_gate_run'])/'source-manifest.json').read_text()); controls=[]
for f,k in [('b-baseline-repaired-validator-review-v2/positive-fixtures.prepared.json','controls'),('b-baseline-repaired-validator-review-v2/url-seam.original.json','results')]:
 for row in json.loads((R.parent/'local-round9'/f).read_text())[k]:
  e=copy.deepcopy(row['envelope']);e['capture']['pipeline_sha']=x['source_head'];e['capture']['config']['harness_sha256']=full['files']['backend/evaluation/research/live.py'];e['capture']['config']['mapping_sha256']=full['files']['backend/evaluation/research/mapping.py']
  controls.append((row.get('case',row.get('raw_url')),e,True))
name,e,_=controls[-1];bad=copy.deepcopy(e);bad['observed']['programme_urls']=['https://example.edu/wrong'];bad['capture']['observations']=[copy.deepcopy(bad['observed'])];controls.append(('wrong_url_rejected',bad,False))
results=[]
for name,e,expected in controls:
 for partial in (False,True):
  errors=m.validate(e['case'],e['capture'],e['observed'],e['budget'],e['raw'],require_complete_job=not partial)
  results.append({'name':name,'partial_lane':partial,'expected_accept':expected,'accepted':not errors,'errors':errors,'passed':(not errors)==expected})
assert all(t['passed'] for t in results)
result={'status':'FRESH_PLAN_TRANSFER_VALIDATE_SMOKE_PASS_PEER_PENDING_NO_LIVE','controller_sha256':hashlib.sha256(b).hexdigest(),'plan_sha256':hashlib.sha256((P/'PLAN.json').read_bytes()).hexdigest(),'source_head':x['source_head'],'normal_import_only':True,'main_preflight_network_process_calls':0,'assertions':len(results),'pass':len(results),'results':results}
assert not(P/'transfer-smoke.json').exists();(P/'transfer-smoke.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
