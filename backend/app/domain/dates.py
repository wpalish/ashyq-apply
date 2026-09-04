"""Parsing published dates without guessing which convention was used.

`03/04/2027` is 3 April to a British admissions office and 4 March to an
American one. The pipeline used to try `%d/%m/%Y` first and `%m/%d/%Y` second,
which silently picked one - and a deadline a month wrong is the difference
between applying and not applying at all.

A string whose two readings disagree is therefore refused. That is the
product's rule everywhere else: an unknown stays unknown.
"""

from __future__ import annotations

from datetime import date, datetime

#: Formats with no ambiguity: ISO, or a written-out month.
UNAMBIGUOUS_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
)

#: The two readings of a purely numeric d/m/y string.
NUMERIC_FORMATS = ("%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%d-%m-%Y", "%m-%d-%Y")

AMBIGUOUS_REASON = "date format ambiguous: d/m or m/d"


def parse_published_date(value: object) -> date | None:
    """A date, or None when the string cannot be read without guessing.

    None has two causes and the caller treats them the same way: the value was
    not a date at all, or it was a numeric date whose two readings differ.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    for fmt in UNAMBIGUOUS_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    readings = set()
    for fmt in NUMERIC_FORMATS:
        try:
            readings.add(datetime.strptime(text, fmt).date())
        except ValueError:
            continue
    if len(readings) == 1:
        # Only one reading is a valid date - "25/05/2027" has no 25th month.
        return readings.pop()
    return None


def is_ambiguous(value: object) -> bool:
    """Whether this string is a date that could be read two ways."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    for fmt in UNAMBIGUOUS_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return False
        except ValueError:
            continue
    readings = set()
    for fmt in NUMERIC_FORMATS:
        try:
            readings.add(datetime.strptime(text, fmt).date())
        except ValueError:
            continue
    return len(readings) > 1
