"""EXTRA-12: a page that names one programme is a programme page, however
many other programmes it links to.

Live run 35754594232's per-page records named this as the cause of five of the
ten zero-claim cases. Groningen's rejected page is the certified corpus' own
source URL — the pipeline found the right page, fetched it, and the
classifier called it a catalogue, so ACCEPTS["requirements"] never let an
extractor near it.

The cause was ordering: link counting ran before the page's own identity was
read. The funding branch of the same module already had the right rule — a
page with links out is an index when it has "no award identity of its own" —
and the programme branch never got it.
"""

from __future__ import annotations

import pytest

from app.adapters.page_classifier import PageType, classify_page

_SIBLING_LINKS = "".join(
    f'<li><a href="/bachelors/programme-{i}">BSc Programme {i}</a></li>' for i in range(9)
)


#: A real catalogue carries prose as well as links; a page that is nothing but
#: anchors classifies as navigation long before the programme family is
#: reached, which is behaviour older than this change.
_CATALOGUE_BODY = (
    "<p>Our faculties offer a wide range of bachelor's degrees taught in English. "
    "Choose a programme below to read its entry requirements, tuition fees and "
    "application deadlines for the coming academic year.</p>"
    f"<ul>{_SIBLING_LINKS}</ul>"
)


def _page(title: str, body: str) -> str:
    return (
        f"<html><head><title>{title}</title></head><body><main>"
        f"<h1>{title}</h1>{body}</main></body></html>"
    )


class TestAProgrammePageKeepsItsIdentity:
    def test_it_survives_linking_to_its_siblings(self):
        """Every real programme page links to related programmes."""
        page = _page(
            "BSc Computing Science",
            "<p>This three-year bachelor's degree programme covers programming and "
            "algorithms. Entry requirements: IELTS Academic overall 6.5.</p>"
            f"<h2>Related programmes</h2><ul>{_SIBLING_LINKS}</ul>",
        )
        found = classify_page(url="https://www.rug.nl/bachelors/computing-science", html=page)
        assert found.page_type is PageType.PROGRAM_DETAIL
        assert found.accepts("requirements"), "the allow-list is what actually blocked extraction"

    def test_a_page_with_no_links_is_unaffected(self):
        page = _page(
            "BSc Computing Science",
            "<p>This three-year bachelor's degree programme covers programming.</p>",
        )
        assert classify_page(url="https://uni.edu/cs", html=page).page_type is (
            PageType.PROGRAM_DETAIL
        )


class TestACatalogueIsStillACatalogue:
    def test_a_plural_heading_settles_it_whatever_the_links(self):
        """The page saying what it is outranks any counting."""
        page = _page("Bachelor's programmes", _CATALOGUE_BODY)
        assert classify_page(url="https://uni.edu/all", html=page).page_type is (
            PageType.PROGRAM_CATALOG
        )

    def test_links_still_decide_when_the_page_names_no_programme(self):
        """The funding branch's rule, applied to programmes: links out plus no
        identity of its own is a listing."""
        page = _page("Study at our university", _CATALOGUE_BODY)
        found = classify_page(url="https://uni.edu/study", html=page)
        assert found.page_type is PageType.PROGRAM_CATALOG
        assert not found.accepts("requirements")

    @pytest.mark.parametrize(
        "heading",
        ["All programmes", "Our degrees", "Browse courses", "Overview of programmes"],
    )
    def test_catalogue_headings_are_unchanged(self, heading):
        page = _page(heading, _CATALOGUE_BODY)
        assert classify_page(url="https://uni.edu/x", html=page).page_type is (
            PageType.PROGRAM_CATALOG
        )
