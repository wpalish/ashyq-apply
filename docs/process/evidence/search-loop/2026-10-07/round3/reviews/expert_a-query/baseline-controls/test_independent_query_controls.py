"""Independent offline controls; loads only a hash-pinned external proposal.

These tests count the fake vendor independently of implementation ledger fields.
They do not import Expert B's fixtures or read evaluation datasets.
"""
import asyncio
import socket
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace, PageCategory
from app.adapters.search import _ThrottleLatch, intent, reset_search_throttle
from app.adapters.search.base import SearchError, SearchProviderNotConfigured, SearchResponse, SearchResult
from app.adapters.search.retrieval import discover_candidates
from app.catalogue import discovery as catalogue
from app.schemas.profile import ApplicantProfileIn

ENTRY = {"name": "Independent Test University", "country": "Example Country", "city": "Example City", "homepage": "https://discovered.example.edu/"}
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def profile(multi):
    return ApplicantProfileIn.model_validate({"context": {"level": "bachelor", "intended_fields": ["Computer Science", "Mathematics"] if multi else ["Computer Science"], "intake_year": 2027, "citizenship": "KZ", "country_of_residence": "KZ", "education_country": "KZ", "education_system": "KZ"}})


class IndependentVendor:
    name = "exa"

    def __init__(self, fail_at=None, exception=None):
        self.calls = []
        self.fail_at = fail_at
        self.exception = exception

    async def search(self, *, query, domains=(), max_results=10):
        self.calls.append(query)
        if self.fail_at == len(self.calls):
            raise self.exception or SearchError("synthetic ordinary seam error")
        results = (SearchResult(url=ENTRY["homepage"], title=ENTRY["name"], provider="exa", rank=1, retrieved_at=NOW),) if "official university website" in query else ()
        return SearchResponse(query=query, provider="exa", retrieved_at=NOW, results=results)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    reset_search_throttle()
    def forbidden(*args, **kwargs):
        raise AssertionError("Real network forbidden")
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    yield
    reset_search_throttle()


def adapter(monkeypatch, vendor, factory_error=False):
    factories = []
    def factory():
        factories.append(True)
        if factory_error:
            raise SearchProviderNotConfigured("synthetic factory error")
        return _ThrottleLatch(vendor)
    monkeypatch.setattr(catalogue, "get_search_provider", factory)
    monkeypatch.setattr("app.adapters.search.get_search_provider", factory)
    fetcher = SimpleNamespace(get=AsyncMock(side_effect=AssertionError("No page reads allowed")))
    instance = catalogue.CatalogueDiscoveryAdapter(fetcher, session=SimpleNamespace(), university_ids=["audit"], live_limit=1)
    for name in ("_navigation_fallback", "_confirm_programs", "_walk_catalogs", "_confirm_added_programs"):
        setattr(instance, name, AsyncMock())
    instance.sitemaps.collect = AsyncMock()
    async def probe(uni, url):
        return dict(ENTRY) if url == ENTRY["homepage"] else None
    instance._probe_site = probe
    return instance, factories


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True])
async def test_vendor_identity_one_plus_five_no_callback_double_charge(monkeypatch, multi):
    vendor = IndependentVendor()
    instance, _ = adapter(monkeypatch, vendor)
    uni = SimpleNamespace(id="audit", name=ENTRY["name"], country=ENTRY["country"], city=ENTRY["city"], domain="example.edu", registry_entry=None, seed_snapshot={})
    candidate = Candidate(uni.name, uni.country, uni.city)
    old_trace = DiscoveryTrace(uni.name, uni.domain)
    found, trace = await instance._enrich(uni, profile(multi), candidate, old_trace)
    assert len(vendor.calls) == 6
    assert sum("official university website" in q for q in vendor.calls) == 1
    assert trace.search_queries_sent == found.search_queries_used == 6
    assert trace.as_dict()["search_queries_attempted"] == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True])
@pytest.mark.parametrize("precharged", [1, 6])
async def test_direct_real_planner_precharge_and_reentry(monkeypatch, multi, precharged):
    vendor = IndependentVendor()
    instance, factories = adapter(monkeypatch, vendor)
    trace = DiscoveryTrace(ENTRY["name"], "example.edu", search_queries_sent=precharged)
    selected = {category: [] for category in PageCategory.ALL}
    await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
    assert len(vendor.calls) == 6 - precharged
    assert trace.search_queries_sent == 6
    await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
    assert len(vendor.calls) == 6 - precharged
    if precharged == 6:
        assert factories == []


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True])
async def test_ordinary_SearchError_second_query_carries_exact_attempts(monkeypatch, multi):
    vendor = IndependentVendor(fail_at=2)
    instance, _ = adapter(monkeypatch, vendor)
    trace = DiscoveryTrace(ENTRY["name"], "example.edu", search_queries_sent=1)
    selected = {category: [] for category in PageCategory.ALL}
    await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
    # Multi-field keeps the old behavior: the second field still gets its
    # allocated2 attempts after field1 aborts at its second attempt.
    assert len(vendor.calls) == (4 if multi else 2)
    assert trace.search_queries_sent == 1 + len(vendor.calls)
    assert trace.search_failures
    vendor.fail_at = None
    await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
    assert len(vendor.calls) == 5
    assert trace.search_queries_sent == 6


@pytest.mark.asyncio
async def test_candidate_upstream_five_survives_lower_trace_and_identity_charge(monkeypatch):
    vendor = IndependentVendor()
    instance, _ = adapter(monkeypatch, vendor)
    uni = SimpleNamespace(id="audit", name=ENTRY["name"], country=ENTRY["country"], city=ENTRY["city"], domain="example.edu", registry_entry=None, seed_snapshot={})
    candidate = Candidate(uni.name, uni.country, uni.city, search_queries_used=5)
    found, trace = await instance._enrich(uni, profile(False), candidate, DiscoveryTrace(uni.name, uni.domain, search_queries_sent=2))
    assert len(vendor.calls) == 1
    assert "official university website" in vendor.calls[0]
    assert found.search_queries_used == trace.search_queries_sent == 6


@pytest.mark.asyncio
async def test_factory_error_never_counted_as_vendor_attempt(monkeypatch):
    vendor = IndependentVendor()
    instance, factories = adapter(monkeypatch, vendor, factory_error=True)
    uni = SimpleNamespace(id="audit", name=ENTRY["name"], country=ENTRY["country"], city=ENTRY["city"], domain="example.edu", registry_entry=None, seed_snapshot={})
    candidate = Candidate(uni.name, uni.country, uni.city, search_queries_used=3)
    found, trace = await instance._enrich(uni, profile(False), candidate, DiscoveryTrace(uni.name, uni.domain, search_queries_sent=1))
    assert vendor.calls == [] and len(factories) == 1
    assert found.search_queries_used == trace.search_queries_sent == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_at", [None, 2])
async def test_retrieval_attempt_callback_once_per_actual_seam_attempt(failure_at):
    vendor = IndependentVendor(fail_at=failure_at)
    callbacks = []
    public_intent = intent.DiscoveryIntent.from_profile(profile(False), institution=ENTRY["name"], domain="example.edu")
    def record(*args):
        callbacks.append(args)
    if failure_at is None:
        result = await discover_candidates(vendor, public_intent, query_budget=5, on_query_attempt=record)
        assert len(callbacks) == len(vendor.calls) == len(result.queries_run) == 5
    else:
        with pytest.raises(SearchError):
            await discover_candidates(vendor, public_intent, query_budget=5, on_query_attempt=record)
        assert len(callbacks) == len(vendor.calls) == 2


@pytest.mark.asyncio
async def test_callback_rejection_prevents_vendor_dispatch():
    vendor = IndependentVendor()
    public_intent = intent.DiscoveryIntent.from_profile(profile(False), institution=ENTRY["name"], domain="example.edu")
    calls = []
    def deny(*args):
        calls.append(args)
        raise RuntimeError("synthetic future preflight guard rejection")
    with pytest.raises(RuntimeError):
        await discover_candidates(vendor, public_intent, query_budget=5, on_query_attempt=deny)
    assert len(calls) == 1 and vendor.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True])
async def test_foreign_cancellation_is_not_swallowed_but_trace_charged(monkeypatch, multi):
    vendor = IndependentVendor(fail_at=1, exception=asyncio.CancelledError())
    instance, _ = adapter(monkeypatch, vendor)
    trace = DiscoveryTrace(ENTRY["name"], "example.edu", search_queries_sent=1)
    with pytest.raises(asyncio.CancelledError):
        await instance._add_search_results(ENTRY, "example.edu", {category: [] for category in PageCategory.ALL}, trace, profile(multi))
    assert len(vendor.calls) == 1 and trace.search_queries_sent == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True])
async def test_full_programme_slots_early_return_preserves_upstream_count(monkeypatch, multi):
    vendor = IndependentVendor()
    instance, _ = adapter(monkeypatch, vendor)
    trace = DiscoveryTrace(ENTRY["name"], "example.edu", search_queries_sent=1)
    selected = {category: [] for category in PageCategory.ALL}
    selected[PageCategory.PROGRAM_PAGE] = [f"https://example.edu/bsc/programme-{i}" for i in range(3)]
    await instance._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
    assert vendor.calls == [] and trace.search_queries_sent == 1


@pytest.mark.asyncio
async def test_existing_retrieval_call_without_callback_is_compatible():
    vendor = IndependentVendor()
    public_intent = intent.DiscoveryIntent.from_profile(profile(False), institution=ENTRY["name"], domain="example.edu")
    report = await discover_candidates(vendor, public_intent)
    assert len(report.queries_run) == len(vendor.calls) == 6
