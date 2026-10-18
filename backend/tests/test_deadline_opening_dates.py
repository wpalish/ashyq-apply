"""The day something opens or is published is not the application deadline.

Wrong-claim analysis of 2026-10-18 (R-E): Imperial's
/study/apply/undergraduate/process/deadlines/ page (hand-fetched 2026-10-18)
gave "28 April 2026 – UCAS' search tool opens" as the deadline because it sits
under the heading "UCAS deadlines for 2027 entry". The fixture is cut from it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_requirements, for_matching

IMPERIAL_DEADLINES = (
    "Application deadlines and dates you need to know\n\n"
    "UCAS deadlines for 2027 entry\n\n"
    "28 April 2026 – UCAS’ search tool opens\n\n"
    "Undergraduate courses will be available to search in \nUCAS’ search tool\n.\n\n"
    "12 May 2026 – UCAS applications open\n\n"
    "You can register and start preparing your application in your \nUCAS Hub account\n"
    " – though you won’t be able to submit it to UCAS until 1 September 2026.\n\n"
    "1 September 2026 – Applications can be submitted\n\n"
    "Once you've completed your application, including your reference, you can submit "
    "it to UCAS.\n\n"
    "13 January 2027 (18.00 UK time) – Equal consideration deadline\n\n"
    "August 2027 (date to be confirmed) – A-level results published\n"
)


def _deadline(text: str) -> object:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    extract_requirements(for_matching(text), builder)
    got = {c.claim_type.value: c.normalized_value for c in builder.claims}
    return got.get("admission_deadline")


def test_imperials_search_tool_opening_is_not_the_deadline():
    assert _deadline(IMPERIAL_DEADLINES) != "2026-04-28"


@pytest.mark.parametrize(
    "text",
    [
        "Application deadline information: 1 October 2026 – applications open",
        "Deadlines: 1 October 2026 (12:00) – the portal opens",
        "Deadline page: applications can be submitted from 1 October 2026",
        "Key dates and deadlines: 20 August 2026 – results published",
    ],
)
def test_an_opening_or_publication_date_is_skipped(text):
    assert _deadline(text) is None


@pytest.mark.parametrize(
    ("text", "iso"),
    [
        ("Application deadline: 15 January 2027; applications open 1 October 2026", "2027-01-15"),
        (
            "Application deadline: applications can be submitted from 1 October 2026 "
            "until 15 January 2027",
            "2027-01-15",
        ),
        (
            "Applications for the August 2027 intake will open on 23 October 2026 "
            "and close on 15 July 2027.",
            "2027-07-15",
        ),
    ],
)
def test_a_deadline_beside_an_opening_date_is_still_read(text, iso):
    assert _deadline(text) == iso
