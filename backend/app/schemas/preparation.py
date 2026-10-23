"""Versioned starter practice; raw practice totals are never official test scores."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.claim import ClaimOut
from app.schemas.result import RequirementCheck

TrackId = Literal["ielts_reading", "sat_math", "sat_reading_writing"]
EvidenceState = Literal["unknown", "locked", "current", "stale", "conflicted"]
Policy = Literal["required", "optional", "waiver_check", "alternatives_unresolved", "unknown"]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PreparationAccess(Base):
    allowed: bool
    reason: Literal["development_mode", "subscription_term", "no_eligible_subscription"]
    subscription_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    development_only: bool = False


class TrackSummary(Base):
    id: TrackId
    title: str
    lesson_ids: list[str]


class LessonSummary(Base):
    id: str
    track_id: TrackId
    title: str
    question_count: int


class ExamSummary(Base):
    id: Literal["ielts_academic", "digital_sat", "toefl_ibt", "det", "hsk_hskk", "csca"]
    title: str
    role: Literal["language", "academic"]
    course_status: Literal["starter", "planned"]
    track_ids: list[TrackId]
    official_info_urls: list[str]
    official_practice_urls: list[str]
    notice: str
    checked_date: str


class PreparationCatalogue(Base):
    version: str
    tracks: list[TrackSummary]
    lessons: list[LessonSummary]
    exams: list[ExamSummary]
    notice: str


class Choice(Base):
    id: str
    text: str


class Question(Base):
    id: str
    prompt: str
    choices: list[Choice]


class PreparationLesson(Base):
    id: str
    track_id: TrackId
    title: str
    version: str
    introduction: str
    questions: list[Question]
    unofficial: Literal[True] = True


class Answer(Base):
    question_id: str = Field(min_length=1, max_length=80)
    choice_id: str = Field(min_length=1, max_length=80)


class StudyAttemptIn(Base):
    attempt_id: UUID
    lesson_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    answers: list[Answer] = Field(min_length=1, max_length=20)


class AnswerFeedback(Base):
    question_id: str
    selected_choice_id: str
    correct_choice_id: str
    correct: bool
    explanation: str


class StudyAttemptOut(Base):
    id: str
    attempt_id: UUID
    profile_id: str
    lesson_id: str
    version: str
    answers: list[Answer]
    correct: int
    total: int
    feedback: list[AnswerFeedback]
    created_at: datetime


class ShortQuestion(Base):
    id: str
    prompt: str
    answer_format: Literal["short_answer"] = "short_answer"
    max_words: int = Field(ge=1, le=2)


class ShortAnswer(Base):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    question_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=100)

    @field_validator("text")
    @classmethod
    def _nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Answer text cannot be blank")
        return value


class ShortAnswerFeedback(Base):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    question_id: str
    selected_text: str
    accepted_answers: list[str]
    correct: bool
    explanation: str


class LearningPackStudyAttemptIn(Base):
    attempt_id: UUID
    lesson_id: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    answers: list[Answer | ShortAnswer] = Field(min_length=1, max_length=20)


class LearningPackStudyAttemptOut(Base):
    id: str
    attempt_id: UUID
    profile_id: str
    lesson_id: str
    version: str
    answers: list[Answer | ShortAnswer]
    correct: int
    total: int
    feedback: list[AnswerFeedback | ShortAnswerFeedback]
    created_at: datetime


class LearningPackLesson(Base):
    id: str
    track_id: TrackId
    title: str
    version: str
    introduction: str
    questions: list[Question | ShortQuestion]
    unofficial: Literal[True] = True


class LearningPackLessonSummary(LessonSummary):
    version: str


class LearningPackCatalogue(Base):
    version: str
    tracks: list[TrackSummary]
    lessons: list[LearningPackLessonSummary]
    exams: list[ExamSummary]
    notice: str


class StudyAttemptReview(Base):
    attempt: StudyAttemptOut | LearningPackStudyAttemptOut
    lesson: PreparationLesson | LearningPackLesson | None
    notice: str


class PreparationProgress(Base):
    profile_id: str
    attempt_count: int
    correct: int
    answered: int
    completed_lesson_ids: list[str]
    attempts: list[StudyAttemptOut | LearningPackStudyAttemptOut]


class PreparationCheck(Base):
    requirement_check: RequirementCheck
    evidence_state: EvidenceState
    policy: Policy
    claims: list[ClaimOut]
    claim_ids: list[str]
    source_urls: list[str]
    lesson_ids: list[str]


class PreparationPlan(Base):
    profile_id: str
    result_id: str | None = None
    research_access: bool
    evidence_state: EvidenceState
    checks: list[PreparationCheck]
    notice: str


class CompletedLesson(Base):
    lesson_id: str
    version: str


class LearningPackProgress(PreparationProgress):
    catalogue_version: Literal["learning-pack-2026-10-11-v1"] = "learning-pack-2026-10-11-v1"
    completed_lessons: list[CompletedLesson]
