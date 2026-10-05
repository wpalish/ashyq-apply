"""A redirect destination cannot supply evidence under the requested site's URL."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
    same_institution,
)
from app.adapters.discovery.live_discovery import (
    registrable_domain as discovery_domain,
)
from app.adapters.extraction import is_official_domain
from app.adapters.fetching import Fetcher, FetchResult, same_source_site
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.search.retrieval import RankedCandidate
from app.domain.claim_verifier import registrable_domain as claim_domain
from app.domain.claim_verifier import url_matches_domains
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome
from tests.test_browser_network import FakePage, FakePlaywrightResponse, browser_with
from tests.test_fetch_pii_hops import allow_all
from tests.test_live_discovery import StubSite, program_html

SOURCE = "https://uni.edu/programmes/bsc-mathematics"
FOREIGN = "https://unrelated.example/programmes/bsc-mathematics"
SAME_SITE = "https://catalog.uni.edu/programmes/bsc-mathematics"
WRONG_LEVEL = "https://uni.edu/programmes/msc-mathematics"


def test_distinct_public_ips_are_distinct_sources():
    assert not same_source_site("https://93.184.216.34/page", "https://1.2.216.34/page")
    assert same_source_site("https://93.184.216.34/page", "https://93.184.216.34/new")


def test_unicode_hostname_uses_the_same_idna_rules_as_httpx():
    assert not same_source_site("https://straße.de/x", "https://strasse.de/y")
    assert same_source_site("https://straße.de/x", "https://xn--strae-oqa.de/y")


def test_malformed_url_is_not_a_same_site_or_institution():
    assert not same_source_site("https://uni.edu/", "https://[bad")
    assert not same_institution("https://[bad", "uni.edu")


@pytest.mark.parametrize("shared_suffix", ["github.io", "pages.dev"])
def test_distinct_shared_hosting_tenants_are_distinct_sources(shared_suffix):
    assert not same_source_site(
        f"https://university.{shared_suffix}/page",
        f"https://attacker.{shared_suffix}/page",
    )
    assert same_source_site(
        f"https://www.university.{shared_suffix}/page",
        f"https://catalog.university.{shared_suffix}/page",
    )


@pytest.mark.parametrize("shared_suffix", ["github.io", "pages.dev"])
def test_direct_foreign_tenant_url_cannot_be_an_official_source(shared_suffix):
    allowed = f"university.{shared_suffix}"
    foreign = f"https://attacker.{shared_suffix}/programmes/bsc-mathematics"
    own = f"https://catalog.{allowed}/programmes/bsc-mathematics"
    assert discovery_domain(own) == allowed
    assert claim_domain(allowed) == allowed
    assert not same_institution(foreign, allowed)
    assert not url_matches_domains(foreign, [allowed])
    assert not is_official_domain(foreign, [allowed])
    assert same_institution(own, allowed)
    assert url_matches_domains(own, [allowed])


@pytest.mark.asyncio
async def test_cross_site_http_redirect_cannot_create_an_official_programme_claim(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    fetched: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"].split(":")[0]
        fetched.append(host)
        if host == "uni.edu":
            return httpx.Response(302, headers={"location": FOREIGN})
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text=program_html("BSc Mathematics")
        )

    candidate = Candidate(
        name="Example University", country="Example", city="Example", domain="uni.edu"
    )
    program = CandidateProgram(
        name="BSc Mathematics", field="Mathematics", degree=DegreeLevel.BACHELOR, url=SOURCE
    )
    async with Fetcher(tmp_path / "cache", delay_seconds=0, respect_robots=False) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        fetched_page = await fetcher.get(SOURCE)
        result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
            candidate, program, "fall 2027"
        )

    assert fetched_page.outcome is FetchOutcome.BLOCKED
    assert fetched == ["uni.edu", "uni.edu"]
    assert result.claims == []


@pytest.mark.asyncio
async def test_same_site_subdomain_redirect_can_still_be_read(tmp_path, monkeypatch):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"].split(":")[0]
        if host == "uni.edu":
            return httpx.Response(302, headers={"location": SAME_SITE})
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text=program_html("BSc Mathematics")
        )

    async with Fetcher(tmp_path / "cache", delay_seconds=0, respect_robots=False) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        result = await fetcher.get(SOURCE)

    assert result.ok
    assert result.final_url == SAME_SITE


@pytest.mark.asyncio
@pytest.mark.parametrize("destination", [SOURCE.replace("bsc", "private-bsc"), SAME_SITE])
async def test_redirect_target_obeys_its_own_robots_rule_before_get(
    tmp_path, monkeypatch, destination
):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    fetched: list[str] = []
    checked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        fetched.append(request.headers["host"] + request.url.path)
        if (
            request.headers["host"] == "uni.edu"
            and request.url.path == "/programmes/bsc-mathematics"
        ):
            return httpx.Response(302, headers={"location": destination})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="private")

    async with Fetcher(tmp_path / "cache", delay_seconds=0) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )

        async def allowed(url, _client):
            checked.append(url)
            return (url != destination, "robots.txt disallows this path")

        fetcher.robots.allowed = allowed  # type: ignore[method-assign]
        result = await fetcher.get(SOURCE)

    assert checked == [SOURCE, destination]
    assert fetched == ["uni.edu/programmes/bsc-mathematics"]
    assert result.outcome is FetchOutcome.ROBOTS_DISALLOWED


@pytest.mark.asyncio
async def test_redirect_target_is_spaced_by_its_own_host(tmp_path, monkeypatch):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    spaced: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["host"] == "uni.edu":
            return httpx.Response(302, headers={"location": SAME_SITE})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="program")

    async with Fetcher(tmp_path / "cache", delay_seconds=0, respect_robots=False) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )

        async def spaced_request(host, url):
            spaced.append((host, url))

        fetcher._space_requests = spaced_request  # type: ignore[method-assign]
        result = await fetcher.get(SOURCE)

    assert result.ok
    assert spaced == [("uni.edu", SOURCE), ("catalog.uni.edu", SAME_SITE)]


@pytest.mark.asyncio
async def test_polite_redirect_delays_do_not_consume_network_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["host"] == "uni.edu":
            return httpx.Response(302, headers={"location": SAME_SITE})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="programme")

    async with Fetcher(
        tmp_path / "cache", delay_seconds=0, respect_robots=False, timeout=0.05
    ) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )

        async def polite_delay(_host, _url):
            await asyncio.sleep(0.035)

        fetcher._space_requests = polite_delay  # type: ignore[method-assign]
        result = await fetcher.get(SOURCE)

    assert result.ok
    assert result.final_url == SAME_SITE


@pytest.mark.asyncio
async def test_reciprocal_subdomain_redirects_do_not_deadlock_host_limits(tmp_path, monkeypatch):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"]
        if request.url.path == "/start":
            other = "b.uni.edu" if host == "a.uni.edu" else "a.uni.edu"
            return httpx.Response(302, headers={"location": f"https://{other}/final"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="programme")

    async with Fetcher(tmp_path / "cache", delay_seconds=0, respect_robots=False) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        urls = ["https://a.uni.edu/start", "https://b.uni.edu/start"] * 2
        results = await asyncio.wait_for(
            asyncio.gather(*(fetcher.get(url, use_cache=False) for url in urls)), timeout=2
        )

    assert all(result.ok for result in results)


@pytest.mark.asyncio
async def test_same_site_redirect_to_master_cannot_confirm_a_bachelor_programme(
    tmp_path, monkeypatch, profile
):
    monkeypatch.setattr("app.adapters.fetching.check_url", allow_all)
    html = (
        "<html><head><title>Mathematics | Example University</title></head>"
        "<body><h1>Mathematics</h1><p>This programme is offered by Example University. "
        "IELTS overall 6.5.</p></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/programmes/bsc"):
            return httpx.Response(302, headers={"location": WRONG_LEVEL})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html)

    profile.context.intended_fields = ["Mathematics"]
    profile.context.level = "bachelor"
    candidate = Candidate(
        name="Example University", country="Example", city="Example", domain="uni.edu"
    )
    program = CandidateProgram(
        name="BSc Mathematics", field="Mathematics", degree=DegreeLevel.BACHELOR, url=SOURCE
    )
    async with Fetcher(tmp_path / "cache", delay_seconds=0, respect_robots=False) as fetcher:
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )
        selected = {category: [] for category in PageCategory.ALL}
        selected[PageCategory.PROGRAM_PAGE] = [SOURCE]
        ranked = {category: [] for category in PageCategory.ALL}
        trace = DiscoveryTrace(institution="Example University", domain="uni.edu")
        await LiveDiscoveryAdapter(fetcher)._confirm_programs(selected, ranked, trace, profile)
        verified = await WebRequirementsAdapter(fetcher, "2026/27").verify(
            candidate, program, "fall 2027"
        )

    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert not any(c.claim_type is ClaimType.PROGRAM_EXISTS for c in verified.claims)
    assert not any(c.claim_type is ClaimType.IELTS_MIN_OVERALL for c in verified.claims)


@pytest.mark.asyncio
async def test_old_cached_foreign_final_url_is_not_used_as_source(tmp_path):
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        fetcher.cache.put(
            FetchResult(
                url=SOURCE,
                outcome=FetchOutcome.OK,
                status_code=200,
                content=program_html("BSc Mathematics").encode(),
                text=program_html("BSc Mathematics"),
                final_url=FOREIGN,
            )
        )
        result = await fetcher.get(SOURCE)

    assert result.outcome is FetchOutcome.NETWORK_UNAVAILABLE
    assert result.text == ""


@pytest.mark.asyncio
async def test_browser_navigation_records_and_refuses_foreign_final_url(tmp_path):
    page = FakePage(FakePlaywrightResponse(200), program_html("BSc Mathematics"))
    page.url = FOREIGN
    result = await browser_with(page, tmp_path).render(SOURCE)

    assert result.outcome is FetchOutcome.BLOCKED
    assert result.final_url == FOREIGN


@pytest.mark.asyncio
async def test_requirements_adapter_refuses_an_ok_result_with_foreign_final_url(
    tmp_path,
):
    candidate = Candidate(
        name="Example University", country="Example", city="Example", domain="uni.edu"
    )
    program = CandidateProgram(
        name="BSc Mathematics", field="Mathematics", degree=DegreeLevel.BACHELOR, url=SOURCE
    )
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        StubSite({SOURCE: program_html("BSc Mathematics")}).install(fetcher)
        original_get = fetcher.get

        async def redirected(url: str, **kwargs):
            result = await original_get(url, **kwargs)
            result.final_url = FOREIGN
            return result

        fetcher.get = redirected  # type: ignore[method-assign]
        result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
            candidate, program, "fall 2027"
        )

    assert result.claims == []
    assert any("redirected off" in error for error in result.errors)


@pytest.mark.asyncio
async def test_discovery_refuses_foreign_body_even_when_a_fetcher_double_reports_ok(
    tmp_path, profile
):
    profile.context.intended_fields = ["Computer Science", "Mathematics"]
    trace = DiscoveryTrace(institution="Example University", domain="uni.edu")
    selected = {category: [] for category in PageCategory.ALL}
    selected[PageCategory.PROGRAM_PAGE] = [SOURCE]
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        StubSite({SOURCE: program_html("BSc Mathematics")}).install(fetcher)
        original_get = fetcher.get

        async def redirected(url: str, **kwargs):
            result = await original_get(url, **kwargs)
            if result.ok:
                result.final_url = FOREIGN
            return result

        fetcher.get = redirected  # type: ignore[method-assign]
        adapter = LiveDiscoveryAdapter(fetcher)
        await adapter._confirm_programs(
            selected, {category: [] for category in PageCategory.ALL}, trace, profile
        )
        recovered: list[str] = []
        await adapter._recover_search_pages(
            [RankedCandidate(SOURCE, "BSc Mathematics", 1, "fake")], recovered, trace, profile
        )

    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert recovered == []
    assert trace.field_sources == {}
