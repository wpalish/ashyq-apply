"""Controlled vocabularies.

Every status the product can show a user is defined here exactly once. The
product's core promise is that it never converts an unknown into a guess, so
each vocabulary carries an explicit "we don't know" member.
"""

from __future__ import annotations

from enum import StrEnum


class DegreeLevel(StrEnum):
    FOUNDATION = "foundation"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


class CurriculumType(StrEnum):
    NATIONAL = "national"
    IB = "ib"
    A_LEVEL = "a_level"
    AP = "ap"
    US_HIGH_SCHOOL = "us_high_school"
    OTHER = "other"


# --- Data quality of a single profile field ------------------------------


class FieldStatus(StrEnum):
    """How much we trust one value in the applicant's own profile."""

    VERIFIED = "verified"  # backed by an uploaded/official artefact
    APPLICANT_CONFIRMED = "applicant_confirmed"  # user asserted it explicitly
    DOCUMENT_SUPPORTED = "document_supported"  # user attached supporting evidence
    UNVERIFIED = "unverified"  # inferred or defaulted
    MISSING = "missing"
    CONFLICTING = "conflicting"


# --- Provenance of a scraped fact ---------------------------------------


class ClaimStatus(StrEnum):
    VERIFIED_CURRENT = "VERIFIED_CURRENT"
    POSSIBLY_STALE = "POSSIBLY_STALE"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    NOT_FOUND = "NOT_FOUND"
    NEEDS_OFFICIAL_CLARIFICATION = "NEEDS_OFFICIAL_CLARIFICATION"


class SourceSpecificity(StrEnum):
    """How close the page is to the exact question being asked.

    Ordered: a programme+intake page beats a generic university page, and any
    official page beats an aggregator. Conflict resolution uses this order.
    """

    PROGRAM_INTAKE = "program_intake"  # 1 - the exact programme, this cycle
    PROGRAM = "program"  # 2 - the programme, cycle unstated
    UNIVERSITY_ADMISSIONS = "university_admissions"  # 3
    APPLICATION_PORTAL = "application_portal"  # 4
    SCHOLARSHIP_ADMINISTRATOR = "scholarship_administrator"  # 5
    GOVERNMENT = "government"  # 6
    ADMISSIONS_OFFICE_REPLY = "admissions_office_reply"  # 7 - written reply
    AGGREGATOR = "aggregator"  # 8 - discovery only, never proof
    UNKNOWN = "unknown"


SPECIFICITY_RANK: dict[SourceSpecificity, int] = {
    SourceSpecificity.PROGRAM_INTAKE: 1,
    SourceSpecificity.PROGRAM: 2,
    SourceSpecificity.UNIVERSITY_ADMISSIONS: 3,
    SourceSpecificity.APPLICATION_PORTAL: 4,
    SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR: 5,
    SourceSpecificity.GOVERNMENT: 6,
    SourceSpecificity.ADMISSIONS_OFFICE_REPLY: 7,
    SourceSpecificity.AGGREGATOR: 8,
    SourceSpecificity.UNKNOWN: 9,
}

#: Specificity levels that may never, on their own, support a decision-grade
#: claim (requirements, deadlines, cost, eligibility, award size).
DISCOVERY_ONLY_SPECIFICITY = frozenset({SourceSpecificity.AGGREGATOR, SourceSpecificity.UNKNOWN})


class ClaimType(StrEnum):
    MIN_GPA = "min_gpa"
    GPA_SCALE = "gpa_scale"
    REQUIRED_SUBJECTS = "required_subjects"
    SAT_POLICY = "sat_policy"
    SAT_MIN_TOTAL = "sat_min_total"
    SUPERSCORE_POLICY = "superscore_policy"
    IELTS_MIN_OVERALL = "ielts_min_overall"
    IELTS_MIN_SUBSCORE = "ielts_min_subscore"
    IELTS_ACCEPTED_TYPES = "ielts_accepted_types"
    TOEFL_MIN_TOTAL = "toefl_min_total"
    DUOLINGO_MIN = "duolingo_min"
    TEST_VALIDITY_MONTHS = "test_validity_months"
    COUNTRY_SPECIFIC_REQUIREMENT = "country_specific_requirement"
    PORTFOLIO_REQUIRED = "portfolio_required"
    INTERVIEW_REQUIRED = "interview_required"
    ENTRANCE_EXAM_REQUIRED = "entrance_exam_required"
    CREDENTIAL_EVALUATION_REQUIRED = "credential_evaluation_required"
    APPLICATION_FEE = "application_fee"
    FEE_WAIVER_AVAILABLE = "fee_waiver_available"
    ADMISSION_DEADLINE = "admission_deadline"
    INTAKE_OPEN = "intake_open"
    PROGRAM_EXISTS = "program_exists"

    SCHOLARSHIP_EXISTS = "scholarship_exists"
    SCHOLARSHIP_AMOUNT = "scholarship_amount"
    SCHOLARSHIP_COVERAGE = "scholarship_coverage"
    SCHOLARSHIP_INTERNATIONAL_ELIGIBLE = "scholarship_international_eligible"
    SCHOLARSHIP_CITIZENSHIP_RESTRICTION = "scholarship_citizenship_restriction"
    SCHOLARSHIP_PROGRAM_RESTRICTION = "scholarship_program_restriction"
    SCHOLARSHIP_APPLICATION_MODE = "scholarship_application_mode"
    SCHOLARSHIP_DEADLINE = "scholarship_deadline"
    SCHOLARSHIP_RENEWABLE = "scholarship_renewable"
    SCHOLARSHIP_RENEWAL_REQUIREMENT = "scholarship_renewal_requirement"
    SCHOLARSHIP_MIN_TEST_SCORE = "scholarship_min_test_score"
    SCHOLARSHIP_STACKABLE = "scholarship_stackable"
    SCHOLARSHIP_COUNT = "scholarship_count"
    SCHOLARSHIP_DURATION_YEARS = "scholarship_duration_years"

    TUITION = "tuition"
    MANDATORY_FEES = "mandatory_fees"
    HOUSING_COST = "housing_cost"
    MEALS_COST = "meals_cost"
    HEALTH_INSURANCE_COST = "health_insurance_cost"
    BOOKS_COST = "books_cost"
    TRAVEL_COST = "travel_cost"
    PERSONAL_EXPENSES_COST = "personal_expenses_cost"
    TOTAL_COST_OF_ATTENDANCE = "total_cost_of_attendance"

    REQUIRED_DOCUMENT = "required_document"
    ESSAY_PROMPT = "essay_prompt"
    RECOMMENDATION_REQUIREMENT = "recommendation_requirement"
    POST_STUDY_WORK = "post_study_work"
    WORK_DURING_STUDY = "work_during_study"
    RANKING_POSITION = "ranking_position"


#: Claim types where an aggregator source can never be the final word.
DECISION_GRADE_CLAIMS = frozenset(
    {
        ClaimType.MIN_GPA,
        ClaimType.SAT_MIN_TOTAL,
        ClaimType.IELTS_MIN_OVERALL,
        ClaimType.IELTS_MIN_SUBSCORE,
        ClaimType.TOEFL_MIN_TOTAL,
        ClaimType.DUOLINGO_MIN,
        ClaimType.ADMISSION_DEADLINE,
        ClaimType.SCHOLARSHIP_DEADLINE,
        ClaimType.SCHOLARSHIP_AMOUNT,
        ClaimType.SCHOLARSHIP_COVERAGE,
        ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE,
        ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION,
        ClaimType.TUITION,
        ClaimType.TOTAL_COST_OF_ATTENDANCE,
        ClaimType.HOUSING_COST,
        ClaimType.INTAKE_OPEN,
    }
)


# --- Assessment outcomes: three independent axes -------------------------


class EligibilityStatus(StrEnum):
    MET = "MET"
    PENDING = "PENDING"
    GAP = "GAP"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_OFFICIAL_CLARIFICATION = "NEEDS_OFFICIAL_CLARIFICATION"


class AdmissionsFit(StrEnum):
    STRONGER_FIT = "STRONGER_FIT"
    PLAUSIBLE_FIT = "PLAUSIBLE_FIT"
    AMBITIOUS = "AMBITIOUS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FundingFit(StrEnum):
    CONFIRMED_OPPORTUNITY = "CONFIRMED_OPPORTUNITY"
    COMPETITIVE_OPPORTUNITY = "COMPETITIVE_OPPORTUNITY"
    LIMITED_OPPORTUNITY = "LIMITED_OPPORTUNITY"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNKNOWN = "UNKNOWN"


class FundingClassification(StrEnum):
    FULL_RIDE_CONFIRMED = "FULL_RIDE_CONFIRMED"
    FULL_TUITION = "FULL_TUITION"
    LARGE_GRANT = "LARGE_GRANT"
    PARTIAL = "PARTIAL"
    NEED_BASED_POSSIBLE = "NEED_BASED_POSSIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNKNOWN = "UNKNOWN"


class CostCategory(StrEnum):
    TUITION = "tuition"
    MANDATORY_FEES = "mandatory_fees"
    HOUSING = "housing"
    MEALS = "meals"
    HEALTH_INSURANCE = "health_insurance"
    BOOKS = "books"
    TRAVEL = "travel"
    VISA = "visa"
    PERSONAL = "personal"


#: The four categories that must all be confirmed-covered for FULL_RIDE_CONFIRMED.
FULL_RIDE_REQUIRED = (
    CostCategory.TUITION,
    CostCategory.MANDATORY_FEES,
    CostCategory.HOUSING,
    CostCategory.MEALS,
)


class ScholarshipType(StrEnum):
    MERIT = "merit"
    NEED_BASED = "need_based"
    AUTOMATIC = "automatic"
    COMPETITIVE = "competitive"
    DEPARTMENTAL = "departmental"
    HONORS = "honors"
    GOVERNMENT = "government"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ApplicationMode(StrEnum):
    AUTOMATIC = "automatic"  # considered on the admission application
    SEPARATE = "separate"  # a distinct scholarship application
    NOMINATION = "nomination"  # by invitation / departmental nomination
    UNKNOWN = "unknown"


class UserDecision(StrEnum):
    UNDECIDED = "undecided"
    APPROVED = "approved"
    MAYBE = "maybe"
    REJECTED = "rejected"


class DocumentOwner(StrEnum):
    APPLICANT = "applicant"
    SCHOOL = "school"
    RECOMMENDER = "recommender"
    THIRD_PARTY = "third_party"  # e.g. WES, IELTS test centre


class DocumentPurpose(StrEnum):
    ADMISSION = "admission"
    SCHOLARSHIP = "scholarship"
    BOTH = "both"


class PipelineStage(StrEnum):
    QUEUED = "queued"
    PROFILE_VALIDATION = "profile_validation"
    CANDIDATE_DISCOVERY = "candidate_discovery"
    PROGRAM_VERIFICATION = "program_verification"
    FUNDING_DISCOVERY = "funding_discovery"
    ASSESSMENT = "assessment"
    AWAITING_USER_DECISION = "awaiting_user_decision"
    DOCUMENT_COLLECTION = "document_collection"
    COMPLETED = "completed"
    FAILED = "failed"
    #: The worker holding this run stopped without finishing. Distinct from
    #: FAILED, which means the work itself failed.
    RETRYABLE_FAILED = "retryable_failed"
    CANCELLED = "cancelled"


#: Legal forward transitions of the research state machine.
STAGE_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.QUEUED,
    PipelineStage.PROFILE_VALIDATION,
    PipelineStage.CANDIDATE_DISCOVERY,
    PipelineStage.PROGRAM_VERIFICATION,
    PipelineStage.FUNDING_DISCOVERY,
    PipelineStage.ASSESSMENT,
    PipelineStage.AWAITING_USER_DECISION,
    PipelineStage.DOCUMENT_COLLECTION,
    PipelineStage.COMPLETED,
)


class FetchOutcome(StrEnum):
    OK = "ok"
    REFUSED_PRIVACY = "refused_privacy"
    CACHED = "cached"
    ROBOTS_DISALLOWED = "robots_disallowed"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    NETWORK_UNAVAILABLE = "network_unavailable"
    UNPARSEABLE = "unparseable"
    #: Refused by the network policy before any connection was made.
    BLOCKED = "blocked"
    #: The body was larger than we will read.
    TOO_LARGE = "too_large"


# --- Social module ------------------------------------------------------


class ApplicantStatus(StrEnum):
    """Where an applicant says they stand with their universities.

    Two members only, and the column is nullable. A brand-new account has not
    told us anything, and NULL says exactly that — the product does not seed a
    default that would read on someone else's screen as a claim they made.
    """

    ACCEPTED = "accepted"
    WAITLIST = "waitlist"
