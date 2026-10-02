"""Admission navigation is evidence work, not a programme identity shortcut."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, PageCategory
from app.adapters.extraction import ClaimBuilder, extract_admission_route
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome, SourceSpecificity
from scripts.canary_discovery import canary_profile
from tests.test_live_discovery import StubSite

ROOT = "https://dept.example.edu/catalogue"
ROUTE = "https://dept.example.edu/route"
NAV = f'''<a href="{ROUTE}">Undergraduate admission</a>
<a href="https://external.example/route">Undergraduate admission</a>
<a href="/people/admissions">Undergraduate admissions staff</a>
<a href="/graduate">Graduate admission</a>
<a href="/greeting">Dean's greeting</a>'''


@pytest.mark.asyncio
async def test_admission_route_is_retained_without_becoming_a_programme(settings):
    f = StubSite({ROOT: NAV}).install(Fetcher(settings.cache_dir, offline=True))
    adapter = LiveDiscoveryAdapter(f)
    selected = {category: [] for category in PageCategory.ALL}
    selected[PageCategory.PROGRAM_CATALOG] = [ROOT]
    trace = DiscoveryTrace(institution="Example", domain="example.edu")
    await adapter._add_admission_obligations(selected, trace, canary_profile())
    assert selected[PageCategory.ADMISSIONS] == [ROUTE]
    assert selected[PageCategory.PROGRAM_PAGE] == []


@pytest.mark.asyncio
async def test_route_page_produces_its_own_fact_not_a_programme_claim(settings):
    html = "<p>Undergraduate students are admitted without a declared major.</p>"
    site = StubSite({ROOT: "<h1>Welcome</h1>", ROUTE: html})
    f = site.install(Fetcher(settings.cache_dir, offline=True))
    candidate = Candidate(
        name="Example",
        country="Canada",
        city="",
        domain="example.edu",
        admissions_url=ROOT,
        admissions_urls=[ROOT, ROUTE, ROUTE],
    )
    result = await WebRequirementsAdapter(f, "2027/28").verify(
        candidate,
        CandidateProgram("Computer Science", "computer science", DegreeLevel.BACHELOR),
        "fall 2027",
    )
    assert site.requested == [ROOT, ROUTE]
    assert [c.claim_type for c in result.claims] == [ClaimType.ADMISSION_ROUTE]
    assert result.claims[0].source_url == ROUTE
    assert "without a declared major" in result.claims[0].original_text_excerpt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome,final_url",
    [
        (FetchOutcome.BLOCKED, ROOT),
        (FetchOutcome.OK, "https://external.example/catalogue"),
    ],
)
async def test_refused_or_redirected_catalogue_cannot_supply_routes(settings, outcome, final_url):
    f = Fetcher(settings.cache_dir, offline=True)
    f.get = AsyncMock(
        return_value=FetchResult(url=ROOT, outcome=outcome, final_url=final_url, text=NAV)
    )
    selected = {category: [] for category in PageCategory.ALL}
    selected[PageCategory.PROGRAM_CATALOG] = [ROOT]
    await LiveDiscoveryAdapter(f)._add_admission_obligations(
        selected, DiscoveryTrace(institution="Example", domain="example.edu"), canary_profile()
    )
    assert not selected[PageCategory.ADMISSIONS]


@pytest.mark.asyncio
async def test_additional_admission_reads_are_bounded_and_external_leads_are_ignored(settings):
    site = StubSite({ROOT: "Welcome", ROUTE: "No facts"})
    f = site.install(Fetcher(settings.cache_dir, offline=True))
    candidate = Candidate(
        name="Example",
        country="Canada",
        city="",
        domain="example.edu",
        admissions_url=ROOT,
        admissions_urls=[ROOT, "https://external.example/route", ROUTE, ROUTE + "-over-budget"],
    )
    result = await WebRequirementsAdapter(f, "2027/28").verify(
        candidate,
        CandidateProgram("Computer Science", "computer science", DegreeLevel.BACHELOR),
        "fall 2027",
    )
    assert site.requested == [ROOT, ROUTE]
    assert not result.claims


@pytest.mark.asyncio
async def test_existing_admission_slots_and_masters_requests_are_preserved(settings):
    site = StubSite({ROOT: NAV})
    f = site.install(Fetcher(settings.cache_dir, offline=True))
    adapter = LiveDiscoveryAdapter(f)
    selected = {category: [] for category in PageCategory.ALL}
    selected[PageCategory.PROGRAM_CATALOG] = [ROOT]
    selected[PageCategory.ADMISSIONS] = [ROOT + str(i) for i in range(3)]
    profile = canary_profile()
    await adapter._add_admission_obligations(
        selected, DiscoveryTrace(institution="Example", domain="example.edu"), profile
    )
    assert not site.requested
    selected[PageCategory.ADMISSIONS] = []
    profile.context.level = DegreeLevel.MASTER
    await adapter._add_admission_obligations(
        selected, DiscoveryTrace(institution="Example", domain="example.edu"), profile
    )
    assert not site.requested


@pytest.mark.parametrize(
    "sentence,degree",
    [
        ("KAIST 학부생은 전공선택 없이 무학과로 입학을 하고 있습니다.", "bachelor"),
        ("다른 대학 학부생은 무학과로 입학을 합니다.", "bachelor"),
        ("전산학부 안내: 무학과로 입학을 합니다.", None),
        ("학부생 및 대학원생은 무학과로 입학을 합니다.", None),
        ("Undergraduate students are admitted without a declared major.", "bachelor"),
        ("Undergraduate and graduate students are admitted without a declared major.", None),
    ],
)
def test_admission_degree_comes_from_quoted_students_not_department_or_request(sentence, degree):
    builder = ClaimBuilder(
        source_url=ROUTE,
        page_title="Admissions",
        specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
        program="Computer Science",
        intake="fall 2027",
        academic_year="2027/28",
        official_domain=True,
        scope=ClaimScope(),
        page_text=sentence,
        allowed_domains=["example.edu"],
    )
    claim = extract_admission_route(sentence, builder)
    assert claim is not None
    assert claim.scope is not None
    assert claim.scope.degree == degree
