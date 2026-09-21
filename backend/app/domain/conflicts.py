"""Detecting and *not* resolving contradictions between official sources.

When two official pages disagree, the product shows both, marks the
higher-specificity one as preferred, and drafts a question the applicant can
send to the admissions office. It never picks a winner silently.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.domain.claim_scope import SCOPE_DIMENSIONS
from app.domain.enums import (
    DECISION_GRADE_CLAIMS,
    DISCOVERY_ONLY_SPECIFICITY,
    SPECIFICITY_RANK,
    ClaimStatus,
    ClaimType,
    ConflictKind,
    SourceSpecificity,
)
from app.schemas.claim import Claim, Conflict, UnresolvedQuestion

_LABELS: dict[ClaimType, str] = {
    ClaimType.IELTS_MIN_OVERALL: "the minimum overall IELTS band",
    ClaimType.IELTS_MIN_SUBSCORE: "the minimum IELTS band per section",
    ClaimType.MIN_GPA: "the minimum GPA",
    ClaimType.SAT_MIN_TOTAL: "the minimum SAT total",
    ClaimType.TOEFL_MIN_TOTAL: "the minimum TOEFL total",
    ClaimType.ADMISSION_DEADLINE: "the application deadline",
    ClaimType.SCHOLARSHIP_DEADLINE: "the scholarship deadline",
    ClaimType.TUITION: "the tuition fee",
    ClaimType.TOTAL_COST_OF_ATTENDANCE: "the total cost of attendance",
    ClaimType.SCHOLARSHIP_AMOUNT: "the award amount",
    ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE: "eligibility for international students",
}


#: Which dimension of a differing scope explains a disagreement, in the order
#: the guide reads them. Only dimensions a page can state about *who or when*
#: a rule applies: a differing programme is a grouping error, not a conflict
#: kind, and university/faculty differences are handled by identity.
_KIND_BY_DIMENSION: dict[str, ConflictKind] = {
    "population": ConflictKind.DIFFERENT_POPULATION,
    "residency": ConflictKind.DIFFERENT_RESIDENCY,
    "intake": ConflictKind.DIFFERENT_INTAKE,
    "academic_year": ConflictKind.DIFFERENT_ACADEMIC_YEAR,
    "degree": ConflictKind.DIFFERENT_DEGREE,
}


#: How far apart two sources must sit before their disagreement is read as
#: "one is simply more specific". Adjacent levels only — a programme page
#: against a university admissions page — because two sources of the same
#: kind disagreeing is a real contradiction, and a programme page against an
#: aggregator is a hierarchy problem that `enforce_source_hierarchy` already
#: handles before this runs.
_SPECIFICITY_LEVELS_THAT_EXPLAIN = frozenset(
    {
        (SourceSpecificity.PROGRAM_INTAKE, SourceSpecificity.UNIVERSITY_ADMISSIONS),
        (SourceSpecificity.PROGRAM, SourceSpecificity.UNIVERSITY_ADMISSIONS),
        (SourceSpecificity.PROGRAM_INTAKE, SourceSpecificity.PROGRAM),
    }
)


def _explained_by_specificity(pool: list[Claim]) -> bool:
    """Whether these sources are a specific rule beside a general one."""
    levels = {c.source_specificity for c in pool}
    if len(levels) != 2:
        return False
    a, b = sorted(levels, key=lambda level: SPECIFICITY_RANK.get(level, 9))
    return (a, b) in _SPECIFICITY_LEVELS_THAT_EXPLAIN


def classify_conflict(pool: list[Claim]) -> ConflictKind:
    """Why these pages disagree, as far as what they *state* can say.

    Two claims that both state a dimension and state it differently are not
    contradicting each other: they are rules for different people, years or
    degrees. Anything else — including a scope nobody recorded — stays a true
    conflict. Unknown is never rounded into "different", because that would
    explain away a real disagreement, which is the more dangerous error of the
    two: a wrongly-kept conflict costs a question, a wrongly-dismissed one
    costs the applicant a decision.
    """
    for dimension in SCOPE_DIMENSIONS:
        kind = _KIND_BY_DIMENSION.get(dimension)
        if kind is None:
            continue
        stated = {
            getattr(c.scope, dimension).strip().casefold()
            for c in pool
            if c.scope is not None and getattr(c.scope, dimension)
        }
        if len(stated) > 1:
            return kind
    if _explained_by_specificity(pool):
        # The guide's own example: a university-wide IELTS 6.5 and a
        # programme's 7.0 are two true rules at different levels, and calling
        # that a contradiction teaches an applicant to distrust both.
        return ConflictKind.MORE_SPECIFIC_SOURCE
    return ConflictKind.TRUE_CONFLICT


def _comparable(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return "|".join(sorted(str(v) for v in value))
    if isinstance(value, dict):
        return "|".join(f"{k}={v}" for k, v in sorted(value.items()))
    return str(value).strip().lower()


def find_conflicts(
    claims: list[Claim],
    claim_ids: dict[int, str] | None = None,
    *,
    context: str = "",
) -> tuple[list[Conflict], list[Claim]]:
    """Group claims by type and flag disagreements.

    Returns the conflicts plus the claim list with contradicting members
    re-stamped as CONFLICTING, so a disputed value can never later be read as
    verified.

    SUPERSEDED claims are dropped at the entry, before any grouping: they are
    the "was" half of a was/became pair — history, not live evidence — so an
    old value can never resurrect as a conflict against its own successor.
    """
    ids = claim_ids or {}
    live = [c for c in claims if c.status != ClaimStatus.SUPERSEDED]
    by_type: dict[tuple[ClaimType, str | None, str | None, str | None], list[Claim]] = defaultdict(
        list
    )
    for c in live:
        by_type[(c.claim_type, c.program, c.intake, c.subject_key)].append(c)

    conflicts: list[Conflict] = []
    conflicted: set[int] = set()

    for (ctype, program, intake, subject_key), group in by_type.items():
        # Aggregators never *create* a conflict with an official page.
        official = [c for c in group if c.source_specificity not in DISCOVERY_ONLY_SPECIFICITY]
        pool = official if official else group
        distinct = {_comparable(c.normalized_value) for c in pool}
        if len(distinct) < 2:
            continue

        pool.sort(key=lambda c: (SPECIFICITY_RANK.get(c.source_specificity, 9), -c.confidence))
        preferred = pool[0]
        label = _LABELS.get(ctype, ctype.value.replace("_", " "))
        subject = (
            label
            + (f" — {subject_key}" if subject_key else "")
            + (f" ({program})" if program else "")
        )

        kind = classify_conflict(pool)
        if kind in (ConflictKind.TRUE_CONFLICT, ConflictKind.MORE_SPECIFIC_SOURCE):
            # A real contradiction may poison the claims. Two rules for two
            # different *populations* may not: they are both correct, and
            # stamping them CONFLICTING would stop either from ever being used.
            #
            # MORE_SPECIFIC_SOURCE keeps today's stamping on purpose, and it
            # is the one case where this code disagrees with the phase guide.
            # The guide says a programme rule beside a university-wide rule is
            # not a contradiction and the specific one should be preferred for
            # assessment; `test_two_official_pages_disagreeing_produce_one_conflict`
            # encodes the opposite. Changing it changes what the product tells
            # an applicant, so the classification lands now, the behaviour
            # waits for the owner (HANDOFF §7).
            for c in pool:
                conflicted.add(id(c))

        conflicts.append(
            Conflict(
                claim_type=ctype,
                kind=kind,
                subject=subject,
                claim_ids=[ids.get(id(c), c.source_url) for c in pool],
                values=[c.normalized_value for c in pool],
                source_urls=[c.source_url for c in pool],
                preferred_claim_id=ids.get(id(preferred), preferred.source_url),
                resolution_rule=(
                    f"Preferring the more specific source ({preferred.source_specificity.value}); "
                    "the disagreement is shown rather than resolved."
                    if kind is ConflictKind.TRUE_CONFLICT
                    else _why_not_a_contradiction(kind, preferred)
                ),
                question_for_admissions=_draft_question(subject, pool, context, intake, kind),
                unresolved=True,
            )
        )

    updated = [
        c.model_copy(update={"status": ClaimStatus.CONFLICTING}) if id(c) in conflicted else c
        for c in live
    ]
    return conflicts, updated


def _ask(kind: ConflictKind) -> str:
    """The one sentence the applicant actually sends.

    Worded per kind, because the question a person needs answered differs:
    with a true contradiction they ask which value is right, and with a
    general rule beside a specific one they already know both may be right
    and need to know which governs their application.
    """
    if kind is ConflictKind.TRUE_CONFLICT:
        return "Could you confirm which value applies to my application cycle?"
    if kind is ConflictKind.MORE_SPECIFIC_SOURCE:
        return (
            "One of these is published for the programme and the other university-wide. "
            "Could you confirm which one governs my application?"
        )
    dimension = kind.value.removeprefix("different_").replace("_", " ")
    return (
        f"These appear to be published for different {dimension}s. Could you confirm which "
        "one applies to me?"
    )


def _why_not_a_contradiction(kind: ConflictKind, preferred: Claim) -> str:
    if kind is ConflictKind.MORE_SPECIFIC_SOURCE:
        return (
            "Not a contradiction: a programme-specific rule and a university-wide rule can "
            f"both be true. The more specific source ({preferred.source_specificity.value}) "
            "applies to this application; the broader rule is kept, not discarded."
        )
    dimension = kind.value.removeprefix("different_").replace("_", " ")
    return (
        f"Not a contradiction: the pages state different {dimension}s, so both values can "
        "be correct. Neither is discarded."
    )


def _draft_question(
    subject: str,
    pool: list[Claim],
    context: str,
    intake: str | None,
    kind: ConflictKind = ConflictKind.TRUE_CONFLICT,
) -> str:
    lines = [
        "Dear Admissions Office,",
        "",
        f"I am preparing an application{f' for {context}' if context else ''}"
        f"{f' for the {intake} intake' if intake else ''} and I found different published values for {subject}:",
        "",
    ]
    for c in pool:
        lines.append(f"  - {c.normalized_value}  ({c.source_url})")
    lines += [
        "",
        _ask(kind),
        "",
        "Thank you for your time.",
    ]
    return "\n".join(lines)


def enforce_source_hierarchy(claims: list[Claim]) -> tuple[list[Claim], list[UnresolvedQuestion]]:
    """Demote decision-grade claims that rest only on an aggregator.

    Rankings and directories are allowed to *find* a university. They are never
    allowed to be the last word on a requirement, a deadline or a price.
    """
    out: list[Claim] = []
    questions: list[UnresolvedQuestion] = []
    for c in claims:
        if (
            c.claim_type in DECISION_GRADE_CLAIMS
            and c.source_specificity in DISCOVERY_ONLY_SPECIFICITY
        ):
            out.append(
                c.model_copy(
                    update={
                        "status": ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION,
                        "confidence": min(c.confidence, 0.3),
                        "notes": ((c.notes + " ") if c.notes else "")
                        + "Demoted: an aggregator or unidentified source cannot support this "
                        "type of claim on its own.",
                    }
                )
            )
            questions.append(
                UnresolvedQuestion(
                    topic=c.claim_type.value,
                    question=(
                        f"Confirm {c.claim_type.value.replace('_', ' ')} on an official university page "
                        f"(current value {c.normalized_value!r} came from a non-official source)."
                    ),
                    why_it_matters="Aggregator data is frequently out of date for this field.",
                    program=c.program,
                )
            )
        else:
            out.append(c)
    return out, questions
