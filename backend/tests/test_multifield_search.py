"""A comma-separated subject profile searches and verifies each bounded subject."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.adapters.search as search_pkg
from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
)
from app.adapters.fetching import Fetcher
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.search.base import SearchUnavailable
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.retrieval import RankedCandidate
from app.api.routes_research import _view
from app.domain.enums import ClaimType, PipelineStage
from app.models import Base
from app.models.research import ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from tests.conftest import profile_row
from tests.test_live_discovery import StubSite, program_html

DOMAIN = "uni.edu"
NAME = "Example University"
MATH_URL = "https://uni.edu/programmes/bsc-mathematics"


@pytest.fixture
def session(settings):
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        yield db


def _query(profile, field: str, index: int = 0) -> str:
    intent = DiscoveryIntent(
        institution=NAME,
        domain=DOMAIN,
        degree=profile.context.level,
        field=field,
    )
    return queries_for(intent)[index].text


def _selected() -> dict[str, list[str]]:
    return {category: [] for category in PageCategory.ALL}


def _selected_ranked() -> dict[str, list[tuple[int, str]]]:
    return {category: [] for category in PageCategory.ALL}


def _candidate() -> Candidate:
    return Candidate(name=NAME, country="Example", city="Example", domain=DOMAIN)


async def _search(
    tmp_path: Path,
    profile,
    monkeypatch,
    corpus,
    pages,
    provider=None,
):
    provider = provider or FakeSearchProvider(corpus)
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: provider)
    site = StubSite(pages)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, registry_path=tmp_path / "missing.json")
        selected = _selected()
        trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
        await adapter._add_search_results({"name": NAME}, DOMAIN, selected, trace, profile)
        candidate = _candidate()
        adapter._apply(candidate, selected, profile, trace)
        claims = []
        if candidate.programs:
            result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
                candidate, candidate.programs[0], "fall 2027"
            )
            claims = result.claims
    return provider, site, selected, trace, candidate, claims


@pytest.mark.asyncio
async def test_second_field_search_yields_verified_programme(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    provider, _site, selected, _trace, candidate, claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {
            _query(profile, "Mathematics"): [(MATH_URL, "BSc Mathematics", "")],
        },
        {MATH_URL: program_html("BSc Mathematics")},
    )

    assert _query(profile, "Mathematics") in [call[0] for call in provider.calls]
    assert len(provider.calls) <= 6
    assert selected[PageCategory.PROGRAM_PAGE] == [MATH_URL]
    assert candidate.programs[0].field == "Mathematics"
    assert any(claim.claim_type == ClaimType.PROGRAM_EXISTS for claim in claims)


@pytest.mark.asyncio
async def test_fetched_subject_overrides_misleading_query_field(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    _provider, _site, _selected_pages, _trace, candidate, claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {
            _query(profile, "Computer Science"): [(MATH_URL, "BSc Computer Science", "")],
        },
        {MATH_URL: program_html("BSc Mathematics")},
    )

    assert candidate.programs[0].field == "Mathematics"
    assert any(claim.claim_type == ClaimType.PROGRAM_EXISTS for claim in claims)


@pytest.mark.asyncio
async def test_unrelated_listing_title_cannot_fill_a_programme_slot(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    physics_url = "https://uni.edu/school"
    _provider, site, selected, _trace, candidate, _claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {
            _query(profile, "Computer Science"): [
                (physics_url, "Bachelor of Science in Physics", "")
            ],
        },
        {
            physics_url: (
                "<html><body><main><h1>Degree programmes</h1>"
                "<p>Bachelor of Science in Physics covers mechanics.</p>"
                "</main></body></html>"
            )
        },
    )

    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert candidate.programs == []


@pytest.mark.asyncio
async def test_official_listing_title_can_confirm_the_second_field(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    listing_url = "https://uni.edu/school"
    _provider, _site, selected, trace, candidate, claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {_query(profile, "Computer Science"): [(listing_url, "BSc Physics", "")]},
        {
            listing_url: (
                "<html><body><main><h1>Degree programmes</h1>"
                "<p>Bachelor of Science in Mathematics covers algebra.</p>"
                "</main></body></html>"
            )
        },
    )

    assert selected[PageCategory.PROGRAM_PAGE] == [listing_url]
    assert candidate.programs[0].field == "Mathematics"
    assert trace.field_sources[listing_url]["basis"] == "full_degree_title_on_listing"
    assert any(claim.claim_type == ClaimType.PROGRAM_EXISTS for claim in claims)


@pytest.mark.asyncio
async def test_one_canonical_url_from_both_fields_is_one_programme(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    _provider, site, selected, _trace, candidate, _claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {
            _query(profile, "Computer Science"): [(MATH_URL, "BSc Mathematics", "")],
            _query(profile, "Mathematics"): [
                (MATH_URL + "?utm_source=provider", "BSc Mathematics", "")
            ],
        },
        {MATH_URL: program_html("BSc Mathematics")},
    )

    assert selected[PageCategory.PROGRAM_PAGE] == [MATH_URL]
    assert len(candidate.programs) == 1
    assert site.requested.count(MATH_URL) == 2  # recovery and requirements, once each


@pytest.mark.asyncio
async def test_first_field_provider_failure_does_not_suppress_second(
    tmp_path, profile, monkeypatch
):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]

    class _OneFieldFailure(FakeSearchProvider):
        async def search(self, *, query, domains=(), max_results=10):
            if "Computer Science" in query:
                self.calls.append((query, tuple(domains), max_results))
                raise SearchUnavailable("one field offline")
            return await super().search(query=query, domains=domains, max_results=max_results)

    provider = _OneFieldFailure(
        {_query(profile, "Mathematics"): [(MATH_URL, "BSc Mathematics", "")]}
    )
    provider, _site, selected, trace, candidate, _claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {},
        {MATH_URL: program_html("BSc Mathematics")},
        provider=provider,
    )

    assert len(provider.calls) == 6
    assert selected[PageCategory.PROGRAM_PAGE] == [MATH_URL]
    assert candidate.programs[0].field == "Mathematics"
    assert trace.search_failures


@pytest.mark.asyncio
async def test_distinct_fields_share_six_queries_and_duplicate_fields_are_one(
    tmp_path, profile, monkeypatch
):
    profile.context.intended_fields = [
        " Computer Science ",
        "computer science",
        "Mathematics",
        "Physics",
    ]
    provider, _site, _selected_pages, _trace, _candidate_row, _claims = await _search(
        tmp_path, profile, monkeypatch, {}, {}
    )

    asked = [call[0] for call in provider.calls]
    assert len(asked) == 6
    assert len(set(asked)) == 6
    assert _query(profile, "Mathematics") in asked
    assert _query(profile, "Physics") in asked


@pytest.mark.asyncio
async def test_two_fields_share_only_three_navigation_roots(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    cs_results = [
        (f"https://cs{n}.uni.edu/programmes/bsc-computer-science", "BSc Computer Science", "")
        for n in range(3)
    ]
    math_results = [
        (f"https://math{n}.uni.edu/programmes/bsc-mathematics", "BSc Mathematics", "")
        for n in range(3)
    ]
    roots = {
        f"https://{prefix}{n}.uni.edu/": "<html><body><nav>Degree programmes</nav></body></html>"
        for prefix in ("cs", "math")
        for n in range(3)
    }
    provider, site, _selected_pages, _trace, _candidate_row, _claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {
            _query(profile, "Computer Science"): cs_results,
            _query(profile, "Mathematics"): math_results,
        },
        roots,
    )

    opened_roots = [url for url in site.requested if url in roots]
    assert len(provider.calls) == 6
    assert len(opened_roots) == 3


@pytest.mark.asyncio
async def test_unrepresented_field_gets_remaining_slot_after_sitemap_pages(
    tmp_path, profile, monkeypatch
):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    cs1 = "https://uni.edu/programmes/bsc-computer-science-one"
    cs2 = "https://uni.edu/programmes/bsc-computer-science-two"
    cs3 = "https://uni.edu/programmes/bsc-computer-science-three"
    provider = FakeSearchProvider(
        {
            _query(profile, "Computer Science"): [(cs3, "BSc Computer Science", "")],
            _query(profile, "Mathematics"): [(MATH_URL, "BSc Mathematics", "")],
        }
    )
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: provider)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        StubSite({cs3: program_html(), MATH_URL: program_html("BSc Mathematics")}).install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, registry_path=tmp_path / "missing.json")
        selected = _selected()
        selected[PageCategory.PROGRAM_PAGE] = [cs1, cs2]
        trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
        for url in (cs1, cs2):
            trace.field_sources[url] = {
                "field": "Computer Science",
                "source_url": url,
                "subject": "BSc Computer Science",
                "basis": "classified_programme_page",
            }
        await adapter._add_search_results({"name": NAME}, DOMAIN, selected, trace, profile)
        candidate = _candidate()
        adapter._apply(candidate, selected, profile, trace)

    assert selected[PageCategory.PROGRAM_PAGE] == [cs1, cs2, MATH_URL]
    assert [program.field for program in candidate.programs] == [
        "Computer Science",
        "Computer Science",
        "Mathematics",
    ]
    assert trace.search_coverage["represented"] == 2


@pytest.mark.asyncio
async def test_catalogue_followups_cannot_hide_another_fields_direct_page(tmp_path, profile):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    listing_url = "https://uni.edu/programmes"
    cs_urls = [f"https://uni.edu/programmes/bsc-computer-science-{n}" for n in range(8)]
    links = "".join(f"<a href='{url}'>Computer Science</a>" for url in cs_urls)
    site = StubSite(
        {
            listing_url: (
                "<html><head><title>All bachelor programmes</title></head>"
                "<body><main><h1>Bachelor programmes</h1>"
                "<p>Browse the university's bachelor degree programmes.</p>"
                f"<ul>{links}</ul></main></body></html>"
            ),
            **{url: program_html() for url in cs_urls},
            MATH_URL: program_html("BSc Mathematics"),
        }
    )
    selected = []
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    leads = [
        RankedCandidate(listing_url, "Degree programmes", 1, "fake"),
        RankedCandidate(MATH_URL, "BSc Mathematics", 1, "fake"),
    ]
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(leads, selected, trace, profile)

    assert any(url in site.requested for url in cs_urls), (
        site.requested,
        selected,
        trace.rejected,
    )
    assert MATH_URL in selected


@pytest.mark.asyncio
async def test_unsafe_field_is_redacted_and_does_not_hide_safe_field(
    tmp_path, profile, monkeypatch
):
    profile.context.intended_fields = ["student@example.com", "Mathematics"]
    provider, _site, selected, trace, candidate, _claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {_query(profile, "Mathematics"): [(MATH_URL, "BSc Mathematics", "")]},
        {MATH_URL: program_html("BSc Mathematics")},
    )

    assert _query(profile, "Mathematics") in [call[0] for call in provider.calls]
    assert all("student@example.com" not in str(call) for call in provider.calls)
    assert "student@example.com" not in str(trace.as_dict())
    assert selected[PageCategory.PROGRAM_PAGE] == [MATH_URL]
    assert candidate.programs[0].field == "Mathematics"


@pytest.mark.asyncio
async def test_rejected_subject_cannot_be_attributed_or_verified_from_cross_field_result(
    tmp_path, profile, monkeypatch
):
    rejected = "Computer Science 123456"
    cs_url = "https://uni.edu/programmes/bsc-computer-science"
    profile.context.intended_fields = [rejected, "Mathematics"]
    _provider, _site, selected, trace, candidate, claims = await _search(
        tmp_path,
        profile,
        monkeypatch,
        {
            _query(profile, "Mathematics"): [
                (cs_url, "BSc Computer Science", ""),
                (MATH_URL, "BSc Mathematics", ""),
            ],
        },
        {
            cs_url: program_html("BSc Computer Science"),
            MATH_URL: program_html("BSc Mathematics"),
        },
    )

    assert selected[PageCategory.PROGRAM_PAGE] == [MATH_URL]
    assert [program.field for program in candidate.programs] == ["Mathematics"]
    assert rejected not in str(trace.as_dict())
    assert any(claim.claim_type == ClaimType.PROGRAM_EXISTS for claim in claims)


@pytest.mark.asyncio
async def test_rejected_subject_is_redacted_on_existing_sitemap_confirmation(tmp_path, profile):
    rejected = "Computer Science 123456"
    cs_url = "https://uni.edu/programmes/bsc-computer-science"
    profile.context.intended_fields = [rejected, "Mathematics"]
    site = StubSite({cs_url: program_html("BSc Computer Science")})
    selected = _selected()
    selected[PageCategory.PROGRAM_PAGE] = [cs_url]
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher)
        await adapter._confirm_programs(selected, _selected_ranked(), trace, profile)
        candidate = _candidate()
        adapter._apply(candidate, selected, profile, trace)

    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert candidate.programs == []
    assert rejected not in str(trace.as_dict())


@pytest.mark.asyncio
async def test_safe_sitemap_subject_has_source_attribution_after_another_field_is_rejected(
    tmp_path, profile
):
    profile.context.intended_fields = ["Computer Science 123456", "Mathematics"]
    selected = _selected()
    selected[PageCategory.PROGRAM_PAGE] = [MATH_URL]
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        StubSite({MATH_URL: program_html("BSc Mathematics")}).install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher)
        await adapter._confirm_programs(selected, _selected_ranked(), trace, profile)
        candidate = _candidate()
        adapter._apply(candidate, selected, profile, trace)

    assert selected[PageCategory.PROGRAM_PAGE] == [MATH_URL]
    assert trace.field_sources[MATH_URL]["field"] == "Mathematics"
    assert candidate.programs[0].field == "Mathematics"


def test_unreadable_root_programme_name_cannot_echo_rejected_subject(tmp_path, profile):
    rejected = "Computer Science 123456"
    profile.context.intended_fields = [rejected, "Mathematics"]
    selected = _selected()
    selected[PageCategory.PROGRAM_PAGE] = ["https://uni.edu/123"]
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    candidate = _candidate()

    LiveDiscoveryAdapter(Fetcher(tmp_path / "cache", offline=True))._apply(
        candidate, selected, profile, trace
    )

    assert rejected not in str(candidate.programs)
    assert candidate.programs[0].field == "Mathematics"


@pytest.mark.asyncio
async def test_public_field_remains_matchable_when_institution_domain_is_not_query_safe(
    tmp_path, profile
):
    profile.context.intended_fields = ["Mathematics"]
    url = "https://uni2027.edu/programmes/bsc-mathematics"
    site = StubSite({url: program_html("BSc Mathematics")})
    selected = _selected()
    selected[PageCategory.PROGRAM_PAGE] = [url]
    trace = DiscoveryTrace(institution="University 2027", domain="uni2027.edu")
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher)
        await adapter._confirm_programs(selected, _selected_ranked(), trace, profile)
        candidate = _candidate()
        adapter._apply(candidate, selected, profile, trace)

    assert selected[PageCategory.PROGRAM_PAGE] == [url]
    assert candidate.programs[0].field == "Mathematics"


@pytest.mark.asyncio
async def test_one_subject_keeps_the_existing_six_query_order(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = ["Computer Science"]
    provider, _site, _selected_pages, trace, _candidate_row, _claims = await _search(
        tmp_path, profile, monkeypatch, {}, {}
    )

    assert [call[0] for call in provider.calls] == [
        query.text
        for query in queries_for(
            DiscoveryIntent(
                institution=NAME,
                domain=DOMAIN,
                degree=profile.context.level,
                field="Computer Science",
            )
        )
    ]
    assert not trace.search_limitations


@pytest.mark.asyncio
async def test_duplicate_spellings_of_one_subject_keep_single_field_search_path(
    tmp_path, profile, monkeypatch
):
    profile.context.intended_fields = ["Computer Science", " computer science "]
    provider, _site, _selected_pages, trace, _candidate_row, _claims = await _search(
        tmp_path, profile, monkeypatch, {}, {}
    )

    assert [call[0] for call in provider.calls] == [
        query.text
        for query in queries_for(
            DiscoveryIntent(
                institution=NAME,
                domain=DOMAIN,
                degree=profile.context.level,
                field="Computer Science",
            )
        )
    ]
    assert trace.search_coverage == {}


@pytest.mark.asyncio
async def test_eight_fields_report_six_queried_and_three_slot_limit(tmp_path, profile, monkeypatch):
    profile.context.intended_fields = [
        "Mathematics",
        "Physics",
        "Chemistry",
        "Biology",
        "Economics",
        "History",
        "Geography",
        "Linguistics",
    ]
    provider, _site, _selected_pages, trace, _candidate_row, _claims = await _search(
        tmp_path, profile, monkeypatch, {}, {}
    )

    assert len(provider.calls) == 6
    assert _query(profile, "Geography") not in [call[0] for call in provider.calls]
    assert any("6 of 8" in message for message in trace.search_limitations)
    assert any("3 programmes" in message for message in trace.search_limitations)
    assert all("SearchUnavailable" not in message for message in trace.search_limitations)


@pytest.mark.asyncio
async def test_unqueried_sitemap_subject_does_not_count_as_queried_search_coverage(
    tmp_path, profile, monkeypatch
):
    profile.context.intended_fields = [
        "Mathematics",
        "Physics",
        "Chemistry",
        "Biology",
        "Economics",
        "History",
        "Geography",
    ]
    geography_url = "https://uni.edu/programmes/bsc-geography"
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: FakeSearchProvider({}))
    selected = _selected()
    selected[PageCategory.PROGRAM_PAGE] = [geography_url]
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        StubSite({geography_url: program_html("BSc Geography")}).install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher)
        await adapter._confirm_programs(selected, _selected_ranked(), trace, profile)
        await adapter._add_search_results({"name": NAME}, DOMAIN, selected, trace, profile)
        candidate = _candidate()
        adapter._apply(candidate, selected, profile, trace)

    assert selected[PageCategory.PROGRAM_PAGE] == [geography_url]
    assert candidate.programs[0].field == "Geography"
    assert trace.search_coverage == {"requested": 7, "queried": 6, "represented": 0}


@pytest.mark.asyncio
async def test_budget_limitation_reaches_the_existing_run_api_contract(
    tmp_path, profile, monkeypatch, session, settings
):
    profile.context.intended_fields = [
        "Mathematics",
        "Physics",
        "Chemistry",
        "Biology",
        "Economics",
        "History",
        "Geography",
        "Linguistics",
    ]
    provider = FakeSearchProvider({})
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: provider)
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps([{"name": NAME, "country": "Example", "homepage": "https://uni.edu/"}])
    )
    row = profile_row(session, profile)
    run = ResearchRun(
        profile_id=row.id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=False,
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    runner = ResearchRunner(session, run, profile, settings)
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        StubSite({}).install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, registry_path=registry)
        monkeypatch.setattr(runner, "_make_discovery_adapter", lambda _: adapter)
        await runner._stage_discover(fetcher)

    session.expire_all()
    saved = session.get(ResearchRun, run.id)
    assert saved is not None
    view = _view(session, saved, counts=(0, 0))
    assert len(provider.calls) == 6
    assert any("6 of 8" in message for message in view.errors)
    assert any("3 programmes" in message for message in view.errors)
    assert view.unknowns == []
    assert all("SearchUnavailable" not in message for message in view.errors)
