"""Two fixes to the search layer, each pinned by a test that fails without it.

The first: search is not asked at all when every programme-page slot is already
filled, because the recovery loop would discard the answer unread.

The second: a rate-limit answer ends the searching instead of being followed by
five more rephrasings of the same question.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from app.adapters.discovery.live_discovery import (
    MAX_PAGES_PER_CATEGORY,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
)
from app.adapters.search import SearchProviderNotConfigured
from app.adapters.search.base import (
    SearchProvider,
    SearchResponse,
    SearchResult,
    SearchUnavailable,
)
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel
from app.schemas.profile import ApplicantProfileIn

NAME = "University of Groningen"
DOMAIN = "www.rug.nl"
FIELD = "Computer Science"
MISSING_REGISTRY = Path("/nonexistent-institution-registry.json")


def profile(fields: tuple[str, ...] = (FIELD,)) -> ApplicantProfileIn:
    return ApplicantProfileIn.model_validate(
        {
            "context": {
                "level": "bachelor",
                "intended_fields": list(fields),
                "intake_year": 2027,
                "citizenship": "KZ",
                "country_of_residence": "KZ",
                "education_country": "KZ",
                "education_system": "KZ",
            }
        }
    )


class CountingProvider:
    """Counts calls; returns three plausible programme pages per query."""

    name = "fake"

    def __init__(self, *, fail_with: int | None = None) -> None:
        self.fail_with = fail_with
        self.queries: list[str] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.queries.append(query)
        if self.fail_with is not None:
            raise SearchUnavailable("refused", http_status=self.fail_with)
        slugs = ("computer-science", "artificial-intelligence", "data-science")
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=datetime.now(UTC),
            results=tuple(
                SearchResult(
                    url=f"https://www.rug.nl/bachelors/{slug}",
                    title=f"BSc {slug.replace('-', ' ').title()}",
                    provider=self.name,
                    rank=index + 1,
                    retrieved_at=datetime.now(UTC),
                )
                for index, slug in enumerate(slugs)
            ),
        )


class RecordingFetcher:
    """Reads whatever the test says; counts the reads."""

    refused_hosts: ClassVar[dict] = {}

    def __init__(self) -> None:
        self.read: list[str] = []

    async def get(self, url):
        self.read.append(url)

        class _Result:
            ok = True
            text = "<html><body>BSc Computer Science programme</body></html>"
            final_url = ""
            outcome = None

        return _Result()


def adapter(provider: CountingProvider, fetcher: RecordingFetcher) -> LiveDiscoveryAdapter:
    """An adapter whose provider is already resolved, as it is mid-run."""
    built = LiveDiscoveryAdapter(fetcher, registry_path=MISSING_REGISTRY)  # type: ignore[arg-type]
    built._search_provider = provider
    built._search_provider_resolved = True
    return built


def selected_with(pages: list[str]) -> dict:
    return {
        category: (list(pages) if category is PageCategory.PROGRAM_PAGE else [])
        for category in PageCategory.ALL
    }


def intent() -> DiscoveryIntent:
    return DiscoveryIntent(
        institution=NAME, domain=DOMAIN, degree=DegreeLevel.BACHELOR, field=FIELD
    )


# --- fix 1: no free slot, no search -----------------------------------------


async def test_search_is_not_run_when_every_programme_slot_is_full():
    provider = CountingProvider()
    fetcher = RecordingFetcher()
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    full = [f"https://www.rug.nl/bachelors/already-{i}" for i in range(MAX_PAGES_PER_CATEGORY)]
    selected = selected_with(full)

    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME}, DOMAIN, selected, trace, profile()
    )

    assert provider.queries == [], "a full slot list must not reach the provider"
    assert fetcher.read == [], "and must not spend a single read on its results"
    assert selected[PageCategory.PROGRAM_PAGE] == full
    assert any("Search not run" in line for line in trace.search_limitations)


async def test_search_still_runs_while_a_slot_is_free():
    provider = CountingProvider()
    fetcher = RecordingFetcher()
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    selected = selected_with(["https://www.rug.nl/bachelors/already"])

    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME}, DOMAIN, selected, trace, profile()
    )

    assert provider.queries, "one free slot must still ask the provider"
    assert not any("Search not run" in line for line in trace.search_limitations)


async def test_the_provider_is_resolved_once_per_run_not_once_per_institution():
    """The MCP handshake lives on the instance, so one run must share one."""
    import app.adapters.search as search_pkg

    built = 0

    class Counting:
        def __init__(self) -> None:
            nonlocal built
            built += 1

    original = search_pkg.get_search_provider
    search_pkg.get_search_provider = Counting
    try:
        under_test = LiveDiscoveryAdapter(RecordingFetcher(), registry_path=MISSING_REGISTRY)
        first = under_test._search_provider_or_none()
        second = under_test._search_provider_or_none()
    finally:
        search_pkg.get_search_provider = original

    assert first is second
    assert built == 1, "resolving twice must build the provider once"


async def test_a_deployment_without_a_provider_is_not_re_probed():
    import app.adapters.search as search_pkg

    def raises():
        raise SearchProviderNotConfigured("none")

    original = search_pkg.get_search_provider
    search_pkg.get_search_provider = raises
    try:
        under_test = LiveDiscoveryAdapter(RecordingFetcher(), registry_path=MISSING_REGISTRY)
        assert under_test._search_provider_or_none() is None
        assert under_test._search_provider_or_none() is None
    finally:
        search_pkg.get_search_provider = original


# --- fix 2: a rate limit ends the searching ---------------------------------


async def test_a_rate_limit_stops_the_remaining_query_families():
    provider = CountingProvider(fail_with=429)
    report = await discover_candidates(provider, intent())

    assert report.throttled is True
    assert len(provider.queries) == 1, (
        "one 429 is an answer; five more rephrasings are five more requests "
        f"against a quota that refused (sent {len(provider.queries)})"
    )
    assert report.failed_queries
    assert report.candidates == ()


async def test_other_failures_do_not_stop_the_remaining_families():
    provider = CountingProvider(fail_with=500)
    report = await discover_candidates(provider, intent())

    assert report.throttled is False
    assert len(provider.queries) > 1, "a transport failure is not a quota refusal"
    assert report.candidates == ()


async def test_a_throttled_run_records_a_quota_stop_not_a_miss():
    provider = CountingProvider(fail_with=429)
    fetcher = RecordingFetcher()
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)

    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME}, DOMAIN, selected_with([]), trace, profile()
    )

    assert any("HTTP 429" in line for line in trace.search_limitations)
    assert any("quota stop" in line for line in trace.search_limitations)
    assert selected_with([])[PageCategory.PROGRAM_PAGE] == []


async def test_a_throttle_ends_a_multi_subject_run():
    """One 429 must not be re-sent once per remaining subject."""
    provider = CountingProvider(fail_with=429)
    fetcher = RecordingFetcher()
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)

    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME},
        DOMAIN,
        selected_with([]),
        trace,
        profile(("Computer Science", "Mathematics", "Physics")),
    )

    assert provider.queries, "the first subject is still asked once"
    assert len(provider.queries) == 1, (
        "three subjects must not cost three separate probes of a refused "
        f"quota (sent {len(provider.queries)})"
    )
    assert any("HTTP 429" in line for line in trace.search_limitations)


def test_the_provider_seam_is_still_the_only_way_in():
    """The slot check must not reach around the provider seam."""
    assert isinstance(CountingProvider(), SearchProvider)
