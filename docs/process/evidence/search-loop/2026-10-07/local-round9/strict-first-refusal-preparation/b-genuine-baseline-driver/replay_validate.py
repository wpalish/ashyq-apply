"""Synthetic protocol validation controls only; never invoke driver main."""
import argparse, copy, hashlib, importlib.util, json, socket, subprocess
from pathlib import Path
B=Path(__file__).resolve().parent
P=json.loads((B/'REVIEW_PLAN.json').read_text())
for name,want in P['inputs'].items(): assert hashlib.sha256((B/name).read_bytes()).hexdigest()==want

def deny(*a,**kw): raise AssertionError('No external/process/network calls in validator replay')
socket.getaddrinfo=deny;socket.create_connection=deny;socket.socket.connect=deny
subprocess.Popen=deny;subprocess.run=deny
parser=argparse.ArgumentParser()
parser.add_argument('--controller',type=Path,default=B/'execute_baseline.py')
parser.add_argument('--controller-sha256')
parser.add_argument('--out',type=Path,default=B/'validator-controls.offline.json')
args=parser.parse_args()
actual_sha=hashlib.sha256(args.controller.read_bytes()).hexdigest()
assert actual_sha==(args.controller_sha256 or P['inputs']['execute_baseline.py'])
spec=importlib.util.spec_from_file_location('reviewed_driver',args.controller)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
case='groningen'
obs={'case_id':case,'error':None,'telemetry':{'http_fetches':2,'search_calls':1,'browser_fetches':0,'model_input_tokens':0,'jev_input_tokens':0}}
budget={'strict_expert_budget':True,'provider':'exa_mcp','fetcher_calls':2,'search_queries':1,'elapsed_ms':1000,'max_fetcher_calls':60,'max_search_queries':6,'max_active_seconds':120,'finalization_reserve_ms':1000,'stop_reason':None,'provider_failure':None,'protocol_persistence_error':None}
raw={'canary':{'run_error':None,'institutions':[{'domain':'www.rug.nl','programs':[]}],'job_protocol':{'kind':'genuine-research-job','started':True,'job_id':'job-1','run_id':'run-1','worker_id':'worker-1','claim_token':1,'lease_token':1,'native_enabled':False,'native_ledger':None,'observation_available':True,'heartbeat_tasks':1,'heartbeat_done':[True],'job_status':'succeeded'}},'claims':[]}
cap={'mode':'live','pipeline_sha':'f0c8fece0b59de3e964d20a1a4daf131e92c4ef8','config':{'cohort':[case],'search_provider':'exa_mcp','fenced_research_job':True,'university_read_budget':False,'research_job_protocol':'genuine-research-job','strict_expert_budget':True,'seconds_per_case':120,'max_fetcher_calls_per_case':60,'shared_query_budget':True,'browser_enabled':False,'case_budgets':{case:copy.deepcopy(budget)}},'observations':[copy.deepcopy(obs)]}
base=[cap,obs,budget,raw]
rows=[]
def check(label,mutate,expected='reject'):
 x=copy.deepcopy(base); mutate(x)
 # Keep exact observations equality when testing a different contract.
 if isinstance(x[0],dict):x[0]['observations']=[copy.deepcopy(x[1])]
 try:errors=m.validate(case,*x); outcome='accepted' if not errors else 'rejected';ex=None
 except Exception as e:errors=None;outcome='uncaught';ex=type(e).__name__
 rows.append({'label':label,'expected':expected,'actual':outcome,'errors':errors,'exception':ex})
check('well_shaped_synthetic_control',lambda x:None,'accept')
check('fractional_fetcher_counter',lambda x:(x[2].update(fetcher_calls=2.5),x[1]['telemetry'].update(http_fetches=2.5)))
check('fractional_search_counter',lambda x:(x[2].update(search_queries=1.5),x[1]['telemetry'].update(search_calls=1.5)))
check('bool_claim_tokens',lambda x:x[3]['canary']['job_protocol'].update(claim_token=True,lease_token=True))
check('false_strict_config_and_changed_caps',lambda x:x[0]['config'].update(strict_expert_budget=False,seconds_per_case=240,max_fetcher_calls_per_case=600,shared_query_budget=False))
check('physical_capture_budget_mismatch',lambda x:x[0]['config']['case_budgets'][case].update(fetcher_calls=44))
check('raw_terminal_error_mismatch',lambda x:x[3]['canary'].update(run_error='RuntimeError: BENCHMARK_PAGE_BUDGET_EXHAUSTED'))
check('raw_missing_institutions_and_claims',lambda x:(x[3]['canary'].pop('institutions'),x[3].pop('claims')))
check('explicit_429_reason_missing_failure',lambda x:x[2].update(stop_reason='http_429'))
check('missing_provider_failure_proof',lambda x:x[2].pop('provider_failure'))
check('malformed_top_raw_array',lambda x:x.__setitem__(3,[]))
check('malformed_raw_canary_array',lambda x:x[3].update(canary=['invalid']))
check('malformed_telemetry_array',lambda x:x[1].update(telemetry=[]))
args.out.write_text(json.dumps({'synthetic_not_actual_capture':True,'no_main_or_network':True,'controller_sha256':actual_sha,'rows':rows},indent=2)+'\n')
print(json.dumps(rows,indent=2))
