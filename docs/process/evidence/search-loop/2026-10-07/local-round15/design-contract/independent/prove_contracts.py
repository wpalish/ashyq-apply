from pathlib import Path
from types import SimpleNamespace
from datetime import UTC, datetime, timedelta
import asyncio
import copy
import hashlib
import json
import socket
import subprocess
import sys

OWN = Path(__file__).resolve().parent
ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend')
network = []
processes = []
def deny_net(*args, **kwargs):
    network.append('denied')
    raise AssertionError('Offline control attempted external network')
def deny_process(*args, **kwargs):
    processes.append('denied')
    raise AssertionError('No model/CLI/process may execute in this proof')
socket.create_connection = deny_net
socket.getaddrinfo = deny_net
socket.socket.connect = deny_net
socket.socket.connect_ex = deny_net
subprocess.run = deny_process
sys.path.insert(0, str(ROOT))
from evaluation.research.expert.controller import execute
from evaluation.research.expert.models import validate_trace, ExpertTrace
from evaluation.research.expert.packet import digest
from evaluation.research.expert.journal import AcceptedJournal
from evaluation.research.expert.blind_cli import Isolation, selector_answer
from evaluation.research.expert.selector import select

checks = []
def expect_rejected(name, call, fragment):
    try:
        call()
    except ValueError as e:
        checks.append({'case':name,'status':'PASS' if fragment in str(e) else 'RED','expected_rejection':fragment,'actual':str(e)})
    else:
        checks.append({'case':name,'status':'RED','actual':'unexpectedly accepted'})

started = datetime(2026,10,8,12,0,0,tzinfo=UTC)
reads = []
async def get(url):
    reads.append(url)
    return SimpleNamespace(outcome='ok', ok=True, content=b'<html><h1>Official example admissions</h1><p>Applications are accepted.</p></html>', status_code=200,final_url=url,url=url,content_type='text/html',from_cache=False,fetch_tier='http',error='',fetched_at=started)
plan={'case_id':'synthetic-contract','strict_budget':True,'max_calls':60,'max_ms':120000,'max_search_queries':6,'official_domains':['example.edu'],'budget_origin':'independent_full_budget','log_prefix':'contract','actions':[{'tool':'fetcher','url':'https://example.edu/requirements'}]}
async def native(p, logs):
    return await execute(p,logs,get=get,search=None,provider_name='exa_mcp',now=lambda:started,monotonic=lambda:1.0)
expect_rejected('legacy_strict900wall_not_supported_before_IO',lambda:asyncio.run(native(dict(plan,max_ms=900000),OWN/'runtime/rejected900')),'Strict run budget exceeds')
checks.append({'case':'legacy900rejection_dispatch0','status':'PASS' if not reads else 'RED','fetch_invocations':len(reads),'HTTP_dispatches':0})
logs = OWN/'runtime/legacy120'
summary = asyncio.run(native(plan,logs))
entry=summary['actions'][0]; raw=json.loads((logs/entry['raw_log_path']).read_text())
checks.append({'case':'native_legacy120_one_read_raw_hash_counter','status':'PASS' if len(reads)==1 and summary['final']['fetcher_calls']==1 and entry['raw_log_sha256']==hashlib.sha256((logs/entry['raw_log_path']).read_bytes()).hexdigest() else 'RED','actual_final':summary['final'],'strict_policy':summary['tool_policy'],'qualification':'Native controller injected synthetic source getter; zero real Fetcher HTTP. Source shape/accounting contract only.'})
packet={'baseline_pipeline_sha':'ab273163','baseline_budget':{'max_fetcher_calls':60,'max_elapsed_ms':120000,'max_search_queries':6,'browser_enabled':False},'comparison_mode':'independent_full_budget','cases':[{'case_id':'synthetic-contract','university':'Example University','domain':'example.edu','request':{}}]}
action={'step':1,'at':started.isoformat(),'observed_before':'Public synthetic packet only.','observed_from_step':None,'tool':'fetcher','action':'Read selected official example URL','outcome_status':entry['outcome_status'],'outcome':entry['outcome'],'stage':'page_understanding','policy_mode':entry['policy_mode'],'url':entry['request']['url'],'final_url':entry['final_url'],'request':entry['request'],'raw_log_path':entry['raw_log_path'],'raw_log_sha256':entry['raw_log_sha256'],'elapsed_ms':entry['elapsed_ms'],'fetcher_calls_cumulative':entry['fetcher_calls_cumulative'],'search_queries_cumulative':entry['search_queries_cumulative'],'elapsed_ms_cumulative':entry['elapsed_ms_cumulative']}
trace={'case_id':'synthetic-contract','packet_sha256':digest(packet),'baseline_pipeline_sha':packet['baseline_pipeline_sha'],'max_fetcher_calls':60,'max_elapsed_ms':120000,'max_search_queries':6,'initial_fetcher_calls':0,'initial_elapsed_ms':0,'initial_search_queries':0,'started_at':started.isoformat(),'ended_at':(started+timedelta(seconds=1)).isoformat(),'actions':[action],'proposals':[],'review_status':'unreviewed'}
parsed=validate_trace(trace,packet,logs_dir=logs)
checks.append({'case':'native_trace_exact120_packet_raw_contract_PASS','status':'PASS','actions':len(parsed.actions),'proposals':len(parsed.proposals),'qualification':'No facts/semantic or receipt admission claimed.'})
t900=dict(trace,max_elapsed_ms=900000)
expect_rejected('trace900_algorithm_packet120_rejected',lambda:validate_trace(t900,packet,logs_dir=logs),'Trace budget differs')
p900=copy.deepcopy(packet);p900['baseline_budget']['max_elapsed_ms']=900000;t900['packet_sha256']=digest(p900)
expect_rejected('validation_packet900_raw120_rejected',lambda:validate_trace(t900,p900,logs_dir=logs),'Controller budget differs')
expect_rejected('zero_actions_trace_cannot_be_complete',lambda:ExpertTrace.model_validate(dict(trace,actions=[])),'at least 1 item')
j=AcceptedJournal.initial(); old=j.sha256
expect_rejected('stale_journal_delta_cannot_accept',lambda:j.candidate({'kind':'submit','observation':'Synthetic only','journal_sha256':'0'*64,'action':None,'facts':[],'question_findings':[]},[action],ended_at=started+timedelta(seconds=1),case_id='synthetic-contract'),'prior journal SHA')
checks.append({'case':'rejected_delta_preserves_immutable_journal','status':'PASS' if j.sha256==old and not j.facts else 'RED','journal_sha256':j.sha256})
iso=Isolation(OWN/'runtime/selector',(OWN/'runtime/sealed',),'/unexecuted/sandbox','/unexecuted/codex')
expect_rejected('legacy_selector55ceiling_preserved_noCLI',lambda:select(iso,OWN/'runtime/selector/schema.json',OWN/'runtime/selector/output.json',{},timeout_seconds=899),'Selector timeout must')
expect_rejected('failed_model_stream_cannot_supply_completion',lambda:selector_answer('{"type":"turn.failed"}','{}'),'did not complete')
checks.append({'case':'denied_network_and_CLI_not_invoked','status':'PASS' if not network and not processes else 'RED','network_attempts':len(network),'CLI_process_attempts':len(processes)})
output={'status':'PASS_SOURCE_CONTRACT_BOUNDARIES_ONLY' if all(c['status']=='PASS' for c in checks) else 'RED_OFFLINE_CONTRACT_PROOF','cases':len(checks),'checks':checks,'legacy_source_unmodified':True,'no_new_route_or_accepted_runtime_receipt':True,'mock_qualification':'Native current controller/model/journal/selector functions on injected own synthetic getter and fixed clock; no real provider, Fetcher HTTP, model CLI, DB, scoring or production gain.'}
(OWN/'native-contract-proof.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({'status':output['status'],'cases':len(checks),'PASS':sum(c['status']=='PASS' for c in checks),'RED':[c for c in checks if c['status']!='PASS'],'network':len(network),'CLI':len(processes)},indent=2))
raise SystemExit(0 if all(c['status']=='PASS' for c in checks) else 1)
