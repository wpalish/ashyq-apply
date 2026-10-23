"""Actual production readers over immutable Wits bytes; all missing URLs stay unknown."""
import asyncio
import dataclasses
import hashlib
import json
import socket
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import readable_text
from app.adapters.fetching import FetchResult, _content_hash
from app.adapters.scholarship import web_scholarships
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import DegreeLevel, FetchOutcome

from replay_scope import CASES, ROOT, denied, legacy, page, proposal
from replay_independent_readers import read

MANIFEST = json.loads((ROOT.parent/'review-start.manifest.json').read_text())


def consistent_classifier(**kwargs):
    """Real installation shares one PageType class; emulate it without module replacement."""
    c = proposal.classify_page(**kwargs)
    return dataclasses.replace(c, page_type=legacy.PageType(c.page_type.value))


async def funding(mode, enabled, url, html, meta):
    index_url = 'https://www.wits.ac.za/offline-review/funding-index'
    index_html = '<html><head><title>Scholarships</title></head><body><main><h1>Scholarships</h1><a href="'+url+'">Computer Science scholarships</a></main></body></html>'
    reads=[]
    async def get(requested_url):
        reads.append(requested_url)
        if requested_url==url:
            return FetchResult(url=url,outcome=FetchOutcome.CACHED,status_code=200,content=html.encode(),text=html,content_type='text/html',final_url=url,from_cache=True,fetched_at=datetime.fromisoformat(meta['fetched_at']),content_hash=meta['content_hash'])
        if mode=='linked_depth_one' and requested_url==index_url:
            return FetchResult(url=index_url,outcome=FetchOutcome.CACHED,status_code=200,content=index_html.encode(),text=index_html,content_type='text/html',final_url=index_url,from_cache=True,fetched_at=datetime.fromisoformat(meta['fetched_at']),content_hash=_content_hash(index_html))
        return FetchResult(url=requested_url,outcome=FetchOutcome.HTTP_ERROR,final_url=requested_url,error='Offline: no retained body supplied for this followed URL; outcome unknown')
    candidate=Candidate(name='University of the Witwatersrand',domain='wits.ac.za',country='South Africa',city='Johannesburg',scholarships_url=None if mode=='programme_fallback' else index_url if mode=='linked_depth_one' else url,search_queries_used=6)
    program=CandidateProgram(name='Computer Science',field='Computer Science',degree=DegreeLevel.BACHELOR,url=url)
    profile=SimpleNamespace(context=SimpleNamespace(citizenship='Kazakhstan',second_citizenship=None))
    proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
    with patch.object(web_scholarships,'classify_page',consistent_classifier),patch('app.adapters.search.get_search_provider',denied),patch.object(socket,'getaddrinfo',denied),patch.object(socket,'create_connection',denied),patch.object(socket.socket,'connect',denied):
        scholarships,result=await web_scholarships.WebScholarshipAdapter(SimpleNamespace(get=get),'2027/28').find(candidate,program,profile,allow_search=False)
    return {'enabled':enabled,'mode':mode,'saved_byte_lookup_calls':reads,'scholarships':[s.model_dump(mode='json') for s in scholarships],'claims':[c.model_dump(mode='json') for c in result.claims],'page_types':result.page_types,'page_outcomes':[dataclasses.asdict(x) for x in result.page_outcomes],'errors':result.errors,'pages_checked':result.pages_checked,'pages_failed':result.pages_failed}


async def main():
    raw=Path(MANIFEST['wits_body_original']).read_bytes()
    mp=Path(MANIFEST['wits_metadata_original']);meta=json.loads(mp.read_text())
    assert hashlib.sha256(raw).hexdigest()==MANIFEST['wits_body_sha256']
    assert hashlib.sha256(mp.read_bytes()).hexdigest()==MANIFEST['wits_metadata_sha256']
    html=raw.decode(meta.get('encoding','utf-8'),errors='replace');url=meta['url']
    assert _content_hash(html)==meta['content_hash']
    title=legacy._title(legacy._parse_markup(html))
    wits=[]
    for enabled in (False,True,True,False):
        proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
        classification=proposal.classify_page(url=url,html=html,text=readable_text(html))
        result=await read(url,html,proposal.classify_page,'Computer Science',meta)
        for c in result['exists_claims']:
            assert is_verbatim_excerpt(c['original_text_excerpt'],title)
            assert c['original_text_excerpt'] in html
            assert c['scope']['intake'] is None and c['scope']['academic_year'] is None
        assert result['intake_open_count']==0
        if enabled: assert 'intake status is unknown' in ' '.join(result['errors'])
        wits.append({'enabled':enabled,'classification':dataclasses.asdict(classification),'reader':result})
    assert [x['reader']['exists_count'] for x in wits]==[0,1,1,0]
    assert wits[0]==wits[3] and wits[1]==wits[2]
    controls=[]
    for name,body,expected in CASES[:4]+[CASES[9],CASES[11]]:
        fixture_html=page(body);fixture_url='https://example.edu/support/computer-science'
        phases=[]
        for enabled in (False,True):
            proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
            phases.append({'enabled':enabled,'reader':await read(fixture_url,fixture_html,proposal.classify_page,'BSc Computer Science')})
        controls.append({'case':name,'html_sha256':hashlib.sha256(fixture_html.encode()).hexdigest(),'expected_classification':expected,'phases':phases})
    assert all(x['phases'][1]['reader']['exists_count']==0 for x in controls[:4])
    funding_results=[]
    for mode in ('programme_fallback','explicit_primary','linked_depth_one'):
        for enabled in (False,True):
            funding_results.append(await funding(mode,enabled,url,html,meta))
    proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=False;off=proposal.classify_page(url=url,html=html)
    proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=True;on=proposal.classify_page(url=url,html=html)
    assert off.accepts('scholarship_links') is True and on.accepts('scholarship_links') is False
    result={'network_calls':0,'provider_calls':0,'model_calls':0,'repo_edits':0,'proposal_sha256':hashlib.sha256((ROOT/'proposal-pinned/proposed_page_classifier.py').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'wits_source_url':url,'wits_body_sha256':MANIFEST['wits_body_sha256'],'wits_metadata_sha256':MANIFEST['wits_metadata_sha256'],'wits_metadata_content_hash':meta['content_hash'],'wits_title':title,'wits_off_on_on_off':wits,'semantic_reader_controls':controls,'scholarship_links_off_on':[off.accepts('scholarship_links'),on.accepts('scholarship_links')],'raw_award_links':web_scholarships._award_links(html,url),'lists_awards_below':web_scholarships._lists_awards_below(html,url),'funding_reader_controls':funding_results,'funding_binding':'Only classify_page is patched; returned page_type is converted to production PageType so production is comparisons use the installed enum singleton. Classifier class/allowlist otherwise untouched. Synthetic index is routing fixture, not a university fact. Missing target bodies are unknown HTTP_ERROR.'}
    (ROOT/'actual-readers.offline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'wits_exists':[x['reader']['exists_count'] for x in wits],'funding_reads':[{'mode':x['mode'],'enabled':x['enabled'],'reads':x['saved_byte_lookup_calls']} for x in funding_results],'scholarship_links_allowlist':[off.accepts('scholarship_links'),on.accepts('scholarship_links')]},indent=2))


if __name__=='__main__':
    asyncio.run(main())
