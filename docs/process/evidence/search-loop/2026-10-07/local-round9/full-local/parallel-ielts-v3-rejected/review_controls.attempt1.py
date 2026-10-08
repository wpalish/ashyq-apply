"""Independent offline caller review; spec-load only immutable proposed modules."""
from __future__ import annotations
import asyncio
import hashlib
import importlib.util
import json
import socket
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

OWN=Path(__file__).resolve().parent
PROPOSAL=OWN.parent.parent/'local-round8/b-ielts-section-proposal-v3'
REPO=OWN.parent.parent/'ashyq-apply/backend'
sys.path.insert(0,str(REPO))
def denied(*a,**k): raise AssertionError('independent review forbids external actions')
socket.getaddrinfo=denied
socket.create_connection=denied
import httpx
httpx.Client.request=denied
httpx.AsyncClient.request=denied
from app.adapters.requirements import web_requirements as actual
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import FetchResult
from app.adapters.page_classifier import classify_page
from app.adapters.extraction import readable_text
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome
import app.adapters
import app.adapters.requirements

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module
extraction=load('app.adapters.extraction',PROPOSAL/'proposed/app/adapters/extraction.py')
helper=load('app.adapters.requirements.ielts_sections',PROPOSAL/'proposed/app/adapters/requirements/ielts_sections.py')
proposed=load('independent_ielts_v3_web_requirements',PROPOSAL/'proposed/app/adapters/requirements/web_requirements.py')
URL='https://admissions.example.edu/admission-requirements'
IELTS={ClaimType.IELTS_MIN_OVERALL.value,ClaimType.IELTS_MIN_SUBSCORE.value,ClaimType.IELTS_ACCEPTED_TYPES.value}

class Reader:
    def __init__(self,url,body): self.url=url;self.body=body;self.calls=[]
    async def get(self,url,**kwargs):
        self.calls.append(url)
        assert url==self.url,'one-page offline transport refuses any secondary source'
        return FetchResult(url=url,final_url=url,outcome=FetchOutcome.OK,status_code=200,text=self.body,content=self.body.encode(),content_type='text/html',from_cache=True,fetched_at=datetime(2026,10,8,tzinfo=UTC))

async def read(body,on=None,url=URL):
    module=actual if on is None else proposed
    reader=Reader(url,body)
    candidate=Candidate(name='Independent Synthetic University',country='Example',city='',domain='example.edu',admissions_url=url,search_queries_used=6)
    program=CandidateProgram(name='Computer Science',field='computer science',degree=DegreeLevel.BACHELOR,url=None)
    if on is not None: module.IELTS_PROSE_SECTION_OWNERSHIP=on
    out=await module.WebRequirementsAdapter(reader,'2027/28').verify(candidate,program,'Fall 2027')
    return {'claims':[c.model_dump(mode='json') for c in out.claims],'page_outcomes':[asdict(o) for o in out.page_outcomes],'errors':out.errors,'pages_checked':out.pages_checked,'pages_failed':out.pages_failed,'fetcher_calls':reader.calls}

def body(inner,title='Bachelor admission requirements'):
    return '<html><head><title>'+title+'</title></head><body><main><h1>'+title+'</h1>'+inner+'</main></body></html>'
# Expected semantics were chosen independently, before observing the candidate.
CASES=[
 ('control_explicit', '<h2>IELTS Academic</h2><p>Overall score 6.5 is required. Writing 6.0.</p>', {'ielts_min_overall':6.5,'ielts_min_subscore':{'writing':6.0}},'positive'),
 ('negated_required','<h2>IELTS Academic</h2><p>Overall minimum 6.5 is not required.</p>',{},'explicit nonrequirement'),
 ('negated_require_verb','<h2>IELTS Academic</h2><p>We do not require an overall minimum 6.5.</p>',{},'explicit nonrequirement'),
 ('cannot_accept_reverse','<h2>IELTS Academic</h2><p>We cannot accept IELTS Academic. Overall minimum 6.5.</p>',{},'explicit exam refusal'),
 ('not_an_accepted_test','<h2>IELTS Academic</h2><p>IELTS Academic is not an accepted test. Overall minimum 6.5.</p>',{},'explicit exam refusal'),
 ('variant_parenthetical_refusal','<h2>IELTS Academic</h2><p>IELTS Academic (including UKVI Academic) is not accepted. Overall minimum 6.5.</p>',{},'explicit exam refusal with modifier'),
 ('other_exam_celpip','<h2>IELTS Academic</h2><h3>CELPIP General</h3><p>Overall 7.0 is required for CELPIP General.</p>',{},'different explicitly named exam'),
 ('other_exam_full_toefl','<h2>IELTS Academic</h2><h3>Test of English as a Foreign Language</h3><p>A writing minimum 6.0 applies to the Test of English as a Foreign Language.</p>',{},'different full-name exam'),
 ('numeric_currency_nzd','<h2>IELTS Academic</h2><h3>Processing charges</h3><p>Overall 6.50 NZD processing fee is payable.</p>',{},'explicit currency fee'),
 ('numeric_cents','<p>IELTS Academic 6.5 cents processing fee is payable.</p>',{},'explicit fee atom'),
 ('numeric_unicode_negative','<p>IELTS Academic overall −6.5 is required.</p>',{},'invalid signed atom'),
 ('aria_heading_owned','<div role="heading" aria-level="2">IELTS Academic</div><p>Overall score 6.5 is required.</p>',{'ielts_min_overall':6.5},'explicit semantic heading'),
 ('aria_labelled_direct_text','<h2 id="ielts">IELTS Academic</h2><section aria-labelledby="ielts">Overall score 6.5 is required.</section>',{'ielts_min_overall':6.5},'explicit heading ownership/direct text'),
 ('owned_direct_span','<h2>IELTS Academic</h2><span>Overall score 6.5 is required.</span>',{'ielts_min_overall':6.5},'explicit heading/direct inline content'),
 ('section_direct_text','<section><h2>IELTS Academic</h2>Overall score 6.5 is required.</section>',{'ielts_min_overall':6.5},'explicit same-section direct text'),
 ('nested_div_break_positive','<h2>IELTS Academic</h2><div>Overall score 6.5 is required.<br>Writing 6.0.</div>',{'ielts_min_overall':6.5,'ielts_min_subscore':{'writing':6.0}},'positive leaf-div'),
 ('role_chrome_negative','<h2>IELTS Academic</h2><div role="navigation"><p>Overall score 9.0 is required.</p></div>',{},'explicit chrome'),
 ('local_year_title_conflict','<h2>IELTS Academic</h2><p>For academic year 2024/25 admission, overall score 6.5 is required.</p>',{'ielts_min_overall':6.5},'observed old-year vs own title2027/28'),
]

async def main():
    rows=[]
    for name,inner,expected,meaning in CASES:
        html=body(inner,'Bachelor admission requirements academic year 2027/28' if name=='local_year_title_conflict' else 'Bachelor admission requirements')
        old=await read(html); off=await read(html,False); on=await read(html,True)
        assert old==off,('legacy OFF changed',name)
        assert old['page_outcomes']==on['page_outcomes'],('page classes/outcomes changed',name)
        assert len(on['fetcher_calls'])==1
        values={c['claim_type']:c['normalized_value'] for c in on['claims'] if c['claim_type'] in IELTS}
        numbers={k:v for k,v in values.items() if k!='ielts_accepted_types'}
        passed=all(numbers.get(k)==v for k,v in expected.items()) and (bool(expected) or not values)
        if name=='local_year_title_conflict':
            claim=next((c for c in on['claims'] if c['claim_type']=='ielts_min_overall'),None)
            passed=passed and claim is not None and claim['scope']['academic_year']=='2024/25'
        rows.append({'case':name,'semantic_expectation':meaning,'expected_numeric':expected,'body':html,'body_sha256':hashlib.sha256(html.encode()).hexdigest(),'contiguous_source_snippet':inner,'passed':passed,'actual_values':values,'legacy_values':{c['claim_type']:c['normalized_value'] for c in old['claims'] if c['claim_type'] in IELTS},'original':old,'off':off,'on':on})
        print(json.dumps({k:rows[-1][k] for k in ['case','passed','expected_numeric','actual_values','legacy_values']}),flush=True)
    # Native UNKNOWN control; no page classifier substitutions.
    unknown_html=body('<p>IELTS Academic minimum 6.5 is required.</p>','English testing')
    url='https://example.edu/english-testing'
    out=await read(unknown_html,True,url)
    rows.append({'case':'native_unknown_permission','body':unknown_html,'body_sha256':hashlib.sha256(unknown_html.encode()).hexdigest(),'passed':not any(c['claim_type'] in IELTS for c in out['claims']) and any(o['page_type']=='unknown' for o in out['page_outcomes']),'on':out,'contiguous_source_snippet':'IELTS Academic minimum 6.5 is required.','semantic_expectation':'UNKNOWN remains no permission'})
    imports=[]
    for name in ['app.adapters.page_classifier','app.adapters.html_parse','app.adapters.requirements.section_scope','app.adapters.scope_reader','app.adapters.document_ir','app.domain.claim_verifier','app.adapters.fetching']:
        m=sys.modules[name]; p=Path(m.__file__).resolve(); assert p.is_relative_to(REPO)
        imports.append({'name':name,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    receipt={'controls':len(rows),'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows),'classifier_overrides':0,'normal_dependencies':imports,'proposal_modules_only':['extraction','ielts_sections','web_requirements'],'network_DNS_provider_model_calls':0,'repo_proposal_git_stop_edits':0,'results':rows}
    (OWN/'controls.original.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='results'}))

if __name__=='__main__': asyncio.run(main())
