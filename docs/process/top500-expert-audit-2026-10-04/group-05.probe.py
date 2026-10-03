"""Offline actual full-catalogue audit; no official-site or provider calls."""
from pathlib import Path
import sys, json, re, hashlib
from dataclasses import asdict
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db import create_all_for_tests
from app.models import University
from app.catalogue.importer import import_catalogue, identity_key, SEED_PATH
from app.catalogue.retrieval import retrieve
from app.domain.dedupe import normalize
from app.adapters.page_classifier import classify_page
from app.adapters.discovery.live_discovery import profile_rejects

HERE = Path(__file__).resolve().parent
packet = json.loads((HERE / 'group-05.packet.json').read_text())
engine = create_engine('sqlite://')
create_all_for_tests(engine)
rows = []
with Session(engine) as s:
    imported = import_catalogue(s)
    s.commit()
    all_rows = list(s.scalars(select(University)))
    assert len(all_rows) == 501
    for seed in packet['universities']:
        u = next(v for v in all_rows if v.identity_key == identity_key(seed['name'], seed['country']))
        tests = []
        def check(kind, query='', country='', provenance='actual imported identity'):
            hits = retrieve(s, query=query, country=country)
            tests.append(dict(kind=kind, query=query, country=country, provenance=provenance,
                target_found=u.id in [h.id for h in hits], target_position=next((i+1 for i,h in enumerate(hits) if h.id==u.id),None),
                hit_count=len(hits), matches=[dict(id=h.id,name=h.name,country=h.country) for h in hits]))
        check('exact_seed', seed['name'])
        check('canonical', u.name)
        for a in u.aliases or []:
            check('stored_alias', a)
        check('normalized_name', normalize(u.name), provenance='mechanical case/accent/punctuation normalization, not translation')
        check('token_reordering', ' '.join(reversed(normalize(u.name).split())), provenance='mechanical token reversal')
        acronym = ''.join(t[0] for t in normalize(u.name).split() if t not in {'of','the','and','de','in','for','at'})
        check('mechanical_initials', acronym, provenance='synthetic initials; no claim this is an official alias')
        check('seed_country_filter', u.name, seed['country'])
        check('seed_country_in_query', u.name+' '+seed['country'])
        check('canonical_country_in_query', u.name+' '+u.country)
        check('programme_intent', u.name+' computer science bachelor', provenance='synthetic user intent; no claim programme exists')
        check('name_typo_control', u.name+' zzzznonexistent', provenance='negative control')
        wrong = 'Japan' if u.country != 'Japan' else 'Canada'
        check('wrong_country_control', u.name, wrong, 'negative control')
        if u.domain:
            check('domain_query', u.domain, provenance='imported domain hint; not currently verified')
        obs = []
        if any(not t['target_found'] for t in tests if t['kind']=='seed_country_in_query'):
            obs.append('Original seed country works as filter but blocks the same identity in q.')
        if any(t['hit_count']>1 for t in tests if t['kind'] in {'exact_seed','canonical','stored_alias'}):
            obs.append('At least one exact/name/alias query has multiple full-catalogue matches; see matches.')
        if not u.domain:
            obs.append('No imported domain: generic discovery needs site identification; missing data is not an error.')
        if not next(t for t in tests if t['kind']=='mechanical_initials')['target_found']:
            obs.append('Mechanical initials not indexed; not proof of a missing real alias.')
        obs.append('Programme intent is outside identity-only catalogue retrieval; no programme absence conclusion.')
        rows.append(dict(seed_id=seed['seed_id'], name=seed['name'], canonical_name=u.name, country=u.country,
            aliases=u.aliases, domain=u.domain, domain_status=u.domain_status,
            hints=dict(official_domain=seed.get('official_domain'),official_site=seed.get('official_site')),
            route='curated_registry' if u.registry_entry else 'generic_site_identification',
            curated_seed_keys=sorted((u.registry_entry or {}).get('seeds',{})),
            tests=tests, observations=obs,
            risk='Identity recall/ambiguity only; programme, language, degree and admissions remain unverified.', live_checked=False))

fixtures = [
 ('bachelor_english', 'BSc Computer Science', '<p>Language of instruction: English</p>', 'bachelor'),
 ('master_negative', 'MSc Computer Science', '<p>Language of instruction: English</p>', 'bachelor'),
 ('subject_negative', 'BSc History', '<p>Language of instruction: English</p>', 'bachelor'),
 ('degree_absent', 'Computer Science', '<p>Language of instruction: English</p>', 'bachelor'),
 ('language_absent', 'BSc Computer Science', '<p>Study our course.</p>', 'bachelor'),
 ('label_spanish', 'BSc Computer Science', '<p>Language of instruction: Spanish</p>', 'bachelor'),
 ('label_turkish', 'BSc Computer Science', '<p>Language of instruction: Turkish</p>', 'bachelor'),
 ('german_label', 'BSc Computer Science', '<p>Unterrichtssprache: Deutsch</p>', 'bachelor'),
 ('catalog_negative', 'Bachelor programmes', '<a href="/programmes/computer-science">BSc Computer Science</a>', 'bachelor'),
 ('translated_degree_synthetic', 'Grado en Computer Science', '<p>Language of instruction: Spanish</p>', 'bachelor'),
]
synthetic=[]
for key,title,body,level in fixtures:
    html=f'<html><head><title>{title}</title></head><body><main><h1>{title}</h1>{body}</main></body></html>'
    c=classify_page(url='https://synthetic.invalid/study/topic',html=html)
    synthetic.append(dict(case=key,fixture_type='synthetic; not from any university',html=html,
        classification=asdict(c), reject_reason=profile_rejects(c,level,['computer science'])))
summary = dict(imported=imported,assigned=len(rows),live_checked=0,
    routes=dict(Counter(r['route'] for r in rows)),domain_status=dict(Counter(r['domain_status'] for r in rows)))
for kind in sorted({t['kind'] for r in rows for t in r['tests']}):
    ts=[t for r in rows for t in r['tests'] if t['kind']==kind]
    summary[kind]=dict(tests=len(ts),target_found=sum(t['target_found'] for t in ts),ambiguous=sum(t['hit_count']>1 for t in ts),no_hits=sum(t['hit_count']==0 for t in ts))
summary['name_has_diacritics']=sum(any(ord(c)>127 for c in r['name']) for r in rows)
summary['distinct_stored_alias_ambiguity_rows']=sum(any(t['hit_count']>1 for t in r['tests'] if t['kind']=='stored_alias') for r in rows)
out=dict(group=5,baseline=packet['source_sha'],seed_sha256=hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(),
    methodology='Actual importer plus full 500-seed and curated 501-university in-memory SQLite; offline non-blind diagnosis.',
    summary=summary,universities=rows,synthetic_classifier_probes=synthetic)
assert len(rows)==50 and len({r['seed_id'] for r in rows})==50
(HERE/'group-05.rows.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,indent=2))
print(json.dumps(synthetic,indent=2))
