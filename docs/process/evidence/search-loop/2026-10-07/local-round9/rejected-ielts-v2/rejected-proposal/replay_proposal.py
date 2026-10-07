"""External actual-caller shadow; all external actions refused before imports."""
from pathlib import Path
import asyncio, importlib.util, json, sys, socket, subprocess, hashlib
from dataclasses import asdict, replace
from datetime import datetime, timezone
from unittest.mock import patch

BASE=Path(__file__).resolve().parent
SOURCE=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261007T220539Z-live-6d0aa77b/source/backend')
def denied(*a,**kw):raise AssertionError('external replay forbids network/DNS/provider/model/process')
socket.getaddrinfo=denied;socket.create_connection=denied
subprocess.Popen=denied;subprocess.run=denied;subprocess.check_output=denied
sys.path.insert(0,str(SOURCE))
from app.adapters.requirements import web_requirements as frozen
from app.adapters.base import Candidate,CandidateProgram
from app.adapters.fetching import FetchOutcome,FetchResult
from app.adapters.page_classifier import classify_page,PageType
from app.adapters.extraction import readable_text
from app.domain.enums import DegreeLevel
import app.adapters.requirements


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module
shadow_extraction=load('app.adapters.extraction',BASE/'proposed/app/adapters/extraction.py')
helper=load('app.adapters.requirements.ielts_sections',BASE/'proposed/app/adapters/requirements/ielts_sections.py')
shadow=load('external_shadow_web_requirements',BASE/'proposed/app/adapters/requirements/web_requirements.py')
ROWS=json.loads((BASE/'retained-receipt.json').read_text())['pages']

class ReaderFetcher:
    def __init__(self,url,html,final_url=None,fetched_at=None,pdf_text=None):
        self.url=url;self.html=html;self.final_url=final_url or url;self.calls=[];self.pdf_text=pdf_text
        self.fetched_at=fetched_at or datetime(2026,10,7,tzinfo=timezone.utc)
    async def get(self,url,**kw):
        self.calls.append(url);assert url==self.url,'isolated one-page reader forbids more reads'
        return FetchResult(url=url,outcome=FetchOutcome.OK,status_code=200,
            content=b'%PDF-external-fixture' if self.pdf_text is not None else self.html.encode(),text=self.html,content_type='application/pdf' if self.pdf_text is not None else 'text/html',
            final_url=self.final_url,fetched_at=self.fetched_at,from_cache=True)

async def read(url,html,*,on=False,old=False,diagnostic=False,final_url=None,fetched_at=None,domain='utoronto.ca',pdf_text=None,language_follow=False):
    module=frozen if old else shadow
    fetcher=ReaderFetcher(url,html,final_url,fetched_at,pdf_text)
    adapter=module.WebRequirementsAdapter(fetcher,'2027/28')
    candidate=Candidate(name='Retained institution',country='Synthetic caller context',city='',domain=domain,
        admissions_url=url,search_queries_used=6)
    programme=CandidateProgram(name='Computer Science',field='computer science',degree=DegreeLevel.BACHELOR,url=None)
    def classify(**kw):
        original=classify_page(**kw)
        return replace(original,page_type=PageType.GENERAL_ADMISSIONS) if diagnostic and original.page_type==PageType.UNKNOWN else original
    target_class=module._Target
    def target(*a,**kw):
        if language_follow:kw['language_follow']=True
        return target_class(*a,**kw)
    with patch.object(module,'classify_page',classify),patch.object(module,'_language_links',lambda *a,**kw:[]),patch.object(module,'_route_links',lambda *a,**kw:[]),patch.object(module,'pdf_to_text',lambda *a:pdf_text),patch.object(module,'_Target',target):
        if not old:module.IELTS_PROSE_SECTION_OWNERSHIP=on
        out=await adapter.verify(candidate,programme,'Fall 2027')
    return {'claims':[c.model_dump(mode='json') for c in out.claims],
        'page_outcomes':[asdict(o) for o in out.page_outcomes], 'errors':out.errors,
        'pages_checked':out.pages_checked,'pages_failed':out.pages_failed,'fetcher_calls':fetcher.calls}

async def retained(row,**kw):
    body=Path(row['body_owned']).read_bytes();assert hashlib.sha256(body).hexdigest()==row['body_sha256']
    meta=json.loads(Path(row['meta_owned']).read_text())
    domain='tudelft.nl' if 'tudelft.nl' in row['url'] else 'utoronto.ca'
    return await read(row['url'],body.decode(meta['encoding']),domain=domain,
        final_url=meta['final_url'],fetched_at=datetime.fromisoformat(meta['fetched_at']),**kw)

async def main():
    results=[]
    for row in ROWS:
        old=await retained(row,old=True);off=await retained(row,on=False);assert old==off,row['url']
        on=await retained(row,on=True)
        diagnostic_on=await retained(row,on=True,diagnostic=True) if 'english-language' in row['url'] else None
        results.append({'url':row['url'],'body_sha256':row['body_sha256'],'off_equals_frozen':True,
            'frozen':old,'off':off,'on':on,'diagnostic_on_not_production_gain':diagnostic_on})
    (BASE/'retained-replay.offline.json').write_text(json.dumps(results,indent=2)+'\n')
    for r in results:
        print(json.dumps({'url':r['url'],'off_equal':r['off_equals_frozen'],
            'on':[(c['claim_type'],c['normalized_value'],c['scope']) for c in r['on']['claims']],
            'diagnostic':[(c['claim_type'],c['normalized_value'],c['scope'],c['original_text_excerpt']) for c in r['diagnostic_on_not_production_gain']['claims']] if r['diagnostic_on_not_production_gain'] else None}))
if __name__=='__main__':asyncio.run(main())
