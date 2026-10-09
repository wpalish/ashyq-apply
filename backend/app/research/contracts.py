"""Public policy evidence, separate from an applicant's local projection."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QuestionState(StrEnum):
    PENDING = "pending"
    PARTIAL = "partial"
    ANSWERED = "answered"
    CONFLICT = "conflict"
    NOT_PUBLISHED = "not_published"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"


class QuestionGroup(StrEnum):
    ENGLISH = "english"
    ACADEMIC = "academic"
    DEADLINE = "deadline"
    TUITION = "tuition"
    SCHOLARSHIP_EXISTENCE = "scholarship_existence"
    SCHOLARSHIP_APPLICABILITY = "scholarship_applicability"


class PublicScope(StrictModel):
    university: str = Field(min_length=1)
    cycle: str = Field(min_length=1)
    programme: str | None = None
    campus: str | None = None
    degree: str | None = None
    population: str | None = None
    qualification: str | None = None
    nationality: str | None = None

    def covers(self, request: PublicScope) -> bool:
        # Missing dimensions never silently mean "every applicant". A rule
        # applying to all programmes must be expanded by a reviewed compiler.
        return all(
            value is None or getattr(self, key) == value
            for key, value in request.model_dump().items()
        )


class EvidenceSpan(StrictModel):
    source_url: HttpUrl
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    accessed_at: datetime
    block_id: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=600)
    section_path: tuple[str, ...] = ()
    row: int | None = None
    column: int | None = None


class PolicyRule(StrictModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    group: QuestionGroup
    value: JsonValue
    scope: PublicScope
    evidence: tuple[EvidenceSpan, ...] = Field(min_length=1)
    conditions: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    valid_until: datetime


class ResearchQuestion(StrictModel):
    id: str = Field(min_length=1)
    group: QuestionGroup
    scope: PublicScope
    required: tuple[str, ...] = Field(min_length=1)


class DecisionAnswer(StrictModel):
    question_id: str
    state: QuestionState
    reason: str = Field(min_length=1)
    rules: tuple[PolicyRule, ...] = ()
    missing: tuple[str, ...] = ()
