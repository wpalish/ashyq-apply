"""Offline engineering diagnosis; no gold answers, providers or persistent DB."""
from __future__ import annotations
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

def deny_network(*args, **kwargs):
    raise AssertionError('network forbidden in group-10 audit')
socket.create_connection = deny_network
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.catalogue.importer import SEED_PATH, REGISTRY_PATH, import_catalogue, identity_key, stable_id
from app.catalogue.retrieval import retrieve
from app.db import create_all_for_tests
from app.domain.dedupe import normalize
from app.domain.site_identity import registrable_domain
from app.models import University
from urllib.parse import urlsplit
from evaluation.research.metrics import score
from evaluation.research.schema import Dataset, Capture


def synthetic_metric_probes():
    # Invented example, draft label, deliberately unrelated quote; no reviewed gold read.
    scope = {'university': 'Synthetic University', 'intake': '2027'}
    evidence = {'url': 'https://synthetic.example/fees', 'excerpt': 'The tuition is 100.',
                'scope': scope, 'accessed_on': '2026-10-04', 'source_type': 'official'}
    case = {'id': 'synthetic', 'dataset_version': 'synthetic-1', 'university': 'Synthetic University',
            'domain': 'synthetic.example', 'country': 'Synthetic', 'site_types': [], 'request': scope,
            'labels': [{'key': 'tuition', 'status': 'known', 'value': 100, 'evidence': [evidence]}],
            'review': {'status': 'draft', 'prepared_by': 'offline synthetic probe', 'notes': 'Invented; never real evidence.'}}
    dataset = Dataset.model_validate({'version': 'synthetic-1', 'split': 'development', 'cases': [case]})
    outputs = {}
    for variant in ['exact_current_unknown', 'exact_current_false', 'sibling_unrelated_quote', 'wrong_scope', 'explicit_unsupported', 'missing_observation']:
        p = {'key': 'tuition', 'value': 100, 'evidence': deepcopy(evidence)}
        if variant == 'exact_current_false': p['current'] = False
        if variant == 'sibling_unrelated_quote':
            p['evidence']['url'] = 'https://synthetic.example/sports'
            p['evidence']['excerpt'] = 'Our football team won a match.'
        if variant == 'wrong_scope': p['evidence']['scope']['intake'] = '2026'
        if variant == 'explicit_unsupported': p['supported'] = False
        capture = Capture.model_validate({'pipeline_sha': 'synthetic', 'captured_at': '2026-10-04', 'mode': 'synthetic',
                  'config': {'no_network': True}, 'observations': [] if variant == 'missing_observation' else [{'case_id': 'synthetic', 'predictions': [p]}]})
        report = score(dataset, capture, allow_drafts=True)
        outputs[variant] = {'metrics': {k: report['metrics'][k] for k in ['claim_recall', 'claim_recall_same_page', 'claim_precision', 'support_adjudication_rate', 'unsupported_claim_rate', 'current_evidence_rate', 'wrong_scope_claim_rate']}, 'cases': report['cases']}
    return outputs


def main():
    packet_path = HERE / 'group-10.packet.json'
    packet = json.loads(packet_path.read_text())
    live_source = (ROOT / 'backend/evaluation/research/live.py').read_text()
    metadata = {}
    for node in ast.parse(live_source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'COHORT', 'HELDOUT'}:
                    metadata[target.id] = ast.literal_eval(node.value)
    engine = create_engine('sqlite://')
    create_all_for_tests(engine)
    rows = []
    with Session(engine) as session:
        imported = import_catalogue(session)
        session.commit()
        all_rows = retrieve(session)
        assert len(all_rows) == 501
        assert len(packet['universities']) == 50
        for original in packet['universities']:
            uid = stable_id(identity_key(original['name'], original['country']))
            uni = session.get(University, uid)
            assert uni is not None
            queries = [('exact_seed_name', original['name'], {}), ('canonical_name', uni.name, {}),
                       ('normalized_name', normalize(uni.name), {}),
                       ('name_and_raw_country', uni.name + ' ' + original['country'], {}),
                       ('name_and_normalized_country', uni.name + ' ' + uni.country, {}),
                       ('country_filter', uni.name, {'country': original['country']})]
            if uni.city: queries.append(('name_and_city', uni.name + ' ' + uni.city, {}))
            variant = re.sub(r'\b(the|university|of)\b', ' ', uni.name, flags=re.I)
            variant = ' '.join(variant.split())
            if variant: queries.append(('short_name_variant', variant, {}))
            for alias in uni.aliases or []: queries.append(('supplied_alias', alias, {}))
            if uni.domain: queries.append(('domain_query_exploratory', uni.domain, {}))
            tests = []
            for kind, query, kwargs in queries:
                results = retrieve(session, query=query, **kwargs)
                ids = [r.id for r in results]
                tests.append({'kind': kind, 'query': query, 'filters': kwargs, 'result_count': len(results),
                              'target_found': uid in ids, 'target_rank': ids.index(uid) + 1 if uid in ids else None,
                              'returned_names': [r.name for r in results], 'returned_ids': ids})
            hints = list(dict.fromkeys(x for x in [f'https://{uni.domain}/' if uni.domain else None, original.get('official_site')] if x))
            domain = original.get('official_domain')
            host = urlsplit(original.get('official_site') or '').hostname
            conflict = bool(domain and host and registrable_domain(domain) != registrable_domain(host))
            route = 'curated_registry' if uni.registry_entry else ('generic_hints_then_search' if hints else 'generic_search_required')
            cohort = [k for k,v in metadata['COHORT'].items() if uni.domain and registrable_domain(uni.domain) == registrable_domain(v)]
            heldout = [k for k,v in metadata['HELDOUT'].items() if uni.domain and registrable_domain(uni.domain) == registrable_domain(v)]
            notes = [f'Offline identity only; route {route} inferred from actual imported fields and discovery.py:88-114.']
            failed = [t['kind'] for t in tests if not t['target_found'] and t['kind'] != 'domain_query_exploratory']
            if failed: notes.append('Observed query misses: ' + ', '.join(failed))
            if conflict: notes.append('Conflicting seed domain/site hosts; importer deliberately leaves domain unknown.')
            ambiguous = [t['query'] for t in tests if t['target_found'] and t['result_count'] > 1]
            if ambiguous: notes.append('Non-unique queries: ' + '; '.join(ambiguous))
            position = next(i + 1 for i,u in enumerate(all_rows) if u.id == uid)
            notes.append(f'Unfiltered catalogue position {position}/501; first-50 selection is not a random sample.')
            rows.append({'seed_id': original['seed_id'], 'name': original['name'], 'university_id': uid,
                         'canonical_name': uni.name, 'country': uni.country, 'aliases': uni.aliases,
                         'domain': uni.domain, 'domain_status': uni.domain_status, 'seed_domain': domain,
                         'seed_site': original.get('official_site'), 'conflicting_seed_hosts': conflict,
                         'hint_urls': hints, 'route': route, 'registry_fields': sorted((uni.registry_entry or {}).keys()),
                         'catalogue_position': position, 'tests': tests, 'observations': notes,
                         'risk': 'Query discoverability loss' if failed else 'Identity success does not establish programme/fact recall',
                         'baseline_cohort_ids': cohort, 'legacy_heldout_ids': heldout,
                         'seed_verification_status': uni.seed_snapshot['verification_status'],
                         'programme_page_recall': None, 'supported_scoped_current_fact_recall': None,
                         'live_checked': False})
    kinds = sorted({t['kind'] for row in rows for t in row['tests']})
    summary = {'rows': len(rows), 'import': imported, 'routes': dict(Counter(r['route'] for r in rows)),
               'domain_statuses': dict(Counter(r['domain_status'] for r in rows)),
               'conflicting_seed_hosts': sum(r['conflicting_seed_hosts'] for r in rows),
               'cohort_overlap': [r['name'] for r in rows if r['baseline_cohort_ids']],
               'legacy_heldout_overlap': [r['name'] for r in rows if r['legacy_heldout_ids']],
               'first50_inclusion': sum(r['catalogue_position'] <= 50 for r in rows),
               'canonical_top1_hits': sum(next(t for t in r['tests'] if t['kind'] == 'canonical_name')['target_rank'] == 1 for r in rows),
               'query_tests': {k: {'target_hits': sum(t['target_found'] for r in rows for t in r['tests'] if t['kind']==k),
                                   'tests': sum(t['kind']==k for r in rows for t in r['tests']),
                                   'unique_hits': sum(t['target_found'] and t['result_count']==1 for r in rows for t in r['tests'] if t['kind']==k)} for k in kinds},
               'programme_cases_measured': 0, 'fact_cases_measured': 0, 'live_cases_measured': 0}
    result = {'group': 10, 'source_sha': packet['source_sha'], 'seed_sha256': hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(),
              'packet_sha256': hashlib.sha256(packet_path.read_bytes()).hexdigest(),
              'source_file_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ['backend/app/catalogue/importer.py', 'backend/app/catalogue/retrieval.py', 'backend/app/catalogue/discovery.py', 'backend/evaluation/research/metrics.py', 'backend/evaluation/research/mapping.py', 'backend/evaluation/research/live.py']},
              'registry_sha256': hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest(),
              'summary': summary, 'synthetic_metric_probes': synthetic_metric_probes(), 'universities': rows}
    (HERE / 'group-10.rows.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('synthetic metric probes:', json.dumps({k: v['metrics']['claim_recall'] for k,v in result['synthetic_metric_probes'].items()}))

if __name__ == '__main__':
    main()
