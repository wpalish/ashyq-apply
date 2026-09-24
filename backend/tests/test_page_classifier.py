"""Page classification: what a page is, and what it only looks like."""

from __future__ import annotations

from app.adapters.page_classifier import PageType, classify_page


class TestADegreeWordIsNotAProgramme:
    """V2-29 — headings a live run actually claimed a programme from.

    Groningen's "Bachelor's Open Day" and Delft's "Preparing for a bachelor"
    became `programme.exists` claims in the 2026-09-21 capture, and the
    benchmark scored them as wrong-scope claims about Computing Science and
    Computer Science and Engineering. Both contain a degree word; neither is a
    programme.
    """

    def test_an_open_day_is_not_a_programme(self):
        from app.adapters.page_classifier import _program_name

        assert _program_name("Bachelor's Open Day") is None

    def test_an_advice_page_is_not_a_programme(self):
        from app.adapters.page_classifier import _program_name

        assert _program_name("Preparing for a bachelor") is None

    def test_an_event_in_any_of_its_usual_words_is_not_a_programme(self):
        from app.adapters.page_classifier import _program_name

        for heading in (
            "Master's Information Session",
            "Bachelor Open Evening",
            "Meet us at the Bachelor Fair",
            "Bachelor taster day",
        ):
            assert _program_name(heading) is None, heading

    def test_a_real_programme_with_an_ordinary_name_still_passes(self):
        """The rule must not cost a programme its page: only headings that
        announce an event or an instruction are refused."""
        from app.adapters.page_classifier import _program_name

        for heading in (
            "BSc Computer Science",
            "Bachelor of Science in Computer Science",
            "Bachelor of Arts, Visual Studies",
            "MSc Computer Science and Engineering",
        ):
            assert _program_name(heading) == heading, heading


class TestABareSubjectHeading:
    """Groningen's certified page: heading "Computing Science", degree only in
    the title and the path, eight links to sibling programmes."""

    _LINKS = "".join(f'<li><a href="/bachelors/p{i}">Programme {i} BSc</a></li>' for i in range(8))

    def _page(self, title: str) -> str:
        return (
            f"<html><head><title>{title}</title></head><body><main>"
            "<h1>Computing Science</h1><p>Three-year bachelor taught in English.</p>"
            f"<ul>{self._LINKS}</ul></main></body></html>"
        )

    def test_title_and_path_name_the_programme(self):
        page = classify_page(
            url="https://www.rug.nl/bachelors/computing-science/",
            html=self._page("Computing Science | Bachelor | University of Groningen"),
        )
        assert page.page_type is PageType.PROGRAM_DETAIL
        assert page.subject == "Computing Science"

    def test_without_a_degree_in_title_or_path_it_stays_a_listing(self):
        page = classify_page(
            url="https://www.rug.nl/about/computing-science/",
            html=self._page("Computing Science | About us | University of Groningen"),
        )
        assert page.page_type is PageType.PROGRAM_CATALOG


class TestASchoolIsNotItsOwnProgramme:
    """Run 12: HKU's "Computing and Data Science" school page was recorded as a
    master's programme of that name — a false programme and a wrong degree."""

    def test_a_heading_the_body_names_under_a_different_degree_title_is_not_a_programme(self):
        html = (
            "<html><head><title>Computing and Data Science | HKU Admissions</title></head>"
            "<body><main><h1>Computing and Data Science</h1>"
            "<p>Explore master programmes as well. The Bachelor of Engineering in Computer "
            "Science covers algorithms and data structures.</p></main></body></html>"
        )
        page = classify_page(
            url="https://admissions.hku.hk/programmes/undergraduate-programmes/"
            "computing-and-data-science",
            html=html,
        )
        assert page.subject != "Computing and Data Science"

    def test_a_context_named_programme_takes_its_degree_from_the_title_not_the_body(self):
        html = (
            "<html><head><title>Computing Science | Bachelor | University of Groningen</title>"
            "</head><body><main><h1>Computing Science</h1>"
            "<p>After this, many continue to a master's degree.</p></main></body></html>"
        )
        page = classify_page(url="https://www.rug.nl/bachelors/computing-science/", html=html)
        assert page.subject == "Computing Science"
        assert page.degree_level == "bachelor"


def test_the_degree_named_first_wins_not_the_first_in_the_word_list():
    from app.adapters.page_classifier import _degree_level

    assert _degree_level("BSc Computer Science. Continue to our master programmes.") == "bachelor"
    assert _degree_level("MSc Data Science, building on a bachelor degree.") == "master"


def test_a_research_output_on_a_research_portal_is_not_a_programme():
    """Run 23: a paper's field words read as a programme on Aalto's portal."""
    html = (
        "<html><head><title>Arguments for and Approaches to Computing Education in "
        "Undergraduate Computer Science Programmes</title></head><body><main>"
        "<h1>Arguments for and Approaches to Computing Education in Undergraduate "
        "Computer Science Programmes</h1><p>Research output: Contribution to journal. "
        "Abstract: we survey bachelor programmes in computer science. DOI 10.1000/x</p>"
        "</main></body></html>"
    )
    result = classify_page(url="https://research.aalto.fi/en/publications/arguments", html=html)
    assert result.page_type is PageType.IRRELEVANT


def test_a_portal_url_alone_does_not_reject_a_page():
    html = (
        "<html><head><title>Bachelor's Programme in Computer Science</title></head><body>"
        "<main><h1>Bachelor's Programme in Computer Science</h1><p>Apply by January. "
        "The programme lasts three years.</p></main></body></html>"
    )
    result = classify_page(url="https://research.example.edu/en/projects/cs", html=html)
    assert result.page_type is not PageType.IRRELEVANT


def test_a_news_block_on_the_page_does_not_make_it_news():
    """Run 31: Vienna's admission-procedure page, rejected on a sidebar h2."""
    html = (
        "<html><head><title>Admission procedure | University of Vienna</title></head><body><main>"
        "<h1>Admission procedure</h1><p>Apply online in u:space by the deadline.</p>"
        "<h2>News</h2><p>Open day on 3 March.</p></main></body></html>"
    )
    result = classify_page(url="https://studieren.univie.ac.at/en/admission-procedure", html=html)
    assert result.page_type is not PageType.NEWS


def test_a_page_titled_as_news_is_still_news():
    html = (
        "<html><head><title>News | University</title></head><body><main>"
        "<h1>New lab opens</h1><p>Text.</p></main></body></html>"
    )
    assert classify_page(url="https://x.edu/a", html=html).page_type is PageType.NEWS
