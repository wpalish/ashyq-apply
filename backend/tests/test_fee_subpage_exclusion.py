"""Plan v3 change #2(b): fee and entry-requirements sub-pages are never programme pages.

Imperial's sitemap queue held two ``tuition-fees---2027/group-7---…`` tables
(``program_page`` 11) and two ``entry-requirements---2027/…`` sub-pages (7)
level with or above the gold ``/2027/computing-beng`` (7); four of the first
seven confirm reads went to them (loss stages v3 2026-10-18 §3.1). Offline,
with the pipeline's own URL scoring.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    PageCategory,
    _is_entry_requirements_path,
    _prefer_exact_field,
    categorise_url,
    evidence_only_score,
    matches_degree,
    matches_field,
    names_other_degree_level,
    score_url,
)

BACKEND = Path(__file__).resolve().parents[1]
BASE = "https://www.imperial.ac.uk/study/courses/undergraduate/2027"
GOLD = f"{BASE}/computing-beng"
MATHS_CS = f"{BASE}/mathematics-computer-science-beng"
FEES = [
    f"{BASE}/tuition-fees---2027/group-7---mathematics-and-computer-science/standard-courses/home",
    f"{BASE}/tuition-fees---2027/group-7---mathematics-and-computer-science/"
    "standard-courses/overseas",
]
ENTRY = [
    f"{BASE}/entry-requirements---2027/mathematics-and-computer-science-for-ai",
    f"{BASE}/entry-requirements---2027/mathematics-and-computer-science-for-ai/"
    "standard-requirement",
]
IMPERIAL = [*FEES, *ENTRY, MATHS_CS, GOLD]
FIELDS = ["computer science"]


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(live_discovery, "FEE_SUBPAGE_EXCLUSION", True)


def _queue(urls: list[str]) -> list[str]:
    """The sitemap stage's programme-page queue (``keep`` + the confirm sort)."""
    ranked: list[tuple[int, str]] = []
    for url in urls:
        category, score = categorise_url(url)
        if category != PageCategory.PROGRAM_PAGE or names_other_degree_level(url, "bachelor"):
            continue
        ranked.append((score + matches_field(url, FIELDS) + matches_degree(url, "bachelor"), url))
    return [url for _score, url in _prefer_exact_field(sorted(ranked, reverse=True), FIELDS)]


def test_off_the_fee_and_entry_pages_outrank_the_gold(monkeypatch) -> None:
    # Pins the pre-#2b ranking: fee/entry sub-pages still score as programme pages.
    monkeypatch.setattr("app.adapters.discovery.live_discovery.FEE_SUBPAGE_EXCLUSION", False)
    assert live_discovery.FEE_SUBPAGE_EXCLUSION is False
    queue = _queue(IMPERIAL)
    assert queue.index(GOLD) > max(queue.index(url) for url in FEES)
    assert all(url in queue for url in ENTRY)
    assert score_url(FEES[0], PageCategory.PROGRAM_PAGE) == 11
    assert score_url(ENTRY[0], PageCategory.PROGRAM_PAGE) == 7


def test_on_the_fee_and_entry_pages_leave_the_programme_queue(on) -> None:
    # Only the two programme pages are left (the joint one first on its
    # field words; R2b reads the gold beside it), the gold at read 2 not ~7.
    queue = _queue(IMPERIAL)
    assert queue == [MATHS_CS, GOLD]
    for url in [*FEES, *ENTRY]:
        assert score_url(url, PageCategory.PROGRAM_PAGE) == 0
        assert score_url(url, PageCategory.PROGRAM_CATALOG) == 0


def test_on_they_keep_their_service_category(on) -> None:
    assert categorise_url(FEES[0])[0] == PageCategory.COSTS
    assert categorise_url(ENTRY[0])[0] == PageCategory.ADMISSIONS


def test_on_regardless_of_sr1_and_r3(monkeypatch, on) -> None:
    for sr1 in (False, True):
        monkeypatch.setattr(live_discovery, "FIELD_SLUG_SCORING", sr1)
        for url in [*FEES, *ENTRY]:
            assert score_url(url, PageCategory.PROGRAM_PAGE) == 0
    monkeypatch.setattr(live_discovery, "SITEMAP_KEEP_EVIDENCE_SUM", True)
    held = "https://uni.example/2027/entry-requirements---2027/computer-science-bachelor"
    assert evidence_only_score(held, FIELDS, "bachelor") == 0


def test_on_programme_pages_are_untouched(on) -> None:
    for url in (
        GOLD,
        MATHS_CS,
        "https://uni.example/study/bachelor/computer-science",
        "https://uni.example/programmes/cost-engineering-bsc",
        "https://uni.example/programmes/requirements-engineering-bsc",
    ):
        assert score_url(url, PageCategory.PROGRAM_PAGE) > 0, url


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/2027/entry-requirements---2027/maths", True),
        ("/courses/cs/entry-requirements", True),
        ("/courses/cs/entry_requirements.html", True),
        ("/courses/cs/admission-requirements", True),
        ("/x/standard-requirement", True),
        ("/x/standard-requirements", True),
        ("/programmes/requirements-engineering-bsc", False),
        ("/programmes/computer-science/entry", False),
        ("/programmes/entry-requirements-for-engineers-guide", False),
    ],
)
def test_entry_requirements_segment(path: str, expected: bool) -> None:
    assert _is_entry_requirements_path(path) is expected


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--fee-subpage-exclusion" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "fx1_module.FEE_SUBPAGE_EXCLUSION = True" in source
    assert '["--fee-subpage-exclusion"]' in source
