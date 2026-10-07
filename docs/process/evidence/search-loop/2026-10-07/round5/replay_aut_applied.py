"""Actual retained AUT bytes through original and external-proposal readers."""
import asyncio
import hashlib
import inspect
import json
import re
import socket
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.discovery import live_discovery as discovery
from app.adapters.fetching import Fetcher
from app.adapters.requirements import web_requirements as requirements
from app.domain.enums import ClaimType, DegreeLevel
from tests.test_live_discovery import StubSite

ROOT=Path(__file__).resolve().parent
CACHE=ROOT.parent/'search-loop-round2/pair-temp/on1'
pages={}
for meta_path in CACHE.glob('*/cache/**/*.meta.json'):
    meta=json.loads(meta_path.read_text());url=meta.get('url','')
    if not any(term in url for term in ('data-science-major-bachelor','computer-science-major-bachelor')):
        continue
    body=meta_path.with_name(meta_path.name.replace('.meta.json','.body'))
    if body.is_file():
        pages[url]=body.read_bytes()
assert len(pages)==2
original=discovery.matches_field_text
proposal=original

def no_network(*args,**kwargs):
    raise AssertionError('Offline original-page replay attempted network')

async def main():
    result=[]
    for flag,matcher in [(False,original),(True,proposal),(True,proposal),(False,original)]:
        with tempfile.TemporaryDirectory() as temp:
            async with Fetcher(Path(temp)/'cache',offline=True) as fetcher:
                StubSite(pages).install(fetcher)
                adapter=requirements.WebRequirementsAdapter(fetcher,'2027/28')
                adapter._find_topic_pages=AsyncMock(return_value=[])
                for url,body in pages.items():
                    candidate=Candidate(name='Auckland University of Technology',country='New Zealand',city='Auckland',domain='aut.ac.nz')
                    programme=CandidateProgram(name=discovery._program_name_from_url(url,['computer science'],DegreeLevel.BACHELOR),field='computer science',degree=DegreeLevel.BACHELOR,url=url)
                    with patch.object(discovery,'SUBJECT_PHRASE_MATCH',flag),patch.object(discovery,'matches_field_text',matcher),patch.object(requirements,'matches_field_text',matcher),patch.object(socket.socket,'connect',no_network),patch.object(socket,'create_connection',no_network):
                        observed=await adapter.verify(candidate,programme,'fall2027')
                    claims=[c for c in observed.claims if c.claim_type==ClaimType.PROGRAM_EXISTS]
                    result.append(dict(proposal_enabled=flag,url=url,body_sha256=hashlib.sha256(body).hexdigest(),
                        discovery_name=programme.name,exists_count=len(claims),errors=observed.errors,
                        existence_proofs=[dict(value=c.normalized_value,excerpt=c.original_text_excerpt) for c in claims]))
    (ROOT/'aut-major.reader-replay.parent-applied.json').write_text(json.dumps(dict(rows=result,network_actions=0,source_edited=False,proposal_only=False,applied_source_sha256=hashlib.sha256(Path(discovery.__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps([dict(proposal=r['proposal_enabled'],url=r['url'].split('/')[-1],exists_count=r['exists_count']) for r in result],indent=2))

asyncio.run(main())
