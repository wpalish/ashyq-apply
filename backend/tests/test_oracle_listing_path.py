"""The oracle reads a listing page's programme existence as the adapter does."""

from __future__ import annotations

from datetime import UTC, datetime

from evaluation.research.oracle import _claims_on

#: The shape of HKU's certified source: an admissions entry named for an area
#: that lists several full degree titles, one of them the requested programme.
LISTING = """<html><head><title>Computing and Data Science | Admissions</title></head>
<body><main><h1>Computing and Data Science</h1>
<p>CODE 6999. STUDY PERIOD 4-year.</p>
<p>The Bachelor of Engineering in Computer Science covers a comprehensive curriculum.</p>
<p>The Bachelor of Engineering in Artificial Intelligence and Data Science is also offered.</p>
</main></body></html>"""

WHEN = datetime(2026, 9, 28, tzinfo=UTC)


def test_existence_is_read_from_a_listing_by_the_requested_field() -> None:
    _, gated, _ = _claims_on("https://x.edu/cds", LISTING, WHEN, "computer science", "bachelor")
    assert ("programme.exists", True) in gated


def test_without_the_request_nothing_is_claimed() -> None:
    _, gated, ungated = _claims_on("https://x.edu/cds", LISTING, WHEN)
    assert ("programme.exists", True) not in gated + ungated


def test_a_listing_naming_only_another_field_confirms_nothing() -> None:
    _, gated, _ = _claims_on(
        "https://x.edu/cds", LISTING, WHEN, "mechanical engineering", "bachelor"
    )
    assert ("programme.exists", True) not in gated


def test_the_oracle_reads_the_stated_teaching_language_as_the_adapter_does():
    from datetime import UTC, datetime

    from evaluation.research.oracle import _claims_on

    html = (
        "<html><head><title>Computer Science (BSc) | University</title></head><body>"
        "<h1>Bachelor of Science in Computer Science</h1>"
        "<p>Language of instruction: German. Duration: 6 semesters.</p></body></html>"
    )
    _type, gated, ungated = _claims_on(
        "https://www.example.ac.at/en/computer-science", html, datetime(2026, 9, 28, tzinfo=UTC)
    )
    assert ("programme.language", "German") in gated
    assert ("programme.exists", True) in gated
