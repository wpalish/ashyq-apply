"""Hand-verified answers, frozen before the extractor is changed.

Why this exists
---------------

Extraction completeness is 5.6% against twenty-five decision questions, and
nothing in the repository can say *why*. The canary counts claims the extractor
produced; it cannot count the ones it should have produced, because nobody
wrote down what the pages actually say. A number with no denominator cannot be
improved against — every change looks like progress if the only measure is how
much the machine emitted.

So: a person reads the page and records the answer, with the URL and the
sentence it came from. The extractor is then measured against that, per field,
as precision and recall rather than as a count.

The three verdicts, and why the third one matters most
-----------------------------------------------------

For each of the twenty-five questions, on each programme, the audit records:

``answered``
    The institution publishes the answer. The truth is recorded with the
    official URL, the excerpt that carries it, when it was read, how specific
    the page is, and the claim's status. Missing it is a **recall failure**.

``absent``
    The institution genuinely does not publish it — checked, not assumed. A
    great many of the twenty-five are simply not answered on most sites, and an
    extractor cannot be marked down for that. Emitting one anyway is a
    **precision failure**, which is the more dangerous direction: an applicant
    acting on an invented deadline misses it.

``not_checked``
    Nobody has audited this pair yet. Counted in **neither** numerator nor
    denominator, and reported as coverage, so the dataset can grow without
    quietly flattering the result. A gold set that hides its own gaps is worse
    than no gold set, because it produces a number that looks like a
    measurement.

The freezing rule
-----------------

The *selection* — which institutions, which programmes — is frozen before any
change to extraction, and the rule that produced it is written down in
``SELECTION_RULE`` rather than left to taste. A benchmark assembled after seeing
the results measures the assembler.

Truth values are added over time, because reading pages by hand takes time.
That is a different thing from changing the selection, and the digest test in
``tests/test_gold_dataset.py`` distinguishes them: adding an audited answer is
expected, and editing which programmes are in the set requires re-freezing in a
visible commit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity

GOLD_DIR = Path(__file__).resolve().parent.parent / "corpus" / "gold"
GOLD_FILE = GOLD_DIR / "gold_claims.json"

#: How the programmes were chosen, recorded before any of them was looked at.
#: Stated as a rule so that the set cannot be quietly curated: an institution
#: that turns out to be hard stays, and is recorded as hard.
SELECTION_RULE = (
    "For each of the ten institutions in the canary registry, the two "
    "English-taught bachelor's programmes nearest to (1) computer science and "
    "(2) mechanical or electrical engineering. Where an institution teaches no "
    "English-taught bachelor's in a discipline, that is recorded as such and "
    "the slot stays empty rather than being filled with an easier programme."
)

ANSWERED = "answered"
ABSENT = "absent"
NOT_CHECKED = "not_checked"
VERDICTS = (ANSWERED, ABSENT, NOT_CHECKED)


@dataclass(frozen=True)
class GoldClaim:
    """One hand-verified answer, with everything needed to check it again."""

    type: ClaimType
    value: str
    source_url: str
    excerpt: str
    accessed_at: date
    specificity: SourceSpecificity
    status: ClaimStatus


@dataclass(frozen=True)
class GoldAnswer:
    """What the audit found for one decision question on one programme."""

    question: str
    verdict: str
    claims: tuple[GoldClaim, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class GoldProgramme:
    """One slot in the frozen selection.

    `institution` + `discipline` is the frozen identity and cannot change
    without re-freezing. `programme` and `programme_url` are *resolved* during
    the audit — a person finds the actual programme that fits the slot — so
    they start empty and are required the moment anything is audited. That
    split is what lets the set be populated over time without letting the
    selection drift toward whatever turned out to be easy.
    """

    id: str
    institution: str
    domain: str
    discipline: str
    programme: str
    programme_url: str
    answers: tuple[GoldAnswer, ...]

    def answered(self) -> tuple[GoldAnswer, ...]:
        return tuple(a for a in self.answers if a.verdict == ANSWERED)

    def absent(self) -> tuple[GoldAnswer, ...]:
        return tuple(a for a in self.answers if a.verdict == ABSENT)

    def checked(self) -> tuple[GoldAnswer, ...]:
        return tuple(a for a in self.answers if a.verdict != NOT_CHECKED)


@dataclass(frozen=True)
class GoldSet:
    version: int
    frozen_at: date
    frozen_at_commit: str
    selection_rule: str
    programmes: tuple[GoldProgramme, ...]

    def resolved(self) -> tuple[GoldProgramme, ...]:
        """Slots where a real programme has been identified."""
        return tuple(p for p in self.programmes if p.programme_url)

    def coverage(self) -> dict[str, int]:
        """How much of the set has actually been audited.

        Reported everywhere the set is used. A partially audited benchmark is
        useful; one that does not say it is partial is not.
        """
        answers = [a for p in self.programmes for a in p.answers]
        return {
            "programmes": len(self.programmes),
            "programmes_resolved": len(self.resolved()),
            "question_slots": len(answers),
            "answered": sum(1 for a in answers if a.verdict == ANSWERED),
            "absent": sum(1 for a in answers if a.verdict == ABSENT),
            "not_checked": sum(1 for a in answers if a.verdict == NOT_CHECKED),
        }


class GoldDataError(ValueError):
    """The dataset says something it cannot support."""


def _registrable(host: str) -> str:
    """Enough of the host to compare two URLs' ownership.

    Deliberately simple: the gold set is checked against the domain the
    programme itself is on, so `www.rug.nl` and `rug.nl` must compare equal
    while `rug.nl.example.com` must not.
    """
    return host.lower().removeprefix("www.")


def _claim(raw: dict[str, Any], *, where: str) -> GoldClaim:
    missing = [
        field
        for field in ("type", "value", "source_url", "excerpt", "accessed_at",
                      "specificity", "status")
        if not raw.get(field)
    ]
    if missing:
        raise GoldDataError(f"{where}: claim is missing {', '.join(missing)}")
    try:
        claim_type = ClaimType(raw["type"])
    except ValueError as exc:
        raise GoldDataError(f"{where}: {raw['type']!r} is not a claim type") from exc
    try:
        specificity = SourceSpecificity(raw["specificity"])
    except ValueError as exc:
        raise GoldDataError(
            f"{where}: {raw['specificity']!r} is not a source specificity"
        ) from exc
    try:
        status = ClaimStatus(raw["status"])
    except ValueError as exc:
        raise GoldDataError(f"{where}: {raw['status']!r} is not a claim status") from exc
    return GoldClaim(
        type=claim_type,
        value=str(raw["value"]),
        source_url=raw["source_url"],
        excerpt=raw["excerpt"],
        accessed_at=date.fromisoformat(raw["accessed_at"]),
        specificity=specificity,
        status=status,
    )


def parse(payload: dict[str, Any]) -> GoldSet:
    """Build the set, refusing anything it could not stand behind."""
    programmes: list[GoldProgramme] = []
    for raw in payload.get("programmes", []):
        where = raw.get("id", "<unnamed programme>")
        answers: list[GoldAnswer] = []
        for entry in raw.get("answers", []):
            verdict = entry.get("verdict")
            if verdict not in VERDICTS:
                raise GoldDataError(
                    f"{where}/{entry.get('question')}: verdict {verdict!r} is not "
                    f"one of {VERDICTS}"
                )
            claims = tuple(
                _claim(c, where=f"{where}/{entry.get('question')}")
                for c in entry.get("claims", [])
            )
            if verdict == ANSWERED and not claims:
                raise GoldDataError(
                    f"{where}/{entry.get('question')}: recorded as answered with "
                    "no claim behind it"
                )
            if verdict != ANSWERED and claims:
                raise GoldDataError(
                    f"{where}/{entry.get('question')}: recorded as {verdict} but "
                    "carries claims"
                )
            answers.append(
                GoldAnswer(
                    question=entry["question"],
                    verdict=verdict,
                    claims=claims,
                    note=entry.get("note", ""),
                )
            )
        programme = GoldProgramme(
            id=raw["id"],
            institution=raw["institution"],
            domain=raw["domain"],
            discipline=raw["discipline"],
            programme=raw.get("programme", ""),
            programme_url=raw.get("programme_url", ""),
            answers=tuple(answers),
        )
        if programme.checked() and not (programme.programme and programme.programme_url):
            raise GoldDataError(
                f"{where}: audited without naming the programme it audited"
            )
        for answer in programme.answered():
            for claim in answer.claims:
                if not source_is_official(claim, programme):
                    raise GoldDataError(
                        f"{where}/{answer.question}: {claim.source_url} is not on "
                        f"{programme.domain}; gold truth must come from the "
                        "institution, not from an aggregator"
                    )
        programmes.append(programme)
    return GoldSet(
        version=payload["version"],
        frozen_at=date.fromisoformat(payload["frozen_at"]),
        frozen_at_commit=payload["frozen_at_commit"],
        selection_rule=payload["selection_rule"],
        programmes=tuple(programmes),
    )


@lru_cache
def load_gold(path: Path | None = None) -> GoldSet:
    return parse(json.loads((path or GOLD_FILE).read_text()))


def source_is_official(claim: GoldClaim, programme: GoldProgramme) -> bool:
    """Whether the claim's URL is on the institution's own domain.

    A gold answer taken from a rankings site or a study-abroad portal would be
    measuring the extractor against an aggregator, which the product refuses to
    treat as proof. The truth has to come from the same kind of source the
    product would accept.
    """
    host = _registrable(urlsplit(claim.source_url).hostname or "")
    domain = _registrable(programme.domain)
    return host == domain or host.endswith(f".{domain}")
