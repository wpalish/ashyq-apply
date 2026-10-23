from pathlib import Path
import shutil
O=Path(__file__).resolve().parent;B=O/'runtime/backend';h=O/'history/static-rewrite-failed';h.mkdir(exist_ok=True)
for p in (O/'proposed/backend').rglob('*.py'):
 q=B/p.relative_to(O/'proposed/backend');r=h/p.relative_to(O/'proposed/backend');r.parent.mkdir(parents=True,exist_ok=True);r.write_bytes(q.read_bytes())
p=B/'tests/test_local_pilot.py';s=p.read_text();middle=s[s.index('def fake_process'):s.index('def test_prepare_real_shaped')]
prefix='''"""Offline route controls; injected transports are ineligible runtime proof."""
from __future__ import annotations
import asyncio
import copy
import json
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import pytest
from evaluation.research import local_pilot as p
from evaluation.research.expert import controller as c, selector as s
from evaluation.research.expert.journal import AcceptedJournal
from evaluation.research.identities import IdentityMap
from evaluation.research.pilot_admission import validate_algorithm

@pytest.fixture(autouse=True)
def denied_network(monkeypatch):
    def denied(*_args,**_kwargs):raise AssertionError('Real network/DNS forbidden')
    monkeypatch.setattr(socket.socket,'connect',denied);monkeypatch.setattr(socket,'getaddrinfo',denied)

def public_input():
    domains=('rug.nl','tudelft.nl','aalto.fi','univie.ac.at','uw.edu.pl','ubc.ca','utoronto.ca','hku.hk','ntu.edu.sg','kaist.ac.kr')
    cases=[]
    for key,domain in zip(p.COHORT,domains,strict=True):
        university='Synthetic '+key.title()+' University'
        cases.append({'case_id':key,'university':university,'domain':domain,'request':{'university':university,'programme':None,'degree':'bachelor','field':'computer science','intake':'fall 2027','population':'international','qualification':'KZ national secondary','academic_year':None}})
    return {'schema_version':'1','public_profile':{'education_system':'KZ national secondary'},'cases':cases}

def setup(tmp_path):
    research=Path(c.__file__).resolve().parents[1];backend=research.parents[1];source=backend.parent
    old=tmp_path/'old-stop.json';old.write_text('{"original":"refused"}')
    public=public_input();public_path=tmp_path/'public.json';p.store(public_path,public)
    manifest={'files':{f'backend/evaluation/research/{name}.py':p.sha(research/f'{name}.py') for name in ('live','mapping')}}
    manifest_path=tmp_path/'manifest.json';p.store(manifest_path,manifest)
    value={'provider':'exa_mcp','cases':list(p.COHORT),'source_snapshot':str(source),'source_head':'synthetic-source','source_tree_sha256':'a'*64,'source_manifest':str(manifest_path),'public_input':str(public_path),'cycle_id':'synthetic-fresh','pins':[{'path':str(public_path),'sha256':p.sha(public_path)},{'path':str(manifest_path),'sha256':p.sha(manifest_path)}],'retained_stop':{'path':str(old),'sha256':p.sha(old)},'executables':{'python':'/mock/python','codex':'/mock/codex','sandbox':'/mock/sandbox'},'selector_model':'explicit-test-model','sealed_roots':[str(tmp_path)],'profile_contract':{'qualification':'synthetic source/argv only'}}
    root=tmp_path/'cycle';root.mkdir();pp=root/'PLAN.json';p.store(pp,value)
    grant={'schema_version':'1','approved_by':'human-owner','plan_sha256':p.sha(pp),'cycle_id':value['cycle_id'],'source_tree_sha256':value['source_tree_sha256'],'retained_stop_sha256':p.sha(old),'provider':'exa_mcp','cases':list(p.COHORT),'two_independent_experts':True,'selector_model':value['selector_model'],'expert_timing_policy':'expert_wall_only','protective_wall_ms':900000,'authorization_id':'synthetic-untrusted-test-only'}
    gp=tmp_path/'grant.json';p.store(gp,grant);return p.Gate(root,value),public,pp,gp

def plan(**changes):
    value={'case_id':'synthetic','provider':'exa_mcp','log_prefix':'synthetic','strict_budget':True,'max_calls':60,'max_search_queries':6,'max_ms':None,'timing_policy':'expert_wall_only','protective_wall_ms':900000,'wall_elapsed_before_ms':0,'official_domains':['example.edu'],'budget_origin':'independent_full_budget','actions':[{'tool':'fetcher','url':'https://example.edu/admissions'}]};value.update(changes);return value
async def get(url):return SimpleNamespace(url=url,final_url=url,ok=True,outcome='ok',status_code=200,content_type='text/plain',content=b'Synthetic admissions source information',error='',from_cache=False,fetch_tier='http',fetched_at=datetime.now(UTC))
async def search(**_kwargs):return SimpleNamespace(results=[])
def run_tool(value,folder,**kwargs):return asyncio.run(c.execute(value,folder,get=get,search=search,provider_name='exa_mcp',**kwargs))
def legacy_plan():
    value=plan(max_ms=120000)
    for key in ('timing_policy','protective_wall_ms','wall_elapsed_before_ms'):value.pop(key)
    return value

def capture_fixture(case,source_plan,manifest):
    basis='capture_one entry; includes canary setup and all pipeline stages, cancellation cleanup, output/raw persistence and final checkpoint work; final metering-envelope persistence is audit only'
    budget={'fetcher_calls':0,'search_queries':0,'elapsed_ms':100,'blocked_search_queries':0,'network_http_requests':0,'max_fetcher_calls':60,'max_search_queries':6,'max_active_seconds':120,'finalization_reserve_ms':1000,'source_work_deadline_ms':119000,'strict_expert_budget':True,'provider':'exa_mcp','active_time_basis':basis,'provider_failure':None,'protocol_persistence_error':None,'stop_reason':None}
    observed={'case_id':case['case_id'],'programme_urls':[],'ranked_urls':None,'predictions':[],'telemetry':{'http_fetches':0,'search_calls':0,'browser_fetches':0,'model_input_tokens':0,'jev_input_tokens':0,'latency_seconds':.1},'page_outcomes':[],'error':None}
    protocol={'kind':'genuine-research-job','started':True,'job_id':'synthetic-job','run_id':'synthetic-run','worker_id':'synthetic-worker','sqlite_case_database':'synthetic.db','claim_token':1,'lease_token':1,'native_enabled':False,'native_ledger':None,'observation_available':True,'heartbeat_tasks':1,'heartbeat_done':[True],'heartbeat_cancelled':[True],'job_status':'succeeded','worker_jobs_done':1,'worker_jobs_failed':0,'recorded_worker_id':None,'claim_records':[],'page_outcomes':[],'run_unknowns':[],'run_errors':[],'control_error':None,'control_type':None,'control_reason':None,'control_message':None}
    raw={'canary':{'institutions':[{'institution':case['university'],'domain':case['domain'],'programs':[]}],'totals':{},'batch':[case['university']],'job_protocol':protocol,'run_error':''},'claims':[],'protocol_observation_available':True}
    config={'harness_sha256':manifest['files']['backend/evaluation/research/live.py'],'mapping_sha256':manifest['files']['backend/evaluation/research/mapping.py'],'cohort':[case['case_id']],'search_provider':'exa_mcp','fenced_research_job':True,'university_read_budget':False,'research_job_protocol':'genuine-research-job','strict_expert_budget':True,'shared_query_budget':True,'browser_enabled':False,'cold_fetcher_reads':True,'site_branding_identity':False,'subject_phrase_match':False,'programme_identity_before_funding':False,'seconds_per_case':120,'child_active_seconds':120,'max_fetcher_calls_per_case':60,'max_search_queries_per_case':6,'finalization_reserve_ms':1000,'source_work_deadline_ms':119000,'parent_process_reserve_seconds':15,'parent_process_timeout_seconds':135,'page_budget_counts':'every Fetcher.get invocation; cache hits consume a call','batch_attempted_case_ids':[case['case_id']],'batch_completed_case_ids':[case['case_id']],'batch_remaining_case_ids':[],'batch_stop_reason':None,'active_time_basis':basis,'case_budgets':{case['case_id']:{**budget,'parent_process_elapsed_seconds':.2,'process_error':None,'active_checkpoint_available':True}}}
    capture={'schema_version':'1','pipeline_sha':source_plan['source_head'],'captured_at':datetime.now(UTC).isoformat(),'mode':'live','config':config,'observations':[observed]};return capture,observed,budget,raw

'''
last='''
def test_prepare_real_shaped_homepage_and_opaque_bindings(tmp_path,monkeypatch):
    import sys
    gate,public,_pp,_gp=setup(tmp_path)
    source=tmp_path/'prepared-source';backend=source/'backend';scripts=backend/'scripts';scripts.mkdir(parents=True)
    current_backend=Path(p.__file__).resolve().parents[2]
    (scripts/'canary_discovery.py').write_bytes((current_backend/'scripts/canary_discovery.py').read_bytes())
    bindings=backend/'evaluation/research/data/identity_bindings.reviewed.json';bindings.parent.mkdir(parents=True);bindings.write_bytes((current_backend/'evaluation/research/data/identity_bindings.reviewed.json').read_bytes())
    marker=backend/'evaluation/research/expert/controller.py';marker.parent.mkdir();marker.write_bytes(Path(c.__file__).read_bytes());monkeypatch.setattr(c,'__file__',str(marker))
    registry=backend/'app/adapters/discovery/institution_registry.json';registry.parent.mkdir(parents=True);registry.write_text(json.dumps([{'name':row['university'],'homepage':'https://www.'+row['domain']+'/'} for row in public['cases']]))
    binaries=tmp_path/'binaries';binaries.mkdir()
    for name in ('codex','sandbox-exec'):(binaries/name).write_text('synthetic binary, never executed')
    monkeypatch.setattr(p.shutil,'which',lambda name:str(binaries/name))
    venv=backend/'.venv/bin';venv.mkdir(parents=True);executable=venv/'python';executable.symlink_to(Path(sys.executable))
    manifest={'snapshot':str(source),'repository':str(source),'source_status':'','source_head':'synthetic','source_tree_sha256':'b'*64,'files':{str(file.relative_to(source)):p.sha(file) for file in [registry,scripts/'canary_discovery.py',bindings]}}
    mp=tmp_path/'prepare-manifest.json';p.store(mp,manifest)
    full=tmp_path/'synthetic-full.json';p.store(full,{'status':'passed','suite':'full','steps':[{'exit_code':0} for _ in range(13)],'source':{'source_tree_sha256':'b'*64}})
    pp=p.prepare(mp,Path(gate.plan['public_input']),Path(gate.plan['retained_stop']['path']),tmp_path/'prepared',selector_model='test-model',sealed_roots=[tmp_path,source],full_receipt=full)
    prepared=p.read(pp)
    assert len(prepared['registry_contract']['resolved'])==10 and prepared['status']=='PREPARED_NOT_EXECUTED'
    assert prepared['profile_contract']['context']['intake_year']==2027
    assert str(Path.home()/'Documents/Codex') in prepared['sealed_roots'] and str(Path.home()/'.codex/sessions') in prepared['sealed_roots']
    assert not (pp.parent/'EXECUTION-START.original.json').exists()
    target=tmp_path/'other-python';target.write_text('never executed');executable.unlink();executable.symlink_to(target)
    with pytest.raises(ValueError,match='executable'):p.verify_binding(prepared)


def test_complete_citation_chain_and_mutation_closure(tmp_path):
    from evaluation.research.expert.models import Action, ExpertTrace, _controller_budget, validate_trace
    gate,public,_pp,_gp=setup(tmp_path)
    def evidence(isolation,schema,output,prompt,**kwargs):
        turn=adaptive_select(isolation,schema,output,prompt,**kwargs)
        if prompt.get('source_views'):
            value=copy.deepcopy(turn.answer);scope={key:None for key in p.REQUEST_FIELDS};scope['university']=public['cases'][0]['university']
            value['facts']=[{'id':'fact1','question':'OTHER','claim_key':'unmapped.admissions_info','value_json':'"Synthetic admissions source information"','source_step':1,'quotation':'Synthetic admissions source information','location':{'kind':'text','block_id':None,'section_path':[],'page':None},'scope':scope}]
            output.write_text(json.dumps(value));return s.SelectorTurn(value,1,streams(value),'',0,None)
        return turn
    receipt=asyncio.run(p.collect_expert(gate,public,public['cases'][0],'A',isolate=FakeIsolation,select=evidence,run_tool=native_tool))
    assert receipt['trace']['proposals'] and receipt['complete_eligible'] is False
    p.verify_admitted_outputs(gate.root,[],[receipt])
    legacy=copy.deepcopy(receipt['trace']);legacy['max_elapsed_ms']=120000;legacy.pop('timing_policy');legacy.pop('protective_wall_ms')
    native_legacy=ExpertTrace.model_validate(legacy).model_dump(mode='json')
    assert 'timing_policy' not in native_legacy and 'protective_wall_ms' not in native_legacy
    root=gate.root/'private/experts/A/groningen';earlier=root/'selector-0001.original.json';original=earlier.read_bytes();earlier.write_text('{}')
    with pytest.raises(ValueError,match='selector original changed'):p.verify_admitted_outputs(gate.root,[],[receipt])
    earlier.write_bytes(original);raw=next((root/'raw').glob('*.json'));before=raw.read_bytes();raw.write_text('{}')
    with pytest.raises(ValueError,match='expert raw changed'):p.verify_admitted_outputs(gate.root,[],[receipt])
    raw.write_bytes(before);p.verify_admitted_outputs(gate.root,[],[receipt])
    summary=p.read(root/'tool-0001.summary.json')
    second_summary=run_tool(plan(case_id='groningen',log_prefix='groningen',official_domains=['rug.nl'],wall_elapsed_before_ms=max(100,summary['final']['wall_elapsed_ms']),resume_summary=summary,actions=[{'tool':'fetcher','url':'https://rug.nl/admissions'}]),root/'raw');row=second_summary['actions'][0]
    second=copy.deepcopy(receipt['trace']['actions'][0]);second.update(step=2,at=row['at'],observed_before='Read the source again.',observed_from_step=1,action='Read the source again.',raw_log_path=row['raw_log_path'],raw_log_sha256=row['raw_log_sha256'],request=row['request'],final_url=row['final_url'],elapsed_ms=row['elapsed_ms'],elapsed_ms_cumulative=row['elapsed_ms_cumulative'],fetcher_calls_cumulative=row['fetcher_calls_cumulative'],search_queries_cumulative=row['search_queries_cumulative'])
    full_trace=copy.deepcopy(receipt['trace']);full_trace['actions'].append(second);full_trace['ended_at']=datetime.now(UTC).isoformat();packet=p.read(root/'packet.original.json')
    validate_trace(full_trace,packet,logs_dir=root/'raw')
    raw_second=root/'raw'/row['raw_log_path'];value=p.read(raw_second);value['wall_elapsed_ms_before']=0;raw_second.write_text(json.dumps(value));full_trace['actions'][1]['raw_log_sha256']=p.sha(raw_second)
    with pytest.raises(ValueError,match='between actions'):validate_trace(full_trace,packet,logs_dir=root/'raw')
    with pytest.raises(ValueError,match='structured'):_controller_budget(ExpertTrace.model_validate(legacy),Action.model_validate(legacy['actions'][0]),{'tool_policy':['malformed']},'independent_full_budget')
    second_case=public['cases'][1]
    def bad(isolation,schema,output,prompt,**kwargs):
        turn=evidence(isolation,schema,output,prompt,**kwargs)
        if prompt.get('source_views'):
            value=copy.deepcopy(turn.answer);value['facts'][0]['scope']['university']=second_case['university'];value['facts'][0]['quotation']='Not in saved source';output.write_text(json.dumps(value));return s.SelectorTurn(value,1,streams(value),'',0,None)
        return turn
    with pytest.raises(ValueError):asyncio.run(p.collect_expert(gate,public,second_case,'B',isolate=FakeIsolation,select=bad,run_tool=native_tool))
    failed=p.read(gate.root/'private/experts/B/delft/receipt.json');assert failed['complete_eligible'] is False and failed['last_accepted_journal']['facts']==[]
'''
p.write_text(prefix+middle+last)
p=B/'evaluation/research/expert/controller.py';s=p.read_text().replace('            raise ValueError("Resume summary wall policy incomplete or contradictory")','                raise ValueError("Resume summary wall policy incomplete or contradictory")',1);p.write_text(s)
for p in (O/'proposed/backend').rglob('*.py'):
 q=B/p.relative_to(O/'proposed/backend');p.write_bytes(q.read_bytes())
print('same finite fixture semantics restored; syntax history preserved')
