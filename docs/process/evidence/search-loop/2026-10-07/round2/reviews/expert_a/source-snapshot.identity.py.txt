"""Read the six identity dimensions off a candidate, and leave the rest UNKNOWN.

The rule that turns six verdicts into a decision lives in
``app.domain.programme_identity``. This module only reads evidence: what the
URL says, what the title says, what the page text states outright.

Its discipline is the whole value. A dimension the page does not establish
stays ``UNKNOWN``. It is always possible to guess — a page under ``/bachelor/``
is *probably* a bachelor page, a catalogue entry is *probably* active — and
every one of those guesses is how a claim ends up attached to the wrong year
or the wrong level. The benchmark already measured the cost: five out of five
claims were the right fact in the wrong scope.

So: confirm from something stated, refute from something stated, and otherwise
say so.
"""

from __future__ import annotations

import re

from app.adapters.discovery.live_discovery import degree_level_named, same_institution
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.ontology import Relation, retrieval_candidates
from app.domain.programme_identity import ProgrammeIdentity, Verdict

#: Wording that says a programme is no longer running. Only explicit phrases:
#: a page can be old without saying anything about the programme's status.
_DISCONTINUED = re.compile(
    r"\b(discontinued|no longer (?:offered|available|recruiting|accepting)|"
    r"has been (?:withdrawn|closed)|closed to (?:new )?applications|"
    r"final intake|last intake|suspended)\b",
    re.IGNORECASE,
)

#: Wording that says it is running and taking applications.
_ACTIVE = re.compile(
    r"\b(now accepting applications|applications? (?:are )?open|apply now|"
    r"currently (?:offered|recruiting)|admissions? (?:are )?open)\b",
    re.IGNORECASE,
)

#: A page establishes a programme exists when it presents itself as one.
_PROGRAMME_PAGE = re.compile(
    r"\b(programme|program|degree|bachelor|master|curriculum|study plan|"
    r"course structure|entry requirements|admission requirements)\b",
    re.IGNORECASE,
)


def _intake_verdict(text: str, intake_year: int | None) -> tuple[Verdict, str]:
    """Whether the page supports the requested intake year.

    A year appearing on a page is not the same as that year's intake being
    offered, so a bare mention is not a YES. Only an explicit statement about
    starting or entry in that year counts, and an explicit statement that it
    is not offered counts against.
    """
    if intake_year is None:
        return Verdict.UNKNOWN, "no intake was requested"

    year = str(intake_year)

    # The negative is checked first, and that order is load-bearing. "There is
    # no intake in 2027" contains "intake ... 2027" and matched the positive
    # pattern, so the page's denial was read as its confirmation — which is
    # precisely how a wrong-scope claim is born. A test pins this.
    not_offered = re.search(
        rf"\bno\b[^.]{{0,30}}\b(?:intake|entry|admission)\b[^.]{{0,30}}\b{year}\b"
        rf"|\b{year}\b[^.]{{0,30}}\bno\b[^.]{{0,20}}\b(?:intake|entry|admission)\b",
        text,
        re.IGNORECASE,
    )
    if not_offered:
        return Verdict.NO, f"the page states there is no {year} intake"

    offered = re.search(
        rf"\b(?:start(?:ing|s)?|entry|intake|admission|commenc\w+|cohort)\b[^.]{{0,40}}\b{year}\b"
        rf"|\b{year}\b[^.]{{0,40}}\b(?:start|entry|intake|admission|cohort)\b",
        text,
        re.IGNORECASE,
    )
    if offered:
        return Verdict.YES, f"the page states entry for {year}"

    if year in text:
        return Verdict.UNKNOWN, f"{year} appears on the page but not as an intake"
    return Verdict.UNKNOWN, f"the page does not mention {year}"


def _field_verdict(haystack: str, intent: DiscoveryIntent) -> tuple[Verdict, str]:
    """Whether the page's programme is the requested field.

    A neighbouring field is an explicit ``NO``, not an ``UNKNOWN``: a page that
    clearly says Data Science has established what it is, and it is not the
    computer science that was asked for. That is the judgement the corpus made
    by hand for Aalto twice.
    """
    terms = retrieval_candidates(intent.field)
    for candidate in terms:
        if candidate.relation is not Relation.RELATED and candidate.term.lower() in haystack:
            return Verdict.YES, f"names {candidate.term!r}"
    for candidate in terms:
        if candidate.relation is Relation.RELATED and candidate.term.lower() in haystack:
            return (
                Verdict.NO,
                f"names {candidate.term!r}, which is a neighbouring field and not the one requested",
            )
    return Verdict.UNKNOWN, "the page does not name the field"


def verify_candidate(
    *,
    url: str,
    intent: DiscoveryIntent,
    title: str = "",
    text: str = "",
) -> ProgrammeIdentity:
    """The six dimensions, each from stated evidence or left UNKNOWN."""
    haystack = f"{title} {url}".lower()
    body = f"{title}\n{text}"
    reasons: list[tuple[str, str]] = []

    if _PROGRAMME_PAGE.search(body) or _PROGRAMME_PAGE.search(url):
        exists, why = Verdict.YES, "the page presents itself as a programme"
    else:
        exists, why = Verdict.UNKNOWN, "nothing on the page presents it as a programme"
    reasons.append(("exists", why))

    if same_institution(url, intent.domain):
        university, why = Verdict.YES, f"served from {intent.domain}"
    else:
        university, why = Verdict.NO, f"not served from {intent.domain}"
    reasons.append(("university", why))

    named_level = degree_level_named(url) or degree_level_named(f"/{title.lower()}/")
    if named_level is None:
        degree, why = Verdict.UNKNOWN, "no degree level is named"
    elif named_level == str(intent.degree):
        degree, why = Verdict.YES, f"names {named_level}"
    else:
        degree, why = Verdict.NO, f"names {named_level}, not {intent.degree}"
    reasons.append(("degree_level", why))

    field, why = _field_verdict(haystack, intent)
    reasons.append(("field", why))

    if _DISCONTINUED.search(body):
        active, why = Verdict.NO, "the page says the programme is not running"
    elif _ACTIVE.search(body):
        active, why = Verdict.YES, "the page says it is accepting applications"
    else:
        active, why = Verdict.UNKNOWN, "the page does not state whether it is running"
    reasons.append(("active", why))

    intake, why = _intake_verdict(body, intent.intake_year)
    reasons.append(("intake", why))

    return ProgrammeIdentity(
        exists=exists,
        university=university,
        degree_level=degree,
        field=field,
        active=active,
        intake=intake,
        reasons=tuple(reasons),
    )
