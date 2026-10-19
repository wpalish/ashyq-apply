"""DA-2: the degree abbreviations the tables read today, and the tokens they must never read.

docs/process/DEGREE_ABBREVIATIONS_2026-10-19.md audited every standard abbreviation the
tables miss against the four dev sets; none appears on two, so none was added (tec's
"B.S." is dev2's alone). These tests pin the reference rows that are read today and
fence the look-alikes any later addition of "B.S."/"BS" or "M.S."/"MS" must keep out.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery.live_discovery import degree_level_named
from app.adapters.page_classifier import degree_levels_named


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("BA in Computer Science", "bachelor"),
        ("BSc (Hons) Computer Science", "bachelor"),
        ("B.Sc. Informatik", "bachelor"),
        ("BEng Computing", "bachelor"),
        ("B.Tech. in Computer Science and Engineering", "bachelor"),
        ("LLB Law", "bachelor"),
        ("MSc Computer Science", "master"),
        ("M.Tech in Computer Science", "master"),
        ("MPhil in Computer Science", "master"),
        ("Ph.D. in Computer Science", "phd"),
    ],
)
def test_the_reference_rows_read_today(text: str, level: str) -> None:
    assert degree_levels_named(text) == {level}


@pytest.mark.parametrize(
    "text",
    [
        # "B.S." is a standard title but seen on one dev set only (tec): not read.
        "B.S. in Computer Science and Technology",
        # British Standards and company names: never a degree, whatever is added.
        "Certified to BS 7799 and BS EN ISO 9001",
        "Sponsored by BS Group",
        "Ms Eunbin Carroll Lee",
        "BIT is the faculty's programme code",
    ],
)
def test_these_name_no_level(text: str) -> None:
    assert degree_levels_named(text) == frozenset()


@pytest.mark.parametrize(
    "url",
    [
        # dev2 tec's English twin: ``bs`` is no degree slug (one dev set).
        "https://tec.mx/en/engineering-and-sciences/bs-in-computer-science-and-technology",
        # cohort kaist: the honorific "Ms", not a master's.
        "https://urobot.kaist.ac.kr/url_teams/ms-eunbin-carroll-lee/",
        # imperial, uct: the English verb "be", seen on all four dev sets, never a degree.
        "https://www.imperial.ac.uk/be-inspired/societal-engagement/funding",
        "https://uct.ac.za/international/articles/2026-07-31-clone-journey-be-proud",
        "https://www.example.com/standards/bs-7799",
    ],
)
def test_these_slugs_name_no_level(url: str) -> None:
    assert degree_level_named(url) is None
