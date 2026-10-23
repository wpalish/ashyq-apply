"""Own current-app support. Only pinned candidate modules are spec-loaded."""
from pathlib import Path
import asyncio, importlib.util, json, sys, socket, hashlib
from dataclasses import asdict, replace
from datetime import UTC, datetime
from unittest.mock import patch
import httpx
BASE=Path(__file__).resolve().parent
ORIGIN=BASE.parent.parent/'local-round8/b-ielts-section-proposal-v3'
REPO=BASE.parent.parent/'ashyq-apply/backend'
sys.path.insert(0,str(REPO))
def denied(*a,**k): raise AssertionError('offline candidate denies HTTP/DNS/provider/model')
socket.getaddrinfo=denied;socket.create_connection=denied
httpx.Client.request=denied;httpx.AsyncClient.request=denied
from app.adapters.requirements import web_requirements as actual
from app.adapters.base import Candidate,CandidateProgram
from app.adapters.fetching import FetchResult
from app.adapters.page_classifier import classify_page,PageType
from app.adapters.extraction import readable_text
from app.domain.enums import FetchOutcome,DegreeLevel
DIAGNOSTIC_OVERRIDES=[]

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
 return module
extraction=load('app.adapters.extraction',BASE/'proposed/app/adapters/extraction.py')
helper=load('app.adapters.requirements.ielts_sections',BASE/'proposed/app/adapters/requirements/ielts_sections.py')
shadow=load('independent_ielts_v4_web_requirements',BASE/'proposed/app/adapters/requirements/web_requirements.py')
ROWS=json.loads((ORIGIN/'retained-receipt.json').read_text())['pages']
# Read-only unchanged origin dataset needed by author tests. No output writer.
assert (BASE/'root-controls.original.json').is_file()

class ReaderFetcher:
 def __init__(self,url,html,final_url,fetched_at,pdf_text):
  self.url=url;self.html=html;self.final_url=final_url or url;self.fetched_at=fetched_at or datetime(2026,10,8,tzinfo=UTC);self.pdf_text=pdf_text;self.calls=[]
 async def get(self,url,**kwargs):
  self.calls.append(url);assert url==self.url,'one-page isolated reader rejects secondary URL'
  return FetchResult(url=url,final_url=self.final_url,outcome=FetchOutcome.OK,status_code=200,text=self.html,content=b'%PDF-synthetic' if self.pdf_text is not None else self.html.encode(),content_type='application/pdf' if self.pdf_text is not None else 'text/html',fetched_at=self.fetched_at,from_cache=True)

async def read(url,html,*,on=False,old=False,diagnostic=False,final_url=None,fetched_at=None,domain='utoronto.ca',pdf_text=None,language_follow=False):
 module=actual if old else shadow
 fetcher=ReaderFetcher(url,html,final_url,fetched_at,pdf_text)
 candidate=Candidate(name='Independent retained institution',country='Synthetic caller context',city='',domain=domain,admissions_url=url,search_queries_used=6)
 programme=CandidateProgram(name='Computer Science',field='computer science',degree=DegreeLevel.BACHELOR,url=None)
 def classify(**kw):
  original=classify_page(**kw)
  if diagnostic and original.page_type==PageType.UNKNOWN:
   DIAGNOSTIC_OVERRIDES.append({'url':url,'original':'unknown','diagnostic_only':True})
   return replace(original,page_type=PageType.GENERAL_ADMISSIONS)
  return original
 target_class=module._Target
 def target(*a,**kw):
  if language_follow:kw['language_follow']=True
  return target_class(*a,**kw)
 with patch.object(module,'classify_page',classify),patch.object(module,'_language_links',lambda *a,**kw:[]),patch.object(module,'_route_links',lambda *a,**kw:[]),patch.object(module,'pdf_to_text',lambda *a:pdf_text),patch.object(module,'_Target',target):
  if not old:module.IELTS_PROSE_SECTION_OWNERSHIP=on
  out=await module.WebRequirementsAdapter(fetcher,'2027/28').verify(candidate,programme,'Fall 2027')
 return {'claims':[c.model_dump(mode='json') for c in out.claims],'page_outcomes':[asdict(o) for o in out.page_outcomes],'errors':out.errors,'pages_checked':out.pages_checked,'pages_failed':out.pages_failed,'fetcher_calls':fetcher.calls}

async def retained(row,**kw):
 body=Path(row['body_owned']).read_bytes();meta_path=Path(row['meta_owned']);assert hashlib.sha256(body).hexdigest()==row['body_sha256'];assert hashlib.sha256(meta_path.read_bytes()).hexdigest()==row['meta_sha256']
 meta=json.loads(meta_path.read_text());domain='tudelft.nl' if 'tudelft.nl' in row['url'] else 'utoronto.ca'
 return await read(row['url'],body.decode(meta['encoding']),domain=domain,final_url=meta['final_url'],fetched_at=datetime.fromisoformat(meta['fetched_at']),**kw)
