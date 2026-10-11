"""Five native MockTransport unit modules: fixed answers, never actual DNS."""
from __future__ import annotations

import socket

import pytest

# These exact native modules already inject httpx.MockTransport, or their
# explicit RecordingClient.post stub. No production resolver is patched.
MODULE_HOST = {
    'tests.test_exa_provider': 'api.exa.ai',
    'tests.test_brave_provider': 'api.search.brave.com',
    'tests.test_serper_provider': 'google.serper.dev',
    'tests.test_tavily_provider': 'api.tavily.com',
    'tests.test_decisions': 'api.typesafe.ai',
}


BROWSER_CASES = {
    ('tests.test_live_discovery', 'TestCatalogWalkerContract', 'test_r5_js_json_payload_yields_programs'): 'uni.edu',
    ('tests.test_live_discovery', 'TestCatalogWalkerContract', 'test_r6_js_unrelated_json_falls_through'): 'uni.edu',
    ('tests.test_live_regressions', 'TestBrowserTierIsReallyUsed', 'test_an_empty_shell_page_escalates_to_the_renderer'): 'uni.edu',
    ('tests.test_redirect_provenance', '', 'test_browser_navigation_records_and_refuses_foreign_final_url'): 'uni.edu',
    ('tests.test_live_regressions', 'TestBrowserTierIsReallyUsed', 'test_a_page_with_real_content_is_not_escalated'): 'uni.edu',
    ('tests.test_live_discovery', 'TestCatalogWalkerContract', 'test_r7_js_silent_shell_is_recorded_not_fatal'): 'uni.edu',
}


@pytest.fixture(autouse=True)
def fixed_mock_endpoint_resolution(request, monkeypatch):
    module = request.node.module.__name__
    cls = request.node.cls.__name__ if request.node.cls else ''
    function = request.node.originalname or request.node.name
    host = MODULE_HOST.get(module) or BROWSER_CASES.get((module, cls, function))
    if host is None:
        return
    from guard_runtime import STATE, deny, write_state

    def synthetic_resolution(requested_host, port, family=0, type=0, proto=0, flags=0):
        if requested_host != host or port != 443 or family not in (0, socket.AF_UNSPEC, socket.AF_INET):
            deny('mock endpoint resolver requested an unlisted host/port/family')
        if type not in (0, socket.SOCK_STREAM) or proto not in (0, socket.IPPROTO_TCP):
            deny('mock endpoint resolver requested an unlisted transport')
        STATE.setdefault('synthetic_mock_endpoint_resolutions', []).append({
            'module': request.node.module.__name__, 'host': host, 'port': port,
            'transport': 'native MockTransport/RecordingClient or exact FakeBrowser/StubClient case',
        })
        write_state()
        # Deterministic public address for the policy arithmetic only. Never
        # call a resolver, open a socket, change HTTP response, or reach a vendor.
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('93.184.216.34', port))]

    monkeypatch.setattr(socket, 'getaddrinfo', synthetic_resolution)
