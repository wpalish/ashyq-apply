"""Judging an applicant against what a page published.

Pure functions, moved out of the runner unchanged. They take a profile and an
award or a requirement and return a verdict with its explanation; none of them
touches the database, the network or the run's state, which is what makes them
testable on their own.

The three judgements the product keeps apart — eligibility, admissions fit and
funding fit — are computed here and never collapsed into one number.
"""

from __future__ import annotations

from app.domain.countries import country_satisfies, describe_restriction
from app.domain.enums import ClaimType, EligibilityStatus
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RequirementCheck, Tristate


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


def _country_checks(s, citizenship: str, residence: str) -> list:
    """Whether the applicant's country satisfies the award's own conditions.

    Each restriction is resolved by membership, not by asking whether one
    string appears inside another — `"Germany" in "European Union"` is False,
    which is how a German citizen came to be refused an EU-only award.

    Three answers per route, and unknown is a real one: an unrecognised country
    or a group with no agreed membership ("students from Europe") is a question
    for the admissions office, not a refusal.
    """
    checks: list[RequirementCheck] = []
    citizenship_verdict = _route_verdict(citizenship, s.citizenship_restrictions)
    residence_verdict = _route_verdict(residence, s.residency_restrictions)
    routes = [v for v in (citizenship_verdict, residence_verdict) if v is not _NO_ROUTE]

    if not routes:
        return checks

    # How the page joins the two. "unknown" is not silently read as "either":
    # doing that turns an AND condition into an OR and admits an applicant who
    # meets half of it.
    logic = getattr(s, "restriction_logic", "unknown")
    if len(routes) < 2:
        satisfied = routes[0]
    elif logic == "all":
        satisfied = _combine_all(routes)
    elif logic == "any":
        satisfied = _combine_any(routes)
    else:
        satisfied = None

    named = ", ".join(
        describe_restriction(r)
        for r in dict.fromkeys([*s.citizenship_restrictions, *s.residency_restrictions])
    )
    if satisfied is True:
        status = EligibilityStatus.MET
        explanation = (
            f"The applicant's country satisfies the published restriction: {named}."
        )
    elif satisfied is False:
        status = EligibilityStatus.NOT_APPLICABLE
        explanation = (
            f"The award is restricted to {named}. An applicant holding "
            f"{citizenship or 'an unrecorded'} citizenship and residing in "
            f"{residence or 'an unrecorded country'} is not eligible."
        )
    else:
        status = EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        explanation = (
            f"The award is restricted to {named}, and whether this applicant "
            "satisfies it could not be decided from the page: "
            + _why_unknown(citizenship, residence, s, logic, len(routes))
            + " This is a question for the admissions office, not a refusal."
        )

    checks.append(
        _check(
            "Scholarship citizenship or residency eligibility",
            [*s.citizenship_restrictions, *s.residency_restrictions],
            f"{citizenship or 'unrecorded'} / {residence or 'unrecorded'}",
            status,
            explanation,
        )
    )
    return checks


#: A route the award does not restrict at all, as opposed to one it restricts
#: and the applicant fails.
_NO_ROUTE = object()


def _route_verdict(country: str, restrictions: list[str]):
    """True / False / None for one route, or `_NO_ROUTE` if unrestricted."""
    if not restrictions:
        return _NO_ROUTE
    verdicts = [country_satisfies(country, r) for r in restrictions]
    if any(v is True for v in verdicts):
        return True
    if any(v is None for v in verdicts):
        return None  # something on the list could not be resolved
    return False


def _combine_any(routes) -> bool | None:
    if any(v is True for v in routes):
        return True
    if any(v is None for v in routes):
        return None
    return False


def _combine_all(routes) -> bool | None:
    if any(v is False for v in routes):
        return False
    if any(v is None for v in routes):
        return None
    return True


def _why_unknown(citizenship, residence, s, logic, route_count) -> str:
    if not citizenship and not residence:
        return "the applicant's citizenship and country of residence are not recorded."
    if route_count > 1 and logic == "unknown":
        return (
            "the page names both a nationality and a residency condition without "
            "saying whether either alone is enough."
        )
    return "the restriction names a group whose membership is not resolved here."


def _scholarship_eligibility(s, profile: ApplicantProfileIn):
    """Check the applicant against an award's own published restrictions."""
    checks = []
    citizenship = profile.context.citizenship
    residence = profile.context.country_of_residence
    if s.citizenship_restrictions or s.residency_restrictions:
        checks.extend(_country_checks(s, citizenship, residence))
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


