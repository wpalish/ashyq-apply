"""Offline expert07 reproduction; writes only group-07.rows.json beside this file."""
from __future__ import annotations
import asyncio
from datetime import datetime, UTC
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db import create_all_for_tests
from app.models import University
from app.catalogue.importer import import_catalogue, canonical_name
from app.catalogue.retrieval import retrieve
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.adapters.discovery.live_discovery import DiscoveryTrace, PageCategory
from app.adapters.fetching import FetchOutcome, FetchResult
from app.adapters.search.base import SearchUnavailable, SearchResponse
from app.schemas.profile import ApplicantProfileIn

logging.disable(logging.CRITICAL)
PROFILE = ApplicantProfileIn.model_validate({'context': {'level':'bachelor', 'intended_fields':['computer science'], 'intake_year':2027, 'citizenship':'Kazakhstan', 'country_of_residence':'Kazakhstan', 'education_country':'Kazakhstan', 'education_system':'KZ national secondary'}})

class OfflineFetcher:
    def __init__(self): self.calls=[]
    async def get(self, url, **kwargs):
        self.calls.append(url)
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR)

class OfflineProvider:
    name='fake'
    def __init__(self, fail=True): self.calls=[]; self.fail=fail
    async def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail: raise SearchUnavailable('synthetic vendor body must not escape', http_status=429)
        return SearchResponse(results=[], provider='fake', query=kwargs['query'], retrieved_at=datetime.now(UTC))

def query_test(session, query, uid):
    found=retrieve(session, query=query)
    return {'query':query, 'hit_count':len(found), 'contains_target':any(u.id==uid for u in found), 'target_rank':next((i+1 for i,u in enumerate(found) if u.id==uid),None), 'names':[u.name for u in found[:8]]}

async def main():
    packet=json.loads(Path(__file__).with_name('group-07.packet.json').read_text())
    engine=create_engine('sqlite://')
    create_all_for_tests(engine)
    with Session(engine) as session:
        imported=import_catalogue(session); session.commit()
        allrows=list(session.scalars(select(University)))
        byseed={(u.seed_snapshot or {}).get('record',{}).get('seed_id'):u for u in allrows}
        full_order=retrieve(session)
        selected=[byseed[r['seed_id']] for r in packet['universities']]
        ids=[u.id for u in selected]
        selected_order=retrieve(session, university_ids=ids)
        ranks={u.id:i+1 for i,u in enumerate(full_order)}
        selected_ranks={u.id:i+1 for i,u in enumerate(selected_order)}
        result=[]
        for seed in packet['universities']:
            uni=byseed[seed['seed_id']]
            variants=[('seed_exact', seed['name']), ('canonical', canonical_name(seed['name'])), ('case_whitespace', '  '+uni.name.upper()+'  '), ('accent_folded', ''.join(c for c in unicodedata.normalize('NFKD',uni.name) if not unicodedata.combining(c))), ('punctuation_folded', re.sub(r'[^\w\s]',' ',uni.name))]
            variants.extend(('alias',a) for a in uni.aliases or [])
            queries=[dict(kind=k,**query_test(session,q,uni.id)) for k,q in variants]
            # Real _enrich -> real _discover_one. Site identification replaced ONLY
            # to make missing/unreachable-domain rows enter the same cancellable stage.
            fetcher=OfflineFetcher()
            adapter=CatalogueDiscoveryAdapter(fetcher,session=session,university_ids=[uni.id],live_limit=1)
            domain=uni.domain or 'example.edu'
            entry=uni.registry_entry or {'name':uni.name,'country':uni.country,'homepage':f'https://{domain}/'}
            async def identify(u,t): return entry
            adapter._identify_site=identify
            observed=[]
            async def collect(homepage, host, inner_trace, keep):
                inner_trace.sitemaps_read.append(homepage+'synthetic-sitemap.xml')
                inner_trace.search_failures.append('synthetic inner progress marker')
                observed.append(inner_trace)
                await asyncio.Event().wait()
            adapter.sitemaps.collect=collect
            real_wait_for=asyncio.wait_for
            recorded_timeouts=[]
            async def short_wait(awaitable, timeout):
                recorded_timeouts.append(timeout)
                return await real_wait_for(awaitable, timeout=0.002)
            with patch('app.catalogue.discovery.asyncio.wait_for', short_wait):
                candidates=await adapter.discover(PROFILE)
            timeout_result={'kind':'synthetic cancellation after real inner trace mutation', 'production_timeout_argument':recorded_timeouts, 'injected_timeout_seconds':0.002, 'retained_candidate_count':len(candidates), 'inner_progress_written':bool(observed and observed[0].sitemaps_read), 'outer_sitemaps_read':adapter.traces[0].sitemaps_read, 'outer_failures':adapter.traces[0].search_failures, 'timeout_reported':any('time limit' in e for e in adapter.traces[0].errors), 'facts_invented':bool(candidates[0].programs)}
            # Repeated 429 handling through actual single-field search integration.
            provider=OfflineProvider()
            trace=DiscoveryTrace(institution=uni.name, domain=domain)
            selected_pages={c:[] for c in PageCategory.ALL}
            selected_pages[PageCategory.PROGRAM_PAGE]=[f'https://{domain}/synthetic-existing-programme']
            with patch('app.adapters.search.get_search_provider',lambda:provider):
                await adapter._add_search_results(entry,domain,selected_pages,trace,PROFILE)
            outage={'kind':'synthetic repeated HTTP429; no real quota tested', 'domain_is_placeholder':not bool(uni.domain), 'provider_calls':len(provider.calls), 'diagnostics':trace.search_failures, 'existing_page_retained':f'https://{domain}/synthetic-existing-programme' in selected_pages[PageCategory.PROGRAM_PAGE], 'raw_body_redacted':'synthetic vendor body' not in str(trace.as_dict())}
            # Actual identity gate on original seed hints under unavailable pages/provider.
            identity=None
            if not uni.registry_entry:
                identity_provider=OfflineProvider(); identity_fetch=OfflineFetcher()
                identity_adapter=CatalogueDiscoveryAdapter(identity_fetch,session=session,university_ids=[uni.id],live_limit=1)
                with patch('app.catalogue.discovery.get_search_provider',lambda:identity_provider):
                    found=await identity_adapter.discover(PROFILE)
                identity={'candidate_retained':len(found)==1, 'programme_count':len(found[0].programs), 'hint_reads':len(identity_fetch.calls), 'provider_calls':len(identity_provider.calls), 'limitations':identity_adapter.traces[0].search_limitations}
            fullrank=ranks[uni.id]; grouprank=selected_ranks[uni.id]
            result.append({'seed_id':seed['seed_id'],'name':seed['name'],'catalogue_id':uni.id,'canonical_name':uni.name,'aliases':uni.aliases,'live_checked':False,'route':'curated' if uni.registry_entry else 'generic_identity','domain':uni.domain,'official_site_hint':seed.get('official_site'),'queries':queries,'tests':{'timeout_progress':timeout_result,'repeated_429':outage,'identity_outage':identity}, 'scheduling':{'unfiltered_rank_in_501':fullrank,'default_candidate_selected':fullrank<=40,'default_live_selected':fullrank<=20,'rank_when_group50_selected':grouprank,'group50_live20_selected':grouprank<=20}, 'observations':['Real importer/retrieval exercised against 501 entries.', 'Synthetic timeout retains candidate but loses inner progress.', 'Synthetic HTTP429 preserves existing programme URL.'], 'risk':'Progress loss on timeout; deterministic budget exclusion when rank exceeds live limit; repeated outage queries. Missing hints are unverified availability limitations, not confirmed wrong facts.'})
        # Controlled scheduling: reversal of caller selection does not change recipients.
        schedules=[]
        for selection in (ids,list(reversed(ids))):
            adapter=CatalogueDiscoveryAdapter(OfflineFetcher(),session=session,university_ids=selection,live_limit=20)
            attempted=[]
            async def enrich(u,p,c,t): attempted.append(u.id); return c,t
            adapter._enrich=enrich
            got=await adapter.discover(PROFILE,50)
            schedules.append({'attempted':attempted,'candidate_count':len(got),'skipped_trace_limitations':[t.search_limitations for t in adapter.traces[20:]]})
        # Completion negative control: inner trace is retained when _discover_one returns.
        uni=selected[0]
        adapter=CatalogueDiscoveryAdapter(OfflineFetcher(),session=session,university_ids=[uni.id],live_limit=1)
        async def identify(u,t): return {'name':uni.name,'country':uni.country,'homepage':'https://example.edu/'}
        adapter._identify_site=identify
        async def completed(e,p):
            from app.adapters.base import Candidate
            return Candidate(name=uni.name,country=uni.country,city=uni.city), DiscoveryTrace(institution=uni.name,domain='example.edu',sitemaps_read=['synthetic-completed'])
        adapter._discover_one=completed
        await adapter.discover(PROFILE)
        success_trace=adapter.traces[0].sitemaps_read
        # No provider failure negative control with same six-query budget.
        provider=OfflineProvider(False)
        from app.adapters.search.retrieval import discover_candidates
        from app.adapters.search.intent import DiscoveryIntent
        with patch.object(provider,'search', provider.search):
            report=await discover_candidates(provider,DiscoveryIntent(institution=uni.name,domain='example.edu',degree='bachelor',field='computer science'),hop_entry_points=0)
        # Historical captures are read only and not current proof.
        history_path=ROOT/'backend/evaluation/research/expert/data/runs.2026-10-02/baseline.capture.json'
        history=json.loads(history_path.read_text())
        history_summary={'path':str(history_path.relative_to(ROOT)),'captured_at':history.get('captured_at'),'pipeline_sha':history.get('pipeline_sha'),'config_seconds_per_case':history['config']['seconds_per_case'],'config_max_network_reads':history['config']['max_network_reads'],'timeout_detail_occurrences':history_path.read_text().count('timeout — host stopped responding earlier in this run')}
        summary={'group':7,'audited':len(result),'catalogue_rows':len(allrows),'import_result':imported,'curated':sum(r['route']=='curated' for r in result),'generic':sum(r['route']!='curated' for r in result),'missing_domain':sum(not r['domain'] for r in result),'query_tests':sum(len(r['queries']) for r in result),'exact_ambiguous':sum(r['queries'][0]['hit_count']>1 for r in result),'exact_target_hits':sum(r['queries'][0]['contains_target'] for r in result),'canonical_target_hits':sum(r['queries'][1]['contains_target'] for r in result),'query_variants_missed':sum(not q['contains_target'] for r in result for q in r['queries']),'timeout_progress_loss':sum(r['tests']['timeout_progress']['inner_progress_written'] and not r['tests']['timeout_progress']['outer_sitemaps_read'] for r in result),'outage_provider_call_counts':sorted(set(r['tests']['repeated_429']['provider_calls'] for r in result)),'default_candidate_selected':sum(r['scheduling']['default_candidate_selected'] for r in result),'default_live_selected':sum(r['scheduling']['default_live_selected'] for r in result),'group50_live20_selected':20,'live_checked':0,'nominal_discovery_timeout_allotment_default_seconds':300*20,'nominal_discovery_timeout_allotment_50_seconds':300*50,'bounds_note':'Timeout allotment only, not measured duration or strict upper bound: cancellation cleanup and synchronous work may overrun, and later pipeline stages add time.'}
        assert len(result)==50 and len(allrows)==501
        assert summary['timeout_progress_loss']==50
        assert all(r['tests']['timeout_progress']['retained_candidate_count']==1 and r['tests']['timeout_progress']['timeout_reported'] and not r['tests']['timeout_progress']['facts_invented'] for r in result)
        assert all(r['tests']['repeated_429']['provider_calls']==6 and r['tests']['repeated_429']['existing_page_retained'] and r['tests']['repeated_429']['raw_body_redacted'] for r in result)
        assert all(r['tests']['identity_outage']['candidate_retained'] and r['tests']['identity_outage']['programme_count']==0 for r in result if r['tests']['identity_outage'])
        output={'summary':summary,'negative_controls':{'all50_retained_in_selected_run':schedules[0]['candidate_count']==50,'selection_reversal_same_live_recipients':schedules[0]['attempted']==schedules[1]['attempted'],'skipped30_have_empty_limitations':all(not x for x in schedules[0]['skipped_trace_limitations']),'completed_inner_trace_retained':success_trace,'empty_success_provider_calls':len(provider.calls),'empty_success_failed_queries':len(report.failed_queries)},'historical_context':history_summary,'universities':result}
        Path(__file__).with_name('group-07.rows.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'summary':summary,'negative_controls':output['negative_controls'],'historical_context':history_summary},ensure_ascii=False,indent=2))
    engine.dispose()

if __name__=='__main__': asyncio.run(main())
