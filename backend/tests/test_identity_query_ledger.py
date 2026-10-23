"""Identity and programme search must share one institution's attempt budget.

No real Fetcher, DB, provider, applicant file or evaluation labels are used.
Actual frozen or externally proposed production methods run through a fake
vendor and the real production throttle latch. Counts are seam attempts, not
claims about vendor HTTP dispatch.
"""

import asyncio
import socket
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace, PageCategory
from app.adapters.search import _ThrottleLatch, intent, reset_search_throttle
from app.adapters.search.base import (
    SearchError,
    SearchProviderNotConfigured,
    SearchResponse,
    SearchResult,
    SearchUnavailable,
)
from app.catalogue import discovery as catalogue
from app.schemas.profile import ApplicantProfileIn
from evaluation.research.live import _ExpertBudget

NAME = "Example University"
ENTRY = {
    "name": NAME,
    "country": "Test Country",
    "city": "Test City",
    "homepage": "https://discovered.example.edu/",
}


def profile(multi=False):
    return ApplicantProfileIn.model_validate(
        {
            "context": {
                "level": "bachelor",
                "intended_fields": ["Computer Science", "Mathematics"]
                if multi
                else ["Computer Science"],
                "intake_year": 2027,
                "citizenship": "KZ",
                "country_of_residence": "KZ",
                "education_country": "KZ",
                "education_system": "KZ",
            }
        }
    )


class Vendor:
    name = "exa"

    def __init__(self, mode="searched", status=500):
        self.mode = mode
        self.status = status
        self.calls = []

    async def search(self, *, query, domains=(), max_results=10):
        self.calls.append({"query": query, "domains": tuple(domains), "max_results": max_results})
        identity = "official university website" in query
        if identity and self.mode == "error":
            raise SearchUnavailable("synthetic failure", http_status=self.status)
        now = datetime(2026, 10, 7, tzinfo=UTC)
        results = (
            (
                SearchResult(
                    url=ENTRY["homepage"], title=NAME, provider=self.name, rank=1, retrieved_at=now
                ),
            )
            if identity and self.mode == "searched"
            else ()
        )
        return SearchResponse(query=query, provider=self.name, retrieved_at=now, results=results)


class Guard:
    name = "exa"

    def __init__(self, vendor, local_refusal=False):
        self.vendor = vendor
        self.local_refusal = local_refusal
        self.attempts = []
        self.budget = _ExpertBudget(60, 120.0, "exa", time.monotonic())

    async def search(self, *, query, domains=(), max_results=10):
        self.attempts.append(query)
        if self.local_refusal:
            raise SearchUnavailable("synthetic wrapper refused before vendor dispatch")
        self.budget.before_search(self.name)
        return await self.vendor.search(query=query, domains=domains, max_results=max_results)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    reset_search_throttle()
    attempts = []

    def refused(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("A test attempted real network")

    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket, "create_connection", refused)
    yield
    reset_search_throttle()
    assert attempts == []


def build(monkeypatch, *, mode="searched", strict=False, local_refusal=False, vendor=None):
    vendor = vendor or Vendor(mode)
    guarded = Guard(vendor, local_refusal) if strict or local_refusal else vendor
    factories = []

    def factory():
        factories.append(True)
        if mode == "factory_error":
            raise SearchProviderNotConfigured("synthetic provider not configured")
        return _ThrottleLatch(guarded)

    monkeypatch.setattr(catalogue, "get_search_provider", factory)
    monkeypatch.setattr("app.adapters.search.get_search_provider", factory)
    fetcher = SimpleNamespace(get=AsyncMock(side_effect=AssertionError("No page reads allowed")))
    adapter = catalogue.CatalogueDiscoveryAdapter(
        fetcher, session=SimpleNamespace(), university_ids=["synthetic"], live_limit=1
    )
    adapter.sitemaps.collect = AsyncMock()
    adapter._navigation_fallback = AsyncMock()
    adapter._confirm_programs = AsyncMock()
    adapter._walk_catalogs = AsyncMock()
    adapter._confirm_added_programs = AsyncMock()
    probes = []

    async def probe(uni, url):
        probes.append(url)
        if mode == "seed" or (mode == "searched" and url == ENTRY["homepage"]):
            return dict(ENTRY)
        return None

    adapter._probe_site = probe
    return SimpleNamespace(
        adapter=adapter,
        vendor=vendor,
        guarded=guarded,
        factories=factories,
        probes=probes,
        fetcher=fetcher,
    )


async def enrich(
    built, *, mode="searched", initial=0, multi=False, candidate_initial=None, trace_initial=None
):
    uni = SimpleNamespace(
        id="synthetic",
        name=NAME,
        aliases=[NAME],
        domain="example.edu",
        country="Test Country",
        city="Test City",
        registry_entry=dict(ENTRY) if mode == "registry" else None,
        seed_snapshot={"record": {"official_site": "http://www.example.edu/"}},
    )
    trace = DiscoveryTrace(institution=NAME, domain=uni.domain)
    trace.search_queries_sent = initial if trace_initial is None else trace_initial
    candidate = Candidate(
        name=NAME,
        country=uni.country,
        city=uni.city,
        search_queries_used=initial if candidate_initial is None else candidate_initial,
    )
    found, returned = await built.adapter._enrich(uni, profile(multi), candidate, trace)
    assert built.fetcher.get.await_count == 0
    return found, returned


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True], ids=["single", "multi"])
@pytest.mark.parametrize("initial", [0, 1, 6])
async def test_searched_identity_and_real_programme_planner_share_budget(
    monkeypatch, multi, initial
):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch)
    found, trace = await enrich(built, initial=initial, multi=multi)
    assert len(built.vendor.calls) == max(0, 6 - initial)
    assert trace.search_queries_sent == 6
    assert found.search_queries_used == 6
    identities = sum("official university website" in c["query"] for c in built.vendor.calls)
    assert identities == (0 if initial == 6 else 1)
    if initial == 6:
        assert built.factories == []
        assert found.programs == []
        assert trace.search_limitations


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True], ids=["single", "multi"])
@pytest.mark.parametrize("initial", [0, 1, 6])
@pytest.mark.parametrize("mode", ["seed", "registry"])
async def test_seed_or_registry_is_not_charged_and_existing_count_survives(
    monkeypatch, multi, initial, mode
):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch, mode=mode)
    found, trace = await enrich(built, mode=mode, initial=initial, multi=multi)
    assert not any("official university website" in c["query"] for c in built.vendor.calls)
    assert len(built.vendor.calls) == 6 - initial
    assert found.search_queries_used == trace.search_queries_sent == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["unknown", "error", "factory_error"])
@pytest.mark.parametrize("initial", [0, 1, 6])
async def test_identity_early_return_preserves_attempt_or_factory_failure(
    monkeypatch, mode, initial
):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch, mode=mode)
    found, trace = await enrich(built, mode=mode, initial=initial)
    charge = int(initial < 6 and mode != "factory_error")
    assert len(built.vendor.calls) == charge
    assert found.search_queries_used == trace.search_queries_sent == initial + charge
    assert found.programs == []
    if initial == 6:
        assert built.factories == []
    if mode == "factory_error":
        assert len(built.vendor.calls) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True], ids=["single", "multi"])
@pytest.mark.parametrize("initial", [0, 1, 6])
async def test_direct_planner_honours_remaining_count_and_zero_is_safe(monkeypatch, multi, initial):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch)
    trace = DiscoveryTrace(institution=NAME, domain="example.edu")
    trace.search_queries_sent = initial
    selected = {c: [] for c in PageCategory.ALL}
    await built.adapter._add_search_results(ENTRY, "example.edu", selected, trace, profile(multi))
    assert len(built.vendor.calls) == 6 - initial
    assert trace.search_queries_sent == 6
    if initial == 6:
        assert built.factories == []


@pytest.mark.asyncio
async def test_direct_multifield_zero_budget_does_not_dispatch(monkeypatch):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch)
    trace = DiscoveryTrace(institution=NAME, domain="example.edu", search_queries_sent=6)
    selected = {c: [] for c in PageCategory.ALL}
    await built.adapter._add_multi_field_search_results(
        ENTRY, "example.edu", selected, trace, profile(True), _ThrottleLatch(built.vendor)
    )
    assert built.vendor.calls == []
    assert trace.search_coverage == {"requested": 2, "queried": 0, "represented": 0}
    assert trace.queried_fields == []


@pytest.mark.asyncio
async def test_candidate_ledger_does_not_get_reset_by_fresh_identity_trace(monkeypatch):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch)
    found, trace = await enrich(built, candidate_initial=1, trace_initial=0)
    assert len(built.vendor.calls) == 5
    assert found.search_queries_used == trace.search_queries_sent == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True], ids=["single", "multi"])
async def test_strict_evaluation_guard_never_receives_seventh_attempt(monkeypatch, multi):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch, strict=True)
    found, trace = await enrich(built, multi=multi)
    assert len(built.vendor.calls) == len(built.guarded.attempts) == 6
    assert built.guarded.budget.blocked_search_queries == 0
    assert built.guarded.budget.stop_reason is None
    assert built.guarded.budget.provider_failure is None
    assert trace.search_failures == []
    assert found.search_queries_used == 6


@pytest.mark.asyncio
async def test_local_identity_rejection_is_attempt_telemetry_not_http_dispatch(monkeypatch):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    built = build(monkeypatch, local_refusal=True)
    found, trace = await enrich(built)
    assert len(built.guarded.attempts) == 1
    assert built.vendor.calls == []
    assert found.search_queries_used == trace.search_queries_sent == 1
    payload = trace.as_dict()
    assert payload["search_queries_attempted"] == 1
    assert "search_queries_sent" not in payload
    assert "vendor_http_requests" not in payload


@pytest.mark.asyncio
async def test_real_429_latch_blocks_second_vendor_dispatch_and_counts_only_attempts(monkeypatch):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)
    vendor = Vendor("error", status=429)
    built = build(monkeypatch, mode="error", vendor=vendor)
    for _ in range(2):
        found, trace = await enrich(built, mode="error")
        assert found.search_queries_used == trace.search_queries_sent == 1
        assert trace.as_dict()["search_queries_attempted"] == 1
        assert "429" in trace.search_failures[0]
    assert len(vendor.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True], ids=["single", "multi"])
@pytest.mark.parametrize("initial", [0, 1, 6])
async def test_shared_disabled_preserves_six_programme_attempts_and_exposes_total(
    monkeypatch, multi, initial
):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", False)
    built = build(monkeypatch)
    found, trace = await enrich(built, initial=initial, multi=multi)
    assert len(built.vendor.calls) == 7
    assert sum("official university website" not in c["query"] for c in built.vendor.calls) == 6
    assert found.search_queries_used == trace.search_queries_sent == initial + 7


@pytest.mark.asyncio
@pytest.mark.parametrize("multi", [False, True], ids=["single", "multi"])
@pytest.mark.parametrize("error_type", [SearchError, SearchProviderNotConfigured])
async def test_escaping_search_error_after_dispatch_keeps_every_attempt(
    monkeypatch, multi, error_type
):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)

    class ProgrammeFailure(Vendor):
        async def search(self, *, query, domains=(), max_results=10):
            response = await super().search(query=query, domains=domains, max_results=max_results)
            if "official university website" not in query:
                raise error_type("synthetic ordinary SearchError after vendor call")
            return response

    built = build(monkeypatch, vendor=ProgrammeFailure())
    found, trace = await enrich(built, multi=multi)
    expected = 3 if multi else 2
    assert len(built.vendor.calls) == expected
    assert trace.search_queries_sent == found.search_queries_used == expected
    assert trace.search_failures
    assert found.programs == []


@pytest.mark.asyncio
async def test_cancellation_records_in_memory_attempt_without_durability_claim(monkeypatch):
    monkeypatch.setattr(intent, "SHARED_QUERY_BUDGET", True)

    class CancelAfterCall(Vendor):
        async def search(self, *, query, domains=(), max_results=10):
            await super().search(query=query, domains=domains, max_results=max_results)
            raise asyncio.CancelledError()

    built = build(monkeypatch, vendor=CancelAfterCall())
    trace = DiscoveryTrace(institution=NAME, domain="example.edu")
    selected = {c: [] for c in PageCategory.ALL}
    with pytest.raises(asyncio.CancelledError):
        await built.adapter._add_search_results(ENTRY, "example.edu", selected, trace, profile())
    assert len(built.vendor.calls) == trace.search_queries_sent == 1
    # No Candidate or RetrievalReport returned and no DB/checkpoint exists.
    # This assertion covers only the still-reachable in-memory trace.
    assert trace.as_dict()["search_queries_attempted"] == 1
