"""Applicant profile.

Two rules shape this module:

1. Nothing is silently converted. A grade keeps its original value and scale;
   any derived number carries the method and the source of that method.
2. Nothing sensitive is modelled. There is no field for a passport number,
   a bank detail, a password, an OTP or a medical record, so no code path can
   accidentally persist or transmit one.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import CurriculumType, DegreeLevel, FieldStatus

Str80 = Annotated[str, Field(max_length=80)]
Str200 = Annotated[str, Field(max_length=200)]
Str2000 = Annotated[str, Field(max_length=2000)]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- A. Application context ---------------------------------------------


class ApplicationContext(Base):
    level: DegreeLevel
    intended_fields: list[Str80] = Field(default_factory=list, max_length=10)
    intake_term: Literal["fall", "spring", "summer", "winter"] = "fall"
    intake_year: int = Field(ge=2024, le=2035)
    citizenship: Str80 = Field(description="ISO-3166 name or code; drives scholarship eligibility")
    country_of_residence: Str80
    education_country: Str80
    education_system: Str80 = Field(description="e.g. 'Kazakhstan national secondary'")
    curriculum_type: CurriculumType = CurriculumType.NATIONAL
    graduation_date: date | None = None
    second_citizenship: Str80 | None = None

    @field_validator("intended_fields")
    @classmethod
    def _non_empty_fields(cls, v: list[str]) -> list[str]:
        return [x for x in v if x]


# --- B. Academic record --------------------------------------------------


class GradeValue(Base):
    """A grade that never loses its origin.

    ``converted_value`` is only ever populated together with ``method`` and
    ``method_source``; the validator refuses the combination where a converted
    number exists without a documented method.
    """

    raw_value: float
    raw_scale_max: float = Field(gt=0, description="e.g. 5.0, 4.0, 100.0")
    raw_scale_label: Str80 = Field(description="e.g. 'KZ 5-point', 'US 4.0 unweighted'")
    converted_value: float | None = None
    converted_scale_label: Str80 | None = None
    method: Str200 | None = None
    method_source: Str200 | None = None
    status: FieldStatus = FieldStatus.APPLICANT_CONFIRMED

    @model_validator(mode="after")
    def _conversion_needs_provenance(self) -> GradeValue:
        if self.converted_value is not None and not (self.method and self.method_source):
            raise ValueError(
                "converted_value requires both 'method' and 'method_source' — "
                "silent grade conversion is not permitted"
            )
        if self.raw_value > self.raw_scale_max:
            raise ValueError("raw_value exceeds raw_scale_max")
        return self


class SubjectGrade(Base):
    subject: Str80
    grade: GradeValue


class TestDate(Base):
    taken_on: date | None = None
    planned_retake_on: date | None = None


class SatScore(Base):
    total: int | None = Field(default=None, ge=400, le=1600)
    math: int | None = Field(default=None, ge=200, le=800)
    reading_writing: int | None = Field(default=None, ge=200, le=800)
    dates: TestDate = Field(default_factory=TestDate)
    status: FieldStatus = FieldStatus.APPLICANT_CONFIRMED


class ActScore(Base):
    composite: int | None = Field(default=None, ge=1, le=36)
    english: int | None = Field(default=None, ge=1, le=36)
    math: int | None = Field(default=None, ge=1, le=36)
    reading: int | None = Field(default=None, ge=1, le=36)
    science: int | None = Field(default=None, ge=1, le=36)
    dates: TestDate = Field(default_factory=TestDate)
    status: FieldStatus = FieldStatus.APPLICANT_CONFIRMED


class IeltsScore(Base):
    """IELTS with every subscore kept separately.

    Subscores matter: a university may publish an overall 6.5 minimum *and* a
    per-band 6.0 minimum, and an applicant can pass one while failing the other.
    """

    overall: float | None = Field(default=None, ge=0, le=9)
    listening: float | None = Field(default=None, ge=0, le=9)
    reading: float | None = Field(default=None, ge=0, le=9)
    writing: float | None = Field(default=None, ge=0, le=9)
    speaking: float | None = Field(default=None, ge=0, le=9)
    test_type: Literal["academic", "general_training", "ukvi_academic", "one_skill_retake"] = (
        "academic"
    )
    dates: TestDate = Field(default_factory=TestDate)
    status: FieldStatus = FieldStatus.APPLICANT_CONFIRMED

    @field_validator("overall", "listening", "reading", "writing", "speaking")
    @classmethod
    def _half_bands(cls, v: float | None) -> float | None:
        if v is not None and (v * 2) % 1 != 0:
            raise ValueError("IELTS bands are reported in halves (e.g. 6.0, 6.5)")
        return v


class ToeflScore(Base):
    total: int | None = Field(default=None, ge=0, le=120)
    reading: int | None = Field(default=None, ge=0, le=30)
    listening: int | None = Field(default=None, ge=0, le=30)
    speaking: int | None = Field(default=None, ge=0, le=30)
    writing: int | None = Field(default=None, ge=0, le=30)
    dates: TestDate = Field(default_factory=TestDate)
    status: FieldStatus = FieldStatus.APPLICANT_CONFIRMED


class OtherLanguageTest(Base):
    name: Str80
    score: float
    max_score: float | None = None
    dates: TestDate = Field(default_factory=TestDate)


class CurriculumResult(Base):
    """AP / IB / A-Level and similar subject results."""

    framework: Literal["AP", "IB", "A-Level", "AS-Level", "other"]
    subject: Str80
    result: Str80 = Field(description="Raw as published, e.g. '5', 'A*', '7'")
    year: int | None = Field(default=None, ge=2015, le=2035)
    predicted: bool = False


class AcademicRecord(Base):
    gpa: GradeValue | None = None
    subject_grades: list[SubjectGrade] = Field(default_factory=list, max_length=40)
    class_rank: int | None = Field(default=None, ge=1)
    class_size: int | None = Field(default=None, ge=1)
    sat: SatScore = Field(default_factory=SatScore)
    act: ActScore = Field(default_factory=ActScore)
    ielts: IeltsScore = Field(default_factory=IeltsScore)
    toefl: ToeflScore = Field(default_factory=ToeflScore)
    duolingo: OtherLanguageTest | None = None
    other_tests: list[OtherLanguageTest] = Field(default_factory=list, max_length=10)
    curriculum_results: list[CurriculumResult] = Field(default_factory=list, max_length=30)
    planned_retakes: list[Str200] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _rank_within_size(self) -> AcademicRecord:
        if self.class_rank and self.class_size and self.class_rank > self.class_size:
            raise ValueError("class_rank cannot exceed class_size")
        return self


# --- C. Activities and achievements --------------------------------------


class Activity(Base):
    name: Str200
    category: Str80 = Field(description="e.g. research, community, athletics, work, arts")
    role: Str80
    duration_months: int | None = Field(default=None, ge=0, le=240)
    hours_per_week: float | None = Field(default=None, ge=0, le=80)
    weeks_per_year: int | None = Field(default=None, ge=0, le=52)
    responsibility_level: Literal[
        "participant", "contributor", "coordinator", "leader", "founder"
    ] = "participant"
    measurable_outcome: Str2000 | None = None
    impact_on_others: Str2000 | None = None
    evidence_links: list[Str200] = Field(default_factory=list, max_length=5)

    @property
    def annual_hours(self) -> float | None:
        if self.hours_per_week is None or self.weeks_per_year is None:
            return None
        return self.hours_per_week * self.weeks_per_year


class Achievement(Base):
    name: Str200
    level: Literal["school", "city", "regional", "national", "international"]
    year: int = Field(ge=2010, le=2035)
    placement: Str80 | None = None
    selection_criterion: Str2000 | None = None
    evidence_links: list[Str200] = Field(default_factory=list, max_length=5)


# --- D. Preferences ------------------------------------------------------


class Preferences(Base):
    preferred_countries: list[Str80] = Field(default_factory=list, max_length=25)
    excluded_countries: list[Str80] = Field(default_factory=list, max_length=25)
    city_size: Literal["any", "small", "medium", "large", "metropolis"] = "any"
    climate: Literal["any", "cold", "temperate", "warm", "mediterranean"] = "any"
    university_size: Literal["any", "small", "medium", "large"] = "any"
    campus_type: Literal["any", "campus", "urban", "suburban"] = "any"
    acceptable_workload: Literal["any", "moderate", "demanding", "very_demanding"] = "any"
    target_ranking_band: Literal["any", "top_50", "top_100", "top_300", "top_500"] = "any"
    research_interests: list[Str80] = Field(default_factory=list, max_length=10)
    values_internships: bool = True
    values_coop: bool = False
    needs_work_during_study: bool = False
    needs_post_study_work: bool = False
    safety_priority: Literal["low", "medium", "high"] = "medium"
    diversity_priority: Literal["low", "medium", "high"] = "medium"
    housing_guarantee_priority: Literal["low", "medium", "high"] = "medium"

    @model_validator(mode="after")
    def _no_country_in_both_lists(self) -> Preferences:
        overlap = {c.lower() for c in self.preferred_countries} & {
            c.lower() for c in self.excluded_countries
        }
        if overlap:
            raise ValueError(f"country listed as both preferred and excluded: {sorted(overlap)}")
        return self


# --- E. Funding ----------------------------------------------------------


class FundingNeeds(Base):
    requires_full_ride: bool = False
    accepts_full_tuition: bool = True
    accepts_partial: bool = True
    max_annual_budget: float | None = Field(default=None, ge=0)
    max_family_contribution: float | None = Field(default=None, ge=0)
    max_acceptable_gap: float | None = Field(
        default=None, ge=0, description="Largest annual shortfall the family can absorb"
    )
    budget_currency: Str80 = "USD"
    willing_to_submit_need_documents: bool = True
    must_cover_housing: bool = True
    must_cover_meals: bool = True
    must_cover_health_insurance: bool = False
    must_cover_books: bool = False
    must_cover_travel: bool = False
    funding_criticality: Literal["nice_to_have", "important", "decisive"] = "decisive"


class ScoringWeights(Base):
    """User-tunable weights for the soft preference score.

    Exposed through the API so the numeric score is never a black box.
    """

    academic_fit: float = Field(default=1.0, ge=0, le=3)
    funding_fit: float = Field(default=1.5, ge=0, le=3)
    extracurricular_alignment: float = Field(default=0.6, ge=0, le=3)
    program_quality: float = Field(default=0.8, ge=0, le=3)
    country_preference: float = Field(default=1.0, ge=0, le=3)
    city_fit: float = Field(default=0.4, ge=0, le=3)
    climate_fit: float = Field(default=0.3, ge=0, le=3)
    workload_fit: float = Field(default=0.3, ge=0, le=3)
    #: Soft, like the other location fits: the registry knows the size and the
    #: campus shape, so a stated preference for one is worth something - but
    #: not enough to outrank a funded place.
    university_size_fit: float = Field(default=0.3, ge=0, le=3)
    campus_fit: float = Field(default=0.3, ge=0, le=3)
    career_outcomes: float = Field(default=0.7, ge=0, le=3)
    post_study_work: float = Field(default=0.5, ge=0, le=3)


# --- Root ----------------------------------------------------------------


class ApplicantProfileIn(Base):
    """Inbound profile. ``display_name`` is a local label, never sent outward."""

    display_name: Str80 = Field(
        default="Applicant", description="Local label only; never leaves this machine"
    )
    context: ApplicationContext
    academics: AcademicRecord = Field(default_factory=AcademicRecord)
    activities: list[Activity] = Field(default_factory=list, max_length=30)
    achievements: list[Achievement] = Field(default_factory=list, max_length=30)
    preferences: Preferences = Field(default_factory=Preferences)
    funding: FundingNeeds = Field(default_factory=FundingNeeds)
    weights: ScoringWeights = Field(default_factory=ScoringWeights)


class ApplicantProfile(ApplicantProfileIn):
    id: str
    created_at: str
    updated_at: str


class ProfileGap(Base):
    """One missing or weak field, with its concrete consequence."""

    field_path: Str200
    status: FieldStatus
    severity: Literal["blocking", "high", "medium", "low"]
    impact: Str2000 = Field(description="What this specific absence does to the result")
    suggested_action: Str2000 | None = None


class ProfileValidationReport(Base):
    gaps: list[ProfileGap]
    can_proceed: bool
    blocking_count: int
    summary: Str2000
