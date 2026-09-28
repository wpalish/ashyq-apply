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
