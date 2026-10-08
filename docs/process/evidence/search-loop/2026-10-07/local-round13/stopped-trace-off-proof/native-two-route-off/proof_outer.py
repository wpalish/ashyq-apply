"""Single bounded next-seam proof: native outer Live/Catalogue paths, synthetic gate."""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import inspect
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
PLAN = json.loads((ROOT / 'PLAN.json').read_text())
DENIED = []
DNS = []


def deny(*args, **kwargs):
    DENIED.append('real network attempted')
    raise AssertionError('Forbidden network')


def dns(host, port, *args, **kwargs):
    assert host == 'example.edu'
    DNS.append(str(host))
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('93.184.216.34', port))]


socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
socket.getaddrinfo = dns

import httpx
from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.domain.enums import DegreeLevel
from app.models import University
from app.pipeline.control import UniversityReadStopped
from app.pipeline.read_budget import BudgetedFetcher
from app.schemas.profile import ApplicantProfileIn
import app.catalogue.discovery as catalogue

METHODS = [BudgetedFetcher.get, Fetcher.get, Fetcher._get, FakeSearchProvider.search,
           LiveDiscoveryAdapter.discover, LiveDiscoveryAdapter._discover_one,
           CatalogueDiscoveryAdapter.discover, CatalogueDiscoveryAdapter._enrich]
ENTRY = {'name': 'Example University', 'country': 'Example', 'city': 'City',
         'homepage': 'https://example.edu/'}
NOW = datetime(2026, 10, 8, 4, 30, tzinfo=UTC)
PROFILE = ApplicantProfileIn.model_validate({'context': {'level': 'bachelor',
    'intended_fields': ['Computer Science'], 'intake_year': 2027, 'citizenship': 'KZ',
    'country_of_residence': 'KZ', 'education_country': 'KZ', 'education_system': 'KZ'}})


class TraceSpy:
    """Only records argument identity then delegates the complete native caller."""
    async def _add_search_results(self, entry, domain, selected, trace, profile):
        self.inner_trace_arguments.append(trace)
        return await super()._add_search_results(entry, domain, selected, trace, profile)


class ObservedLive(TraceSpy, LiveDiscoveryAdapter):
    pass


class ObservedCatalogue(TraceSpy, CatalogueDiscoveryAdapter):
    pass


def sources():
    values = {rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest() for rel in PLAN['sources']}
    assert values == {rel: e['sha256'] for rel, e in PLAN['sources'].items()}
    assert hashlib.sha256(Path(PLAN['STOP']['path']).read_bytes()).hexdigest() == PLAN['STOP']['sha256']
    return values


async def one_path(kind):
    read_count = 56  # Existing admitted get invocations, simulated rather than SQL.
    guards, exchanges = [], []
    original = UniversityReadStopped('read_cap')
    dns_start = len(DNS)

    def reserve():
        nonlocal read_count
        event = {'before': read_count, 'admitted': read_count < 60}
        guards.append(event)
        if read_count >= 60:
            event['same_original_stop'] = True
            event['http_exchanges_before_refusal'] = len(exchanges)
            raise original
        read_count += 1
        event['after'] = read_count

    def exchange(request):
        assert request.headers['host'] == 'example.edu' and request.url.host == '93.184.216.34'
        exchanges.append({'method': request.method, 'path': request.url.path})
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /\nSitemap: https://example.edu/sitemap.xml\n', headers={'content-type': 'text/plain'})
        if request.url.path == '/sitemap.xml':
            return httpx.Response(200, text='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>', headers={'content-type': 'application/xml'})
        if request.url.path == '/':
            return httpx.Response(200, text='<html><title>Example University</title><h1>Example University</h1><p>' + 'Welcome to our institution. ' * 30 + '</p></html>', headers={'content-type': 'text/html'})
        raise AssertionError('Unexpected mock resource')

    requested = DiscoveryIntent(ENTRY['name'], 'example.edu', DegreeLevel.BACHELOR, 'Computer Science')
    provider = FakeSearchProvider({q.text: [('https://example.edu/bachelors/computer-science', 'Bachelor Computer Science', '')] for q in queries_for(requested, budget=6)}, now=NOW)
    fetcher = BudgetedFetcher(ROOT / 'runtime' / kind, before_get=reserve, delay_seconds=0)
    uni = University(id='synthetic-offline-university', name=ENTRY['name'], country=ENTRY['country'],
                     city=ENTRY['city'], domain='example.edu', registry_entry=dict(ENTRY))
    if kind == 'catalogue':
        adapter = ObservedCatalogue(fetcher, session=None, university_ids=[uni.id], live_limit=1)
    else:
        adapter = ObservedLive(fetcher, registry_path=ROOT / 'no-registry.json')
    adapter.inner_trace_arguments = []
    adapter._search_provider = provider
    adapter._search_provider_resolved = True
    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange), follow_redirects=False) as client:
        fetcher._client = client
        with patch.object(LiveDiscoveryAdapter, 'registry', lambda _: [dict(ENTRY)]), patch.object(catalogue, 'retrieve', lambda *a, **k: [uni]):
            candidates = await adapter.discover(PROFILE, 1)
        fetcher._client = None
    assert len(candidates) == len(adapter.traces) == len(adapter.inner_trace_arguments) == 1
    outer, inner, candidate = adapter.traces[0], adapter.inner_trace_arguments[0], candidates[0]
    checks = {'six_actual_fake_provider_calls': len(provider.calls) == 6,
              'inner_native_seam_charged_six': inner.search_queries_sent == 6,
              'outer_trace_drops_inner_queries': outer.search_queries_sent == 0,
              'candidate_query_ledger_zero': candidate.search_queries_used == 0,
              'no_applied_programme_or_domain': not candidate.programs and not candidate.domain,
              'honest_unknown_readcap_limit': any('unknown' in x and 'read_cap' in x for x in outer.search_limitations),
              'four_prior_admissions_then_refusal': len(guards) == 5 and sum(x['admitted'] for x in guards) == 4 and read_count == 60,
              'zero_post_refusal_http': len(exchanges) == guards[-1]['http_exchanges_before_refusal'],
              'native_stats_separate_four_completed_gets': sum(fetcher.stats.values()) == 4,
              'catalogue_stable_id_preserved': kind != 'catalogue' or candidate.catalogue_id == uni.id,
              'outer_different_trace': inner is not outer}
    assert all(checks.values()), checks
    return {'kind': kind, 'status': 'CONFIRMED_TRACE_AND_CANDIDATE_LEDGER_TRANSFER_LOSS',
            'checks': checks, 'inner_native_trace': inner.as_dict(), 'exported_native_trace': outer.as_dict(),
            'exported_candidate': dataclasses.asdict(candidate), 'mock_provider_query_calls': provider.calls,
            'simulated_read_count_start': 56, 'simulated_read_count_end': read_count,
            'guard_events': guards, 'native_fetcher_stats': fetcher.stats,
            'native_fetch_tiers': fetcher.tier_counts, 'mock_HTTP_exchanges': exchanges,
            'synthetic_DNS_count': len(DNS)-dns_start,
            'walker_outcomes_remain_separate': [dataclasses.asdict(x) for x in adapter.walker_outcomes],
            'qualified_not_proven': ['No >6 vendor dispatch or later-stage search proven', 'Candidate lacks domain/URLs; requirements topic search currently returns early', 'No SQL reservation/Worker/Job/persisted final report executed', 'Internal exported native trace is final discovery report input, not a complete serialized research run']}


async def main():
    before = sources()
    rows = []
    try:
        for kind in ('curated', 'catalogue'):
            rows.append(await one_path(kind))
    except BaseException as error:
        result = {'status': 'PROOF_FAILURE_PRESERVED', 'exception': type(error).__name__, 'error': str(error), 'completed_paths': rows, 'network_attempts': DENIED}
        (ROOT / 'outcomes.initial-error.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
        raise
    assert METHODS == [BudgetedFetcher.get, Fetcher.get, Fetcher._get, FakeSearchProvider.search,
                       LiveDiscoveryAdapter.discover, LiveDiscoveryAdapter._discover_one,
                       CatalogueDiscoveryAdapter.discover, CatalogueDiscoveryAdapter._enrich]
    assert sources() == before and not DENIED
    methods = [{'name': m.__qualname__, 'module': m.__module__, 'source_file': inspect.getfile(m)} for m in METHODS]
    result = {'paths': rows, 'native_method_imports': methods, 'source_pre_post_equal': True,
              'network_attempts': DENIED, 'qualification': 'Current source inner fix applied; separate next-seam diagnosis. SQL/job states not simulated as successful.'}
    target = ROOT / 'outcomes.original.json'
    assert not target.exists()
    target.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({'paths': len(rows), 'checks_PASS': sum(len(r['checks']) for r in rows), 'network_attempts': len(DENIED)}))


if __name__ == '__main__':
    asyncio.run(main())
