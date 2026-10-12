"""Applicant-entered study planning, separate from official requirement evidence."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Exam = Literal["ielts_academic", "digital_sat"]
TaskKind = Literal[
    "diagnostic",
    "skill",
    "review",
    "timed_practice",
    "mock",
    "exam",
    "results",
    "delivery",
    "submit",
]
Weekday = Annotated[int, Field(strict=True, ge=0, le=6)]
CompletionId = Annotated[str, Field(min_length=1, max_length=160)]
IELTS_KEYS = frozenset({"overall", "listening", "reading", "writing", "speaking"})
SAT_KEYS = frozenset({"total", "math", "reading_writing"})
MAX_DAILY_MINUTES = 180


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ScheduleSettings(Base):
    exam: Exam
    starts_on: date
    certificate_deadline: date
    first_exam_on: date
    retake_on: date | None = None
    result_wait_days: int = Field(ge=1, le=60, strict=True)
    delivery_days: int = Field(ge=0, le=30, strict=True)
    safety_days: int = Field(ge=0, le=30, strict=True)
    timezone: str = Field(min_length=1, max_length=80)
    weekly_minutes: int = Field(ge=30, le=1260, strict=True)
    study_days: list[Weekday] = Field(min_length=1, max_length=7)
    target_scores: dict[str, float]
    baseline_scores: dict[str, float] = Field(default_factory=dict)
    baseline_on: date | None = None
    confirmed_planning_dates: Literal[True]
    completed_task_ids: list[CompletionId] = Field(default_factory=list, max_length=400)

    @field_validator("confirmed_planning_dates", mode="before")
    @classmethod
    def _explicit_confirmation(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Planning dates must be explicitly confirmed as applicant-entered")
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return value

    @field_validator("study_days", "completed_task_ids")
    @classmethod
    def _unique(cls, value: list) -> list:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate entries are not allowed")
        return value

    @field_validator("target_scores", "baseline_scores", mode="before")
    @classmethod
    def _not_boolean_scores(cls, value: object) -> object:
        if isinstance(value, dict) and any(isinstance(v, bool) for v in value.values()):
            raise ValueError("A boolean is not a test score")
        return value

    @model_validator(mode="after")
    def _settings(self) -> ScheduleSettings:
        keys = IELTS_KEYS if self.exam == "ielts_academic" else SAT_KEYS
        if set(self.target_scores) != keys or not set(self.baseline_scores) <= keys:
            raise ValueError(
                "Use the complete target keys and only known baseline keys for this exam"
            )
        for scores in (self.target_scores, self.baseline_scores):
            for key, value in scores.items():
                if not math.isfinite(value):
                    raise ValueError("Scores must be finite")
                if self.exam == "ielts_academic":
                    if not 0 <= value <= 9 or value * 2 != int(value * 2):
                        raise ValueError("IELTS planning scores must be 0..9 in half bands")
                else:
                    low, high = (400, 1600) if key == "total" else (200, 800)
                    if not low <= value <= high or value != int(value):
                        raise ValueError(
                            "SAT planning scores must be integers within their score range"
                        )
        if self.exam == "ielts_academic" and self.target_scores["overall"] <= 0:
            raise ValueError("The IELTS overall target must be positive")
        if self.exam == "digital_sat":
            if (
                self.target_scores["math"] + self.target_scores["reading_writing"]
                < self.target_scores["total"]
            ):
                raise ValueError("SAT section targets must sum to at least the total target")
            if (
                set(self.baseline_scores) == SAT_KEYS
                and self.baseline_scores["math"] + self.baseline_scores["reading_writing"]
                != self.baseline_scores["total"]
            ):
                raise ValueError("A complete SAT baseline total must equal its sections")
        if bool(self.baseline_scores) != (self.baseline_on is not None):
            raise ValueError("Baseline scores and baseline_on must be provided together")
        if not self.starts_on <= self.first_exam_on < self.certificate_deadline:
            raise ValueError("Use starts_on <= first_exam_on < certificate_deadline")
        if (
            self.retake_on is not None
            and not self.first_exam_on < self.retake_on < self.certificate_deadline
        ):
            raise ValueError(
                "A retake must be after the first exam and before the entered deadline"
            )
        if (self.certificate_deadline - self.starts_on).days > 365:
            raise ValueError("The planning horizon cannot exceed 365 days")
        try:
            self.certificate_deadline - timedelta(
                days=self.result_wait_days + self.delivery_days + self.safety_days
            )
            (self.retake_on or self.first_exam_on) + timedelta(
                days=self.result_wait_days + self.delivery_days + self.safety_days
            )
        except OverflowError as exc:
            raise ValueError("Planning dates exceed the supported calendar range") from exc
        return self


class ScheduleWrite(Base):
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)
    settings: ScheduleSettings


class ScheduleTask(Base):
    id: str = Field(min_length=1, max_length=160)
    due_on: date
    title: str
    kind: TaskKind
    skill: str | None = None
    minutes: int = Field(ge=0, le=MAX_DAILY_MINUTES)
    lesson_id: str | None = None
    completed: bool = False
    overdue: bool = False


class GeneratedSchedule(Base):
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
    tasks: list[ScheduleTask] = Field(max_length=400)


class StudyScheduleOut(Base):
    profile_id: str
    revision: int = Field(ge=0)
    settings: ScheduleSettings | None = None
    schedule: GeneratedSchedule | None = None
    updated_at: datetime | None = None
