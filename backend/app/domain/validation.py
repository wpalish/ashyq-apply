"""Profile completeness: what each absence actually costs.

The report never blocks research over an optional field. It explains, per gap,
which part of the result will be weaker — because "fill in everything" is
advice a user cannot prioritise.
"""

from __future__ import annotations

from app.domain.enums import FieldStatus
from app.schemas.profile import ApplicantProfileIn, ProfileGap, ProfileValidationReport


def validate_profile(profile: ApplicantProfileIn) -> ProfileValidationReport:
    gaps: list[ProfileGap] = []
    a = profile.academics
    ctx = profile.context

    if not ctx.intended_fields:
        gaps.append(
            ProfileGap(
                field_path="context.intended_fields",
                status=FieldStatus.MISSING,
                severity="blocking",
                impact=(
                    "Without at least one field of study there is nothing to match a programme "
                    "against; discovery cannot select programmes."
                ),
                suggested_action="Add one to three subject areas, e.g. 'Computer Science'.",
            )
        )

    if a.gpa is None:
        gaps.append(
            ProfileGap(
                field_path="academics.gpa",
                status=FieldStatus.MISSING,
                severity="high",
                impact=(
                    "Any published minimum GPA will be reported as PENDING rather than met, and "
                    "merit scholarships gated on GPA cannot be assessed."
                ),
                suggested_action="Enter the GPA with its original scale; no conversion is applied.",
            )
        )
    elif a.gpa.converted_value is None and a.gpa.raw_scale_max not in (4.0, 4.3):
        gaps.append(
            ProfileGap(
                field_path="academics.gpa.converted_value",
                status=FieldStatus.UNVERIFIED,
                severity="medium",
                impact=(
                    f"The GPA is on the {a.gpa.raw_scale_label} scale. Programmes publishing a "
                    "4.0-scale minimum will be reported as NEEDS_OFFICIAL_CLARIFICATION instead "
                    "of being decided."
                ),
                suggested_action=(
                    "Accept a documented conversion in the profile screen, or obtain a credential "
                    "evaluation (WES/ECE) for US applications."
                ),
            )
        )

    has_english = any(
        [
            a.ielts.overall is not None,
            a.toefl.total is not None,
            a.duolingo is not None,
            bool(a.other_tests),
        ]
    )
    if not has_english:
        gaps.append(
            ProfileGap(
                field_path="academics.ielts / academics.toefl",
                status=FieldStatus.MISSING,
                severity="high",
                impact=(
                    "English-language minimums are a hard requirement almost everywhere. Every "
                    "programme will report PENDING on language, and no programme can reach "
                    "eligibility MET."
                ),
                suggested_action="Add IELTS or TOEFL results, including every subscore.",
            )
        )
    elif a.ielts.overall is not None and any(
        getattr(a.ielts, s) is None for s in ("listening", "reading", "writing", "speaking")
    ):
        gaps.append(
            ProfileGap(
                field_path="academics.ielts subscores",
                status=FieldStatus.MISSING,
                severity="high",
                impact=(
                    "Many programmes publish a per-section minimum in addition to the overall "
                    "band. Without subscores those checks stay PENDING even when the overall "
                    "band clears."
                ),
                suggested_action="Enter all four IELTS section scores from the test report form.",
            )
        )

    if ctx.level in ("bachelor", "foundation") and not a.sat.total and not a.act.composite:
        gaps.append(
            ProfileGap(
                field_path="academics.sat / academics.act",
                status=FieldStatus.MISSING,
                severity="low",
                impact=(
                    "Test-optional programmes are unaffected. Programmes that publish an SAT/ACT "
                    "minimum will report PENDING, and some US merit scholarships are score-gated."
                ),
                suggested_action="Add SAT or ACT scores if taken, or note a planned test date.",
            )
        )

    if not profile.activities and not profile.achievements:
        gaps.append(
            ProfileGap(
                field_path="activities / achievements",
                status=FieldStatus.MISSING,
                severity="medium",
                impact=(
                    "Admissions fit cannot rise above PLAUSIBLE_FIT, competitive scholarships "
                    "cannot be assessed, and the preference score takes a missing-data penalty."
                ),
                suggested_action="Add activities with hours, role and a measurable outcome.",
            )
        )

    if not profile.preferences.preferred_countries:
        gaps.append(
            ProfileGap(
                field_path="preferences.preferred_countries",
                status=FieldStatus.MISSING,
                severity="medium",
                impact=(
                    "Discovery will search every supported country, producing a broader and less "
                    "relevant candidate list."
                ),
                suggested_action="Name the countries you would actually move to.",
            )
        )

    if profile.funding.max_annual_budget is None and profile.funding.max_acceptable_gap is None:
        gaps.append(
            ProfileGap(
                field_path="funding.max_annual_budget",
                status=FieldStatus.MISSING,
                severity="medium",
                impact=(
                    "The remaining annual cost is still computed, but it cannot be compared "
                    "against what the family can pay, so affordability scores neutrally."
                ),
                suggested_action="State the maximum you can pay per year, in any currency.",
            )
        )

    if ctx.graduation_date is None:
        gaps.append(
            ProfileGap(
                field_path="context.graduation_date",
                status=FieldStatus.MISSING,
                severity="low",
                impact="Intake eligibility cannot be cross-checked against your completion date.",
                suggested_action="Add the month you finish (or finished) school.",
            )
        )

    blocking = sum(1 for g in gaps if g.severity == "blocking")
    high = sum(1 for g in gaps if g.severity == "high")
    return ProfileValidationReport(
        gaps=gaps,
        can_proceed=blocking == 0,
        blocking_count=blocking,
        summary=(
            f"{len(gaps)} gaps found: {blocking} blocking, {high} high-impact. "
            + (
                "Research can run; results affected by the gaps above will be marked."
                if blocking == 0
                else "Research cannot start until the blocking items are filled in."
            )
        ),
    )
