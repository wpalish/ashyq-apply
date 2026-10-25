"""Rule FRH: follow a refused hub's field link (NO_SEARCH_FLOOR_2026-10-21 §8.5).

A page the confirm stage or the walker reads and refuses is a *hub* when it
reads as a listing (unknown or catalogue) and its URL or head names a requested
field. On (``FOLLOW_REFUSED_HUB_LINK``): the hub's one best field link
(``catalog_walker.refused_hub_lead``: the hub's own children first, then the
link score, then the URL) is read next, one hop, and judged like any candidate;
at most ``FOLLOW_REFUSED_HUB_LINK_CAP`` follows per case and one per hub, none
once a programme page is confirmed, none once the stage budget is spent, and a
followed page is never a hub. A hub's URL names the field as whole consecutive
slug words (§8.6): one word of a longer field name is not the field. Off:
nothing changes.

Every site, page, label and subject here is written for the test
(``example-uni.edu``, the subjects "geology" and "marine biology"); no page,
label or word comes from a development or heldout case. Offline: a fake
fetcher serves the pages and a fake clock times the reads.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

import httpx
import pytest

from app.adapters import fetching
from app.adapters.discovery import catalog_walker, live_discovery
from app.adapters.discovery.catalog_walker import (
    CatalogWalk,
    CatalogWalker,
    WalkerLink,
    refused_hub_lead,
)
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    is_refused_hub,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageClassification, classify_page
from evaluation.research import live
from tests.test_live_discovery import StubSite, program_html, sitemap_xml
from tests.test_stage_budgets import FakeClock

BACKEND = Path(__file__).resolve().parents[1]
DOMAIN = "www.example-uni.edu"
W = f"https://{DOMAIN}"
STUDY = "https://study.example-uni.edu"
HOME = f"{W}/"
FIELDS = ["geology"]

# 1. The confirm shape: a refused listing page whose URL names the field.
HUB = f"{W}/find/geology.html"
CHILD = f"{W}/find/geology/undergraduate.html"
SCHOOL = f"{W}/about/school-of-geology.html"

# 2. The walker shape: a catalogue whose first lead is a refused college page.
CATALOGUE = f"{W}/study/programmes"
COLLEGE = f"{W}/college-of-geology"
COLLEGE_PROGRAMME = f"{W}/program/bsc-in-geology"
SECOND = f"{W}/study/geology-pathway-programme"
DEAD_SEED = f"{W}/programmes/geology-closed"


def hub_html(title: str, *links: tuple[str, str]) -> str:
    """A page that lists links and reads as no programme (``unknown``)."""
    anchors = "".join(f'<li><a href="{url}">{label}</a></li>' for url, label in links)
    return (
        f"<html><head><title>{title} - Example University</title></head><body>"
        f"<main><h1>{title}</h1><p>Explore what you can study with us.</p>"
        f"<ul>{anchors}</ul></main></body></html>"
    )


def catalogue_html(*links: tuple[str, str]) -> str:
    anchors = "".join(f'<li><a href="{url}">{label}</a></li>' for url, label in links)
    return (
        "<html><head><title>Programmes | Example University</title></head><body><main>"
        "<h1>Our programmes</h1><p>Browse all the programmes this university offers across "
        "every faculty, with details about each course and how to apply for it.</p>"
        f"<ul>{anchors}</ul></main></body></html>"
    )


@pytest.fixture
def geology(profile):
    profile.context.intended_fields = list(FIELDS)
    profile.context.level = "bachelor"
    return profile


@pytest.fixture(params=[False, True], ids=["frh-off", "frh-on"])
def frh(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "FOLLOW_REFUSED_HUB_LINK", request.param)
    return request.param


async def _run(
    tmp_path: Path,
    profile: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    pages: dict[str, bytes | str],
    seeds: dict[str, str] | None = None,
    on: bool,
) -> tuple[DiscoveryTrace, StubSite]:
    monkeypatch.setattr(live_discovery, "FOLLOW_REFUSED_HUB_LINK", on)
    monkeypatch.setattr(live_discovery, "STAGE_BUDGETS", True)
    clock = FakeClock()
    monkeypatch.setattr(live_discovery, "_clock", clock)
    site = StubSite(pages)
    entry: dict[str, object] = {"name": "U", "country": "Testland", "city": "X", "homepage": HOME}
    if seeds:
        entry["seeds"] = seeds
    tmp_path.mkdir(parents=True, exist_ok=True)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([entry]))
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        stub_get = fetcher.get

        async def timed_get(url, **kwargs):
            clock.now += 0.1
            return await stub_get(url, **kwargs)

        fetcher.get = timed_get  # type: ignore[method-assign]
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        adapter._search_provider = None
        adapter._search_provider_resolved = True
        await adapter.discover(profile)
    return adapter.traces[0], site


def _serialised(trace: DiscoveryTrace) -> str:
    data = trace.as_dict()
    data.pop("case_time", None)  # the case clock runs on the wall clock
    return json.dumps(data, sort_keys=True, default=str)


def _confirm_pages() -> dict[str, bytes | str]:
    return {
        HUB: hub_html(
            "Geology",
            ("/about/school-of-geology.html", "School of Geology"),
            ("/find/geology/undergraduate.html", "Undergraduate study"),
        ),
        CHILD: program_html("Bachelor of Science in Geology"),
        SCHOOL: hub_html("School of Geology"),
    }


# --- 1. the confirm shape ------------------------------------------------------------


class TestConfirmShape:
    async def test_on_reads_the_child_next_and_confirms_it(self, tmp_path, geology, monkeypatch):
        trace, site = await _run(
            tmp_path,
            geology,
            monkeypatch,
            pages=_confirm_pages(),
            seeds={"program_page": HUB},
            on=True,
        )
        assert site.requested[site.requested.index(HUB) + 1] == CHILD
        assert SCHOOL not in site.requested, "the higher-scored non-child is never fetched"
        assert trace.selected["program_page"] == [CHILD]
        assert trace.refused_hub_links == [(HUB, CHILD, "confirmed")]
        assert trace.as_dict()["refused_hub_links"] == [(HUB, CHILD, "confirmed")]
        assert (HUB, "reads as unknown, not a programme page") in trace.pages_read

    async def test_off_reads_neither_and_the_trace_is_unchanged(
        self, tmp_path, geology, monkeypatch
    ):
        pages, seeds = _confirm_pages(), {"program_page": HUB}
        trace, site = await _run(
            tmp_path / "off", geology, monkeypatch, pages=pages, seeds=seeds, on=False
        )
        assert HUB in site.requested
        assert CHILD not in site.requested and SCHOOL not in site.requested
        assert "refused_hub_links" not in trace.as_dict()
        assert "program_page" not in trace.selected

        def untouched(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("the rule is consulted while it is off")

        # The flag-less run: the rule's code cannot run at all.
        monkeypatch.setattr(catalog_walker, "refused_hub_lead", untouched)
        monkeypatch.setattr(live_discovery, "is_refused_hub", untouched)
        bare, bare_site = await _run(
            tmp_path / "bare", geology, monkeypatch, pages=pages, seeds=seeds, on=False
        )
        assert bare_site.requested == site.requested
        assert _serialised(bare) == _serialised(trace)


# --- 2. the walker shape -------------------------------------------------------------


def _walker_pages() -> dict[str, bytes | str]:
    return {
        CATALOGUE: catalogue_html(
            ("/college-of-geology", "College of Geology"),
            ("/study/geology-pathway-programme", "Geology pathway programme"),
        ),
        COLLEGE: hub_html(
            "College of Geology",
            ("/program/bsc-in-geology", "Bachelor of Science in Geology"),
        ),
        COLLEGE_PROGRAMME: program_html("Bachelor of Science in Geology"),
        SECOND: program_html("Bachelor of Science in Geology Pathway"),
    }


class TestWalkerShape:
    #: A dead programme seed keeps the navigation fallback out of the walk.
    SEEDS: ClassVar[dict[str, str]] = {"program_catalog": CATALOGUE, "program_page": DEAD_SEED}

    async def test_on_confirms_the_linked_programme_and_stops(self, tmp_path, geology, monkeypatch):
        trace, site = await _run(
            tmp_path, geology, monkeypatch, pages=_walker_pages(), seeds=self.SEEDS, on=True
        )
        assert site.requested[site.requested.index(COLLEGE) + 1] == COLLEGE_PROGRAMME
        assert SECOND not in site.requested
        outcomes = [(row["url"], row["outcome"]) for row in trace.walker["outcomes"]]
        assert (COLLEGE, "reads_as_unknown") in outcomes
        assert (COLLEGE_PROGRAMME, "hub_link_program_detail") in outcomes
        assert (SECOND, "walker_stopped") in outcomes
        assert trace.selected["program_page"] == [COLLEGE_PROGRAMME]
        assert trace.refused_hub_links == [(COLLEGE, COLLEGE_PROGRAMME, "confirmed")]

    async def test_off_is_unchanged(self, tmp_path, geology, monkeypatch):
        trace, site = await _run(
            tmp_path, geology, monkeypatch, pages=_walker_pages(), seeds=self.SEEDS, on=False
        )
        assert COLLEGE in site.requested and SECOND in site.requested
        assert COLLEGE_PROGRAMME not in site.requested
        assert trace.selected["program_page"] == [SECOND]
        assert not any(row["outcome"].startswith("hub_link_") for row in trace.walker["outcomes"])
        assert "refused_hub_links" not in trace.as_dict()


# --- 3. the trigger ------------------------------------------------------------------


class TestTrigger:
    async def test_a_listing_naming_no_field_is_no_hub(self, tmp_path, geology, monkeypatch):
        page = f"{W}/find/rocks.html"
        target = f"{W}/find/rocks/geology-undergraduate.html"
        pages = {
            page: hub_html("Rocks and minerals", (target, "Bachelor of Science in Geology")),
            target: program_html("Bachelor of Science in Geology"),
        }
        trace, site = await _run(
            tmp_path, geology, monkeypatch, pages=pages, seeds={"program_page": page}, on=True
        )
        assert page in site.requested and target not in site.requested
        assert trace.refused_hub_links == []

    @pytest.mark.parametrize(
        ("page", "title"),
        [
            (f"{W}/programmes/geology-and-history", "Bachelor of Arts in History"),
            (f"{W}/programmes/geology-advanced", "Master of Science in Geology"),
        ],
        ids=["refused-on-subject", "refused-on-level"],
    )
    async def test_a_programme_page_refused_on_identity_is_no_hub(
        self, tmp_path, geology, monkeypatch, page, title
    ):
        target = f"{page}/bachelor-of-science-in-geology"
        html = program_html(title).replace(
            "</main>", f'<a href="{target}">Bachelor of Science in Geology</a></main>'
        )
        pages = {page: html, target: program_html("Bachelor of Science in Geology")}
        trace, site = await _run(
            tmp_path, geology, monkeypatch, pages=pages, seeds={"program_page": page}, on=True
        )
        assert page in site.requested and target not in site.requested
        assert trace.refused_hub_links == []

    async def test_a_followed_page_is_never_a_hub(self, tmp_path, geology, monkeypatch):
        overview = f"{W}/find/geology/overview.html"
        below = f"{W}/find/geology/overview/bachelor-of-science.html"
        pages = {
            HUB: hub_html("Geology", ("/find/geology/overview.html", "Geology overview")),
            overview: hub_html("Geology overview", (below, "Bachelor of Science in Geology")),
            below: program_html("Bachelor of Science in Geology"),
        }
        trace, site = await _run(
            tmp_path, geology, monkeypatch, pages=pages, seeds={"program_page": HUB}, on=True
        )
        assert overview in site.requested, "the follow read the field-named hub page"
        assert below not in site.requested, "a page reached by a follow triggers no follow"
        assert trace.refused_hub_links == [
            (HUB, overview, "reads as unknown, not a programme page")
        ]

    def test_the_hub_predicate(self) -> None:
        unknown = classify_page(url=HUB, html=hub_html("Geology"))
        assert is_refused_hub(unknown, HUB, FIELDS)
        assert not is_refused_hub(unknown, f"{W}/find/rocks.html", FIELDS)
        assert not is_refused_hub(unknown, HUB, [])
        programme = classify_page(url=CHILD, html=program_html("Bachelor of Arts in History"))
        assert not is_refused_hub(programme, CHILD, FIELDS)

    def test_one_word_of_a_longer_field_in_the_url_is_no_hub(self) -> None:
        """§8.6: the URL names the whole field (SR-1's phrase test), not one of its words."""
        fields = ["marine biology"]
        listing = hub_html("Laboratories")
        for url, hub in [
            (f"{W}/research/biology-labs", False),
            (f"{W}/events/biology-week", False),
            (f"{W}/research/marine-research", False),
            (f"{W}/find/marine-biology.html", True),
            (f"{W}/faculty/school-of-marine-biology/study", True),
        ]:
            page = classify_page(url=url, html=listing)
            assert live_discovery.matches_field(url, fields) > 0, url
            assert is_refused_hub(page, url, fields) is hub, url

    async def test_a_listing_naming_one_word_of_the_field_causes_no_fetch(
        self, tmp_path, profile, monkeypatch
    ):
        profile.context.intended_fields = ["marine biology"]
        profile.context.level = "bachelor"
        page = f"{W}/research/biology-labs"
        target = f"{W}/research/biology-labs/marine-biology-bsc"
        pages = {
            page: hub_html("Laboratories", (target, "Bachelor of Science in Marine Biology")),
            target: program_html("Bachelor of Science in Marine Biology"),
        }
        trace, site = await _run(
            tmp_path, profile, monkeypatch, pages=pages, seeds={"program_page": page}, on=True
        )
        assert page in site.requested and target not in site.requested
        assert trace.refused_hub_links == []

    async def test_a_hub_read_again_is_not_followed_again(self, tmp_path, geology, monkeypatch):
        """§8.6: the confirm stage refuses the hub and follows it; the walker reads it again."""
        first, second = f"{W}/find/geology/a.html", f"{W}/find/geology/b.html"
        pages = {
            HUB: hub_html(
                "Geology",
                ("/find/geology/a.html", "Geology overview a"),
                ("/find/geology/b.html", "Geology overview b"),
            ),
            first: hub_html("Geology overview a"),
            second: hub_html("Geology overview b"),
            CATALOGUE: catalogue_html(("/find/geology.html", "Geology study options")),
        }
        seeds = {"program_page": HUB, "program_catalog": CATALOGUE}
        trace, site = await _run(tmp_path, geology, monkeypatch, pages=pages, seeds=seeds, on=True)
        outcomes = [(row["url"], row["outcome"]) for row in trace.walker["outcomes"]]
        assert (HUB, "reads_as_unknown") in outcomes, "the walker read the hub a second time"
        assert site.requested.count(first) == 1
        assert second not in site.requested, "a hub is followed once"
        assert trace.refused_hub_links == [(HUB, first, "reads as unknown, not a programme page")]

    async def test_the_walker_asks_no_follow_for_a_level_refusal_or_a_followed_page(
        self, tmp_path
    ) -> None:
        master = f"{W}/programmes/geology-advanced"
        overview = f"{W}/find/geology/overview.html"
        site = StubSite(
            {
                master: program_html("Master of Science in Geology"),
                HUB: hub_html("Geology"),
                overview: hub_html("Geology overview"),
            }
        )
        asked: list[str] = []

        async def follow(hub: str, html: str, page: PageClassification) -> str | None:
            asked.append(hub)
            return overview

        async with Fetcher(tmp_path / "c", offline=True) as fetcher:
            site.install(fetcher)
            walker = CatalogWalker(
                fetcher=fetcher, domain=DOMAIN, degree="bachelor", fields=FIELDS, follow=follow
            )
            walk = CatalogWalk(catalogue_url=CATALOGUE)
            await walker._read_lead(WalkerLink(master, "Geology advanced", 8, "html"), walk)
            assert asked == [], "a page refused on its level is no hub"
            await walker._read_lead(WalkerLink(HUB, "Geology overview", 16, "html"), walk)
        assert asked == [HUB], "the followed page asked nothing"
        assert (overview, "hub_link_unknown") in walk.outcomes
        assert walk.hub_links == [(HUB, overview, "reads as unknown, not a programme page")]


# --- 4. the link filters -------------------------------------------------------------


class TestLinkFilters:
    REFUSED = (
        ("https://www.other-uni.edu/geology/bachelor", "Bachelor of Science in Geology"),
        ("/find/geology/advanced.html", "Master of Science in Geology"),
        ("/find/geology/msc-geology", "Geology advanced degree"),
        ("/news/geology-field-trip", "Geology field trip report"),
        ("/find/undergraduate.html", "Undergraduate study"),
        ("/find/geology/x.html", "Geology"),
    )

    def _lead(self, *links: tuple[str, str], skip: tuple[str, ...] = ()) -> WalkerLink | None:
        return refused_hub_lead(
            hub_html("Geology", *links), HUB, HUB, DOMAIN, (), "bachelor", FIELDS, skip
        )

    def test_none_of_the_refused_links_is_read(self) -> None:
        assert self._lead(*self.REFUSED) is None

    def test_a_kept_link_beside_them_is_the_one(self) -> None:
        lead = self._lead(*self.REFUSED, ("/study/geology-degrees.html", "Geology degree options"))
        assert lead is not None and lead.url == f"{W}/study/geology-degrees.html"

    def test_a_link_already_read_or_queued_is_skipped(self) -> None:
        links = (
            ("/find/geology/undergraduate.html", "Undergraduate study"),
            ("/about/school-of-geology.html", "School of Geology"),
        )
        assert self._lead(*links).url == CHILD  # type: ignore[union-attr]
        assert self._lead(*links, skip=(CHILD,)).url == SCHOOL  # type: ignore[union-attr]
        assert self._lead(*links, skip=(CHILD, SCHOOL)) is None

    async def test_a_link_read_by_an_earlier_follow_is_not_read_twice(
        self, tmp_path, geology, monkeypatch
    ):
        first, second = f"{W}/programmes/geology-a", f"{W}/programmes/geology-b"
        shared, other = f"{W}/study/geology-options", f"{W}/study/geology-more"
        pages = {
            f"{W}/robots.txt": f"Sitemap: {W}/sitemap.xml\n",
            f"{W}/sitemap.xml": sitemap_xml(first, second),
            first: hub_html("Geology A", (shared, "Geology study options")),
            second: hub_html(
                "Geology B", (shared, "Geology study options"), (other, "More geology options")
            ),
        }
        trace, site = await _run(tmp_path, geology, monkeypatch, pages=pages, on=True)
        assert site.requested.count(shared) == 1
        assert [link for _hub, link, _verdict in trace.refused_hub_links] == [shared, other]


# --- 5. order and cap ----------------------------------------------------------------


def _hubs(n: int) -> dict[str, bytes | str]:
    names = "abcdefgh"[:n]
    hubs = [f"{W}/programmes/geology-{x}" for x in names]
    pages: dict[str, bytes | str] = {
        f"{W}/robots.txt": f"Sitemap: {W}/sitemap.xml\n",
        f"{W}/sitemap.xml": sitemap_xml(*hubs),
    }
    for x, hub in zip(names, hubs, strict=True):
        pages[hub] = hub_html(f"Geology {x}", (f"{hub}/overview", f"Geology {x} overview"))
        pages[f"{hub}/overview"] = hub_html(f"Geology {x} overview")
    return pages


class TestOrderAndCap:
    def test_a_child_outranks_a_higher_scored_link(self) -> None:
        html = _confirm_pages()[HUB]
        assert isinstance(html, str)
        lead = refused_hub_lead(html, HUB, HUB, DOMAIN, (), "bachelor", FIELDS, ())
        assert lead is not None and lead.url == CHILD
        school = catalog_walker.score_link(SCHOOL, "School of Geology", "bachelor", FIELDS)
        assert school is not None and school > lead.score

    def test_equal_children_are_ordered_by_score_then_url(self) -> None:
        html = hub_html(
            "Geology",
            ("/find/geology/b.html", "Geology studies b"),
            ("/find/geology/a.html", "Geology studies a"),
            ("/find/geology/bachelor.html", "Geology bachelor studies"),
        )
        lead = refused_hub_lead(html, HUB, HUB, DOMAIN, (), "bachelor", FIELDS, ())
        assert lead is not None and lead.url == f"{W}/find/geology/bachelor.html"
        lead = refused_hub_lead(
            html, HUB, HUB, DOMAIN, (), "bachelor", FIELDS, (f"{W}/find/geology/bachelor.html",)
        )
        assert lead is not None and lead.url == f"{W}/find/geology/a.html"

    async def test_four_hubs_make_three_follows(self, tmp_path, geology, monkeypatch):
        trace, site = await _run(tmp_path, geology, monkeypatch, pages=_hubs(4), on=True)
        assert live_discovery.FOLLOW_REFUSED_HUB_LINK_CAP == 3
        assert [hub for hub, _link, _verdict in trace.refused_hub_links] == [
            f"{W}/programmes/geology-{x}" for x in "abc"
        ]
        assert f"{W}/programmes/geology-d" in site.requested
        assert f"{W}/programmes/geology-d/overview" not in site.requested

    @pytest.mark.parametrize("by", ["sitemap", "seed", "follow"])
    async def test_no_follow_once_a_programme_page_is_confirmed(
        self, tmp_path, geology, monkeypatch, by
    ):
        pages = _hubs(2)
        first, second = f"{W}/programmes/geology-a", f"{W}/programmes/geology-b"
        seeds: dict[str, str] | None = None
        if by == "sitemap":
            pages[f"{W}/sitemap.xml"] = sitemap_xml(f"{W}/programmes/geology", first, second)
            pages[f"{W}/programmes/geology"] = program_html("Bachelor of Science in Geology")
        elif by == "seed":
            seeds = {"program_page": f"{W}/bachelor/geology-programme"}
            pages[seeds["program_page"]] = program_html("Bachelor of Science in Geology")
        else:
            pages[f"{first}/overview"] = program_html("Bachelor of Science in Geology")
        trace, site = await _run(tmp_path, geology, monkeypatch, pages=pages, seeds=seeds, on=True)
        assert second in site.requested, "the second hub was read and refused"
        assert f"{second}/overview" not in site.requested
        if by == "follow":
            assert trace.refused_hub_links == [(first, f"{first}/overview", "confirmed")]
            assert trace.selected["program_page"] == [f"{first}/overview"]
        else:
            assert trace.refused_hub_links == []
            assert f"{first}/overview" not in site.requested


# --- 6. a refused follow and a spent budget ------------------------------------------


def _allow_all(url: str, **_kwargs: Any) -> Any:
    from app.adapters.network_policy import check_url as real

    def resolve(host: str, port: int, **_kw: Any) -> list[Any]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ]

    return real(url, resolver=resolve)


class TestRefusedFollow:
    @pytest.mark.parametrize("refusal", ["http-403", "robots"])
    async def test_a_refused_follow_costs_one_read_and_is_not_retried(
        self, tmp_path, geology, monkeypatch, refusal
    ):
        monkeypatch.setattr("app.adapters.fetching.check_url", _allow_all)
        monkeypatch.setattr(fetching, "CASE_READ_LEDGER", True)
        monkeypatch.setattr(live_discovery, "STAGE_BUDGETS", True)
        pages = _confirm_pages()
        # Requests reach the transport at the pinned address: count them by path.
        wire: list[str] = []
        child = "/find/geology/undergraduate.html"

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            wire.append(path)
            if path == "/robots.txt":
                body = "User-agent: *\n"
                if refusal == "robots":
                    body += "Disallow: /find/geology/\n"
                return httpx.Response(200, headers={"content-type": "text/plain"}, text=body)
            if path == child:
                return httpx.Response(403)
            page = pages.get(f"{W}{path}")
            if page is None:
                return httpx.Response(404)
            return httpx.Response(200, headers={"content-type": "text/html"}, text=str(page))

        async def discover(on: bool) -> DiscoveryTrace:
            monkeypatch.setattr(live_discovery, "FOLLOW_REFUSED_HUB_LINK", on)
            wire.clear()
            entry = {
                "name": "U",
                "country": "Testland",
                "city": "X",
                "homepage": HOME,
                "seeds": {"program_page": HUB},
            }
            registry = tmp_path / f"registry-{on}.json"
            registry.write_text(json.dumps([entry]))
            async with Fetcher(
                tmp_path / f"cache-{on}", delay_seconds=0.0, respect_robots=True
            ) as fetcher:
                fetcher._client = httpx.AsyncClient(
                    transport=httpx.MockTransport(handler), follow_redirects=False
                )
                adapter = LiveDiscoveryAdapter(fetcher, registry)
                adapter._search_provider = None
                adapter._search_provider_resolved = True
                await adapter.discover(geology)
            return adapter.traces[0]

        off = await discover(False)
        off_wire = list(wire)
        on = await discover(True)
        assert off.read_ledger is not None and on.read_ledger is not None
        assert on.stage_budget["reads"] == off.stage_budget["reads"] + 1
        if refusal == "http-403":
            assert wire.count(child) == 1, "one wire request, never retried"
            assert on.read_ledger.spent == off.read_ledger.spent + 1
            assert on.refused_hub_links == [(HUB, CHILD, "could not be read (http_error)")]
        else:
            assert child not in wire, "robots refuse it before any request"
            assert on.read_ledger.spent == off.read_ledger.spent
            assert on.refused_hub_links == [(HUB, CHILD, "could not be read (robots_disallowed)")]
        assert "/about/school-of-geology.html" not in wire, "no second link is tried"
        assert [path for path in wire if path != child] == off_wire

    async def test_a_spent_stage_budget_means_no_follow(self, tmp_path, geology, monkeypatch):
        """The hub is the case's one candidate read; with a read cap of one, it spends it."""
        pages, seeds = _confirm_pages(), {"program_page": HUB}
        monkeypatch.setattr(live_discovery, "DISCOVERY_READ_CAP", 1)
        off, off_site = await _run(
            tmp_path / "off", geology, monkeypatch, pages=pages, seeds=seeds, on=False
        )
        assert off_site.requested[-1] == HUB
        assert off.stage_budget["stopped_by"] == "read_cap"
        trace, site = await _run(
            tmp_path / "on", geology, monkeypatch, pages=pages, seeds=seeds, on=True
        )
        assert site.requested == off_site.requested
        assert trace.refused_hub_links == []
        assert _serialised(trace) == _serialised(off)


# --- 7. the budget tests, and R2b / SP-1, with the flag off and on --------------------

BUDGET_TESTS = (
    "tests/test_case_read_ledger.py",
    "tests/test_stage_budgets.py",
    "tests/test_case_time_budget.py",
)
CONFIRM_TESTS = ("tests/test_subject_title_shapes.py", "tests/test_subpage_head.py")


def _pytest(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", *args],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("arm", ["off", "on"])
def test_the_budget_tests_pass_with_the_flag_off_and_on(arm: str) -> None:
    """The 60-read ledger, the stage budgets and the 120 s case clock, unchanged."""
    plugin = [] if arm == "off" else ["-p", "tests._follow_refused_hub_link_on"]
    result = _pytest(*plugin, *BUDGET_TESTS)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert " passed" in result.stdout


def test_the_r2b_and_sp1_tests_pass_with_the_flag_on() -> None:
    result = _pytest("-p", "tests._follow_refused_hub_link_on", *CONFIRM_TESTS)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert " passed" in result.stdout


def test_the_on_plugin_switches_the_rule_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests import _follow_refused_hub_link_on

    monkeypatch.setattr(live_discovery, "FOLLOW_REFUSED_HUB_LINK", False)
    _follow_refused_hub_link_on.pytest_configure(None)
    assert live_discovery.FOLLOW_REFUSED_HUB_LINK is True


# --- 8. the default, the harness flag, and the demo ---------------------------------


def test_on_by_default() -> None:
    assert live_discovery.FOLLOW_REFUSED_HUB_LINK is True  # on since the 2026-10-25 FRH re-run (§8.6)
    assert live_discovery.FOLLOW_REFUSED_HUB_LINK_CAP == 3
    assert DiscoveryTrace(institution="U", domain=DOMAIN).as_dict().get("refused_hub_links") is None


def test_the_flag_is_a_negatable_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_benchmark_rule_negations import _parent

    assert live.NEGATABLE_RULES["follow-refused-hub-link"] == (
        ("app.adapters.discovery.live_discovery", "FOLLOW_REFUSED_HUB_LINK"),
    )
    assert "follow-refused-hub-link" not in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--follow-refused-hub-link")
    assert "--follow-refused-hub-link" in commands[0]


def test_the_child_switches_the_rule_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):  # type: ignore[no-untyped-def]
        seen["on"] = live_discovery.FOLLOW_REFUSED_HUB_LINK

    monkeypatch.setattr(live_discovery, "FOLLOW_REFUSED_HUB_LINK", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--follow-refused-hub-link"])
    live.main()
    assert seen == {"on": True}
