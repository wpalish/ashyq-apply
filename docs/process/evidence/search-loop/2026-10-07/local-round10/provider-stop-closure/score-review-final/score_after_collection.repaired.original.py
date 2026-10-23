"""Offline score only after ten validated bounded terminal capture records."""
from pathlib import Path
import hashlib,importlib.util,json,socket,subprocess,sys
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
from evaluation.research.scorecard import CORE_QUESTIONS, cost, core_coverage, label_outcomes
assert not Path(PLAN['stop_file']).exists(), 'Global provider STOP: incomplete/no score'
assert hashlib.sha256((OWN/'execute_baseline.py').read_bytes()).hexdigest()==PLAN['driver_sha256']=='4fa670fb54d6f62c296b68e682c2f46417cf02ba0daf75deb69f329be32f269b'
spec=importlib.util.spec_from_file_location('accepted_capture_validator',OWN/'execute_baseline.py')
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
receipt=json.loads((OWN/'execution-receipt.json').read_text())
assert receipt['status']=='TERMINAL_ORIGINAL10_CAPTURE_COMPLETE_AWAIT_OFFLINE_SCORING'
assert receipt['attempted']==PLAN['cases'] and receipt['remaining']==[]
assert set(receipt['capture_kinds'])==set(PLAN['cases']) and not receipt['validation_errors']
observations=[];origins=[];parts=[]
for case in PLAN['cases']:
 paths=list((OWN/case).glob('*/capture.json'));assert len(paths)==1
 path=paths[0];physical={'capture':path,'observation':path.with_name(case+'.json'),'budget':path.with_name(case+'.budget.json'),'raw':path.with_name(case+'.raw.json')}
 hashes={name:{'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for name,file in physical.items()}
 loaded={name:json.loads(file.read_text()) for name,file in physical.items()}
 errors=validator.validate(case,loaded['capture'],loaded['observation'],loaded['budget'],loaded['raw'],require_complete_job=False)
 assert not errors,(case,errors)
 kind=validator.capture_kind(loaded['observation'],loaded['budget'],loaded['raw']);assert kind==receipt['capture_kinds'][case]
 part=Capture.model_validate(loaded['capture']);assert [o.case_id for o in part.observations]==[case]
 assert part.pipeline_sha==PLAN['source_head'];parts.append(part);observations+=part.observations
 origins.append({'case':case,'capture_kind':kind,'artifacts':hashes,'physical_budget':part.config['case_budgets'][case]})
merged=parts[0].model_copy(update={'observations':observations,'config':{'provenance':'offline aggregation only, original captures immutable','cohort':PLAN['cases'],'originals':origins,'source_sha256':PLAN['source_tree_sha256']}})
results={}
for name in ['ground_truth.reviewed.json','ground_truth.reviewed9.json']:
 dataset=Dataset.model_validate_json((SOURCE/'evaluation/research/data'/name).read_text())
 assert len(dataset.cases)==10 and {c.id for c in dataset.cases}==set(PLAN['cases'])
 metrics=score(dataset,merged,allow_drafts=False);outcomes=label_outcomes(dataset,merged)
 known_core=[row for row in outcomes['labels'] if any(pattern.match(row['key']) for _,pattern in CORE_QUESTIONS)]
 results[name]={'dataset_sha256':PINS['files']['evaluation/research/data/'+name],'known_labels':sum(l.status=='known' for c in dataset.cases for l in c.labels),'human_verified_cases':sum(c.review.status=='human_verified' for c in dataset.cases),'metrics':metrics,'label_outcomes':outcomes,'raw_answered_core_questions':core_coverage(merged),'known_core_label_hits':{'n':sum(row['outcome']=='hit' for row in known_core),'d':len(known_core),'note':'Correct matching known atomic core labels; raw answered questions are not verified correctness or paired DoD acceptance'},'cost':cost(merged)}
for origin in origins:
 for artifact in origin['artifacts'].values():assert hashlib.sha256(Path(artifact['path']).read_bytes()).hexdigest()==artifact['sha256'],'Original capture changed while scoring'
assert not Path(PLAN['stop_file']).exists(), 'Global provider STOP before score persistence' 
output={'status':'DEV_BASELINE_SCORED_EXISTING_STRICT_SCORER','source_head':PLAN['source_head'],'attempted_cases':PLAN['cases'],'capture_kinds':receipt['capture_kinds'],'partial_cases':receipt.get('partial_cases',[]),'all_missing_unknown_retained_in_dataset_denominator':True,'network_model_process_calls':0,'originals':origins,'results':results,'limits':['single native-OFF baseline; no paired gain','existing ground-truth scope/year limitations remain','claim precision interpreted with adjudication/support coverage','not accepted blindexpert40/62/heldout/production/default/launch']}
target=OWN/'offline-score.json';assert not target.exists();target.write_text(json.dumps(output,indent=2,default=str)+'\n')
print(json.dumps({'status':output['status'],'partial_cases':output['partial_cases'],'datasets':{k:{'known_labels':v['known_labels'],'human_verified_cases':v['human_verified_cases'],'metrics':v['metrics'].get('rates',v['metrics'].get('metrics'))} for k,v in results.items()}},indent=2,default=str))
