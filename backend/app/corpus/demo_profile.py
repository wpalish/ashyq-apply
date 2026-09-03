"""The synthetic applicant used for demos and tests.

Entirely invented. The scores are chosen to sit on the interesting boundaries:
the IELTS writing band is below several published per-section minimums, the GPA
is on a 5-point scale that no US programme publishes, and the budget is far
below every unfunded cost of attendance in the corpus.
"""

from __future__ import annotations

from app.schemas.profile import (
    AcademicRecord,
    Achievement,
    Activity,
    ApplicantProfileIn,
    ApplicationContext,
    CurriculumResult,
    FundingNeeds,
    GradeValue,
    IeltsScore,
    Preferences,
    SatScore,
    SubjectGrade,
    TestDate,
)

DEMO_PROFILE = ApplicantProfileIn(
    display_name="Demo Applicant (synthetic)",
    context=ApplicationContext(
        level="bachelor",
        intended_fields=["computer science"],
        intake_term="fall",
        intake_year=2027,
        citizenship="Kazakhstan",
        country_of_residence="Kazakhstan",
        education_country="Kazakhstan",
        education_system="Kazakhstan national secondary (attestat)",
        curriculum_type="national",
        graduation_date="2027-05-25",
    ),
    academics=AcademicRecord(
        gpa=GradeValue(
            raw_value=4.8,
            raw_scale_max=5.0,
            raw_scale_label="KZ 5-point",
            status="applicant_confirmed",
        ),
        subject_grades=[
            SubjectGrade(
                subject="mathematics",
                grade=GradeValue(raw_value=5.0, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            ),
            SubjectGrade(
                subject="physics",
                grade=GradeValue(raw_value=4.7, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            ),
            SubjectGrade(
                subject="informatics",
                grade=GradeValue(raw_value=5.0, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            ),
        ],
        class_rank=3,
        class_size=112,
        # Overall clears 6.5 but writing is 6.0 — below several per-band minimums.
        ielts=IeltsScore(
            overall=7.0,
            listening=7.5,
            reading=7.5,
            writing=6.0,
            speaking=7.0,
            test_type="academic",
            dates=TestDate(taken_on="2026-04-18"),
        ),
        sat=SatScore(
            total=1400,
            math=760,
            reading_writing=640,
            dates=TestDate(taken_on="2026-05-02", planned_retake_on="2026-10-03"),
        ),
        curriculum_results=[
            CurriculumResult(framework="other", subject="mathematics", result="5", year=2026),
            CurriculumResult(framework="other", subject="informatics", result="5", year=2026),
        ],
        planned_retakes=[
            "SAT on 2026-10-03 targeting 1500",
            "IELTS writing retake if a 6.5 band is needed",
        ],
    ),
    activities=[
        Activity(
            name="Regional Informatics Olympiad team",
            category="academic",
            role="team captain",
            duration_months=24,
            hours_per_week=8,
            weeks_per_year=36,
            responsibility_level="leader",
            measurable_outcome="Led a four-person team to 2nd place at the national round in 2026.",
            impact_on_others="Ran weekly training for 15 younger students.",
        ),
        Activity(
            name="Volunteer coding club at School 42, Astana",
            category="community",
            role="founder and instructor",
            duration_months=18,
            hours_per_week=4,
            weeks_per_year=40,
            responsibility_level="founder",
            measurable_outcome="Taught Python to 60 students across three cohorts.",
            impact_on_others="Six participants went on to enter regional competitions.",
        ),
        Activity(
            name="Part-time junior web developer",
            category="work",
            role="contractor",
            duration_months=8,
            hours_per_week=10,
            weeks_per_year=44,
            responsibility_level="contributor",
            measurable_outcome="Shipped two client sites; maintained them for six months.",
        ),
    ],
    achievements=[
        Achievement(
            name="National Informatics Olympiad",
            level="national",
            year=2026,
            placement="2nd place (team)",
            selection_criterion="Top 40 of 900 regional qualifiers.",
        ),
        Achievement(
            name="Republic Mathematics Tournament",
            level="national",
            year=2025,
            placement="Honourable mention",
        ),
        Achievement(name="City science fair", level="city", year=2024, placement="1st place"),
    ],
    preferences=Preferences(
        preferred_countries=["Netherlands", "Germany", "Canada", "Finland", "Belgium"],
        excluded_countries=["Russia"],
        city_size="medium",
        climate="temperate",
        university_size="large",
        campus_type="campus",
        acceptable_workload="demanding",
        target_ranking_band="top_300",
        research_interests=["machine learning", "distributed systems"],
        values_internships=True,
        needs_post_study_work=True,
        needs_work_during_study=True,
        safety_priority="high",
        housing_guarantee_priority="high",
    ),
    funding=FundingNeeds(
        requires_full_ride=False,
        accepts_full_tuition=True,
        accepts_partial=True,
        max_annual_budget=6000,
        max_family_contribution=5000,
        max_acceptable_gap=6000,
        budget_currency="USD",
        willing_to_submit_need_documents=True,
        must_cover_housing=True,
        must_cover_meals=True,
        funding_criticality="decisive",
    ),
)
