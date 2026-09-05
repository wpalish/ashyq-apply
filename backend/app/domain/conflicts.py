"""Detecting and *not* resolving contradictions between official sources.

When two official pages disagree, the product shows both, marks the
higher-specificity one as preferred, and drafts a question the applicant can
send to the admissions office. It never picks a winner silently.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.domain.enums import (
    DECISION_GRADE_CLAIMS,
    DISCOVERY_ONLY_SPECIFICITY,
    SPECIFICITY_RANK,
    ClaimStatus,
    ClaimType,
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
    """
    ids = claim_ids or {}
    by_type: dict[tuple[ClaimType, str | None, str | None, str | None], list[Claim]] = defaultdict(
        list
    )
    for c in claims:
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

        for c in pool:
            conflicted.add(id(c))

        conflicts.append(
            Conflict(
                claim_type=ctype,
                subject=subject,
                claim_ids=[ids.get(id(c), c.source_url) for c in pool],
                values=[c.normalized_value for c in pool],
                source_urls=[c.source_url for c in pool],
                preferred_claim_id=ids.get(id(preferred), preferred.source_url),
                resolution_rule=(
                    f"Preferring the more specific source ({preferred.source_specificity.value}); "
                    "the disagreement is shown rather than resolved."
                ),
                question_for_admissions=_draft_question(subject, pool, context, intake),
                unresolved=True,
            )
        )

    updated = [
        c.model_copy(update={"status": ClaimStatus.CONFLICTING}) if id(c) in conflicted else c
        for c in claims
    ]
    return conflicts, updated


def _draft_question(subject: str, pool: list[Claim], context: str, intake: str | None) -> str:
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
        "Could you confirm which value applies to my application cycle?",
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
