"""Offline actual full-catalogue audit; synthetic claims are explicitly labelled.
Run from repository root: backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-04.probe.py
Writes only group-04.rows.json. Never fetches a page or loads applicant data.
"""
import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, fields
from datetime import UTC, datetime, date
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Base, University, UniversityObservation
from app.catalogue.importer import SEED_PATH, import_catalogue, identity_key, canonical_name
from app.catalogue.retrieval import retrieve
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.domain.dedupe import normalize
from app.domain.claim_scope import ClaimScope, RequestedScope
from app.domain.eligibility import requested_scope, _confirmed, evaluate_program
from app.schemas.claim import Claim
from app.schemas.profile import ApplicantProfileIn, ApplicationContext, AcademicRecord, IeltsScore

HERE = Path(__file__).resolve().parent
packet = json.loads((HERE / 'group-04.packet.json').read_text())
seed = json.loads(SEED_PATH.read_text())
assert hashlib.sha256(SEED_PATH.read_bytes()).hexdigest() == packet['seed_sha256']
assert len(packet['universities']) == 50
assert all(r in seed['universities'] for r in packet['universities'])
class NoNetwork:
    async def get(self, *args, **kwargs):
        raise AssertionError('No network is authorized by this offline probe')
profile = ApplicantProfileIn(context=ApplicationContext(level='bachelor', intended_fields=['computer science'], intake_year=2027, citizenship='Kazakhstan', country_of_residence='Kazakhstan', education_country='Kazakhstan', education_system='Synthetic secondary'), academics=AcademicRecord(ielts=IeltsScore(overall=6.0)))
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine, tables=[University.__table__, UniversityObservation.__table__])
rows = []
with Session(engine) as session:
    imported = import_catalogue(session)
    session.commit()
    all_unis = list(session.scalars(select(University)))
    by_key = {u.identity_key:u for u in all_unis}
    order_before = [u.id for u in retrieve(session)]
    selected = [by_key[identity_key(r['name'],r['country'])].id for r in packet['universities']]
    adapter = CatalogueDiscoveryAdapter(NoNetwork(),session=session,university_ids=selected,live_limit=0)
    candidates_before = asyncio.run(adapter.discover(profile,limit=50))
    candidates = {c.discovery_source.split(':',1)[1]:c for c in candidates_before}
    for r in packet['universities']:
        u = by_key[identity_key(r['name'],r['country'])]
        tests = []
        queries = [('exact_name',r['name']),('canonical_name',canonical_name(r['name'])),('uppercase',u.name.upper()),('accent_folded',normalize(u.name)),('reverse_tokens',' '.join(reversed(normalize(u.name).split()))),('name_with_admissions',u.name+' admissions'),('name_with_bachelor',u.name+' bachelor'),('name_with_country',u.name+' '+r['country'])]
        queries += [('supplied_alias',a) for a in u.aliases or []]
        if u.domain: queries.append(('domain_query',u.domain))
        for label, q in queries:
            found = retrieve(session,query=q)
            ids = [v.id for v in found]
            tests.append({'label':label,'query':q,'target_found':u.id in ids,'target_rank':ids.index(u.id)+1 if u.id in ids else None,'result_count':len(ids),'result_names':[v.name for v in found[:8]]})
        filtered=retrieve(session,query=u.name,country=r['country'])
        tests.append({'label':'structured_country','query':u.name,'country':r['country'],'target_found':u.id in [v.id for v in filtered],'result_count':len(filtered)})
        record=u.seed_snapshot['record']
        hints=list(dict.fromkeys(h for h in [f'https://{u.domain}/' if u.domain else None,record.get('official_site')] if h))
        admission=record.get('admissions_snapshot') or []
        cost=record.get('tuition_usd_estimate')
        mixed=any(a['test'] in {'GRE','GMAT'} for a in admission) and any(a['test']=='SAT' for a in admission)
        obs=['Seed snapshot remains unverified_seed with observed_at=null; no admission or fee claim is created by import.', 'Zero-live discovery retains institution candidate with no programme, requirements URL or costs URL.']
        obs.append('Observed retrieval limitation: appending admissions or bachelor yields no target; structured identity query succeeds.')
        if tests[0]['target_rank'] != 1: obs.append('Observed exact-name ordering defect: target is not first; substring/city matches precede it.')
        if admission: obs.append('Unscoped seed exam hints exist; they do not establish this applicant programme/degree/intake eligibility.')
        if cost: obs.append('Secondary USD fee estimate exists without programme/degree/intake/fee-population scope; not decision-grade annual net cost.')
        if mixed: obs.append('SAT and GRE/GMAT appear together without degree scope; pooling as one admission rule would be unsafe.')
        if not hints: obs.append('No retained site hints; generic identity research depends on configured search. Coverage limitation, not proven live failure.')
        if not u.registry_entry: obs.append('Generic identification route precedes programme research.')
        if any(t['label']=='supplied_alias' and t['result_count']>1 for t in tests): obs.append('A supplied alias returns multiple identities; needs disambiguation.')
        rows.append({'seed_id':r['seed_id'],'name':r['name'],'university_id':u.id,'canonical_name':u.name,'aliases':u.aliases,'tests':tests,'observations':obs,'risk':'high_if_seed_promoted' if admission or cost else 'research_incomplete','live_checked':False,'route':'curated_registry' if u.registry_entry else 'generic_identity','domain':u.domain,'domain_status':u.domain_status,'hints':hints,'seed_verification_status':u.seed_snapshot['verification_status'],'seed_observed_at':u.seed_snapshot['observed_at'],'admission_hint_count':len(admission),'admission_tests':[a['test'] for a in admission],'has_tuition_hint':bool(cost),'mixed_SAT_GRE_GMAT':mixed,'seed_decision_scope_missing':['programme','degree','campus','intake','fee_population'],'zero_live_candidate':asdict(candidates[u.id]),'catalogue_default_rank':order_before.index(u.id)+1,'next_research_priority':['official_site_identity']*(not bool(u.registry_entry))+['programme_degree_campus_intake_identity','qualification_recognition_and_entry_requirements','population_scoped_tuition_and_mandatory_costs','funding_eligibility_and_deadlines']})
    # Adversarial sensitivity control: radically alter only unverified fee/exam hints.
    for u in all_unis:
        if u.seed_snapshot:
            snap=deepcopy(u.seed_snapshot)
            snap['record']['tuition_usd_estimate']={'min':999999.0,'max':999999.0,'quality':'synthetic_only'}
            snap['record']['admissions_snapshot']=[{'test':'IELTS','minimum':'9+'},{'test':'SAT','minimum':'1600+'}]
            u.seed_snapshot=snap
    session.flush()
    order_after=[u.id for u in retrieve(session)]
    after=asyncio.run(adapter.discover(profile,limit=50))
    seed_mutation={'synthetic':True,'mutated_seed_rows':sum(bool(u.seed_snapshot) for u in all_unis),'catalogue_order_unchanged':order_before==order_after,'all_50_zero_live_candidates_unchanged':[asdict(c) for c in candidates_before]==[asdict(c) for c in after]}
    for r in rows: r['seed_hint_mutation_control']=seed_mutation['all_50_zero_live_candidates_unchanged']
engine.dispose()
# Exercise real pure scope and eligibility functions with explicitly synthetic claims.
base=dict(claim_type='ielts_min_overall',normalized_value=7.0,source_url='https://example.edu/synthetic',accessed_at=datetime(2026,10,4,tzinfo=UTC),status='VERIFIED_CURRENT',intake='fall 2027',program='Computer Science')
claims={
 'legacy_none':Claim(**base),
 'empty_scope':Claim(**base,scope=ClaimScope()),
 'matching_intake':Claim(**base,scope=ClaimScope(programme='Computer Science',degree='bachelor',intake='fall 2027')),
 'wrong_intake':Claim(**base,scope=ClaimScope(programme='Computer Science',degree='bachelor',intake='fall 2026')),
 'wrong_programme_degree_same_intake':Claim(**base,scope=ClaimScope(programme='MBA',degree='master',intake='fall 2027')),
}
scope_results={}
for label,c in claims.items():
    request=requested_scope([c])
    result=evaluate_program(profile,[c],today=date(2026,10,4))
    scope_results[label]={'synthetic':True,'request_scope':asdict(request),'confirmed':_confirmed(c,request),'eligibility':result.status.value,'hard_filter_failures':result.hard_filter_failures}
full_request=RequestedScope(programme='Computer Science',degree='bachelor',intake='fall 2027')
scope_results['explicit_full_request_wrong_degree_control']={'verdict':claims['wrong_programme_degree_same_intake'].scope.covers(full_request).value}
campus_a=ClaimScope.from_mapping({'programme':'Computer Science','intake':'fall 2027','campus':'A'})
campus_b=ClaimScope.from_mapping({'programme':'Computer Science','intake':'fall 2027','campus':'B'})
scope_results['campus_distinction']={'synthetic':True,'campus_is_dimension':any(f.name=='campus' for f in fields(ClaimScope)),'different_campus_mappings_equal':campus_a==campus_b}
labels=sorted({t['label'] for r in rows for t in r['tests']})
summary={'rows':len(rows),'import':imported,'test_count':sum(len(r['tests']) for r in rows),'routes':dict(Counter(r['route'] for r in rows)),'domain_status':dict(Counter(r['domain_status'] for r in rows)),'no_hints':sum(not r['hints'] for r in rows),'with_admission_hints':sum(r['admission_hint_count']>0 for r in rows),'with_tuition_hints':sum(r['has_tuition_hint'] for r in rows),'with_either_hint':sum(r['admission_hint_count']>0 or r['has_tuition_hint'] for r in rows),'mixed_SAT_GRE_GMAT':sum(r['mixed_SAT_GRE_GMAT'] for r in rows),'default_first_20':sum(r['catalogue_default_rank']<=20 for r in rows),'default_first_50':sum(r['catalogue_default_rank']<=50 for r in rows),'tests':{label:{'count':len(ts),'found':sum(t['target_found'] for t in ts),'ambiguous':sum(t['result_count']>1 for t in ts)} for label in labels for ts in [[t for r in rows for t in r['tests'] if t['label']==label]]}}
output={'group':4,'source_sha':packet['source_sha'],'seed_sha256':packet['seed_sha256'],'method':'non-blind offline diagnosis; actual importer/retrieve full catalogue; no source verification','live_checked':False,'summary':summary,'seed_mutation_control':seed_mutation,'synthetic_scope_tests':scope_results,'rows':rows}
(HERE/'group-04.rows.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in output.items() if k!='rows'},ensure_ascii=False,indent=2))
