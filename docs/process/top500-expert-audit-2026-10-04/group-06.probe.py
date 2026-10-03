"""Offline diagnostic; actual full importer/retrieval, synthetic discovery transport."""
from __future__ import annotations
import asyncio
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.catalogue.importer import SEED_PATH, import_catalogue, identity_key, stable_id, country_name
from app.catalogue.retrieval import retrieve, REGIONS
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.domain.dedupe import normalize
from app.domain.ranking_v2 import u_country, KnockOut
from app.db import create_all_for_tests
from app.models import University
from app.schemas.profile import Preferences

OUT = Path(__file__).parent

def new_db(document=None):
    engine = create_engine('sqlite://')
    create_all_for_tests(engine)
    session = Session(engine)
    counts = import_catalogue(session, document)
    session.commit()
    return engine, session, counts

def query_test(session, u, query):
    found = retrieve(session, query=query)
    ids = [x.id for x in found]
    return {'query': query, 'target_found': u.id in ids, 'target_position': ids.index(u.id)+1 if u.id in ids else None,
            'result_count': len(ids), 'other_names': [x.name for x in found if x.id != u.id][:8]}

def excluded_score(country, constraint):
    try:
        u_country(country, [], [constraint])
        return False
    except KnockOut:
        return True

async def allocation(session, preferred=None, excluded=None, selected=None, limit=40, live_limit=20):
    # Synthetic: preserve actual discover() loop, replace enrichment before any fetch.
    adapter = CatalogueDiscoveryAdapter(SimpleNamespace(), session=session, university_ids=selected, live_limit=live_limit)
    attempted=[]
    async def fake_enrich(u, profile, candidate, trace):
        attempted.append(u.id)
        return candidate, trace
    adapter._enrich = fake_enrich
    candidates=await adapter.discover(SimpleNamespace(preferences=Preferences(preferred_countries=preferred or [], excluded_countries=excluded or [])), limit)
    return {'candidate_ids': [c.discovery_source.split(':', 1)[1] for c in candidates], 'attempted_ids': attempted,
            'rankings_count': sum(len(c.rankings) for c in candidates), 'programs_count': sum(len(c.programs) for c in candidates),
            'unattempted_blank_trace_count': sum(not t.errors and not t.search_limitations for t in adapter.traces[len(attempted):])}

async def main():
    packet=json.loads((OUT/'group-06.packet.json').read_text())
    engine,s,counts=new_db()
    all_rows=retrieve(s)
    bykey={u.identity_key:u for u in all_rows}
    default=await allocation(s)
    again=await allocation(s)
    preferred_all={c:[u.id for u in retrieve(s, preferred=[c])] for c in {u.country for u in all_rows}}
    country_sets={c:{u.id for u in retrieve(s,country=c)} for c in {u.country for u in all_rows}}
    region_sets={r:{u.id for u in retrieve(s,country=r)} for r in REGIONS}
    excluded_regions={r:{u.id for u in retrieve(s,excluded=[r])} for r in REGIONS}
    raw_country_sets={x['country']:{u.id for u in retrieve(s,country=x['country'])} for x in packet['universities']}
    results=[]
    for row in packet['universities']:
        u=bykey[identity_key(row['name'],row['country'])]
        regions=[r for r, countries in REGIONS.items() if u.country in countries]
        tests={name:query_test(s,u,q) for name,q in {'exact_seed':row['name'],'canonical':u.name,'normalized':normalize(u.name),'word_reorder':' '.join(reversed(u.name.split()))}.items()}
        alias_tests=[query_test(s,u,a) for a in u.aliases or []]
        region_results=[{'region':r,'retrieved':u.id in region_sets[r],'excluded':u.id not in excluded_regions[r], 'ranking_preferred_utility':u_country(u.country,[r],[])[0], 'ranking_excluded_knockout':excluded_score(u.country,r)} for r in regions]
        selected=await allocation(s,selected=[u.id],limit=1,live_limit=0)
        # Synthetic route test invokes actual _enrich with both external seams mocked.
        route_adapter=CatalogueDiscoveryAdapter(SimpleNamespace(),session=s,university_ids=[u.id],live_limit=1)
        route_adapter._identify_site=AsyncMock(return_value=None)
        from app.adapters.base import Candidate
        from app.adapters.discovery.live_discovery import DiscoveryTrace
        route_adapter._discover_one=AsyncMock(return_value=(Candidate(name=u.name,country=u.country,city=u.city),DiscoveryTrace(institution=u.name,domain=u.domain or '')))
        route_candidates=await route_adapter.discover(SimpleNamespace(preferences=Preferences()),1)
        observations=['Region preference/exclusion semantics differ between retrieval and country ranking under synthetic region profile.']
        if u.id not in default['attempted_ids']: observations.append('Not allocated enrichment in synthetic 40-candidate / 20-enrichment default run; deterministic repetition does not rotate exposure.')
        if tests['exact_seed']['result_count']>1: observations.append('Full seed name returns additional institutions; lexical substring matching does not prioritize exact identity.')
        results.append({'seed_id':row['seed_id'],'name':row['name'],'university_id':u.id,'canonical_name':u.name,'country':u.country,'live_checked':False,
            'tests':tests,'aliases':alias_tests,'country_filter':{'seed_country':row['country'],'raw_match':u.id in raw_country_sets[row['country']],'canonical_match':u.id in country_sets[u.country], 'excluded_removes':u.id not in {x.id for x in retrieve(s,excluded=[u.country])},'preference_position':preferred_all[u.country].index(u.id)+1,'literal_ranking_utility':u_country(u.country,[u.country],[])[0],'literal_ranking_knockout':excluded_score(u.country,u.country),'raw_seed_ranking_utility':u_country(u.country,[row['country']],[])[0]},
            'regions':region_results,'discovery_route':{'kind':'curated' if u.registry_entry else 'generic_identity','domain':u.domain,'domain_status':u.domain_status,'official_site_hint':row.get('official_site'),'registry_entry':bool(u.registry_entry),'synthetic_identify_calls':route_adapter._identify_site.await_count,'synthetic_discover_one_calls':route_adapter._discover_one.await_count,'fallback_keeps_candidate':len(route_candidates)==1},
            'allocation':{'default_position':all_rows.index(u)+1,'in_candidate_40':u.id in default['candidate_ids'],'enrichment_20':u.id in default['attempted_ids'],'selected_returns_exact_id':selected['candidate_ids']==[u.id], 'empty_rankings_programs':selected['rankings_count']==selected['programs_count']==0},
            'observations':observations,'risk':'observed cross-stage semantic inconsistency; allocation limitation under bounded synthetic scenario; admissions facts unverified'})
    # Input permutation and seed-only value controls use the actual importer in a second DB.
    altered=json.loads(SEED_PATH.read_text())
    altered['universities'].reverse()
    for row in altered['universities']:
        row['qs_rank_2027']='1'
        row['tuition_usd_estimate']={'min':999999,'max':999999,'quality':'synthetic_test'}
        row['admissions_snapshot']=[]
    e2,s2,c2=new_db(altered)
    ids1=[u.id for u in retrieve(s)]
    ids2=[u.id for u in retrieve(s2)]
    pref_uk=await allocation(s,preferred=['UK'])
    overlap=Preferences(preferred_countries=['UK'],excluded_countries=['United Kingdom'])
    literal_rejected=False
    try: Preferences(preferred_countries=['United Kingdom'],excluded_countries=['United Kingdom'])
    except ValueError: literal_rejected=True
    selected_ids=[r['university_id'] for r in results]
    selected_forward=await allocation(s,selected=selected_ids,limit=50,live_limit=20)
    selected_reverse=await allocation(s,selected=selected_ids[::-1],limit=50,live_limit=20)
    summary={'covered':len(results),'import':counts,'curated_total':sum(bool(u.registry_entry) for u in all_rows),
        'exact_recall':sum(r['tests']['exact_seed']['target_found'] for r in results),'canonical_recall':sum(r['tests']['canonical']['target_found'] for r in results),
        'alias_queries':sum(len(r['aliases']) for r in results),'alias_recall':sum(t['target_found'] for r in results for t in r['aliases']),
        'ambiguous_exact':sum(r['tests']['exact_seed']['result_count']>1 for r in results),'exact_not_first':sum(r['tests']['exact_seed']['target_position']!=1 for r in results),
        'curated_group':sum(r['discovery_route']['registry_entry'] for r in results),'missing_domain':sum(not r['discovery_route']['domain'] for r in results),
        'in_default_40':sum(r['allocation']['in_candidate_40'] for r in results),'in_default_live_20':sum(r['allocation']['enrichment_20'] for r in results),
        'region_semantic_mismatch':sum(any(t['ranking_preferred_utility']!=1 or not t['ranking_excluded_knockout'] for t in r['regions']) for r in results),
        'raw_seed_country_ranking_mismatch':sum(r['country_filter']['raw_seed_ranking_utility']!=1 for r in results),
        'stable_ids_and_order_under_seed_permutation_and_unverified_values':ids1==ids2,
        'idempotent_import':import_catalogue(s),'repeat_allocation_identical':default==again,'selected_input_order_ignored':selected_forward['candidate_ids']==selected_reverse['candidate_ids'],
        'alias_overlap_validates':bool(overlap),'literal_overlap_rejected':literal_rejected,
        'full_default_allocation':default,'default_20_countries':dict(Counter(s.get(University,i).country for i in default['attempted_ids'])),
        'default_20_curated':sum(bool(s.get(University,i).registry_entry) for i in default['attempted_ids']),
        'uk_preference_20_countries':dict(Counter(s.get(University,i).country for i in pref_uk['attempted_ids'])),
        'synthetic_renaming_changes_identity':stable_id(identity_key(results[0]['name'],results[0]['country']))!=stable_id(identity_key(results[0]['name']+' Renamed',results[0]['country']))}
    output={'method':'Non-blind offline diagnosis; full seed+registry importer/retrieve; synthetic allocation and route seams; no live source reads.','summary':summary,'universities':results}
    (OUT/'group-06.rows.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2))
    s2.close();e2.dispose();s.close();engine.dispose()

if __name__=='__main__': asyncio.run(main())
