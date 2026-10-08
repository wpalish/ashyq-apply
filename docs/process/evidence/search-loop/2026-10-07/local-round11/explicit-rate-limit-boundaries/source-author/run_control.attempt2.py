"""Fresh child, real native Exa methods, denied sockets, external target modules only."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import json
import socket
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

B = Path(__file__).resolve().parent
REPO = B.parents[1] / 'ashyq-apply/backend'
PLAN = json.loads((B / 'PLAN.json').read_text())
sys.path.insert(0, str(REPO))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_pins():
    return {rel: digest(REPO / rel) for rel in PLAN['source_sha256']}

def proposal_pins():
    return {rel: digest(B / 'proposed' / rel) for rel in PLAN['source_files']}

def deny(*args, **kwargs):
    raise AssertionError('Real network/DNS/socket forbidden')

resolutions = []
def synthetic_resolver(host, port, *args, **kwargs):
    assert host == 'mcp.exa.ai', host
    resolutions.append({'host': host, 'port': port, 'kind': 'synthetic resolver, no DNS'})
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))]

socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
socket.getaddrinfo = synthetic_resolver

import httpx
from app import config
from app.adapters import search as original_search
from app.adapters.discovery import live_discovery as original_live
from app.adapters.search import exa_mcp as mcp
from app.adapters.search import retrieval as original_retrieval
from app.adapters.search.base import SearchFailureReason, SearchResponse, SearchUnavailable
from app.adapters.search.intent import DiscoveryIntent

assert source_pins() == PLAN['source_sha256']
assert original_search._THROTTLED_UNTIL == {}
assert mcp._last_query_at is None
METHODS = {key: getattr(mcp.ExaMcpSearchProvider, key) for key in ['search', '_search_once', '_post', '_initialize']}
SOURCE_BEFORE = source_pins()
PROPOSAL_BEFORE = proposal_pins()
FIXED_NOW = datetime(2026, 10, 8, 3, 0, 0, tzinfo=UTC)


def load(rel, name, package=False):
    opts = {'submodule_search_locations': [str(REPO / 'app/adapters/search')]} if package else {}
    spec = importlib.util.spec_from_file_location(name, B / 'proposed' / rel, **opts)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def targets(mode):
    if mode == 'off':
        return original_search, original_retrieval, original_live
    import app.adapters
    search = load('app/adapters/search/__init__.py', '_a_proposed_search', True)
    sys.modules['app.adapters.search'] = search
    app.adapters.search = search
    retrieval = load('app/adapters/search/retrieval.py', '_a_proposed_retrieval')
    sys.modules['app.adapters.search.retrieval'] = retrieval
    search.retrieval = retrieval
    live = load('app/adapters/discovery/live_discovery.py', '_a_proposed_live')
    return search, retrieval, live


class Clock:
    def __init__(self, step=0.0):
        self.value = 100.0
        self.step = step
        self.sleeps = []
    def monotonic(self):
        value = self.value
        self.value += self.step
        return value
    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


class Server:
    def __init__(self, mode):
        self.mode = mode
        self.events = []
    async def handle(self, request):
        payload = json.loads(request.content)
        row = {'method': payload['method'], 'payload': payload, 'url': str(request.url),
               'session_header': request.headers.get('mcp-session-id')}
        self.events.append(row)
        method = payload['method']
        if method == 'initialize':
            body = {'jsonrpc': '2.0', 'id': payload['id'], 'result': {'protocolVersion': mcp.PROTOCOL_VERSION, 'capabilities': {}, 'serverInfo': {'name': 'offline-synthetic-mcp', 'version': '1'}}}
            row.update(status=200, response=body)
            return httpx.Response(200, json=body, headers={'mcp-session-id': 'synthetic-session'})
        if method == 'notifications/initialized':
            row.update(status=202, response=None)
            return httpx.Response(202)
        assert method == 'tools/call'
        assert payload['params']['name'] == 'web_search_advanced_exa'
        if self.mode == 'http429':
            row.update(status=429)
            return httpx.Response(429, json={'error': 'synthetic refusal'})
        if self.mode == 'transport':
            row.update(status=None, raised='httpx.ConnectError')
            raise httpx.ConnectError('Synthetic transport only', request=request)
        if self.mode == 'timeout':
            row.update(status=None, raised='httpx.ReadTimeout')
            raise httpx.ReadTimeout('Synthetic timeout only', request=request)
        result = {'structuredContent': {'results': [{'url': 'https://example.edu/bachelors/computer-science', 'title': 'BSc Computer Science', 'highlights': ['Public discovery hint only']}]}}
        metadata = {'meta': True, 'meta-false': False, 'meta-one': 1, 'meta-string': 'true'}
        if self.mode in metadata:
            result['_meta'] = {'ai.exa/rateLimited': metadata[self.mode]}
        if self.mode in {'vendor-text', 'vendor-error'}:
            result['content'] = [{'type': 'text', 'text': 'rate limited: vendor-only arbitrary text'}]
            if self.mode == 'vendor-error':
                result['isError'] = True
        body = {'jsonrpc': '2.0', 'id': payload['id'], 'result': result}
        row.update(status=200, response=body)
        return httpx.Response(200, json=body)


class EmptyFetcher:
    refused_hosts = {}
    def __init__(self):
        self.calls = []
    async def get(self, url):
        self.calls.append(url)
        return SimpleNamespace(ok=False, text='', final_url=url, outcome=SimpleNamespace(value='offline_mock_unavailable'))


def error(exc):
    return {'type': type(exc).__name__, 'reason': exc.reason.value if isinstance(exc.reason, SearchFailureReason) else exc.reason,
            'http_status': exc.http_status, 'message': str(exc)}


async def main(mode, scenario):
    search, retrieval, live = targets(mode)
    checks = []
    def check(key, expected, okay):
        checks.append({'case': key, 'expected': expected, 'status': 'PASS' if okay else 'RED'})
    server_mode = scenario.split(':')[1] if ':' in scenario else 'meta'
    clock = Clock(1.0 if scenario == 'state:stamp' else 0.0)
    server = Server(server_mode)
    clients = []
    original_client = httpx.AsyncClient
    def client_factory(*args, **kwargs):
        assert 'transport' not in kwargs
        kwargs['transport'] = httpx.MockTransport(server.handle)
        client = original_client(*args, **kwargs)
        clients.append(client)
        return client
    retry = False if scenario.endswith(':no-retry') else mcp.RATE_LIMIT_RETRY
    if scenario.endswith(':no-retry'):
        server.mode = 'meta'
    seam = []
    outputs = []
    counts = []
    fetcher = EmptyFetcher()
    def http_counts():
        return {key: sum(row['method'] == key for row in server.events) for key in ['initialize', 'notifications/initialized', 'tools/call']}
    async def ask(provider, query):
        seam.append({'query': query, 'provider_object': len(seam), 'HTTP_before': len(server.events)})
        try:
            response = await provider.search(query=query, domains=['example.edu'], max_results=10)
            outputs.append({'error': None, 'response': asdict(response)})
        except SearchUnavailable as exc:
            outputs.append({'error': error(exc), 'response': None})
        counts.append(http_counts())
    native_flags = {'RATE_LIMIT_RETRY': mcp.RATE_LIMIT_RETRY, 'RETRY_429_ONCE': mcp.RETRY_429_ONCE, 'MIN_QUERY_INTERVAL_SECONDS': mcp.MIN_QUERY_INTERVAL_SECONDS}
    with patch.object(config, 'get_settings', lambda: SimpleNamespace(search_provider='exa_mcp')), patch.object(httpx, 'AsyncClient', client_factory), patch.object(search, 'time', SimpleNamespace(monotonic=clock.monotonic)), patch.object(mcp, 'time', SimpleNamespace(monotonic=clock.monotonic)), patch.object(mcp, 'datetime', SimpleNamespace(now=lambda zone: FIXED_NOW)), patch.object(mcp, 'asyncio', SimpleNamespace(sleep=clock.sleep, Lock=asyncio.Lock, timeout=asyncio.timeout)), patch.object(mcp, 'RATE_LIMIT_RETRY', retry):
        if scenario.startswith('factory:'):
            first = search.get_search_provider()
            assert type(first.inner) is mcp.ExaMcpSearchProvider
            await ask(first, 'public first')
            await ask(first, 'public repeat')
            # Created AFTER the first native refusal, unlike the earlier selector control.
            second = search.get_search_provider()
            await ask(second, 'public other adapter')
            explicit = server.mode in {'meta', 'http429'}
            if explicit:
                first_tools = 2 if server.mode == 'meta' and retry else 1
                check('first_native_refusal_status_reason', 'metadata None/RATE_LIMITED or originalHTTP429/None', outputs[0]['error']['http_status'] == (None if server.mode == 'meta' else 429) and outputs[0]['error']['reason'] == ('rate limited' if server.mode == 'meta' else None))
                check('later_errors_preserve_status_reason', 'local refusal retains original fixed enum and exact status', all(item['error'] and (item['error']['reason'], item['error']['http_status']) == (outputs[0]['error']['reason'], outputs[0]['error']['http_status']) for item in outputs))
                check('shared_local_repeat', 'later same/new adapter sends no protocol or tool request', counts[0] == counts[1] == counts[2] and counts[0]['tools/call'] == first_tools)
                check('latch_explicit_refusal', 'process latch exists after first native failure escapes', bool(search._THROTTLED_UNTIL.get('exa_mcp')))
                check('no_text_invented_quota_or_429', 'meta local errors use generic rate wording, no429/quota conversion', server.mode != 'meta' or all('429' not in item['error']['message'] and 'quota' not in item['error']['message'] for item in outputs[1:]))
            else:
                check('non_rate_failures_no_latch', 'nonexplicit modes stay unlatchable', search._THROTTLED_UNTIL == {})
                check('non_rate_three_tools', 'three seams dispatch3tools/2handshakes without newretry', http_counts() == {'initialize': 2, 'notifications/initialized': 2, 'tools/call': 3} and clock.sleeps == [])
                if server.mode in {'transport', 'timeout', 'vendor-error'}:
                    expected = {'transport': 'transport error', 'timeout': 'timeout', 'vendor-error': 'MCP tool error'}[server.mode]
                    check('non_rate_error_provenance', 'original typed nonquota failure/status retained', all(item['error'] and item['error']['http_status'] is None and item['error']['reason'] == expected for item in outputs))
                else:
                    check('success_rows_preserved', 'normal actualSearchResponse has one original result', all(item['error'] is None and len(item['response']['results']) == 1 for item in outputs))
        elif scenario.startswith('retrieval:'):
            provider = search.get_search_provider()
            def charge():
                seam.append({'family_attempt': len(seam) + 1, 'HTTP_before': len(server.events)})
            report = await retrieval.discover_candidates(provider, DiscoveryIntent(institution='Synthetic University', domain='example.edu', degree='bachelor', field='computer science'), query_budget=6, fetch=None, on_query_attempt=charge)
            outputs = {'retrieval': asdict(report)}
            explicit = server.mode in {'meta', 'http429'}
            tools = 2 if server.mode == 'meta' and retry else 1
            if explicit:
                check('stop_unattempted_families', 'onecharged attemptedfamily, no laterfamily or tool dispatch', len(seam) == len(report.queries_run) == 1 and http_counts()['tools/call'] == tools)
                check('explicit_throttled', 'report marks typed explicit rate limit', report.throttled is True)
                check('safe_exact_diagnostic', 'metadataNone stayswithoutHTTP429 and retainsenum', len(report.failure_diagnostics) == 1 and (('rate limited' in report.failure_diagnostics[0] and 'HTTP 429' not in report.failure_diagnostics[0]) if server.mode == 'meta' else 'HTTP 429' in report.failure_diagnostics[0]))
            else:
                check('all_non_rate_families_attempted', 'ordinary failures/success dispatch and charge6families', len(seam) == len(report.queries_run) == http_counts()['tools/call'] == 6)
                check('non_rate_not_throttled', 'no rate-limit stop for arbitraryvendor/transient', not report.throttled and search._THROTTLED_UNTIL == {})
        elif scenario.startswith('caller:'):
            # Actual native caller -> normal import retrieval -> real factory/client.
            server.mode = 'http429' if scenario.endswith('429') else 'success' if scenario.endswith('success') else 'meta'
            adapter = live.LiveDiscoveryAdapter(fetcher, registry_path=original_live.REGISTRY_PATH)
            fields = ['computer science', 'mathematics'] if ':multi-' in scenario else ['computer science']
            profile = SimpleNamespace(context=SimpleNamespace(level='bachelor', intended_fields=fields))
            trace = live.DiscoveryTrace('Synthetic University', 'example.edu')
            selected = {category: [] for category in live.PageCategory.ALL}
            await adapter._add_search_results({'name': 'Synthetic University'}, 'example.edu', selected, trace, profile)
            outputs = {'trace': trace.as_dict(), 'selected': selected, 'fetches': fetcher.calls}
            if server.mode in {'meta', 'http429'}:
                expected_tools = 2 if server.mode == 'meta' else 1
                check('native_caller_onecharge', 'single/multi caller chargesonlyfirstfamily and no later subject', trace.search_queries_sent == 1 and http_counts()['tools/call'] == expected_tools)
                check('native_caller_safe_limit_text', 'rate-limit/incomplete wording withoutquota orHTTP429status fabrication', any('rate-limit stop' in text and 'incomplete' in text and 'quota' not in text and 'HTTP 429' not in text for text in trace.search_limitations))
                check('native_caller_failure_diagnostic', 'safe native failure retains enum/status', len(trace.search_failures) == 1 and (('rate limited' in trace.search_failures[0] and 'HTTP 429' not in trace.search_failures[0]) if server.mode == 'meta' else 'HTTP 429' in trace.search_failures[0]))
                check('no_official_get_after_empty_refusal', 'no search result/claim/page get fabricated', fetcher.calls == [] and selected[live.PageCategory.PROGRAM_PAGE] == [])
            else:
                check('native_caller_normal_charge', 'successful native caller retains6search-seam attempts', trace.search_queries_sent == 6 and http_counts()['tools/call'] == 6)
        else:
            # Independent low-level state/type controls, not claimed as Exa integration.
            class Controlled:
                name = 'exa_mcp'
                calls = 0
                reason = None
                status = None
                message = 'rate limited vendor text only'
                async def search(self, *, query, domains=(), max_results=10):
                    self.calls += 1
                    raise SearchUnavailable(self.message, reason=self.reason, http_status=self.status)
            inner = Controlled()
            if scenario in {'state:stamp', 'state:expiry', 'state:isolation', 'state:stale', 'state:reset'}:
                inner.reason = SearchFailureReason.RATE_LIMITED
            elif scenario == 'state:string-reason':
                inner.reason = 'rate limited'
            elif scenario == 'state:429-untyped':
                inner.status = 429
                inner.reason = 'arbitrary vendor text'
            elif scenario == 'state:500-typed':
                inner.status = 500
                inner.reason = SearchFailureReason.RATE_LIMITED
            elif scenario == 'state:legacy-float':
                search._THROTTLED_UNTIL['exa_mcp'] = 400.0
            provider = search._ThrottleLatch(inner)
            await ask(provider, 'q1')
            if scenario == 'state:expiry':
                clock.value = search._THROTTLED_UNTIL.get('exa_mcp', 400.0)
            if scenario == 'state:stale':
                search._THROTTLED_UNTIL['exa_mcp'] = 900.0
            if scenario == 'state:reset':
                search.reset_search_throttle()  # only the fresh child-owned module
                check('reset_clears_both_before_io', 'fresh child reset clears both maps before next innercall', search._THROTTLED_UNTIL == {} and getattr(search, '_THROTTLED_ORIGIN', {}) == {})
            if scenario == 'state:isolation':
                other = Controlled()
                other.name = 'tavily'
                await ask(search._ThrottleLatch(other), 'other provider')
                check('provider_isolation', 'anotherprovider is not suppressed', other.calls == 1)
            else:
                await ask(provider, 'q2')
            if scenario in {'state:string-reason', 'state:vendor-text'}:
                check('untyped_text_no_latch', 'enum identity required; arbitrarystrings donot stop', inner.calls == 2 and search._THROTTLED_UNTIL == {})
                charged = []
                report = await retrieval.discover_candidates(provider, DiscoveryIntent(institution='Synthetic University', domain='example.edu', degree='bachelor', field='computer science'), query_budget=6, on_query_attempt=lambda: charged.append(1))
                outputs.append({'retrieval': asdict(report)})
                check('untyped_text_no_loopstop', 'all6ordinary failurefamilies attempted, no throttledreport', len(charged) == 6 and len(report.queries_run) == 6 and report.throttled is False)
            elif scenario in {'state:expiry', 'state:reset'}:
                check('expiry_or_reset_allows_inner_again', 'exactdeadline expired or bothchildmaps reset before secondnativecall', inner.calls == 2)
                if scenario == 'state:reset':
                    check('reset_both_owned_maps', 'reset does not leave a stale typedorigin', bool(getattr(search, '_THROTTLED_ORIGIN', {})) and getattr(search, '_THROTTLED_ORIGIN', {}).get('exa_mcp', (None,))[0] == search._THROTTLED_UNTIL.get('exa_mcp'))
            elif scenario == 'state:legacy-float':
                check('legacy_float_429_only', 'knownoldfloat-only state keepsHTTP429/None without innercall', inner.calls == 0 and all(item['error']['http_status'] == 429 and item['error']['reason'] is None for item in outputs))
            elif scenario == 'state:stale':
                check('stale_stamp_legacy_fallback', 'deliberatelychangedoldfloat deadline cannotborrowtypedNoneorigin', inner.calls == 1 and outputs[1]['error']['http_status'] == 429 and outputs[1]['error']['reason'] is None)
            elif scenario == 'state:stamp':
                origin = getattr(search, '_THROTTLED_ORIGIN', {}).get('exa_mcp')
                check('one_computed_deadline_stamp', 'exactuntil reused once, tickclock doesnot eraseNone provenance', origin is not None and origin[0] == search._THROTTLED_UNTIL['exa_mcp'] and inner.calls == 1 and outputs[1]['error']['http_status'] is None and outputs[1]['error']['reason'] == 'rate limited')
            elif scenario == 'state:500-typed':
                check('typed_non429_exactstatus', 'typedrate stop preservesstatus500 (notcoerce429)', inner.calls == 1 and outputs[1]['error']['http_status'] == 500 and outputs[1]['error']['reason'] == 'rate limited')
            elif scenario == 'state:429-untyped':
                check('429_no_arbitrary_reason_copy', 'actual429 triggers but arbitraryvendorstringnotstoredinlocalerror', inner.calls == 1 and outputs[1]['error']['http_status'] == 429 and outputs[1]['error']['reason'] is None and 'arbitrary' not in outputs[1]['error']['message'])
        check('native_methods_never_substituted', 'actualExa search/search_once/post/initialize function identity unchanged', all(getattr(mcp.ExaMcpSearchProvider, key) is method for key, method in METHODS.items()))
        check('transport_denied_closed', 'allHTTP MockTransport, closedownedclients, real sockets denied', all(isinstance(client._transport, httpx.MockTransport) and client.is_closed for client in clients))
        state = {'until': dict(search._THROTTLED_UNTIL), 'origin': getattr(search, '_THROTTLED_ORIGIN', None)}
    after = source_pins()
    prop_after = proposal_pins()
    assert after == SOURCE_BEFORE == PLAN['source_sha256']
    assert prop_after == PROPOSAL_BEFORE
    result = {'mode': mode, 'scenario': scenario, 'counts': {'PASS': sum(row['status'] == 'PASS' for row in checks), 'RED': sum(row['status'] == 'RED' for row in checks), 'total': len(checks)},
              'checks': checks, 'outputs': outputs, 'query_seam_attempts': seam, 'mock_HTTP_counts': http_counts(), 'mock_HTTP_events': server.events,
              'owned_child_latch': state, 'fake_clock_sleeps': clock.sleeps, 'synthetic_resolutions': resolutions,
              'native_source_before': SOURCE_BEFORE, 'native_source_after': after, 'proposal_source_before': PROPOSAL_BEFORE, 'proposal_source_after': prop_after,
              'native_flags': native_flags, 'effective_child_retry': retry, 'native_methods': {key: {'name': method.__qualname__, 'file': inspect.getsourcefile(method)} for key, method in METHODS.items()},
              'target_files': {'search': search.__file__, 'retrieval': retrieval.__file__, 'live': live.__file__}, 'real_network_provider_model_Git_app_STOP_changes': 0,
              'qualification': 'Mock HTTP protocol/tool dispatch is independent of query seam charges. Defaultnative metadata retryTrue2tools stays intact. State controls use an explicitlysyntheticprovider; actualintegration cases never replace nativeExa methods. Childreset occurs only in statedfreshownedstatecontrol; primary state untouched.'}
    out = B / sys.argv[3] / (scenario.replace(':', '-') + '.' + mode + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    assert not out.exists()
    out.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({'mode': mode, 'scenario': scenario, **result['counts']}))
    return 1 if result['counts']['RED'] else 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main(sys.argv[1], sys.argv[2])))
