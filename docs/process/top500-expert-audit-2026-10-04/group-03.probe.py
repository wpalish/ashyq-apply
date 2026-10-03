"""Offline non-blind engineering audit. Run from repository root; no provider calls.
All identity/route responses are synthetic spies, never admissions evidence.
"""
from __future__ import annotations
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.catalogue.importer import SEED_PATH, import_catalogue, identity_key, seed_domain
from app.catalogue.retrieval import retrieve
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter, DiscoveryTrace
from app.domain.site_identity import registrable_domain
from app.models import Base, University
from urllib.parse import urlsplit

OUT = Path(__file__).with_name('group-03.rows.json')
PACKET = Path(__file__).with_name('group-03.packet.json')

def blocked(*args, **kwargs):
    raise AssertionError('Network prohibited in group-03 audit')

async def run():
    packet = json.loads(PACKET.read_text())
    assert len(packet['universities']) == 50
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    profile = SimpleNamespace(preferences=SimpleNamespace(preferred_countries=[], excluded_countries=[]), context=SimpleNamespace(level='bachelor', intended_fields=['Computer Science']))
    with Session(engine) as session:
        imported = import_catalogue(session)
        session.flush()
        all_rows = retrieve(session)
        by_key = {u.identity_key: u for u in all_rows}
        global_positions = {u.id: i + 1 for i, u in enumerate(all_rows)}
        packet_ids = [by_key[identity_key(r['name'], r['country'])].id for r in packet['universities']]
        group_positions = {u.id: i + 1 for i, u in enumerate(retrieve(session, university_ids=packet_ids))}
        second_import = import_catalogue(session)
        attempted = []
        adapter = CatalogueDiscoveryAdapter(SimpleNamespace(get=blocked), session=session, university_ids=None, live_limit=20)
        async def spy_enrich(uni, profile, candidate, trace):
            attempted.append(uni.id)
            return candidate, trace
        adapter._enrich = spy_enrich
        discovered = await adapter.discover(profile, limit=40)
        results = []
        for row in packet['universities']:
            uni = by_key[identity_key(row['name'], row['country'])]
            aliases = {a: [x.id for x in retrieve(session, query=a)] for a in uni.aliases}
            full = retrieve(session, query=row['name'])
            canonical = retrieve(session, query=uni.name)
            country = retrieve(session, country=row['country'])
            preferred = retrieve(session, preferred=[row['country']])
            pref_pos = next(i + 1 for i, x in enumerate(preferred) if x.id == uni.id)
            selected = retrieve(session, university_ids=[uni.id])
            route_events = []
            route_adapter = CatalogueDiscoveryAdapter(SimpleNamespace(get=blocked), session=session, university_ids=[uni.id], live_limit=1)
            async def identify(u, trace):
                route_events.append('identify_site')
                # Synthetic successful identity response, no site verification.
                return {'name': u.name, 'country': u.country, 'homepage': 'https://audit.example.org/'}
            async def discover_one(entry, p):
                route_events.append('discover_one_with_seeds' if entry.get('seeds') else 'discover_one_without_seeds')
                from app.adapters.base import Candidate
                return Candidate(name=uni.name, country=uni.country, city=uni.city), DiscoveryTrace(institution=uni.name, domain='')
            route_adapter._identify_site = identify
            route_adapter._discover_one = discover_one
            await route_adapter.discover(profile, limit=1)
            domain = row.get('official_domain')
            host = urlsplit(row.get('official_site') or '').hostname
            conflict = bool(domain and host and registrable_domain(domain) != registrable_domain(host))
            observations = []
            if not uni.registry_entry:
                observations.append('Generic identity route; no curated programme/admissions entry points.')
            else:
                observations.append('Curated registry route; seed facts remain unverified.')
            if not uni.domain:
                observations.append('No usable imported domain; identity hints/provider become prerequisite when scheduled.')
            if conflict:
                observations.append('Seed domain and website registrable domains conflict; importer rejects domain hint.')
            if global_positions[uni.id] > 40:
                observations.append('Outside default 40-candidate window with no preferences.')
            elif global_positions[uni.id] > 20:
                observations.append('Retained as candidate but outside default 20-live window with no preferences.')
            if row['name'] != uni.name:
                observations.append('Canonical name differs; full source name retained as searchable alias.')
            ambiguous = {k: len(v) for k, v in aliases.items() if len(v) > 1}
            if ambiguous:
                observations.append('One or more alias token queries retrieve multiple institutions.')
            tests = {
                'imported_identity': True,
                'full_name_retrieves_identity': uni.id in {x.id for x in full},
                'canonical_retrieves_identity': uni.id in {x.id for x in canonical},
                'all_aliases_retrieve_identity': all(uni.id in ids for ids in aliases.values()),
                'country_alias_retrieves_identity': uni.id in {x.id for x in country},
                'country_exclusion_removes_identity': uni.id not in {x.id for x in retrieve(session, excluded=[row['country']])},
                'explicit_id_retrieval_exact': len(selected) == 1 and selected[0].id == uni.id,
                'observation_remains_unverified': uni.seed_snapshot['verification_status'] == 'unverified_seed',
                'routing_matches_registry': ('identify_site' in route_events) == (uni.registry_entry is None),
            }
            assert all(tests.values()), (row['seed_id'], tests)
            results.append({'seed_id': row['seed_id'], 'name': row['name'], 'canonical_name': uni.name, 'country': uni.country, 'aliases': uni.aliases, 'domain': uni.domain, 'domain_status': uni.domain_status, 'seed_hint_conflict': conflict, 'imported_seed_domain': seed_domain(row), 'registry_covered': bool(uni.registry_entry), 'registry_seed_categories': sorted((uni.registry_entry or {}).get('seeds', {})), 'global_position': global_positions[uni.id], 'group_position': group_positions[uni.id], 'country_preferred_position': pref_pos, 'default_live_attempted_synthetic_spy': uni.id in attempted, 'full_name_matches': len(full), 'ambiguous_alias_queries': ambiguous, 'synthetic_route_events': route_events, 'tests': tests, 'observations': observations, 'risk': 'high' if not uni.domain or global_positions[uni.id] > 40 else 'medium', 'live_checked': False})
        # Real stage orchestrator with synthetic no-op stages: proves ordering only.
        stages = []
        stage_adapter = LiveDiscoveryAdapter(SimpleNamespace(get=blocked))
        async def collect(*args, **kwargs): stages.append('sitemaps'); return []
        stage_adapter.sitemaps.collect = collect
        for name, label in [('_navigation_fallback','navigation'),('_confirm_programs','confirmation'),('_walk_catalogs','catalogue_walker'),('_add_search_results','search_stage')]:
            async def stage(*args, _label=label, **kwargs): stages.append(_label)
            setattr(stage_adapter, name, stage)
        stage_adapter._apply = lambda *args: None
        await stage_adapter._discover_one({'name':'Synthetic University','country':'Test Country','homepage':'https://audit.example.org/'}, profile)
        metrics = {'audited_rows':len(results), 'test_assertions_passed':sum(len(r['tests']) for r in results), 'registry_covered':sum(r['registry_covered'] for r in results), 'generic_route':sum(not r['registry_covered'] for r in results), 'domain_status':dict(Counter(r['domain_status'] for r in results)), 'seed_hint_conflicts':sum(r['seed_hint_conflict'] for r in results), 'default_candidate_window_40':sum(r['global_position']<=40 for r in results), 'default_live_window_20':sum(r['default_live_attempted_synthetic_spy'] for r in results), 'country_preferred_live_window_20':sum(r['country_preferred_position']<=20 for r in results), 'canonical_names_changed':sum(r['name'] != r['canonical_name'] for r in results), 'ambiguous_alias_rows':sum(bool(r['ambiguous_alias_queries']) for r in results), 'live_checked':0}
        document = {'audit':'Non-blind offline engineering audit; seed facts unverified', 'source_sha':packet['source_sha'], 'seed_sha256':hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(), 'import':imported, 'second_import_new_observations':second_import['new_observations'], 'default_spy_candidates':len(discovered), 'default_spy_live_attempts':len(attempted), 'synthetic_stage_order':stages, 'metrics_within_group':metrics, 'rows':results}
        OUT.write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        print('Synthetic stage order:', stages)
    engine.dispose()

if __name__ == '__main__':
    with patch.object(socket.socket, 'connect', blocked), patch.object(socket, 'create_connection', blocked):
        asyncio.run(run())
