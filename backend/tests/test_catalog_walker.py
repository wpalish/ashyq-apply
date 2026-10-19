"""CC-1: a course is never a programme lead (``COURSE_LEAD_GUARD``).

MISS_STAGES_2026-10-19 §3.3. A catalogue or listing links its individual
courses beside its programmes. iitd's ``all-courses`` listing (dev3) queued
``col100-…``, ``col703-…`` and ``col863-…`` as recovery follow-ups ahead of the
ranked results and spent three of the four checks between the gold and the read
cap. On: ``catalog_walker.score_link`` — shared by the walker and recovery's
listing follow-up — hard-rejects a link whose label or last slug starts with a
course code (2-4 letters directly followed by 3-4 digits), or whose path has a
``course``/``courses`` segment followed by a course identifier or ``view``.
A ``/courses/<programme-slug>/`` path is never a course.

Offline and synthetic: no university's page, label or capture is used.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import (
    CatalogWalker,
    WalkerLink,
    _drop_outcome,
    is_course_link,
    score_link,
)
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.adapters.search.retrieval import RankedCandidate
from evaluation.research import live
from tests.test_live_discovery import StubSite, program_html

BACKEND = Path(__file__).resolve().parents[1]
CS = ["computer science"]
HOST = "https://www.uni.example"


@pytest.fixture(params=[False, True], ids=["off", "on"])
def cc1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "COURSE_LEAD_GUARD", request.param)
    return request.param


@pytest.fixture
def cc1_on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "COURSE_LEAD_GUARD", True)


def test_the_rule_is_on_by_default() -> None:
    # On since the 2026-10-19 replay (dev3 iitd missed -> hit, no hit lost).
    assert live_discovery.COURSE_LEAD_GUARD is True


# --- the pattern ------------------------------------------------------------

COURSE_LABELS = [
    "COL100 Introduction to Computer Science",
    "CSL102 Introduction to Computer Science",
    "COMP1511 Programming Fundamentals",
    "INF1000 Introduksjon til programmering",  # Norwegian
    "MAT1100 Kalkulus",
    "BI101 Biologia generale",  # Italian, two letters
    "INFO2001: Algorithmen und Datenstrukturen",  # German, trailing colon
    "(CS2040) Data Structures and Algorithms",
]

PROGRAMME_LABELS = [
    "Computer Science",
    "S1-INF Informatika (Sarjana)",  # one digit: a programme code
    "6999 Computing and Data Science",  # digits only
    "3778 - Bachelor Computer Science",
    "BSc Computer Science",
    "Licenciatura en Ingeniería Informática",
    "Bachelor of Technology in Computer Science and Engineering",
    "Informatik B.Sc. 2027",
    "MSc 2027 Computer Science",  # a space separates letters from digits
]


@pytest.mark.parametrize("label", COURSE_LABELS)
def test_a_label_that_starts_with_a_course_code_is_a_course(label) -> None:
    assert is_course_link(f"{HOST}/study/programmes/x", label)


@pytest.mark.parametrize("label", PROGRAMME_LABELS)
def test_a_programme_label_is_no_course(label) -> None:
    assert not is_course_link(f"{HOST}/study/programmes/x", label)


@pytest.mark.parametrize(
    "path",
    [
        "/study/course/294207/",
        "/courses/view",
        "/en/courses/view.php",
        "/course/CS2040",
        "/academics/courses/col100-introduction-to-computer-science",
        "/catalog/col703-logic-for-computer-science",
        "/kurs/inf1000-introduksjon",  # last slug starts with a code, any language
        "/courses/comp1511/",
    ],
)
def test_a_course_path_is_a_course(path) -> None:
    assert is_course_link(f"{HOST}{path}", "Introduction to the subject")


@pytest.mark.parametrize(
    "path",
    [
        "/courses/undergraduate/courses/computer-science/",
        "/study/courses/undergraduate/computing-beng",
        "/study/courses/undergraduate/2027/computing-beng",
        "/courses/2027/computer-science",  # a year after courses is an intake
        "/programmes/s1-informatika",
        "/en/study/bachelor/6999-computing-and-data-science",
        "/study/courses",
        "/course-finder/computer-science",
        "/undergraduate/2027/computing-beng",
        "/b-tech-program",
    ],
)
def test_a_programme_path_is_no_course(path) -> None:
    assert not is_course_link(f"{HOST}{path}", "Computer Science programme")


def test_the_course_query_is_read_from_the_path_not_the_query() -> None:
    # ``/courses/view?prz_kod=…``: ``view`` is the identifier; the query is not read.
    assert is_course_link(f"{HOST}/courses/view?prz_kod=1000-INF", "Programowanie obiektowe")
    assert not is_course_link(f"{HOST}/courses?code=COL100", "All courses on offer")


# --- score_link (the ticket's table) ----------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "COL100 Introduction to Computer Science",
        "CSL102 Introduction to Computer Science",
        "COMP1511 Computer Science fundamentals",
    ],
)
def test_score_link_rejects_a_course_label_only_on(cc1, label) -> None:
    value = score_link(f"{HOST}/study/programmes/x", label, "bachelor", CS)
    assert (value is None) is cc1


@pytest.mark.parametrize(
    "label",
    [
        "Computer Science",
        "S1-INF Informatika (Sarjana)",
        "6999 Computing and Data Science",
        "3778 - Bachelor Computer Science",
    ],
)
def test_score_link_scores_a_programme_label_either_way(cc1, label) -> None:
    url = f"{HOST}/study/programmes/x"
    assert score_link(url, label, "bachelor", CS) is not None


@pytest.mark.parametrize("path", ["/study/course/294207/", "/en/courses/view.php"])
def test_score_link_rejects_a_course_path_only_on(cc1, path) -> None:
    value = score_link(f"{HOST}{path}", "Computer Science foundations", "bachelor", CS)
    assert (value is None) is cc1


def test_score_link_rejects_courses_view_either_way(cc1) -> None:
    # ``/courses/view`` is already on discovery's exclusion list; CC-1 agrees.
    url = f"{HOST}/courses/view"
    assert score_link(url, "Computer Science foundations", "bachelor", CS) is None
    assert is_course_link(url, "Computer Science foundations")


@pytest.mark.parametrize(
    "path",
    [
        "/courses/undergraduate/courses/computer-science/",
        "/study/courses/undergraduate/computing-beng",
    ],
)
def test_score_link_leaves_a_courses_programme_path_alone(monkeypatch, path) -> None:
    url = f"{HOST}{path}"
    monkeypatch.setattr(live_discovery, "COURSE_LEAD_GUARD", False)
    off = score_link(url, "Computer Science", "bachelor", CS)
    monkeypatch.setattr(live_discovery, "COURSE_LEAD_GUARD", True)
    on = score_link(url, "Computer Science", "bachelor", CS)
    assert off is not None
    assert on == off


def test_the_drop_outcome_names_a_course_only_on(cc1) -> None:
    url = f"{HOST}/academics/courses/col100-introduction"
    expected = "course_page" if cc1 else "degree_level_mismatch"
    assert _drop_outcome(url, "COL100 Introduction to Computer Science") == expected


# --- the walker -------------------------------------------------------------


def _walker() -> CatalogWalker:
    return CatalogWalker(
        fetcher=None,  # type: ignore[arg-type]
        domain="uni.example",
        degree="bachelor",
        fields=list(CS),
    )


def _link(url: str, label: str) -> WalkerLink:
    return WalkerLink(url=url, label=label, score=0, source="html")


def test_the_walker_queues_no_course_ahead_of_the_programme_only_on(cc1) -> None:
    programme = f"{HOST}/study/undergraduate/bachelor-computer-science"
    courses = [
        f"{HOST}/academics/courses/col100-introduction-to-computer-science",
        f"{HOST}/academics/courses/col703-logic-for-computer-science",
        f"{HOST}/academics/courses/col863-topics-in-computer-science",
    ]
    links = [_link(url, f"COL{url.split('col')[1][:3]} Computer Science course") for url in courses]
    links.append(_link(programme, "Bachelor of Technology in Computer Science"))
    outcomes: list[tuple[str, str]] = []
    scored = _walker()._score(links, outcomes, "www.uni.example")
    urls = [link.url for link in scored]
    assert programme in urls
    if cc1:
        assert urls == [programme]
        assert sorted(outcomes) == sorted((url, "course_page") for url in courses)
    else:
        assert set(courses) <= set(urls)
        assert outcomes == []


# --- recovery's listing follow-up (iitd's shape) ----------------------------

LISTING = f"{HOST}/academics/all-courses"
GOLD = f"{HOST}/b-tech-program"
COURSES = [
    f"{HOST}/academics/col100-introduction-to-computer-science",
    f"{HOST}/academics/col703-logic-for-computer-science",
    f"{HOST}/academics/col863-special-topics-in-computer-science",
]


def _listing_html() -> str:
    items = "".join(
        f"<li><a href='{url}'>COL{url.split('/col')[1][:3]} "
        f"{url.split('/col')[1][4:].replace('-', ' ').title()}</a></li>"
        for url in COURSES
    )
    return (
        "<html><head><title>All courses | Department</title></head><body><main>"
        "<h1>All courses</h1><p>The courses the department offers, by code.</p>"
        f"<ul>{items}</ul></main></body></html>"
    )


def _course_html(code: str) -> str:
    return (
        f"<html><head><title>{code} | Department</title></head><body><main>"
        f"<h1>{code}</h1><p>Credits: 4. Lectures, tutorials and a lab.</p>"
        "</main></body></html>"
    )


async def _recover(tmp_path, profile, pages, leads):
    profile.context.intended_fields = list(CS)
    site = StubSite(pages)
    trace = DiscoveryTrace(institution="U", domain="uni.example", country="India")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(leads, found, trace, profile)
    return found, trace, site.requested


@pytest.mark.asyncio
async def test_recovery_reads_no_course_follow_up_only_on(tmp_path, profile, cc1) -> None:
    pages: dict[str, bytes | str] = {
        LISTING: _listing_html(),
        GOLD: program_html("Bachelor of Technology in Computer Science"),
    }
    for url in COURSES:
        pages[url] = _course_html(url.split("/")[-1][:6].upper())
    leads = [
        RankedCandidate(LISTING, "All courses", 2.0, "fake"),
        RankedCandidate(GOLD, "B.Tech Computer Science", 1.0, "fake"),
    ]
    found, _trace, requested = await _recover(tmp_path, profile, pages, leads)
    assert requested[0] == LISTING
    followed = [url for url in requested if url in COURSES]
    if cc1:
        assert followed == []
        assert GOLD in requested
        assert found == [GOLD]
    else:
        # Off: the listing's course links are read as follow-ups ahead of the gold.
        assert followed
        if GOLD in requested:
            assert requested.index(followed[0]) < requested.index(GOLD)


# --- the harness ------------------------------------------------------------


def test_harness_exposes_forwards_and_negates_the_flag(monkeypatch, tmp_path) -> None:
    from tests.test_benchmark_rule_negations import _parent

    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--course-lead-guard" in result.stdout
    assert "--no-course-lead-guard" in result.stdout
    assert live.NEGATABLE_RULES["course-lead-guard"] == (
        ("app.adapters.discovery.live_discovery", "COURSE_LEAD_GUARD"),
    )
    assert "course-lead-guard" not in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--course-lead-guard")
    assert "--course-lead-guard" in commands[0]


def test_the_child_switches_the_rule_on(monkeypatch, tmp_path) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["cc1"] = live_discovery.COURSE_LEAD_GUARD

    monkeypatch.setattr(live_discovery, "COURSE_LEAD_GUARD", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "iitd", "--out", str(tmp_path / "u.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--course-lead-guard"])
    live.main()
    assert seen == {"cc1": True}
