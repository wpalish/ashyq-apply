"""Reading a page's own statement of who it is for.

:mod:`app.domain.claim_scope` gave scope a shape. This module is the only
thing that fills it, and it fills it from one source: sentences the page
actually wrote. It never derives a dimension from the URL, from the candidate
we happened to be researching, or from the programme record that sent us
here. Those are what *we* were asking about; scope is what the *page*
answered, and the whole point of the wrong-scope measurement is that the two
are not the same.

Two rules keep it honest.

**Silence stays silent.** A dimension with no matching phrase comes back
``None``. ``ClaimScope`` already treats that as "the page did not say", which
is the only reading that cannot manufacture coverage.

**Ambiguity is silence too.** A page that names both international and
domestic applicants is not scoped to either, so a dimension with more than
one distinct value comes back ``None`` rather than the first or the nearest
match. This loses scope we could have guessed at; guessing is the failure
this module exists to stop.

Four of the nine dimensions are deliberately never read here:

``university``, ``faculty``, ``programme``
    A page states these in its own markup and navigation, which V2-17's
    identity work already reads and verifies. Re-deriving them from prose
    would give a second, weaker answer to a question that has a stronger one.

``nationality``
    No phrase family survived review. "Applicants from Kazakhstan" is a
    nationality; "applicants from partner universities" is not, and the two
    are the same sentence shape. Until there is a pattern that cannot read
    one as the other, this stays unread rather than wrong.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.domain.claim_scope import ClaimScope

#: How far back a negation may sit and still govern a phrase. Long enough for
#: "this scholarship is not available to international applicants", short
#: enough that the previous sentence cannot reach across a full stop — the
#: pattern below forbids one.
_NEGATION_RADIUS = 60

_NEGATION = re.compile(
    # ``do(es) not <verb>`` is deliberately open-ended: "does not start in
    # September 2026" negates as surely as "does not apply to". Reading a
    # negated clause as a scope is the expensive mistake; suppressing a real
    # scope because a nearby clause was negative only costs silence, which is
    # what an unread dimension already is.
    r"(?:not\s+(?:available|open|applicable)|do(?:es)?\s+not\s+\w+"
    rf"|except|excluding|other\s+than|rather\s+than)[^.\n]{{0,{_NEGATION_RADIUS}}}$",
    re.IGNORECASE,
)

_ACADEMIC_YEAR = re.compile(r"\b(20\d{2})\s*[/–—-]\s*(20\d{2}|\d{2})\b")
#: A year range scopes the page only when something says it is *the* year.
#: A bare one is usually attached to a single figure — Toronto's demo award
#: says it is "worth CAD 89,000 per year for 2024/25" on a 2026/27 page, and
#: without this the deadline, the coverage and the renewal rules on that page
#: all came back scoped to 2024/25. The same mistake as a deadline read as an
#: intake, one dimension over.
_YEAR_MARKER = re.compile(
    r"\b(?:academic\s+(?:year|session)|study\s+year|year\s+of\s+entry|entry|intake|admission)\b",
    re.IGNORECASE,
)

_SEASONS = {
    "fall": "Fall",
    "autumn": "Fall",
    "spring": "Spring",
    "summer": "Summer",
    "winter": "Winter",
}
_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_INTAKE_TERM = "|".join((*_SEASONS, *_MONTHS))
_SEASON_TERM = "|".join(_SEASONS)
_MONTH_TERM = "|".join(_MONTHS)
#: A season and a year name a term by themselves: nothing else on an
#: admissions page is written "Fall 2026".
_INTAKE_SEASON = re.compile(rf"\b({_SEASON_TERM})\s+(20\d{{2}})\b", re.IGNORECASE)
#: A month and a year do not. "15 January 2027" is a deadline, and reading it
#: as an intake is the exact move this module exists to refuse — the first
#: draft did it, and put a deadline date into 39 demo claims as their intake.
#: So a month counts only when a day number is not in front of it *and* an
#: intake word stands beside it.
_INTAKE_MONTH = re.compile(rf"(?<!\d)(?<!\d )\b({_MONTH_TERM})\s+(20\d{{2}})\b", re.IGNORECASE)
_INTAKE_MARKER = re.compile(
    r"\b(?:intake|entry|admission|semester|term|start(?:s|ing)?|commenc\w+)\b", re.IGNORECASE
)
#: How far an intake word may stand from the month it governs.
_MARKER_RADIUS = 40
_INTAKE_REVERSED = re.compile(
    rf"\b(20\d{{2}})\s+({_INTAKE_TERM})\s+(?:intake|entry)\b", re.IGNORECASE
)

_DEGREE_WORDS = {
    "bachelor": "bachelor",
    "bachelors": "bachelor",
    "bachelor's": "bachelor",
    "undergraduate": "bachelor",
    "bsc": "bachelor",
    "beng": "bachelor",
    "master": "master",
    "masters": "master",
    "master's": "master",
    "postgraduate": "master",
    "msc": "master",
    "meng": "master",
    "phd": "doctorate",
    "doctoral": "doctorate",
    "doctorate": "doctorate",
}
#: A degree word only scopes the page when it is attached to the thing being
#: described. "Master's programme" scopes; "our master's graduates work at"
#: does not, and a bare "master" anywhere on the page scopes nothing.
_DEGREE = re.compile(
    r"\b(bachelor(?:'?s)?|undergraduate|bsc|beng|master(?:'?s)?|postgraduate|msc|meng"
    r"|phd|doctoral|doctorate)\b[\s’'-]{0,3}"
    r"(?:degree\s+)?(?:programme|program|degree|studies|course|student|students|applicants)\b",
    re.IGNORECASE,
)

#: Ordered: the first pattern that matches wins for that phrase, so
#: "non-EU/EEA" is never read as "EU/EEA".
_POPULATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bnon[-\s]?(?:EU|EEA)(?:/(?:EU|EEA))?\b", re.IGNORECASE), "non-EU/EEA"),
    # The lookbehind is load-bearing: "-" is a word boundary, so without it
    # "non-EU/EEA" matches this pattern too and the page reads as naming two
    # populations when it named one.
    (
        re.compile(r"(?<!non-)(?<!non )\bEU\s*(?:/|and|&)\s*EEA\b", re.IGNORECASE),
        "EU/EEA",
    ),
    (
        re.compile(r"\binternational\s+(?:applicants|students|candidates)\b", re.IGNORECASE),
        "international",
    ),
    (re.compile(r"\b(?:domestic|home)\s+(?:applicants|students)\b", re.IGNORECASE), "domestic"),
    (re.compile(r"\btransfer\s+(?:applicants|students)\b", re.IGNORECASE), "transfer"),
    (
        re.compile(
            r"\b(?:first[-\s]year|freshman|freshmen)\s+(?:applicants|students)\b", re.IGNORECASE
        ),
        "first-year",
    ),
)

_RESIDENCIES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\boverseas\s+fee(?:s|\s+status)?\b", re.IGNORECASE), "overseas"),
    (re.compile(r"\bhome\s+fee(?:s|\s+status)?\b", re.IGNORECASE), "home"),
)


def _flatten(text: str) -> str:
    """Newlines to spaces, character for character.

    Same trick, and same reason, as ``extraction.for_matching``: a scope
    sentence wraps as readily as a requirement one, and every pattern here
    stays inside a sentence with ``[^.\\n]``.
    """
    return text.replace("\n", " ").replace("\r", " ")


def _negated(text: str, start: int) -> bool:
    return bool(_NEGATION.search(text[max(0, start - _NEGATION_RADIUS) : start]))


def _single(values: Iterable[str]) -> str | None:
    """The one value, or ``None`` when the page named none or several."""
    distinct = sorted(set(values))
    return distinct[0] if len(distinct) == 1 else None


def _academic_years(text: str) -> list[str]:
    found = []
    for m in _ACADEMIC_YEAR.finditer(text):
        if _negated(text, m.start()) or not _has_marker(text, m.start(), m.end(), _YEAR_MARKER):
            continue
        start, end = m.group(1), m.group(2)
        found.append(f"{start}/{end[-2:]}")
    return found


def _intakes(text: str) -> list[str]:
    found = []
    for m in _INTAKE_SEASON.finditer(text):
        if _negated(text, m.start()):
            continue
        found.append(f"{_term(m.group(1))} {m.group(2)}")
    for m in _INTAKE_MONTH.finditer(text):
        if _negated(text, m.start()) or not _has_marker(text, m.start(), m.end()):
            continue
        found.append(f"{_term(m.group(1))} {m.group(2)}")
    for m in _INTAKE_REVERSED.finditer(text):
        if _negated(text, m.start()):
            continue
        found.append(f"{_term(m.group(2))} {m.group(1)}")
    return found


def _has_marker(text: str, start: int, end: int, marker: re.Pattern[str] = _INTAKE_MARKER) -> bool:
    """Whether a scoping word stands beside this match."""
    window = text[max(0, start - _MARKER_RADIUS) : end + _MARKER_RADIUS]
    return bool(marker.search(window))


def _term(word: str) -> str:
    lowered = word.lower()
    return _SEASONS.get(lowered, lowered.capitalize())


def _degrees(text: str) -> list[str]:
    return [
        _DEGREE_WORDS[m.group(1).lower().replace("’", "'")]
        for m in _DEGREE.finditer(text)
        if not _negated(text, m.start()) and m.group(1).lower().replace("’", "'") in _DEGREE_WORDS
    ]


def _by_table(text: str, table: tuple[tuple[re.Pattern[str], str], ...]) -> list[str]:
    found = []
    for pattern, value in table:
        for m in pattern.finditer(text):
            if not _negated(text, m.start()):
                found.append(value)
    return found


def read_scope(text: str, *, title: str = "") -> ClaimScope:
    """What this page states about who and what it covers.

    ``title`` is scanned alongside the body because a page's own title is
    where a degree and an intake are most often stated outright, and it is
    the page's words as much as its prose is.
    """
    haystack = _flatten(f"{title}. {text}" if title else text)
    populations = _by_table(haystack, _POPULATIONS)
    # "non-EU/EEA" contains no "EU/EEA" match by construction, but a page may
    # state both in the same breath ("EU/EEA and non-EU/EEA applicants pay
    # different fees"). Two populations is two, and two is silence.
    return ClaimScope(
        degree=_single(_degrees(haystack)),
        intake=_single(_intakes(haystack)),
        academic_year=_single(_academic_years(haystack)),
        population=_single(populations),
        residency=_single(_by_table(haystack, _RESIDENCIES)),
    )
