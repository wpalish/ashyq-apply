"""Does this award apply to this applicant?

An award page that never mentions a degree level does not thereby apply to
every degree level. Each question below answers yes / no / unknown from an
explicit statement, and unknown is the default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

#: How each degree level is written on real pages.
DEGREE_SYNONYMS: dict[str, tuple[str, ...]] = {
    "bachelor": ("bachelor'?s?", r"b\.?sc\b", r"b\.?a\b", "beng", "llb", "undergraduate"),
    "master": ("master'?s?", r"m\.?sc\b", r"m\.?a\b", "meng", "llm", "mba", "mphil",
               "postgraduate taught", "graduate"),
    "phd": ("ph\\.?d", "doctoral", "doctorate", "dphil"),
    "foundation": ("foundation year", "foundation programme", "pre-?bachelor"),
}
_NEGATION = (
    r"not available for", r"not open to", r"does not apply to", r"excludes?",
    r"is not intended for", r"not eligible", r"unavailable to", r"other than",
)
_INCLUSION = (
    r"awarded to", r"open to", r"available to", r"for", r"intended for",
    r"who wish to pursue", r"enrolling in", r"enrolled in", r"pursuing", r"studying",
)


#: Mirrors app.schemas.result.Tristate; declared here to keep this module free
#: of a schema import.
Verdict = Literal["yes", "no", "unknown"]


@dataclass(frozen=True)
class Applicability:
    verdict: Verdict
    reason: str
    evidence: str = ""
    mentioned_degrees: tuple[str, ...] = ()


def _pattern_for(degree: str) -> str:
    return "|".join(DEGREE_SYNONYMS.get(degree, (re.escape(degree),)))


def _mentioned(text: str) -> tuple[str, ...]:
    return tuple(
        level for level, words in DEGREE_SYNONYMS.items()
        if re.search(rf"\b(?:{'|'.join(words)})\b", text, re.IGNORECASE)
    )


def assess_degree_applicability(text: str, requested_degree: str) -> Applicability:
    """Whether an award applies to the applicant's degree level."""
    flat = " ".join((text or "").split())
    if not flat or not requested_degree:
        return Applicability("unknown", "no text or no degree level to check against")

    wanted = _pattern_for(requested_degree)
    mentioned = _mentioned(flat)

    # An explicit exclusion of this level settles it.
    for negation in _NEGATION:
        match = re.search(
            rf"[^.]*\b{negation}\b[^.]{{0,60}}?\b(?:{wanted})\b[^.]{{0,60}}\.", flat, re.IGNORECASE
        )
        if match:
            return Applicability(
                "no",
                f"the page explicitly excludes {requested_degree} applicants",
                match.group(0).strip()[:400],
                mentioned,
            )

    # An explicit inclusion of this level settles it the other way.
    for inclusion in _INCLUSION:
        match = re.search(
            rf"[^.]*\b{inclusion}\b[^.]{{0,60}}?\b(?:{wanted})\b[^.]{{0,80}}\.", flat, re.IGNORECASE
        )
        if match and not any(
            re.search(rf"\b{n}\b", match.group(0), re.IGNORECASE) for n in _NEGATION
        ):
            return Applicability(
                "yes",
                f"the page states the award is for {requested_degree} applicants",
                match.group(0).strip()[:400],
                mentioned,
            )

    # The page talks about other levels and never this one: not applicable.
    others = [level for level in mentioned if level != requested_degree]
    if others and requested_degree not in mentioned:
        return Applicability(
            "no",
            f"the page describes the award for {', '.join(others)} only and never mentions "
            f"{requested_degree}",
            "",
            mentioned,
        )

    return Applicability(
        "unknown",
        "the page does not state which degree levels the award applies to",
        "",
        mentioned,
    )


#: An affirmative clause. A page merely *containing* the phrase "international
#: students" is not evidence — "few external scholarships are offered to
#: international students" is a discouragement, not an eligibility statement.
_INTERNATIONAL_YES = (
    re.compile(r"[^.]*\binternational (?:students?|applicants?|candidates?)\b[^.]{0,60}\b"
               r"(?:are eligible|may apply|can apply|are welcome to apply|are invited to apply)\b[^.]{0,60}\.", re.I),
    re.compile(r"[^.]*\bopen to\b[^.]{0,60}\b(?:international|non-?(?:eu|eea|domestic|resident)|all nationalities|students of any nationality)\b[^.]{0,60}\.", re.I),
    re.compile(r"[^.]*\b(?:students|applicants|candidates) of (?:all|any) nationalit(?:y|ies)\b[^.]{0,60}\.", re.I),
    re.compile(r"[^.]*\bavailable to international (?:students?|applicants?)\b[^.]{0,60}\.", re.I),
    re.compile(r"[^.]*\bawarded to\b[^.]{0,60}\b(?:excellent )?students from outside\b[^.]{0,60}\.", re.I),
)
_INTERNATIONAL_NO = (
    re.compile(r"[^.]*\bnot (?:open|available) to international (?:students?|applicants?)\b[^.]{0,60}\.", re.I),
    re.compile(r"[^.]*\b(?:domestic|home|national) (?:students?|applicants?) only\b[^.]{0,60}\.", re.I),
    re.compile(r"[^.]*\binternational (?:students?|applicants?)\b[^.]{0,40}\bnot eligible\b[^.]{0,60}\.", re.I),
)


def assess_international_eligibility(text: str) -> Applicability:
    """Yes only on an affirmative clause; no only on an explicit exclusion."""
    flat = " ".join((text or "").split())
    for pattern in _INTERNATIONAL_NO:
        match = pattern.search(flat)
        if match:
            return Applicability("no", "the page excludes international applicants",
                                 match.group(0).strip()[:400])
    for pattern in _INTERNATIONAL_YES:
        match = pattern.search(flat)
        if match:
            return Applicability("yes", "the page affirmatively admits international applicants",
                                 match.group(0).strip()[:400])
    return Applicability(
        "unknown",
        "the page contains no affirmative statement about international eligibility",
    )
