"""The site-identity fallback query counts in the institution's six-query budget.

A seed row with no domain (utokyo, ntutw, auckland) asked the search provider
once for its official website, and discovery then sent its full share of six,
so the case sent seven (paired run 39113844090). The identity query is the
institution's too: discovery now gets one fewer, and a row whose own host
answers is unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import FetchResult
from app.adapters.search import intent as intent_module
from app.adapters.search.base import SearchResponse, SearchResult
from app.adapters.search.intent import DEFAULT_QUERY_BUDGET
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.catalogue.importer import import_catalogue
from app.db import create_all_for_tests
from app.models import University
from app.schemas.profile import ApplicantProfileIn
from tests.test_site_identity_v2 import Fetcher, page, university, without_domain

HOME = "https://www.auckland.ac.nz/"
FINAL = "https://www.auckland.ac.nz/en.html"


def profile() -> ApplicantProfileIn:
    return ApplicantProfileIn.model_validate(
        {
            "context": {
                "level": "bachelor",
                "intended_fields": ["Computer Science"],
                "intake_year": 2027,
                "citizenship": "KZ",
                "country_of_residence": "KZ",
                "education_country": "KZ",
                "education_system": "KZ",
            }
        }
    )


class Provider:
    """One provider for identity and discovery; answers with the homepage, counts queries."""

    name = "fake"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.queries.append(query)
        now = datetime.now(UTC)
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=now,
            results=(
                SearchResult(url=HOME, title="Home", provider=self.name, rank=1, retrieved_at=now),
            ),
        )


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as db:
        import_catalogue(db)
        db.commit()
        yield db
    engine.dispose()


@pytest.fixture
def gate(monkeypatch):
    from app.catalogue import discovery

    monkeypatch.setattr(discovery, "SITE_IDENTITY_V2", True)
    monkeypatch.setattr(intent_module, "SHARED_QUERY_BUDGET", True)
    monkeypatch.setattr(intent_module, "DISCOVERY_QUERY_RESERVE", True)
    provider = Provider()
    monkeypatch.setattr(discovery, "get_search_provider", lambda: provider)
    return provider


async def enrich(
    session, provider: Provider, uni: University, pages: dict[str, FetchResult]
) -> tuple[Candidate, DiscoveryTrace]:
    fetcher = Fetcher(pages)
    adapter = CatalogueDiscoveryAdapter(
        fetcher, session=session, university_ids=[uni.id], live_limit=1
    )
    adapter._search_provider = provider  # type: ignore[assignment]
    adapter._search_provider_resolved = True
    candidate = Candidate(name=uni.name, country=uni.country, city=uni.city)
    trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
    return await adapter._enrich(uni, profile(), candidate, trace)


async def test_a_row_with_no_domain_sends_six_queries_in_all(session, gate):
    uni = without_domain(university(session, "auckland"))
    pages = {HOME: page(HOME, "auckland_home.html", final=FINAL)}
    candidate, trace = await enrich(session, gate, uni, pages)

    assert HOME in candidate.discovery_source
    assert "official university website" in gate.queries[0]
    assert len(gate.queries) <= DEFAULT_QUERY_BUDGET
    # Both discovery passes ran (nothing was confirmed), on one query fewer.
    assert trace.discovery_query_passes == [3, 2]
    assert trace.search_queries_sent == len(gate.queries) == DEFAULT_QUERY_BUDGET
    # The later stages see the budget as spent, identity query included.
    assert candidate.search_queries_used == DEFAULT_QUERY_BUDGET


async def test_a_row_with_a_domain_is_unchanged(session, gate):
    uni = university(session, "ucph")
    assert uni.domain
    url = f"https://{uni.domain}/"
    candidate, trace = await enrich(session, gate, uni, {url: page(url, "ucph_home.html")})

    assert not any("official university website" in query for query in gate.queries)
    assert trace.discovery_query_passes == [3, 3]
    assert trace.search_queries_sent == len(gate.queries) == DEFAULT_QUERY_BUDGET
    assert candidate.search_queries_used == DEFAULT_QUERY_BUDGET


async def test_a_retained_row_carries_the_identity_query(session, gate, monkeypatch):
    """No identity established: the one query sent is still on the candidate's ledger."""
    uni = without_domain(university(session, "auckland"))
    fetcher = Fetcher({})
    adapter = CatalogueDiscoveryAdapter(
        fetcher, session=session, university_ids=[uni.id], live_limit=1
    )
    candidate = Candidate(name=uni.name, country=uni.country, city=uni.city)
    trace = DiscoveryTrace(institution=uni.name, domain="")
    candidate, trace = await adapter._enrich(uni, profile(), candidate, trace)

    assert len(gate.queries) == 1
    assert candidate.search_queries_used == trace.search_queries_sent == 1
