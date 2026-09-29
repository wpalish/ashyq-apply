"""Repeated links to one award must not turn its detail page into an index."""

from __future__ import annotations

from app.adapters.page_classifier import PageType, classify_page

_RECTOR_TITLE = (
    "Everything you need to know about the Rector’s Scholarship – academic year 2026/2027"
)
_DETAIL_URL = (
    "https://bpm.uw.edu.pl/en/"
    "everything-you-need-to-know-about-the-rectors-scholarship-academic-year-2026-2027"
)
_CATEGORY_LINK = (
    '<a href="https://bpm.uw.edu.pl/en/category/rectors-scholarship/">Rector’s scholarship</a>'
)
_DETAIL_LINK = '<a href="https://bpm.uw.edu.pl/en/rectors-scholarship/">RECTOR’S SCHOLARSHIP</a>'


def _page(heading: str, links: str) -> str:
    """The retained Warsaw notice's named heading, category and substantive prose."""
    return (
        f"<html><head><title>{heading} - Biuro ds. Pomocy Materialnej</title></head>"
        f"<body><main><h1>{heading}</h1>{links}"
        "<p>Applications for the Rector’s Scholarship for the 2026/2027 academic year "
        "may be submitted from 1 to 15 October 2026. Remember that this is a strict "
        "deadline and cannot be extended!</p>"
        "<p>The percentage of eligible students and the amount of the scholarship "
        "will be announced no earlier than late November or early December.</p>"
        "</main></body></html>"
    )


def test_category_and_detail_links_naming_one_award_do_not_make_it_an_index() -> None:
    """Actual source: two different destinations, one case-insensitive award name."""
    page = classify_page(
        url=_DETAIL_URL,
        html=_page(_RECTOR_TITLE, _CATEGORY_LINK + _DETAIL_LINK),
    )

    assert page.page_type is PageType.SCHOLARSHIP_AWARD
    assert page.subject == _RECTOR_TITLE
    assert page.accepts("scholarship_award")


def test_two_distinct_named_awards_remain_an_index() -> None:
    other_award = (
        '<a href="https://bpm.uw.edu.pl/en/start-scholarship-for-olympians/">'
        "START Scholarship for Olympians</a>"
    )
    page = classify_page(
        url=_DETAIL_URL,
        html=_page(_RECTOR_TITLE, _DETAIL_LINK + other_award),
    )

    assert page.page_type is PageType.SCHOLARSHIP_INDEX
    assert page.subject is None
    assert not page.accepts("scholarship_award")


def test_repeated_award_links_do_not_override_a_faq_heading() -> None:
    page = classify_page(
        url="https://bpm.uw.edu.pl/en/rectors-scholarship-faq/",
        html=_page("Rector’s Scholarship FAQ", _CATEGORY_LINK + _DETAIL_LINK),
    )

    assert page.page_type is PageType.SCHOLARSHIP_FAQ
    assert not page.accepts("scholarship_award")


def test_repeated_award_links_do_not_override_a_plural_listing_heading() -> None:
    page = classify_page(
        url="https://bpm.uw.edu.pl/en/scholarships/",
        html=_page("Scholarships", _CATEGORY_LINK + _DETAIL_LINK),
    )

    assert page.page_type is PageType.SCHOLARSHIP_INDEX
    assert page.subject is None
    assert not page.accepts("scholarship_award")
