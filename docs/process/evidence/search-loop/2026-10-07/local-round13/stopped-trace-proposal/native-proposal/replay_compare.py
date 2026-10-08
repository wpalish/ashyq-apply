"""Normal owned module imports; finite actual-discovery output comparisons."""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.adapters.search.fake import FakeSearchProvider
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.read_budget import BudgetedFetcher
from tests.conftest import profile
from tests.test_live_discovery import _stopped_trace_case

OWN = Path(__file__).resolve().parent
MODE = sys.argv[1]
TARGET = OWN / f'whole-output.{MODE}.json'
assert MODE in {'off', 'on'} and not TARGET.exists()
METHODS = [LiveDiscoveryAdapter.discover, LiveDiscoveryAdapter._discover_one,
           CatalogueDiscoveryAdapter.discover, CatalogueDiscoveryAdapter._enrich,
           BudgetedFetcher.get, Fetcher.get, Fetcher._get, FakeSearchProvider.search]
SOURCES = [Path(inspect.getfile(x)) for x in METHODS]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

async def main():
    cases = [('curated-cap', {'kind': 'curated'}), ('catalogue-cap', {'kind': 'catalogue'}),
             ('curated-enter', {'kind': 'curated', 'mode': 'enter'}),
             ('catalogue-enter', {'kind': 'catalogue', 'mode': 'enter'}),
             ('curated-busy', {'kind': 'curated', 'mode': 'control', 'signal': UniversityReadStopped('checkpoint_busy')}),
             ('catalogue-busy', {'kind': 'catalogue', 'mode': 'control', 'signal': UniversityReadStopped('checkpoint_busy')}),
             ('curated-async', {'kind': 'curated', 'mode': 'control', 'signal': asyncio.CancelledError()}),
             ('curated-cancel', {'kind': 'curated', 'mode': 'control', 'signal': RunCancelled()}),
             ('catalogue-lease', {'kind': 'catalogue', 'mode': 'control', 'signal': LeaseLost()}),
             ('future-reason', {'kind': 'curated', 'signal': UniversityReadStopped('future_native_reason')}),
             ('curated-success', {'kind': 'curated', 'mode': 'success'}),
             ('catalogue-success', {'kind': 'catalogue', 'mode': 'success'}),
             ('catalogue-timeout', {'kind': 'catalogue', 'mode': 'timeout'}),
             ('identity-stop', {'kind': 'catalogue', 'mode': 'identity-stop'}),
             ('identity-missing', {'kind': 'catalogue', 'mode': 'identity-missing'}),
             ('catalogue-prefix-max-alias', {'kind': 'catalogue', 'prime': True}),
             ('two-institutions', {'kind': 'catalogue', 'entries': [
                 {'name': 'Example University', 'country': 'Example', 'city': 'City', 'homepage': 'https://example.edu/'},
                 {'name': 'Second University', 'country': 'Example', 'city': 'City', 'homepage': 'https://second.edu/'}]}),
             ('repeated-adapter', {'repeat': True})]
    rows = {}
    source_before = {str(p): sha(p) for p in set(SOURCES)}
    for name, kwargs in cases:
        with pytest.MonkeyPatch.context() as monkeypatch:
            result = await _stopped_trace_case(OWN / 'runtime' / f'compare-{MODE}' / name, monkeypatch,
                                             profile.__wrapped__(), **kwargs)
        rows[name] = {'captured': result.captured, 'exception': None if result.error is None else {
            'type': type(result.error).__name__, 'reason': getattr(result.error, 'reason', None),
            'same_original_object': result.error is result.original}, 'provider_calls': result.provider.calls,
            'get_reservations': result.events, 'read_counts': result.counts,
            'mock_HTTP_exchanges': result.exchanges, 'fetcher_stats': result.stats, 'fetch_tiers': result.tiers,
            'separate_walker_outcomes': [dataclasses.asdict(x) for x in result.adapter.walker_outcomes]}
    assert [LiveDiscoveryAdapter.discover, LiveDiscoveryAdapter._discover_one,
            CatalogueDiscoveryAdapter.discover, CatalogueDiscoveryAdapter._enrich,
            BudgetedFetcher.get, Fetcher.get, Fetcher._get, FakeSearchProvider.search] == METHODS
    assert source_before == {str(p): sha(p) for p in set(SOURCES)}
    TARGET.write_text(json.dumps({'mode': MODE, 'rows': rows, 'native_method_imports': [
        {'module': x.__module__, 'method': x.__qualname__, 'file': inspect.getfile(x)} for x in METHODS],
        'source_pre_post_sha256': source_before, 'real_network': 'denied by sockets; only explicitly synthetic DNS + MockTransport',
        'qualification': 'Native discovery report input, not canary/scorer or persisted Runner/Job/SQL; charged FakeSearchProvider seam attempts not vendor HTTP.'}, indent=2) + '\n')
    print(json.dumps({'mode': MODE, 'cases': len(rows), 'file': str(TARGET)}))

asyncio.run(main())
