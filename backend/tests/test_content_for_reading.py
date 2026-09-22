"""EXTRA-9: extraction must be handed the page's content, not a projection of it.

`readable_text` — used by every extractor — routed through
`page_classifier.main_content`, which exists for the *classifier*: it deletes
site chrome so that counting links measures the page rather than the site.
That function deletes `form`, deletes `aside`, and deletes anything whose
class or id merely mentions a chrome word.

A requirement is very often inside exactly those. The demo corpus could never
catch this, because it is synthetic prose in plain `<p>` tags; real university
pages are not.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.adapters.extraction import readable_text
from app.adapters.page_classifier import classify_page, content_for_reading, main_content

_REAL_SHAPED_PAGE = """<html><head><title>BSc Computer Science</title></head><body>
<nav class="site-menu"><a href="/a">Programmes</a><a href="/b">Research</a></nav>
<main>
  <h1>BSc Computer Science</h1>
  <form class="application-picker">
    <label>Choose application type</label>
    <p>International applicants: IELTS Academic overall band of 6.5 is required.</p>
  </form>
  <aside class="key-facts">
    <p>Application deadline: 15 January 2027.</p>
  </aside>
  <div class="requirements-banner"><p>A minimum GPA of 3.0 is required.</p></div>
  <p>The programme lasts three years and is taught in English.</p>
</main>
<footer class="site-footer"><p>Cookie policy</p></footer>
</body></html>"""


class TestTheFactsSurviveTheirMarkup:
    def test_a_requirement_inside_a_form_is_kept(self):
        """UBC publishes admission requirements behind an application-type
        selector, which is a form."""
        assert "IELTS" in readable_text(_REAL_SHAPED_PAGE)

    def test_a_deadline_inside_an_aside_is_kept(self):
        """A deadline in a sidebar is one of the commonest layouts there is."""
        assert "15 January 2027" in readable_text(_REAL_SHAPED_PAGE)

    def test_a_container_whose_class_merely_says_banner_is_kept(self):
        """The old rule deleted any element whose class matched "banner", so a
        container classed "requirements-banner" took the GPA with it."""
        assert "GPA" in readable_text(_REAL_SHAPED_PAGE)

    def test_the_page_s_own_prose_is_still_there(self):
        assert "three years" in readable_text(_REAL_SHAPED_PAGE)


class TestChromeIsStillRemoved:
    def test_a_bulky_site_menu_does_not_become_the_page_s_vocabulary(self):
        page = _REAL_SHAPED_PAGE.replace(
            '<a href="/a">Programmes</a>',
            "".join(f'<a href="/p{i}">Master of Programme {i}</a>' for i in range(200)),
        )
        text = readable_text(page)
        assert "Master of Programme 7" not in text
        assert "IELTS" in text, "removing chrome must not remove content with it"

    def test_a_short_nav_is_kept_because_it_may_be_a_tab_strip(self):
        page = (
            "<html><body><nav><a href='#r'>Entry requirements</a></nav>"
            "<p>IELTS 6.5 overall.</p></body></html>"
        )
        assert "Entry requirements" in readable_text(page)


class TestClassificationIsUnaffected:
    def test_the_classifier_still_uses_its_own_stricter_view(self):
        """Two functions, two purposes: the classifier must not start seeing
        forms and asides, or an award page linking six awards from a sidebar
        becomes an index again.
        """
        soup = BeautifulSoup(_REAL_SHAPED_PAGE, "lxml")
        classifier_view = main_content(soup).get_text(" ", strip=True)
        reading_view = content_for_reading(BeautifulSoup(_REAL_SHAPED_PAGE, "lxml")).get_text(
            " ", strip=True
        )

        assert "IELTS" not in classifier_view
        assert "IELTS" in reading_view

    def test_the_page_still_classifies_the_same_way(self):
        assert classify_page(
            url="https://uni.edu/bsc-cs", html=_REAL_SHAPED_PAGE
        ).page_type.value in {
            "program_detail",
            "intake_specific_program",
        }
