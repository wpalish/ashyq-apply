"""Matching an applicant's citizenship against an award's own restrictions.

The previous test was a substring: `citizenship.lower() in " ".join(restrictions)`.
It was wrong in both directions, and both directions cost the applicant money:

- "Korea" is a substring of "North Korea only", so a South Korean applicant was
  told an award was open to them.
- "Kazakhstan" is not a substring of "Central Asian nationals", so a
  Kazakhstani applicant had a scholarship they may well hold struck off.

Matching is therefore done phrase by phrase, and a restriction that names a
*group* rather than a country is answered with "requires clarification" instead
of a verdict. Guessing either way is the thing this product does not do.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

#: Words an award adds around a nationality, carrying no meaning of their own.
_NOISE = {
    "citizens",
    "citizen",
    "citizenship",
    "nationals",
    "national",
    "nationality",
    "students",
    "student",
    "applicants",
    "applicant",
    "passport",
    "holders",
    "residents",
    "only",
    "of",
    "the",
    "from",
    "and",
    "or",
}

_EU27 = (
    "austria",
    "belgium",
    "bulgaria",
    "croatia",
    "cyprus",
    "czechia",
    "czech republic",
    "denmark",
    "estonia",
    "finland",
    "france",
    "germany",
    "greece",
    "hungary",
    "ireland",
    "italy",
    "latvia",
    "lithuania",
    "luxembourg",
    "malta",
    "netherlands",
    "poland",
    "portugal",
    "romania",
    "slovakia",
    "slovenia",
    "spain",
    "sweden",
)
_EEA = (*_EU27, "iceland", "liechtenstein", "norway")
_EFTA = ("iceland", "liechtenstein", "norway", "switzerland")

#: Blocs whose membership is a published list, so "not a member" is a fact
#: rather than a guess. Naming one of these is as good as naming its members.
_DEFINED_BLOCS: dict[str, tuple[str, ...]] = {
    "european union": _EU27,
    "eu": _EU27,
    "european economic area": _EEA,
    "eea": _EEA,
    "efta": _EFTA,
}

#: Markers of a collective restriction whose membership cannot be settled from
#: the page: they produce PENDING rather than a verdict in either direction.
_GROUP_MARKERS = (
    "asia",
    "asian",
    "africa",
    "african",
    "europe",
    "european",
    "latin america",
    "caribbean",
    "middle east",
    "commonwealth",
    "oecd",
    "developing",
    "least developed",
    "low income",
    "middle income",
    "third country",
    "non-eu",
    "overseas",
    "region",
    "worldwide",
    "any country",
    "all countries",
    "international",
)

#: Suffixes that turn a country into its demonym: Kazakhstan -> Kazakhstani,
#: Korea -> Korean, China -> Chinese. Checked as a suffix on the country stem,
#: never as a free-form similarity.
#: "stan" is here for the reverse direction — "Kazakh nationals" naming
#: Kazakhstan — which matters for this product's primary audience.
_DEMONYM_SUFFIXES = ("", "n", "an", "ian", "i", "ish", "ese", "er", "ic", "stan")


class CitizenshipMatch(StrEnum):
    MET = "met"
    #: Named restriction the applicant plainly does not meet.
    NOT_APPLICABLE = "not_applicable"
    #: A group we cannot resolve from the page. Never a "no".
    PENDING = "pending"


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s-]", " ", folded).strip()


def _phrases(restriction: str) -> list[str]:
    """Split one restriction line into the nationalities it names."""
    parts = re.split(r",|;|/|\band\b|\bor\b|\bplus\b", _normalize(restriction))
    out = []
    for part in parts:
        words = [w for w in part.split() if w and w not in _NOISE]
        if words:
            out.append(" ".join(words))
    return out


def _is_demonym_of(phrase: str, country: str) -> bool:
    """Whether `phrase` is `country` or a demonym built from it.

    Deliberately strict about direction: "north korea" is not a demonym of
    "korea", because the qualifier makes it a different country.
    """
    if phrase == country:
        return True
    for stem, other in ((country, phrase), (phrase, country)):
        if other.startswith(stem) and len(stem) >= 5:
            suffix = other[len(stem) :]
            if suffix in _DEMONYM_SUFFIXES:
                return True
    return False


def match_citizenship(
    restrictions: list[str], citizenships: list[str | None]
) -> tuple[CitizenshipMatch, str]:
    """Compare an award's restrictions against the citizenships an applicant holds.

    Returns the verdict and a sentence explaining it in the applicant's terms.
    """
    held = [_normalize(c) for c in citizenships if c]
    named = [p for restriction in restrictions for p in _phrases(restriction)]
    if not named or not held:
        return CitizenshipMatch.PENDING, (
            "The award publishes a citizenship restriction that could not be read as a "
            "list of countries. It needs official clarification."
        )

    for country in held:
        for phrase in named:
            if _is_demonym_of(phrase, country):
                return CitizenshipMatch.MET, (
                    f"The published restriction names {phrase}, which matches the "
                    f"{country.title()} citizenship in the profile."
                )
            members = _DEFINED_BLOCS.get(phrase)
            if members and any(_is_demonym_of(member, country) for member in members):
                return CitizenshipMatch.MET, (
                    f"{country.title()} is a member of the {phrase.upper()}, which the award "
                    f"names as its restriction."
                )

    # A phrase is unresolvable only if it is neither a country nor a bloc whose
    # membership is published. "European Economic Area" names a list; "Central
    # Asian nationals" does not, even though both mention a continent.
    unresolved = [
        phrase
        for phrase in named
        if phrase not in _DEFINED_BLOCS
        and any(re.search(rf"\b{re.escape(m)}\b", phrase) for m in _GROUP_MARKERS)
    ]
    if unresolved:
        return CitizenshipMatch.PENDING, (
            f"The award is restricted to a group ('{', '.join(restrictions)}') whose membership "
            f"is not published as a list of countries. Whether "
            f"{', '.join(c.title() for c in held)} falls inside it cannot be settled from the "
            f"page, so it is left for the admissions office to confirm."
        )

    return CitizenshipMatch.NOT_APPLICABLE, (
        f"The award is restricted to {', '.join(restrictions)}. An applicant holding "
        f"{', '.join(c.title() for c in held)} citizenship is not eligible."
    )
