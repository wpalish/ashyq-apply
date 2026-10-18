"""Plan rule SR-1: a programme URL earns the field bonus for whole slug words only.

Imperial's sitemap lists the gold ``/2027/computing-beng`` page, but it ranked
35 of 40 in the confirm queue: "science" scored as a substring of every
``*-science`` URL, "computer" missed "computing", and tuition-fee tables scored
as programme pages. Offline, with the pipeline's own sitemap ranking.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    PageCategory,
    categorise_url,
    matches_degree,
    matches_field,
    matches_field_text,
    names_other_degree_level,
    score_url,
)

BASE = "https://www.imperial.ac.uk"
GOLD = f"{BASE}/study/courses/undergraduate/2027/computing-beng"
IMPERIAL = [
    f"{BASE}/study/courses/undergraduate/2027/mathematics-computer-science-beng",
    f"{BASE}/study/courses/undergraduate/2027/mathematics-computer-science-ai-beng",
    f"{BASE}/study/courses/undergraduate/2027/tuition-fees---2027/"
    "group-7---mathematics-and-computer-science/standard-courses/home",
    f"{BASE}/study/courses/undergraduate/2027/tuition-fees---2027/"
    "group-7---mathematics-and-computer-science/standard-courses/overseas",
    f"{BASE}/study/courses/undergraduate/2027/materials-science-beng",
    f"{BASE}/study/courses/undergraduate/2027/biological-sciences-bsc",
    f"{BASE}/study/courses/undergraduate/2027/natural-sciences-bsc",
    GOLD,
]
FIELDS = ["Computer Science"]


@pytest.fixture
def sr1(monkeypatch):
    monkeypatch.setattr(live_discovery, "FIELD_SLUG_SCORING", True)


def _queue(urls: list[str]) -> list[tuple[int, str]]:
    """The sitemap stage's programme-page ranking (``keep`` + the final sort)."""
    ranked: list[tuple[int, str]] = []
    for url in urls:
        category, score = categorise_url(url)
        if category not in (PageCategory.PROGRAM_PAGE, PageCategory.PROGRAM_CATALOG):
            continue
        if names_other_degree_level(url, "bachelor"):
            continue
        score += matches_field(url, FIELDS) + matches_degree(url, "bachelor")
        if score > 0 and category == PageCategory.PROGRAM_PAGE:
            ranked.append((score, url))
    ranked.sort(key=lambda pair: (-pair[0], len(pair[1])))
    return ranked


def _scores(queue: list[tuple[int, str]]) -> dict[str, int]:
    return {url: score for score, url in queue}


SCIENCE = [u for u in IMPERIAL if u.endswith(("materials-science-beng", "-sciences-bsc"))]
MATHS_CS = [u for u in IMPERIAL if "mathematics-computer-science" in u and "/2027/m" in u]


def test_imperial_gold_heads_the_queue_with_sr1(sr1):
    queue = _queue(IMPERIAL)
    assert queue[0][1] == GOLD
    scores = _scores(queue)
    assert not any("tuition" in url for url in scores)
    assert all(scores[url] < scores[GOLD] for url in SCIENCE)
    assert all(scores[url] <= scores[GOLD] for url in MATHS_CS)


def test_imperial_queue_is_unchanged_with_sr1_off():
    # Off: the ranking the dev3 analysis measured (tuition tables 31, maths
    # and computer science 27, the gold tied with every *-science URL at 19).
    queue = _queue(IMPERIAL)
    assert [score for score, _url in queue] == [31, 31, 27, 27, 19, 19, 19, 19]
    assert "tuition-fees" in queue[0][1]
    scores = _scores(queue)
    assert all(scores[url] == scores[GOLD] for url in SCIENCE)


def test_generic_word_earns_nothing(sr1):
    assert matches_field(f"{BASE}/study/materials-science", FIELDS) == 0
    assert matches_field(f"{BASE}/departments/natural-sciences", FIELDS) == 0
    assert matches_field(f"{BASE}/study/computer-engineering", FIELDS) == 0


def test_materials_science_bonus_differs_by_flag(monkeypatch):
    url = f"{BASE}/study/materials-science"
    assert matches_field(url, FIELDS) == 8
    monkeypatch.setattr(live_discovery, "FIELD_SLUG_SCORING", True)
    assert matches_field(url, FIELDS) == 0


def test_phrase_and_whole_word_aliases_match(sr1):
    full = 16
    assert matches_field(f"{BASE}/study/mathematics-computer-science-beng", FIELDS) == full
    assert matches_field("https://www.rug.nl/bachelors/computing-science", FIELDS) == full
    assert matches_field(GOLD, FIELDS) == full
    assert matches_field("https://www.ed.ac.uk/study/informatics_bsc", FIELDS) == full
    assert matches_field("https://www.tum.example/studium/informatik", FIELDS) == full
    # Inside another word, an alias is not the field.
    assert matches_field("https://x.example/study/bioinformatics", FIELDS) == 0
    assert matches_field("https://x.example/wirtschaftsinformatik", FIELDS) == 0
    assert matches_field("https://x.example/study/computerscience", FIELDS) == 0


def test_fee_and_cost_pages_are_never_programme_pages(sr1):
    for url in (
        f"{BASE}/study/fees/undergraduate/computer-science",
        f"{BASE}/undergraduate/tuition-fees---2027/computing-beng",
        f"{BASE}/undergraduate/cost-of-living/computer-science",
        f"{BASE}/undergraduate/scholarship-guide/computer-science-bsc",
    ):
        assert score_url(url, PageCategory.PROGRAM_PAGE) == 0
        assert score_url(url, PageCategory.PROGRAM_CATALOG) == 0
    # A subject that only contains the word stays a programme page.
    assert score_url(f"{BASE}/undergraduate/cost-engineering-bsc", PageCategory.PROGRAM_PAGE) > 0


def test_degree_slug_tokens_are_title_filler(monkeypatch):
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
    assert not matches_field_text("Computing BEng", FIELDS)
    monkeypatch.setattr(live_discovery, "FIELD_SLUG_SCORING", True)
    assert matches_field_text("Computing BEng", FIELDS)
    assert matches_field_text("Computing MEng", FIELDS)
    assert not matches_field_text("Business Computing BEng", FIELDS)


def test_degree_slug_tokens_are_filler_under_localized_identity(monkeypatch):
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
    assert not matches_field_text("Computing BTech", FIELDS)
    monkeypatch.setattr(live_discovery, "FIELD_SLUG_SCORING", True)
    assert matches_field_text("Computing BTech", FIELDS)
