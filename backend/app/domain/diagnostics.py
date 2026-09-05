"""Telling a failure apart from an honest unknown.

Both used to land in `run.errors`, so a clean demo run showed 47 entries under
"Research limitations" - and every one of them was the product working exactly
as designed: a page that does not state an application window cannot be made to
state one. Mixing those with genuine fetch failures taught the applicant to
distrust a correct result.

The split is a presentation decision, not a change of substance: nothing is
hidden, and an unknown is still never converted into a value.
"""

from __future__ import annotations

import re
from enum import StrEnum

#: A page was not read: the network, the site or the parser stopped us.
_FAILURE_MARKERS = (
    "timeout",
    "timed out",
    "connect",
    "connection",
    "network",
    "dns",
    "ssl",
    "certificate",
    "http error",
    "http 4",
    "http 5",
    "status 4",
    "status 5",
    "429",
    "rate limit",
    "robots",
    "blocked",
    "refused",
    "unreachable",
    "unparseable",
    "could not be parsed",
    "empty response",
    "too large",
    "redirect",
)

#: A page was read and simply does not say. This is the product working.
_UNKNOWN_MARKERS = (
    "cannot confirm",
    "could not confirm",
    "no statement about",
    "does not state",
    "not stated",
    "is unknown",
    "remains unknown",
    "no known url",
    "not located",
    # "No official cost page is known for X" - we never had a URL to read, so
    # nothing failed; the value simply stays unknown.
    "no official",
    "page is known",
    "is known for",
    "not applicable",
    "no candidate matched",
    "requires official clarification",
    "needs official clarification",
)


class DiagnosticKind(StrEnum):
    #: A page could not be read at all.
    FAILURE = "failure"
    #: A page was read and does not answer the question.
    UNKNOWN = "unknown"


def classify(message: str) -> DiagnosticKind:
    """Which bucket a diagnostic line belongs in.

    Failure markers win a tie: "timed out while confirming X" is a failure that
    happens to mention confirmation, and calling it normal would bury it.
    """
    text = message.casefold()
    for marker in _FAILURE_MARKERS:
        if re.search(rf"\b{re.escape(marker)}", text):
            return DiagnosticKind.FAILURE
    for marker in _UNKNOWN_MARKERS:
        if marker in text:
            return DiagnosticKind.UNKNOWN
    # Unrecognised wording is reported as a failure. Over-reporting a problem
    # is recoverable; quietly filing a real one under "this is normal" is not.
    return DiagnosticKind.FAILURE


def split(messages: list[str]) -> tuple[list[str], list[str]]:
    """(failures, unknowns), each keeping its original order."""
    failures: list[str] = []
    unknowns: list[str] = []
    for message in messages:
        target = failures if classify(message) is DiagnosticKind.FAILURE else unknowns
        target.append(message)
    return failures, unknowns
