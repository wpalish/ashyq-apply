from pathlib import Path
import hashlib,json
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply'); P=R.parent/'local-round10/genuine-baseline'; plan=json.loads((P/'PLAN.json').read_text());S=Path(plan['source_snapshot'])/'backend'
files={}
for name in ['evaluation/research/metrics.py','evaluation/research/scorecard.py','evaluation/research/schema.py','evaluation/research/data/ground_truth.reviewed.json','evaluation/research/data/ground_truth.reviewed9.json']:
 f=S/name;files[name]=hashlib.sha256(f.read_bytes()).hexdigest()
script='''"""Offline score only after ten validated bounded terminal capture records."""
from pathlib import Path
import hashlib,json,socket,subprocess,sys
OWN=Path(__file__).resolve().parent
PLAN=json.loads((OWN/'PLAN.json').read_text())
SOURCE=Path(PLAN['source_snapshot'])/'backend'
PINS=json.loads((OWN/'score-pins.json').read_text())
for name,digest in PINS['files'].items():
 assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest,name
def denied(*a,**k):raise AssertionError('offline scoring forbids network/model/process')
socket.getaddrinfo=socket.create_connection=denied
subprocess.Popen=subprocess.run=subprocess.check_output=denied
sys.path.insert(0,str(SOURCE))
from evaluation.research.schema import Capture,Dataset
from evaluation.research.metrics import score
from evaluation.research.scorecard import label_outcomes
receipt=json.loads((OWN/'execution-receipt.json').read_text())
assert receipt['status']=='TERMINAL_ORIGINAL10_CAPTURE_COMPLETE_AWAIT_OFFLINE_SCORING'
assert receipt['attempted']==PLAN['cases'] and receipt['remaining']==[]
assert set(receipt['capture_kinds'])==set(PLAN['cases']) and not receipt['validation_errors']
observations=[];origins=[];parts=[]
for case in PLAN['cases']:
 paths=list((OWN/case).glob('*/capture.json'));assert len(paths)==1
 path=paths[0];part=Capture.model_validate_json(path.read_text());assert [o.case_id for o in part.observations]==[case]
 assert part.pipeline_sha==PLAN['source_head'];parts.append(part);observations+=part.observations
 origins.append({'case':case,'capture_kind':receipt['capture_kinds'][case],'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'physical_budget':part.config['case_budgets'][case]})
merged=parts[0].model_copy(update={'observations':observations,'config':{'provenance':'offline aggregation only, original captures immutable','cohort':PLAN['cases'],'originals':origins,'source_sha256':PLAN['source_tree_sha256']}})
results={}
for name in ['ground_truth.reviewed.json','ground_truth.reviewed9.json']:
 dataset=Dataset.model_validate_json((SOURCE/'evaluation/research/data'/name).read_text())
 assert len(dataset.cases)==10 and {c.id for c in dataset.cases}==set(PLAN['cases'])
 results[name]={'dataset_sha256':PINS['files']['evaluation/research/data/'+name],'known_labels':sum(l.status=='known' for c in dataset.cases for l in c.labels),'human_verified_cases':sum(c.review.status=='human_verified' for c in dataset.cases),'metrics':score(dataset,merged,allow_drafts=False),'label_outcomes':label_outcomes(dataset,merged)}
output={'status':'DEV_BASELINE_SCORED_EXISTING_STRICT_SCORER','source_head':PLAN['source_head'],'attempted_cases':PLAN['cases'],'capture_kinds':receipt['capture_kinds'],'partial_cases':receipt.get('partial_cases',[]),'all_missing_unknown_retained_in_dataset_denominator':True,'network_model_process_calls':0,'originals':origins,'results':results,'limits':['single native-OFF baseline; no paired gain','existing ground-truth scope/year limitations remain','claim precision interpreted with adjudication/support coverage','not accepted blindexpert40/62/heldout/production/default/launch']}
target=OWN/'offline-score.json';assert not target.exists();target.write_text(json.dumps(output,indent=2,default=str)+'\\n')
print(json.dumps({'status':output['status'],'partial_cases':output['partial_cases'],'datasets':{k:{'known_labels':v['known_labels'],'human_verified_cases':v['human_verified_cases'],'metrics':v['metrics'].get('rates',v['metrics'].get('metrics'))} for k,v in results.items()}},indent=2,default=str))
'''
(P/'score-pins.json').write_text(json.dumps({'status':'PINNED_BEFORE_CAPTURE_AND_SCORING','files':files},indent=2)+'\n');(P/'score_after_collection.py').write_text(script)
print('offline scoring script prepared, not executed; no dataset values read for preparation')
