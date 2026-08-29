"""Site chrome is not the page.

Every page on a university site carries the same header, menu and footer. Those
regions contain headings, and until they were excluded they crowded out the
page's own: on Toronto's programme pages the first six headings were "Main
Menu", "Breadcrumbs" and four items from the site header, so the checks that
read the leading headings saw navigation and nothing else.

Worse, the header on that site reads "Find the program that's right for you" —
catalogue phrasing, present identically on a catalogue and on a single
programme page. Chrome cannot distinguish the two, so it must not be consulted.
"""
from pathlib import Path

import pytest

from app.adapters.page_classifier import (
    PageType,
    _degree_level,
    _headings,
    classify_page,
)

PAGES = Path(__file__).parent / "fixtures" / "pages"


def _soup(name: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup((PAGES / name).read_text(), "lxml")


def test_headings_skip_navigation_and_keep_the_pages_own() -> None:
    heads = _headings(_soup("uoft-computer-science.html"))
    assert "Main Menu" not in heads
    assert "Breadcrumbs" not in heads
    assert heads[0] == "Computer Science"


def test_chrome_catalogue_phrasing_does_not_make_a_programme_page_a_catalogue() -> None:
    """The site header says "Find the program that's right for you" on *every*
    page. Reading it as a signal turned each programme page into a catalogue."""
    heads = _headings(_soup("uoft-computer-science.html"))
    assert not any("right for you" in h.lower() for h in heads)


def test_a_hub_that_lists_programmes_in_its_own_content_is_a_catalogue() -> None:
    html = (PAGES / "toronto-datacs.html").read_text()
    result = classify_page(
        url="https://future.utoronto.ca/data-computer-science", html=html
    )
    assert result.page_type is PageType.PROGRAM_CATALOG
    assert any("explore programs" in s.lower() for s in result.signals), result.signals


def test_the_hub_is_never_read_as_a_single_programme() -> None:
    """It names a field, not a programme. Accepting it would be a false
    positive of exactly the kind the zero-tolerance rule forbids."""
    html = (PAGES / "toronto-datacs.html").read_text()
    result = classify_page(
        url="https://future.utoronto.ca/data-computer-science", html=html
    )
    assert result.page_type is not PageType.PROGRAM_DETAIL


@pytest.mark.parametrize(
    "text",
    ["HBSc Major, Minor, Specialist", "Honours Bachelor of Arts", "HBA"],
)
def test_canadian_honours_credentials_name_the_bachelor_level(text: str) -> None:
    """HBSc and HBA are how Ontario universities write their undergraduate
    degrees. Without them a page that states its level reads as stating none."""
    assert _degree_level(text) == "bachelor"


def test_a_plural_category_with_qualifiers_is_still_a_listing() -> None:
    """Warsaw heads its catalogue "Degree Programmes: 1st, 2nd and long cycle
    studies (Bachelor and Master)".

    The plural guard only fired when the listing word ended the heading, so
    everything after the colon hid it: the page was accepted as one programme
    at master's level with 0.85 confidence. A student would have been shown a
    catalogue as a specific programme — the false positive this product treats
    as unacceptable.
    """
    html = (PAGES / "warsaw-degree-programmes.html").read_text()
    result = classify_page(
        url="https://en.uw.edu.pl/education/degree-programmes-1st-2nd-and-long-cycle-studies/",
        html=html,
    )
    assert result.page_type is not PageType.PROGRAM_DETAIL
    assert result.page_type is not PageType.INTAKE_SPECIFIC_PROGRAM


def test_a_programme_page_is_not_caught_by_the_category_rule() -> None:
    """The rule keys on a plural listing word leading the heading. A real
    programme page names a subject and must be untouched by it."""
    result = classify_page(
        url="https://www.rug.nl/bachelors/computing-science/",
        html=(PAGES / "rug-computing-science.html").read_text(),
    )
    assert result.page_type in {PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}


class TestACredentialBesideTheSubject:
    """Toronto's programme pages name a subject and state its credential.

    `future.utoronto.ca/program/computer-science` is a real programme page: it
    is headed "Computer Science", states HBSc beside it, lists the options
    (major, minor, specialist), gives the OUAC application code and publishes
    admission requirements for every school system. It classified as UNKNOWN.

    The promotion path for a heading that names a subject without a level
    required two distinct programme sections; this page carries one. The
    guard's own reason is that "a faculty or department page names a subject
    and nothing else" — and this page does say something else. It states a
    degree credential right beside its subject, which is precisely what a
    department page does not do.
    """

    def test_the_programme_page_is_recognised(self) -> None:
        result = classify_page(
            url="https://future.utoronto.ca/program/computer-science",
            html=(PAGES / "uoft-computer-science.html").read_text(),
        )
        assert result.page_type in {
            PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM,
        }, result.signals
        assert result.degree_level == "bachelor"

    @pytest.mark.parametrize("stem,url", [
        ("uoft-cs-department", "https://web.cs.toronto.edu/"),
        ("rug-faculty-science-engineering", "https://www.rug.nl/fse/"),
    ])
    def test_a_department_or_faculty_page_is_still_refused(self, stem, url) -> None:
        """The pages the guard exists for. Both name a field; neither states a
        credential for it, and neither may be presented as a programme."""
        result = classify_page(url=url, html=(PAGES / f"{stem}.html").read_text())
        assert result.page_type not in {
            PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM,
        }, result.signals
