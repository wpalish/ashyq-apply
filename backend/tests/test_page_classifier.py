"""Page classification: what a page is, and what it only looks like."""

from __future__ import annotations

import pytest

from app.adapters.page_classifier import PageType, classify_page


class TestLabelledTeachingLanguage:
    def test_warsaws_language_field_is_read(self):
        from app.adapters.page_classifier import _language

        assert _language("full-time, 3-year studies\nLanguage: Polish\nJump to:") == "polish"

    def test_viennas_label_and_value_may_be_on_separate_lines(self):
        from app.adapters.page_classifier import _language

        assert _language("Language\n\nGerman\n\nTest language\nEnglish") == "german"

    def test_a_foreign_language_exam_is_not_the_teaching_language(self):
        from app.adapters.page_classifier import _language

        assert _language("Foreign language exam (B2)\nPolish\nGerman proficiency: A2") is None

    def test_conflicting_language_fields_are_not_reduced_to_one(self):
        from app.adapters.page_classifier import _language

        assert _language("Language: Polish\nLanguage: English") is None


class TestContinuingCourses:
    def test_topic_courses_are_not_a_degree_named_in_their_enrolment_rules(self):
        page = classify_page(
            url="https://uni.edu/undergraduate-students/topic-courses/computer-science-topic-courses",
            html="<h1>Computer Science Topic Courses</h1><p>Fall 2026. "
            "Senior undergraduate course. Priority for Computer Science Major students.</p>",
        )
        assert page.page_type is PageType.IRRELEVANT

    def test_a_teacher_course_is_not_a_degree_its_audience_holds(self):
        page = classify_page(
            url="https://uni.edu/lifelong/computer-science-courses-teachers-informatics/id",
            html="<h1>Computer Science</h1><p>Courses for teachers of informatics. "
            "Applicants hold a bachelor degree. Computer Science topics.</p>",
        )
        assert page.page_type is PageType.IRRELEVANT

    def test_a_degree_is_preserved_when_it_mentions_a_teacher_course_in_the_body(self):
        page = classify_page(
            url="https://uni.edu/bachelors/computer-science",
            html="<h1>BSc Computer Science</h1><p>A three-year degree. "
            "We also offer courses for teachers.</p>",
        )
        assert page.page_type is PageType.PROGRAM_DETAIL


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


def test_an_admission_procedure_page_is_an_admissions_page():
    """Run 32: Vienna's page, once no longer news, was left unknown."""
    html = (
        "<html><head><title>Admission procedure | University of Vienna</title></head><body><main>"
        "<h1>Admission procedure</h1><p>Apply online in u:space by the deadline.</p>"
        "</main></body></html>"
    )
    result = classify_page(url="https://studieren.univie.ac.at/en/admission-procedure", html=html)
    assert result.page_type is PageType.GENERAL_ADMISSIONS


def test_a_degree_title_with_its_subject_in_brackets_is_read():
    """The bracketed way programme lists name a subject; HKU's page is a suspect, unconfirmed."""
    from app.adapters.page_classifier import full_degree_titles

    assert full_degree_titles("BEng(CompSc) Bachelor of Engineering (Computer Science)") == [
        "Bachelor of Engineering in Computer Science"
    ]
    assert full_degree_titles("Bachelor of Arts (Hons)") == []


class TestProgrammePageGuard:
    """PG-1: a research-output URL or a host root needs programme structure."""

    #: A research-portal "fingerprints" page (Pure-style): a concept list with
    #: weights, no research words, and title words that read as a bachelor.
    PUBLICATION = (
        "<html><head><title>Undergraduate Computer Science Bachelor Education - Fingerprint"
        " - Example Research Portal</title></head><body>"
        "<nav><a href='/en/'>Home</a><a href='/en/persons/'>Profiles</a></nav><main>"
        "<h1>Undergraduate Computer Science Bachelor Education</h1><h2>Fingerprint</h2>"
        "<p>Dive into the research topics of 'Undergraduate Computer Science Bachelor "
        "Education'. Together they form a unique fingerprint.</p><ul>"
        "<li>Computer Science Education 100%</li><li>Undergraduate Students 72%</li>"
        "<li>Bachelor Programme 45%</li><li>Teaching Methods 38%</li></ul>"
        "<p>Sort by weight or alphabetically. Engineering and Materials Science. "
        "Social Sciences. Computer Science. Mathematics.</p></main></body></html>"
    )
    PUBLICATION_URL = "https://portal.research.example.edu/en/publications/undergraduate-cs-education/fingerprints"
    #: A department home page whose heading names the degree it teaches.
    DEPARTMENT = (
        "<html><head><title>Department of Computer Science - Bachelor of Science in Computer "
        "Science - Example University</title></head><body><main>"
        "<h1>Bachelor of Science in Computer Science</h1>"
        "<p>Welcome to the Department of Computer Science. Our faculty conduct world-class "
        "research in artificial intelligence, systems, theory and human-computer interaction. "
        "We host seminars every week and welcome visitors from around the world.</p>"
        "<h2>Research highlights</h2><p>Our group received a best paper award at a leading "
        "venue this year. Read about our latest projects, meet our people and explore our "
        "laboratories. Industry partners collaborate with us on many topics.</p>"
        "</main></body></html>"
    )
    #: A real programme page: credits, duration, start of studies, requirements.
    PROGRAMME = (
        "<html><head><title>Computer Science - Bachelor of Science (B.Sc.) - Example "
        "University</title></head><body><main><h1>Bachelor of Science in Computer Science</h1>"
        "<p>The bachelor programme in computer science covers algorithms and theory.</p>"
        "<h2>Key facts</h2><ul><li>Credits: 180 ECTS</li><li>Standard period of study: "
        "6 semesters</li><li>Start of studies: winter semester</li><li>Language: English</li>"
        "</ul><h2>Admission requirements</h2><p>A higher education entrance qualification "
        "and English at B2 level.</p></main></body></html>"
    )

    @staticmethod
    def _guard(monkeypatch, on: bool) -> None:
        from app.adapters import page_classifier

        monkeypatch.setattr(page_classifier, "PROGRAMME_PAGE_GUARD", on)

    def test_a_publication_fingerprint_is_not_a_programme(self, monkeypatch):
        self._guard(monkeypatch, True)
        page = classify_page(url=self.PUBLICATION_URL, html=self.PUBLICATION)
        assert page.page_type is PageType.UNKNOWN
        assert page.subject is None

    @pytest.mark.parametrize("url", ["https://cs.example.edu/", "https://cs.example.edu/en/"])
    def test_a_department_home_is_not_a_programme(self, monkeypatch, url):
        self._guard(monkeypatch, True)
        assert classify_page(url=url, html=self.DEPARTMENT).page_type is PageType.UNKNOWN

    def test_off_both_pages_still_read_as_programmes(self, monkeypatch):
        self._guard(monkeypatch, False)
        for url, html in (
            (self.PUBLICATION_URL, self.PUBLICATION),
            ("https://cs.example.edu/", self.DEPARTMENT),
        ):
            assert classify_page(url=url, html=html).page_type is PageType.PROGRAM_DETAIL

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.example.edu/en/studies/bachelor/computer-science",
            "https://cs.example.edu/",
            "https://portal.research.example.edu/en/publications/x",
        ],
    )
    def test_a_real_programme_page_stays_a_programme(self, monkeypatch, url):
        self._guard(monkeypatch, True)
        page = classify_page(url=url, html=self.PROGRAMME)
        assert page.page_type is PageType.PROGRAM_DETAIL
        assert page.degree_level == "bachelor"

    def test_structure_signals_count_kinds_not_mentions(self):
        from app.adapters.page_classifier import programme_structure_signals

        assert programme_structure_signals("180 ECTS, 30 ECTS per semester") == ["credits"]
        assert programme_structure_signals(
            "6 semesters. Admission requirements: a diploma. Tuition: none."
        ) == ["duration", "admission_requirements", "tuition"]
        assert programme_structure_signals("Dive into the research topics.") == []

    def test_host_root(self):
        from app.adapters.page_classifier import is_host_root

        assert is_host_root("https://cs.hku.hk/")
        assert is_host_root("https://cs.example.edu")
        en = '<html lang="en"><body></body></html>'
        assert is_host_root("https://cs.example.edu/en/index.html", en)
        # "/cs" is Czech and also where a computer-science programme lives:
        # without the page saying it is Czech, it is not a language root.
        assert not is_host_root("https://uni.edu/cs")
        assert not is_host_root("https://uni.edu/cs", en)
        assert is_host_root("https://cs.example.edu/en/")  # no lang: a UI code
        assert is_host_root("https://uni.cz/cs/", '<html lang="cs">')
        assert not is_host_root("https://cs.example.edu/en/bachelor")
        assert not is_host_root("https://cs.example.edu/?page=bsc")


class TestCatalogHeadingScope:
    """CL-1: catalogue words in two unrelated headings do not make a catalogue.

    Minimal fixtures shaped like the hand-fetched dev2 pages (evidence analysis
    2026-10-17 §1.2): only the title, the headings and the links that decided
    the verdict are kept.
    """

    TCD_URL = "https://www.tcd.ie/courses/undergraduate/courses/computer-science/"
    TCD = (
        "<html><head><title>Computer Science - Courses | Trinity College Dublin</title></head>"
        "<body><main><h1>Computer Science</h1><h2>Overview</h2>"
        "<p>Computer science is the study of computation and its applications.</p>"
        "<h2>Course Details</h2><p>Duration: 4 years. CAO code TR033.</p>"
        "<h2>Admission Requirements</h2><p>Leaving Certificate H4 in Mathematics.</p>"
        "<h2>Related courses</h2><ul>"
        + "".join(
            f'<li><a href="/courses/undergraduate/courses/{slug}/">{slug}</a></li>'
            for slug in ("computer-engineering", "mathematics", "engineering", "physics", "csl")
        )
        + "</ul></main></body></html>"
    )
    UPPSALA_URL = "https://www.uu.se/en/study/programme/bachelors-programme-computer-science"
    UPPSALA = (
        "<html><head><title>Bachelor's Programme in Computer Science – Uppsala University"
        "</title></head><body><main><h1>Bachelor's Programme in Computer Science</h1>"
        "<p>180 credits. Start of studies: autumn 2027. Teaching language: English.</p>"
        "<h2>Application and entry requirements</h2><p>Application deadline: 15 April.</p>"
        "<h2>Programme syllabus</h2><h2>Admitted or on the waiting list</h2>"
        "<p>Read more about your next steps.</p></main></body></html>"
    )
    CATALOGUE_URL = "https://www.tcd.ie/courses/undergraduate/"
    CATALOGUE = (
        "<html><head><title>Undergraduate Courses | Trinity College Dublin</title></head>"
        "<body><main><h1>Undergraduate Courses</h1><h2>Browse courses A-Z</h2><ul>"
        + "".join(
            f'<li><a href="/courses/undergraduate/courses/{slug}/">{slug}</a></li>'
            for slug in (
                "computer-science",
                "computer-engineering",
                "mathematics",
                "engineering",
                "physics",
                "history",
                "law",
                "medicine",
            )
        )
        + "</ul></main></body></html>"
    )

    @staticmethod
    def _scope(monkeypatch, on: bool) -> None:
        from app.adapters import page_classifier

        monkeypatch.setattr(page_classifier, "CATALOG_HEADING_SCOPE", on)

    def test_cl1_is_on_by_default(self):
        from app.adapters import page_classifier

        assert page_classifier.CATALOG_HEADING_SCOPE is True

    def test_on_tcds_course_page_is_a_programme(self, monkeypatch):
        self._scope(monkeypatch, True)
        page = classify_page(url=self.TCD_URL, html=self.TCD)
        assert page.page_type is PageType.PROGRAM_DETAIL
        assert page.subject == "Computer Science"
        assert page.degree_level == "bachelor"

    def test_on_uppsalas_programme_page_is_a_programme(self, monkeypatch):
        self._scope(monkeypatch, True)
        page = classify_page(url=self.UPPSALA_URL, html=self.UPPSALA)
        assert page.page_type is PageType.PROGRAM_DETAIL
        assert page.subject == "Bachelor's Programme in Computer Science"

    def test_off_both_pages_read_as_catalogues_as_before(self, monkeypatch):
        self._scope(monkeypatch, False)
        for url, html in ((self.TCD_URL, self.TCD), (self.UPPSALA_URL, self.UPPSALA)):
            page = classify_page(url=url, html=html)
            assert page.page_type is PageType.PROGRAM_CATALOG
            assert "plural catalogue heading" in page.signals

    @pytest.mark.parametrize("on", [False, True])
    def test_a_real_catalogue_stays_a_catalogue(self, monkeypatch, on):
        self._scope(monkeypatch, on)
        page = classify_page(url=self.CATALOGUE_URL, html=self.CATALOGUE)
        assert page.page_type is PageType.PROGRAM_CATALOG

    @pytest.mark.parametrize("on", [False, True])
    def test_a_catalogue_shaped_identity_or_title_still_decides(self, monkeypatch, on):
        self._scope(monkeypatch, on)
        by_heading = "<html><body><main><h1>Find a course</h1><p>Search.</p></main></body></html>"
        by_title = (
            "<html><head><title>Browse all programmes | Example University</title></head>"
            "<body><main><p>Pick a bachelor programme.</p></main></body></html>"
        )
        for html in (by_heading, by_title):
            page = classify_page(url="https://www.example.edu/study/", html=html)
            assert page.page_type is PageType.PROGRAM_CATALOG
