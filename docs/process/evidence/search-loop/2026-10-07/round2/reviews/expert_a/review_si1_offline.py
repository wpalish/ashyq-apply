"""Independent synthetic SI-1 probe review. No network/database/source edits."""
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import app.catalogue.discovery as mod
from app.adapters.fetching import FetchResult, _content_hash
from app.domain.enums import FetchOutcome

OUT = Path(__file__).resolve().parent
SOURCE = Path(mod.__file__)
SOURCE_BYTES = SOURCE.read_bytes()
SOURCE_SHA = hashlib.sha256(SOURCE_BYTES).hexdigest()


class SessionStub:
    def __init__(self):
        self.rows = {}
        self.flushes = 0

    def get(self, model, key):
        return self.rows.get(key)

    def add(self, row):
        self.rows[row.id] = row

    def flush(self):
        self.flushes += 1


class OneSyntheticPage:
    def __init__(self, html, final, fetched_at=None):
        self.html = html
        self.final = final
        self.reads = []
        self.fetched_at = fetched_at or datetime(2026, 10, 7, tzinfo=timezone.utc)

    async def get(self, url, **kwargs):
        self.reads.append(url)
        return FetchResult(url=url, final_url=self.final or url, outcome=FetchOutcome.OK,
                           content=self.html.encode(), text=self.html, content_type='text/html',
                           fetched_at=self.fetched_at)


GENERIC = '<title>Home</title><h1>Welcome to our website</h1>'
CASES = [
    ('exact_og', 'Example University', GENERIC + '<meta property="og:site_name" content="Example University">', 'https://example.edu/', '', True),
    ('article_og', 'University of Witwatersrand', GENERIC + '<meta property="og:site_name" content="University of the Witwatersrand">', 'https://example.edu/', '', True),
    ('exact_owner', 'Example University', GENERIC + '<footer><p>Copyright © 2026 Example University</p></footer>', 'https://example.edu/', '', True),
    ('city_owner', 'Example University', GENERIC + '<footer><p>Copyright © 2026 Example University, Johannesburg.</p></footer>', 'https://example.edu/', '', True),
    ('body_mention', 'Example University', GENERIC + '<main>We partner with Example University.</main>', 'https://example.edu/', '', False),
    ('footer_mention', 'Example University', GENERIC + '<footer><p>We partner with Example University.</p></footer>', 'https://example.edu/', '', False),
    ('owner_elsewhere_in_body', 'Example University', GENERIC + '<main><p>Copyright 2026 Example University</p></main>', 'https://example.edu/', '', False),
    ('longer_owner', 'Example University', GENERIC + '<footer><p>Copyright 2026 Example University Foundation</p></footer>', 'https://example.edu/', '', False),
    ('longer_og', 'Example University', GENERIC + '<meta property="og:site_name" content="Example University Foundation">', 'https://example.edu/', '', False),
    ('different_owner_prefix', 'Example University', GENERIC + '<footer><p>Copyright 2026 Directory Ltd; Example University partner</p></footer>', 'https://example.edu/', '', False),
    ('different_og_prefix', 'Example University', GENERIC + '<meta property="og:site_name" content="News about Example University">', 'https://example.edu/', '', False),
    ('comma_longer_legal_owner', 'Example University', GENERIC + '<footer><p>Copyright 2026 Example University, Inc.</p></footer>', 'https://example.edu/', '', False),
    ('qualified_entity_og', 'Example University (Foundation)', GENERIC + '<meta property="og:site_name" content="Example University">', 'https://example.edu/', '', False),
    ('qualified_entity_owner', 'Example University (Foundation)', GENERIC + '<footer><p>Copyright 2026 Example University</p></footer>', 'https://example.edu/', '', False),
    ('unrelated_host', 'Example University', GENERIC + '<meta property="og:site_name" content="Example University">', 'https://directory.edu/', '', False),
    ('suffix_trick_host', 'Example University', GENERIC + '<meta property="og:site_name" content="Example University">', 'https://example.edu.directory.edu/', '', False),
    ('off_site_redirect', 'Example University', GENERIC + '<meta property="og:site_name" content="Example University">', 'https://example.edu/', 'https://directory.edu/', False),
    ('same_site_subdomain', 'Example University', GENERIC + '<meta property="og:site_name" content="Example University">', 'https://www.example.edu/', 'https://home.example.edu/', True),
    ('legacy_full_title', 'Example University', '<title>Example University</title><h1>Example University</h1>', 'https://example.edu/', '', True),
]


async def probe(name, html, hint, final, enabled, *, domain='example.edu',
                country='Synthetic', city='Johannesburg', fetched_at=None):
    fetcher = OneSyntheticPage(html, final, fetched_at)
    session = SessionStub()
    uni = SimpleNamespace(id='synthetic', name=name, aliases=[], domain=domain,
                          country=country, city=city, domain_status='seed')
    adapter = mod.CatalogueDiscoveryAdapter(fetcher, session=session,
                                            university_ids=[uni.id], live_limit=1)
    old = mod.SITE_BRANDING_IDENTITY
    mod.SITE_BRANDING_IDENTITY = enabled
    try:
        result = await adapter._probe_site(uni, hint)
    finally:
        mod.SITE_BRANDING_IDENTITY = old
    return {'accepted': result is not None, 'entry': result,
            'proofs': [row.payload for row in session.rows.values()],
            'domain_status': uni.domain_status, 'synthetic_reads': fetcher.reads,
            'network_calls': 0, 'provider_calls': 0}


async def main():
    records = []
    for key, name, html, hint, final, wanted in CASES:
        off = await probe(name, html, hint, final, False)
        on = await probe(name, html, hint, final, True)
        records.append({'case': key, 'name': name, 'html': html, 'hint': hint,
                        'final': final, 'expected_enabled_acceptance': wanted,
                        'feature_off': off, 'feature_on': on,
                        'pass': on['accepted'] == wanted})
    retained = []
    parent_path = OUT.parents[1] / 'site-identity-replay.offline.json'
    parent_bytes = parent_path.read_bytes()
    parent = json.loads(parent_bytes)
    for row in parent['rows']:
        body_path = Path(row['retained_body_path'])
        metadata_path = body_path.with_suffix('.meta.json')
        body, meta_bytes = body_path.read_bytes(), metadata_path.read_bytes()
        metadata = json.loads(meta_bytes)
        html = body.decode('utf8')
        uni = row['outcomes']['current_on']
        kwargs = dict(domain=row['proof']['domain'], country=uni['country'], city=uni['city'],
                      fetched_at=datetime.fromisoformat(metadata['fetched_at']))
        off = await probe(uni['name'], html, metadata['url'], metadata['final_url'], False, **kwargs)
        on = await probe(uni['name'], html, metadata['url'], metadata['final_url'], True, **kwargs)
        assert not off['accepted'] and on['accepted']
        assert on['proofs'][0]['excerpt'] == row['proof']['excerpt']
        assert on['proofs'][0]['identity_basis'] == row['proof']['identity_basis']
        assert body_path.read_bytes() == body and metadata_path.read_bytes() == meta_bytes
        assert hashlib.sha256(body).hexdigest() == row['raw_sha256']
        assert _content_hash(html) == metadata['content_hash'] == row['normalized_content_hash']
        retained.append({'case_id': row['case_id'], 'body_path': str(body_path),
                         'body_sha256': hashlib.sha256(body).hexdigest(),
                         'metadata_sha256': hashlib.sha256(meta_bytes).hexdigest(),
                         'normalized_hash_verified': True, 'originals_unchanged': True,
                         'current_off': off, 'current_on': on, 'parent_excerpt_and_basis_match': True})
    assert SOURCE.read_bytes() == SOURCE_BYTES
    (OUT / 'si1-reviewed-discovery.source.py.txt').write_bytes(SOURCE_BYTES)
    failures = [r['case'] for r in records if not r['pass']]
    result = {'at': datetime.now(timezone.utc).isoformat(),
              'mode': 'Independent actual _probe_site synthetic offline replay, memory session only',
              'source_path': str(SOURCE), 'source_sha256': SOURCE_SHA,
              'default_flag_false': mod.SITE_BRANDING_IDENTITY is False,
              'source_unchanged': True, 'cases': records, 'failed_cases': failures,
              'current_retained_source_replays': retained,
              'parent_replay_json': {'path': str(parent_path), 'sha256': hashlib.sha256(parent_bytes).hexdigest(),
                                     'source_hashes_recorded': parent['source_file_sha256']},
              'network_calls': 0, 'provider_calls': 0,
              'legacy_proof_identical_off_on': records[-1]['feature_off']['proofs'] == records[-1]['feature_on']['proofs']}
    (OUT / 'si1-site-identity.offline.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'source_sha256': SOURCE_SHA, 'cases': len(records),
                      'failed_cases': failures, 'source_unchanged': True,
                      'network_calls': 0, 'provider_calls': 0,
                      'current_retained_replays_passed': len(retained),
                      'legacy_proof_identical_off_on': result['legacy_proof_identical_off_on']}))


asyncio.run(main())
