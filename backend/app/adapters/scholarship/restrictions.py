"""Who may hold an award, and how many are given.

Two claims live here, and the product's rules keep them apart:

* **the award's restriction** — what the page says about nationality,
  residency or programme;
* **this applicant's eligibility** — whether their citizenship and residence
  satisfy that restriction.

An award existing says nothing about the second. `docs/CANARY_AUDIT.md`
recorded the cost of merging them: the CLIP award goes to students who "hold
either a Greek passport or Greek residence", nothing read it, and a Kazakhstani
applicant was shown an award they cannot hold.

Silence is never permission. A page that says nothing about nationality leaves
eligibility `unknown`, not `yes`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domain.countries import (
    _normalise,
    bloc_phrases,
    country_phrases,
    country_satisfies,
)

#: Demonym -> country. Only entries where the adjective is unambiguous enough
#: to carry a restriction. A country named without restricting language around
#: it is not a rule, so this table is only consulted inside a match.
#: Country names, aliases and demonyms come from `app/domain/countries.py`.
#: They were duplicated here — 48 names and 44 demonyms — and the two tables
#: drifted apart. One table, or they disagree about who is eligible.
_COUNTRY_PHRASES = country_phrases()


#: Groups that are restrictions but not single countries.
#:
#: Taken from `app/domain/countries.py` rather than listed again here. This was
#: a separate six-entry table, and the two drifted: "citizens of EFTA
#: countries" and "nationals of ASEAN member states" matched nothing, so awards
#: restricted to four and ten countries were presented as unrestricted. A
#: student loses an application to that, not a place.
#:
#: Longest phrase first, so "european economic area" is matched before "eea"
#: and "eu" cannot claim a sentence that says "eu/eea".
_BLOCS = dict(
    sorted(bloc_phrases().items(), key=lambda kv: -len(kv[0]))
)

#: Sentences that impose a nationality or residency condition. Each needs
#: restricting language, not merely a country word: "Greek mythology is taught
#: in the first year" names a nationality and restricts nothing.
_RESTRICTION_SENTENCE = re.compile(
    r"[^.]*\b("
    r"hold(?:ing|s)?\s+(?:either\s+)?an?\s+\w+\s+(?:passport|residence|residency|citizenship)"
    r"|(?:open|available|restricted|limited|offered)\s+(?:only\s+)?to\b[^.]{0,120}"
    r"|must\s+(?:be|hold|have)\b[^.]{0,120}"
    r"|reserved\s+for\b[^.]{0,120}"
    r"|citizens?\s+of\b[^.]{0,80}"
    r"|nationals?\s+of\b[^.]{0,80}"
    r"|\w+\s+(?:nationals?|citizens?)\b"
    r"|with\s+\w+\s+citizenship"
    r")[^.]*\.",
    re.IGNORECASE,
)
#: Words proving the sentence is about who may hold the award.
_STATUS_WORD = re.compile(
    r"\b(passports?|residence|residency|residents?|citizens?|citizenship"
    r"|nationals?|nationality|eligible|eligibility|apply|applicants?)\b",
    re.IGNORECASE,
)
_RESIDENCE_WORD = re.compile(r"\b(residence|residency|residents?|domicile[ds]?)\b", re.IGNORECASE)
_CITIZEN_WORD = re.compile(
    r"\b(passports?|citizens?|citizenship|nationals?|nationality)\b", re.IGNORECASE
)
#: Phrasings that widen rather than restrict.
_NOT_A_RESTRICTION = re.compile(
    r"\b(all over the world|any nationality|all nationalities|from over \d+ countries"
    r"|regardless of nationality|worldwide|international students are welcome)\b",
    re.IGNORECASE,
)

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "twenty": 20, "thirty": 30, "fifty": 50, "hundred": 100,
}
#: A published count names a number. "A number of scholarships" does not.
_COUNT = re.compile(
    r"(?:up to|maximum of|number of scholarships?|we award|awards?|offers?)?\s*"
    r"\b(\d{1,4}|" + "|".join(_NUMBER_WORDS) + r")\b"
    r"[^.]{0,40}?\b(scholarships?|awards?|grants?|places?|bursaries)\b"
    r"|\b(scholarships?|awards?|grants?|bursaries)\b[^.]{0,24}?\b(\d{1,4})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Restrictions:
    """What the page says about who may hold the award."""

    citizenships: list[str] = field(default_factory=list)
    residencies: list[str] = field(default_factory=list)
    blocs: list[str] = field(default_factory=list)
    #: The sentence the restriction was read from, verbatim.
    evidence: str = ""
    #: restriction -> the sentence it came from. A page can state two rules in
    #: two sentences, and attaching the first quote to both proves neither.
    evidence_by_restriction: dict[str, str] = field(default_factory=dict)
    #: True when the page offers alternatives ("a passport *or* residence").
    alternatives: bool = False

    @property
    def any(self) -> bool:
        return bool(self.citizenships or self.residencies or self.blocs)


@dataclass(frozen=True)
class EligibilityVerdict:
    eligible: str  # "yes" | "no" | "unknown"
    reason: str
    evidence: str = ""


@dataclass(frozen=True)
class PublishedCount:
    value: int
    evidence: str


def _countries_in(sentence: str) -> list[str]:
    """Countries a restriction sentence names, from the one country table.

    This used a 48-name table and 44 demonyms kept here, beside the canonical
    144-country model. The two drifted, and awards restricted to Rwanda,
    Cyprus, Malta, Brunei, Mozambique or Togo read as unrestricted — which
    tells a student to spend an application they cannot win.

    Longest phrase first, so "United Kingdom of Great Britain and Northern
    Ireland" is not claimed by "United Kingdom" inside it, and each country is
    reported once however many of its names appear.
    """
    # Normalised the same way the phrase table is, or an accented name never
    # matches its own entry: "Côte d'Ivoire" is stored as "cote divoire", and
    # comparing it against a merely lower-cased sentence found nothing.
    low = _normalise(sentence)
    found: list[str] = []
    consumed: list[tuple[int, int]] = []
    for phrase, country in _COUNTRY_PHRASES.items():
        for match in re.finditer(rf"\b{re.escape(phrase)}\b", low):
            # A longer name already covering this span wins; "United Kingdom"
            # inside the official long form is the same country said once.
            if any(start <= match.start() < end for start, end in consumed):
                continue
            consumed.append((match.start(), match.end()))
            if country not in found:
                found.append(country)
    return found


def extract_restrictions(text: str) -> Restrictions:
    """Nationality and residency conditions stated on an award page."""
    citizenships: list[str] = []
    residencies: list[str] = []
    blocs: list[str] = []
    evidence = ""
    alternatives = False
    by_restriction: dict[str, str] = {}

    for match in _RESTRICTION_SENTENCE.finditer(text or ""):
        sentence = " ".join(match.group(0).split())
        if _NOT_A_RESTRICTION.search(sentence) or not _STATUS_WORD.search(sentence):
            continue
        countries = _countries_in(sentence)
        # Deduplicated: several phrases resolve to one group, and
        # "Commonwealth countries" matched both "commonwealth" and
        # "commonwealth countries", so the award was reported as restricted to
        # the Commonwealth twice.
        found_blocs = list(
            dict.fromkeys(
                label
                for key, label in _BLOCS.items()
                if re.search(rf"\b{re.escape(key)}\b", sentence, re.IGNORECASE)
            )
        )
        if not countries and not found_blocs:
            continue

        # Which kind of condition is it? A sentence can state both, as CLIP's
        # "a Greek passport or Greek residence" does.
        if _CITIZEN_WORD.search(sentence):
            citizenships += [c for c in countries if c not in citizenships]
        if _RESIDENCE_WORD.search(sentence):
            residencies += [c for c in countries if c not in residencies]
        blocs += [b for b in found_blocs if b not in blocs]
        for label in [*countries, *found_blocs]:
            by_restriction.setdefault(label, sentence)
        if not evidence:
            evidence = sentence
        if re.search(r"\beither\b|\bor\b", sentence, re.IGNORECASE):
            alternatives = True

    return Restrictions(
        citizenships=citizenships,
        residencies=residencies,
        blocs=blocs,
        evidence=evidence,
        evidence_by_restriction=by_restriction,
        alternatives=alternatives,
    )


def assess_applicant_eligibility(
    restrictions: Restrictions, *, citizenship: str, residence: str,
) -> EligibilityVerdict:
    """Whether this applicant satisfies the award's stated conditions.

    Three answers, and `unknown` is the default. An award silent on nationality
    has not said this applicant may hold it, and an applicant who has not told
    us their citizenship cannot be measured against one that has.
    """
    if not restrictions.any:
        return EligibilityVerdict(
            "unknown", "The page states no nationality or residency condition.",
        )
    if not citizenship and not residence:
        return EligibilityVerdict(
            "unknown",
            "The award restricts by nationality or residency, and the applicant's "
            "citizenship and residence are not recorded.",
            restrictions.evidence,
        )

    # Decided by the one eligibility engine, not by string equality.
    #
    # This compared the applicant's country to the restriction with `in` and
    # never consulted bloc membership, so a Cypriot against a Commonwealth-only
    # award came back `no` — a confident refusal of an eligible applicant, from
    # an API that disagreed with the one the pipeline uses. It also could not
    # see that "Deutschland" and "Germany" are one country.
    citizenship_answers = [
        country_satisfies(citizenship, restriction)
        for restriction in (*restrictions.citizenships, *restrictions.blocs)
    ] if citizenship else []
    residence_answers = [
        country_satisfies(residence, restriction)
        for restriction in (*restrictions.residencies, *restrictions.blocs)
    ] if residence else []
    answers = citizenship_answers + residence_answers

    if any(answer is True for answer in answers):
        satisfied = "citizenship" if True in citizenship_answers else "residence"
        return EligibilityVerdict(
            "yes", f"The applicant's {satisfied} is among those the award names.",
            restrictions.evidence,
        )

    named = ", ".join(sorted(set(
        restrictions.citizenships + restrictions.residencies + restrictions.blocs
    )))
    # An unresolved question is never a refusal. If nothing said "yes" and
    # anything said "I do not know" — an unrecognised country, a group with no
    # settled membership — the honest answer is unknown.
    if not answers or any(answer is None for answer in answers):
        return EligibilityVerdict(
            "unknown",
            f"The award is restricted to {named}, and whether the applicant "
            f"satisfies that could not be determined from what is recorded.",
            restrictions.evidence,
        )

    return EligibilityVerdict(
        "no",
        f"The award is restricted to {named}; the applicant holds "
        f"{citizenship or 'an unrecorded citizenship'} and resides in "
        f"{residence or 'an unrecorded country'}.",
        restrictions.evidence,
    )


def extract_published_count(text: str) -> PublishedCount | None:
    """The number of awards, only when the page states one.

    "A number of scholarships are available" publishes no number, and reading
    one out of it would be an invented fact.
    """
    for match in _COUNT.finditer(text or ""):
        sentence = " ".join(match.group(0).split())
        raw = next(
            (g for g in match.groups()
             if g and (g.isdigit() or g.lower() in _NUMBER_WORDS)),
            None,
        )
        if raw is None:
            continue
        value = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw.lower()]
        if value <= 0 or value > 10_000:
            continue
        return PublishedCount(value, sentence)
    return None
