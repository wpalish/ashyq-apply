"""Eligibility evaluation.

Two asymmetries are deliberate:

* A hard filter fires only on a *confirmed* requirement the applicant
  *confirmed* they miss. Absent data never eliminates a university.
* A test-optional policy, or a requirement we could not read, produces
  PENDING or NEEDS_OFFICIAL_CLARIFICATION — never GAP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.domain.enums import (
    SPECIFICITY_RANK,
    ClaimStatus,
    ClaimType,
    EligibilityStatus,
)
from app.schemas.claim import Claim
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import RequirementCheck

IELTS_SUBSKILLS = ("listening", "reading", "writing", "speaking")


@dataclass
class EligibilityOutcome:
    status: EligibilityStatus
    checks: list[RequirementCheck] = field(default_factory=list)
    hard_filter_failures: list[str] = field(default_factory=list)
    missing_prerequisites: list[str] = field(default_factory=list)


def _confirmed(claim: Claim | None) -> bool:
    """A claim strong enough to eliminate a candidate."""
    return claim is not None and claim.status in {
        ClaimStatus.VERIFIED_CURRENT,
        ClaimStatus.POSSIBLY_STALE,
    }


def _first(claims: list[Claim], claim_type: ClaimType) -> Claim | None:
    matches = [c for c in claims if c.claim_type == claim_type]
    if not matches:
        return None
    # Source specificity comes first, so that when a programme page and a
    # general admissions page disagree, the evaluation follows the same rule the
    # conflict panel shows the user: the more specific page wins. Falling back
    # to recency here would let the two disagree with each other.
    matches.sort(
        key=lambda c: (
            SPECIFICITY_RANK.get(c.source_specificity, 9),
            c.status != ClaimStatus.VERIFIED_CURRENT,
            -c.confidence,
            -c.accessed_at.timestamp(),
        )
    )
    return matches[0]


def _check_numeric_minimum(
    label: str,
    claim: Claim | None,
    applicant_value: float | None,
    *,
    higher_is_better: bool = True,
    hard: bool = True,
) -> RequirementCheck:
    if claim is None:
        return RequirementCheck(
            requirement=label,
            status=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION,
            explanation=f"No official minimum for {label} was found; not treated as a barrier.",
        )
    try:
        published = float(claim.normalized_value)
    except (TypeError, ValueError):
        return RequirementCheck(
            requirement=label,
            published_value=claim.normalized_value,
            status=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION,
            explanation=f"The published {label} could not be read as a number.",
            claim_ids=[claim.source_url],
        )
    if applicant_value is None:
        return RequirementCheck(
            requirement=label,
            published_value=published,
            status=EligibilityStatus.PENDING,
            explanation=(
                f"The programme publishes a minimum of {published:g}, but the profile has no "
                f"{label} value yet. Add it to resolve this check."
            ),
            claim_ids=[claim.source_url],
        )
    ok = applicant_value >= published if higher_is_better else applicant_value <= published
    return RequirementCheck(
        requirement=label,
        published_value=published,
        applicant_value=applicant_value,
        status=EligibilityStatus.MET if ok else EligibilityStatus.GAP,
        is_hard_filter=hard and _confirmed(claim) and not ok,
        explanation=(
            f"Published minimum {published:g}; applicant {applicant_value:g}."
            + ("" if ok else " The published minimum is not met.")
        ),
        claim_ids=[claim.source_url],
    )


#: Months before an intake starts within which its application deadline can
#: plausibly fall. Eighteen covers the early-decision routes that open more
#: than a year ahead; anything earlier belongs to the previous cycle.
DEADLINE_WINDOW_MONTHS = 18

#: Roughly when each intake term begins, for measuring that window. Only the
#: month matters, and only to within a month or two.
_INTAKE_START_MONTH = {"fall": 9, "autumn": 9, "spring": 1, "summer": 6, "winter": 1}


def _plausible_for_intake(deadline: date, profile: ApplicantProfileIn) -> bool:
    """Whether a published deadline could belong to the applicant's intake.

    A deadline is for one admission cycle. Comparing it to today answers "has
    this date passed", which is not the same question as "is this my deadline",
    and the two come apart exactly when a page still shows last cycle's date.
    """
    term = (profile.context.intake_term or "fall").lower()
    year = profile.context.intake_year
    if not year:
        return True  # nothing to scope against; fall back to the date comparison
    month = _INTAKE_START_MONTH.get(term, 9)
    start = date(year, month, 1)
    earliest = start - timedelta(days=DEADLINE_WINDOW_MONTHS * 31)
    # A deadline after the intake starts is odd but not evidence of the wrong
    # cycle; only "far too early" identifies a previous one.
    return deadline >= earliest


def evaluate_program(
    profile: ApplicantProfileIn,
    claims: list[Claim],
    *,
    today: date | None = None,
) -> EligibilityOutcome:
    """Compare one programme's published requirements against the profile."""
    today = today or date.today()
    checks: list[RequirementCheck] = []
    a = profile.academics

    # --- intake open --------------------------------------------------
    intake_claim = _first(claims, ClaimType.INTAKE_OPEN)
    if intake_claim is not None and intake_claim.normalized_value is False and _confirmed(intake_claim):
        checks.append(
            RequirementCheck(
                requirement="Intake accepting applications",
                published_value=False,
                status=EligibilityStatus.GAP,
                is_hard_filter=True,
                explanation="The programme officially states it is not accepting applications for this intake.",
                claim_ids=[intake_claim.source_url],
            )
        )

    # --- deadline -----------------------------------------------------
    deadline_claim = _first(claims, ClaimType.ADMISSION_DEADLINE)
    if deadline_claim is not None:
        parsed = _as_date(deadline_claim.normalized_value)
        if parsed is None:
            checks.append(
                RequirementCheck(
                    requirement="Admission deadline",
                    published_value=deadline_claim.normalized_value,
                    status=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION,
                    explanation="A deadline was published but could not be parsed into a date.",
                    claim_ids=[deadline_claim.source_url],
                )
            )
        elif not _plausible_for_intake(parsed, profile):
            # A deadline from another admission cycle is published, confirmed,
            # and not this applicant's requirement. Uppsala shows "Application
            # deadline 15 January 2026" on programme pages; read against a Fall
            # 2027 applicant in August 2026 the date has passed, and using it as
            # a hard filter eliminated the programme on the previous intake's
            # deadline.
            intake = f"{profile.context.intake_term.title()} {profile.context.intake_year}"
            checks.append(
                RequirementCheck(
                    requirement="Admission deadline",
                    published_value=parsed.isoformat(),
                    applicant_value=today.isoformat(),
                    status=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION,
                    is_hard_filter=False,
                    explanation=(
                        f"The page publishes {parsed.isoformat()}, which is too early to "
                        f"be the deadline for the {intake} intake. The deadline for that "
                        f"intake was not found, so this is a question for the admissions "
                        f"office rather than a reason to rule the programme out."
                    ),
                    claim_ids=[deadline_claim.source_url],
                )
            )
        else:
            passed = parsed < today
            checks.append(
                RequirementCheck(
                    requirement="Admission deadline",
                    published_value=parsed.isoformat(),
                    applicant_value=today.isoformat(),
                    status=EligibilityStatus.GAP if passed else EligibilityStatus.MET,
                    is_hard_filter=passed and _confirmed(deadline_claim),
                    explanation=(
                        f"The published deadline {parsed.isoformat()} has passed."
                        if passed
                        else f"Applications close {parsed.isoformat()}."
                    ),
                    claim_ids=[deadline_claim.source_url],
                )
            )

    # --- GPA ----------------------------------------------------------
    gpa_claim = _first(claims, ClaimType.MIN_GPA)
    gpa_value = None
    if a.gpa is not None:
        # Compare on the published scale only when we can do so honestly.
        gpa_value = a.gpa.converted_value if a.gpa.converted_value is not None else None
        if gpa_value is None and gpa_claim is not None:
            published_scale = _first(claims, ClaimType.GPA_SCALE)
            scale_max = _to_float(published_scale.normalized_value) if published_scale else None
            if scale_max and abs(scale_max - a.gpa.raw_scale_max) < 1e-9:
                gpa_value = a.gpa.raw_value
            else:
                checks.append(
                    RequirementCheck(
                        requirement="Minimum GPA",
                        published_value=gpa_claim.normalized_value,
                        applicant_value=f"{a.gpa.raw_value:g} on {a.gpa.raw_scale_label}",
                        status=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION,
                        explanation=(
                            f"The applicant's GPA is on the {a.gpa.raw_scale_label} scale and the "
                            "programme publishes a different scale. No conversion is applied "
                            "without a documented method, so this cannot be decided here."
                        ),
                        claim_ids=[gpa_claim.source_url],
                    )
                )
                gpa_claim = None  # already reported
    if gpa_claim is not None:
        checks.append(_check_numeric_minimum("Minimum GPA", gpa_claim, gpa_value))

    # --- English ------------------------------------------------------
    checks.extend(_english_checks(claims, profile))

    # --- SAT ----------------------------------------------------------
    sat_policy = _first(claims, ClaimType.SAT_POLICY)
    policy_text = str(sat_policy.normalized_value).lower() if sat_policy else ""
    test_optional = "optional" in policy_text or "blind" in policy_text or "not required" in policy_text
    sat_min = _first(claims, ClaimType.SAT_MIN_TOTAL)
    if sat_min is not None and not test_optional:
        checks.append(_check_numeric_minimum("SAT total", sat_min, _to_float(a.sat.total)))
    elif sat_policy is not None:
        checks.append(
            RequirementCheck(
                requirement="SAT policy",
                published_value=sat_policy.normalized_value,
                applicant_value=a.sat.total,
                status=EligibilityStatus.NOT_APPLICABLE if test_optional else EligibilityStatus.PENDING,
                explanation=(
                    "The programme is test-optional, so a missing SAT score is not a barrier."
                    if test_optional
                    else "An SAT policy is published but no minimum score was found."
                ),
                claim_ids=[sat_policy.source_url],
            )
        )

    # --- non-numeric prerequisites -------------------------------------
    for ctype, label in (
        (ClaimType.PORTFOLIO_REQUIRED, "Portfolio"),
        (ClaimType.INTERVIEW_REQUIRED, "Interview"),
        (ClaimType.ENTRANCE_EXAM_REQUIRED, "Entrance examination"),
        (ClaimType.CREDENTIAL_EVALUATION_REQUIRED, "Credential evaluation"),
    ):
        c = _first(claims, ctype)
        if c is not None and c.normalized_value:
            checks.append(
                RequirementCheck(
                    requirement=label,
                    published_value=True,
                    status=EligibilityStatus.PENDING,
                    explanation=f"{label} is required. This is an action to complete, not a disqualification.",
                    claim_ids=[c.source_url],
                )
            )

    subj = _first(claims, ClaimType.REQUIRED_SUBJECTS)
    if subj is not None and isinstance(subj.normalized_value, list):
        have = {s.subject.lower() for s in a.subject_grades} | {
            r.subject.lower() for r in a.curriculum_results
        }
        missing = [s for s in subj.normalized_value if str(s).lower() not in have]
        checks.append(
            RequirementCheck(
                requirement="Required subjects",
                published_value=subj.normalized_value,
                applicant_value=sorted(have),
                status=EligibilityStatus.MET if not missing else EligibilityStatus.PENDING,
                explanation=(
                    "All published subject prerequisites are present in the profile."
                    if not missing
                    else "Not listed in the profile: "
                    + ", ".join(map(str, missing))
                    + ". Add them if they were studied; otherwise this is a genuine gap."
                ),
                claim_ids=[subj.source_url],
            )
        )

    return _summarise(checks)


def _english_checks(claims: list[Claim], profile: ApplicantProfileIn) -> list[RequirementCheck]:
    out: list[RequirementCheck] = []
    a = profile.academics

    accepted = _first(claims, ClaimType.IELTS_ACCEPTED_TYPES)
    if accepted is not None and isinstance(accepted.normalized_value, list):
        allowed = {str(t).lower() for t in accepted.normalized_value}
        ok = a.ielts.test_type.lower() in allowed
        if a.ielts.overall is not None:
            out.append(
                RequirementCheck(
                    requirement="Accepted IELTS test type",
                    published_value=sorted(allowed),
                    applicant_value=a.ielts.test_type,
                    status=EligibilityStatus.MET if ok else EligibilityStatus.GAP,
                    is_hard_filter=not ok and _confirmed(accepted),
                    explanation=(
                        f"The programme accepts {', '.join(sorted(allowed))}; the applicant holds "
                        f"{a.ielts.test_type}."
                    ),
                    claim_ids=[accepted.source_url],
                )
            )

    overall = _first(claims, ClaimType.IELTS_MIN_OVERALL)
    if overall is not None:
        out.append(_check_numeric_minimum("IELTS overall", overall, a.ielts.overall))

    # Subscore minimums are evaluated per band: passing overall proves nothing here.
    sub = _first(claims, ClaimType.IELTS_MIN_SUBSCORE)
    if sub is not None:
        required = sub.normalized_value
        per_band: dict[str, float] = {}
        if isinstance(required, dict):
            per_band = {k.lower(): float(v) for k, v in required.items()}
        else:
            val = _to_float(required)
            if val is not None:
                per_band = {s: val for s in IELTS_SUBSKILLS}
        for band, minimum in per_band.items():
            got = getattr(a.ielts, band, None)
            out.append(
                _check_numeric_minimum(
                    f"IELTS {band}",
                    Claim(
                        claim_type=ClaimType.IELTS_MIN_SUBSCORE,
                        normalized_value=minimum,
                        source_url=sub.source_url,
                        accessed_at=sub.accessed_at,
                        status=sub.status,
                        confidence=sub.confidence,
                        source_specificity=sub.source_specificity,
                    ),
                    got,
                )
            )

    toefl = _first(claims, ClaimType.TOEFL_MIN_TOTAL)
    if toefl is not None and a.ielts.overall is None:
        out.append(_check_numeric_minimum("TOEFL total", toefl, _to_float(a.toefl.total)))
    return out


def _summarise(checks: list[RequirementCheck]) -> EligibilityOutcome:
    hard = [c.requirement for c in checks if c.is_hard_filter]
    if hard:
        return EligibilityOutcome(
            EligibilityStatus.GAP,
            checks,
            hard,
            [c.requirement for c in checks if c.status == EligibilityStatus.GAP],
        )
    statuses = {c.status for c in checks}
    if not checks:
        status = EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
    elif EligibilityStatus.GAP in statuses:
        status = EligibilityStatus.GAP
    elif EligibilityStatus.PENDING in statuses:
        status = EligibilityStatus.PENDING
    elif EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION in statuses and not (
        statuses & {EligibilityStatus.MET}
    ):
        status = EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
    elif EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION in statuses:
        status = EligibilityStatus.PENDING
    else:
        status = EligibilityStatus.MET
    return EligibilityOutcome(
        status,
        checks,
        [],
        [c.requirement for c in checks if c.status in {EligibilityStatus.GAP, EligibilityStatus.PENDING}],
    )


def _to_float(v: object) -> float | None:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_date(v: object) -> date | None:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %B %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except ValueError:
                continue
    return None
