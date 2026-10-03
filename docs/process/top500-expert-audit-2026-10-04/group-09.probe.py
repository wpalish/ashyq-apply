"""Offline Group09 audit. Run from repository root; no network/provider calls."""
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import html
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.models import University, UniversityObservation
from app.catalogue.importer import import_catalogue, SEED_PATH, identity_key, canonical_name, validate_snapshot
from app.catalogue.retrieval import retrieve
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import ResponseCache, FetchResult, Fetcher
from app.domain.enums import FetchOutcome

OUT = Path(__file__).parent
DOC = json.loads(SEED_PATH.read_text())
PACKET = json.loads((OUT / 'group-09.packet.json').read_text())

class FakeFetcher:
    def __init__(self, name):
        self.name = name
        self.calls = []
        self.at = datetime(2026, 10, 4, tzinfo=UTC)
    async def get(self, url):
        self.calls.append(url)
        body = f'<title>{html.escape(self.name)} University</title>'.encode()
        return FetchResult(url=url, final_url=url, outcome=FetchOutcome.OK, content=body, fetched_at=self.at)

async def main():
    engine = create_engine('sqlite:///:memory:')
    University.__table__.create(engine)
    UniversityObservation.__table__.create(engine)
    with Session(engine) as s:
        imported = import_catalogue(s, DOC)
        s.commit()
        repeat = import_catalogue(s, DOC)
        rows = []
        by_key = {u.identity_key: u for u in s.scalars(select(University))}
        domains = Counter(u.domain for u in by_key.values() if u.domain)
        ordered_ids = [u.id for u in retrieve(s)]
        for seed in PACKET['universities']:
            u = by_key[identity_key(seed['name'], seed['country'])]
            tests = []
            queries = [('exact', seed['name']), ('canonical', canonical_name(seed['name'])),
                       ('case_spacing', '  ' + seed['name'].upper() + '  '),
                       ('name_country', u.name + ' ' + seed['country'])]
            queries += [('alias', a) for a in u.aliases if a not in {u.name, seed['name']}]
            if seed.get('city'): queries += [('name_city', u.name + ' ' + seed['city'])]
            for kind, q in queries:
                result = retrieve(s, query=q)
                ids = [v.id for v in result]
                tests.append({'kind': kind, 'query': q, 'count': len(ids), 'target_present': u.id in ids,
                              'target_rank': ids.index(u.id) + 1 if u.id in ids else None,
                              'matches': [v.name for v in result]})
            row = {'seed_id': seed['seed_id'], 'name': seed['name'], 'university_id': u.id,
                   'live_checked': False, 'seed_verification': u.seed_snapshot['verification_status'],
                   'retrieval': tests, 'aliases': u.aliases, 'domain': u.domain, 'domain_status': u.domain_status,
                   'official_site_hint': seed.get('official_site'), 'domain_identity_count': domains[u.domain] if u.domain else 0,
                   'route': 'curated' if u.registry_entry else 'generic',
                   'curated_seed_categories': sorted((u.registry_entry or {}).get('seeds', {})),
                   'default_position': ordered_ids.index(u.id) + 1}
            before_domain = u.domain
            fake = FakeFetcher(u.name)
            adapter = CatalogueDiscoveryAdapter(fake, session=s, university_ids=[u.id], live_limit=1)
            # Synthetic page matches each identity; it asserts mechanism only, never website truth.
            synthetic_host = u.name.lower() + '.edu' if len(u.name) < 8 and ' ' not in u.name else f'audit{seed["list_index"]}.edu'
            hint = f'https://{synthetic_host}/'
            n0 = s.scalar(select(func.count()).select_from(UniversityObservation))
            first = await adapter._probe_site(u, hint)
            assert first is not None
            n1 = s.scalar(select(func.count()).select_from(UniversityObservation))
            second = await adapter._identify_site(u, DiscoveryTrace(institution=u.name, domain=u.domain))
            n2 = s.scalar(select(func.count()).select_from(UniversityObservation))
            fake.at += timedelta(days=2)
            third = await adapter._identify_site(u, DiscoveryTrace(institution=u.name, domain=u.domain))
            n3 = s.scalar(select(func.count()).select_from(UniversityObservation))
            checked_domain = u.domain
            reimport = import_catalogue(s, DOC)
            row['synthetic_identity_reuse'] = {
                'fake_url': hint, 'get_calls_for_three_identifications': len(fake.calls),
                'observation_deltas': [n1-n0, n2-n1, n3-n2],
                'returned_entry_fields': sorted(third),
                'registry_entry_created': bool(u.registry_entry) if row['route'] == 'generic' else 'preexisting_curated',
                'checked_domain_before_reimport': checked_domain,
                'domain_after_reimport': u.domain, 'status_after_reimport': u.domain_status,
                'checked_domain_preserved': u.domain == checked_domain,
                'new_seed_observations_on_reimport': reimport['new_observations']}
            row['tests'] = [dict(test, category='catalogue_retrieval', synthetic=False)
                            for test in tests]
            row['tests'].append({
                'kind': 'identity_reuse_and_reimport',
                'category': 'synthetic_identity',
                'synthetic': True,
                'executed': True,
                'results': deepcopy(row['synthetic_identity_reuse']),
            })
            row['observations'] = []
            if row['route'] == 'generic': row['observations'].append('Generic route repeats homepage identification; learned entry has no programme route seeds. Synthetic checked domain survives seed reimport.')
            else: row['observations'].append('Curated route bypasses runtime identity probing during enrichment; import restores curated domain over synthetic checked identity.')
            if not before_domain: row['observations'].append('No imported domain hint: discovery limitation, not a verified university-site error.')
            failures = [t['kind'] for t in tests if not t['target_present']]
            if failures: row['observations'].append('Measured query misses: ' + ', '.join(failures))
            row['risk'] = 'Repeated discovery cost and route loss after cache expiry; runtime site identity is synthetic and admissions remain unverified.'
            rows.append(row)
        # Validator compares full hosts, importer collapses registrable hosts: synthetic same-site identities accepted.
        changed = deepcopy(DOC)
        chosen = [r for r in changed['universities'] if r['seed_id'] in {rows[0]['seed_id'], rows[1]['seed_id']}]
        for label, r in zip(['one', 'two'], chosen):
            r['official_domain'] = label + '.collision-audit.edu'
            r['official_site'] = 'https://' + r['official_domain'] + '/'
        validate_snapshot(changed)
        e2 = create_engine('sqlite:///:memory:')
        University.__table__.create(e2); UniversityObservation.__table__.create(e2)
        with Session(e2) as s2:
            import_catalogue(s2, changed)
            collision = [{'name': u.name, 'domain': u.domain} for u in s2.scalars(select(University).where(University.domain == 'collision-audit.edu'))]
        e2.dispose()
        with TemporaryDirectory(prefix='group09-offline-') as tmp:
            cache = ResponseCache(Path(tmp))
            url = 'https://cache-audit.edu/catalogue'
            original = FetchResult(url=url, final_url=url, outcome=FetchOutcome.OK, content=b'page', fetch_tier='browser', fetched_at=datetime(2026,10,4,tzinfo=UTC), etag='v1')
            cache.put(original)
            cached = cache.get(url)
            fetcher = Fetcher(Path(tmp), offline=True)
            warm = await fetcher.get(url)
            conditional = await fetcher.get(url, etag='v1')
            cache_results = {'synthetic': True, 'written_tier': original.fetch_tier, 'read_tier': cached.fetch_tier,
                             'same_url_hit': cached is not None, 'trailing_slash_hit': cache.get(url+'/') is not None,
                             'timestamp_preserved': cached.fetched_at == original.fetched_at,
                             'etag_preserved': cached.etag == original.etag,
                             'fetcher_warm_outcome': warm.outcome.value,
                             'fetcher_validator_offline_outcome': conditional.outcome.value,
                             'fetcher_tier_counts': fetcher.tier_counts}
        summary = {'university_rows':len(rows), 'full_import': imported, 'identical_reimport': repeat,
                   'curated': sum(r['route']=='curated' for r in rows),
                   'generic':sum(r['route']=='generic' for r in rows),
                   'domain_missing':sum(r['domain'] is None for r in rows),
                   'exact_target_present':sum(r['retrieval'][0]['target_present'] for r in rows),
                   'canonical_target_present':sum(r['retrieval'][1]['target_present'] for r in rows),
                   'name_country_miss':sum(any(t['kind']=='name_country' and not t['target_present'] for t in r['retrieval']) for r in rows),
                   'checked_identity_preserved_after_reimport':sum(r['synthetic_identity_reuse']['checked_domain_preserved'] for r in rows),
                   'first20_default':sum(r['default_position']<=20 for r in rows),
                   'first40_default':sum(r['default_position']<=40 for r in rows),
                   'baseline_shared_domain_rows':sum(r['domain_identity_count']>1 for r in rows)}
        output = {'group':9,'live_checked':False,'scope':'non-blind offline engineering diagnosis; no admissions verification',
                  'summary':summary,'synthetic_cache':cache_results,'synthetic_subdomain_collision':collision,'rows':rows}
        (OUT/'group-09.rows.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in output.items() if k!='rows'}, ensure_ascii=False, indent=2))
    engine.dispose()

if __name__ == '__main__':
    # Fail closed even if a future code path unexpectedly attempts network I/O.
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('network disabled in offline audit')):
        asyncio.run(main())
