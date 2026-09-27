"""ER-06: archive, mirror, repository and journal pages are not programme pages."""

from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.search.base import SearchResult
from app.adapters.search.prefilter import is_archive_page, prefilter
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


def test_the_switch_is_off_by_default() -> None:
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
