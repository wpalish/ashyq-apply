"""The questions the phase guide says the evidence must be able to answer.

The guide lists them outright: which evidence currently supports a
requirement for a programme and intake; which claims are stale; which are
conflicting; which facts are still unknown; what a claim used to say. Until
now each one was answerable only by reading rows by hand, which means nobody
answered them.

Every function here returns **claims**, never a verdict. That is the whole
design rule: the product's promise is that a user can see the evidence, and a
function that answered "yes, IELTS 6.5" instead of "these two pages say so"
would be the beginning of a system that asserts rather than shows.

Deliberately pure Python over claims a caller already holds, with **no SQL and
no migration**. Indexed scope columns on ``claims`` are the obvious
alternative and are premature twice over: nothing queries by scope in
production yet, and the guide's own answer to persistent scoped knowledge is
the SourceSnapshot / ClaimVersion model that plan V2-20 has half-built. If a
query ever needs an index, these functions name exactly which one.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from app.domain.claim_scope import RequestedScope
from app.domain.enums import ClaimStatus, ClaimType
from app.domain.freshness import is_stale
from app.domain.programme_identity import Verdict
from app.schemas.claim import Claim

#: Statuses that are live evidence. SUPERSEDED is history and NOT_FOUND is the
#: record of an answered-in-the-negative question; neither supports anything.
LIVE_STATUSES = frozenset(
    {
        ClaimStatus.VERIFIED_CURRENT,
        ClaimStatus.POSSIBLY_STALE,
        ClaimStatus.CONFLICTING,
        ClaimStatus.UNVERIFIED,
        ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION,
    }
)


def live(claims: Iterable[Claim]) -> list[Claim]:
    """Only what still stands. History and negatives are excluded."""
    return [c for c in claims if c.status in LIVE_STATUSES]


def supporting(
    claims: Sequence[Claim],
    claim_type: ClaimType,
    *,
    subject_key: str | None = None,
) -> list[Claim]:
    """Which evidence currently supports one requirement.

    ``subject_key`` narrows to one scholarship or one fee category, because
    two awards' amounts are two answers and not two opinions about one.
    """
    return [
        c
        for c in live(claims)
        if c.claim_type == claim_type and (subject_key is None or c.subject_key == subject_key)
    ]


def scoped_to(claims: Sequence[Claim], requested: RequestedScope) -> list[Claim]:
    """Evidence whose page says it is about what was asked.

    Only ``YES``. A claim whose page never said is genuinely not an answer to
    a scoped question, and including it here would undo V2-23 one layer down.
    """
    return [
        c for c in live(claims) if c.scope is not None and c.scope.covers(requested) is Verdict.YES
    ]


def stale(claims: Sequence[Claim], *, now: datetime | None = None) -> list[Claim]:
    """Which claims have aged out of their type's freshness window."""
    return [c for c in live(claims) if is_stale(c.claim_type, c.accessed_at, now)]


def conflicting(claims: Sequence[Claim]) -> list[Claim]:
    """Which claims are in an unresolved disagreement."""
    return [c for c in claims if c.status is ClaimStatus.CONFLICTING]


def unknown_for(claims: Sequence[Claim], wanted: Iterable[ClaimType]) -> list[ClaimType]:
    """Which of the facts we wanted are still unanswered.

    Returns the missing **types**, not claims — there is nothing to show for a
    fact nobody has established, and pretending otherwise with an empty list
    would hide the gap inside a successful-looking answer.
    """
    answered = {c.claim_type for c in live(claims)}
    return [t for t in wanted if t not in answered]


def superseded_history(claims: Sequence[Claim], claim_type: ClaimType) -> list[Claim]:
    """What this fact used to say, oldest first.

    Ordered by when each version was **read**, which is the best a claim alone
    can say: V2-20b records when a value stopped being current on the claim
    *row* (``claims.superseded_at``), and that column is deliberately not part
    of the claim document. Read time gives the same sequence whenever a page
    is read once per generation, which is how re-extraction works; a caller
    holding rows can sort by the exact end time instead.
    """
    history = [
        c for c in claims if c.claim_type == claim_type and c.status is ClaimStatus.SUPERSEDED
    ]
    return sorted(history, key=lambda c: c.accessed_at)
