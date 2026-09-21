"""V2-10 — the search provider seam.

These tests are mostly about what a provider may *not* do. The retrieval
itself is later work; what has to hold from day one is that no vendor leaks
upwards, no search result is mistaken for evidence, and no deployment can end
up searching without anyone having decided to.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.search import (
    KNOWN_SEARCH_PROVIDERS,
    SearchProvider,
    SearchProviderNotConfigured,
    SearchResponse,
    SearchResult,
    SearchUnavailable,
    get_search_provider,
)
from app.adapters.search.fake import FakeSearchProvider
from app.config import Settings

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def a_result(**kw) -> SearchResult:
    return SearchResult(
        **{
            "url": "https://nu.edu.kz/programmes/cs",
            "title": "Computer Science",
            "provider": "fake",
            "rank": 1,
            "retrieved_at": NOW,
            **kw,
        }
    )


class TestTheFakeAnswersOnlyFromItsCorpus:
    async def test_it_returns_what_it_was_given_in_the_order_it_was_given(self):
        provider = FakeSearchProvider(
            {"bsc computer science nu.edu.kz": ["https://nu.edu.kz/cs", "https://nu.edu.kz/seds"]},
            now=NOW,
        )

        response = await provider.search(query="bsc computer science nu.edu.kz")

        assert [r.url for r in response.results] == [
            "https://nu.edu.kz/cs",
            "https://nu.edu.kz/seds",
        ]
        assert [r.rank for r in response.results] == [1, 2]
        assert all(r.provider == "fake" for r in response.results)
        assert all(r.retrieved_at == NOW for r in response.results)

    async def test_an_unknown_query_finds_nothing_rather_than_something_plausible(self):
        """A fake that guessed URLs would let retrieval look built before it is."""
        provider = FakeSearchProvider({"known": ["https://nu.edu.kz/cs"]}, now=NOW)

        response = await provider.search(query="never seen")

        assert len(response) == 0
        assert response.query == "never seen"

    async def test_it_is_deterministic(self):
        provider = FakeSearchProvider({"q": ["https://a.test/1", "https://b.test/2"]}, now=NOW)

        first = await provider.search(query="q")
        second = await provider.search(query="q")

        assert first == second

    async def test_max_results_truncates_from_the_top_and_must_be_positive(self):
        provider = FakeSearchProvider({"q": [f"https://a.test/{i}" for i in range(5)]}, now=NOW)

        response = await provider.search(query="q", max_results=2)

        assert [r.url for r in response.results] == ["https://a.test/0", "https://a.test/1"]
        with pytest.raises(ValueError, match="max_results"):
            await provider.search(query="q", max_results=0)


class TestDomainRestrictionIsHonouredNotApproximated:
    async def test_a_domain_matches_itself_and_its_subdomains(self):
        provider = FakeSearchProvider(
            {"q": ["https://nu.edu.kz/a", "https://admissions.nu.edu.kz/b"]}, now=NOW
        )

        response = await provider.search(query="q", domains=["nu.edu.kz"])

        assert len(response) == 2

    async def test_a_lookalike_domain_is_not_the_domain(self):
        """``notnu.edu.kz`` ends with the same characters and is a different owner."""
        provider = FakeSearchProvider(
            {
                "q": [
                    "https://notnu.edu.kz/a",
                    "https://nu.edu.kz.evil.test/b",
                    "https://nu.edu.kz/c",
                ]
            },
            now=NOW,
        )

        response = await provider.search(query="q", domains=["nu.edu.kz"])

        assert [r.url for r in response.results] == ["https://nu.edu.kz/c"]

    async def test_ranks_are_renumbered_after_filtering_so_there_is_no_gap(self):
        provider = FakeSearchProvider(
            {"q": ["https://other.test/a", "https://nu.edu.kz/b"]}, now=NOW
        )

        response = await provider.search(query="q", domains=["nu.edu.kz"])

        assert [r.rank for r in response.results] == [1]


class TestAResultCarriesItsOwnProvenance:
    def test_a_result_without_a_url_or_a_provider_is_not_a_result(self):
        with pytest.raises(ValueError, match="URL"):
            a_result(url="")
        with pytest.raises(ValueError, match="provider"):
            a_result(provider="")

    def test_rank_is_one_based(self):
        with pytest.raises(ValueError, match="1-based"):
            a_result(rank=0)

    def test_a_response_may_not_carry_another_providers_results(self):
        """Fusing providers is V2-16 and needs its own provenance, not a mixed bag."""
        with pytest.raises(ValueError, match="brave"):
            SearchResponse(
                query="q",
                provider="fake",
                retrieved_at=NOW,
                results=(a_result(provider="brave"),),
            )

    def test_a_response_must_be_ordered_and_unambiguous(self):
        with pytest.raises(ValueError, match="rank"):
            SearchResponse(
                query="q",
                provider="fake",
                retrieved_at=NOW,
                results=(a_result(rank=2), a_result(rank=1)),
            )
        with pytest.raises(ValueError, match="share a rank"):
            SearchResponse(
                query="q",
                provider="fake",
                retrieved_at=NOW,
                results=(a_result(rank=1), a_result(rank=1)),
            )


class TestASearchResultIsAHintAndNeverEvidence:
    def test_it_carries_nothing_a_claim_could_be_built_from(self):
        """A snippet is a vendor's summary of a page nobody here has read.

        The moment a result grows a value, a scope or an excerpt-of-record,
        somebody will cite one instead of fetching the page, and the corpus
        will contain facts whose source is a search engine.
        """
        forbidden = {"value", "scope", "excerpt", "claim", "evidence", "verified", "status"}

        assert not forbidden & set(SearchResult.__dataclass_fields__)

    def test_the_domain_layer_may_not_import_the_search_package(self):
        """The seam is only a seam while nothing under app/domain reaches through it."""
        domain = Path(__file__).resolve().parents[1] / "app/domain"
        offenders = []
        for path in domain.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                    "app.adapters"
                ):
                    offenders.append(f"{path.name}: {node.module}")
                elif isinstance(node, ast.Import):
                    offenders += [
                        f"{path.name}: {n.name}"
                        for n in node.names
                        if n.name.startswith("app.adapters")
                    ]

        assert offenders == []


class TestNobodySearchesByAccident:
    def test_no_provider_is_configured_by_default(self):
        assert Settings().search_provider == "none"

    def test_asking_for_a_provider_when_there_is_none_raises(self, monkeypatch):
        from app.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
        try:
            with pytest.raises(SearchProviderNotConfigured, match="no web search layer"):
                get_search_provider()
        finally:
            get_settings.cache_clear()

    def test_configuring_the_fake_yields_the_fake_and_nothing_else(self, monkeypatch):
        from app.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "fake")
        try:
            provider = get_search_provider()
            assert isinstance(provider, FakeSearchProvider)
            assert provider.name == "fake"
        finally:
            get_settings.cache_clear()

    def test_a_typo_is_refused_at_startup_not_at_the_first_search(self):
        settings = Settings(search_provider="brave")
        with pytest.raises(RuntimeError, match="not a search provider"):
            settings.validate_runtime()

    def test_production_refuses_the_fake(self):
        settings = Settings(search_provider="fake", environment="production")
        with pytest.raises(RuntimeError, match="must not be 'fake' in production"):
            settings._validate_search()

    def test_every_known_name_is_one_this_build_can_actually_build(self):
        assert set(KNOWN_SEARCH_PROVIDERS) == {"none", "fake", "exa"}


class TestTheContractItself:
    def test_the_fake_satisfies_the_protocol(self):
        assert isinstance(FakeSearchProvider(), SearchProvider)

    async def test_a_provider_that_cannot_answer_raises_rather_than_reporting_nothing(self):
        """Degraded retrieval and empty retrieval are different facts."""
        provider = FakeSearchProvider({"q": ["https://a.test/1"]}, fail_with="quota exhausted")

        with pytest.raises(SearchUnavailable, match="quota"):
            await provider.search(query="q")

    async def test_the_query_is_the_only_thing_a_provider_is_told(self):
        """No overload takes a profile, so applicant data cannot structurally reach a vendor."""
        import inspect

        params = inspect.signature(FakeSearchProvider().search).parameters

        assert set(params) == {"query", "domains", "max_results"}
        assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())
