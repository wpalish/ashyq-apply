"""ER-06: archive, mirror, repository and journal pages are not programme pages."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import pytest

from app.adapters.search.base import SearchResult
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.prefilter import is_archive_page, prefilter
from app.adapters.search.retrieval import discover_candidates
from app.domain.enums import DegreeLevel


def _result(url: str, rank: int = 1) -> SearchResult:
    return SearchResult(
        url=url,
        title="Computer Science",
        provider="fake",
        rank=rank,
        retrieved_at=datetime(2026, 9, 27, tzinfo=UTC),
    )


def test_the_kaist_capture_choices_are_archives() -> None:
    assert is_archive_page("https://ftp.kaist.ac.kr/ctan/macros/latex/contrib/x/x.pdf")
    assert is_archive_page("https://pure.kaist.ac.kr/en/clippings/free-cs-courses")
    assert is_archive_page("https://an.kaist.ac.kr/courses/2006/cs492")


def test_programme_and_department_pages_are_not() -> None:
    assert not is_archive_page("https://cs.kaist.ac.kr/content?menu=40")
    assert not is_archive_page("https://www.utsc.utoronto.ca/admissions/programs/computer-science")
    assert not is_archive_page("https://www.mff.cuni.cz/en/students/bachelor-of-computer-science")
    assert not is_archive_page("https://www.tum.de/en/studies/degree-programs/detail/informatics")


def test_the_switch_is_off_by_default(monkeypatch) -> None:
    from app.adapters import page_classifier as _pg1

    monkeypatch.setattr(_pg1, "PROGRAMME_PAGE_GUARD", False)  # the pre-PG-1 path
    url = "https://pure.kaist.ac.kr/en/clippings/free-cs-courses"
    off = prefilter([_result(url)], domain="kaist.ac.kr", degree=DegreeLevel.BACHELOR)
    on = prefilter(
        [_result(url)],
        domain="kaist.ac.kr",
        degree=DegreeLevel.BACHELOR,
        reject_archive_hosts=True,
    )
    assert [c.url for c in off.kept] == [url]
    assert on.kept == () and on.rejection_counts == {"not_a_programme_page": 1}


# --- PG-1: the programme-page guard turns these rejections on --------------

#: KAIST/TUM-shaped junk the 2026 captures spent identity-recovery reads on.
_JUNK = (
    "https://ftp.kaist.ac.kr/ctan/macros/latex/contrib/x/x.pdf",
    "https://pure.kaist.ac.kr/en/clippings/free-cs-courses",
    "https://an.kaist.ac.kr/courses/2006/cs492",
    "https://portal.kaist.ac.kr/en/publications/undergraduate-cs-education/fingerprints",
    "https://ed.kaist.ac.kr/news-single-view-start/article/computer-science-bachelor",
    "https://www.kaist.ac.kr/en/article/computer-science-bachelor-students",
)
_PROGRAMME = "https://cs.kaist.ac.kr/content?menu=40"


@pytest.fixture
def guard(monkeypatch):
    from app.adapters import page_classifier

    monkeypatch.setattr(page_classifier, "PROGRAMME_PAGE_GUARD", True)


def test_pg1_is_on_by_default() -> None:
    from app.adapters import page_classifier

    assert page_classifier.PROGRAMME_PAGE_GUARD is True


def test_pg1_excluded_paths_learn_publications_articles_and_clippings(monkeypatch) -> None:
    from app.adapters import page_classifier
    from app.adapters.discovery.live_discovery import is_excluded_path

    urls = [
        "https://portal.tum.de/en/publications/x/fingerprints",
        "https://www.uni.edu/publication/x",
        "https://ed.tum.de/news-single-view-start/article/x",
        "https://pure.kaist.ac.kr/en/clippings/free-cs-courses",
    ]
    monkeypatch.setattr(page_classifier, "PROGRAMME_PAGE_GUARD", False)
    assert not any(is_excluded_path(u) for u in urls)
    monkeypatch.setattr(page_classifier, "PROGRAMME_PAGE_GUARD", True)
    assert all(is_excluded_path(u) for u in urls)
    assert not is_excluded_path("https://www.tum.de/en/studies/degree-programs/detail/informatics")


def _intent() -> DiscoveryIntent:
    return DiscoveryIntent(
        institution="KAIST",
        domain="kaist.ac.kr",
        degree=DegreeLevel.BACHELOR,
        field="computer science",
    )


async def _discover(opened: list[str]):
    intent = _intent()
    rows = [(url, "Computer Science bachelor", "") for url in (*_JUNK, _PROGRAMME)]
    provider = FakeSearchProvider(
        {q.text: rows for q in queries_for(intent, budget=99)},
        now=datetime(2026, 10, 17, tzinfo=UTC),
    )

    async def fetch(url: str) -> str:
        opened.append(url)
        return ""

    return await discover_candidates(provider, intent, fetch=fetch)


async def test_pg1_archive_and_publication_urls_never_take_a_read(guard) -> None:
    opened: list[str] = []
    report = await _discover(opened)
    ranked = [c.url for c in report.candidates]
    assert _PROGRAMME in ranked
    assert not set(_JUNK) & set(ranked)
    junk_hosts = {urlparse(url).hostname for url in _JUNK} - {"www.kaist.ac.kr"}
    assert not any(urlparse(url).hostname in junk_hosts for url in opened)


async def test_without_pg1_the_junk_is_still_offered(monkeypatch) -> None:
    from app.adapters import page_classifier as _pg1

    monkeypatch.setattr(_pg1, "PROGRAMME_PAGE_GUARD", False)  # the pre-PG-1 path
    report = await _discover([])
    assert set(_JUNK) & {c.url for c in report.candidates}
