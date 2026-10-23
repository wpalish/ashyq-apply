"""Independent saved-byte WS-1 design simulation; no applied source flag or network."""
from __future__ import annotations
import asyncio
from dataclasses import asdict
from datetime import UTC,datetime
import hashlib,json,socket,subprocess,sys
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO=ROOT/'work/ashyq-apply/backend'
sys.path.insert(0,str(REPO))

def deny(*args,**kwargs):
    raise AssertionError('Offline WS-1 review: no network/provider/process fallback')
socket.getaddrinfo=deny;socket.create_connection=deny;socket.socket.connect=deny
subprocess.run=deny;subprocess.Popen=deny;subprocess.check_output=deny
import httpx
httpx.AsyncClient.send=deny;httpx.Client.send=deny
from app.adapters import page_classifier as pc
from app.adapters.discovery import live_discovery as ld
from app.adapters.discovery.catalog_walker import CatalogWalker,CatalogWalk,WalkerLink
from app.adapters.fetching import FetchResult,_content_hash
from app.domain.enums import FetchOutcome
from app.adapters.html_parse import parse_html
from app.adapters.search import intent

class StopAfterExistingConfirmation(Exception):
    def __init__(self,walk):self.walk=walk

class SimulatedInnerStop(CatalogWalker):
    """Only simulate the proposed inner break after real _read_lead, never fake acceptance."""
    def __init__(self,*args,stop=False,**kwargs):super().__init__(*args,**kwargs);self.stop=stop
    async def _read_lead(self,link,walk):
        await super()._read_lead(link,walk)
        if self.stop and len(ld._distinct_fields(self.fields))==1 and walk.confirmed:
            raise StopAfterExistingConfirmation(walk)
    async def walk_catalog(self,*args,**kwargs):
        try:return await super().walk_catalog(*args,**kwargs)
        except StopAfterExistingConfirmation as exc:return exc.walk

class OfflineFetcher:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    async def get(self,url,**kwargs):
        self.calls.append(url)
        if url not in self.pages:raise AssertionError('Missing retained/synthetic fixture, no fallback: '+url)
        item=self.pages[url]
        if isinstance(item,str):return FetchResult(url=url,final_url=url,outcome=FetchOutcome.OK,text=item,status_code=200,content_hash=_content_hash(item))
        return item

def saved(body_path,meta_path):
    raw=Path(body_path).read_bytes();meta_raw=Path(meta_path).read_bytes();meta=json.loads(meta_raw)
    html=raw.decode(meta.get('encoding','utf-8'),errors='replace')
    assert _content_hash(html)==meta['content_hash']
    return meta['url'],html,{'body_path':str(body_path),'meta_path':str(meta_path),'body_sha256':hashlib.sha256(raw).hexdigest(),'meta_sha256':hashlib.sha256(meta_raw).hexdigest(),'content_hash_formula_matches':True}

def simple(title,body):return '<html><head><title>'+title+'</title></head><body><main><h1>'+title+'</h1>'+body+'</main></body></html>'

def catalogue(urls_labels):return simple('Bachelor programmes','<p>Choose a programme.</p>'+''.join('<a href="'+u+'">'+label+'</a>' for u,label in urls_labels))

async def paired(name,domain,pages,urls_labels,fields=None,strict_phrase=False,purpose=False):
    pc.PROGRAMME_IDENTITY_BEFORE_FUNDING=purpose;ld.SUBJECT_PHRASE_MATCH=strict_phrase
    cat='https://'+domain+'/bachelors/catalogue';allpages={cat:catalogue(urls_labels),**pages}
    phases=[]
    for stop in (False,True,True,False):
        f=OfflineFetcher(allpages);walker=SimulatedInnerStop(fetcher=f,domain=domain,degree='bachelor',fields=['computer science'] if fields is None else fields,stop=stop)
        walk=await walker.walk_catalog(cat)
        phases.append({'inner_stop':stop,'reads':f.calls,'walk':asdict(walk)})
    assert phases[0]==phases[3] and phases[1]==phases[2]
    # Compare prototype OFF with actual frozen walker, including full outputs.
    frozen=OfflineFetcher(allpages);walk=await CatalogWalker(fetcher=frozen,domain=domain,degree='bachelor',fields=['computer science'] if fields is None else fields).walk_catalog(cat)
    assert frozen.calls==phases[0]['reads'] and asdict(walk)==phases[0]['walk']
    return {'case':name,'evidence_type':'synthetic catalogue composition; real saved detail bodies where specified','subject_phrase_match':strict_phrase,'programme_identity_before_funding':purpose,'fields':['computer science'] if fields is None else fields,'synthetic_catalogue_html':allpages[cat],'off_on_on_off':phases}

async def direct(name,url,body,domain='example.edu'):
    f=OfflineFetcher({url:body});w=SimulatedInnerStop(fetcher=f,domain=domain,degree='bachelor',fields=['computer science'],stop=True);walk=CatalogWalk('https://'+domain+'/catalogue')
    stopped=False
    try:await w._read_lead(WalkerLink(url,'BSc Computer Science',20,'html'),walk)
    except StopAfterExistingConfirmation:stopped=True
    return {'case':name,'url':url,'classification':asdict(pc.classify_page(url=url,html=body)) if isinstance(body,str) else None,'stop':stopped,'walk':asdict(walk),'reads':f.calls}

async def replay():
    old=(pc.PROGRAMME_IDENTITY_BEFORE_FUNDING,ld.SUBJECT_PHRASE_MATCH)
    try:
        pc.PROGRAMME_IDENTITY_BEFORE_FUNDING=False;ld.SUBJECT_PHRASE_MATCH=False
        entries={};pins={};classifications={}
        for label in ('data-science','computer-science'):
            root=ROOT/'work/search-loop-round5/reviews/expert_a/retained-pages'
            u,h,p=saved(root/(label+'.body'),root/(label+'.meta.json'));entries[label]=(u,h);pins[label]=p
            page=pc.classify_page(url=u,html=h);classifications[label]={'url':u,'page':asdict(page),'profile_rejection':ld.profile_rejects(page,'bachelor',['computer science'])}
        du,dh=entries['data-science'];cu,ch=entries['computer-science']
        labels=[(du,classifications['data-science']['page']['title']),(cu,classifications['computer-science']['page']['title'])]
        cases=[]
        cases.append(await paired('AUT_saved_wrong_major_precedes_correct_major','www.aut.ac.nz',{du:dh,cu:ch},labels))
        assert cases[-1]['off_on_on_off'][0]['walk']['confirmed']==[du,cu]
        assert cases[-1]['off_on_on_off'][1]['walk']['confirmed']==[du]
        cases.append(await paired('AUT_precise_subject_experiment_opt_in','www.aut.ac.nz',{du:dh,cu:ch},labels,strict_phrase=True))
        assert cases[-1]['off_on_on_off'][1]['walk']['confirmed']==[cu]
        # Explicitly synthetic purpose/scope controls: no claim of official existence.
        generic=simple('BSc Computer Science','<h2>Curriculum</h2><p>The bachelor programme teaches first-year programming and second-year algorithms.</p><p>International applicants for academic year 2027/28 may apply.</p>')
        hiddenfund=simple('BSc Computer Science','<h2>Eligibility</h2><p>This page lists fee waivers for students already admitted to another degree. The award covers tuition fees and its annual value is 5000 EUR. This support page does not offer a degree.</p>')
        funding='https://example.edu/bachelors/computer-science';correct='https://example.edu/bachelors/computer-science-current-programme'
        cases.append(await paired('synthetic_funding_copy_without_funding_heading','example.edu',{funding:hiddenfund,correct:generic},[(funding,'BSc Computer Science'),(correct,'BSc Computer Science')]))
        assert cases[-1]['off_on_on_off'][0]['walk']['confirmed']==[funding,correct]
        assert cases[-1]['off_on_on_off'][1]['walk']['confirmed']==[funding]
        oldscope=simple('BSc Computer Science','<p>This bachelor programme at Satellite Campus is for continuing domestic students. Academic year 2019/20. International applications are closed.</p>')
        oldurl='https://example.edu/bachelors/computer-science';newurl='https://example.edu/bachelors/computer-science-international-2027'
        cases.append(await paired('synthetic_older_population_campus_first','example.edu',{oldurl:oldscope,newurl:generic},[(oldurl,'BSc Computer Science'),(newurl,'BSc Computer Science')],strict_phrase=True))
        assert cases[-1]['off_on_on_off'][1]['walk']['confirmed']==[oldurl]
        assert cases[-1]['off_on_on_off'][0]['walk']['confirmed']==[oldurl,newurl]
        # Exact multi-field counting is deliberately lexical, not ontology collapsing.
        for fields in (['computer science',' Computer Science '],['computer science','Computing Science'],['computer science','mathematics'],[],['  ']):
            case=await paired('distinct_fields_'+str(len(cases)),'example.edu',{oldurl:oldscope,newurl:generic},[(oldurl,'BSc Computer Science'),(newurl,'BSc Computer Science')],fields=fields,strict_phrase=True)
            case['distinct_normalized_fields']=ld._distinct_fields(fields);cases.append(case)
            if len(ld._distinct_fields(fields))!=1:assert case['off_on_on_off'][0]['reads']==case['off_on_on_off'][1]['reads']
        pc.PROGRAMME_IDENTITY_BEFORE_FUNDING=False;ld.SUBJECT_PHRASE_MATCH=False
        start=json.loads((ROOT/'work/search-loop-round6/reviews/expert_a/review-start.manifest.json').read_text())
        wu,wh,wp=saved(start['wits_body_original'],start['wits_metadata_original']);pins['wits']=wp
        wits=await direct('actual_Wits_PF1_defaultFalse',wu,wh,domain='www.wits.ac.za');assert not wits['stop'] and wits['classification']['page_type'].value=='scholarship_index'
        # Existing Nagoya mixed requirements page was never programme proof.
        nup=json.loads((ROOT/'work/development-experts/expert_a/nagoya-nupace-scope-evidence.offline.json').read_text())
        nu,nh,np=saved(nup['body_path'],nup['meta_path']);pins['nagoya']=np
        nagoya=await direct('actual_Nagoya_mixed_language_requirements',nu,nh,domain='en.nagoya-u.ac.jp');assert not nagoya['stop']
        purpose=await direct('synthetic_explicit_funding_heading',funding,simple('BSc Computer Science','<h2>Scholarships and funding</h2><a href="/awards/a">Alpha Scholarship</a><a href="/awards/b">Beta Scholarship</a><p>Fee waivers apply to students already admitted.</p>'));assert not purpose['stop']
        redirects=await direct('synthetic_offsite_redirect',funding,FetchResult(url=funding,final_url='https://foreign.edu/computer-science',outcome=FetchOutcome.OK,status_code=200,text=generic));assert not redirects['stop']
        # Record exact public caller proof without rerunning immutable B script.
        b=ROOT/'work/local-round7/reviews/expert_b-baseline-funnel';caller=json.loads((b/'caller-boundary.offline.json').read_text());boundary=caller['search_boundary']
        bsummary={'ready_manifest_sha256':hashlib.sha256((b/'ready-manifest.json').read_bytes()).hexdigest(),'caller_sha256':hashlib.sha256((b/'caller-boundary.offline.json').read_bytes()).hexdigest(),'selected_programme':boundary['selected']['program_page'],'reads_completed_before_search_count':len(boundary['reads_completed_before_search']),'full_32_get_prefix_matches_live_log':caller['full_32_get_prefix_matches_live_log'],'provider_result_control':caller['provider_result_control'],'actual_timeout_result':caller['actual_timeout_result']}
        return {'status':'OFFLINE_DESIGN_SIMULATION_NOT_APPLIED_SOURCE','pins':pins,'classifications':classifications,'cases':cases,'purpose_controls':[wits,nagoya,purpose,redirects],'B_actual_caller_retained_summary':bsummary,'no_invented_official_catalogue_membership':True,'source_scope_year_campus_population_not_proven':True,'network_provider_model_calls':0,'source_git_STOP_edits':0}
    finally:pc.PROGRAMME_IDENTITY_BEFORE_FUNDING,ld.SUBJECT_PHRASE_MATCH=old

if __name__=='__main__':
    data=asyncio.run(replay());(BASE/'incremental-risks.offline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n');print(json.dumps({'cases':len(data['cases']),'purpose_controls':len(data['purpose_controls']),'AUT_on_confirmed':data['cases'][0]['off_on_on_off'][1]['walk']['confirmed'],'B_caller':data['B_actual_caller_retained_summary'],'network_calls':0},indent=2))
