"""Plan rule DL-5 (core-gap analysis 2026-10-18 §3 change 5): the deadline and the
tuition are read from the requested intake's own section of the page.

DL-5 absorbs EX-2 (``DEADLINE_WINDOW_SCOPE``): on, EX-2's study-period and
intake-section rules apply whatever EX-2's flag says, plus calendar-year intake
headings, "closing date(s)" as a deadline label, the requested intake's row of a
table of intakes, and the section's own tuition. The pages are the real ones,
hand-fetched 2026-10-18 for the core-gap analysis, trimmed to the markup that
decides (the Uppsala programme page's two intake panes, the Auckland BSc page's
"Key dates" block).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import app.adapters.extraction as extraction
from app.adapters.extraction import ClaimBuilder, extract_costs, extract_requirements, readable_text


def _uppsala_pane(index: int, intake: str, period: str, deadline: str) -> str:
    return (
        f'<div id="semesters-{index}" class="card-body tab-pane" role="tabpanel">'
        "<p>Expand the information below to show details on entry requirements, "
        "programme-specific documents, selection criteria and tuition fees.</p>"
        '<div class="sv-collapsible-content"><h3 class="uu-subheading m-0"><a href="#x">'
        f'<span><span><span class="visually-hidden">{intake}</span> '
        f'<span class="education-print-only">{intake}, </span>'
        "Uppsala, 100%, On-campus, Swedish</span></span></a></h3>"
        '<div class="toggle-section"><dl class="education-instance-info">'
        "<dt>Location</dt><dd>Uppsala</dd><dt>Pace of study</dt><dd>100%</dd>"
        f"<dt>Study period</dt><dd>{period}</dd>"
        "<dt>Language of instruction</dt><dd>Swedish</dd>"
        "<dt>Fees</dt><dd>If you are not a citizen of a European Union (EU) or European "
        "Economic Area (EEA) country, or Switzerland, you are required to pay application "
        'and tuition fees. <div class="pt-2"><ul>'
        '<li>First tuition fee instalment: <span class="is-nowrap">SEK 75,000</span></li> '
        '<li>Total tuition fee: <span class="is-nowrap">SEK 450,000</span></li></ul>'
        '<p><a href="/en/study/fees">Read more about fees.</a></p></div></dd>'
        f"<dt>Application deadline</dt><dd>{deadline}</dd>"
        "<dt>Application code</dt><dd>UU-P1100</dd></dl>"
        '<div><a href="https://www.antagning.se/se/search/public">Apply now</a></div>'
        "</div></div></div>"
    )


#: https://www.uu.se/en/study/programme/bachelors-programme-computer-science
UPPSALA_HTML = (
    "<html><head><title>Bachelor's Programme in Computer Science | Uppsala University"
    "</title></head><body><main><h1>Bachelor's Programme in Computer Science</h1>"
    "<p>180 credits</p>"
    '<div class="education"><h2 class="mb-3">Application and entry requirements</h2>'
    '<nav aria-label="Semesters"><ul class="nav nav-tabs" role="tablist">'
    '<li class="nav-item"><button type="button">Autumn 2026</button> </li>'
    '<li class="nav-item"><button type="button">Autumn 2027</button> </li></ul></nav>'
    '<div class="card tab-card tab-content">'
    + _uppsala_pane(
        0, "Autumn 2026", "31&nbsp;August&nbsp;2026–3&nbsp;June&nbsp;2029", "15 April 2026"
    )
    + _uppsala_pane(
        1, "Autumn 2027", "30&nbsp;August&nbsp;2027–9&nbsp;June&nbsp;2030", "15 April 2027"
    )
    + "</div></div>"
    '<h2 class="uu-subheading m-0">Programme syllabus</h2><ul>'
    '<li><a href="/en/study/programme-syllabus?query=1">Programme syllabus valid from '
    "Autumn 2026</a></li></ul></main></body></html>"
)

#: https://www.auckland.ac.nz/en/study/study-options/find-a-study-option/bachelor-of-science-bsc.html
AUCKLAND_HTML = (
    "<html><head><title>Bachelor of Science (BSc) - The University of Auckland</title>"
    "</head><body><main><h1>Bachelor of Science (BSc)</h1>"
    "<p>Full-time: 3 years</p><p>Next start date</p>"
    "<p>2027 Semester One – 1 March</p><p>2027 Semester Two – 19 July</p>"
    "<h2>Key dates</h2>"
    '<p class="sub">Please note: We will consider late applications if places are still '
    "available. International students should start the application process as early as "
    "possible to allow sufficient time to apply for a visa.</p>"
    '<div class="text"><h3>Application closing dates</h3><div class="closing-dates">'
    '<div class="closing-dates__container"><dl class="closing-dates__list">'
    '<dt class="closing-dates__heading">Summer School 2027</dt><dd>1 December 2026</dd>'
    '</dl></div><div class="closing-dates__container"><dl class="closing-dates__list">'
    '<dt class="closing-dates__heading">Semester One 2027</dt><dd>8 December 2026</dd>'
    '</dl></div><div class="closing-dates__container"><dl class="closing-dates__list">'
    '<dt class="closing-dates__heading">Semester Two 2027</dt><dd>4 July 2027</dd>'
    "</dl></div></div></div>"
    '<div class="text"><h3>Start dates</h3><p>Here are the start dates for the programme.</p>'
    "</div><h4>Start dates for 2027</h4><dl><dt>Summer School</dt><dd>Starts – 6 January</dd>"
    "<dd>Ends – 17 February</dd><dt>Semester One</dt><dd>Starts – 1 March</dd>"
    "<dd>Ends – 28 June</dd><dt>Semester Two</dt><dd>Starts – 19 July</dd>"
    "<dd>Ends – 15 November</dd></dl></main></body></html>"
)

UPPSALA_URL = "https://www.uu.se/en/study/programme/bachelors-programme-computer-science"
AUCKLAND_URL = (
    "https://www.auckland.ac.nz/en/study/study-options/find-a-study-option/"
    "bachelor-of-science-bsc.html"
)


def _builder(url: str, text: str, intake: str | None) -> ClaimBuilder:
    builder = ClaimBuilder(
        source_url=url,
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 10, 18, tzinfo=UTC),
        intake=intake,
        page_text=text,
    )
    builder.requested_academic_year = "2027/28"
    return builder


def deadlines(html: str, url: str, intake: str | None = "fall 2027") -> list[str]:
    text = readable_text(html)
    builder = _builder(url, text, intake)
    extract_requirements(text, builder)
    return [
        str(c.normalized_value)
        for c in builder.claims
        if c.claim_type.value == "admission_deadline"
    ]


def tuition(html: str, url: str, intake: str | None = "fall 2027") -> list[object]:
    text = readable_text(html)
    builder = _builder(url, text, intake)
    extract_costs(text, builder)
    return [c.normalized_value for c in builder.claims if c.claim_type.value == "tuition"]


@pytest.fixture
def dl5(monkeypatch):
    monkeypatch.setattr(extraction, "INTAKE_SECTION_DEADLINE", True)


def test_on_by_default():
    # DL-5 is on by default; EX-2's own flag stays off, its rules absorbed.
    assert extraction.INTAKE_SECTION_DEADLINE is True
    assert extraction.DEADLINE_WINDOW_SCOPE is False
    assert deadlines(UPPSALA_HTML, UPPSALA_URL) == ["2027-04-15"]
    assert tuition(UPPSALA_HTML, UPPSALA_URL) == []
    assert deadlines(AUCKLAND_HTML, AUCKLAND_URL) == ["2026-12-08"]


class TestOffIsUnchanged:
    @pytest.fixture(autouse=True)
    def off(self, monkeypatch):
        monkeypatch.setattr(extraction, "INTAKE_SECTION_DEADLINE", False)

    def test_uppsala_study_periods_still_block_the_deadline_and_no_tuition(self):
        assert deadlines(UPPSALA_HTML, UPPSALA_URL) == []
        assert tuition(UPPSALA_HTML, UPPSALA_URL) == []

    def test_auckland_closing_dates_are_not_a_deadline(self):
        assert deadlines(AUCKLAND_HTML, AUCKLAND_URL) == []


class TestUppsala:
    def test_the_requested_intakes_deadline(self, dl5):
        assert deadlines(UPPSALA_HTML, UPPSALA_URL, "fall 2027") == ["2027-04-15"]
        assert deadlines(UPPSALA_HTML, UPPSALA_URL, "Autumn 2026") == ["2026-04-15"]

    def test_an_intake_without_a_section_claims_nothing(self, dl5):
        assert deadlines(UPPSALA_HTML, UPPSALA_URL, "fall 2028") == []
        assert deadlines(UPPSALA_HTML, UPPSALA_URL, None) == []

    def test_the_sections_total_tuition_is_not_a_years_fee(self, dl5):
        # DL-5b: "Total tuition fee: SEK 450,000" is the whole programme's
        # fee and "First tuition fee instalment: SEK 75,000" one part of it;
        # neither is a year's tuition, and neither is converted into one.
        assert tuition(UPPSALA_HTML, UPPSALA_URL) == []
        assert deadlines(UPPSALA_HTML, UPPSALA_URL) == ["2027-04-15"]

    def test_no_tuition_for_an_intake_without_a_section(self, dl5):
        assert tuition(UPPSALA_HTML, UPPSALA_URL, "fall 2028") == []

    def test_ex2_alone_still_reads_no_tuition(self, monkeypatch):
        monkeypatch.setattr(extraction, "DEADLINE_WINDOW_SCOPE", True)
        assert deadlines(UPPSALA_HTML, UPPSALA_URL) == ["2027-04-15"]
        assert tuition(UPPSALA_HTML, UPPSALA_URL) == []

    def test_the_excerpt_stays_inside_the_section(self, dl5):
        text = readable_text(UPPSALA_HTML)
        builder = _builder(UPPSALA_URL, text, "fall 2027")
        extract_requirements(text, builder)
        (claim,) = [c for c in builder.claims if c.claim_type.value == "admission_deadline"]
        assert "15 April 2027" in claim.original_text_excerpt
        assert "15 April 2026" not in claim.original_text_excerpt


_UPPSALA_TOTAL = '<li>Total tuition fee: <span class="is-nowrap">SEK 450,000</span></li>'


class TestSectionTuitionNeedsAYearsFee:
    """DL-5b: the section's tuition is claimed only when its amount says it is
    one year's fee; a whole programme's price, or an amount with no period,
    is abstained on and never converted."""

    @pytest.mark.parametrize(
        ("fee", "claimed"),
        [
            ("Tuition fee: SEK 150,000 per year", {"amount": 150000.0, "currency": "SEK"}),
            ("Annual tuition fee: SEK 150,000", {"amount": 150000.0, "currency": "SEK"}),
            (
                "Tuition fee per academic year: SEK 150,000",
                {"amount": 150000.0, "currency": "SEK"},
            ),
            ("Tuition fee: SEK 150,000", None),
            ("Tuition fee: SEK 75,000 per semester", None),
            ("Tuition fee for the whole programme: SEK 450,000", None),
            ("Tuition fee: SEK 450,000 for the full programme", None),
            ("Full programme tuition fee: SEK 450,000", None),
            ("Total tuition fee: SEK 150,000 per year", None),
        ],
    )
    def test_only_a_years_fee_is_claimed(self, dl5, fee, claimed):
        html = UPPSALA_HTML.replace(_UPPSALA_TOTAL, f"<li>{fee}</li>")
        assert html != UPPSALA_HTML
        assert tuition(html, UPPSALA_URL) == ([claimed] if claimed else [])
        assert deadlines(html, UPPSALA_URL) == ["2027-04-15"]


class TestAuckland:
    def test_fall_reads_the_semester_one_row(self, dl5):
        assert deadlines(AUCKLAND_HTML, AUCKLAND_URL, "fall 2027") == ["2026-12-08"]

    def test_the_excerpt_quotes_the_label_and_the_row(self, dl5):
        text = readable_text(AUCKLAND_HTML)
        builder = _builder(AUCKLAND_URL, text, "fall 2027")
        extract_requirements(text, builder)
        (claim,) = [c for c in builder.claims if c.claim_type.value == "admission_deadline"]
        assert "Application closing dates" in claim.original_text_excerpt
        assert "Semester One 2027 8 December 2026" in claim.original_text_excerpt
        assert "DL-5" in claim.notes

    def test_an_intake_with_no_row_claims_nothing(self, dl5):
        assert deadlines(AUCKLAND_HTML, AUCKLAND_URL, "fall 2028") == []
        assert deadlines(AUCKLAND_HTML, AUCKLAND_URL, None) == []

    def test_a_table_without_a_deadline_label_is_not_read(self, dl5):
        html = AUCKLAND_HTML.replace("Application closing dates", "Teaching periods")
        assert deadlines(html, AUCKLAND_URL) == []


class TestClosingDateLabel:
    def test_closing_date_is_a_deadline_label(self, dl5):
        text = "Applications for the BSc: closing date 1 December 2026 for all applicants."
        builder = _builder(AUCKLAND_URL, text, "fall 2027")
        extract_requirements(text, builder)
        values = [c.normalized_value for c in builder.claims]
        assert values == ["2026-12-01"]

    def test_off_closing_date_is_not_read(self, monkeypatch):
        monkeypatch.setattr(extraction, "INTAKE_SECTION_DEADLINE", False)
        text = "Applications for the BSc: closing date 1 December 2026 for all applicants."
        builder = _builder(AUCKLAND_URL, text, "fall 2027")
        extract_requirements(text, builder)
        assert builder.claims == []

    def test_an_award_closing_date_is_still_not_the_admission_deadline(self, dl5):
        text = "Scholarship applications: closing date 1 October 2026."
        builder = _builder(AUCKLAND_URL, text, "fall 2027")
        extract_requirements(text, builder)
        assert builder.claims == []


def test_study_periods_never_trip_the_several_windows_guard(dl5):
    text = (
        "Study period\n30 August 2027–9 June 2030\n"
        "Semester dates\n30 August 2027 – 16 January 2028\n"
        "Application deadline\n15 April 2027\n"
    )
    builder = _builder(UPPSALA_URL, text, "fall 2027")
    extract_requirements(text, builder)
    assert [c.normalized_value for c in builder.claims] == ["2027-04-15"]
