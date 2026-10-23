"""Finite OFF native boundaries. No SQL-fence or production network proof."""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(os.environ['CONTROL_OUTPUT_DIR'])
REPO = Path(os.environ['SOURCE_ROOT'])
STOP = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/local-round7/provider-STOP.json')
PLAN = json.loads((ROOT / 'PLAN.json').read_text())
DENIED = []


def deny(*args, **kwargs):
    DENIED.append('transport_or_DNS')
    raise AssertionError('Offline boundary control attempted network')


socket.getaddrinfo = deny
socket.socket.connect = deny
socket.socket.connect_ex = deny

from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, PageCategory
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.search.base import SearchResponse, SearchResult
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel, FetchOutcome
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.read_budget import BudgetedFetcher
from app.schemas.profile import ApplicantProfileIn

import app.adapters.discovery.live_discovery as live_module
import app.adapters.search.retrieval as retrieval_module
import app.pipeline.control as control_module
import app.pipeline.read_budget as budget_module
import httpx

NAME = 'Test University'
DOMAIN = 'example.edu'
NOW = datetime(2026, 10, 8, tzinfo=UTC)
URL = 'https://example.edu/bachelors/computer-science'
HTML = '<h1>BSc Computer Science</h1><nav><a href="/bachelors/mathematics">BSc Mathematics</a></nav>'


class Provider:
    name = 'fake'

    def __init__(self):
        self.calls = []

    async def search(self, *, query, domains=(), max_results=10):
        self.calls.append(query)
        return SearchResponse(query, self.name, NOW, (
            SearchResult(URL, 'BSc Computer Science', self.name, 1, NOW),
        ))


def profile(multi=False):
    return ApplicantProfileIn.model_validate({'context': {
        'level': 'bachelor',
        'intended_fields': ['Computer Science', 'Mathematics', 'Physics'] if multi else ['Computer Science'],
        'intake_year': 2027, 'citizenship': 'KZ', 'country_of_residence': 'KZ',
        'education_country': 'KZ', 'education_system': 'KZ',
    }})


def source_check():
    bad = []
    for rel, entry in PLAN['sources'].items():
        if hashlib.sha256((REPO / rel).read_bytes()).hexdigest() != entry['sha256']:
            bad.append(rel)
    if hashlib.sha256(STOP.read_bytes()).hexdigest() != PLAN['stop']['sha256']:
        bad.append('STOP')
    if bad:
        raise AssertionError(f'Source drift: {bad}')


async def typed_case(lane, kind):
    signal = {
        'read_cap': lambda: UniversityReadStopped('read_cap'),
        'checkpoint_busy': lambda: UniversityReadStopped('checkpoint_busy'),
        'run_cancelled': lambda: RunCancelled('controlled cancellation'),
        'lease_lost': lambda: LeaseLost('controlled lost attempt'),
        'async_cancelled': lambda: asyncio.CancelledError('controlled async cancellation'),
    }[kind]()
    before, underlying, charges = [], [], []

    def reserve():
        before.append('before_get')
        raise signal

    async def base_get(self, url, **kwargs):
        underlying.append(url)
        raise AssertionError('A refused BudgetedFetcher.get reached base Fetcher.get')

    fetcher = BudgetedFetcher(ROOT / 'temporary-cache' / lane / kind, before_get=reserve)
    provider = Provider()
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN, search_queries_sent=1)
    selected = {category: [] for category in PageCategory.ALL}
    observed = None
    returned = None
    with patch.object(Fetcher, 'get', base_get):
        try:
            if lane == 'retrieval':
                async def read(url):
                    return (await fetcher.get(url)).text
                returned = await discover_candidates(provider, DiscoveryIntent(
                    institution=NAME, domain=DOMAIN, degree=DegreeLevel.BACHELOR,
                    field='Computer Science'), query_budget=2, fetch=read,
                    on_query_attempt=lambda: charges.append(1))
            else:
                adapter = LiveDiscoveryAdapter(fetcher, registry_path=ROOT / 'no-registry.json')
                adapter._search_provider = provider
                adapter._search_provider_resolved = True
                returned = await adapter._add_search_results(
                    {'name': NAME}, DOMAIN, selected, trace, profile(lane == 'multi'))
        except BaseException as error:
            observed = error
    expected_queries = 2 if lane in {'retrieval', 'multi'} else 5
    native_reason = getattr(observed, 'reason', None)
    checks = {
        'same_exception_object': observed is signal,
        'reason_unchanged': native_reason == getattr(signal, 'reason', None),
        'no_second_read_attempt': len(before) == 1,
        'base_get_never_reached': underlying == [],
        'no_unattempted_subject_queries': len(provider.calls) == expected_queries,
        'prior_identity_charge_preserved': lane == 'retrieval' or trace.search_queries_sent == 1 + expected_queries,
        'no_selected_page_mutation': all(not value for value in selected.values()),
    }
    return {'lane': lane, 'kind': kind, 'status': 'PASS' if all(checks.values()) else 'RED',
            'checks': checks, 'observed_exception': type(observed).__name__ if observed else None,
            'reason': native_reason, 'query_calls': len(provider.calls), 'read_attempts': len(before),
            'base_get_calls': len(underlying), 'trace_queries': trace.search_queries_sent,
            'returned_report': dataclasses.asdict(returned) if dataclasses.is_dataclass(returned) else returned,
            'trace_search_failures': trace.search_failures,
            'qualification': 'Controlled native before_get boundary; no real SQL fence invocation.'}


async def ordinary_case(kind):
    before, underlying, charges = [], [], []

    def reserve():
        before.append('before_get')
        if kind == 'site_runtime':
            raise RuntimeError('the site refused')
        if kind == 'site_timeout':
            raise TimeoutError('the site timed out')

    async def base_get(self, url, **kwargs):
        underlying.append(url)
        outcome = {'http_error': FetchOutcome.HTTP_ERROR, 'robots': FetchOutcome.ROBOTS_DISALLOWED}.get(kind, FetchOutcome.OK)
        return FetchResult(url=url, outcome=outcome, final_url=url,
                           text=HTML if kind == 'navigation' else '', fetched_at=NOW)

    provider = Provider()
    fetcher = BudgetedFetcher(ROOT / 'temporary-cache' / 'ordinary' / kind, before_get=reserve)
    async def read(url):
        result = await fetcher.get(url)
        return result.text if result.ok else ''
    with patch.object(Fetcher, 'get', base_get):
        report = await discover_candidates(provider, DiscoveryIntent(
            institution=NAME, domain=DOMAIN, degree=DegreeLevel.BACHELOR,
            field='Computer Science'), query_budget=2, fetch=read,
            on_query_attempt=lambda: charges.append(1))
    checks = {
        'queries_and_charge_two': len(provider.calls) == len(charges) == len(report.queries_run) == 2,
        'one_entry_root_attempt': len(before) == 1,
        'search_candidate_retained': any(item.url == URL for item in report.candidates),
        'no_false_provider_failure': not report.failed_queries and not report.failure_diagnostics and not report.throttled,
        'empty_or_unavailable_is_unreachable': report.hop_entry_points_unreachable == (0 if kind == 'navigation' else 1),
        'entry_opened_only_with_html': len(report.hop_entry_points) == (1 if kind == 'navigation' else 0),
    }
    return {'kind': kind, 'status': 'PASS' if all(checks.values()) else 'RED', 'checks': checks,
            'report': dataclasses.asdict(report), 'query_calls': len(provider.calls),
            'read_attempts': len(before), 'base_get_calls': len(underlying)}


async def main():
    source_check()
    modules = []
    for module in (retrieval_module, live_module, control_module, budget_module):
        path = Path(module.__file__).resolve()
        expected = REPO / 'backend' / Path(*module.__name__.split('.')).with_suffix('.py')
        assert path == expected
        modules.append({'name': module.__name__, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    rows = []
    with patch.object(httpx.AsyncClient, 'send', deny), patch.object(httpx.Client, 'send', deny):
        for lane in ('retrieval', 'single', 'multi'):
            for kind in ('read_cap', 'checkpoint_busy', 'run_cancelled', 'lease_lost', 'async_cancelled'):
                rows.append(await typed_case(lane, kind))
        for kind in ('site_runtime', 'site_timeout', 'http_error', 'robots', 'empty', 'navigation'):
            rows.append(await ordinary_case(kind))
    source_check()
    result = {'modules': modules, 'controls': rows,
              'summary': {'total': len(rows), 'pass': sum(r['status'] == 'PASS' for r in rows),
                          'red': sum(r['status'] == 'RED' for r in rows), 'network_attempts': len(DENIED)},
              'qualification': 'OFF native source; before_get objects controlled. Ordinary full reports preserved for eventual exact proposal equality; A supplies independent real fenced BudgetedFetcher proof.'}
    path = ROOT / 'boundaries.original.json'
    assert not path.exists()
    path.write_text(json.dumps(result, indent=2, default=str)+'\n')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    asyncio.run(main())
