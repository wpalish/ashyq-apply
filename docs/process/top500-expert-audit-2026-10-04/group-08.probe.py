"""Offline audit: actual full catalogue and retrieval; all discovery transport synthetic."""
from __future__ import annotations
import asyncio
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db import create_all_for_tests
from app.models import University, UniversityObservation
from app.catalogue.importer import SEED_PATH, import_catalogue, identity_key
from app.catalogue.retrieval import retrieve
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import FetchResult
from app.domain.enums import FetchOutcome
from app.domain.dedupe import normalize
from app.schemas.profile import Preferences

OUT = Path(__file__).parent
PROFILE = SimpleNamespace(preferences=Preferences())


def query(s, uni, value):
    result = retrieve(s, query=value)
    ids = [u.id for u in result]
    return {'query': value, 'target_found': uni.id in ids, 'target_position': ids.index(uni.id)+1 if uni.id in ids else None,
            'result_count':len(ids), 'other_names':[u.name for u in result if u.id != uni.id][:8]}

async def run(s, ids, live_limit, limit):
    adapter = CatalogueDiscoveryAdapter(SimpleNamespace(), session=s, university_ids=ids, live_limit=live_limit)
    calls=[]
    async def stub(uni, profile, candidate, trace):
        calls.append(uni.id)
        return candidate, trace
    adapter._enrich=stub
    candidates=await adapter.discover(PROFILE, limit)
    return {'ids':[c.discovery_source.split(':',1)[1] for c in candidates], 'attempted':calls,
            'traces':[t.as_dict() for t in adapter.traces]}

async def main():
    packet=json.loads((OUT/'group-08.packet.json').read_text())
    engine=create_engine('sqlite://')
    create_all_for_tests(engine)
    with Session(engine) as s:
        counts=import_catalogue(s)
        s.commit()
        ordered=retrieve(s)
        bykey={u.identity_key:u for u in ordered}
        default=await run(s,None,20,40)
        rows=[]
        for seed in packet['universities']:
            uni=bykey[identity_key(seed['name'],seed['country'])]
            skipped=await run(s,[uni.id],0,1)
            attempted=await run(s,[uni.id],1,1)
            adapter=CatalogueDiscoveryAdapter(SimpleNamespace(),session=s,university_ids=[uni.id],live_limit=1)
            adapter._identify_site=AsyncMock(return_value=None)
            adapter._discover_one=AsyncMock(return_value=(Candidate(name=uni.name,country=uni.country,city=uni.city),DiscoveryTrace(institution=uni.name,domain=uni.domain or '')))
            await adapter.discover(PROFILE,1)
            route_trace=adapter.traces[0].as_dict()
            tests={k:query(s,uni,v) for k,v in {'exact_seed':seed['name'],'canonical':uni.name,'normalized':normalize(uni.name),'reordered':' '.join(reversed(uni.name.split()))}.items()}
            aliases=[query(s,uni,a) for a in uni.aliases]
            observations=['Offline catalogue retrieval completed; admissions and official domain correctness remain unverified.','Synthetic budget-skipped and attempted-empty enrichment serialize to identical traces.']
            if not uni.registry_entry: observations.append('Generic identity route; a synthetic unidentified site retains candidate with an explicit search limitation.')
            if not uni.domain: observations.append('No imported domain hint; this is missing metadata, not an observed failed crawl.')
            if tests['exact_seed']['result_count']>1: observations.append('Exact seed query matches additional identities.')
            rows.append({'seed_id':seed['seed_id'],'name':seed['name'],'university_id':uni.id,'live_checked':False,
                'tests':tests,'aliases':aliases,'seed_verification_status':uni.seed_snapshot['verification_status'],'seed_observed_at':uni.seed_snapshot['observed_at'],
                'domain':uni.domain,'domain_status':uni.domain_status,'official_site_hint':seed.get('official_site'),'duplicate_probe_hint': bool(not uni.registry_entry and uni.domain and seed.get('official_site') and f'https://{uni.domain}/' != seed['official_site'] and uni.domain == urlsplit(seed['official_site']).hostname),
                'discovery_route':'curated' if uni.registry_entry else 'generic_identity',
                'route_test':{'synthetic':True,'identify_calls':adapter._identify_site.await_count,'discover_one_calls':adapter._discover_one.await_count,'trace':route_trace},
                'allocation':{'unfiltered_position':ordered.index(uni)+1,'candidate_in_40':uni.id in default['ids'],'enrichment_in_20':uni.id in default['attempted']},
                'trace_state_test':{'synthetic':True,'skipped_and_attempted_empty_identical':skipped['traces']==attempted['traces'],'skipped_calls':len(skipped['attempted']),'attempted_calls':len(attempted['attempted'])},
                'observations':observations,'risk':'Observed missing stage status; generic identity evidence provenance needs trace linkage. No live failure inferred.'})
        assigned_ids={r['university_id'] for r in rows}
        target=next(u for u in ordered if u.id in assigned_ids and not u.registry_entry and u.domain and len(normalize(u.name))>=8)
        # Actual identity function, fixed synthetic transport; no DNS/provider calls.
        identity=[]
        for label,outcome,title,final in [('fetch_failed',FetchOutcome.HTTP_ERROR,'',''),('identity_mismatch',FetchOutcome.OK,'Unrelated University',''),('off_site_redirect',FetchOutcome.OK,target.name,'https://example.org/'),('matched',FetchOutcome.OK,target.name,'')]:
            fetcher=SimpleNamespace(get=AsyncMock(return_value=FetchResult(url=f'https://{target.domain}/',outcome=outcome,text=f'<title>{title}</title>',final_url=final,fetched_at=datetime(2026,10,4,tzinfo=UTC))))
            recorder=SimpleNamespace(calls=[])
            adapter=CatalogueDiscoveryAdapter(fetcher,session=s,university_ids=[target.id],live_limit=1,page_recorder=lambda **kwargs:recorder.calls.append(kwargs))
            provider=SimpleNamespace(search=AsyncMock(return_value=SimpleNamespace(results=[])))
            trace=DiscoveryTrace(institution=target.name,domain=target.domain or '')
            with patch('app.catalogue.discovery.get_search_provider',return_value=provider):
                result=await adapter._identify_site(target,trace)
            identity.append({'scenario':label,'matched':result is not None,'fetch_calls':fetcher.get.await_count,'provider_calls':provider.search.await_count,'trace':trace.as_dict(),'page_recorder_calls':len(recorder.calls)})
        proofs=[o.payload for o in s.scalars(select(UniversityObservation)) if o.seed_version=='live-site-identity']
        # Test explicit trace handoff; inserted markers are synthetic, not current emitted errors.
        adapter=CatalogueDiscoveryAdapter(SimpleNamespace(),session=s,university_ids=[target.id],live_limit=1)
        adapter._identify_site=AsyncMock(return_value={'name':target.name})
        adapter._discover_one=AsyncMock(return_value=(Candidate(name=target.name,country=target.country,city=target.city),DiscoveryTrace(institution=target.name,domain=target.domain or '')))
        initial=DiscoveryTrace(institution=target.name,domain=target.domain or '',errors=['synthetic identity diagnostic'],search_failures=['synthetic provider failure'],search_limitations=['synthetic identity limitation'])
        _, after=await adapter._enrich(target,PROFILE,Candidate(name=target.name,country=target.country,city=target.city),initial)
        history=[]
        for rel in ['backend/evaluation/research/expert/data/runs.2026-09-27/aalto.trace.json','backend/evaluation/research/expert/data/runs.2026-10-02/identity-replay.capture.json','backend/evaluation/research/expert/data/runs.2026-10-03/er15.37112534809/capture.json']:
            path=ROOT/rel
            data=json.loads(path.read_text())
            observations=data.get('observations',[]) if isinstance(data,dict) else []
            history.append({'path':rel,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'top_level_type':type(data).__name__,'top_level_keys':list(data) if isinstance(data,dict) else None,'captured_at':data.get('captured_at') if isinstance(data,dict) else None,'mode':data.get('mode') if isinstance(data,dict) else None,'pipeline_sha':data.get('pipeline_sha') if isinstance(data,dict) else None,'observations':[{'case_id':o['case_id'],'prediction_count':len(o.get('predictions',[])),'page_outcome_counts':dict(Counter(p['category'] for p in o.get('page_outcomes',[]))),'error':o.get('error'),'telemetry':o.get('telemetry')} for o in observations]})
        summary={'assigned':len(rows),'import':counts,'route_counts':dict(Counter(r['discovery_route'] for r in rows)),'domain_status_counts':dict(Counter(r['domain_status'] for r in rows)),'exact_target_found':sum(r['tests']['exact_seed']['target_found'] for r in rows),'exact_ambiguous':sum(r['tests']['exact_seed']['result_count']>1 for r in rows),'canonical_ambiguous':sum(r['tests']['canonical']['result_count']>1 for r in rows),'query_tests':sum(len(r['tests'])+len(r['aliases']) for r in rows),'alias_query_failures':sum(not a['target_found'] for r in rows for a in r['aliases']),'candidate_exposure_40':sum(r['allocation']['candidate_in_40'] for r in rows),'enrichment_exposure_20':sum(r['allocation']['enrichment_in_20'] for r in rows),'identical_skip_attempt_trace':sum(r['trace_state_test']['skipped_and_attempted_empty_identical'] for r in rows),'duplicate_probe_hint':sum(r['duplicate_probe_hint'] for r in rows),'live_checked':0}
        output={'group':8,'source_sha':packet['source_sha'],'seed_sha256':hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(),'summary':summary,'rows':rows,'synthetic_identity_cases':identity,'synthetic_identity_target':target.name,'synthetic_identity_proofs':proofs,'synthetic_handoff':{'before':initial.as_dict(),'after':after.as_dict()},'historical_artifacts':history,'equal_budget_measurements':{'trace_pair_institutions':50,'each_scenario_provider_calls':0,'each_scenario_fetch_calls':0,'current_trace_distinguishable_pairs':0,'explicit_attempt_sidecar_distinguishable_pairs':50}}
        (OUT/'group-08.rows.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(summary,sort_keys=True))

if __name__=='__main__': asyncio.run(main())
