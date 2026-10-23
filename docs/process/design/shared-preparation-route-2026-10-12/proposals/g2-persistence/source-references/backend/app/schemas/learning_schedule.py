"""Opt-in calendar binding. Legacy ScheduleSettings and its wire shape stay intact."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.study_schedule import Base, ScheduleSettings, ScheduleTask


class LessonRef(Base):
    kind: Literal["lesson"] = "lesson"
    id: str = Field(min_length=1, max_length=200)
    lesson_id: str = Field(min_length=1, max_length=80)
    content_version: str = Field(min_length=1, max_length=40)


class AttemptReviewRef(Base):
    kind: Literal["attempt_review"] = "attempt_review"
    id: str = Field(min_length=1, max_length=200)
    attempt_id: UUID
    lesson_id: str = Field(min_length=1, max_length=80)
    content_version: str = Field(min_length=1, max_length=40)


class AssessmentRef(Base):
    kind: Literal["assessment"] = "assessment"
    id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=40)


class ResourceRef(Base):
    kind: Literal["external_resource"] = "external_resource"
    id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=40)


LearningTaskRef = Annotated[
    LessonRef | AttemptReviewRef | AssessmentRef | ResourceRef, Field(discriminator="kind")
]


class LearningUnit(Base):
    ref: LessonRef
    skill: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    # Scheduling allocation, not a claim about time to learn or improve a score.
    planned_minutes: Literal[20] = 20


class LearningPathSettings(Base):
    planner_version: Literal["schedule-v2"] = "schedule-v2"
    catalogue_version: str = Field(min_length=1, max_length=40)
    schedule_settings: ScheduleSettings
    lessons: list[LearningUnit] = Field(min_length=1, max_length=9)
    reviews: list[AttemptReviewRef] = Field(default_factory=list, max_length=400)

    @model_validator(mode="after")
    def independent_ticks(self) -> LearningPathSettings:
        if self.schedule_settings.completed_task_ids:
            raise ValueError("Legacy checkmarks belong to the preserved original calendar")
        if len({unit.ref.id for unit in self.lessons}) != len(self.lessons):
            raise ValueError("Duplicate lesson references")
        if len({ref.id for ref in self.reviews}) != len(self.reviews):
            raise ValueError("Duplicate review references")
        return self


class LearningTask(ScheduleTask):
    learning_ref: LearningTaskRef | None = None
    availability: Literal["available", "unavailable"] = "unavailable"
    unavailable_reason: (
        Literal["no_local_content", "attempt_required", "not_implemented", "version_unavailable"]
        | None
    ) = None
    submitted_attempt_id: UUID | None = None


class LearningSchedule(Base):
    as_of: date
    latest_exam_on: date
    latest_safe_exam_on: date
    result_expected_on: date
    delivery_expected_on: date
    study_minutes_remaining: int = Field(ge=0)
    remaining_study_days: int = Field(ge=0)
    diagnostic_required: bool
    readiness: Literal["not_assessed"] = "not_assessed"
    timing: Literal["within_entered_buffers", "at_risk", "deadline_passed"]
    warnings: list[str]
    tasks: list[LearningTask] = Field(max_length=400)
    unallocated_lesson_ids: list[str]
    unallocated_review_ids: list[str]


class LearningPathDraft(Base):
    plan: LearningPathSettings
    planned_on: date
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class LearningPathSnapshot(Base):
    draft: LearningPathDraft
    schedule: LearningSchedule
    legacy_settings: ScheduleSettings
    legacy_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class LearningPathOut(Base):
    profile_id: str
    revision: int = Field(ge=0)
    legacy_fingerprint: str | None = None
    learning_path: LearningPathSnapshot | None = None
    needs_review: bool = False
    updated_at: datetime | None = None


class LearningPathPreview(Base):
    expected_revision: int = Field(ge=1, le=2_147_483_646, strict=True)


class LearningPathWrite(LearningPathPreview):
    legacy_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft: LearningPathDraft
