"""Actual production reader over pinned Wits bytes and independent funding controls."""
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
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome
from app.adapters.requirements import web_requirements

from replay_independent_scope_negatives import CASES, ROOT, legacy, page, proposal

MANIFEST = json.loads((ROOT / 'review-start.manifest.json').read_text())


def denied(*args, **kwargs):
    raise AssertionError('Offline reader attempted network/provider access')


async def read(url, html, classifier, program_name, metadata=None):
    reads = []
    meta = metadata or {'fetched_at':'2026-10-07T20:28:37+00:00', 'content_hash':_content_hash(html)}
    async def get(requested_url):
        reads.append(requested_url)
        if requested_url != url:
            return FetchResult(url=requested_url, outcome=FetchOutcome.HTTP_ERROR, final_url=requested_url,
                               error='Offline: no retained body supplied for this followed URL')
        return FetchResult(url=url, outcome=FetchOutcome.CACHED, status_code=200,
                           content=html.encode(), text=html, content_type='text/html', final_url=url,
                           from_cache=True, fetched_at=datetime.fromisoformat(meta['fetched_at']),
                           content_hash=meta['content_hash'])
    domain = 'wits.ac.za' if 'wits.ac.za' in url else 'example.edu'
    candidate = Candidate(name='Saved Wits' if domain == 'wits.ac.za' else 'Synthetic funding fixture',
                          country='South Africa' if domain == 'wits.ac.za' else 'Synthetic',
                          city='Johannesburg' if domain == 'wits.ac.za' else 'Synthetic',
                          domain=domain, search_queries_used=6)
    program = CandidateProgram(name=program_name, field='Computer Science', degree=DegreeLevel.BACHELOR, url=url)
    with patch.object(web_requirements, 'classify_page', classifier), patch('app.adapters.search.get_search_provider', denied), patch.object(socket,'getaddrinfo',denied), patch.object(socket,'create_connection',denied), patch.object(socket.socket,'connect',denied):
        result = await web_requirements.WebRequirementsAdapter(SimpleNamespace(get=get), '2027/28').verify(candidate, program, 'fall2027')
    claims = [c.model_dump(mode='json') for c in result.claims]
    exists = [c for c in claims if c['claim_type'] == ClaimType.PROGRAM_EXISTS.value]
    return {'claims':claims,'exists_claims':exists,'exists_count':len(exists),'errors':result.errors,
            'page_types':result.page_types,'page_outcomes':[dataclasses.asdict(x) for x in result.page_outcomes],
            'saved_byte_lookup_calls':reads,'intake_open_count':sum(c['claim_type']==ClaimType.INTAKE_OPEN.value and c['normalized_value'] is True for c in claims)}


async def main():
    body = Path(MANIFEST['wits_body_original']); mp = Path(MANIFEST['wits_metadata_original'])
    raw = body.read_bytes(); meta = json.loads(mp.read_text())
    assert hashlib.sha256(raw).hexdigest() == MANIFEST['wits_body_sha256']
    assert hashlib.sha256(mp.read_bytes()).hexdigest() == MANIFEST['wits_metadata_sha256']
    html = raw.decode(meta.get('encoding','utf-8'), errors='replace'); url = meta['url']
    assert _content_hash(html) == meta['content_hash']
    wits = []
    title = legacy._title(legacy._parse_markup(html))
    for enabled in (False,True,True,False):
        proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = enabled
        classified = proposal.classify_page(url=url, html=html, text=readable_text(html))
        reader = await read(url,html,proposal.classify_page,'Computer Science',meta)
        for claim in reader['exists_claims']:
            assert is_verbatim_excerpt(claim['original_text_excerpt'],title)
            assert claim['original_text_excerpt'] in html
            assert claim['scope']['intake'] is None and claim['scope']['academic_year'] is None
        assert reader['intake_open_count'] == 0
        if enabled:
            assert 'intake status is unknown' in ' '.join(reader['errors'])
        wits.append({'enabled':enabled,'classification':dataclasses.asdict(classified),'reader':reader})
    assert [r['reader']['exists_count'] for r in wits] == [0,1,1,0]
    assert wits[0] == wits[3] and wits[1] == wits[2]
    negatives = []
    for name, content, expected in CASES[:4]:
        fixture_html = page(content); fixture_url = 'https://example.edu/support/computer-science'
        proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
        off = await read(fixture_url,fixture_html,proposal.classify_page,'BSc Computer Science')
        proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
        on = await read(fixture_url,fixture_html,proposal.classify_page,'BSc Computer Science')
        assert off['exists_count']==0 and on['exists_count']==1
        negatives.append({'case':name,'html':fixture_html,'html_sha256':hashlib.sha256(fixture_html.encode()).hexdigest(),
                          'synthetic_source_url':fixture_url,'expected_programme_exists':False,'off':off,'on':on})
    result={'network_calls':0,'provider_calls':0,'model_calls':0,'repo_edits':0,
            'proposal_source_sha256':hashlib.sha256((ROOT/'proposal-pinned/proposed_page_classifier.py').read_bytes()).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'wits_source_url':url,'wits_body_sha256':MANIFEST['wits_body_sha256'],'wits_metadata_sha256':MANIFEST['wits_metadata_sha256'],
            'wits_metadata_content_hash':meta['content_hash'],'wits_original_title':title,
            'wits_off_on_on_off':wits,'independent_funding_reader_negatives':negatives,
            'scope':'Actual WebRequirementsAdapter.verify with saved-byte get. Wits subject exists can be quoted; 2027 intake/campus/international route not confirmed. Synthetic fixtures do not claim university facts.'}
    (ROOT/'independent-readers.offline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'wits_exists':[r['reader']['exists_count'] for r in wits],
                      'false_programme_exists_on':[r['case'] for r in negatives],'source':result['proposal_source_sha256']},indent=2))


if __name__ == '__main__':
    asyncio.run(main())
