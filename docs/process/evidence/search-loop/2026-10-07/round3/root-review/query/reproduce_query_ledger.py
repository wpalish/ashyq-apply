"""Offline production query-ledger reproduction; no real provider, DB or Fetcher."""
from __future__ import annotations
import asyncio
import ast
from datetime import UTC, datetime
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import time

from app.adapters.base import Candidate
from app.adapters.discovery import live_discovery as discovery
from app.adapters.discovery.live_discovery import DiscoveryTrace, PageCategory
from app.adapters.search import _ThrottleLatch
from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable
from app.adapters.search import intent
from app.catalogue import discovery as catalogue
from app.schemas.profile import ApplicantProfileIn
from evaluation.research.live import _ExpertBudget

BASE=Path(__file__).resolve().parent
REPO=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
STOP=REPO.parent/'development-STOP.json'
SOURCE_FILES=[
 'backend/app/catalogue/discovery.py','backend/app/adapters/discovery/live_discovery.py',
 'backend/app/adapters/search/__init__.py','backend/app/adapters/search/base.py',
 'backend/app/adapters/search/intent.py','backend/app/adapters/search/retrieval.py',
 'backend/app/adapters/search/exa.py','backend/app/adapters/requirements/web_requirements.py',
 'backend/app/adapters/scholarship/web_scholarships.py','backend/app/pipeline/runner.py',
 'backend/evaluation/research/live.py',
]

def hashfile(p):
 return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def profile(fields):
 return ApplicantProfileIn.model_validate({'context':{'level':'bachelor','intended_fields':fields,'intake_year':2027,'citizenship':'KZ','country_of_residence':'KZ','education_country':'KZ','education_system':'KZ'}})

class CountingVendor:
 name='exa'
 def __init__(self, identity=True, failed=False):
  self.calls=[]; self.identity=identity; self.failed=failed
 async def search(self, *, query, domains=(), max_results=10):
  self.calls.append({'query':query,'domains':list(domains),'max_results':max_results})
  now=datetime(2026,10,7,tzinfo=UTC)
  is_identity='official university website' in query
  if self.failed and is_identity:
   raise SearchUnavailable('synthetic refusal',http_status=500)
  results=(SearchResult(url='https://discovered.example.edu/',title='Example University',provider=self.name,rank=1,retrieved_at=now),) if is_identity and self.identity else ()
  return SearchResponse(query=query,provider=self.name,retrieved_at=now,results=results)

class StrictOnlyWrapper:
 name='exa'
 def __init__(self,inner):
  self.inner=inner
  self.budget=_ExpertBudget(60,120.0,'exa',time.monotonic())
  self.attempts=[]
 async def search(self, *, query, domains=(), max_results=10):
  self.attempts.append(query)
  self.budget.before_search(self.name)
  return await self.inner.search(query=query,domains=domains,max_results=max_results)

async def case(name, *, fields=None, seed_success=False, registry=False, identity_success=True, identity_error=False, strict=False, initial_trace_count=0):
 fields=fields or ['Computer Science']
 vendor=CountingVendor(identity_success,identity_error)
 guarded=StrictOnlyWrapper(vendor) if strict else vendor
 # The normal production throttle latch is retained in both factories.
 def factory(): return _ThrottleLatch(guarded)
 fetcher=SimpleNamespace(get=AsyncMock(side_effect=AssertionError('Unexpected page read: offline reproduction must not reach Fetcher')))
 adapter=catalogue.CatalogueDiscoveryAdapter(fetcher,session=SimpleNamespace(),university_ids=['synthetic'],live_limit=1)
 adapter.sitemaps.collect=AsyncMock()
 adapter._navigation_fallback=AsyncMock()
 adapter._confirm_programs=AsyncMock()
 adapter._walk_catalogs=AsyncMock()
 adapter._confirm_added_programs=AsyncMock()
 entry={'name':'Example University','country':'Test Country','city':'Test City','homepage':'https://discovered.example.edu/'}
 probes=[]
 async def probe(uni,url):
  probes.append(url)
  if seed_success or (identity_success and url=='https://discovered.example.edu/'):
   return dict(entry)
  return None
 adapter._probe_site=probe
 uni=SimpleNamespace(id='synthetic',name='Example University',aliases=['Example University'],domain='example.edu',country='Test Country',city='Test City',registry_entry=dict(entry) if registry else None,seed_snapshot={'record':{'official_site':'http://www.example.edu/'}})
 upstream=DiscoveryTrace(institution=uni.name,domain=uni.domain)
 upstream.search_queries_sent=initial_trace_count
 candidate=Candidate(name=uni.name,country=uni.country,city=uni.city)
 with patch.object(catalogue,'get_search_provider',factory),patch('app.adapters.search.get_search_provider',factory):
  found,trace=await adapter._enrich(uni,profile(fields),candidate,upstream)
 result={'name':name,'fields':fields,'shared_query_budget':intent.SHARED_QUERY_BUDGET,'default_query_budget':intent.DEFAULT_QUERY_BUDGET,'actual_offline_vendor_calls':len(vendor.calls),'identity_vendor_calls':sum('official university website' in q['query'] for q in vendor.calls),'programme_vendor_calls':sum('official university website' not in q['query'] for q in vendor.calls),'upstream_trace_search_queries_sent':upstream.search_queries_sent,'returned_trace_is_upstream':trace is upstream,'returned_trace_search_queries_sent':trace.search_queries_sent,'candidate_search_queries_used':found.search_queries_used,'trace_search_counter_serialized':'search_queries_sent' in trace.as_dict(),'programme_count':len(found.programs),'probe_urls':probes,'queries':vendor.calls,'returned_trace':trace.as_dict(),'fetcher_calls':fetcher.get.await_count,'downstream_stages':{'sitemaps':adapter.sitemaps.collect.await_count,'navigation':adapter._navigation_fallback.await_count,'walker':adapter._walk_catalogs.await_count}}
 if strict:
  result['strict_guard']={'attempts':len(guarded.attempts),'sent_count':guarded.budget.search_queries,'blocked_count':guarded.budget.blocked_search_queries,'stop_reason':guarded.budget.stop_reason,'provider_failure':guarded.budget.provider_failure}
 return result

async def planner_case(name, fields, initial_count):
 vendor=CountingVendor(identity=False)
 adapter=catalogue.CatalogueDiscoveryAdapter(SimpleNamespace(get=AsyncMock(side_effect=AssertionError('No Fetcher allowed'))),session=SimpleNamespace(),university_ids=['synthetic'],live_limit=1)
 adapter._search_provider=_ThrottleLatch(vendor)
 adapter._search_provider_resolved=True
 trace=DiscoveryTrace(institution='Example University',domain='example.edu')
 trace.search_queries_sent=initial_count
 selected={c:[] for c in PageCategory.ALL}
 await adapter._add_search_results({'name':'Example University'},'example.edu',selected,trace,profile(fields))
 return {'name':name,'fields':fields,'initial_count':initial_count,'remaining_under_existing_six_query_contract':max(0,intent.DEFAULT_QUERY_BUDGET-initial_count),'new_fake_vendor_calls':len(vendor.calls),'returned_trace_search_queries_sent':trace.search_queries_sent,'queries':vendor.calls}

async def main():
 before={n:hashfile(REPO/n) for n in SOURCE_FILES};stop_before=hashfile(STOP)
 cases=[]
 specs=[('registry_control',{'registry':True}),('seed_identity_control',{'seed_success':True}),('identity_then_single_field',{}),('identity_then_multifield',{'fields':['Computer Science','Mathematics']}),('identity_unknown',{'identity_success':False}),('identity_provider_error',{'identity_error':True}),('identity_plus_strict_evaluation_guard',{'strict':True}),('precounted_upstream_trace_is_discarded',{'initial_trace_count':1})]
 for name,kwargs in specs: cases.append(await case(name,**kwargs))
 by={c['name']:c for c in cases}
 assert by['registry_control']['actual_offline_vendor_calls']==6
 assert by['seed_identity_control']['actual_offline_vendor_calls']==6
 for name in ['identity_then_single_field','identity_then_multifield','precounted_upstream_trace_is_discarded']:
  c=by[name]; assert c['actual_offline_vendor_calls']==7 and c['returned_trace_search_queries_sent']==6 and c['candidate_search_queries_used']==6
 for name in ['identity_unknown','identity_provider_error']:
  c=by[name]; assert c['actual_offline_vendor_calls']==1 and c['returned_trace_search_queries_sent']==0 and c['candidate_search_queries_used']==0
 c=by['identity_plus_strict_evaluation_guard']; assert c['actual_offline_vendor_calls']==6 and c['strict_guard']['blocked_count']==1 and c['strict_guard']['stop_reason']=='search_budget_exhausted' and c['strict_guard']['provider_failure'] is None
 assert any('Search service unavailable' in f for f in c['returned_trace']['search_failures'])
 planner_controls=[await planner_case('single_field_precharged_one',['Computer Science'],1),await planner_case('multifield_precharged_one',['Computer Science','Mathematics'],1),await planner_case('already_exhausted',['Computer Science'],6)]
 for c in planner_controls: assert c['new_fake_vendor_calls']==6 and c['returned_trace_search_queries_sent']==c['initial_count']+6
 after={n:hashfile(REPO/n) for n in SOURCE_FILES};assert before==after;assert stop_before==hashfile(STOP)
 targets={'backend/app/catalogue/discovery.py':['CatalogueDiscoveryAdapter._enrich','CatalogueDiscoveryAdapter._identify_site'],'backend/app/adapters/discovery/live_discovery.py':['LiveDiscoveryAdapter._discover_one','LiveDiscoveryAdapter._add_search_results','LiveDiscoveryAdapter._add_multi_field_search_results','LiveDiscoveryAdapter._apply','DiscoveryTrace.as_dict'],'backend/app/adapters/search/__init__.py':['_ThrottleLatch.search','get_search_provider'],'backend/app/adapters/search/retrieval.py':['discover_candidates'],'backend/evaluation/research/live.py':['_ExpertBudget.before_search']}
 function_records={}
 for path,wanted in targets.items():
  src=(REPO/path).read_text();lines=src.splitlines(keepends=True);tree=ast.parse(src)
  def walk(nodes,prefix=''):
   for node in nodes:
    if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
     q=prefix+node.name
     if q in wanted:
      function_records[path+'::'+q]={'line':node.lineno,'end_line':node.end_lineno,'sha256':hashlib.sha256(''.join(lines[node.lineno-1:node.end_lineno]).encode()).hexdigest()}
     if isinstance(node,ast.ClassDef):walk(node.body,q+'.')
  walk(tree.body)
 payload={'source_sha_before':before,'source_sha_after':after,'source_unchanged':True,'source_functions':function_records,'shared_stop_before':stop_before,'shared_stop_after':hashfile(STOP),'shared_stop_unchanged':True,'frozen_commit_owner_report':'d669fd2; no Git command run by reviewer','network_calls':0,'real_vendor_calls':0,'git_calls':0,'all_assertions_passed':True,'reproduction_scope':'Actual production _enrich/_identify_site/_discover_one/_add_search_results/discover_candidates/_apply and real _ThrottleLatch; identity probes and unrelated sitemap/navigation/confirmation/walker IO mocked; vendor/session fake; strict case additionally actual local _ExpertBudget.before_search','cases':cases,'planner_precharge_controls':planner_controls}
 (BASE/'query-ledger-reproduction.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'all_assertions_passed':True,'case_count':len(cases),'counts':[{k:c[k] for k in ['name','actual_offline_vendor_calls','upstream_trace_search_queries_sent','returned_trace_search_queries_sent','candidate_search_queries_used']} for c in cases],'source_sha':before,'network_calls':0},indent=2))

if __name__=='__main__':asyncio.run(main())
