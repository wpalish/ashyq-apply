"""Lean independent normal-import cases; no author fixture/test imports."""

import asyncio
import dataclasses
import hashlib
import inspect
import json
import socket
import sys
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

OWN = Path(__file__).resolve().parent
MODE = sys.argv[1]
ATTEMPT = sys.argv[2] if len(sys.argv) > 2 else 'attempt1'
BACKEND = OWN / 'runtime' / MODE / 'backend'
DENIED = []


def deny(*args, **kwargs):
    DENIED.append(True)
    raise AssertionError('Forbidden real transport')


def dns(host, port, *args, **kwargs):
    assert host in {'example.edu', 'dept.example.edu', 'second.edu'}
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('93.184.216.34', port))]


socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
socket.getaddrinfo = dns

import httpx

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.catalogue import discovery as catalogue
from app.domain.enums import DegreeLevel
from app.domain.site_identity import registrable_domain
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.read_budget import BudgetedFetcher
from app.schemas.profile import ApplicantProfileIn

METHODS = [LiveDiscoveryAdapter.discover, LiveDiscoveryAdapter._discover_one,
           catalogue.CatalogueDiscoveryAdapter.discover, catalogue.CatalogueDiscoveryAdapter._enrich,
           BudgetedFetcher.get, Fetcher.get, Fetcher._get, FakeSearchProvider.search]
assert all(Path(inspect.getfile(method)).is_relative_to(BACKEND) for method in METHODS)
SOURCE_PATHS = set(Path(inspect.getfile(method)) for method in METHODS)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PROFILE = ApplicantProfileIn.model_validate({'context': {'level': 'bachelor', 'intended_fields': ['Computer Science'], 'intake_year': 2027, 'citizenship': 'KZ', 'country_of_residence': 'KZ', 'education_country': 'KZ', 'education_system': 'KZ'}})
ENTRY = {'name': 'Example University', 'country': 'Example', 'city': 'City', 'homepage': 'https://example.edu/'}


async def run_native(label, *, kind='catalogue', mode='cap', alias=False, signal=None, repeat=False, second=False):
    entries = [dict(ENTRY)]
    if alias:
        entries[0]['homepage'] = 'https://dept.example.edu/'
    if second:
        entries.append({'name': 'Second University', 'country': 'Example', 'city': 'City', 'homepage': 'https://second.edu/'})
    events, exchanges, outer_observers = [], [], []
    counts = {}
    current = None
    original = signal if signal is not None else UniversityReadStopped('read_cap')

    @contextmanager
    def scope(candidate):
        nonlocal current
        current = candidate.name
        counts[current] = 60 if mode.startswith('identity') else 56 if mode in {'cap', 'control'} else 0
        if second and current == 'Second University':
            raise original
        yield

    def reserve():
        before = counts[current]
        refused = before >= 60
        events.append({'institution': current, 'before': before, 'admitted': not refused, 'exchanges_before': len(exchanges)})
        if refused:
            raise original
        counts[current] += 1

    query_map = {}
    rows = []
    for index, entry in enumerate(entries):
        registry = dict(entry)
        if alias:
            registry['name'] = 'Registry Alias University'
        host = entry['homepage'].split('/')[2]
        intent = DiscoveryIntent(registry['name'], registrable_domain(host) or host, DegreeLevel.BACHELOR, 'Computer Science')
        for query in queries_for(intent, budget=6):
            query_map[query.text] = [] if mode == 'private' else [(entry['homepage'] + 'bachelors/computer-science', 'Bachelor Computer Science', '')]
        query_map[f'"{entry["name"]}" "{entry["country"]}" official university website'] = [(entry['homepage'], entry['name'], '')]
        rows.append(SimpleNamespace(id=f'own-{index}', name=entry['name'], country=entry['country'], city=entry['city'], domain='' if mode == 'identity-after-query' else registrable_domain(host) or host, registry_entry=None if mode.startswith('identity') else registry, aliases=[], seed_snapshot={}))

    def exchange(request):
        host = request.headers['host']
        assert host in {e['homepage'].split('/')[2] for e in entries} and request.url.host == '93.184.216.34'
        exchanges.append({'host': host, 'path': request.url.path})
        if request.url.path == '/robots.txt':
            body = f'User-agent: *\nAllow: /\nSitemap: https://{host}/sitemap.xml\n'
            content_type = 'text/plain'
        elif request.url.path == '/sitemap.xml':
            body = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
            content_type = 'application/xml'
        elif request.url.path == '/bachelors/computer-science':
            body = '<html><title>Bachelor Computer Science</title><h1>Bachelor Computer Science</h1><p>This bachelor degree has a curriculum in algorithms and computing.</p><p>' + 'Study computer science at this university. ' * 30 + '</p></html>'
            content_type = 'text/html'
        else:
            name = next(e['name'] for e in entries if e['homepage'].split('/')[2] == host)
            body = f'<html><title>{name}</title><h1>{name}</h1><p>' + 'Welcome to our university. ' * 30 + '</p></html>'
            content_type = 'text/html'
        return httpx.Response(200, text=body, headers={'content-type': content_type})

    class ObservedCatalogue(catalogue.CatalogueDiscoveryAdapter):
        async def _enrich(self, uni, applicant, candidate, trace):
            if alias:
                # Synthetic prior-spend input, not a claim of SQL persistence.
                trace.search_queries_sent = 1
                candidate.search_queries_used = 4
                trace.search_failures.append('Prior identity diagnostic')
                trace.search_limitations.append('Prior identity limitation')
            outer_observers.append(trace)
            return await super()._enrich(uni, applicant, candidate, trace)

    provider = FakeSearchProvider(query_map, now=datetime(2026, 10, 8, tzinfo=UTC))
    fetcher = BudgetedFetcher(OWN / 'runtime-data' / ATTEMPT / MODE / label, before_get=reserve, delay_seconds=0)
    if kind == 'curated':
        adapter = LiveDiscoveryAdapter(fetcher, registry_path=OWN/'unused.json', research_scope=scope)
    else:
        session = SimpleNamespace(get=lambda *a: None, add=lambda *a: None, flush=lambda: None)
        adapter = ObservedCatalogue(fetcher, session=session, university_ids=[r.id for r in rows], live_limit=len(rows), research_scope=scope)
    adapter._search_provider, adapter._search_provider_resolved = provider, True
    captured, error, first_trace = [], None, None
    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange), follow_redirects=False) as client:
        fetcher._client = client
        try:
            with patch.object(LiveDiscoveryAdapter, 'registry', lambda _: entries), patch.object(catalogue, 'retrieve', lambda *a, **k: rows), patch.object(catalogue, 'get_search_provider', lambda: provider):
                for _ in range(2 if repeat else 1):
                    if mode == 'private':
                        current = ENTRY['name']; counts[current] = 0
                        candidate, trace = await adapter._discover_one(ENTRY, PROFILE, search_queries_used=3)
                        candidates, traces = [candidate], [trace]
                    else:
                        candidates = await adapter.discover(PROFILE, len(entries))
                        traces = adapter.traces
                    if first_trace is None:
                        first_trace = traces[0]
                    captured.append({'candidates': [dataclasses.asdict(c) for c in candidates], 'traces': deepcopy([t.as_dict() for t in traces])})
        except BaseException as caught:
            error = caught
        finally:
            fetcher._client = None
    checks = {'zero_real_network': not DENIED, 'native_methods_unchanged': METHODS == [LiveDiscoveryAdapter.discover, LiveDiscoveryAdapter._discover_one, catalogue.CatalogueDiscoveryAdapter.discover, catalogue.CatalogueDiscoveryAdapter._enrich, BudgetedFetcher.get, Fetcher.get, Fetcher._get, FakeSearchProvider.search]}
    if signal is not None:
        checks.update({'same_original_control_object': error is signal, 'no_phantom_completed_output': captured == [] and adapter.traces == [], 'no_HTTP_after_refusal': not events or len(exchanges) == events[-1]['exchanges_before']})
    else:
        checks['no_unexpected_exception'] = error is None
        if captured:
            candidate, trace = captured[0]['candidates'][0], captured[0]['traces'][0]
            expected = 1 if mode == 'identity-after-query' else 0 if mode == 'identity-before-read' else 6
            checks.update({'honest_spent_count': candidate['search_queries_used'] == trace['search_queries_attempted'] == expected, 'no_fake_HTTP_counter_field': 'vendor_http_requests' not in trace})
            if mode in {'cap', 'identity-before-read', 'identity-after-query'}:
                checks.update({'unknown_seed_programmes_domain': candidate['programs'] == [] and candidate['domain'] == '', 'stopped_report_input_owned': trace['institution'] == candidate['name'], 'original_readcap_unknown_reason': any('read_cap' in s and 'unknown' in s for s in trace['search_limitations']), 'no_HTTP_after_refusal': len(exchanges) == events[-1]['exchanges_before']})
            if alias:
                checks.update({'prefix_failure_once': trace['search_failures'] == ['Prior identity diagnostic'], 'prefix_limitation_once': trace['search_limitations'].count('Prior identity limitation') == 1, 'latest_subdomain_retained': trace['domain'] == 'dept.example.edu', 'max_prior_not_sum': len(provider.calls) == 2})
                if mode == 'success':
                    checks['normal_alias_identity_retained'] = trace['institution'] == candidate['name'] == 'Registry Alias University'
            if mode.startswith('identity'):
                checks.update({'query_before_IO_count': len(provider.calls) == expected, 'no_HTTP_no_DNS_IO': not exchanges, 'one_original_before_get_refusal': len(events) == 1})
            if second:
                last_candidate, last_trace = captured[0]['candidates'][1], captured[0]['traces'][1]
                checks.update({'first_success_kept': bool(candidate['programs']), 'next_scope_unobserved_zero': last_candidate['search_queries_used'] == last_trace['search_queries_attempted'] == 0 and last_trace['sitemaps_read'] == [] and last_trace['field_sources'] == {}, 'ids_owned': [c['catalogue_id'] for c in captured[0]['candidates']] == ['own-0','own-1'], 'next_unknown_seed': last_candidate['domain'] == '' and last_candidate['programs'] == [], 'next_trace_identity_owned': last_trace['institution'] == last_candidate['name'] == 'Second University', 'lists_not_shared': adapter.traces[0].errors is not adapter.traces[1].errors})
            if repeat:
                checks.update({'each_run_spent_six': [r['candidates'][0]['search_queries_used'] for r in captured] == [6,6], 'query_seams_each_run_six_not_vendorHTTP': len(provider.calls) == 12, 'trace_object_fresh': first_trace is not adapter.traces[0], 'previous_trace_snapshot_stable': first_trace.as_dict() == captured[0]['traces'][0], 'previous_limit_list_independent': first_trace.search_limitations is not adapter.traces[0].search_limitations})
            if mode == 'private':
                checks['default_optional_trace_direct_call'] = len(provider.calls) == 3 and candidate['search_queries_used'] == 6
    return {'case': label, 'checks': checks, 'captured': captured, 'exception': None if error is None else {'type': type(error).__name__, 'reason': getattr(error, 'reason', None), 'same_original': error is original}, 'query_seam_calls': provider.calls, 'before_get_events': events, 'mock_HTTP': exchanges, 'native_fetcher_stats': dict(fetcher.stats), 'native_tiers': dict(fetcher.tier_counts), 'qualified': 'Native source confirmation/query/get methods; scope/reservation simulated, no SQL or vendor HTTP. Prefix input observer delegates native _enrich.'}


async def compatibility():
    fetcher = SimpleNamespace()
    adapter = catalogue.CatalogueDiscoveryAdapter(fetcher, session=None, university_ids=['mock'], live_limit=1)
    uni = SimpleNamespace(id='mock', registry_entry=dict(ENTRY))
    candidate = Candidate(ENTRY['name'], ENTRY['country'], ENTRY['city'], search_queries_used=2)
    trace = DiscoveryTrace(ENTRY['name'], 'example.edu', search_queries_sent=1)
    trace.search_failures.append('prior'); trace.search_limitations.append('prior limitation')
    received = []
    async def legacy_mock(entry, profile, **kwargs):
        received.append(kwargs['search_queries_used'])
        other = DiscoveryTrace(ENTRY['name'], 'example.edu', search_queries_sent=3)
        other.search_failures.append('inner'); other.search_limitations.append('inner limitation')
        return Candidate(ENTRY['name'], ENTRY['country'], ENTRY['city'], search_queries_used=3), other
    with patch.object(adapter, '_discover_one', legacy_mock):
        found, returned = await adapter._enrich(uni, PROFILE, candidate, trace)
    checks = {'existing_kwargs_mock_compatible': received == [2], 'fresh_returned_trace_honoured': returned is not trace, 'prefix_and_returned_diagnostics_once': returned.search_failures == ['prior', 'inner'] and returned.search_limitations == ['prior limitation', 'inner limitation'], 'returned_candidate_preserved': found.catalogue_id == 'mock' and found.search_queries_used == 3}
    return {'case':'legacy-mock-new-trace', 'checks':checks, 'candidate':dataclasses.asdict(found), 'trace':returned.as_dict(), 'qualification':'Explicit compatibility-only private mock; not native confirmation proof. Original six tests untouched.'}


async def main():
    before = {str(p): sha(p) for p in SOURCE_PATHS}
    cases = [('alias-cap', {'alias':True}), ('alias-success', {'alias':True,'mode':'success'}), ('before-identity-get', {'mode':'identity-before-read'}), ('after-identity-query-before-IO', {'mode':'identity-after-query'}), ('first-success-next-enter-stop', {'mode':'success','second':True}), ('curated-repeated-cap', {'kind':'curated','repeat':True}), ('catalogue-cancel', {'mode':'control','signal':RunCancelled('synthetic')}), ('curated-lease', {'kind':'curated','mode':'control','signal':LeaseLost('synthetic')}), ('catalogue-async', {'mode':'control','signal':asyncio.CancelledError()}), ('identity-busy', {'mode':'identity-after-query','signal':UniversityReadStopped('checkpoint_busy')}), ('private-default', {'kind':'curated','mode':'private'})]
    rows = []
    for label, kwargs in cases:
        try:
            rows.append(await run_native(label, **kwargs))
        except BaseException as caught:
            rows.append({'case':label, 'fixture_error':{'type':type(caught).__name__, 'message':str(caught)}, 'checks':{}})
    rows.append(await compatibility())
    assert before == {str(p):sha(p) for p in SOURCE_PATHS}
    assert not DENIED
    target = OWN / f'peer.{MODE}.original.json'; assert not target.exists()
    results = {'mode':MODE,'rows':rows,'source_pre_post_sha256':before,'native_method_imports':[{'module':m.__module__,'method':m.__qualname__,'file':inspect.getfile(m)} for m in METHODS],'denied_real_network_attempts':DENIED,'scope':'Independent finite peer, no author test/helpers; no canary/gather/scorer/SQL/Worker or primary/source writes.'}
    target.write_text(json.dumps(results,indent=2)+'\n')
    count = sum(len(r['checks']) for r in rows); red = sum(not check for r in rows for check in r['checks'].values()); errors = sum('fixture_error' in r for r in rows)
    print(json.dumps({'mode':MODE,'cases':len(rows),'checks':count,'PASS':count-red,'RED':red,'fixture_errors':errors,'real_network_attempts':len(DENIED)}))
    if red or errors:
        raise SystemExit(1)


asyncio.run(main())
