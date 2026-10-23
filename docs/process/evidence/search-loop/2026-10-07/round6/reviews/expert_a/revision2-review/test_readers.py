"""Independent production-caller controls with zero provider/transport availability."""
import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from replay_readers import MANIFEST, funding, read
from replay_scope import CASES, legacy, page, proposal
from app.domain.claim_verifier import is_verbatim_excerpt


def retained_wits():
    raw = Path(MANIFEST['wits_body_original']).read_bytes()
    meta = json.loads(Path(MANIFEST['wits_metadata_original']).read_text())
    assert hashlib.sha256(raw).hexdigest() == MANIFEST['wits_body_sha256']
    return meta['url'], raw.decode(meta.get('encoding','utf-8'),errors='replace'), meta


@pytest.mark.parametrize('mode', ('programme_fallback','explicit_primary','linked_depth_one'))
def test_saved_programme_preserves_funding_discovery_route(mode):
    url,html,meta = retained_wits()
    off = asyncio.run(funding(mode,False,url,html,meta))
    on = asyncio.run(funding(mode,True,url,html,meta))
    assert off['saved_byte_lookup_calls'] == on['saved_byte_lookup_calls']
    assert off['scholarships'] == on['scholarships'] == []


def test_saved_wits_requirements_actual_reader_quote_and_unknown_intake():
    url,html,meta=retained_wits()
    title=legacy._title(legacy._parse_markup(html))
    phases=[]
    for enabled in (False,True,True,False):
        proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
        result=asyncio.run(read(url,html,proposal.classify_page,'Computer Science',meta))
        phases.append(result)
        assert result['intake_open_count']==0
        for claim in result['exists_claims']:
            assert is_verbatim_excerpt(claim['original_text_excerpt'],title)
            assert claim['scope']['intake'] is None
            assert claim['scope']['academic_year'] is None
    assert [r['exists_count'] for r in phases]==[0,1,1,0]
    assert phases[0]==phases[3] and phases[1]==phases[2]


@pytest.mark.parametrize('name,body,expected',CASES[:4],ids=[x[0] for x in CASES[:4]])
def test_funding_page_cannot_create_programme_exists(name,body,expected):
    html=page(body);url='https://example.edu/support/computer-science'
    for enabled in (False,True):
        proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
        result=asyncio.run(read(url,html,proposal.classify_page,'BSc Computer Science'))
        assert result['exists_count']==0
