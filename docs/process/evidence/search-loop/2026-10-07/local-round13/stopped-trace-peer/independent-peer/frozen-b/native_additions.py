# --- stopped-discovery trace accounting -----------------------------------


async def _stopped_trace_case(
    tmp_path, monkeypatch, profile, *, kind="curated", mode="cap", signal=None, prime=False,
    entries=None, repeat=False,
):
    """Run native wrappers/get methods; only public source selection and I/O are synthetic."""
    import socket
    from contextlib import contextmanager
    from dataclasses import asdict
    from types import SimpleNamespace

    import httpx

    from app.adapters.search.fake import FakeSearchProvider
    from app.adapters.search.intent import DiscoveryIntent, queries_for
    from app.catalogue import discovery as catalogue
    from app.domain.enums import DegreeLevel
    from app.pipeline.control import UniversityReadStopped
    from app.pipeline.read_budget import BudgetedFetcher

    entries = entries or [{
        "name": "Example University", "country": "Example", "city": "City",
        "homepage": "https://example.edu/",
    }]
    events, exchanges, denied, observed = [], [], [], []
    counts = {}
    current = None
    original = signal if signal is not None else UniversityReadStopped("read_cap")

    def deny(*args, **kwargs):
        denied.append(True)
        raise AssertionError("Real network forbidden")

    hosts = {entry["homepage"].split("/")[2] for entry in entries}

    def dns(host, port, *args, **kwargs):
        assert host in hosts
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", dns)

    @contextmanager
    def scope(candidate):
        nonlocal current
        current = candidate.name
        counts[current] = 59 if mode == "identity-stop" else 56 if mode in {"cap", "control"} else 0
        if mode == "enter" or (len(entries) > 1 and current == entries[1]["name"]):
            raise original
        yield

    def reserve():
        before = counts[current]
        refused = before >= 60 or (mode == "timeout" and before == 3)
        events.append({"institution": current, "before": before, "admitted": not refused})
        if refused:
            events[-1]["exchanges_at_stop"] = len(exchanges)
            raise original if mode != "timeout" else TimeoutError("synthetic ordinary timeout")
        counts[current] += 1

    query_map = {}
    for entry in entries:
        host = entry["homepage"].split("/")[2]
        for field_name in (profile.context.intended_fields[0], "Computer Science"):
            intent = DiscoveryIntent(entry["name"], host, DegreeLevel.BACHELOR, field_name)
            for query in queries_for(intent, budget=6):
                query_map[query.text] = [(f"https://{host}/bachelors/computer-science", "Bachelor Computer Science", "")]
        identity = f'"{entry["name"]}" "{entry["country"]}" official university website'
        query_map[identity] = [] if mode == "identity-missing" else [(entry["homepage"], entry["name"], "")]
    provider = FakeSearchProvider(query_map, now=datetime(2026, 10, 8, tzinfo=UTC))

    def exchange(request):
        host = request.headers["host"]
        assert host in hosts and request.url.host == "93.184.216.34"
        exchanges.append({"host": host, "path": request.url.path})
        entry = next(e for e in entries if e["homepage"].split("/")[2] == host)
        if request.url.path == "/robots.txt":
            body = f"User-agent: *\nAllow: /\nSitemap: https://{host}/sitemap.xml\n"
            content_type = "text/plain"
        elif request.url.path == "/sitemap.xml":
            body = sitemap_xml()
            content_type = "application/xml"
        elif request.url.path == "/bachelors/computer-science":
            body = program_html()
            content_type = "text/html"
        else:
            body = f'<html><title>{entry["name"]}</title><h1>{entry["name"]}</h1><p>' + "Welcome to our institution. " * 30 + "</p></html>"
            content_type = "text/html"
        return httpx.Response(200, text=body, headers={"content-type": content_type})

    class PrimedCatalogue(catalogue.CatalogueDiscoveryAdapter):
        async def _enrich(self, uni, applicant, candidate, trace):
            if prime:
                trace.search_queries_sent = 1
                candidate.search_queries_used = 4
                trace.search_failures.append("Earlier identity diagnostic")
                trace.search_limitations.append("Earlier identity limitation")
            observed.append(trace)
            return await super()._enrich(uni, applicant, candidate, trace)

    fetcher = BudgetedFetcher(tmp_path / "cache", before_get=reserve, delay_seconds=0)
    rows = []
    for index, entry in enumerate(entries):
        registry = dict(entry)
        if mode == "timeout":
            registry["seeds"] = {"program_page": entry["homepage"] + "bachelors/computer-science"}
        if prime:
            registry["name"] = "Registry Alias University"
            host = entry["homepage"].split("/")[2]
            intent = DiscoveryIntent(registry["name"], host, DegreeLevel.BACHELOR, "Computer Science")
            for query in queries_for(intent, budget=6):
                query_map[query.text] = [(entry["homepage"] + "bachelors/computer-science", "Bachelor Computer Science", "")]
        rows.append(SimpleNamespace(id=f"offline-{index}", name=entry["name"], country=entry["country"],
                    city=entry["city"], domain="" if mode.startswith("identity-") else entry["homepage"].split("/")[2],
                    registry_entry=None if mode.startswith("identity-") else registry, aliases=[], seed_snapshot={}))
    if kind == "catalogue":
        session = SimpleNamespace(get=lambda *a: None, add=lambda *a: None, flush=lambda: None)
        adapter = PrimedCatalogue(fetcher, session=session, university_ids=[r.id for r in rows], live_limit=len(rows), research_scope=scope)
        monkeypatch.setattr(catalogue, "retrieve", lambda *a, **k: rows)
        monkeypatch.setattr(catalogue, "get_search_provider", lambda: provider)
    else:
        adapter = LiveDiscoveryAdapter(fetcher, registry_path=tmp_path / "unused.json", research_scope=scope)
        monkeypatch.setattr(adapter, "registry", lambda: entries)
    adapter._search_provider = provider
    adapter._search_provider_resolved = True
    captured, error, first_trace = [], None, None
    async with httpx.AsyncClient(transport=httpx.MockTransport(exchange), follow_redirects=False) as client:
        fetcher._client = client
        for _ in range(2 if repeat else 1):
            try:
                candidates = await adapter.discover(profile, len(entries))
            except BaseException as caught:
                error = caught
                break
            if first_trace is None:
                first_trace = adapter.traces[0]
            captured.append({"candidates": [asdict(c) for c in candidates], "traces": [t.as_dict() for t in adapter.traces]})
        fetcher._client = None
    assert not denied
    return SimpleNamespace(adapter=adapter, captured=captured, error=error, original=original, provider=provider,
                           events=events, exchanges=exchanges, counts=counts, stats=dict(fetcher.stats),
                           tiers=dict(fetcher.tier_counts), first_trace=first_trace, observed=observed)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["curated", "catalogue"])
async def test_stopped_native_discovery_exports_spent_queries(tmp_path, monkeypatch, profile_bachelor, kind):
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind=kind)
    out = case.captured[0]
    candidate, trace = out["candidates"][0], out["traces"][0]
    assert case.error is None and len(case.provider.calls) == 6
    assert candidate["search_queries_used"] == trace["search_queries_attempted"] == 6
    assert candidate["domain"] == "" and candidate["programs"] == []
    assert candidate["catalogue_id"] == ("offline-0" if kind == "catalogue" else None)
    assert trace["sitemaps_read"] and trace["used_navigation_fallback"]
    assert trace["walker"]["catalogs_walked"] == 1 and trace["selected"] == {}
    assert len(case.events) == 5 and sum(e["admitted"] for e in case.events) == 4
    assert case.counts == {"Example University": 60} and sum(case.stats.values()) == 4
    assert len(case.exchanges) == case.events[-1]["exchanges_at_stop"]
    assert any("read_cap" in text and "unknown" in text for text in trace["search_limitations"])


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["curated", "catalogue"])
async def test_scope_entry_stop_exports_only_unobserved_seed(tmp_path, monkeypatch, profile_bachelor, kind):
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind=kind, mode="enter")
    row = case.captured[0]
    assert not case.provider.calls and not case.events and not case.exchanges
    assert row["candidates"][0]["search_queries_used"] == row["traces"][0]["search_queries_attempted"] == 0
    assert row["candidates"][0]["domain"] == "" and not row["candidates"][0]["programs"]
    assert row["traces"][0]["institution"] == "Example University"
    assert row["traces"][0]["domain"] == ("example.edu" if kind == "catalogue" else "")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind, signal_name", [("curated", "busy"), ("catalogue", "busy"),
    ("curated", "async"), ("curated", "cancel"), ("catalogue", "lease")])
async def test_stopped_accounting_keeps_propagating_controls(tmp_path, monkeypatch, profile_bachelor, kind, signal_name):
    from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped

    signal = {"busy": UniversityReadStopped("checkpoint_busy"), "async": asyncio.CancelledError(),
              "cancel": RunCancelled(), "lease": LeaseLost()}[signal_name]
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind=kind, mode="control", signal=signal)
    assert case.error is signal and case.captured == [] and case.adapter.traces == []
    assert len(case.provider.calls) == 6 and len(case.events) == 5
    assert len(case.exchanges) == case.events[-1]["exchanges_at_stop"]


@pytest.mark.asyncio
async def test_future_read_reason_preserves_observed_trace(tmp_path, monkeypatch, profile_bachelor):
    from app.pipeline.control import UniversityReadStopped

    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, signal=UniversityReadStopped("future_native_reason"))
    row = case.captured[0]
    assert row["candidates"][0]["search_queries_used"] == row["traces"][0]["search_queries_attempted"] == 6
    assert any("future_native_reason" in s for s in row["traces"][0]["search_limitations"])


@pytest.mark.asyncio
@pytest.mark.parametrize("kind, mode", [("curated", "success"), ("catalogue", "success"), ("catalogue", "timeout")])
async def test_trace_lifecycle_ordinary_completion_and_timeout(tmp_path, monkeypatch, profile_bachelor, kind, mode):
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind=kind, mode=mode)
    row = case.captured[0]
    assert case.error is None
    if mode == "timeout":
        assert row["traces"][0]["search_queries_attempted"] == 0
        assert row["traces"][0]["manual_seeds"] == {} and row["candidates"][0]["programs"] == []
        assert row["traces"][0]["errors"] == ["Live discovery time limit reached; local university candidate retained."]
    else:
        assert row["candidates"][0]["programs"]
        assert row["candidates"][0]["search_queries_used"] == row["traces"][0]["search_queries_attempted"] == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["identity-stop", "identity-missing"])
async def test_native_identity_query_count_survives_before_inner_entry(tmp_path, monkeypatch, profile_bachelor, mode):
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind="catalogue", mode=mode)
    row = case.captured[0]
    assert len(case.provider.calls) == 1
    assert row["candidates"][0]["search_queries_used"] == row["traces"][0]["search_queries_attempted"] == 1
    assert not row["candidates"][0]["programs"] and row["candidates"][0]["domain"] == ""
    if mode == "identity-stop":
        assert len(case.events) == 2 and len(case.exchanges) == 1
    else:
        assert not case.events and not case.exchanges


@pytest.mark.asyncio
async def test_catalogue_stopped_trace_keeps_owner_and_prefix_once(tmp_path, monkeypatch, profile_bachelor):
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind="catalogue", prime=True)
    row = case.captured[0]
    candidate, trace = row["candidates"][0], row["traces"][0]
    assert len(case.provider.calls) == 2
    assert candidate["search_queries_used"] == trace["search_queries_attempted"] == 6
    assert trace["institution"] == candidate["name"] == "Example University"
    assert trace["search_failures"] == ["Earlier identity diagnostic"]
    assert trace["search_limitations"].count("Earlier identity limitation") == 1
    assert candidate["catalogue_id"] == "offline-0" and candidate["domain"] == "" and not candidate["programs"]


@pytest.mark.asyncio
async def test_next_scope_stop_does_not_reuse_previous_university_trace(tmp_path, monkeypatch, profile_bachelor):
    entries = [{"name": "Example University", "country": "Example", "city": "City", "homepage": "https://example.edu/"},
               {"name": "Second University", "country": "Example", "city": "City", "homepage": "https://second.edu/"}]
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, kind="catalogue", entries=entries)
    candidates, traces = case.captured[0]["candidates"], case.captured[0]["traces"]
    assert [c["catalogue_id"] for c in candidates] == ["offline-0", "offline-1"]
    assert [t["institution"] for t in traces] == [e["name"] for e in entries]
    assert [c["search_queries_used"] for c in candidates] == [6, 0]
    assert [t["search_queries_attempted"] for t in traces] == [6, 0]
    assert traces[1]["sitemaps_read"] == [] and traces[1]["walker"]["catalogs_walked"] == 0
    assert case.adapter.traces[0].errors is not case.adapter.traces[1].errors
    assert case.adapter.traces[0].search_limitations is not case.adapter.traces[1].search_limitations


@pytest.mark.asyncio
async def test_repeated_discovery_does_not_reset_or_mutate_prior_owned_trace(tmp_path, monkeypatch, profile_bachelor):
    case = await _stopped_trace_case(tmp_path, monkeypatch, profile_bachelor, repeat=True)
    assert len(case.provider.calls) == 12
    assert [r["candidates"][0]["search_queries_used"] for r in case.captured] == [6, 6]
    assert case.first_trace is not case.adapter.traces[0]
    assert case.first_trace.as_dict() == case.captured[0]["traces"][0]
    assert case.first_trace.search_limitations is not case.adapter.traces[0].search_limitations
