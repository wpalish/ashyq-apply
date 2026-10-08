"""Finite OFF proof; native retrieval/Fetcher methods, no source replacements."""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import socket
import sys
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
DENIED: list[dict] = []
DNS: list[dict] = []


def deny(kind: str):
    def rejected(*args, **kwargs):
        DENIED.append({'kind': kind})
        raise AssertionError('DENIED_REAL_NETWORK_' + kind)
    return rejected


def synthetic_dns(host, port, *args, **kwargs):
    if host != 'example.edu':
        DENIED.append({'kind': 'unapproved DNS host', 'host': str(host)})
        raise AssertionError('DENIED_REAL_DNS')
    DNS.append({'host': host, 'port': port})
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('93.184.216.34', port))]


socket.socket.connect = deny('socket.connect')
socket.socket.connect_ex = deny('socket.connect_ex')
socket.create_connection = deny('socket.create_connection')
socket.getaddrinfo = synthetic_dns
sys.path.insert(0, str(REPO / 'backend'))
import httpx

httpx.HTTPTransport.handle_request = deny('default sync HTTP transport')


async def deny_async_http(*args, **kwargs):
    DENIED.append({'kind': 'default async HTTP transport'})
    raise AssertionError('DENIED_REAL_HTTP')


httpx.AsyncHTTPTransport.handle_async_request = deny_async_http
from app.adapters.fetching import Fetcher, same_source_site
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.read_budget import BudgetedFetcher

IMPORTED = {
    item.__qualname__: {'module': item.__module__, 'file': inspect.getfile(item)}
    for item in (Fetcher, BudgetedFetcher, FakeSearchProvider, DiscoveryIntent,
                 discover_candidates, UniversityReadStopped, RunCancelled, LeaseLost)
}
METHODS = {label: value for label, value in {
    'BudgetedFetcher.get': BudgetedFetcher.get, 'Fetcher.get': Fetcher.get,
    'Fetcher._get': Fetcher._get, 'Fetcher._request_with_redirects': Fetcher._request_with_redirects,
    'FakeSearchProvider.search': FakeSearchProvider.search,
    'discover_candidates': discover_candidates,
}.items()}
NOW = datetime(2026, 10, 8, 4, 0, tzinfo=UTC)


def exception_record(exc: BaseException | None) -> dict | None:
    if exc is None:
        return None
    return {'class': type(exc).__name__, 'module': type(exc).__module__,
            'reason': getattr(exc, 'reason', None), 'message': str(exc)}


async def control_case(name: str) -> dict:
    # A callback is the native durable-reservation seam. Its decision below is
    # synthetic, not SQL lease/counter proof. No get/fetch/provider method is patched.
    original = {
        'read_cap': lambda: UniversityReadStopped('read_cap'),
        'checkpoint_busy': lambda: UniversityReadStopped('checkpoint_busy'),
        'run_cancelled': lambda: RunCancelled('synthetic cancellation'),
        'lease_lost': lambda: LeaseLost('synthetic stale ownership'),
        'async_cancelled': lambda: asyncio.CancelledError('synthetic task cancellation'),
        'ordinary_runtime_control_text': lambda: RuntimeError('University read allowance refused: read_cap'),
    }.get(name, lambda: None)()
    initial_count = 60 if name == 'read_cap' else (17 if original is not None else 0)
    read_count = initial_count
    guard_events: list[dict] = []
    http_events: list[dict] = []
    fetch_events: list[dict] = []
    query_attempts: list[int] = []
    requested_urls: list[str] = []
    before_dns, before_denied = len(DNS), len(DENIED)

    def before_get():
        nonlocal read_count
        event = {'attempt': len(guard_events) + 1, 'read_count_before': read_count,
                 'reserved': False, 'raised_original_object': original is not None,
                 'raised': exception_record(original)}
        guard_events.append(event)
        if original is not None:
            raise original
        read_count += 1
        event.update({'reserved': True, 'read_count_after': read_count})

    def exchange(request: httpx.Request) -> httpx.Response:
        host = request.headers.get('host', '')
        http_events.append({'method': request.method, 'host_header': host,
                            'pinned_host': request.url.host, 'path': request.url.path})
        if host != 'example.edu' or request.url.host != '93.184.216.34':
            raise AssertionError('UNEXPECTED_MOCK_HTTP_TARGET')
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /\n',
                                  headers={'content-type': 'text/plain'})
        if request.url.path != '/':
            raise AssertionError('UNEXPECTED_MOCK_HTTP_PATH')
        if name == 'transport':
            raise httpx.ConnectError('synthetic transport unavailable', request=request)
        if name == 'timeout':
            raise httpx.ReadTimeout('synthetic read timeout', request=request)
        if name == 'access_403':
            return httpx.Response(403, text='Forbidden', headers={'content-type': 'text/html'})
        body = '' if name == 'empty_html' else (
            '<html><body><a href="/programmes/bsc-computer-science">'
            'Bachelor Computer Science</a></body></html>')
        return httpx.Response(200, text=body, headers={'content-type': 'text/html'})

    intent = DiscoveryIntent('Example University', 'example.edu', DegreeLevel.BACHELOR,
                             'Computer Science')
    corpus = {q.text: [('https://example.edu/programmes/computer-science',
                       'Bachelor Computer Science', '')]
              for q in queries_for(intent, budget=1)}
    provider = FakeSearchProvider(corpus, now=NOW)
    fetcher = BudgetedFetcher(HERE / 'runtime' / name, before_get=before_get,
                              delay_seconds=0, respect_robots=True, offline=False)
    report = None
    escaped = None
    # Installing a MockTransport at the client ownership seam leaves the
    # BudgetedFetcher/Fetcher methods and HTTP/robots/retry flow native.
    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange), follow_redirects=False,
                                 timeout=fetcher.timeout) as client:
        fetcher._client = client

        async def read(url: str) -> str:
            requested_urls.append(url)
            result = await fetcher.get(url)
            fetch_events.append({'url': result.url, 'outcome': result.outcome.value,
                                 'status_code': result.status_code, 'error': result.error,
                                 'text_length': len(result.text), 'final_url': result.final_url})
            # The unchanged production caller closure semantics.
            return result.text if result.ok and same_source_site(url, result.final_url or url) else ''

        try:
            report = await discover_candidates(provider, intent, query_budget=1, top_k=10,
                                               hop_entry_points=1, fetch=read,
                                               on_query_attempt=lambda: query_attempts.append(1))
        except BaseException as exc:
            escaped = exc
        finally:
            fetcher._client = None

    must_propagate = name in {'read_cap', 'checkpoint_busy', 'run_cancelled',
                             'lease_lost', 'async_cancelled'}
    propagation = escaped is original and report is None if must_propagate else escaped is None
    row = {
        'case': name, 'status': 'PASS' if propagation else 'RED',
        'contract': 'propagate original typed signal' if must_propagate else 'contain ordinary unavailability / retain normal navigation',
        'original_exception': exception_record(original), 'escaped_exception': exception_record(escaped),
        'escaped_same_original_object': escaped is original if original is not None else None,
        'report_returned': report is not None, 'report': asdict(report) if report else None,
        'query_seam_attempts': len(query_attempts), 'synthetic_provider_calls': provider.calls,
        'get_requests': requested_urls, 'before_get_events': guard_events,
        'synthetic_read_count_before': initial_count, 'synthetic_read_count_after': read_count,
        'synthetic_read_admissions': read_count-initial_count, 'native_fetch_results': fetch_events,
        'native_fetcher_stats': fetcher.stats, 'mock_http_exchanges': http_events,
        'synthetic_dns_resolutions': DNS[before_dns:], 'denied_real_network_attempts': DENIED[before_denied:],
    }
    checks = {
        'one_query_attempt': len(query_attempts) == 1,
        'one_provider_call': len(provider.calls) == 1,
        'one_native_get_entry': requested_urls == ['https://example.edu/'] and len(guard_events) == 1,
        'no_real_network_attempt': len(DENIED) == before_denied,
        'methods_unmodified': all(value is METHODS[label] for label, value in {
            'BudgetedFetcher.get': BudgetedFetcher.get, 'Fetcher.get': Fetcher.get,
            'Fetcher._get': Fetcher._get, 'Fetcher._request_with_redirects': Fetcher._request_with_redirects,
            'FakeSearchProvider.search': FakeSearchProvider.search,
            'discover_candidates': discover_candidates,
        }.items()),
        'guard_refusal_zero_io' if original else 'one_native_read_admitted':
            (not http_events and not DNS[before_dns:] and read_count == initial_count)
            if original else read_count == initial_count+1,
    }
    if report is not None:
        checks['query_report_kept_attempt'] = len(report.queries_run) == 1
        checks['search_hint_not_erased'] = bool(report.candidates)
        if name == 'normal_html':
            checks['normal_hop_opened'] = report.hop_entry_points == ('https://example.edu/',)
            checks['navigation_added'] = report.hop_candidates >= 1
        else:
            checks['unavailable_hop_recorded'] = (report.hop_entry_points == () and
                                                 report.hop_entry_points_unreachable == 1 and
                                                 report.hop_candidates == 0)
    row['accounting_checks'] = checks
    if not all(checks.values()):
        row['fixture_or_accounting_failure'] = True
        row['status'] = 'RED'
    return row


async def main():
    names = ['read_cap', 'checkpoint_busy', 'run_cancelled', 'lease_lost', 'async_cancelled',
             'ordinary_runtime_control_text', 'empty_html', 'transport', 'access_403',
             'timeout', 'normal_html']
    rows = []
    for name in names:
        try:
            row = await control_case(name)
        except BaseException as exc:
            row = {'case': name, 'status': 'RED', 'fixture_error': exception_record(exc),
                   'traceback': traceback.format_exc()}
        rows.append(row)
        print(json.dumps({'case': name, 'status': row['status'],
                          'same_original': row.get('escaped_same_original_object'),
                          'report_returned': row.get('report_returned'),
                          'fixture_error': row.get('fixture_error'),
                          'query_attempts': row.get('query_seam_attempts'),
                          'native_get_entries': len(row.get('before_get_events', [])),
                          'mock_http_exchanges': len(row.get('mock_http_exchanges', []))}), flush=True)
    result = {'imports': IMPORTED, 'cases': rows, 'summary': {
        'case_count': len(rows), 'PASS': sum(r['status'] == 'PASS' for r in rows),
        'RED': sum(r['status'] == 'RED' for r in rows),
        'fixture_failures': sum(bool(r.get('fixture_error') or r.get('fixture_or_accounting_failure')) for r in rows),
        'real_network_attempts': len(DENIED),
        'qualification': 'OFF defect proof only; actual native get fence with synthetic callback; no SQL/Worker/crash durability or launch-quality claim.'}}
    (HERE / 'outcomes.attempt1.original.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(result['summary']), flush=True)
    return 1 if result['summary']['RED'] else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
