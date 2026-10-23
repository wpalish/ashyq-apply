"""Independent finite controls; native client/factory through denied MockTransport."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_control as r


async def main(scenario: str):
    search, retrieval, _live = r.targets('on')
    clock = r.Clock()
    server = r.Server('meta')
    clients = []
    events = []
    checks = []
    native_client = r.httpx.AsyncClient

    def client_factory(*args, **kwargs):
        assert 'transport' not in kwargs
        client = native_client(*args, transport=r.httpx.MockTransport(server.handle), **kwargs)
        clients.append(client)
        return client

    def check(name, expected, actual):
        checks.append({'case': name, 'expected': expected, 'actual': actual,
                       'status': 'PASS' if expected == actual else 'RED'})

    def counts():
        return {method: sum(e['method'] == method for e in server.events)
                for method in ['initialize', 'notifications/initialized', 'tools/call']}

    async def ask(provider, query):
        try:
            result = await provider.search(query=query, domains=['example.edu'])
            events.append({'error': None, 'response': asdict(result)})
            return None
        except r.SearchUnavailable as exc:
            events.append({'error': r.error(exc), 'response': None})
            return exc

    with patch.object(r.config, 'get_settings', lambda: SimpleNamespace(search_provider='exa_mcp')), \
         patch.object(r.httpx, 'AsyncClient', client_factory), \
         patch.object(search, 'time', SimpleNamespace(monotonic=clock.monotonic)), \
         patch.object(r.mcp, 'time', SimpleNamespace(monotonic=clock.monotonic)), \
         patch.object(r.mcp, 'datetime', SimpleNamespace(now=lambda zone: r.FIXED_NOW)), \
         patch.object(r.mcp, 'asyncio', SimpleNamespace(sleep=clock.sleep, Lock=asyncio.Lock, timeout=asyncio.timeout)):
        if scenario == 'native-precreated':
            first = search.get_search_provider()
            already_created = search.get_search_provider()
            error1 = await ask(first, 'first public query')
            before = counts()
            error2 = await ask(already_created, 'already-created instance after refusal')
            error3 = await ask(search.get_search_provider(), 'instance created after refusal')
            check('no_extra_handshake_or_tool_after_escape', before, counts())
            check('actual_native_retry_two_tools_first', {'initialize': 1, 'notifications/initialized': 1, 'tools/call': 2}, before)
            check('all_errors_none_enum_identity', True, all(e and e.http_status is None and e.reason is r.SearchFailureReason.RATE_LIMITED for e in [error1,error2,error3]))
        elif scenario in ['native-429-to-meta', 'native-meta-to-429']:
            first_kind = 'http429' if scenario == 'native-429-to-meta' else 'meta'
            second_kind = 'meta' if first_kind == 'http429' else 'http429'
            server.mode = first_kind
            await ask(search.get_search_provider(), 'first explicit refusal')
            old_stamp = search._THROTTLED_ORIGIN['exa_mcp']
            clock.value = search._THROTTLED_UNTIL['exa_mcp']
            server.mode = second_kind
            second = await ask(search.get_search_provider(), 'new explicit refusal at exact expiry')
            after_dispatch = counts()
            local = await ask(search.get_search_provider(), 'local refusal with updated origin')
            new_stamp = search._THROTTLED_ORIGIN['exa_mcp']
            check('second_origin_replaces_expired_origin', True, new_stamp != old_stamp and new_stamp[0] == search._THROTTLED_UNTIL['exa_mcp'])
            check('local_preserves_latest_none_or429_and_enum', True, second is not None and local is not None and local.http_status == second.http_status and local.reason is second.reason)
            check('no_extra_HTTP_after_latest_escape', after_dispatch, counts())
            check('native_two_handshakes_and_three_tools', {'initialize': 2, 'notifications/initialized': 2, 'tools/call': 3}, counts())
            check('latest_metadata_exact', (None, 'rate limited') if second_kind == 'meta' else (429, None), (local.http_status, local.reason.value if local.reason else None))
        elif scenario == 'local-retrieval-charge':
            await ask(search.get_search_provider(), 'first escaped metadata refusal')
            before = counts()
            charges = []
            report = await retrieval.discover_candidates(search.get_search_provider(), r.DiscoveryIntent(institution='Synthetic University', domain='example.edu', degree='bachelor', field='computer science'), query_budget=6, on_query_attempt=lambda: charges.append(1))
            events.append({'report': asdict(report)})
            check('local_family_attempt_charged_once', 1, len(charges))
            check('only_one_family_in_report', 1, len(report.queries_run))
            check('local_refusal_causes_no_vendor_dispatch', before, counts())
            check('local_typed_throttle_true', True, report.throttled)
            check('no_fabricated_HTTP429_diagnostic', True, len(report.failure_diagnostics) == 1 and 'rate limited' in report.failure_diagnostics[0] and 'HTTP 429' not in report.failure_diagnostics[0])
        elif scenario == 'synthetic-status500':
            class Inner:
                name = 'exa_mcp'
                calls = 0
                async def search(self, **kwargs):
                    self.calls += 1
                    raise r.SearchUnavailable('synthetic typed refusal', http_status=500, reason=r.SearchFailureReason.RATE_LIMITED)
            inner = Inner()
            provider = search._ThrottleLatch(inner)
            first = await ask(provider, 'synthetic first')
            local = await ask(provider, 'synthetic local')
            check('synthetic_non429_status_not_reinterpreted', True, first.http_status == local.http_status == 500 and local.reason is r.SearchFailureReason.RATE_LIMITED)
            check('only_one_synthetic_inner_dispatch', 1, inner.calls)
            check('synthetic_control_not_vendor_integration', {'initialize':0,'notifications/initialized':0,'tools/call':0}, counts())
        else:
            raise ValueError(scenario)
        check('actual_native_methods_unchanged', True, all(getattr(r.mcp.ExaMcpSearchProvider, name) is method for name,method in r.METHODS.items()))
        check('owned_mock_clients_closed', True, all(client.is_closed and isinstance(client._transport,r.httpx.MockTransport) for client in clients))
        state = {'until':dict(search._THROTTLED_UNTIL),'origin':dict(search._THROTTLED_ORIGIN)}
    check('all_original_source_pins_preserved', r.SOURCE_BEFORE, r.source_pins())
    check('all_proposed_source_pins_preserved', r.PROPOSAL_BEFORE, r.proposal_pins())
    result = {'scenario':scenario,'checks':checks,'counts':{name:sum(c['status']==name for c in checks) for name in ['PASS','RED']}, 'events':events,'mock_HTTP_events':server.events,'mock_HTTP_counts':counts(),'child_state':state,'fake_sleeps':clock.sleeps,'synthetic_resolutions':r.resolutions,'native_methods':{name:method.__qualname__ for name,method in r.METHODS.items()},'original_source_before':r.SOURCE_BEFORE,'original_source_after':r.source_pins(),'proposed_source_before':r.PROPOSAL_BEFORE,'proposed_source_after':r.proposal_pins(),'real_network_calls':0,'primary_reset_calls':0,'qualification':'Only final synthetic-status500 uses a test provider; other controls use actual factory/Exa/MCP methods with MockTransport. Local charge proves attempt, not HTTP dispatch.'}
    out = r.B/'independent-controls'/f'{scenario}.json'
    out.parent.mkdir(exist_ok=True)
    assert not out.exists()
    out.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({'scenario':scenario,**result['counts']}))
    return bool(result['counts']['RED'])


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main(sys.argv[1])))
