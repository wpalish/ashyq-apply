from pathlib import Path
B=Path(__file__).resolve().parent
p=B/'proposed/tests/test_search_throttle_latch.py';s=p.read_text().replace('from datetime import UTC, datetime','from datetime import UTC, datetime\nfrom types import SimpleNamespace\nfrom typing import cast');s=s.replace('    SearchResponse,','    SearchResponse,');s=s.replace(')\n\n\nclass Refusing:', ')\nfrom app.adapters.search.base import SearchFailureReason\n\n\nclass Refusing:',1)
s=s.replace('def __init__(self, status: int | None = 429) -> None:', 'def __init__(self, status: int | None = 429, reason: SearchFailureReason | None = None) -> None:')
s=s.replace('        self.status = status','        self.status = status\n        self.error = SearchUnavailable("refused", http_status=status, reason=reason)',1)
s=s.replace('        raise SearchUnavailable("refused", http_status=self.status)', '        raise self.error',1)
s=s.replace('    assert search._THROTTLED_UNTIL == {}\n', '    assert search._THROTTLED_UNTIL == {}\n    assert getattr(search, "_THROTTLED_ORIGIN", {}) == {}\n',1)
s+='''

async def test_typed_status_none_is_shared_without_status_or_message_invention():
    first, second = Refusing(None, SearchFailureReason.RATE_LIMITED), Answering()
    with pytest.raises(SearchUnavailable) as initial:
        await _ThrottleLatch(first).search(query="first")
    assert initial.value is first.error
    with pytest.raises(SearchUnavailable) as local:
        await _ThrottleLatch(second).search(query="other adapter")
    assert first.calls == 1 and second.calls == 0
    assert local.value.http_status is None
    assert local.value.reason is SearchFailureReason.RATE_LIMITED
    assert "429" not in str(local.value)
    assert "quota" not in str(local.value)
    assert "request was not sent" in str(local.value)


@pytest.mark.parametrize("reason", [None, "rate limited"])
async def test_vendor_text_and_untyped_reason_do_not_latch(reason):
    import app.adapters.search as search

    # RATE_LIMITED is a StrEnum: equality to this string is true; identity is not.
    first = Refusing(None, cast(SearchFailureReason | None, reason))
    first.error = SearchUnavailable("rate limited vendor text", reason=cast(SearchFailureReason | None, reason))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(first).search(query="first")
    second = Answering()
    await _ThrottleLatch(second).search(query="second")
    assert second.calls == 1
    assert search._THROTTLED_UNTIL == {}
    assert getattr(search, "_THROTTLED_ORIGIN", {}) == {}


async def test_typed_origin_uses_one_deadline_with_a_ticking_clock(monkeypatch):
    import app.adapters.search as search

    ticks = iter((100.0, 101.0, 102.0))
    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    assert search._THROTTLED_UNTIL["exa_mcp"] == 101.0 + THROTTLE_COOLDOWN_SECONDS
    origin = getattr(search, "_THROTTLED_ORIGIN", {})
    assert origin["exa_mcp"] == (search._THROTTLED_UNTIL["exa_mcp"], None, SearchFailureReason.RATE_LIMITED)
    next_provider = Answering()
    with pytest.raises(SearchUnavailable) as local:
        await _ThrottleLatch(next_provider).search(query="later")
    assert next_provider.calls == 0
    assert local.value.http_status is None
    assert local.value.reason is SearchFailureReason.RATE_LIMITED


async def test_exact_typed_cooldown_expiry_and_provider_isolation(monkeypatch):
    import app.adapters.search as search

    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=lambda: clock.now))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    other = Answering()
    other.name = "tavily"
    await _ThrottleLatch(other).search(query="different provider")
    assert other.calls == 1
    deadline = search._THROTTLED_UNTIL["exa_mcp"]
    clock.now = deadline - 0.001
    before = Answering()
    with pytest.raises(SearchUnavailable) as local:
        await _ThrottleLatch(before).search(query="before expiry")
    assert before.calls == 0 and local.value.http_status is None
    clock.now = deadline
    after = Answering()
    await _ThrottleLatch(after).search(query="exact expiry")
    assert after.calls == 1


async def test_stale_origin_does_not_relabel_a_deliberately_injected_legacy_float(monkeypatch):
    import app.adapters.search as search

    monkeypatch.setattr(search, "time", SimpleNamespace(monotonic=lambda: 100.0))
    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    origin = getattr(search, "_THROTTLED_ORIGIN", {})
    assert origin["exa_mcp"] == (400.0, None, SearchFailureReason.RATE_LIMITED)
    # Only a test/operator legacy float injection changes the recorded deadline.
    # This is not evidence that current metadata None should become HTTP429.
    search._THROTTLED_UNTIL["exa_mcp"] = 900.0
    other = Answering()
    with pytest.raises(SearchUnavailable) as legacy:
        await _ThrottleLatch(other).search(query="legacy injected state")
    assert other.calls == 0
    assert legacy.value.http_status == 429 and legacy.value.reason is None
    assert origin["exa_mcp"] == (400.0, None, SearchFailureReason.RATE_LIMITED)


async def test_reset_clears_actual_typed_origin_before_a_new_query():
    import app.adapters.search as search

    with pytest.raises(SearchUnavailable):
        await _ThrottleLatch(Refusing(None, SearchFailureReason.RATE_LIMITED)).search(query="first")
    assert search._THROTTLED_UNTIL
    assert getattr(search, "_THROTTLED_ORIGIN", {})
    reset_search_throttle()
    assert search._THROTTLED_UNTIL == {}
    assert search._THROTTLED_ORIGIN == {}
    answering = Answering()
    await _ThrottleLatch(answering).search(query="after deliberate reset")
    assert answering.calls == 1
''';p.write_text(s)
p=B/'proposed/tests/test_search_layer_budget_fixes.py';s=p.read_text().replace('from typing import ClassVar','from typing import ClassVar, cast\n\nimport pytest').replace('    SearchProvider,','    SearchFailureReason,\n    SearchProvider,',1)
s=s.replace('def __init__(self, *, fail_with: int | None = None) -> None:', 'def __init__(self, *, fail_with: int | None = None, fail_reason: SearchFailureReason | None = None, fail_message: str | None = None) -> None:')
s=s.replace('        self.fail_with = fail_with','        self.fail_with = fail_with\n        self.fail_reason = fail_reason\n        self.fail_message = fail_message',1)
s=s.replace('''        if self.fail_with is not None:
            raise SearchUnavailable("refused", http_status=self.fail_with)''','''        if self.fail_with is not None or self.fail_reason is not None or self.fail_message is not None:
            raise SearchUnavailable(self.fail_message or "refused", http_status=self.fail_with, reason=self.fail_reason)''',1)
s=s.replace('async def test_a_throttled_run_records_a_quota_stop_not_a_miss():','async def test_a_throttled_run_records_status_and_incomplete_rate_limit_stop():')
s=s.replace('''    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME}, DOMAIN, selected_with([]), trace, profile()
    )

    assert any("HTTP 429" in line for line in trace.search_limitations)
    assert any("quota stop" in line for line in trace.search_limitations)
    assert selected_with([])[PageCategory.PROGRAM_PAGE] == []''','''    selected = selected_with([])
    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME}, DOMAIN, selected, trace, profile()
    )

    assert any("HTTP 429" in line for line in trace.search_failures)
    assert any("rate-limit stop" in line and "incomplete" in line for line in trace.search_limitations)
    assert not any("quota" in line or "HTTP 429" in line for line in trace.search_limitations)
    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert len(provider.queries) == trace.search_queries_sent == 1
    assert fetcher.read == []''',1)
s=s.replace('''    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME},
        DOMAIN,
        selected_with([]),
        trace,''','''    selected = selected_with([])
    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME},
        DOMAIN,
        selected,
        trace,''',1)
s=s.replace('''    assert any("HTTP 429" in line for line in trace.search_limitations)


def test_the_provider_seam''','''    assert any("HTTP 429" in line for line in trace.search_failures)
    assert any("rate-limit stop" in line and "incomplete" in line for line in trace.search_limitations)
    assert not any("quota" in line or "HTTP 429" in line for line in trace.search_limitations)
    assert trace.search_queries_sent == 1
    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert fetcher.read == []


def test_the_provider_seam''',1)
s+='''

@pytest.mark.parametrize("status,reason", [(429, None), (None, SearchFailureReason.RATE_LIMITED)])
async def test_explicit_rate_limit_charges_only_the_attempted_family(status, reason):
    provider = CountingProvider(fail_with=status, fail_reason=reason)
    charges: list[int] = []
    report = await discover_candidates(provider, intent(), query_budget=6, on_query_attempt=lambda: charges.append(1))
    assert report.throttled is True
    assert len(charges) == len(report.queries_run) == len(provider.queries) == 1
    assert report.candidates == ()
    assert len(report.failed_queries) == 1
    assert len(report.failure_diagnostics) == 1
    if status is None:
        assert "rate limited" in report.failure_diagnostics[0]
        assert "HTTP" not in report.failure_diagnostics[0]
    else:
        assert "HTTP 429" in report.failure_diagnostics[0]


@pytest.mark.parametrize("reason", [None, "rate limited"])
async def test_untyped_vendor_refusal_does_not_cut_query_families(reason):
    provider = CountingProvider(fail_reason=cast(SearchFailureReason | None, reason), fail_message="rate limited vendor text")
    charges: list[int] = []
    report = await discover_candidates(provider, intent(), query_budget=6, on_query_attempt=lambda: charges.append(1))
    assert not report.throttled
    assert len(charges) == len(report.queries_run) == len(provider.queries) == 6
    assert report.candidates == ()
    assert len(report.failed_queries) == 6
    assert all("rate limited" not in line for line in report.failure_diagnostics)


@pytest.mark.parametrize("fields", [("Computer Science",), ("Computer Science", "Mathematics", "Physics")])
async def test_typed_status_none_caller_retains_safe_diagnostic_and_exact_query_charge(fields):
    provider = CountingProvider(fail_reason=SearchFailureReason.RATE_LIMITED)
    fetcher = RecordingFetcher()
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    trace.search_queries_sent = 1  # A prior identity query is not refunded.
    selected = selected_with([])
    await adapter(provider, fetcher)._add_search_results({"name": NAME}, DOMAIN, selected, trace, profile(fields))
    assert len(provider.queries) == 1
    assert trace.search_queries_sent == 2
    assert len(trace.search_failures) == 1
    assert "rate limited" in trace.search_failures[0]
    assert "HTTP" not in trace.search_failures[0]
    assert any("rate-limit stop" in line and "incomplete" in line for line in trace.search_limitations)
    assert not any("quota" in line or "HTTP" in line for line in trace.search_limitations)
    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert fetcher.read == []
''';p.write_text(s)
p=B/'proposed/tests/test_exa_mcp.py';s=p.read_text().replace('from typing import Any','from typing import Any\nfrom types import SimpleNamespace');s+='''

@pytest.fixture
async def make_factory_provider(monkeypatch):
    """Real factory and Exa methods; only its HTTP client transport is synthetic."""
    from app import config
    from app.adapters.search import get_search_provider

    original_client = httpx.AsyncClient
    clients: list[httpx.AsyncClient] = []
    handler: list[Reply] = []

    def client_factory(*args, **kwargs):
        assert "transport" not in kwargs
        client = original_client(*args, transport=httpx.MockTransport(handler[0]), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(search_provider="exa_mcp"))
    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    def make(server):
        handler[:] = [server]
        provider = get_search_provider()
        assert type(provider.inner) is ExaMcpSearchProvider
        return provider

    yield make
    for client in clients:
        await client.aclose()
    assert all(client.is_closed for client in clients)


@pytest.mark.parametrize("metadata,retry,tools", [(True, True, 2), (True, False, 1), (False, True, 1)])
async def test_factory_suppresses_only_post_escape_explicit_refusal(make_factory_provider, monkeypatch, metadata, retry, tools):
    import app.adapters.search as search

    assert module.RATE_LIMIT_RETRY is True
    assert module.RETRY_429_ONCE is False
    slept: list[float] = []
    async def sleep(seconds: float) -> None:
        slept.append(seconds)
    monkeypatch.setattr(module, "asyncio", SimpleNamespace(sleep=sleep, Lock=asyncio.Lock, timeout=asyncio.timeout))
    monkeypatch.setattr(module, "RATE_LIMIT_RETRY", retry)
    server = McpServer(result=RATE_LIMITED) if metadata else McpServer(overrides={"tools/call": lambda request: httpx.Response(429)})
    first = make_factory_provider(server)
    with pytest.raises(SearchUnavailable) as original:
        await first.search(query="first public programme query")
    assert original.value.http_status is (None if metadata else original.value.http_status)
    assert original.value.http_status == (None if metadata else 429)
    assert original.value.reason is (SearchFailureReason.RATE_LIMITED if metadata else None)
    assert server.methods == ["initialize", "notifications/initialized"] + ["tools/call"] * tools
    before = list(server.methods)
    # The second factory instance is constructed after the original error escaped.
    second = make_factory_provider(server)
    for provider in (first, second):
        with pytest.raises(SearchUnavailable) as local:
            await provider.search(query="later public query")
        assert local.value.http_status == original.value.http_status
        assert local.value.reason is original.value.reason
        assert "request was not sent" in str(local.value)
        if metadata:
            assert "429" not in str(local.value)
        assert server.methods == before
    assert slept == ([module.RATE_LIMIT_BACKOFF_SECONDS] if metadata and retry else [])
    assert search._THROTTLED_UNTIL


async def test_factory_does_not_latch_when_the_approved_native_retry_recovers(make_factory_provider, monkeypatch):
    import app.adapters.search as search

    assert module.RATE_LIMIT_RETRY is True
    slept: list[float] = []
    async def sleep(seconds: float) -> None:
        slept.append(seconds)
    monkeypatch.setattr(module, "asyncio", SimpleNamespace(sleep=sleep, Lock=asyncio.Lock, timeout=asyncio.timeout))
    server = _FlakyServer()
    first = make_factory_provider(server)
    response = await first.search(query="first public programme query")
    assert [row.url for row in response.results] == [row["url"] for row in ROWS]
    assert server.queries == 2
    assert search._THROTTLED_UNTIL == {}
    assert getattr(search, "_THROTTLED_ORIGIN", {}) == {}
    await first.search(query="later same adapter")
    await make_factory_provider(server).search(query="new adapter")
    assert server.queries == 4
    assert server.methods == ["initialize", "notifications/initialized", "tools/call", "tools/call", "tools/call", "initialize", "notifications/initialized", "tools/call"]
    assert slept == [module.RATE_LIMIT_BACKOFF_SECONDS]
    assert search._THROTTLED_UNTIL == {}


@pytest.mark.parametrize("value", [False, 1, "true"])
async def test_factory_metadata_requires_boolean_true(make_factory_provider, value):
    import app.adapters.search as search

    result = tool_result(ROWS, structured=True)
    result["_meta"] = {"ai.exa/rateLimited": value}
    server = McpServer(result=result)
    first = make_factory_provider(server)
    await first.search(query="first public programme query")
    await make_factory_provider(server).search(query="new adapter")
    assert server.methods.count("tools/call") == 2
    assert server.methods.count("initialize") == 2
    assert search._THROTTLED_UNTIL == {}
    assert getattr(search, "_THROTTLED_ORIGIN", {}) == {}
''';p.write_text(s)
