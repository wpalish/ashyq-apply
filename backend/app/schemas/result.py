"""The result row and everything hanging off it."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AdmissionsFit,
    ApplicationMode,
    CostCategory,
    DegreeLevel,
    DocumentOwner,
    DocumentPurpose,
    EligibilityStatus,
    FundingClassification,
    FundingFit,
    ScholarshipType,
    UserDecision,
)
from app.schemas.claim import ClaimOut, Conflict, UnresolvedQuestion
from app.schemas.money import Money


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


#: Whether an award covers a cost category. "unknown" is a first-class answer.
Coverage = Literal["yes", "no", "partial", "unknown"]


class RankingEntry(Base):
    source: str
    year: int
    position: str = Field(description="Kept as published: '=71' and '301-350' are real values")
    url: str | None = None


class RequirementCheck(Base):
    """One published requirement compared against one applicant value."""

    requirement: str
    published_value: Any = None
    applicant_value: Any = None
    status: EligibilityStatus
    is_hard_filter: bool = False
    explanation: str = ""
    claim_ids: list[str] = Field(default_factory=list)


class CoverageBreakdown(Base):
    """Per-cost-category truth table behind the funding classification."""

    category: CostCategory
    covered: Coverage
    amount: Money | None = None
    claim_ids: list[str] = Field(default_factory=list)


class Scholarship(Base):
    id: str
    name: str
    scholarship_type: ScholarshipType = ScholarshipType.UNKNOWN
    classification: FundingClassification = FundingClassification.UNKNOWN
    classification_reason: str = ""
    amount: Money | None = None
    amount_is_percentage_of_tuition: float | None = None
    coverage: list[CoverageBreakdown] = Field(default_factory=list)
    international_eligible: Literal["yes", "no", "unknown"] = "unknown"
    citizenship_restrictions: list[str] = Field(default_factory=list)
    program_restrictions: list[str] = Field(default_factory=list)
    application_mode: ApplicationMode = ApplicationMode.UNKNOWN
    requires_extra_essays: bool | None = None
    deadline: date | None = None
    deadline_timezone: str | None = None
    deadline_raw: str | None = None
    renewable: bool | None = None
    duration_years: float | None = None
    renewal_requirements: list[str] = Field(default_factory=list)
    min_test_scores: dict[str, float] = Field(default_factory=dict)
    stackable: Literal["yes", "no", "unknown"] = "unknown"
    published_count: int | None = Field(default=None, description="Only set when officially published")
    available_this_intake: Literal["yes", "no", "unknown"] = "unknown"
    eligibility_checks: list[RequirementCheck] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    last_verified: datetime | None = None


class CostBreakdown(Base):
    items: dict[CostCategory, Money] = Field(default_factory=dict)
    total: Money | None = None
    academic_year: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    is_range: bool = False


class FundingGap(Base):
    """Result of the cost-minus-aid arithmetic, including refusals to compute."""

    computable: bool
    gap: Money | None = None
    gap_low: float | None = None
    gap_high: float | None = None
    total_cost: Money | None = None
    confirmed_aid: Money | None = None
    stackable_aid: Money | None = None
    reason: str = ""
    year_mismatch: bool = False
    currency_mismatch: bool = False
    category_mismatch: bool = False
    warnings: list[str] = Field(default_factory=list)


class ScoreComponent(Base):
    name: str
    raw: float = Field(ge=0.0, le=1.0)
    weight: float
    weighted: float
    explanation: str
    data_present: bool = True


class ExplainableScore(Base):
    """A weighted sum that is explicitly *not* a probability.

    ``disclaimer`` travels with the number everywhere it is rendered.
    """

    total: float
    max_possible: float
    components: list[ScoreComponent]
    missing_data_penalty: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "A preference-match score, not a probability of admission or of receiving funding."
    )


class DocumentItem(Base):
    name: str
    purpose: DocumentPurpose
    owner: DocumentOwner
    required: bool = True
    format_notes: str = ""
    max_pages: int | None = None
    max_file_size_mb: float | None = None
    naming_convention: str | None = None
    needs_translation: bool = False
    needs_notarization: bool = False
    needs_apostille: bool = False
    needs_credential_evaluation: bool = False
    word_limit: int | None = None
    character_limit: int | None = None
    prompt_text: str | None = None
    deadline: date | None = None
    deadline_timezone: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    lead_time_days: int | None = None
    source_url: str | None = None
    claim_ids: list[str] = Field(default_factory=list)


class DocumentChecklist(Base):
    result_id: str
    university: str
    program: str
    admission_documents: list[DocumentItem] = Field(default_factory=list)
    scholarship_documents: list[DocumentItem] = Field(default_factory=list)
    applicant_actions: list[DocumentItem] = Field(default_factory=list)
    school_actions: list[DocumentItem] = Field(default_factory=list)
    recommender_actions: list[DocumentItem] = Field(default_factory=list)
    certification_actions: list[DocumentItem] = Field(default_factory=list)
    ordered_steps: list[str] = Field(default_factory=list)
    unresolved: list[UnresolvedQuestion] = Field(default_factory=list)
    generated_at: datetime | None = None
    completeness: Literal["official", "partial", "unavailable"] = "partial"


class ProgramResult(Base):
    """One row of the shortlist table."""

    id: str
    run_id: str

    university: str
    university_id: str
    country: str
    city: str
    program: str
    program_url: str | None = None
    degree: DegreeLevel
    intake: str
    rankings: list[RankingEntry] = Field(default_factory=list)

    # Three independent axes — never collapsed into one verdict.
    eligibility: EligibilityStatus = EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
    admissions_fit: AdmissionsFit = AdmissionsFit.INSUFFICIENT_DATA
    funding_fit: FundingFit = FundingFit.UNKNOWN
    best_funding_classification: FundingClassification = FundingClassification.UNKNOWN

    requirement_checks: list[RequirementCheck] = Field(default_factory=list)
    missing_prerequisites: list[str] = Field(default_factory=list)
    hard_filter_failures: list[str] = Field(default_factory=list)

    scholarships: list[Scholarship] = Field(default_factory=list)
    costs: CostBreakdown = Field(default_factory=CostBreakdown)
    funding_gap: FundingGap | None = None

    preference_score: ExplainableScore | None = None

    admission_deadline: date | None = None
    admission_deadline_timezone: str | None = None
    admission_deadline_raw: str | None = None
    deadline_passed: bool = False

    climate_fit: str = "unknown"
    city_fit: str = "unknown"
    workload_fit: str = "unknown"
    career_notes: str = ""
    post_study_work: str = ""
    work_during_study: str = ""

    conflicts: list[Conflict] = Field(default_factory=list)
    unresolved: list[UnresolvedQuestion] = Field(default_factory=list)
    claims: list[ClaimOut] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    last_verified: datetime | None = None
    verification_completeness: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Share of decision-grade fields backed by an official claim"
    )

    user_decision: UserDecision = UserDecision.UNDECIDED
    user_decision_reason: str = ""
    user_notes: str = ""
    decided_at: datetime | None = None

    checklist: DocumentChecklist | None = None


class DecisionIn(Base):
    decision: UserDecision
    reason: str = ""
    notes: str = ""
