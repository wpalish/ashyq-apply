"""Classification of real university pages, saved verbatim.

Every fixture here was fetched from the live site, then stripped of styles,
non-JSON-LD scripts and image payloads. The DOM structure that decides the
classification — headings, link targets, structured data — is untouched, and
each fixture was checked to reproduce the same verdict as the live page.

These exist because the failure they pin is invisible to hand-written HTML: a
programme page that links to its own sub-pages looks exactly like a catalogue
to a rule that only counts links.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.page_classifier import PageType, classify_page

FIXTURES = Path(__file__).parent / "fixtures" / "pages"

#: fixture stem -> the URL it was fetched from. The URL matters: several rules
#: read the path, and a classifier judged on a wrong URL proves nothing.
SOURCE_URL = {
    "delft-aerospace":
        "https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/ae/bsc-aerospace-engineering",
    "delft-cse":
        "https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/"
        "computer-science-and-engineering/bachelor-of-computer-science-and-engineering",
    "delft-catalog": "https://www.tudelft.nl/en/education/programmes/bachelors",
    "toronto-datacs": "https://future.utoronto.ca/data-computer-science",
    "vienna-cs":
        "https://studieren.univie.ac.at/en/bachelordiploma-programmes/"
        "computer-science-bachelor-with-entrance-exam-procedure",
    "ntu-cs":
        "https://www.ntu.edu.sg/education/undergraduate-programme/"
        "bachelor-of-computing-in-computer-science",
    "rug-campus-tour": "https://www.rug.nl/education/bachelor/campus-tour",
    "rug-news": "https://www.rug.nl/news/",
    "delft-scholarship-index":
        "https://www.tudelft.nl/en/education/study-programme-orientation/"
        "practical-matters/scholarships",
    "delft-vaneffen":
        "https://www.tudelft.nl/en/education/study-programme-orientation/"
        "practical-matters/scholarships/justus-louise-van-effen-excellence-scholarships",
    "clip-scholarship":
        "https://www.tudelft.nl/en/delft-university-fund/we-support/"
        "support-innovative-education/clip-scholarship",
}

PROGRAMME_TYPES = {PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}


def classify(stem: str):
    return classify_page(url=SOURCE_URL[stem], html=(FIXTURES / f"{stem}.html").read_text())


class TestGenuineProgrammePages:
    """Pages a human would call "the page for this programme"."""

    @pytest.mark.parametrize("stem", ["delft-aerospace", "delft-cse", "vienna-cs", "ntu-cs"])
    def test_they_classify_as_a_programme(self, stem):
        assert classify(stem).page_type in PROGRAMME_TYPES

    @pytest.mark.parametrize("stem", ["delft-aerospace", "delft-cse", "vienna-cs", "ntu-cs"])
    def test_they_name_the_programme_they_are_about(self, stem):
        assert classify(stem).subject

    def test_a_programmes_own_subpages_are_not_other_programmes(self):
        """The Delft defect, stated as a rule.

        `/bsc-aerospace-engineering` links to `/bsc-aerospace-engineering/
        about-the-programme`, `/after-your-studies`, `/student-experiences/...`
        — eighteen of them, every one under the programme's own path. Counting
        links that merely sit under `/bachelors/` made the programme page look
        like a catalogue of eighteen programmes.
        """
        result = classify("delft-aerospace")
        assert result.page_type in PROGRAMME_TYPES
        assert "Aerospace" in (result.subject or "")


class TestCataloguesAreNotProgrammes:
    @pytest.mark.parametrize("stem", ["delft-catalog", "toronto-datacs"])
    def test_they_do_not_classify_as_a_programme(self, stem):
        assert classify(stem).page_type not in PROGRAMME_TYPES

    def test_a_real_catalogue_still_reads_as_a_catalogue(self):
        """Delft's bachelor list links to seventeen *sibling* programmes.

        The fix must not make every listing page look like a programme.
        """
        assert classify("delft-catalog").page_type is PageType.PROGRAM_CATALOG

    def test_a_subject_area_hub_is_not_a_programme(self):
        """Toronto's "Data & Computer Science" spans three campuses and links
        out to programmes; it is a hub, not a programme."""
        assert classify("toronto-datacs").page_type not in PROGRAMME_TYPES


class TestPagesThatMustNeverBeProgrammes:
    @pytest.mark.parametrize("stem", [
        "rug-campus-tour", "rug-news", "delft-scholarship-index",
        "delft-vaneffen", "clip-scholarship",
    ])
    def test_they_are_not_programmes(self, stem):
        assert classify(stem).page_type not in PROGRAMME_TYPES

    def test_the_scholarship_index_is_an_index(self):
        assert classify("delft-scholarship-index").page_type is PageType.SCHOLARSHIP_INDEX

    @pytest.mark.parametrize("stem", ["delft-vaneffen", "clip-scholarship"])
    def test_named_awards_are_awards(self, stem):
        assert classify(stem).page_type is PageType.SCHOLARSHIP_AWARD


class TestSignalsAreTruthful:
    """A classification has to say what actually decided it.

    The catalogue branch reported "plural catalogue heading" for every page it
    fired on, including pages whose heading is "BSc Aerospace Engineering". A
    signal list that does not describe the rule that fired is misinformation in
    the evidence panel.
    """

    def test_a_catalogue_does_not_claim_a_plural_heading_it_does_not_have(self):
        result = classify("toronto-datacs")
        joined = " ".join(result.signals).lower()
        if "plural catalogue heading" in joined:
            from bs4 import BeautifulSoup

            from app.adapters.page_classifier import (
                _PLURAL_PROGRAM_HEADING,
                _identity,
                main_content,
            )
            soup = main_content(BeautifulSoup(
                (FIXTURES / "toronto-datacs.html").read_text(), "lxml"))
            assert _PLURAL_PROGRAM_HEADING.match(_identity(soup, result.title)), (
                "reported a plural catalogue heading that the page does not have"
            )

    def test_every_signal_is_non_empty(self):
        for stem in SOURCE_URL:
            result = classify(stem)
            assert result.signals, f"{stem} produced no signals at all"
            assert all(s.strip() for s in result.signals), f"{stem} has a blank signal"


# --- adversarial structures ------------------------------------------------


def page(body: str, *, head: str = "", title: str = "T") -> str:
    return f"<html><head><title>{title}</title>{head}</head><body>{body}</body></html>"


PROGRAMME_BODY = (
    "<p>This three-year bachelor's degree programme is taught in English. "
    "Entry requirements include IELTS 6.5 overall, and the curriculum covers "
    "180 credits across six semesters. Applications close on 1 May.</p>"
    "<h2>Entry requirements</h2><p>A secondary school diploma and IELTS 6.5.</p>"
    "<h2>Curriculum</h2><p>Duration: three years, 180 ECTS credits.</p>"
)

LD_PROGRAM = (
    '<script type="application/ld+json">'
    '{"@context":"https://schema.org","@type":"EducationalOccupationalProgram",'
    '"name":"BSc Computer Science"}</script>'
)


class TestAdversarialStructures:
    def test_structured_data_planted_in_navigation_cannot_invent_a_programme(self):
        """A Course blob in the global menu describes a *linked* course.

        Structured data is only ever corroboration here: the page still has to
        name one programme in its own content region.
        """
        html = page(
            f"<nav>{LD_PROGRAM}<a href='/programmes/x'>Programmes</a></nav>"
            "<main><h1>Student life</h1><p>Clubs, sport and housing at our "
            "campus for everyone who studies here.</p></main>"
        )
        assert classify_page(url="https://uni.edu/student-life", html=html).page_type \
            not in PROGRAMME_TYPES

    def test_a_page_with_no_h1_falls_back_to_its_title(self):
        html = page(
            "<main>" + PROGRAMME_BODY + "</main>",
            head=LD_PROGRAM, title="BSc Computer Science - University",
        )
        result = classify_page(url="https://uni.edu/programmes/cs", html=html)
        assert result.page_type in PROGRAMME_TYPES
        assert result.subject

    def test_malformed_html_does_not_raise(self):
        broken = "<html><body><main><h1>BSc Computer Science<p>unclosed " + PROGRAMME_BODY
        result = classify_page(url="https://uni.edu/programmes/cs", html=broken)
        assert result.page_type is not None

    def test_malformed_structured_data_is_ignored_not_fatal(self):
        html = page(
            "<main><h1>BSc Computer Science</h1>" + PROGRAMME_BODY + "</main>",
            head='<script type="application/ld+json">{not json at all</script>',
        )
        assert classify_page(url="https://uni.edu/programmes/cs", html=html).page_type \
            in PROGRAMME_TYPES

    def test_a_research_project_page_is_not_a_programme(self):
        html = page(
            "<main><h1>MSc and BSc projects</h1><p>Available graduation projects "
            "in our group. Contact the supervisor listed beside each project.</p>"
            "</main>", title="MSc and BSc projects | Zernike Institute",
        )
        assert classify_page(
            url="https://uni.edu/research/zernike/group/msc-and-bsc-projects", html=html,
        ).page_type not in PROGRAMME_TYPES

    def test_a_departmental_programme_page_is_still_a_programme(self):
        """Programmes often live on a faculty subdomain rather than the main site."""
        html = page(
            "<main><h1>BSc Computer Science</h1>" + PROGRAMME_BODY + "</main>",
            title="BSc Computer Science | School of Computing",
        )
        assert classify_page(
            url="https://cs.uni.edu/education/undergraduate/bsc-computer-science", html=html,
        ).page_type in PROGRAMME_TYPES

    def test_a_related_programmes_block_does_not_make_a_catalogue(self):
        related = "".join(
            f"<a href='/en/programmes/bachelors/other-{i}'>Other programme {i}</a>"
            for i in range(6)
        )
        html = page(
            "<main><h1>BSc Computer Science</h1>" + PROGRAMME_BODY
            + f"<section><h2>Related programmes</h2>{related}</section></main>"
        )
        result = classify_page(
            url="https://uni.edu/en/programmes/bachelors/computer-science", html=html)
        assert result.page_type in PROGRAMME_TYPES
        assert any("names only one" in s for s in result.signals)

    def test_a_catalogue_titled_after_one_entry_is_still_a_catalogue(self):
        """The failure mode the sibling-link rule could have introduced.

        Twelve or more distinct other programmes is a listing whatever the
        heading claims.
        """
        entries = "".join(
            f"<a href='/en/programmes/bachelors/prog-{i}'>Programme {i}</a>"
            for i in range(14)
        )
        html = page(
            f"<main><h1>BSc Computer Science</h1><p>Browse our degrees.</p>{entries}</main>"
        )
        assert classify_page(
            url="https://uni.edu/en/programmes/bachelors", html=html,
        ).page_type is PageType.PROGRAM_CATALOG

    def test_a_bare_degree_word_is_not_a_programme_name(self):
        """TU Delft's catalogue is headed "Bachelors"."""
        html = page("<main><h1>Bachelors</h1><p>Our bachelor programmes.</p></main>")
        assert classify_page(url="https://uni.edu/education/programmes/bachelors",
                             html=html).page_type not in PROGRAMME_TYPES

    def test_catalogue_phrasing_must_appear_within_one_heading(self):
        """The Toronto defect: `.*` bridged two unrelated headings.

        "…across our three campuses" and a later "Explore programs" combined
        into a catalogue match on a page whose headings say no such thing.
        """
        html = page(
            "<main><h1>BSc Computer Science</h1>"
            "<h2>Our teaching across three campuses</h2>" + PROGRAMME_BODY
            + "<h2>Explore programs</h2></main>"
        )
        result = classify_page(url="https://uni.edu/programmes/cs", html=html)
        assert result.page_type in PROGRAMME_TYPES


class TestRecruitmentIsNotAlwaysHiring:
    """In a university's own words, "recruitment" means students as often as staff.

    HKU publishes its joint admission route as the "HKU-Cambridge Undergraduate
    Recruitment Scheme". The irrelevance rule read the word as staff hiring and
    threw the page away.
    """

    @pytest.mark.parametrize("title", [
        "HKU-Cambridge Undergraduate Recruitment Scheme (Engineering)",
        "Student recruitment and admissions",
        "Undergraduate recruitment",
    ])
    def test_student_recruitment_is_not_discarded(self, title):
        html = page(f"<main><h1>{title}</h1>{PROGRAMME_BODY}</main>", title=title)
        assert classify_page(url="https://uni.edu/programmes/x", html=html).page_type \
            is not PageType.IRRELEVANT

    @pytest.mark.parametrize("title", [
        "Staff recruitment",
        "Recruitment and careers at the university",
        "Academic recruitment - vacancies",
    ])
    def test_staff_recruitment_is_still_discarded(self, title):
        html = page(f"<main><h1>{title}</h1><p>Apply for a post with us.</p></main>",
                    title=title)
        assert classify_page(url="https://uni.edu/about/x", html=html).page_type \
            is PageType.IRRELEVANT
