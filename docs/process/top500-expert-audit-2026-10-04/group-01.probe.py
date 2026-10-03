"""Group 01 non-blind offline catalogue probe. Run with backend/.venv/bin/python.
Uses actual importer/retrieve against all 500 seed rows plus curated identities;
reports only the 50 packet rows. No application settings, providers or network.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Base, University, UniversityObservation
from app.catalogue.importer import SEED_PATH, import_catalogue, identity_key, canonical_name
from app.catalogue.retrieval import retrieve
from app.domain.dedupe import normalize

HERE = Path(__file__).resolve().parent
packet = json.loads((HERE / 'group-01.packet.json').read_text())
assert hashlib.sha256(SEED_PATH.read_bytes()).hexdigest() == packet['seed_sha256']
seed = json.loads(SEED_PATH.read_text())
by_seed = {r['seed_id']: r for r in seed['universities']}
assert all(by_seed[r['seed_id']] == r for r in packet['universities'])
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine, tables=[University.__table__, UniversityObservation.__table__])
results = []
with Session(engine) as session:
    imported = import_catalogue(session)
    session.commit()
    all_rows = list(session.scalars(select(University)))
    by_key = {u.identity_key: u for u in all_rows}
    cache = {}
    def check(label, q, u, **kwargs):
        key = (q, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = retrieve(session, query=q, **kwargs)
        found = cache[key]
        ids = [v.id for v in found]
        return {'label': label, 'query': q, 'country_filter': kwargs.get('country'),
                'target_found': u.id in ids, 'target_rank': ids.index(u.id)+1 if u.id in ids else None,
                'result_count': len(found), 'first_five': [{'name': v.name, 'id': v.id} for v in found[:5]],
                'other_result_count': len(found) - int(u.id in ids)}
    for row in packet['universities']:
        u = by_key[identity_key(row['name'], row['country'])]
        n = u.name
        tests = [check('exact_seed_name',row['name'],u), check('canonical_name',canonical_name(row['name']),u),
                 check('uppercase',n.upper(),u), check('NFD_unicode',unicodedata.normalize('NFD',n),u),
                 check('normalized_accent_folded',normalize(n),u),
                 check('reordered_tokens',' '.join(reversed(normalize(n).split())),u),
                 check('seed_country_filter',n,u,country=row['country']),
                 check('seed_country_in_free_query',n+' '+row['country'],u),
                 check('admissions_intent',n+' admissions',u)]
        for alias in u.aliases or []:
            tests.append(check('supplied_alias',alias,u))
        for acronym in re.findall(r'\(([^()]+)\)',row['name']):
            tests.append(check('parenthetical_token',acronym,u))
        if re.search(r"['’\-]",n):
            tests.append(check('punctuation_deleted',re.sub(r"['’\-]",'',n),u))
        german = n.replace('ü','ue').replace('ä','ae').replace('ö','oe').replace('ß','ss')
        if german != n:
            tests.append(check('german_transliteration',german,u))
        if u.domain:
            tests.append(check('domain_query',u.domain,u))
        if row['seed_id']=='qs2027-221':
            tests.append(check('IISc_without_punctuation','IISc',u))
        hints = list(dict.fromkeys(h for h in [f'https://{u.domain}/' if u.domain else None,row.get('official_site')] if h))
        core = [t for t in tests if t['label'] in {'exact_seed_name','canonical_name','supplied_alias','normalized_accent_folded','NFD_unicode','uppercase','seed_country_filter'}]
        observations = []
        if all(t['target_found'] for t in core): observations.append('Exact/canonical/supplied-alias and normalization controls recover target.')
        if any(t['label']=='german_transliteration' and not t['target_found'] for t in tests): observations.append('Umlaut-to-digraph query variant misses despite accent-folded control matching.')
        if any(t['label']=='punctuation_deleted' and not t['target_found'] for t in tests): observations.append('Deleting punctuation joins characters and misses; normalizer replaces punctuation with spaces.')
        if any(t['label']=='seed_country_in_free_query' and not t['target_found'] for t in tests): observations.append('Raw seed country text fails in free query although structured country filter succeeds.')
        if any(t['label']=='supplied_alias' and t['other_result_count'] for t in tests): observations.append('At least one supplied alias also retrieves other identities; inspect results before treating these as false positives.')
        if tests[0]['target_rank'] != 1: observations.append('Exact seed-name target is not ranked first.')
        if not u.registry_entry: observations.append('Generic discovery requires site identification before programme discovery.')
        if not hints: observations.append('No retained domain/site hint; identity route requires configured search provider. This is a seed coverage limitation, not a proven live failure.')
        risk = 'moderate' if any(t['label'] in {'german_transliteration','punctuation_deleted','seed_country_in_free_query'} and not t['target_found'] for t in tests) or not hints or tests[0]['target_rank'] != 1 else 'low'
        results.append({'seed_id': row['seed_id'], 'name':row['name'], 'university_id':u.id,'canonical_name':n,
                        'country':u.country,'aliases':u.aliases,'tests':tests,'observations':observations,'risk':risk,
                        'live_checked':False,'seed_verification_status':u.seed_snapshot['verification_status'],
                        'diacritics_present':any(unicodedata.combining(c) for c in unicodedata.normalize('NFD',n)),
                        'domain':u.domain,'domain_status':u.domain_status,'hints':hints,
                        'route':'curated_registry' if u.registry_entry else 'generic_site_identification',
                        'registry_fields':sorted(u.registry_entry) if u.registry_entry else []})
engine.dispose()
summary={'rows':len(results),'imported':imported,'all_test_count':sum(len(r['tests']) for r in results),
         'routes':dict(Counter(r['route'] for r in results)), 'domain_status':dict(Counter(r['domain_status'] for r in results)),
         'no_hints':sum(not r['hints'] for r in results),'diacritic_rows':sum(r['diacritics_present'] for r in results),
         'tests':{label:{'n':len(ts),'target_found':sum(t['target_found'] for t in ts),'multiple_results':sum(t['other_result_count']>0 for t in ts)}
                  for label in sorted({t['label'] for r in results for t in r['tests']})
                  for ts in [[t for r in results for t in r['tests'] if t['label']==label]]}}
output={'group':1,'source_sha':packet['source_sha'],'seed_sha256':packet['seed_sha256'],
        'method':'non-blind offline engineering audit; actual importer/retrieve, full seed search space, SQLite memory; no network',
        'live_checked':False,'summary':summary,'rows':results}
(HERE/'group-01.rows.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
