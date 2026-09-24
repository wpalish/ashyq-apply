"""A page lxml cannot build must not end a case (run 49, Toronto)."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.adapters.html_parse import parse_html

#: An attribute name lxml reads as a namespace and bs4 fails to unpack.
HOSTILE = '<html><body><a {x="1" href="/awards/entrance">Entrance award</a></body></html>'


def test_lxml_really_crashes_on_this_markup():
    with pytest.raises(ValueError):
        BeautifulSoup(HOSTILE, "lxml")


def test_parse_html_falls_back_and_keeps_the_links():
    soup = parse_html(HOSTILE)
    assert [a.get_text() for a in soup.find_all("a")] == ["Entrance award"]


def test_ordinary_markup_is_unchanged():
    assert parse_html("<p>hello</p>").get_text() == "hello"


def test_the_scholarship_link_reader_survives_it():
    from app.adapters.scholarship.web_scholarships import _award_links

    _award_links(HOSTILE, "https://uni.edu/finances/scholarships")
