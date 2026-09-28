"""Search must reach the programme behind noisy results, within its read cap."""

from pathlib import Path

import pytest

from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, program_html


async def recover(tmp_path, profile, urls, bodies, existing=()):
    profile.context.intended_fields = ["computer science"]
    site = StubSite(dict(zip(urls, bodies, strict=True)))
    pages = list(existing)
    trace = DiscoveryTrace(institution="U", domain="uni.edu")
    candidates = [RankedCandidate(u, "Computer Science", 1, "fake") for u in urls]
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(candidates, pages, trace, profile)
    return pages, trace, site.requested


@pytest.mark.asyncio
async def test_a_news_item_and_article_do_not_hide_the_third_result(tmp_path, profile):
    urls = ["https://uni.edu/story", "https://uni.edu/article", "https://uni.edu/bsc/cs"]
    pages, _, _ = await recover(
        tmp_path,
        profile,
        urls,
        [
            "<h1>Success of a former computer science student</h1>",
            "<h1>Teaching computer science in economic studies</h1>",
            program_html(),
        ],
    )
    assert pages == [urls[2]]


@pytest.mark.asyncio
async def test_a_school_listing_still_confirms_a_full_degree_title(tmp_path, profile):
    url = "https://uni.edu/school"
    html = (
        "<h1>Computing and Data Science</h1><p>Explore masters programmes.</p>"
        "<p>Bachelor of Engineering in Computer Science covers algorithms.</p>"
    )
    pages, _, _ = await recover(tmp_path, profile, [url], [html])
    assert pages == [url]


@pytest.mark.asyncio
async def test_a_masters_programme_does_not_confirm_a_bachelor(tmp_path, profile):
    pages, _, _ = await recover(
        tmp_path, profile, ["https://uni.edu/cs"], [program_html("MSc Computer Science")]
    )
    assert pages == []


@pytest.mark.asyncio
async def test_a_failed_host_does_not_displace_a_reachable_programme(tmp_path, profile):
    urls = ["https://uni.edu/missing", "https://uni.edu/bsc/cs"]
    pages, _, _ = await recover(tmp_path, profile, urls, [None, program_html()])
    assert pages == [urls[1]]


@pytest.mark.asyncio
async def test_all_unavailable_results_remain_unresolved_leads(tmp_path, profile):
    url = "https://uni.edu/missing"
    pages, trace, _ = await recover(tmp_path, profile, [url], [None])
    assert pages == [url]
    assert trace.rejected


@pytest.mark.asyncio
async def test_recovery_is_bounded_and_keeps_previously_confirmed_pages(tmp_path, profile):
    urls = [f"https://uni.edu/noise{i}" for i in range(12)]
    pages, _, requested = await recover(
        tmp_path,
        profile,
        urls,
        ["<h1>A staff directory</h1>"] * 12,
        existing=["https://uni.edu/confirmed"],
    )
    assert pages == ["https://uni.edu/confirmed"]
    assert len(requested) == 8


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title",
    [
        "Bachelor Teaching Education: Teaching Subject Computer Science",
        "Bachelor Teaching Education: Teaching Subject Digital Literacy and Computer Science",
        "Bachelor Computer Science: Specialisations",
        "BSc Computer Science minor",
        "State final examination for the bachelor of Computer Science study program",
    ],
)
async def test_an_alternate_programme_is_not_the_requested_degree(tmp_path, profile, title):
    pages, trace, _ = await recover(
        tmp_path, profile, ["https://uni.edu/cs"], [program_html(title)]
    )
    assert pages == []
    assert trace.rejected


@pytest.mark.asyncio
async def test_a_search_catalogue_lead_reaches_its_matching_detail_page(tmp_path, profile):
    urls = ["https://uni.edu/programmes", "https://uni.edu/programmes/bsc-cs"]
    pages, _, requested = await recover(
        tmp_path,
        profile,
        urls,
        [
            "<h1>Degree programmes</h1>"
            "<a href='/programmes/bsc-cs'>Computer Science bachelor</a>"
            "<a href='/programmes/msc-cs'>Computer Science master</a>",
            program_html(),
        ],
    )
    assert pages == [urls[1]]
    assert requested == urls


@pytest.mark.asyncio
async def test_a_subject_page_without_a_degree_is_not_confirmed(tmp_path, profile):
    pages, _, _ = await recover(
        tmp_path, profile, ["https://uni.edu/cs"], ["<h1>Computer Science</h1><p>Courses.</p>"]
    )
    assert pages == []
