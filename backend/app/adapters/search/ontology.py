"""What counts as the same field, and what is merely worth looking at.

The distinction this module exists for is the one the phase guide states and
this repository has already paid for by hand: *computing science* is another
name for computer science, while *data science* is a neighbour. Treating the
second like the first is how an applicant who asked for computer science ends
up looking at a programme that will not accept their application.

So the two ideas never share a return value:

* :func:`is_equivalent` answers "same field?" and consults strong aliases only;
* :func:`retrieval_candidates` answers "what else is worth fetching?" and
  labels every result with its relation.

A related concept can therefore never be returned from the equivalence
function, whatever a caller does with it. That is the point — the wrong call
should be hard to write, not merely discouraged.

The vocabulary itself lives in ``ontology.json`` and carries a version, so a
retrieval result measured today can be explained later.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from app.domain.enums import DegreeLevel
from app.domain.programme_identity import Verdict

ONTOLOGY_PATH = Path(__file__).resolve().parent / "ontology.json"


class Relation(StrEnum):
    """How a term relates to a canonical concept."""

    #: The same field under another name. Safe to treat as a match.
    STRONG_ALIAS = "strong_alias"
    #: A neighbouring field. Worth retrieving, never an automatic match.
    RELATED = "related"
    #: A strong alias in another language.
    LOCALIZED_ALIAS = "localized_alias"


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    """One term to search for, and why it is on the list."""

    term: str
    relation: Relation
    #: ISO-639-1 where the term is not English.
    language: str = "en"

    @property
    def is_match(self) -> bool:
        """Whether finding this term means the requested field was found."""
        return self.relation is not Relation.RELATED


@dataclass(frozen=True, slots=True)
class Ontology:
    version: str
    fields: dict[str, dict]
    degrees: dict[str, dict]


def _normalize(term: str) -> str:
    """Casefold and strip accents, so ``Informatik`` and ``informatik`` agree.

    Accent folding is for lookup only. The ontology keeps terms as they are
    written, because a query goes out in the language of the site.
    """
    decomposed = unicodedata.normalize("NFKD", term.strip().casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def load_ontology() -> Ontology:
    raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    return Ontology(version=raw["version"], fields=raw["fields"], degrees=raw["degrees"])


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    """Every strong and localized alias to its concept key.

    Related terms are deliberately absent: they are other concepts' names, and
    resolving through them would make ``data science`` resolve to computer
    science, which is the error this module exists to prevent.
    """
    index: dict[str, str] = {}
    for key, concept in load_ontology().fields.items():
        terms = [key.replace("_", " "), *concept["strong_aliases"]]
        terms += [entry["alias"] for entry in concept.get("localized_aliases", ())]
        for term in terms:
            normalized = _normalize(term)
            first = index.setdefault(normalized, key)
            if first != key:
                raise ValueError(
                    f"{term!r} is a strong alias of both {first!r} and {key!r}. "
                    "An ambiguous alias cannot be resolved; make one of them a "
                    "related_not_equivalent entry."
                )
    return index


def canonical_field(term: str) -> str | None:
    """The concept key ``term`` names, or ``None`` if the ontology has no entry.

    ``None`` means "not in the vocabulary", never "not a real field". An
    unknown field is searched for verbatim, which is what happened before this
    module existed and remains correct.
    """
    return _alias_index().get(_normalize(term))


def is_equivalent(left: str, right: str) -> bool:
    """Whether two terms name the same field.

    Two spellings of one word are equal; beyond that, equality comes only from
    sharing a canonical concept through a *strong* alias. Two terms the
    ontology has never heard of are equal only if they are written the same:
    this function will not guess that two unknown names mean one field.
    """
    if _normalize(left) == _normalize(right):
        return True
    left_key, right_key = canonical_field(left), canonical_field(right)
    return left_key is not None and left_key == right_key


def fields_named_in(title: str) -> frozenset[str]:
    """Which canonical fields a programme *title* states outright.

    A title is not a term: "Bachelor of Computing (Hons) in Computer Science"
    names a field inside a sentence about a degree. Matching is still exact —
    a strong or localized alias found as a whole phrase — so nothing is
    inferred from a title merely looking like a field's name.

    Related terms stay out, for the reason ``_alias_index`` gives: resolving
    through them would let "data science" name computer science.
    """
    haystack = f" {_normalize(title)} "
    return frozenset(key for alias, key in _alias_index().items() if f" {alias} " in haystack)


def titles_name_same_programme(left: str, right: str) -> Verdict:
    """Whether two programme titles name one programme, as far as evidence says.

    Exists because the benchmark compares a label's short name against the
    full official title a page publishes, and scores them as a wrong-scope
    claim: NTU's "Bachelor of Computing (Hons) in Computer Science" against a
    label reading "Computer Science" is the same programme written two ways,
    while "Bachelor of Science in Mathematical and Computer Sciences" may well
    be a different degree.

    ``UNKNOWN`` is therefore common and correct. A title naming no field in
    the vocabulary resolves to nothing rather than to a guess, and two titles
    naming different fields are refused outright.
    """
    if _normalize(left) == _normalize(right):
        return Verdict.YES
    left_fields, right_fields = fields_named_in(left), fields_named_in(right)
    if not left_fields or not right_fields:
        return Verdict.UNKNOWN
    if left_fields == right_fields:
        return Verdict.YES
    if left_fields.isdisjoint(right_fields):
        return Verdict.NO
    # Overlapping but not equal: one title names a field the other does not,
    # e.g. a joint degree. That is a question for a human, not a match.
    return Verdict.UNKNOWN


def retrieval_candidates(
    term: str, *, include_localized: bool = True
) -> tuple[RetrievalCandidate, ...]:
    """Terms worth searching for when looking for ``term``, most certain first.

    Strong aliases come before related concepts, so a caller with a small
    query budget spends it on terms that would be a match rather than on
    neighbours it would still have to adjudicate.
    """
    key = canonical_field(term)
    if key is None:
        return (RetrievalCandidate(term=term.strip(), relation=Relation.STRONG_ALIAS),)

    concept = load_ontology().fields[key]
    candidates = [
        RetrievalCandidate(term=alias, relation=Relation.STRONG_ALIAS)
        for alias in concept["strong_aliases"]
    ]
    if include_localized:
        candidates += [
            RetrievalCandidate(
                term=entry["alias"],
                relation=Relation.LOCALIZED_ALIAS,
                language=entry["language"],
            )
            for entry in concept.get("localized_aliases", ())
        ]
    candidates += [
        RetrievalCandidate(term=related, relation=Relation.RELATED)
        for related in concept["related_not_equivalent"]
    ]
    return tuple(candidates)


def degree_aliases(degree: DegreeLevel) -> tuple[str, ...]:
    """Every published way of writing this degree level, canonical form first."""
    return tuple(load_ontology().degrees[str(degree)]["aliases"])


def ontology_version() -> str:
    """Stamp this onto any retrieval measurement, so it can be explained later."""
    return load_ontology().version
