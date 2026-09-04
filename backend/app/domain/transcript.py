"""Reading an applicant's transcript into *suggestions*, never into a profile.

An applicant already holds a PDF carrying their grade average, its scale and
the date they finish school. Copying three numbers into a form by hand is where
digits get transposed, so this reads them out.

It only ever proposes. Nothing here writes to a profile, and every suggestion
carries the line it came from so the applicant confirms against their own
document rather than on trust. That is the same rule the pipeline follows with
a university's pages: a value with no source is not a value.

What it refuses to do matters more than what it reads:

* A grade average with no scale beside it is not offered at all. "4.82" is
  excellent out of 5, and a fail out of 100.
* A numeric date whose two readings differ is refused, exactly as
  `app.domain.dates` refuses it for a published deadline.
* A value above its own scale is a misread line, not a strong student.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.dates import parse_published_date

#: Scales real school systems actually use: 4 and 5 point averages, the Dutch
#: and Indian 10, the Danish 12, the French 20, and percentages. A "/3" is a
#: misread character rather than a grading system, and accepting it would turn
#: a scanning artefact into the number every later comparison rests on.
KNOWN_SCALES = (4.0, 5.0, 6.0, 7.0, 10.0, 12.0, 20.0, 100.0)

_AVERAGE_WORDS = r"(?:cumulative\s+)?(?:gpa|grade\s+point\s+average|average\s+mark|average\s+grade)"
_NUMBER = r"(\d{1,3}(?:[.,]\d{1,3})?)"
#: "3.85/4.00", "4.82 out of 5", "8.4 (scale 10)" - one statement, both halves.
_GPA = re.compile(
    rf"{_AVERAGE_WORDS}\s*[:\-]?\s*{_NUMBER}\s*(?:/|out\s+of|of|\(\s*scale\s*)\s*{_NUMBER}",
    re.IGNORECASE,
)

_GRADUATION_WORDS = r"(?:date\s+of\s+graduation|graduation\s+date|graduated\s+on)"
_DATE_TOKEN = (
    r"(\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"
)
_GRADUATION = re.compile(rf"{_GRADUATION_WORDS}\s*[:\-]?\s*{_DATE_TOKEN}", re.IGNORECASE)


@dataclass(frozen=True)
class Suggestion:
    """One proposed field, and the words it was read from.

    `field` is the dotted path the form uses, so the screen can put the value
    where it belongs without a second mapping table to keep in step.
    """

    field: str
    label: str
    value: object
    excerpt: str


def _number(raw: str) -> float:
    # "4,82" is how half of Europe writes it, including Kazakh documents.
    return float(raw.replace(",", "."))


def suggest_from_transcript(text: str) -> list[Suggestion]:
    """Everything the document says plainly, and nothing it merely implies."""
    # Collapsed to single spaces: a transcript wraps mid-sentence, and an
    # excerpt has to be quotable back to the applicant as one line.
    flat = " ".join((text or "").split())
    if not flat:
        return []

    suggestions: list[Suggestion] = []

    match = _GPA.search(flat)
    if match:
        value, scale = _number(match.group(1)), _number(match.group(2))
        if scale in KNOWN_SCALES and 0 < value <= scale:
            suggestions.append(
                Suggestion(
                    field="academics.gpa",
                    label="Grade average",
                    value={
                        "raw_value": value,
                        "raw_scale_max": scale,
                        # The label is the applicant's to choose: the document
                        # says what the numbers are, not what the system is
                        # called on the form.
                        "raw_scale_label": "",
                    },
                    excerpt=match.group(0),
                )
            )

    match = _GRADUATION.search(flat)
    if match:
        parsed = parse_published_date(match.group(1).strip().rstrip(","))
        if parsed is not None:
            suggestions.append(
                Suggestion(
                    field="context.graduation_date",
                    label="Graduation date",
                    value=parsed.isoformat(),
                    excerpt=match.group(0),
                )
            )

    return suggestions
