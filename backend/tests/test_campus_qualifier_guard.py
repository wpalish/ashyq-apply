"""DC-1 (``CAMPUS_QUALIFIER_GUARD``): a domestic second campus the site's own URLs name.

TRACK_B_2026-10-26 §1: on the Exa and Tavily stores ubc confirmed UBC Okanagan's
department page whenever ``you.ubc.ca`` could not be read. CG-1 refuses only a
campus abroad. DC-1 learns campus places from the site's own URLs - two results
on one host and parent path whose last segments differ in one token, the
institution's city against another word - and refuses a lead that names such a
place in its host, URL or head, or in its text when the text never names the city.

Offline: every page and URL is written for the test; no site is named.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    OTHER_CAMPUS_VERDICT,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    campus_places,
    other_campus_named,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, program_html

BACKEND = Path(__file__).resolve().parents[1]
CITY = "Riverton"
TWINS = [
    "https://apply.uni.example/programs/computer-science-riverton-bsc/",
    "https://apply.uni.example/programs/computer-science-lakeside-bsc/",
]
LAKESIDE_DEPT = "https://cs.ls.uni.example/undergraduate/computer-science"
LAKESIDE_CAL = "https://lakeside.calendar.uni.example/science/computer-science-bsc"
RIVERTON = "https://www.uni.example/study/computer-science-bsc"


def lakeside_page() -> str:
    """A programme page of the other campus that never names the city."""
    return program_html("BSc Computer Science").replace(
        "<h2>Entry requirements</h2>",
        "<p>Study Computer Science at UNI Lakeside, on the Lakeside campus.</p>"
        "<h2>Entry requirements</h2>",
    )


def test_campus_places_come_from_one_token_city_twins_only() -> None:
    assert campus_places(TWINS, CITY) == frozenset({"lakeside"})
    assert campus_places(TWINS, "") == frozenset()
    assert campus_places(TWINS[:1], CITY) == frozenset()
    # Two tokens differ: not a twin. Another parent path: not a twin.
    assert campus_places([TWINS[0], TWINS[0].replace("riverton-bsc", "lakeside-ba")], CITY) == (
        frozenset()
    )
    assert campus_places([TWINS[0], TWINS[1].replace("/programs/", "/other/")], CITY) == (
        frozenset()
    )
    # A number is a year or a code, never a place.
    assert campus_places([TWINS[0], TWINS[0].replace("riverton", "2027")], CITY) == frozenset()
    # Neither side names the city: no place.
    assert (
        campus_places(
            [TWINS[0].replace("riverton", "north"), TWINS[0].replace("riverton", "south")], CITY
        )
        == frozenset()
    )


def test_other_campus_named_reads_host_url_head_then_text() -> None:
    places = frozenset({"lakeside"})
    plain = classify_page(url=RIVERTON, html=program_html("BSc Computer Science"))
    assert other_campus_named(plain, LAKESIDE_CAL, "", places, CITY) == "lakeside"
    assert other_campus_named(plain, RIVERTON, "a page on the Lakeside campus", places, CITY) == (
        "lakeside"
    )
    # The text names the city too: the page may serve both campuses.
    text = "Lakeside and Riverton campuses"
    assert other_campus_named(plain, RIVERTON, text, places, CITY) is None
    assert other_campus_named(plain, RIVERTON, "nothing of the kind", places, CITY) is None
    assert other_campus_named(plain, LAKESIDE_CAL, "", frozenset(), CITY) is None
    headed = classify_page(url=RIVERTON, html=program_html("BSc Computer Science (Lakeside)"))
    assert other_campus_named(headed, RIVERTON, "Riverton", places, CITY) == "lakeside"


async def _recover(tmp_path, profile, pages, leads, *, city=CITY, results=TWINS):
    profile.context.intended_fields = ["computer science"]
    site = StubSite(pages)
    trace = DiscoveryTrace(institution="U", domain="www.uni.example", country="Canada", city=city)
    trace.record_search_results([("field_and_degree", results)])
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(leads, found, trace, profile)
    return found, trace


@pytest.fixture(params=[False, True], ids=["off", "on"])
def dc1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "CAMPUS_QUALIFIER_GUARD", request.param)
    return request.param


def test_dc1_is_off_by_default() -> None:
    assert live_discovery.CAMPUS_QUALIFIER_GUARD is False


@pytest.mark.asyncio
async def test_recovery_refuses_the_other_campus_only_on(tmp_path, profile, dc1) -> None:
    pages = {
        LAKESIDE_DEPT: lakeside_page(),
        LAKESIDE_CAL: program_html("BSc Computer Science"),
        RIVERTON: program_html("BSc Computer Science"),
    }
    leads = [
        RankedCandidate(LAKESIDE_DEPT, "Computer Science", 3.0, "fake"),
        RankedCandidate(LAKESIDE_CAL, "Computer Science", 2.0, "fake"),
        RankedCandidate(RIVERTON, "Computer Science", 1.0, "fake"),
    ]
    found, trace = await _recover(tmp_path, profile, pages, leads)
    if dc1:
        assert found == [RIVERTON]
        verdicts = dict(trace.rejected)
        assert verdicts[LAKESIDE_DEPT] == f"{OTHER_CAMPUS_VERDICT} (lakeside), not {CITY}"
        assert verdicts[LAKESIDE_CAL] == f"{OTHER_CAMPUS_VERDICT} (lakeside), not {CITY}"
    else:
        # No stage budget here, so recovery fills every slot, the other campus first.
        assert found[:2] == [LAKESIDE_DEPT, LAKESIDE_CAL]
        assert not any(OTHER_CAMPUS_VERDICT in why for _url, why in trace.rejected)


@pytest.mark.asyncio
async def test_without_a_city_or_a_twin_pair_nothing_changes(tmp_path, profile, dc1) -> None:
    pages = {LAKESIDE_DEPT: lakeside_page()}
    leads = [RankedCandidate(LAKESIDE_DEPT, "Computer Science", 1.0, "fake")]
    found, _trace = await _recover(tmp_path, profile, pages, leads, city="")
    assert found == [LAKESIDE_DEPT]
    found, _trace = await _recover(tmp_path, profile, pages, leads, results=TWINS[:1])
    assert found == [LAKESIDE_DEPT]


def test_dc1_the_harness_flag_and_its_off_form(tmp_path, monkeypatch) -> None:
    from evaluation.research import live

    assert live.NEGATABLE_RULES["campus-qualifier-guard"] == (
        ("app.adapters.discovery.live_discovery", "CAMPUS_QUALIFIER_GUARD"),
    )
    assert "campus-qualifier-guard" in live.DEFAULT_OFF_NEGATABLE
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--campus-qualifier-guard" in result.stdout
    assert "--no-campus-qualifier-guard" in result.stdout

    seen = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        seen.append(live_discovery.CAMPUS_QUALIFIER_GUARD)

    monkeypatch.setattr(live_discovery, "CAMPUS_QUALIFIER_GUARD", False)
    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    argv = ["live", "--live", "--child", "--case", "groningen", "--out", str(tmp_path / "o.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--campus-qualifier-guard"])
    live.main()
    assert seen == [True]


def test_dc1_the_parent_forwards_the_flag(tmp_path, monkeypatch) -> None:
    from evaluation.research import live
    from evaluation.research.schema import Observation

    argv = ["live", "--live", "--case", "groningen", "--out", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", [*argv, "--campus-qualifier-guard"])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--campus-qualifier-guard" in commands[0]
