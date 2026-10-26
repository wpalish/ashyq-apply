"""IM-1: a UK integrated master's is master level for programme confirmation.

Imperial lists ``/undergraduate/2027/mathematics-computer-science-meng`` beside
the BEng. ``degree_level_named`` read "undergraduate" before "meng", so a
bachelor computer-science request confirmed the MEng and every claim read from
it was scored out of scope (paired run 39098958849). Offline.
"""

from __future__ import annotations

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    PageCategory,
    _prefer_exact_field,
    categorise_url,
    degree_level_named,
    exact_field_slug,
    matches_degree,
    matches_field,
    names_integrated_master,
    names_other_degree_level,
    profile_rejects,
    url_names_integrated_master,
)
from app.adapters.page_classifier import PageClassification, PageType, classify_page

BASE = "https://www.imperial.ac.uk/study/courses/undergraduate/2027"
MENG = f"{BASE}/mathematics-computer-science-meng"
JOINT_BENG = f"{BASE}/mathematics-computer-science-beng"
GOLD = f"{BASE}/computing-beng"
FIELDS = ["Computer Science"]


def _programme(title: str, subject: str, level: str | None = "bachelor") -> PageClassification:
    return PageClassification(
        PageType.PROGRAM_DETAIL, 0.75, [], title, subject=subject, degree_level=level
    )


def _meng_html() -> str:
    return (
        "<html><head><title>Mathematics and Computer Science MEng | Study | Imperial College"
        " London</title></head><body><main><h1>Mathematics and Computer Science</h1>"
        "<p>MEng, 4 years full-time. Undergraduate course starting October 2027.</p>"
        "<h2>Entry requirements</h2><p>A-level: A*A*A including Mathematics.</p>"
        "<h2>Structure</h2><p>Year 1 to Year 4 modules; 240 credits.</p></main></body></html>"
    )


@pytest.mark.parametrize(
    "url",
    [
        MENG,
        f"{BASE}/mathematics-computer-science-ai-meng",
        "https://www.ucl.ac.uk/prospective-students/undergraduate/degrees/physics-msci",
        "https://www.example.ac.uk/undergraduate/courses/mathematics-mmath/",
        "https://www.example.ac.uk/undergraduate/physics-mphys",
        "https://www.example.ac.uk/undergraduate/chemistry-mchem",
        "https://www.example.ac.uk/undergraduate/integrated-masters/computing",
    ],
)
def test_url_naming_an_integrated_master_reads_master(url):
    assert url_names_integrated_master(url)
    assert degree_level_named(url) == "master"
    assert names_other_degree_level(url, "bachelor")


@pytest.mark.parametrize(
    "url",
    [
        JOINT_BENG,
        GOLD,
        "https://www.example.ac.uk/undergraduate/physics-bsc-msci",
        "https://www.imperial.ac.uk/study/apply/undergraduate/entry-requirements",
    ],
)
def test_bachelor_and_neutral_urls_keep_their_reading(url):
    assert not url_names_integrated_master(url)
    assert not names_other_degree_level(url, "bachelor")


def test_flag_off_restores_the_old_reading(monkeypatch):
    monkeypatch.setattr(live_discovery, "INTEGRATED_MASTERS_LEVEL", False)
    # IM-1 alone: CQ-1 and CH-1 would refuse this joint maths-and-CS head on their own grounds.
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_COMBINATION_HEAD", False)
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", False)
    assert degree_level_named(MENG) == "bachelor"
    page = _programme("Mathematics and Computer Science MEng | Imperial", "Computer Science")
    assert profile_rejects(page, "bachelor", FIELDS, url=MENG) is None


def test_meng_title_names_an_integrated_master():
    assert names_integrated_master("Mathematics and Computer Science MEng")
    assert names_integrated_master("Computer Science (Integrated Master's)")
    assert names_integrated_master("Physics MSci")
    assert not names_integrated_master("Physics BSc/MSci")
    assert not names_integrated_master("Computing BEng")
    assert not names_integrated_master("Mathematics and Computer Science")


def test_the_imperial_meng_page_is_refused_for_a_bachelor_request():
    page = classify_page(url=MENG, html=_meng_html())
    reason = profile_rejects(page, "bachelor", FIELDS, url=MENG)
    assert reason is not None
    assert "master" in reason


def test_meng_title_is_refused_even_without_a_degree_slug():
    url = "https://www.example.ac.uk/undergraduate/courses/computer-science"
    page = _programme("Computer Science MEng | Example University", "Computer Science")
    assert profile_rejects(page, "bachelor", FIELDS, url=url) == (
        "page names an integrated master's (master level), not bachelor"
    )


def test_a_page_naming_both_forms_is_kept():
    url = "https://www.example.ac.uk/undergraduate/courses/computer-science"
    page = _programme("Computer Science BSc/MEng | Example University", "Computer Science")
    assert profile_rejects(page, "bachelor", FIELDS, url=url) is None


def test_the_beng_beside_it_is_still_confirmed():
    page = _programme("Computing BEng | Study | Imperial College London", "Computing")
    assert profile_rejects(page, "bachelor", FIELDS, url=GOLD) is None


def test_uk_undergraduate_admissions_page_mentioning_meng_keeps_its_level():
    # The classifier's own reading is untouched: a general undergraduate
    # admissions page listing MEng courses is not turned into a master's page,
    # so the requirements reader does not refuse it on level.
    html = (
        "<html><head><title>Entry requirements | Undergraduate | Imperial</title></head>"
        "<body><main><h1>Undergraduate entry requirements</h1>"
        "<p>Our MEng, BEng and BSc courses ask for A-levels or the IB.</p>"
        "<h2>Admission requirements</h2><p>International qualifications.</p></main></body></html>"
    )
    url = "https://www.imperial.ac.uk/study/apply/undergraduate/entry-requirements"
    page = classify_page(url=url, html=html)
    assert page.degree_level != "master"
    assert page_classifier.degree_level_of("Our MEng, BEng and BSc courses") == "bachelor"
    assert not names_other_degree_level(url, "bachelor")


def test_master_request_is_not_changed():
    page = _programme("Computer Science MEng | Example", "Computer Science", level="master")
    url = "https://www.example.ac.uk/postgraduate/computer-science"
    assert profile_rejects(page, "master", FIELDS, url=url) is None


@pytest.mark.parametrize(
    ("url", "exact"),
    [
        (GOLD, True),
        (f"{BASE}/computer-science-bsc", True),
        ("https://www.ed.ac.uk/study/informatics_bsc", True),
        (JOINT_BENG, False),
        (f"{BASE}/mathematics-computer-science-ai-beng", False),
        (f"{BASE}/materials-science-beng", False),
    ],
)
def test_exact_field_slug(url, exact):
    assert exact_field_slug(url, FIELDS) is exact


def _sitemap_queue(urls: list[str]) -> list[tuple[int, str]]:
    """The sitemap stage's programme-page ranking (``keep`` + the final sort)."""
    ranked: list[tuple[int, str]] = []
    for url in urls:
        category, score = categorise_url(url)
        if category != PageCategory.PROGRAM_PAGE or names_other_degree_level(url, "bachelor"):
            continue
        score += matches_field(url, FIELDS) + matches_degree(url, "bachelor")
        if score > 0:
            ranked.append((score, url))
    ranked.sort(key=lambda pair: (-pair[0], len(pair[1])))
    return _prefer_exact_field(ranked, FIELDS)


def test_sitemap_queue_refuses_the_meng_and_heads_with_the_exact_field(monkeypatch):
    monkeypatch.setattr(live_discovery, "FIELD_SLUG_SCORING", True)
    queue = _sitemap_queue([JOINT_BENG, MENG, GOLD])
    urls = [url for _score, url in queue]
    assert MENG not in urls
    assert urls == [GOLD, JOINT_BENG]


def test_joint_title_is_not_preferred_over_the_exact_field_on_a_tie():
    # The exact-field URL is the longer one, so length alone would put the
    # joint programme first.
    exact = "https://www.example.ac.uk/undergraduate/courses/2027/full-time/computer-science-bsc"
    joint = "https://www.example.ac.uk/ug/mathematics-computer-science-bsc"
    ranked = sorted([(30, exact), (30, joint)], key=lambda pair: (-pair[0], len(pair[1])))
    assert ranked[0][1] == joint
    assert [url for _s, url in _prefer_exact_field(ranked, FIELDS)] == [exact, joint]


def test_a_higher_score_still_wins_over_an_exact_field():
    ranked = [(31, JOINT_BENG), (19, GOLD)]
    assert _prefer_exact_field(ranked, FIELDS) == ranked


def test_order_is_unchanged_without_an_exact_field_url():
    ranked = [(27, JOINT_BENG), (27, f"{BASE}/mathematics-computer-science-ai-beng")]
    assert _prefer_exact_field(ranked, FIELDS) == ranked
