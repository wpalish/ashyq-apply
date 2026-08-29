"""Judging an applicant against what a page published.

Pure functions, moved out of the runner unchanged. They take a profile and an
award or a requirement and return a verdict with its explanation; none of them
touches the database, the network or the run's state, which is what makes them
testable on their own.

The three judgements the product keeps apart — eligibility, admissions fit and
funding fit — are computed here and never collapsed into one number.
"""

from __future__ import annotations

from app.domain.enums import ClaimType, EligibilityStatus
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import Tristate


def _check(requirement, published, applicant, status, explanation, hard=False):
    from app.schemas.result import RequirementCheck

    return RequirementCheck(
        requirement=requirement,
        published_value=published,
        applicant_value=applicant,
        status=status,
        is_hard_filter=hard,
        explanation=explanation,
    )


def _scholarship_eligibility(s, profile: ApplicantProfileIn):
    """Check the applicant against an award's own published restrictions."""
    checks = []
    citizenship = profile.context.citizenship
    residence = profile.context.country_of_residence
    if s.citizenship_restrictions or s.residency_restrictions:
        # Nationality and residency are separate routes into the same award,
        # and an award naming both accepts either. TU Delft's CLIP award goes
        # to students who "hold either a Greek passport or Greek residence": an
        # applicant with Greek residence qualifies on residence alone, so
        # checking citizenship by itself would wrongly exclude them.
        by_citizenship = bool(
            s.citizenship_restrictions
            and citizenship
            and citizenship.lower() in " ".join(s.citizenship_restrictions).lower()
        )
        by_residence = bool(
            s.residency_restrictions
            and residence
            and residence.lower() in " ".join(s.residency_restrictions).lower()
        )
        ok = by_citizenship or by_residence
        named = ", ".join(sorted(
            {*s.citizenship_restrictions, *s.residency_restrictions}
        ))
        if ok:
            route = "citizenship" if by_citizenship else "country of residence"
            explanation = f"The applicant's {route} falls within the published restriction."
        else:
            explanation = (
                f"The award is restricted to {named}. An applicant holding "
                f"{citizenship or 'an unrecorded'} citizenship and residing in "
                f"{residence or 'an unrecorded country'} is not eligible."
            )
        checks.append(
            _check(
                "Scholarship citizenship or residency eligibility",
                [*s.citizenship_restrictions, *s.residency_restrictions],
                f"{citizenship} / {residence}",
                EligibilityStatus.MET if ok else EligibilityStatus.NOT_APPLICABLE,
                explanation,
            )
        )
    elif s.international_eligible == "no":
        checks.append(
            _check(
                "Scholarship international eligibility",
                False,
                citizenship,
                EligibilityStatus.NOT_APPLICABLE,
                "The award is officially closed to international students.",
            )
        )
    elif s.international_eligible == "yes":
        checks.append(
            _check(
                "Scholarship international eligibility",
                True,
                citizenship,
                EligibilityStatus.MET,
                "The award is officially open to international students of any nationality.",
            )
        )

    for test, minimum in (s.min_test_scores or {}).items():
        got = {
            "ielts": profile.academics.ielts.overall,
            "toefl": profile.academics.toefl.total,
            "sat": profile.academics.sat.total,
        }.get(test)
        if got is None:
            checks.append(
                _check(
                    f"Scholarship {test.upper()} minimum",
                    minimum,
                    None,
                    EligibilityStatus.PENDING,
                    f"The award requires {test.upper()} {minimum}; no score is in the profile.",
                )
            )
        else:
            checks.append(
                _check(
                    f"Scholarship {test.upper()} minimum",
                    minimum,
                    got,
                    EligibilityStatus.MET if got >= minimum else EligibilityStatus.GAP,
                    f"Published minimum {minimum}; applicant {got}.",
                )
            )
    return checks


def _applicant_eligible(scholarship) -> Tristate:
    """Roll a scholarship's eligibility checks into one three-valued verdict."""
    statuses = {c.status for c in scholarship.eligibility_checks}
    if scholarship.degree_applicability == "no" or scholarship.international_eligible == "no":
        return "no"
    if EligibilityStatus.NOT_APPLICABLE in statuses or EligibilityStatus.GAP in statuses:
        return "no"
    if not statuses or EligibilityStatus.PENDING in statuses:
        return "unknown"
    if scholarship.degree_applicability == "unknown":
        return "unknown"
    if statuses <= {EligibilityStatus.MET}:
        return "yes"
    return "unknown"


def _explanation_component(text: str):
    from app.schemas.result import ScoreComponent

    return ScoreComponent(
        name="Admissions fit rationale",
        raw=0.0,
        weight=0.0,
        weighted=0.0,
        explanation=text,
        data_present=True,
    )


#: The questions a user actually needs answered before applying. Completeness is
#: measured against these, not against whatever happened to be extracted -
#: otherwise a page yielding one verified fact and nothing else reads as 100%.
CORE_QUESTIONS: tuple[tuple[ClaimType, ...], ...] = (
    (ClaimType.IELTS_MIN_OVERALL, ClaimType.TOEFL_MIN_TOTAL, ClaimType.DUOLINGO_MIN),
    (ClaimType.MIN_GPA,),
    (ClaimType.ADMISSION_DEADLINE,),
    (ClaimType.TUITION, ClaimType.TOTAL_COST_OF_ATTENDANCE),
    (ClaimType.SCHOLARSHIP_EXISTS,),
    (ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION),
)


def _fit_label(actual: str | None, preferred: str) -> str:
    if not actual or actual == "unknown":
        return "unknown"
    if preferred in ("any", ""):
        return "acceptable"
    if actual == preferred:
        return "strong"
    ladders = {
        "city": ["small", "medium", "large", "metropolis"],
        "climate": ["cold", "temperate", "mediterranean", "warm"],
        "workload": ["moderate", "demanding", "very_demanding"],
    }
    for ladder in ladders.values():
        if actual in ladder and preferred in ladder:
            gap = abs(ladder.index(actual) - ladder.index(preferred))
            return {0: "strong", 1: "good", 2: "acceptable"}.get(gap, "weak")
    return "acceptable"


