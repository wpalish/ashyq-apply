"""Independent classifier/caller controls; no live or production source mutations."""
import asyncio
import hashlib
import json
import socket
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.adapters import page_classifier as classifier
from app.adapters.base import Candidate,CandidateProgram
from app.adapters.fetching import FetchResult,_content_hash
from app.adapters.requirements import web_requirements
from app.adapters.scholarship import web_scholarships
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import DegreeLevel,FetchOutcome

ROOT=Path(__file__).resolve().parent/'fixtures/programme_funding'
SNAPSHOTS=json.loads((ROOT/'scope-controls.json').read_text())
OFF={(x['url'],x['html']):x['off'] for x in SNAPSHOTS['controls']}
ORIGINAL=SNAPSHOTS['original_a_controls']
MARKER='subsidiary funding index on a programme page'
LINKS='<a href="/awards/one">Alpha Scholarship</a><a href="/awards/two">Beta Scholarship</a>'
ACADEMIC='<h2>Curriculum</h2><p>Students take first-year courses in programming and second-year modules in algorithms, followed by a project.</p>'


def page(body,title='BSc Computer Science'):
    return '<html><head><title>'+title+'</title></head><body><main><h1>'+title+'</h1>'+body+'</main></body></html>'


CONTROLS=[(x['name'],x['html'],x['url'],x['expected']) for x in SNAPSHOTS['controls']]

def denied(*args,**kwargs):
    raise AssertionError('Offline review forbids network/provider/model')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING',False,raising=False)
    monkeypatch.setattr('app.adapters.search.get_search_provider',denied)


@pytest.mark.parametrize('name,html,url,expected',CONTROLS,ids=[x[0] for x in CONTROLS])
def test_off_full_asdict_equals_immutable_legacy(name,html,url,expected):
    assert asdict(classifier.classify_page(url=url,html=html))==OFF[(url,html)]


@pytest.mark.parametrize('name,html,url,expected',CONTROLS,ids=[x[0] for x in CONTROLS])
def test_enabled_scope_and_marker(name,html,url,expected,monkeypatch):
    monkeypatch.setattr(classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING',True,raising=False)
    result=classifier.classify_page(url=url,html=html)
    old=OFF[(url,html)]
    assert result.page_type.value==expected
    marked=MARKER in result.signals
    assert marked is (old['page_type']=='scholarship_index' and expected in {'program_detail','intake_specific_program'})
    if not marked:
        assert asdict(result)==old
    assert classifier.ACCEPTS=={k:frozenset(v) for k,v in SNAPSHOTS['accepts'].items()}


@pytest.mark.parametrize('case',[ORIGINAL[9],ORIGINAL[11]],ids=[ORIGINAL[9]['case'],ORIGINAL[11]['case']])
def test_known_conservative_abstention_is_not_silently_expanded(case,monkeypatch):
    monkeypatch.setattr(classifier,'PROGRAMME_IDENTITY_BEFORE_FUNDING',True,raising=False)
    result=classifier.classify_page(url=case['url'],html=case['html'])
    assert result.page_type.value=='scholarship_index'
    assert MARKER not in result.signals


def retained_wits():
    raw=(ROOT/'wits-programme.html').read_bytes()
    mp=ROOT/'wits-programme.meta.json';meta=json.loads(mp.read_text())
    assert hashlib.sha256(raw).hexdigest()=='88d1f716c82840fa66317ff1ceb42a152439a924d7625c0d2ef18a0f315f0a87'
    assert hashlib.sha256(mp.read_bytes()).hexdigest()=='d54f742c251cd9cd36c06ee4b89a74a7c1ca701b829b5ffa99d6cc5701096b8c'
    html=raw.decode(meta.get('encoding','utf-8'),errors='replace')
    assert _content_hash(html)==meta['content_hash']
    return meta['url'],html,meta


async def funding_route(mode,enabled,url,html,meta,*,wits_html=None,extra_bodies=None,index_limit=None):
    classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
    index_url='https://www.wits.ac.za/offline-review/funding-index'
    index_html='<html><head><title>Scholarships</title></head><body><main><h1>Scholarships</h1><a href="'+url+'">Computer Science scholarships</a></main></body></html>'
    reads=[]
    bodies={url:wits_html if wits_html is not None else html}
    if mode=='linked_depth_one':bodies[index_url]=index_html
    bodies.update(extra_bodies or {})
    async def get(requested_url):
        reads.append(requested_url)
        body=bodies.get(requested_url)
        if body is None:return FetchResult(url=requested_url,outcome=FetchOutcome.HTTP_ERROR,final_url=requested_url,error='Offline: no retained body provided; unknown')
        return FetchResult(url=requested_url,outcome=FetchOutcome.CACHED,status_code=200,content=body.encode(),text=body,content_type='text/html',final_url=requested_url,from_cache=True,fetched_at=datetime.fromisoformat(meta['fetched_at']),content_hash=meta['content_hash'] if body==html else _content_hash(body))
    candidate=Candidate(name='University of the Witwatersrand',country='South Africa',city='Johannesburg',domain='wits.ac.za',scholarships_url=None if mode=='programme_fallback' else index_url if mode=='linked_depth_one' else url,search_queries_used=6)
    program=CandidateProgram(name='Computer Science',field='Computer Science',degree=DegreeLevel.BACHELOR,url=url)
    profile=SimpleNamespace(context=SimpleNamespace(citizenship='Kazakhstan',second_citizenship=None))
    scholarships,result=await web_scholarships.WebScholarshipAdapter(SimpleNamespace(get=get),'2027/28').find(candidate,program,profile,allow_search=False)
    return {'enabled':enabled,'mode':mode,'reads':reads,'scholarships':[s.model_dump(mode='json') for s in scholarships],'claims':[c.model_dump(mode='json') for c in result.claims],'outcomes':[asdict(x) for x in result.page_outcomes],'errors':result.errors}


@pytest.mark.parametrize('mode',('programme_fallback','explicit_primary','linked_depth_one'))
def test_actual_saved_wits_preserves_funding_discovery_off_on_on_off(mode):
    url,html,meta=retained_wits()
    phases=[asyncio.run(funding_route(mode,x,url,html,meta)) for x in (False,True,True,False)]
    assert phases[0]['reads']==phases[1]['reads']==phases[2]['reads']==phases[3]['reads']
    assert url in phases[1]['reads']
    assert 'https://www.wits.ac.za/study-at-wits/financial-aid-and-scholarships-administration' in phases[1]['reads']
    assert all(p['scholarships']==[] and p['claims']==[] for p in phases)


def test_marked_programme_is_never_its_own_award(monkeypatch):
    url,html,meta=retained_wits()
    synthetic=page(ACADEMIC+'<h2>Funding</h2><p>Value covers tuition per year. Deadline applies.</p>'+LINKS)
    def no_programme_award(*args,**kwargs):raise AssertionError('Programme page became award proof')
    monkeypatch.setattr(web_scholarships.WebScholarshipAdapter,'_parse_award',no_programme_award)
    result=asyncio.run(funding_route('linked_depth_one',True,url,html,meta,wits_html=synthetic))
    assert result['claims']==[] and result['scholarships']==[]
    assert len(result['reads'])==4


def test_marked_programme_respects_index_budget(monkeypatch):
    url,html,meta=retained_wits()
    monkeypatch.setattr(web_scholarships,'_MAX_INDEX_PAGES',1)
    result=asyncio.run(funding_route('linked_depth_one',True,url,html,meta))
    assert len(result['reads'])==2
    assert any('index page beyond the index budget' in x['detail'] for x in result['outcomes'])


def test_marked_programme_respects_award_page_budget(monkeypatch):
    url,html,meta=retained_wits()
    synthetic=page(ACADEMIC+'<h2>Funding</h2>'+LINKS+'<a href="/awards/three">Gamma Scholarship</a>')
    monkeypatch.setattr(web_scholarships,'_MAX_AWARD_PAGES',1)
    result=asyncio.run(funding_route('linked_depth_one',True,url,html,meta,wits_html=synthetic))
    assert result['reads']==['https://www.wits.ac.za/offline-review/funding-index',url,'https://www.wits.ac.za/awards/one']
    assert result['claims']==[] and result['scholarships']==[]


@pytest.mark.parametrize('title',('BSc Computer Science support','Computer Science scholarships'))
def test_funding_only_and_support_caller_routes_keep_legacy_policy(title):
    url,html,meta=retained_wits()
    synthetic=page(ACADEMIC+'<h2>Funding</h2>'+LINKS,title)
    classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=True
    classified=classifier.classify_page(url=url,html=synthetic)
    assert classified.page_type.value=='scholarship_index' and MARKER not in classified.signals
    off=asyncio.run(funding_route('linked_depth_one',False,url,html,meta,wits_html=synthetic))
    on=asyncio.run(funding_route('linked_depth_one',True,url,html,meta,wits_html=synthetic))
    assert off['reads']==on['reads']
    assert off['claims']==on['claims']==[]
    assert off['scholarships']==on['scholarships']==[]


def test_marked_programme_retains_same_host_and_domestic_url_controls(monkeypatch):
    # South Africa name is PENDING in the existing citizenship matcher; test the
    # URL guard only after the existing caller obtains a clear international verdict.
    monkeypatch.setattr(web_scholarships,"_is_international",lambda profile,candidate:True)
    url,html,meta=retained_wits()
    synthetic=page(ACADEMIC+'<h2>Funding</h2>'+LINKS+'<a href="https://unrelated.example/scholarship">Unrelated scholarship</a><a href="/awards/domestic-students-scholarship">Domestic students scholarship</a>')
    result=asyncio.run(funding_route('linked_depth_one',True,url,html,meta,wits_html=synthetic))
    assert not any('unrelated.example' in x or 'domestic-students' in x for x in result['reads'])
    assert 'https://www.wits.ac.za/awards/one' in result['reads']
    assert 'https://www.wits.ac.za/awards/two' in result['reads']


def test_marker_on_non_programme_cannot_bypass_class_policy(monkeypatch):
    url,html,meta=retained_wits()
    old_classify=web_scholarships.classify_page
    def classified(**kwargs):
        if kwargs['url']==url:return classifier.PageClassification(classifier.PageType.UNKNOWN,0.2,[MARKER],'No identity')
        return old_classify(**kwargs)
    monkeypatch.setattr(web_scholarships,'classify_page',classified)
    result=asyncio.run(funding_route('linked_depth_one',True,url,html,meta))
    assert len(result['reads'])==2
    assert result['claims']==[] and result['scholarships']==[]


def test_saved_actual_requirements_reader_quote_and_intake_scope():
    url,html,meta=retained_wits();reads=[]
    async def get(requested_url):
        reads.append(requested_url)
        if requested_url!=url:return FetchResult(url=requested_url,outcome=FetchOutcome.HTTP_ERROR,final_url=requested_url,error='Offline: missing retained source')
        return FetchResult(url=url,outcome=FetchOutcome.CACHED,status_code=200,content=html.encode(),text=html,content_type='text/html',final_url=url,from_cache=True,fetched_at=datetime.fromisoformat(meta['fetched_at']),content_hash=meta['content_hash'])
    candidate=Candidate(name='University of the Witwatersrand',domain='wits.ac.za',country='South Africa',city='Johannesburg',search_queries_used=6)
    program=CandidateProgram(name='Computer Science',field='Computer Science',degree=DegreeLevel.BACHELOR,url=url)
    title=classifier._title(classifier._parse_markup(html));phases=[]
    for enabled in (False,True,True,False):
        classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
        result=asyncio.run(web_requirements.WebRequirementsAdapter(SimpleNamespace(get=get),'2027/28').verify(candidate,program,'fall2027'))
        claims=[c.model_dump(mode='json') for c in result.claims]
        exists=[c for c in claims if c['claim_type']=='program_exists']
        assert not any(c['claim_type']=='intake_open' and c['normalized_value'] is True for c in claims)
        for c in exists:
            assert is_verbatim_excerpt(c['original_text_excerpt'],title)
            assert c['scope']['intake'] is None and c['scope']['academic_year'] is None
        if enabled:assert 'intake status is unknown' in ' '.join(result.errors)
        phases.append({'claims':claims,'errors':result.errors,'exists':exists})
    assert [len(x['exists']) for x in phases]==[0,1,1,0]
    assert phases[0]==phases[3] and phases[1]==phases[2]
