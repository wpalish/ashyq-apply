"""Plan rule SB-1: discovery gets a deadline, a read cap and a stop condition.

Structural analysis 2026-10-18 §2 F3: discovery had no stage budget, so the
first stages consumed whatever they could. UBC spent 78 s on navigation before
its first query, Imperial and UNSW never queried, and after the walker
confirmed Groningen's and TCD's pages the run kept reading. Offline: a fake
clock advances by a fixed cost per read; search goes to a fake provider.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import CatalogWalker
from app.adapters.discovery.live_discovery import (
    DISCOVERY_DEADLINE_SECONDS,
    DISCOVERY_SITEMAP_ALLOWANCE,
    RECOVERY_RESERVE_READS,
    SEARCH_LATEST_START_SECONDS,
    SLOW_HOST_SITEMAP_DOCUMENTS,
    LiveDiscoveryAdapter,
    StageBudget,
)
from app.adapters.fetching import Fetcher
from app.adapters.search import retrieval
from app.adapters.search.base import SearchResponse, SearchResult
from tests.test_live_discovery import (
    StubSite,
    _catalogue_html,
    program_html,
    sitemap_index_xml,
    sitemap_xml,
)

HOME = "https://uni.edu/"
CATALOGUE = "https://uni.edu/study/catalogue"
PROGRAMME = "https://uni.edu/programmes/bachelors/computer-science"
TWIN = "https://uni.edu/programmes/bachelors/computer-science-and-engineering"
CHILDREN = [f"https://uni.edu/s{i}.xml" for i in range(1, 6)]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Provider:
    """Returns ``answers`` for every query and counts the queries."""

    name = "fake"

    def __init__(self, answers: list[str], clock: FakeClock, latency: float = 0.0) -> None:
        self.answers = answers
        self.clock = clock
        self.latency = latency
        self.sent_at: list[float] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.sent_at.append(self.clock.now)
        self.clock.now += self.latency
        now = datetime.now(UTC)
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=now,
            results=tuple(
                SearchResult(
                    url=url,
                    title="BSc Computer Science",
                    provider=self.name,
                    rank=i + 1,
                    retrieved_at=now,
                )
                for i, url in enumerate(self.answers)
            ),
        )


def _junk(n: int) -> list[str]:
    """Programme-shaped sitemap leads that do not exist (404)."""
    return [f"https://uni.edu/programmes/bachelors/computer-science-{i}" for i in range(n)]


def _pages(*, programme_in: str | None = "s1", junk: int = 0) -> dict[str, bytes | str]:
    pages: dict[str, bytes | str] = {
        "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/index.xml\n",
        "https://uni.edu/index.xml": sitemap_index_xml(*CHILDREN),
        PROGRAMME: program_html(),
        TWIN: program_html("BSc Computer Science and Engineering"),
    }
    for i, child in enumerate(CHILDREN):
        pages[child] = sitemap_xml(f"https://uni.edu/about-{i}")
    if programme_in is not None:
        pages[f"https://uni.edu/{programme_in}.xml"] = sitemap_xml(PROGRAMME, *_junk(junk))
    elif junk:
        pages["https://uni.edu/s1.xml"] = sitemap_xml(*_junk(junk))
    return pages


async def _run(
    tmp_path,
    profile,
    monkeypatch,
    *,
    flag: bool,
    seconds_per_read: float,
    pages: dict[str, bytes | str],
    seeds: dict | None = None,
    answers: list[str] | None = None,
    latency: float = 0.0,
):
    monkeypatch.setattr(live_discovery, "STAGE_BUDGETS", flag)
    clock = FakeClock()
    monkeypatch.setattr(live_discovery, "_clock", clock)
    site = StubSite(pages)
    entry: dict[str, object] = {"name": "U", "country": "Turkey", "city": "X", "homepage": HOME}
    if seeds:
        entry["seeds"] = seeds
    tmp_path.mkdir(parents=True, exist_ok=True)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([entry]))
    provider = Provider(answers, clock, latency) if answers is not None else None
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        stub_get = fetcher.get

        async def timed_get(url, **kwargs):
            clock.now += seconds_per_read
            return await stub_get(url, **kwargs)

        fetcher.get = timed_get  # type: ignore[method-assign]
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        adapter._search_provider = provider  # type: ignore[assignment]
        adapter._search_provider_resolved = True
        candidates = await adapter.discover(profile)
        assert adapter.fetcher is fetcher, "the budgeted wrapper is removed after discovery"
    return candidates[0], adapter.traces[0], site, provider, clock


@pytest.fixture
def cs_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


class TestStageBudget:
    def test_deadline_and_read_cap_latch(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget(deadline_seconds=10, read_cap=2)
        assert not budget.exhausted()
        clock.now = 10.0
        assert budget.exhausted()
        assert budget.stopped_by == "deadline"
        clock.now = 0.0
        assert budget.exhausted(), "a spent budget stays spent"

    def test_seconds_go_to_the_stage_that_spent_them(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget()
        clock.now = 3.0
        budget.enter("confirm")
        clock.now = 7.0
        budget.query_sent()
        report = budget.as_dict()
        assert report["stage_seconds"]["sitemap"] == 3.0
        assert report["stage_seconds"]["confirm"] == 4.0
        assert report["t_first_query"] == 7.0
        assert report["deadline_seconds"] == DISCOVERY_DEADLINE_SECONDS


class TestDeadline:
    @pytest.mark.asyncio
    async def test_deadline_ends_discovery_and_keeps_the_confirmed_page(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        candidate, trace, site, _, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=4.0,
            pages=_pages(junk=8),
        )
        report = trace.as_dict()["stage_budget"]
        assert report["stopped_by"] == "deadline"
        assert report["stopped_in"] == "confirm"
        # No read starts after the deadline; the last one may end past it.
        assert clock.now < DISCOVERY_DEADLINE_SECONDS + 4.0
        assert report["refused_reads"] == 0, "stages check before they read"
        # The verify stage's input: the confirmed programme page.
        assert [program.url for program in candidate.programs] == [PROGRAMME]
        assert trace.stage_order[-2:] == ["walker_skipped", "search_skipped"]
        assert any("not read: the discovery stage budget is spent" in r for _, r in trace.rejected)

    @pytest.mark.asyncio
    async def test_read_cap_ends_discovery(self, tmp_path, cs_bachelor, monkeypatch):
        monkeypatch.setattr(live_discovery, "DISCOVERY_READ_CAP", 5)
        candidate, trace, site, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=_pages(junk=8),
        )
        # SB-1b: the seven sitemap reads are not candidate reads.
        assert len(site.requested) == 7 + 5
        assert trace.stage_budget["candidate_reads"] == 5
        assert trace.stage_budget["stopped_by"] == "read_cap"
        assert [program.url for program in candidate.programs] == [PROGRAMME]

    @pytest.mark.asyncio
    async def test_flag_off_reads_past_the_deadline(self, tmp_path, cs_bachelor, monkeypatch):
        candidate, trace, site, _, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=4.0,
            pages=_pages(junk=8),
        )
        assert clock.now > DISCOVERY_DEADLINE_SECONDS
        assert len([u for u in site.requested if "computer-science" in u]) == 8
        assert "stage_budget" not in trace.as_dict()
        assert "stage_order" not in trace.as_dict()
        assert [program.url for program in candidate.programs] == [PROGRAMME]


class TestStopWhenConfirmed:
    @pytest.mark.asyncio
    async def test_a_confirmed_page_skips_the_walker(self, tmp_path, cs_bachelor, monkeypatch):
        seeds = {"program_catalog": CATALOGUE}
        pages = {**_pages(), CATALOGUE: _catalogue_html((TWIN, "Computer Science and Eng"))}
        _, off_trace, off_site, _, _ = await _run(
            tmp_path / "off",
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=0.1,
            pages=pages,
            seeds=seeds,
        )
        assert CATALOGUE in off_site.requested, "today the walker reads the catalogue"
        _, trace, site, _, _ = await _run(
            tmp_path / "on",
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=pages,
            seeds=seeds,
        )
        assert CATALOGUE not in site.requested
        assert "walker_skipped" in trace.stage_order
        assert trace.walker["catalogs_walked"] == 0

    @pytest.mark.asyncio
    async def test_walker_reads_no_lead_after_a_confirmation(self, tmp_path):
        site = StubSite(
            {
                CATALOGUE: _catalogue_html(
                    (PROGRAMME, "Computer Science"),
                    (TWIN, "Computer Science and Engineering"),
                ),
                PROGRAMME: program_html(),
                TWIN: program_html("BSc Computer Science and Engineering"),
            }
        )

        async def walk(stop_when_confirmed: bool) -> list[str]:
            site.requested.clear()
            async with Fetcher(tmp_path / f"c{stop_when_confirmed}", offline=True) as fetcher:
                site.install(fetcher)
                walker = CatalogWalker(
                    fetcher=fetcher,
                    domain="uni.edu",
                    degree="bachelor",
                    fields=["computer science"],
                    stop_when_confirmed=stop_when_confirmed,
                )
                walks = await walker.walk([CATALOGUE])
            return walks[0].confirmed

        assert sorted(await walk(False)) == sorted([PROGRAMME, TWIN])
        assert len(await walk(True)) == 1
        assert len(site.requested) == 2, "the catalogue and one lead"

    @pytest.mark.asyncio
    async def test_recovery_stops_at_its_first_confirmation_and_no_second_pass(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        pages = _pages(programme_in=None)
        _, off_trace, off_site, off_provider, _ = await _run(
            tmp_path / "off",
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=0.1,
            pages=pages,
            answers=[PROGRAMME, TWIN],
        )
        assert TWIN in off_site.requested
        _, trace, site, provider, _ = await _run(
            tmp_path / "on",
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=pages,
            answers=[PROGRAMME, TWIN],
        )
        assert PROGRAMME in site.requested
        assert TWIN not in site.requested
        assert trace.selected["program_page"] == [PROGRAMME]
        assert trace.discovery_query_passes == [3], "no second pass after a confirmation"
        assert provider is not None and len(provider.sent_at) == 3

    @pytest.mark.asyncio
    async def test_hop_roots_are_skipped_when_a_candidate_exists(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        hops: list[int] = []
        real = retrieval.discover_candidates

        async def spy(*args, **kwargs):
            hops.append(kwargs.get("hop_entry_points", retrieval.DEFAULT_HOP_ENTRY_POINTS))
            return await real(*args, **kwargs)

        monkeypatch.setattr(retrieval, "discover_candidates", spy)
        # The sitemap offers programme leads, none of which exists.
        pages = _pages(programme_in=None, junk=2)
        _, trace, site, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.1,
            pages=pages,
            answers=[PROGRAMME],
        )
        assert hops and hops[0] == 0
        assert HOME not in site.requested
        assert any("SB-1: no entry-point hop" in line for line in trace.errors)


class TestSlowHost:
    @pytest.mark.asyncio
    async def test_slow_host_searches_after_the_first_sitemap_document(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        candidate, trace, site, provider, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=10.0,
            pages=_pages(programme_in=None),
            answers=[PROGRAMME],
        )
        assert provider is not None
        # robots.txt and the index, then the first query.
        assert provider.sent_at[0] == 20.0
        assert trace.stage_budget["t_first_query"] == 20.0
        # Search confirmed the page, so no further sitemap document is read.
        assert not any(child in site.requested for child in CHILDREN)
        assert site.requested.count(PROGRAMME) == 1, "confirm trusts recovery's read"
        assert [program.url for program in candidate.programs] == [PROGRAMME]
        assert trace.stage_order == ["sitemaps", "search", "confirm", "walker_skipped"]
        assert trace.host_cost["slow"] is True

    @pytest.mark.asyncio
    async def test_slow_host_without_a_search_page_reads_three_sitemap_documents(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        _, trace, site, provider, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=6.0,
            pages=_pages(programme_in="s1"),
            answers=[],
        )
        sitemap_documents = [u for u in site.requested if u.endswith(".xml")]
        assert len(sitemap_documents) == SLOW_HOST_SITEMAP_DOCUMENTS
        assert provider is not None and provider.sent_at[0] == 12.0
        assert trace.stage_order[:2] == ["sitemaps", "search"]
        assert "walker_skipped" in trace.stage_order
        assert trace.stage_order.count("search") == 1

    @pytest.mark.asyncio
    async def test_fast_host_keeps_todays_order(self, tmp_path, cs_bachelor, monkeypatch):
        _, trace, site, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=1.0,
            pages=_pages(programme_in="s1"),
            answers=[],
        )
        assert len([u for u in site.requested if u.endswith(".xml")]) == 6
        assert trace.stage_order == ["sitemaps", "confirm", "walker_skipped", "search"]
        assert trace.host_cost["slow"] is False


class TestTrace:
    @pytest.mark.asyncio
    async def test_trace_has_seconds_and_reads_per_stage(self, tmp_path, cs_bachelor, monkeypatch):
        _, trace, site, _, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=1.0,
            pages=_pages(programme_in="s1"),
            answers=[TWIN],
        )
        report = trace.as_dict()["stage_budget"]
        assert set(report["stage_seconds"]) == {
            "sitemap",
            "navigation",
            "walker",
            "confirm",
            "search",
            "recovery",
        }
        assert report["stage_reads"]["sitemap"] == 7  # robots, index, five children
        assert report["stage_reads"]["confirm"] == 1
        assert report["reads"] == len(site.requested)
        assert sum(report["stage_seconds"].values()) == pytest.approx(clock.now)
        assert report["seconds"] == pytest.approx(clock.now)
        assert report["t_first_query"] == 8.0
        assert report["stopped_by"] is None


# SB-1b (wrong-claims analysis 2026-10-18 §3): a catalogue of twenty
# programme-shaped links that do not exist keeps navigation, confirm and the
# walker reading; only search knows where the programme is.
TRACKS = [f"https://uni.edu/programmes/bachelors/computer-science-track-{i}" for i in range(20)]
DEAD = [f"https://uni.edu/programmes/bachelors/computer-science-old-{i}" for i in range(5)]


def _walker_site() -> dict[str, bytes | str]:
    links = [(url, f"Computer Science track {i}") for i, url in enumerate(TRACKS)]
    return {**_pages(programme_in=None), CATALOGUE: _catalogue_html(*links)}


async def _walker_run(tmp_path, profile, monkeypatch, *, flag: bool, **kwargs):
    return await _run(
        tmp_path,
        profile,
        monkeypatch,
        flag=flag,
        pages=_walker_site(),
        seeds={"program_catalog": CATALOGUE},
        **kwargs,
    )


class TestSearchIsNotARead:
    @pytest.mark.asyncio
    async def test_read_cap_spent_in_the_walker_still_searches_and_recovers(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        """UCPH: the walker spent the read cap; search confirmed the page in the off arm."""
        monkeypatch.setattr(live_discovery, "DISCOVERY_READ_CAP", 6)
        candidate, trace, _, provider, clock = await _walker_run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.5,
            answers=[PROGRAMME],
        )
        report = trace.stage_budget
        assert report["stopped_by"] == "read_cap"
        assert report["stopped_in"] == "walker"
        assert clock.now < SEARCH_LATEST_START_SECONDS, "the cap, not the clock, stopped it"
        assert "search_skipped" not in trace.stage_order
        assert trace.stage_order[-1] == "search"
        assert provider is not None and len(provider.sent_at) == 3
        # The page is read from the reserve past the spent cap.
        assert report["reserve_reads"] == 1
        assert report["stage_reads"]["recovery"] == 1
        assert report["refused_reads"] == 0
        assert [program.url for program in candidate.programs] == [PROGRAMME]
        assert trace.discovery_query_passes == [3], "no second pass on a spent budget"

    @pytest.mark.asyncio
    async def test_the_reserve_is_three_reads(self, tmp_path, cs_bachelor, monkeypatch):
        monkeypatch.setattr(live_discovery, "DISCOVERY_READ_CAP", 6)
        candidate, trace, site, _, _ = await _walker_run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.5,
            answers=DEAD,
        )
        assert trace.stage_budget["reserve_reads"] == RECOVERY_RESERVE_READS
        read = [url for url in DEAD if url in site.requested]
        assert len(read) == RECOVERY_RESERVE_READS < len(DEAD)
        assert trace.stage_budget["refused_reads"] == 0
        assert candidate.programs == []


class TestLatestFirstQuery:
    @pytest.mark.asyncio
    async def test_search_starts_by_33_seconds_and_cuts_the_walker(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        """Chula: sitemaps, navigation and the walker put the first query at 34 s."""
        candidate, trace, site, provider, _ = await _walker_run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=2.0,
            answers=[PROGRAMME],
        )
        assert provider is not None
        # No read starts at or after 33 s before the first query; one may end past it.
        assert provider.sent_at[0] < SEARCH_LATEST_START_SECONDS + 2.0
        assert trace.stage_budget["t_first_query"] == provider.sent_at[0]
        assert any(o["outcome"] == "walker_stopped" for o in trace.walker["outcomes"])
        assert not any(url in site.requested for url in TRACKS[10:])
        assert any("SB-1b: nothing confirmed by 33 s" in line for line in trace.errors)
        assert [program.url for program in candidate.programs] == [PROGRAMME]

    @pytest.mark.asyncio
    async def test_deadline_during_the_queries_keeps_the_recovery_reserve(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        """Chula rep 1: slow provider answers; the deadline fell before any recovery read."""
        candidate, trace, site, provider, _ = await _walker_run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=2.0,
            answers=[DEAD[0], PROGRAMME],
            latency=8.0,
        )
        report = trace.stage_budget
        assert provider is not None and len(provider.sent_at) == 3
        assert provider.sent_at[-1] + 8.0 > DISCOVERY_DEADLINE_SECONDS
        assert report["stopped_by"] == "deadline"
        assert report["reserve_reads"] == 2
        assert site.requested[-2:] == [DEAD[0], PROGRAMME]
        assert [program.url for program in candidate.programs] == [PROGRAMME]

    def test_no_reserve_past_the_deadline_once_recovery_has_read(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget(deadline_seconds=10, read_cap=28)
        budget.enter("recovery")
        budget.note_recovery_read()
        clock.now = 10.0
        assert budget.exhausted()
        assert not budget.reserve_open()

    @pytest.mark.asyncio
    async def test_nothing_is_cut_without_a_search_provider(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        _, trace, _, _, _ = await _walker_run(
            tmp_path, cs_bachelor, monkeypatch, flag=True, seconds_per_read=1.5
        )
        assert trace.stage_budget["seconds"] > SEARCH_LATEST_START_SECONDS
        assert trace.stage_budget["stopped_by"] is None
        assert not any(o["outcome"] == "walker_stopped" for o in trace.walker["outcomes"])
        assert not any("SB-1b" in line for line in trace.errors)


class TestSitemapAllowance:
    @pytest.mark.asyncio
    async def test_sitemap_documents_do_not_spend_candidate_reads(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        """UCPH and Chula: 13 sitemap reads of the 28."""
        monkeypatch.setattr(live_discovery, "DISCOVERY_READ_CAP", 3)
        children = [f"https://uni.edu/t{i}.xml" for i in range(1, 12)]
        pages: dict[str, bytes | str] = {
            "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/index.xml\n",
            "https://uni.edu/index.xml": sitemap_index_xml(*children),
            PROGRAMME: program_html(),
        }
        for i, child in enumerate(children[:-1]):
            pages[child] = sitemap_xml(f"https://uni.edu/about-{i}")
        pages[children[-1]] = sitemap_xml(PROGRAMME)
        candidate, trace, _, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=0.5,
            pages=pages,
        )
        report = trace.stage_budget
        assert report["stage_reads"]["sitemap"] == 13 == DISCOVERY_SITEMAP_ALLOWANCE
        assert report["candidate_reads"] == 1
        assert report["stopped_by"] is None
        assert [program.url for program in candidate.programs] == [PROGRAMME]

    def test_the_allowance_is_its_own_count(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(live_discovery, "_clock", clock)
        budget = StageBudget(read_cap=1)
        budget.reads["sitemap"] = budget.sitemap_allowance
        assert budget.sitemap_spent()
        assert not budget.exhausted(), "sitemap reads are not candidate reads"


class TestFlagOffUnchanged:
    @pytest.mark.asyncio
    async def test_flag_off_reads_every_lead_before_it_searches(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        """The SB-1b scenario with the rule off: the order before SB-1b, read for read."""
        candidate, trace, site, provider, clock = await _walker_run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=2.0,
            answers=[PROGRAMME],
        )
        assert provider is not None and provider.sent_at == [64.0, 64.0, 64.0]
        assert len(site.requested) == 34
        assert all(url in site.requested for url in TRACKS)
        assert clock.now == 68.0
        assert "stage_budget" not in trace.as_dict()
        assert not any("SB-1" in line for line in trace.errors)
        assert [program.url for program in candidate.programs] == [PROGRAMME]


def _uio_site(*, programme_in_sitemap: bool = False) -> dict[str, bytes | str]:
    """UiO: three programme-shaped sitemap leads, none of them a page, in a long index."""
    children = [f"https://uni.edu/t{i}.xml" for i in range(1, 11)]
    leads = [*([PROGRAMME] if programme_in_sitemap else []), *_junk(3)]
    pages: dict[str, bytes | str] = {
        "https://uni.edu/robots.txt": "Sitemap: https://uni.edu/index.xml\n",
        "https://uni.edu/index.xml": sitemap_index_xml(*children),
        children[0]: sitemap_xml(*leads),
        PROGRAMME: program_html(),
    }
    for i, child in enumerate(children[1:]):
        pages[child] = sitemap_xml(f"https://uni.edu/about-{i}")
    return pages


class TestUnconfirmedLeadsDoNotBlockSearch:
    """SB-1c (discovery analysis 2026-10-18 D1): UiO sent no query in either repetition."""

    @pytest.mark.asyncio
    async def test_three_unconfirmed_leads_at_33_seconds_still_search_and_recover(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        candidate, trace, site, provider, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=4.0,
            pages=_uio_site(),
            answers=[PROGRAMME],
        )
        assert provider is not None and provider.sent_at, "a query was sent"
        assert provider.sent_at[0] < SEARCH_LATEST_START_SECONDS + 4.0
        assert trace.discovery_query_passes == [3]
        assert not any("slots were already filled" in line for line in trace.search_limitations)
        assert any("SB-1b: nothing confirmed by 33 s" in line for line in trace.errors)
        assert any("SB-1c: 3 unconfirmed programme lead(s)" in line for line in trace.errors)
        assert trace.stage_budget["stage_reads"]["recovery"] == 1
        assert site.requested.count(PROGRAMME) == 1, "confirm trusts recovery's read"
        # The leads keep their slots for the confirm stage, which still reads them.
        assert all(url in site.requested for url in _junk(3))
        assert trace.stage_order.count("search") == 1
        assert trace.stage_order[-2:] == ["confirm", "walker_skipped"]
        assert [program.url for program in candidate.programs] == [PROGRAMME]

    @pytest.mark.asyncio
    async def test_an_early_search_that_sent_nothing_runs_again_after_the_walker(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        calls: list[str] = []

        async def refused(self, entry, domain, selected, trace, profile, **kwargs):
            calls.append("search")
            trace.search_limitations.append("Search not run: refused before any query")

        monkeypatch.setattr(LiveDiscoveryAdapter, "_add_search_results", refused)
        _, trace, _, _, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=4.0,
            pages=_uio_site(),
            answers=[PROGRAMME],
        )
        # Once by 33 s and once after the walker: the first sent no query.
        assert len(calls) == 2
        assert trace.stage_order.count("search") == 2
        assert trace.stage_order[-1] == "search"

    @pytest.mark.asyncio
    async def test_confirmed_before_33_seconds_is_unchanged(
        self, tmp_path, cs_bachelor, monkeypatch
    ):
        candidate, trace, site, provider, _ = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=True,
            seconds_per_read=1.0,
            pages=_uio_site(programme_in_sitemap=True),
            answers=[PROGRAMME],
        )
        assert trace.stage_order == ["sitemaps", "confirm", "walker_skipped", "search"]
        assert not any("SB-1c" in line for line in trace.errors)
        assert not any("SB-1b" in line for line in trace.errors)
        assert site.requested.count(PROGRAMME) == 1
        assert [program.url for program in candidate.programs] == [PROGRAMME]
        assert provider is not None and len(provider.sent_at) == 3

    @pytest.mark.asyncio
    async def test_flag_off_is_unchanged(self, tmp_path, cs_bachelor, monkeypatch):
        candidate, trace, site, provider, clock = await _run(
            tmp_path,
            cs_bachelor,
            monkeypatch,
            flag=False,
            seconds_per_read=4.0,
            pages=_uio_site(),
            answers=[PROGRAMME],
        )
        assert provider is not None and provider.sent_at == [60.0, 60.0, 60.0]
        assert clock.now == 68.0
        assert len(site.requested) == 17
        assert "stage_budget" not in trace.as_dict()
        assert not any("SB-1" in line for line in trace.errors)
        assert [program.url for program in candidate.programs] == [PROGRAMME]
