"""Is this the right programme, and may its page speak about the intake we asked for?

Two questions, deliberately not one. The benchmark says the pipeline reads
official pages correctly — ``primary_source_rate`` is 13/13 — and then applies
what it read to the wrong population, year or programme: ``wrong_scope_claim_rate``
is 5/5. A single "is this a match" score cannot express that failure, which is
why the phase guide says in as many words: *do not collapse identity into one
fuzzy score.*

So identity is six independent dimensions. Four say whether this is the right
programme at all; two say whether a claim read from it may be applied to the
intake that was requested.

**``UNKNOWN`` is never a match, and never a failure either.** An unverified
dimension is not a refuted one — that is invariant I4, already settled for
ranking in HANDOFF §7, and it holds here for the same reason: the only way to
turn "the page does not say" into a yes or a no is to make something up.
:meth:`ProgrammeIdentity.applies_to` therefore returns a ``Verdict`` rather
than a bool, because a bool has nowhere to put "we do not know" and whichever
way a caller rounds it, somebody's application is affected.

Pure domain logic: no I/O, no adapters, no network. Reading these dimensions
off a real page is an adapter's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    YES = "yes"
    NO = "no"
    #: The page does not say. Not a failure, not a pass.
    UNKNOWN = "unknown"


class IdentityState(StrEnum):
    #: All four identity dimensions confirmed.
    EXACT = "exact"
    #: At least one identity dimension refuted. Not this programme.
    NOT_A_MATCH = "not_a_match"
    #: Nothing refuted, something unconfirmed. A person decides.
    NEEDS_REVIEW = "needs_review"


class ScopeState(StrEnum):
    #: Active, and the requested intake is supported.
    IN_SCOPE = "in_scope"
    #: Discontinued, or the requested intake is explicitly not offered.
    OUT_OF_SCOPE = "out_of_scope"
    #: The page does not establish either. The common case, and not an error.
    UNKNOWN = "unknown"


#: The four dimensions that decide whether this is the right programme.
IDENTITY_DIMENSIONS = ("exists", "university", "degree_level", "field")

#: The two that decide whether its content may be applied to the requested
#: intake. Separated from identity because the right programme's page can
#: still be about a different year, which is the failure being fixed.
SCOPE_DIMENSIONS = ("active", "intake")


@dataclass(frozen=True, slots=True)
class ProgrammeIdentity:
    """Six verdicts and the reason behind each, never averaged into one."""

    exists: Verdict = Verdict.UNKNOWN
    university: Verdict = Verdict.UNKNOWN
    degree_level: Verdict = Verdict.UNKNOWN
    field: Verdict = Verdict.UNKNOWN
    active: Verdict = Verdict.UNKNOWN
    intake: Verdict = Verdict.UNKNOWN
    #: Dimension name to the sentence that justifies its verdict. What makes a
    #: verdict reviewable instead of merely asserted.
    reasons: tuple[tuple[str, str], ...] = ()

    def verdict(self, dimension: str) -> Verdict:
        if dimension not in IDENTITY_DIMENSIONS + SCOPE_DIMENSIONS:
            raise KeyError(f"{dimension!r} is not an identity dimension")
        return getattr(self, dimension)

    def reason(self, dimension: str) -> str:
        return dict(self.reasons).get(dimension, "")

    @property
    def identity_state(self) -> IdentityState:
        verdicts = [self.verdict(d) for d in IDENTITY_DIMENSIONS]
        if Verdict.NO in verdicts:
            return IdentityState.NOT_A_MATCH
        if all(v is Verdict.YES for v in verdicts):
            return IdentityState.EXACT
        return IdentityState.NEEDS_REVIEW

    @property
    def scope_state(self) -> ScopeState:
        verdicts = [self.verdict(d) for d in SCOPE_DIMENSIONS]
        if Verdict.NO in verdicts:
            return ScopeState.OUT_OF_SCOPE
        if all(v is Verdict.YES for v in verdicts):
            return ScopeState.IN_SCOPE
        return ScopeState.UNKNOWN

    @property
    def is_exact_match(self) -> bool:
        """Whether this is the requested programme. Says nothing about intake."""
        return self.identity_state is IdentityState.EXACT

    def applies_to_requested_intake(self) -> Verdict:
        """Whether a claim from this page may be stated for the requested intake.

        Returns a verdict, not a bool, and that is the whole point. ``UNKNOWN``
        means the claim is real but its scope is not established: record it
        with the scope it has, do not promote it to the requested intake. That
        promotion is what ``wrong_scope_claim_rate`` 5/5 is made of.
        """
        if self.identity_state is IdentityState.NOT_A_MATCH:
            return Verdict.NO
        if self.scope_state is ScopeState.OUT_OF_SCOPE:
            return Verdict.NO
        if self.identity_state is IdentityState.EXACT and self.scope_state is ScopeState.IN_SCOPE:
            return Verdict.YES
        return Verdict.UNKNOWN

    @property
    def unresolved(self) -> tuple[str, ...]:
        """Which dimensions a human would have to settle. Ordered, for a worksheet."""
        return tuple(
            d for d in IDENTITY_DIMENSIONS + SCOPE_DIMENSIONS if self.verdict(d) is Verdict.UNKNOWN
        )

    @property
    def refuted(self) -> tuple[str, ...]:
        """Which dimensions rule this candidate out, and why it was rejected."""
        return tuple(
            d for d in IDENTITY_DIMENSIONS + SCOPE_DIMENSIONS if self.verdict(d) is Verdict.NO
        )

    def explain(self) -> str:
        """One line per dimension. A candidate's whole case, readable."""
        return "; ".join(
            f"{d}={self.verdict(d)}" + (f" ({self.reason(d)})" if self.reason(d) else "")
            for d in IDENTITY_DIMENSIONS + SCOPE_DIMENSIONS
        )
