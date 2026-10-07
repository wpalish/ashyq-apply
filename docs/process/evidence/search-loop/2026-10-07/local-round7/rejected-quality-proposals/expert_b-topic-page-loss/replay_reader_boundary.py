"""Actual frozen verify path, one retained official page; permission diagnostic only."""
from pathlib import Path
import asyncio, json, sys, socket, subprocess, hashlib
from dataclasses import replace, asdict
from datetime import datetime
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SOURCE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261007T220539Z-live-6d0aa77b/source/backend')
def denied(*a, **kw):raise AssertionError('offline external action denied')
socket.getaddrinfo=denied;socket.create_connection=denied
subprocess.Popen=denied;subprocess.run=denied;subprocess.check_output=denied
sys.path.insert(0,str(SOURCE))
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import FetchResult, FetchOutcome
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.requirements import web_requirements as req
from app.domain.enums import DegreeLevel

class RetainedFetcher:
    def __init__(self, row):self.row=row;self.calls=[]
    async def get(self,url,**kwargs):
        self.calls.append(url)
        assert url==self.row['url'], 'No additional page reads allowed in isolated reader control'
        body=Path(self.row['body_owned']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==self.row['body_sha256']
        meta=json.loads(Path(self.row['meta_owned']).read_text())
        return FetchResult(url=url,outcome=FetchOutcome.OK,status_code=meta['status_code'],
            content=body,text=body.decode(meta['encoding']),content_type=meta['content_type'],
            final_url=meta['final_url'],fetched_at=datetime.fromisoformat(meta['fetched_at']),
            content_hash=meta['content_hash'],from_cache=True)

async def one(row, force=False):
    fetcher=RetainedFetcher(row)
    adapter=req.WebRequirementsAdapter(fetcher,'2027/28')
    candidate=Candidate(name='University of Toronto',country='Canada',city='Toronto',
        domain='utoronto.ca',admissions_url=row['url'],search_queries_used=6)
    program=CandidateProgram(name='Computer Science',field='computer science',degree=DegreeLevel.BACHELOR,url=None)
    def diagnostic(**kwargs):
        p=classify_page(**kwargs)
        return replace(p,page_type=PageType.GENERAL_ADMISSIONS,signals=[*p.signals,'DIAGNOSTIC force permission only']) if force and p.page_type==PageType.UNKNOWN else p
    with patch.object(req,'classify_page',diagnostic),patch.object(req,'_language_links',lambda *a,**kw:[]),patch.object(req,'_route_links',lambda *a,**kw:[]):
        result=await adapter.verify(candidate,program,'Fall 2027')
    return {'url':row['url'],'force_unknown_to_general_admissions_DIAGNOSTIC_NOT_RULE':force,
        'fetcher_calls':fetcher.calls,'outcomes':[asdict(x) for x in result.page_outcomes],
        'claims':[x.model_dump(mode='json') for x in result.claims],'errors':result.errors,
        'followups_disabled_for_isolated_reader_boundary':True,'source_text_and_all_extractors_unchanged':True}

async def main():
    rows=json.loads((BASE/'original-cache-receipt.json').read_text())['pages']
    targets=[r for r in rows if 'english-language' in r['url'] or r['url'].endswith('deadlines')]
    controls=[r for r in rows if r['url'].endswith('/apply') or r['url'].endswith('/computer-science')]
    result=[]
    for row in targets+controls:
        result.extend([await one(row),await one(row,True)])
    (BASE/'reader-boundary.offline.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    for row in result:
        print(json.dumps({'url':row['url'],'forced':row['force_unknown_to_general_admissions_DIAGNOSTIC_NOT_RULE'],
            'outcomes':[(o['category'],o['page_type']) for o in row['outcomes']],
            'claims':[(c['claim_type'],c.get('payload'),c.get('scope')) for c in row['claims']]},default=str))
if __name__=='__main__':asyncio.run(main())
