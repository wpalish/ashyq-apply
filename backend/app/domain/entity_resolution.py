"""Which institution a name or a URL is actually about.

Today identity is `dedupe.university_key(name, country)`: normalise the name,
drop noise words, **sort what remains into a set**, join. That is a fuzzy
matcher wearing a deterministic coat, and it fails in both directions.

It splits one institution: *Technische Universiteit Delft* and *Delft
University of Technology* are the same place and reduce to different keys, so
the same university can enter a run twice, once per spelling.

It merges two: any names reducing to the same token set in the same country
become one key, silently, because a sorted set carries no order and no
evidence. The phase guide's own sentence: *do not merge because names are
merely similar.*

So resolution here is a ladder of **evidence**, strongest first, and it stops
rather than guessing:

1. **A registrable domain** the registry records for that institution. A page
   served by `rug.nl` is the University of Groningen's whatever it calls
   itself on the page; a host is the hardest evidence this product holds.
2. **An alias recorded for it** — exactly, after case and whitespace
   normalisation. Recorded by a human, never inferred here.
3. **Nothing.** Two pages that may describe different institutions stay
   separate until something above says otherwise.

Every answer carries the basis and the exact evidence that produced it,
because the guide requires entity resolution to be *auditable*: a merge nobody
can explain afterwards is the failure, not the merge.

Pure domain logic: no I/O, no adapters, no registry loading — the caller hands
in the identities it already has.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse

from app.domain.claim_verifier import registrable_domain
from app.domain.dedupe import normalize


class Basis(StrEnum):
    """What a resolution rests on. Ordered strongest to weakest."""

    DOMAIN = "domain"
    ALIAS = "alias"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class InstitutionIdentity:
    """One real institution, and the evidence that identifies it.

    ``aliases`` and ``former_names`` are **recorded**, never derived. An empty
    tuple means nobody has written them down yet, which is why resolution by
    name alone fails honestly instead of falling back to resemblance.
    """

    key: str
    name: str
    country: str = ""
    #: Domains the registry holds for this institution, verified by a human.
    domains: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    former_names: tuple[str, ...] = ()
    #: Where the above came from, for the audit trail.
    source_urls: tuple[str, ...] = field(default_factory=tuple)

    def names(self) -> tuple[str, ...]:
        """Every name this institution is recorded under, canonical first."""
        return (self.name, *self.aliases, *self.former_names)


@dataclass(frozen=True, slots=True)
class Resolution:
    """An answer and the reason for it. Never just an answer."""

    identity: InstitutionIdentity | None
    basis: Basis
    #: The exact string that decided it: the domain matched, or the recorded
    #: name matched. Empty when nothing did.
    evidence: str = ""

    @property
    def resolved(self) -> bool:
        return self.identity is not None

    def explain(self) -> str:
        if self.identity is None:
            return "unresolved: no recorded domain or alias matches"
        if self.basis is Basis.DOMAIN:
            return f"{self.identity.name}: served by {self.evidence}"
        return f"{self.identity.name}: recorded as {self.evidence!r}"


def _hosts(identity: InstitutionIdentity) -> set[str]:
    return {registrable_domain(d) for d in identity.domains if d}


def resolve_institution(
    identities: list[InstitutionIdentity],
    *,
    url: str = "",
    name: str = "",
    country: str = "",
) -> Resolution:
    """Which of ``identities`` this URL or name is about, and why.

    The URL is tried first whenever both are given: a name is what a page
    calls something, a host is who served it. ``country``, when given, only
    ever *narrows* a name match — it never creates one, so an institution
    recorded without a country is still reachable.
    """
    if url:
        host = registrable_domain(urlparse(url).hostname or "")
        if host:
            for identity in identities:
                if host in _hosts(identity):
                    return Resolution(identity, Basis.DOMAIN, host)

    if name:
        wanted = normalize(name)
        for identity in identities:
            if country and normalize(identity.country) != normalize(country):
                continue
            for recorded in identity.names():
                if normalize(recorded) == wanted:
                    return Resolution(identity, Basis.ALIAS, recorded)

    return Resolution(None, Basis.UNRESOLVED)


def same_institution(left: Resolution, right: Resolution) -> bool:
    """Whether two resolutions name one institution.

    Two *unresolved* resolutions are never the same institution, however alike
    the strings behind them looked. That is the whole discipline in one line:
    without evidence there is no identity, and "both unknown" is not a match.
    """
    if left.identity is None or right.identity is None:
        return False
    return left.identity.key == right.identity.key
