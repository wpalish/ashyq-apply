"""Does this page describe the programme we asked about?

A page being reachable proves nothing. Before a PROGRAM_EXISTS claim can be
made, the page's own subject and degree level have to line up with the
programme being researched.
"""

from __future__ import annotations

import re

from app.domain.enums import DegreeLevel

#: Words that describe the *kind* of qualification rather than its subject.
_DEGREE_TOKENS = {
    "bsc", "ba", "beng", "llb", "msc", "ma", "meng", "llm", "mba", "mphil", "phd",
    "bachelor", "bachelors", "master", "masters", "doctoral", "doctorate",
    "undergraduate", "postgraduate", "graduate", "foundation", "honours", "hons",
    "programme", "program", "degree", "course", "studies", "study", "hbsc", "mod",
}
_STOPWORDS = {"and", "of", "the", "in", "for", "with", "a", "an", "at", "to"}
_SPLIT = re.compile(r"[^\w]+", re.UNICODE)


def content_tokens(name: str) -> set[str]:
    """Subject words only — degree words and stopwords removed."""
    return {
        t for t in (p.lower() for p in _SPLIT.split(name or "") if p)
        if t not in _DEGREE_TOKENS and t not in _STOPWORDS and not t.isdigit() and len(t) > 1
    }


def degree_matches(requested: str | DegreeLevel | None, found: str | None) -> bool | None:
    """True / False, or None when the page does not state a level."""
    if not requested or not found:
        return None
    return str(requested).lower() == str(found).lower()


def program_matches(
    requested_name: str,
    requested_field: str,
    page_subject: str | None,
    requested_degree: str | DegreeLevel | None = None,
    page_degree: str | None = None,
) -> tuple[bool, str]:
    """Whether a page's subject is the programme we asked about, and why.

    Conservative by construction: no subject means no match, and a stated
    degree level that disagrees is a hard no. Recall is sacrificed here on
    purpose — a missed programme is a gap, a wrong one is a false claim.
    """
    if not page_subject:
        return False, "the page does not identify a single programme"

    level = degree_matches(requested_degree, page_degree)
    if level is False:
        return False, (
            f"the page describes a {page_degree} programme, not {requested_degree}"
        )

    wanted = content_tokens(requested_name) | content_tokens(requested_field)
    found = content_tokens(page_subject)
    if not wanted:
        return False, "no subject words to match against"
    if not found:
        return False, f"the page heading {page_subject!r} carries no subject words"

    overlap = wanted & found
    if wanted <= found:
        return True, f"page subject {page_subject!r} covers every requested subject word"
    if found <= wanted and len(overlap) >= 1:
        return True, f"page subject {page_subject!r} is a narrower name for the same subject"
    # Require most of what was asked for, not merely one shared word: "computer
    # science" and "political science" share "science".
    if len(overlap) >= 2 and len(overlap) / len(wanted) >= 0.6:
        return True, f"page subject {page_subject!r} shares {sorted(overlap)}"
    return False, (
        f"page subject {page_subject!r} does not match the requested "
        f"{requested_name!r} (shared: {sorted(overlap) or 'nothing'})"
    )
