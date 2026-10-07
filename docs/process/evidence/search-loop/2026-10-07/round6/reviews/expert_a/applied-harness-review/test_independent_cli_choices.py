"""Independent real batch/child CLI controls; all external work is denied or mocked."""
import ast
import json
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import config
from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.search import intent
from app.catalogue import discovery as catalogue_discovery
from evaluation.research import live
from evaluation.research.schema import Capture, Observation

ROOT=Path(__file__).resolve().parent
CASES=['offline-review-a','offline-review-b']
ON='--programme-identity-before-funding'
OFF='--no-programme-identity-before-funding'
CHOICES=[([],False,False),([],True,True),([ON],False,True),([OFF],True,False),([ON,OFF],True,False),([OFF,ON],False,True),([ON,OFF,ON],False,True)]


def denied(*args,**kwargs):
    raise AssertionError('No network/provider/Git/real subprocess allowed in harness review')


@pytest.fixture(autouse=True)
def isolation(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr('app.adapters.search.get_search_provider',denied)
    monkeypatch.setattr(subprocess,'run',denied)
    monkeypatch.setattr(subprocess,'check_output',denied)
    monkeypatch.setattr(page_classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING',False)
    monkeypatch.setattr(live_discovery,'SUBJECT_PHRASE_MATCH',False)
    monkeypatch.setattr(intent,'SHARED_QUERY_BUDGET',True)
    monkeypatch.setattr(catalogue_discovery,'SITE_BRANDING_IDENTITY',False)
    monkeypatch.setattr(config,'Settings',lambda **kw:SimpleNamespace(search_provider=kw.get('search_provider','exa_mcp'),_validate_search=lambda:None))
    monkeypatch.setattr(config,'get_settings',SimpleNamespace(cache_clear=lambda:None))
    monkeypatch.setattr('evaluation.research.expert.catalogue.load_catalogue',lambda:SimpleNamespace(identities=[SimpleNamespace(id=x,domain='offline.example.edu') for x in CASES]))


def record(tmp_path,data):
    raw=ROOT/'raw-controls';raw.mkdir(exist_ok=True)
    (raw/(tmp_path.name+'.json')).write_text(json.dumps(data,indent=2)+'\n')


def run_batch(tmp_path,monkeypatch,arguments,*,initial=False,subject=False,branding=False,stop_before=False,stop_after_first=False,budget_stop=None):
    monkeypatch.setattr(page_classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING',initial)
    stop=tmp_path/'synthetic-STOP.json'
    if stop_before:stop.write_text('{"reason":"synthetic refusal before start"}')
    out=tmp_path/'capture'
    argv=['review','--live','--catalogue-id',CASES[0],'--catalogue-id',CASES[1],'--out',str(out),'--strict-expert-budget','--stop-file',str(stop),*arguments]
    argv.extend(['--subject-phrase-match' if subject else '--no-subject-phrase-match'])
    if branding:argv.append('--site-branding-identity')
    monkeypatch.setattr(sys,'argv',argv)
    def fake_sha(command,**kwargs):
        assert command==['git','rev-parse','HEAD']
        return 'f'*40
    monkeypatch.setattr(subprocess,'check_output',fake_sha)
    child_effective=[];commands=[]
    async def fake_capture(case_id,output,max_pages,seconds,**kwargs):
        child_effective.append({'case_id':case_id,'programme':page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING,'subject':live_discovery.SUBJECT_PHRASE_MATCH,'branding':catalogue_discovery.SITE_BRANDING_IDENTITY,'shared':intent.SHARED_QUERY_BUDGET,'max_pages':max_pages,'seconds':seconds,'strict':kwargs.get('strict_expert_budget')})
        output.write_text(Observation(case_id=case_id).model_dump_json())
        if budget_stop!='missing':
            budget={'stop_reason':budget_stop or 'completed'}
            if budget_stop=='provider_failure':budget['provider_failure']={'status':401,'reason':'synthetic refusal'}
            output.with_suffix('.budget.json').write_text(json.dumps(budget))
    monkeypatch.setattr(live,'capture_one',fake_capture)
    def child_process(command,**kwargs):
        assert command[:3]==[sys.executable,'-m','evaluation.research.live']
        assert command.count(ON)+command.count(OFF)==1
        assert kwargs['env']['UNIMATCH_ENABLE_BROWSER_TIER']=='false'
        assert kwargs['env']['UNIMATCH_RESPECT_ROBOTS']=='true'
        assert kwargs['timeout']==135
        commands.append(command[3:])
        saved=[page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING,live_discovery.SUBJECT_PHRASE_MATCH,catalogue_discovery.SITE_BRANDING_IDENTITY,intent.SHARED_QUERY_BUDGET]
        old=sys.argv
        try:
            # Simulate isolated child starting with hostile opposite choices. Explicit
            # forwarded args, not inherited in-memory state, must select the result.
            page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=OFF in command
            live_discovery.SUBJECT_PHRASE_MATCH=not subject
            catalogue_discovery.SITE_BRANDING_IDENTITY=False
            sys.argv=['mock-child',*command[3:]]
            live.main()
        finally:
            sys.argv=old
            page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING,live_discovery.SUBJECT_PHRASE_MATCH,catalogue_discovery.SITE_BRANDING_IDENTITY,intent.SHARED_QUERY_BUDGET=saved
        if stop_after_first and len(commands)==1:stop.write_text('{"reason":"synthetic refusal between cases"}')
        return subprocess.CompletedProcess(command,0)
    monkeypatch.setattr(subprocess,'run',child_process)
    live.main()
    capture=Capture.model_validate_json(next(out.rglob('capture.json')).read_text())
    data={'arguments':arguments,'initial_programme':initial,'subject':subject,'branding':branding,'stop_before':stop_before,'stop_after_first':stop_after_first,'budget_stop':budget_stop,'commands':commands,'child_effective':child_effective,'capture':capture.model_dump(mode='json'),'settings_is_mock':True,'pipeline_sha_is_mock':True,'capture_one_is_mock':True,'real_network_provider_model_git_subprocess_calls':0}
    record(tmp_path,data)
    return capture,commands,child_effective


@pytest.mark.parametrize('arguments,initial,expected',CHOICES)
def test_real_batch_parser_resolves_omission_and_last_choice(tmp_path,monkeypatch,arguments,initial,expected):
    capture,commands,seen=run_batch(tmp_path,monkeypatch,arguments,initial=initial)
    assert len(commands)==len(seen)==len(capture.observations)==2
    assert capture.config['programme_identity_before_funding'] is expected
    assert capture.config['shared_query_budget'] is True
    assert all(c['programme'] is expected and c['max_pages']==60 and c['seconds']==120 and c['strict'] is True for c in seen)
    assert all((ON in command) is expected and (OFF in command) is not expected for command in commands)
    assert capture.config['batch_remaining_case_ids']==[]


@pytest.mark.parametrize('arguments,initial,expected',CHOICES)
def test_direct_real_child_parser_resolves_omission_and_last_choice(tmp_path,monkeypatch,arguments,initial,expected):
    monkeypatch.setattr(page_classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING',initial)
    monkeypatch.setattr(sys,'argv',['review','--live','--child','--catalogue-id',CASES[0],'--out',str(tmp_path/'child.json'),'--strict-expert-budget',*arguments])
    seen=[]
    async def capture(*args,**kwargs):seen.append(page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING)
    monkeypatch.setattr(live,'capture_one',capture)
    live.main()
    assert seen==[expected]
    record(tmp_path,{'arguments':arguments,'initial_programme':initial,'effective_programme':seen,'direct_child':True,'capture_one_is_mock':True,'real_network_provider_model_git_subprocess_calls':0})


@pytest.mark.parametrize('programme',[False,True])
@pytest.mark.parametrize('subject',[False,True])
def test_pf_choice_stays_independent_of_sph_and_fixed_experimental_si(tmp_path,monkeypatch,programme,subject):
    capture,commands,seen=run_batch(tmp_path,monkeypatch,[ON if programme else OFF],initial=not programme,subject=subject,branding=True)
    assert capture.config['programme_identity_before_funding'] is programme
    assert capture.config['subject_phrase_match'] is subject
    assert capture.config['site_branding_identity'] is True
    assert all(x['programme'] is programme and x['subject'] is subject and x['branding'] is True for x in seen)


@pytest.mark.parametrize('arguments,initial,expected',CHOICES[:4])
def test_prestart_synthetic_refusal_keeps_mode_without_child(tmp_path,monkeypatch,arguments,initial,expected):
    capture,commands,seen=run_batch(tmp_path,monkeypatch,arguments,initial=initial,stop_before=True)
    assert commands==seen==capture.observations==[]
    assert capture.config['programme_identity_before_funding'] is expected
    assert capture.config['batch_attempted_case_ids']==[]
    assert capture.config['batch_remaining_case_ids']==CASES
    assert capture.config['batch_stop_reason']=='external_provider_failure'


@pytest.mark.parametrize('programme',[False,True])
def test_sentinel_between_cases_retains_first_observation_and_choice(tmp_path,monkeypatch,programme):
    capture,commands,seen=run_batch(tmp_path,monkeypatch,[ON if programme else OFF],stop_after_first=True)
    assert len(commands)==len(seen)==len(capture.observations)==1
    assert capture.observations[0].case_id==CASES[0]
    assert capture.config['programme_identity_before_funding'] is programme
    assert capture.config['batch_attempted_case_ids']==CASES[:1]
    assert capture.config['batch_remaining_case_ids']==CASES[1:]
    assert capture.config['batch_stop_reason']=='external_provider_failure'


@pytest.mark.parametrize('programme',[False,True])
@pytest.mark.parametrize('budget_stop,expected_reason',[('http_429','http_429'),('provider_failure','provider_failure'),('missing','capture_unavailable')])
def test_child_budget_failure_stops_batch_with_mode_and_partial_output(tmp_path,monkeypatch,programme,budget_stop,expected_reason):
    capture,commands,seen=run_batch(tmp_path,monkeypatch,[ON if programme else OFF],budget_stop=budget_stop)
    assert len(commands)==len(seen)==len(capture.observations)==1
    assert capture.config['programme_identity_before_funding'] is programme
    assert capture.config['batch_attempted_case_ids']==CASES[:1]
    assert capture.config['batch_remaining_case_ids']==CASES[1:]
    assert capture.config['batch_stop_reason']==expected_reason


def test_actual_source_defaults_remain_off():
    # Read literal source declarations, rather than the fixture's forced runtime values.
    for module,name in [(page_classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING'),(live_discovery,'SUBJECT_PHRASE_MATCH'),(catalogue_discovery,'SITE_BRANDING_IDENTITY')]:
        assignments=[node for node in ast.parse(Path(module.__file__).read_text()).body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==name for target in node.targets)]
        assert len(assignments)==1
        assert isinstance(assignments[0].value,ast.Constant) and assignments[0].value.value is False
