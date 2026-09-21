"""What discovery is allowed to tell a search engine.

A provider logs whatever it is sent. A name, a score or a budget sent once
cannot be unsent, and it is sent on behalf of a person who asked for help
finding a university, not for their file to be handed to a vendor. So the
query generator does not take an applicant profile. It takes a
:class:`DiscoveryIntent`, which has room for the discovery dimensions and for
nothing else.

Two different guarantees are at work, and neither replaces the other:

* the search seam's signature takes a query string, so no profile *object*
  can reach a provider — see ``app.adapters.search.base``;
* :class:`DiscoveryIntent` validates its own values, so a profile *formatted
  into a string* cannot reach one either.

The second exists because the first is easy to satisfy while still leaking:
``f"{profile.display_name} bsc computer science"`` passes every type check
ever written.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from app.domain.enums import DegreeLevel

if TYPE_CHECKING:  # pragma: no cover - import kept out of the runtime path
    from app.schemas.profile import ApplicantProfileIn

#: The most queries one intent may produce. §4 of the phase guide: do not
#: explode aliases into unlimited queries. A budget also bounds spend and the
#: footprint left in a vendor's logs.
DEFAULT_QUERY_BUDGET = 6

#: Population markers that may appear in a query, and only for a country's
#: public requirements page. They describe a published policy audience, not
#: this applicant: "Kazakhstan admission requirements" is a page title, not a
#: statement that our applicant is Kazakhstani.
ALLOWED_POPULATION_MARKERS = frozenset({"international", "Kazakhstan"})

_EMAIL = re.compile(r"\S+@\S+")
_PHONE_OR_SCORE = re.compile(r"\d{3,}")
_MONEY = re.compile(r"[$€£₸]|\b(?:usd|eur|gbp|kzt)\b", re.IGNORECASE)
_GPA = re.compile(r"\b\d\.\d+\b")


class QueryPrivacyError(ValueError):
    """Raised when a value carries something a provider must never be told."""


def _reject_applicant_data(field: str, value: str) -> None:
    """Refuse a value that looks like it came off a profile.

    Deliberately blunt. A false positive here costs one caller a clearer
    phrasing; a false negative puts a real person's score in a vendor's logs
    forever. Years are the one numeric run a discovery query legitimately
    needs, and they are carried by ``intake_year`` rather than free text.
    """
    if _EMAIL.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} contains an email address. Contact details are never "
            "part of a discovery query."
        )
    if _MONEY.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} contains a currency amount. Budget and family "
            "contribution never leave this service."
        )
    if _GPA.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} looks like a grade. A search engine is asked where a "
            "programme is, never how well the applicant did."
        )
    if _PHONE_OR_SCORE.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} contains a long number, which is how a test score or a "
            "phone number gets into a query. Use intake_year for a year."
        )


@dataclass(frozen=True, slots=True)
class DiscoveryIntent:
    """The discovery question, with no room for anything else.

    Every field here is about a *programme*. There is deliberately no field
    for the applicant: adding one is the change that would need reviewing.
    """

    institution: str
    domain: str
    degree: DegreeLevel
    field: str
    #: Included in a query only when it plausibly narrows a result, e.g. a
    #: catalogue that publishes per-year pages.
    intake_year: int | None = None
    #: ``international`` or a country name, and only for a public
    #: requirements page. See :data:`ALLOWED_POPULATION_MARKERS`.
    population_marker: str = ""

    def __post_init__(self) -> None:
        if not self.institution.strip():
            raise ValueError("A discovery intent needs an institution")
        if not self.domain.strip():
            raise ValueError("A discovery intent needs the institution's domain")
        if not self.field.strip():
            raise ValueError("A discovery intent needs a field of study")
        for name in ("institution", "domain", "field", "population_marker"):
            _reject_applicant_data(name, getattr(self, name))
        if self.population_marker and self.population_marker not in ALLOWED_POPULATION_MARKERS:
            raise QueryPrivacyError(
                f"population_marker={self.population_marker!r} is not one of "
                f"{sorted(ALLOWED_POPULATION_MARKERS)}. A narrower audience describes this "
                "applicant rather than a published policy."
            )
        if self.intake_year is not None and not (2000 <= self.intake_year <= 2100):
            raise ValueError(f"intake_year={self.intake_year} is not a plausible intake year")

    @classmethod
    def from_profile(
        cls,
        profile: ApplicantProfileIn,
        *,
        institution: str,
        domain: str,
        field: str = "",
        include_intake: bool = False,
        population_marker: str = "",
    ) -> DiscoveryIntent:
        """The only sanctioned way to build an intent from a profile.

        It reads exactly three things — the degree level, the first intended
        field, and optionally the intake year — and ignores the rest of the
        object. Written once, here, so that every call site does not invent
        its own subset and quietly include one field too many.

        Dropped, explicitly: ``display_name``, every test score, every grade
        and GPA, the funding and family contribution, all activities,
        achievements, preferences and weights, citizenship, residence and
        graduation date. Citizenship is *not* forwarded even though it feels
        like a discovery dimension: use ``population_marker`` for a country's
        public requirements page, which is a statement about the page, not
        about the applicant.
        """
        context = profile.context
        chosen = field or (context.intended_fields[0] if context.intended_fields else "")
        return cls(
            institution=institution,
            domain=domain,
            degree=context.level,
            field=chosen,
            intake_year=context.intake_year if include_intake else None,
            population_marker=population_marker,
        )

    def without_intake(self) -> DiscoveryIntent:
        return replace(self, intake_year=None)


@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    """One query, and which family it came from.

    The family travels with the text so telemetry can say *which kind* of
    query finds programme pages, which is the question V2-13 has to answer.
    """

    text: str
    family: str


def _degree_aliases(degree: DegreeLevel) -> str:
    return {
        DegreeLevel.FOUNDATION: "foundation",
        DegreeLevel.BACHELOR: "bachelor",
        DegreeLevel.MASTER: "master",
        DegreeLevel.PHD: "phd",
    }[degree]


def queries_for(
    intent: DiscoveryIntent,
    *,
    budget: int = DEFAULT_QUERY_BUDGET,
    families: Sequence[str] = (),
) -> tuple[DiscoveryQuery, ...]:
    """Render an intent into at most ``budget`` queries, best first.

    The order is the order of usefulness observed in the phase guide: the
    most specific query first, so a caller that can afford only one or two
    still gets the ones most likely to land on a programme page.
    """
    if budget < 1:
        raise ValueError(f"A query budget must be at least 1, got {budget}")

    site = f"site:{intent.domain}"
    degree = _degree_aliases(intent.degree)
    year = f" {intent.intake_year}" if intent.intake_year else ""
    candidates: list[DiscoveryQuery] = [
        DiscoveryQuery(f'{site} "{intent.field}" "{degree}"{year}', "field_and_degree"),
        DiscoveryQuery(f'{site} programmes "{intent.field}"{year}', "programmes"),
        DiscoveryQuery(f'{site} courses "{intent.field}"{year}', "courses"),
        DiscoveryQuery(f'{site} undergraduate "{intent.field}"', "undergraduate"),
        DiscoveryQuery(f"{site} admissions {degree}", "admissions"),
    ]
    if intent.population_marker:
        candidates.append(
            DiscoveryQuery(
                f"{site} {intent.population_marker} admission requirements",
                "country_requirements",
            )
        )
        candidates.append(
            DiscoveryQuery(
                f"{site} scholarships {intent.population_marker} {degree}",
                "scholarships",
            )
        )

    if families:
        wanted = set(families)
        unknown = wanted - {q.family for q in candidates}
        if unknown:
            raise ValueError(f"Unknown query families: {sorted(unknown)}")
        candidates = [q for q in candidates if q.family in wanted]

    return tuple(candidates[:budget])


@dataclass(frozen=True, slots=True)
class QueryAuditRecord:
    """What is safe to keep about a query we ran.

    The phase guide asks for a *redacted* audit record. Keeping the full
    query text in our own logs would recreate, on our side, exactly the
    trail we are careful not to leave on the vendor's.
    """

    institution: str
    domain: str
    degree: str
    field: str
    family: str
    provider: str
    result_count: int
    intake_year: int | None = None
    population_marker: str = ""


def redacted_audit_record(
    intent: DiscoveryIntent,
    query: DiscoveryQuery,
    *,
    provider: str,
    result_count: int,
) -> QueryAuditRecord:
    """Describe a search without storing its text."""
    return QueryAuditRecord(
        institution=intent.institution,
        domain=intent.domain,
        degree=str(intent.degree),
        field=intent.field,
        family=query.family,
        provider=provider,
        result_count=result_count,
        intake_year=intent.intake_year,
        population_marker=intent.population_marker,
    )
