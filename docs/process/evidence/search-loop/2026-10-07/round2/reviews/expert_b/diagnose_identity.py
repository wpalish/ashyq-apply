"""Read-only retained-page reproduction; no network or repository writes."""

from __future__ import annotations

import asyncio
import ast
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from types import MethodType, SimpleNamespace

from bs4 import BeautifulSoup

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.catalogue import discovery as module
from app.catalogue.importer import canonical_name
from app.domain.dedupe import normalize

WORK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work')
REPO = WORK / 'ashyq-apply'
OUT = WORK / 'search-loop-round2/reviews/expert_b'
WITS = '0386940c5cef525b3c8e7966868f5ed6'
CALTECH = '05e4d59f87261553f15d14b0cdb470d2'
CASES = [
    ('baseline', WITS, 'development-baseline/20261007T164735Z', 'development-baseline-temp/canary-lsaouqcu'),
    ('baseline', CALTECH, 'development-baseline/20261007T164735Z', 'development-baseline-temp/canary-bostmz9k'),
    ('repeat', WITS, 'scope-fix-repeat/20261007T172952Z', 'scope-fix-repeat-temp/canary-dfflsxvu'),
    ('repeat', CALTECH, 'scope-fix-repeat/20261007T172952Z', 'scope-fix-repeat-temp/canary-xnrq_uq6'),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def functions(path: Path, names: set[str]) -> dict:
    source = path.read_text()
    lines = source.splitlines(keepends=True)
    return {
        node.name: {
            'line': node.lineno,
            'end_line': node.end_lineno,
            'sha256': hashlib.sha256(''.join(lines[node.lineno - 1:node.end_lineno]).encode()).hexdigest(),
        }
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    }


class MemorySession:
    def __init__(self):
        self.proofs = []
        self.flushes = 0

    def get(self, _model, _key):
        return None

    def add(self, observation):
        self.proofs.append(observation.payload)

    def flush(self):
        self.flushes += 1


class PageReplay:
    def __init__(self, pages: dict, failures: dict):
        self.pages = pages
        self.failures = failures
        self.calls = []

    async def get(self, url):
        self.calls.append(url)
        if url in self.pages:
            return self.pages[url]
        if url in self.failures:
            return SimpleNamespace(ok=False, final_url=url)
        raise AssertionError(f'Unretained URL requested: {url}')


class RootDiscoveryReplay:
    """Synthetic discovery responses use observed roots, not unretained snippets."""

    def __init__(self, roots):
        self.roots = roots
        self.calls = []

    async def search(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(results=[SimpleNamespace(url=url) for url in self.roots])


async def main():
    source_names = [
        'backend/app/catalogue/discovery.py',
        'backend/app/catalogue/retrieval.py',
        'backend/app/adapters/discovery/live_discovery.py',
        'backend/app/adapters/discovery/catalog_walker.py',
        'backend/app/adapters/search/retrieval.py',
        'backend/evaluation/research/live.py',
    ]
    before = {name: digest(REPO / name) for name in source_names}
    stop = WORK / 'development-STOP.json'
    stop_before = digest(stop) if stop.exists() else None
    old_get_provider = module.get_search_provider
    old_flag = module.SITE_BRANDING_IDENTITY
    results = []
    try:
        for label, uid, capture_folder, cache_folder in CASES:
            capture = WORK / capture_folder
            temp = WORK / cache_folder
            db_path = temp / 'canary.db'
            db_before = digest(db_path)
            database = sqlite3.connect(f'file:{db_path}?mode=ro&immutable=1', uri=True)
            database.row_factory = sqlite3.Row
            row = dict(database.execute(
                'SELECT id,name,country,city,aliases,domain,domain_status,registry_entry,seed_snapshot '
                'FROM universities WHERE id=?', (uid,),
            ).fetchone())
            database.close()
            for name in ['aliases', 'registry_entry', 'seed_snapshot']:
                row[name] = json.loads(row[name]) if row[name] is not None else None
            raw_path = capture / f'{uid}.raw.json'
            observation = json.loads(raw_path.read_text())['canary']['institutions'][0]
            budget_path = capture / f'{uid}.budget.json'
            budget = json.loads(budget_path.read_text())
            pages, cache_evidence = {}, []
            for meta_path in sorted((temp / 'cache').rglob('*.meta.json')):
                meta = json.loads(meta_path.read_text())
                body_path = meta_path.with_name(meta_path.name.replace('.meta.json', '.body'))
                body = body_path.read_bytes()
                text = body.decode(meta.get('encoding', 'utf-8'), errors='replace')
                pages[meta['url']] = SimpleNamespace(
                    ok=True, content=body, text=text, final_url=meta['final_url'],
                    fetched_at=datetime.fromisoformat(meta['fetched_at']),
                )
                soup = BeautifulSoup(body, 'html.parser')
                title = soup.title.get_text(' ', strip=True) if soup.title else ''
                headings = [h.get_text(' ', strip=True) for h in soup.find_all('h1')]
                copyright_blocks = [
                    node.get_text(' ', strip=True) for node in soup.select('footer p, footer small')
                    if 'copyright' in node.get_text().lower() or '©' in node.get_text()
                ]
                cache_evidence.append({
                    'url': meta['url'], 'final_url': meta['final_url'], 'status_code': meta['status_code'],
                    'meta_path': str(meta_path), 'meta_sha256': digest(meta_path),
                    'body_path': str(body_path), 'body_sha256': digest(body_path),
                    'fetcher_content_hash': meta['content_hash'], 'title': title, 'h1': headings,
                    'original_identity_text': normalize(f'{title} {" ".join(headings)}'),
                    'og_site_names': [str(m.get('content') or '') for m in soup.select('meta[property="og:site_name"]')],
                    'copyright_blocks': copyright_blocks,
                })
            failures = dict(observation['failures'])
            roots = ['https://www.wits.ac.za/'] if uid == WITS else [
                'https://www.caltech.edu/',
                'https://catalog-prod.resources.caltech.edu/' if label == 'baseline' else 'https://en.wikipedia.org/',
            ]
            modes = []
            for enabled in [False, True]:
                uni = SimpleNamespace(**row)
                replay = PageReplay(pages, failures)
                provider = RootDiscoveryReplay(roots)
                module.get_search_provider = lambda: provider
                module.SITE_BRANDING_IDENTITY = enabled
                adapter = object.__new__(module.CatalogueDiscoveryAdapter)
                adapter.fetcher = replay
                adapter.session = MemorySession()
                entered = []

                async def downstream_marker(self, entry, profile):
                    entered.append(entry)
                    return Candidate(name=uni.name, country=uni.country, city=uni.city,
                                     domain=uni.domain, discovery_source='offline-stage-entry-marker'), DiscoveryTrace(
                                         institution=uni.name, domain=uni.domain)

                adapter._discover_one = MethodType(downstream_marker, adapter)
                candidate, trace = await adapter._enrich(
                    uni, SimpleNamespace(), Candidate(name=uni.name, country=uni.country, city=uni.city),
                    DiscoveryTrace(institution=uni.name, domain=uni.domain),
                )
                modes.append({
                    'enabled': enabled, 'homepage_probe_urls': replay.calls,
                    'offline_fetch_calls': len(replay.calls), 'synthetic_provider_queries': provider.calls,
                    'downstream_stage_entered': bool(entered), 'entry': entered,
                    'proofs_memory_only': adapter.session.proofs,
                    'candidate_programmes': [p.url for p in candidate.programs],
                    'limitations': trace.search_limitations,
                })
                assert bool(entered) is enabled, (label, uid, enabled)
                assert not candidate.programs
            assert db_before == digest(db_path)
            results.append({
                'capture': label, 'case_id': uid, 'capture_path': str(capture),
                'raw_sha256': digest(raw_path), 'budget_sha256': digest(budget_path),
                'db_path': str(db_path), 'db_sha256': db_before, 'db_unchanged': True,
                'identity_record': {k:row[k] for k in ['id','name','aliases','country','city','domain','domain_status','registry_entry']},
                'seed_official_site': row['seed_snapshot']['record']['official_site'],
                'normalized_known_names': [normalize(canonical_name(n)) for n in [row['name'], *row['aliases']]],
                'recorded_fetcher_calls': budget['fetcher_calls'], 'recorded_search_queries': budget['search_queries'],
                'recorded_elapsed_ms': budget['elapsed_ms'], 'recorded_stop_reason': budget['stop_reason'],
                'recorded_provider_failure': budget['provider_failure'],
                'institution_pages_checked': observation['pages_checked'],
                'institution_failures': observation['failures'], 'discovery_trace': observation['discovery_trace'],
                'cache_evidence': cache_evidence, 'offline_reproduction': modes,
                'reconstruction_limit': 'Provider root lists are synthetic from observed roots; original response text/order was not retained. Stage-entry marker is not programme verification.',
            })
    finally:
        module.get_search_provider = old_get_provider
        module.SITE_BRANDING_IDENTITY = old_flag
    after = {name: digest(REPO / name) for name in source_names}
    stop_after = digest(stop) if stop.exists() else None
    payload = {
        'network_calls': 0, 'provider_network_calls': 0,
        'source_sha_before': before, 'source_sha_after': after, 'source_unchanged': before == after,
        'source_functions': functions(REPO / source_names[0], {'_enrich', '_identify_site', '_probe_site', '_site_branding'}),
        'shared_stop_before': stop_before, 'shared_stop_after': stop_after, 'shared_stop_unchanged': stop_before == stop_after,
        'cases': results,
    }
    assert before == after and stop_before == stop_after
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'diagnosis-and-replay.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps({
        'source_sha': before, 'network_calls': 0, 'shared_stop_unchanged': True,
        'cases': [{'capture':r['capture'],'case_id':r['case_id'],
                   'recorded_fetcher_calls':r['recorded_fetcher_calls'],
                   'off_calls':r['offline_reproduction'][0]['offline_fetch_calls'],
                   'on_calls':r['offline_reproduction'][1]['offline_fetch_calls'],
                   'off_entered':r['offline_reproduction'][0]['downstream_stage_entered'],
                   'on_entered':r['offline_reproduction'][1]['downstream_stage_entered']} for r in results],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
