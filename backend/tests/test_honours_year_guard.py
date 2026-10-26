"""HONS-1 (``HONOURS_YEAR_GUARD``): an honours year after a bachelor's is not a bachelor's.

LOOP_REPORT 2026-10-26 16:35: on the new default (fused1 store, DC-1 on) a
dev3 case confirmed the site's "Bachelor of Science (Honours)" plan - a
one-year programme entered after a completed bachelor's, which the site files
as postgraduate study - beside the gold. A "(Hons)" rule would refuse every
honours bachelor's entered from school (the UK's "BSc (Hons)"). HONS-1 refuses
a page only when its head names honours, its own content calls the study
postgraduate, and nothing in the document or its URL says undergraduate.

Offline: every page and URL is written for the test; no site is named.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    HONOURS_YEAR_VERDICT,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    honours_year_page,
    profile_rejects,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, program_html

BACKEND = Path(__file__).resolve().parents[1]
FIELDS = ["computer science"]
YEAR_URL = "https://handbook.uni.example/plan?code=CS-BSc%28Hons%29"
YEAR_TITLE = "Bachelor of Science (Honours) in Computer Science"
BACHELOR_URL = "https://www.uni.example/study/computer-science-bsc"
UK_URL = "https://www.college.example/courses/computer-science-bsc-hons"
UK_TITLE = "BSc (Hons) Computer Science"


def with_paragraph(name: str, paragraph: str, *, nav: str = "Home") -> str:
    """``program_html`` with one more paragraph in its main content."""
    return (
        program_html(name)
        .replace("<h2>Entry requirements</h2>", f"<p>{paragraph}</p><h2>Entry requirements</h2>")
        .replace(">Home</a>", f">{nav}</a>")
    )


def honours_year_html() -> str:
    return with_paragraph(
        YEAR_TITLE,
        "A further year of postgraduate study for graduates who hold a degree with a major "
        "in the subject, finished by a research project.",
    )


def uk_honours_html(nav: str = "Undergraduate courses") -> str:
    return with_paragraph(
        UK_TITLE,
        "Many of our graduates continue to postgraduate study or research.",
        nav=nav,
    )


def page_of(url: str, html: str):
    return classify_page(url=url, html=html)


@pytest.fixture(params=[False, True], ids=["off", "on"])
def hons1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "HONOURS_YEAR_GUARD", request.param)
    return request.param


def test_hons1_is_off_by_default() -> None:
    assert live_discovery.HONOURS_YEAR_GUARD is False


def test_both_pages_read_as_a_bachelor_programme() -> None:
    for url, html in ((YEAR_URL, honours_year_html()), (UK_URL, uk_honours_html())):
        page = page_of(url, html)
        assert page.page_type.value == "program_detail"
        assert page.degree_level == "bachelor"


def test_the_predicate_reads_head_content_and_the_whole_document() -> None:
    year = page_of(YEAR_URL, honours_year_html())
    assert honours_year_page(year, YEAR_URL, honours_year_html()) is True
    # Without the page as read nothing is known.
    assert honours_year_page(year, YEAR_URL, "") is False
    # An honours bachelor's that says undergraduate anywhere: in its menu, or in its URL.
    uk = page_of(UK_URL, uk_honours_html())
    assert honours_year_page(uk, UK_URL, uk_honours_html()) is False
    bare = uk_honours_html(nav="Home")
    routed = "https://www.college.example/study/undergraduate/computer-science-bsc-hons"
    assert honours_year_page(page_of(routed, bare), routed, bare) is False
    # The head does not name honours: a postgraduate word alone decides nothing.
    plain = with_paragraph("BSc Computer Science", "Postgraduate study follows the degree.")
    assert honours_year_page(page_of(BACHELOR_URL, plain), BACHELOR_URL, plain) is False
    # Honours in the head, no postgraduate word in the page's own content.
    quiet = with_paragraph(UK_TITLE, "A degree with a final-year dissertation.", nav="Home")
    assert honours_year_page(page_of(UK_URL, quiet), UK_URL, quiet) is False


def test_a_postgraduate_word_only_in_the_menu_is_not_the_page_content() -> None:
    menu = with_paragraph(UK_TITLE, "A degree with a final-year dissertation.", nav="Postgraduate")
    assert honours_year_page(page_of(UK_URL, menu), UK_URL, menu) is False


def test_profile_rejects_refuses_the_honours_year_only_on(hons1) -> None:
    html = honours_year_html()
    verdict = profile_rejects(page_of(YEAR_URL, html), "bachelor", FIELDS, url=YEAR_URL, html=html)
    assert verdict == (HONOURS_YEAR_VERDICT if hons1 else None)
    # Without ``html`` (every caller before HONS-1) nothing changes.
    assert profile_rejects(page_of(YEAR_URL, html), "bachelor", FIELDS, url=YEAR_URL) is None
    uk = uk_honours_html()
    assert profile_rejects(page_of(UK_URL, uk), "bachelor", FIELDS, url=UK_URL, html=uk) is None


def test_another_refusal_keeps_its_own_verdict(hons1) -> None:
    html = with_paragraph(
        "Bachelor of Science (Honours) in Geology",
        "A further year of postgraduate study for graduates.",
    )
    verdict = profile_rejects(page_of(YEAR_URL, html), "bachelor", FIELDS, url=YEAR_URL, html=html)
    assert verdict is not None
    assert verdict != HONOURS_YEAR_VERDICT


def test_hons1_the_verdict_string_is_pinned() -> None:
    assert HONOURS_YEAR_VERDICT == (
        "page names an honours year that follows a bachelor's (postgraduate), not bachelor"
    )


@pytest.mark.asyncio
async def test_recovery_reads_past_the_honours_year_only_on(tmp_path, profile, hons1) -> None:
    profile.context.intended_fields = FIELDS
    site = StubSite(
        {YEAR_URL: honours_year_html(), BACHELOR_URL: program_html("BSc Computer Science")}
    )
    trace = DiscoveryTrace(institution="U", domain="www.uni.example", country="New Zealand")
    leads = [
        RankedCandidate(YEAR_URL, YEAR_TITLE, 2.0, "fake"),
        RankedCandidate(BACHELOR_URL, "Computer Science", 1.0, "fake"),
    ]
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(leads, found, trace, profile)
    if hons1:
        assert found == [BACHELOR_URL]
        assert dict(trace.rejected)[YEAR_URL] == HONOURS_YEAR_VERDICT
    else:
        assert found[0] == YEAR_URL
        assert not any(HONOURS_YEAR_VERDICT in why for _url, why in trace.rejected)


def test_hons1_the_harness_flag_and_its_off_form(tmp_path, monkeypatch) -> None:
    from evaluation.research import live

    assert live.NEGATABLE_RULES["honours-year-guard"] == (
        ("app.adapters.discovery.live_discovery", "HONOURS_YEAR_GUARD"),
    )
    assert "honours-year-guard" in live.DEFAULT_OFF_NEGATABLE
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--honours-year-guard" in result.stdout
    assert "--no-honours-year-guard" in result.stdout

    seen = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        seen.append(live_discovery.HONOURS_YEAR_GUARD)

    monkeypatch.setattr(live_discovery, "HONOURS_YEAR_GUARD", False)
    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    argv = ["live", "--live", "--child", "--case", "groningen", "--out", str(tmp_path / "o.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--honours-year-guard"])
    live.main()
    assert seen == [True]


def test_hons1_the_parent_forwards_the_flag(tmp_path, monkeypatch) -> None:
    from evaluation.research import live
    from evaluation.research.schema import Observation

    argv = ["live", "--live", "--case", "groningen", "--out", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", [*argv, "--honours-year-guard"])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--honours-year-guard" in commands[0]
