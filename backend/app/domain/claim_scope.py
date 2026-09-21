"""Who a published rule actually applies to.

The benchmark measured the failure this module exists to fix: the pipeline
reads official pages correctly — primary-source rate 13/13 — and then states
what it read as the answer to a question it was never about. Every claim it
produced was the right fact about the wrong population, year or programme.
A requirement published for non-EU/EEA applicants in the 2026 cycle came back
as the answer for fall 2027.

That is not an extraction problem. A university page is *true*; it is true
**of somebody**, and of a year, and of one programme. Losing that is losing
the only thing that makes the fact usable.

Today a claim carries a programme, an intake and an academic year, and
everything else about who a rule covers lives in free-text notes — which the
phase guide forbids in as many words. Worse, a dimension nobody recorded is
treated as covering everyone, which is exactly backwards: a page that never
says which applicants it is for has not said it is for all of them.

So the rule here has one shape, the same one V2-17 uses for identity:

* a dimension the claim **states and matches** supports the claim;
* a dimension it **states and contradicts** refutes it;
* a dimension it is **silent on**, where the request names one, is UNKNOWN.

:meth:`ClaimScope.covers` therefore returns a ``Verdict`` and not a bool.
Silence is not agreement, and there is nowhere in a bool to put that.

Pure domain logic: no I/O, no adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from app.domain.programme_identity import Verdict

#: The dimensions a decision-grade claim can be scoped by, in the order a
#: reviewer would read them: where, then what, then who.
SCOPE_DIMENSIONS = (
    "university",
    "faculty",
    "programme",
    "degree",
    "intake",
    "academic_year",
    "population",
    "nationality",
    "residency",
)


def _same(left: str, right: str) -> bool:
    """Case- and whitespace-insensitive equality.

    Deliberately not fuzzy. Two scope values that merely look alike are two
    scopes until something authoritative says otherwise — the phase guide's
    rule for entity resolution, applied here too.
    """
    return left.strip().casefold() == right.strip().casefold()


@dataclass(frozen=True, slots=True)
class RequestedScope:
    """What was actually asked for. ``None`` means the request did not say."""

    university: str | None = None
    faculty: str | None = None
    programme: str | None = None
    degree: str | None = None
    intake: str | None = None
    academic_year: str | None = None
    population: str | None = None
    nationality: str | None = None
    residency: str | None = None

    def stated(self) -> tuple[str, ...]:
        return tuple(d for d in SCOPE_DIMENSIONS if getattr(self, d))


@dataclass(frozen=True, slots=True)
class ClaimScope:
    """Who and what a claim's source says it is about.

    ``None`` on a dimension means the page did not say, which is never the
    same as "everyone". Every field defaults to ``None`` so a scope built from
    a page that stated nothing is honestly empty rather than accidentally
    universal.
    """

    university: str | None = None
    faculty: str | None = None
    programme: str | None = None
    degree: str | None = None
    intake: str | None = None
    academic_year: str | None = None
    population: str | None = None
    nationality: str | None = None
    residency: str | None = None

    def stated(self) -> tuple[str, ...]:
        """Dimensions this scope actually records."""
        return tuple(d for d in SCOPE_DIMENSIONS if getattr(self, d))

    def unstated(self) -> tuple[str, ...]:
        return tuple(d for d in SCOPE_DIMENSIONS if not getattr(self, d))

    def contradictions(self, requested: RequestedScope) -> tuple[str, ...]:
        """Dimensions where both sides spoke and disagreed."""
        return tuple(
            d
            for d in SCOPE_DIMENSIONS
            if getattr(self, d)
            and getattr(requested, d)
            and not _same(getattr(self, d), getattr(requested, d))
        )

    def gaps(self, requested: RequestedScope) -> tuple[str, ...]:
        """Dimensions the request names and the claim is silent on.

        These are what stands between a claim and being usable. Naming them is
        what lets a reviewer, or a later fetch, close the gap — as opposed to
        a single confidence number, which names nothing.
        """
        return tuple(d for d in SCOPE_DIMENSIONS if getattr(requested, d) and not getattr(self, d))

    def covers(self, requested: RequestedScope) -> Verdict:
        """Whether this claim may be stated as the answer to ``requested``.

        ``UNKNOWN`` is the common and correct answer for a page that simply
        did not say who it was for. It means *record the claim with the scope
        it has*; it does not mean discard it, and it must never be rounded up
        to YES — that rounding is what the wrong-scope rate is made of.
        """
        if self.contradictions(requested):
            return Verdict.NO
        if self.gaps(requested):
            return Verdict.UNKNOWN
        if not requested.stated():
            # Nothing was asked for, so nothing can be answered. Refusing to
            # call that a match keeps an unscoped question from matching
            # everything.
            return Verdict.UNKNOWN
        return Verdict.YES

    def narrower_than(self, other: ClaimScope) -> bool:
        """Whether this scope is strictly more specific than ``other``.

        Used to prefer the more specific of two claims that agree. It is a
        subset test, not a count: a claim scoped to a programme and a claim
        scoped to a nationality both state one dimension and neither is
        narrower, so neither wins by accident.
        """
        mine, theirs = set(self.stated()), set(other.stated())
        return theirs < mine

    def explain(self, requested: RequestedScope) -> str:
        """Why this scope does or does not answer the request, in one line."""
        verdict = self.covers(requested)
        if verdict is Verdict.NO:
            return f"does not apply: {', '.join(self.contradictions(requested))} differ"
        if verdict is Verdict.UNKNOWN:
            gaps = self.gaps(requested)
            return (
                f"scope unestablished: the source does not state {', '.join(gaps)}"
                if gaps
                else "scope unestablished: nothing was requested"
            )
        return f"applies: {', '.join(self.stated())} all match"

    @classmethod
    def from_mapping(cls, values: dict[str, str | None]) -> ClaimScope:
        """Build from a loose mapping, ignoring keys that are not dimensions.

        Corpus records and extractor output both carry extra keys; silently
        dropping an unknown one is right, while silently dropping a *known*
        one would lose scope, so only the declared fields are read.
        """
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in values.items() if k in known and v})
