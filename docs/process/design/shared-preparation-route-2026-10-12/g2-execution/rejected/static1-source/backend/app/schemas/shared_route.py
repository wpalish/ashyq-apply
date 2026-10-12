"""Strict personal shared planning; no admissions proof or persistence authority."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, timedelta
from typing import Annotated, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_serializer,
    model_validator,
)

from app.schemas.learning_schedule import AttemptReviewRef, LessonRef
from app.schemas.preparation_graph import Digest, ResultId
from app.schemas.study_schedule import MAX_DAILY_MINUTES, Exam, Weekday

CATALOGUE_VERSION = "learning-pack-2026-10-11-v1"
STARTER_VERSION = "starter-2026-10-11-v1"
PLANNER_VERSION: Literal["shared-route-allocator-v1"] = "shared-route-allocator-v1"
Track = Literal["ielts_reading", "sat_math", "sat_reading_writing"]
TimingState = Literal["within_buffers", "at_risk", "deadline_passed"]
EXACT_LESSONS: tuple[tuple[str, Track, str], ...] = (
    ("ielts-reading-1", "ielts_reading", STARTER_VERSION),
    ("ielts-reading-headings-1", "ielts_reading", CATALOGUE_VERSION),
    ("ielts-reading-completion-1", "ielts_reading", CATALOGUE_VERSION),
    ("ielts-reading-features-1", "ielts_reading", CATALOGUE_VERSION),
    ("sat-math-1", "sat_math", STARTER_VERSION),
    ("sat-quadratic-structure-1", "sat_math", CATALOGUE_VERSION),
    ("sat-data-interpretation-1", "sat_math", CATALOGUE_VERSION),
    ("sat-rw-1", "sat_reading_writing", STARTER_VERSION),
    ("sat-grammar-transitions-1", "sat_reading_writing", CATALOGUE_VERSION),
)


def _local_date(value: object) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise ValueError("Use a local YYYY-MM-DD date, without a time or timestamp")


def _canonical_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        value,
    ):
        return UUID(value)
    raise ValueError("Use a hyphenated UUID")


def _confirmation(value: object) -> object:
    if value is not True:
        raise ValueError("Personal planning inputs must be explicitly confirmed")
    return value


def _iana_zone(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Use a valid IANA timezone string")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Use a valid IANA timezone") from exc
    return value


def _half_band(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("A personal band target must be a finite native number")
    if not 0 <= value <= 9 or not math.isfinite(value) or value * 2 != int(value * 2):
        raise ValueError("A personal band target must be 0..9 in half bands")
    return float(value)


def _positive_half_band(value: object) -> float:
    result = _half_band(value)
    if result == 0:
        raise ValueError("An entered overall target must be positive")
    return result


def _strict_ref(value: object, kind: Literal["lesson", "attempt_review"]) -> dict:
    if isinstance(value, LessonRef | AttemptReviewRef):
        value = value.model_dump(mode="python")
    if not isinstance(value, dict):
        raise ValueError("Use an exact typed learning reference")
    values = dict(value)
    if values.get("kind", kind) != kind:
        raise ValueError("Reference kind does not match the action")
    values["kind"] = kind
    for key in ("id", "lesson_id", "content_version"):
        item = values.get(key)
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError("Learning reference identifiers must be exact strings")
    if kind == "attempt_review":
        attempt_id = _canonical_uuid(values.get("attempt_id"))
        values["attempt_id"] = attempt_id
        expected = f"attempt:{attempt_id}"
    else:
        expected = f"lesson:{values['lesson_id']}:{values['content_version']}"
    if values["id"] != expected:
        raise ValueError("Learning reference ID must match its exact identity")
    return values


def _lesson_ref(value: object) -> dict:
    return _strict_ref(value, "lesson")


def _review_ref(value: object) -> dict:
    return _strict_ref(value, "attempt_review")


def _schedulable_ref(value: object) -> dict:
    if isinstance(value, LessonRef | AttemptReviewRef):
        return _strict_ref(value, value.kind)
    if isinstance(value, dict) and value.get("kind") in {"lesson", "attempt_review"}:
        return _strict_ref(value, value["kind"])
    raise ValueError("Only exact lessons and own attempt reviews are schedulable")


LocalDate = Annotated[date, BeforeValidator(_local_date)]
Confirmed = Annotated[Literal[True], BeforeValidator(_confirmation)]
IanaZone = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=80), BeforeValidator(_iana_zone)
]
HalfBand = Annotated[float, BeforeValidator(_half_band)]
PositiveHalfBand = Annotated[float, BeforeValidator(_positive_half_band)]
StrictLessonRef = Annotated[LessonRef, BeforeValidator(_lesson_ref)]
StrictReviewRef = Annotated[AttemptReviewRef, BeforeValidator(_review_ref)]
SchedulableRef = Annotated[
    LessonRef | AttemptReviewRef,
    Field(discriminator="kind"),
    BeforeValidator(_schedulable_ref),
]


def _identity_digest(value: object) -> str:
    wire = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def reference_action_id(exam: Exam, ref: LessonRef | AttemptReviewRef) -> str:
    """Stable exact-ref identity, with no programme or planned date component."""
    return _identity_digest(["shared-route-action-v1", exam, ref.kind, ref.model_dump(mode="json")])


def reference_occurrence_id(action_id: str, local_date: date) -> str:
    """One immutable whole action has occurrence ordinal zero on its local date."""
    return _identity_digest(["shared-route-slot-v1", action_id, local_date.isoformat(), 0])


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True, frozen=True)


class PersonalTargets(Base):
    @model_serializer(mode="wrap")
    def _supplied_fields(self, handler) -> dict:
        values = handler(self)
        return {name: value for name, value in values.items() if name in self.model_fields_set}

    @model_validator(mode="before")
    @classmethod
    def _provided_values(cls, value: object) -> object:
        if isinstance(value, dict) and any(item is None for item in value.values()):
            raise ValueError("Omit an unknown target component; do not fill it with null")
        return value


class PersonalIeltsTargets(PersonalTargets):
    overall: PositiveHalfBand | None = None
    listening: HalfBand | None = None
    reading: HalfBand | None = None
    writing: HalfBand | None = None
    speaking: HalfBand | None = None


class PersonalSatTargets(PersonalTargets):
    total: int | None = Field(default=None, ge=400, le=1600, strict=True)
    math: int | None = Field(default=None, ge=200, le=800, strict=True)
    reading_writing: int | None = Field(default=None, ge=200, le=800, strict=True)

    @model_validator(mode="after")
    def _complete_sum(self) -> Self:
        if self.total is not None and self.math is not None and self.reading_writing is not None:
            if self.math + self.reading_writing < self.total:
                raise ValueError("Complete personal SAT section targets must cover the total")
        return self


class ExamWindowInput(Base):
    priority: int = Field(ge=0, le=1, strict=True)
    first_exam_on: LocalDate
    retake_on: LocalDate | None = None
    certificate_deadline: LocalDate
    result_wait_days: int = Field(ge=1, le=60, strict=True)
    delivery_days: int = Field(ge=0, le=30, strict=True)
    safety_days: int = Field(ge=0, le=30, strict=True)
    confirmed_exam_dates_and_buffers: Confirmed

    @model_validator(mode="after")
    def _window(self) -> Self:
        if self.first_exam_on >= self.certificate_deadline:
            raise ValueError("The first exam must precede the entered certificate deadline")
        if self.retake_on is not None and not (
            self.first_exam_on < self.retake_on < self.certificate_deadline
        ):
            raise ValueError(
                "A retake must be after the first exam and before the entered deadline"
            )
        try:
            days = self.result_wait_days + self.delivery_days + self.safety_days
            self.certificate_deadline - timedelta(days=days)
            (self.retake_on or self.first_exam_on) + timedelta(days=days)
        except OverflowError as exc:
            raise ValueError("Entered dates and buffers exceed the supported calendar") from exc
        return self


class IeltsExamChoiceInput(ExamWindowInput):
    exam: Literal["ielts_academic"]
    personal_targets: PersonalIeltsTargets | None = None


class SatExamChoiceInput(ExamWindowInput):
    exam: Literal["digital_sat"]
    personal_targets: PersonalSatTargets | None = None


ExamChoiceInput = Annotated[IeltsExamChoiceInput | SatExamChoiceInput, Field(discriminator="exam")]


class OwnReviewInput(Base):
    ref: StrictReviewRef
    exam: Exam
    planned_minutes: int = Field(ge=1, le=1260, strict=True)


class SharedRouteInputV1(Base):
    schema_version: Literal["shared-route-v1"] = "shared-route-v1"
    selected_result_ids: list[ResultId] = Field(min_length=2, max_length=20)
    starts_on: LocalDate
    timezone: IanaZone
    study_days: list[Weekday] = Field(min_length=1, max_length=7)
    shared_weekly_minutes: int = Field(ge=30, le=1260, strict=True)
    exam_choices: list[ExamChoiceInput] = Field(min_length=1, max_length=2)
    own_reviews: list[OwnReviewInput] = Field(default_factory=list, max_length=400)
    confirmed_shared_planning_inputs: Confirmed

    @model_validator(mode="after")
    def _route(self) -> Self:
        if any(value != value.strip() for value in self.selected_result_ids) or len(
            set(self.selected_result_ids)
        ) != len(self.selected_result_ids):
            raise ValueError("Selected result IDs must be exact, unique and ordered")
        if len(set(self.study_days)) != len(self.study_days):
            raise ValueError("Study days must be unique")
        exams = [choice.exam for choice in self.exam_choices]
        if len(set(exams)) != len(exams) or [c.priority for c in self.exam_choices] != list(
            range(len(exams))
        ):
            raise ValueError("Unique exam priorities must match the explicit choice order")
        if any(choice.first_exam_on < self.starts_on for choice in self.exam_choices):
            raise ValueError("Each first exam must be on or after the shared start")
        if (max(c.certificate_deadline for c in self.exam_choices) - self.starts_on).days > 365:
            raise ValueError("The complete planning horizon cannot exceed 365 days")
        if len({review.ref.attempt_id for review in self.own_reviews}) != len(self.own_reviews):
            raise ValueError("An own attempt may be selected once")
        if any(review.exam not in exams for review in self.own_reviews):
            raise ValueError("Every review must belong to an explicitly chosen personal exam")
        return self


class ExactCatalogueLesson(Base):
    ref: StrictLessonRef
    track: Track
    available: bool = Field(strict=True)


class FrozenExactCatalogue(Base):
    """Caller-supplied nine public identities and exact dispatcher availability."""

    version: Literal["learning-pack-2026-10-11-v1"] = "learning-pack-2026-10-11-v1"
    lessons: list[ExactCatalogueLesson] = Field(min_length=9, max_length=9)

    @model_validator(mode="after")
    def _exact_registry(self) -> Self:
        actual = tuple(
            (unit.ref.lesson_id, unit.track, unit.ref.content_version) for unit in self.lessons
        )
        if actual != EXACT_LESSONS:
            raise ValueError("Use the nine pinned exact-version refs in catalogue track order")
        return self


class ValidatedOwnedReviewV1(Base):
    """An upstream owner/exact receipt/exam association check, never a DB lookup."""

    ref: StrictReviewRef
    exam: Exam
    available: bool = Field(strict=True)


class DatedSlot(Base):
    occurrence_id: Digest
    action_id: Digest
    ref: SchedulableRef
    exam: Exam
    kind: Literal["lesson", "attempt_review"]
    local_date: LocalDate
    planned_minutes: int = Field(ge=1, le=MAX_DAILY_MINUTES, strict=True)
    origin: Literal["personal_practice"] = "personal_practice"
    completion: Literal["not_projected"] = "not_projected"

    @model_validator(mode="after")
    def _identity(self) -> Self:
        if self.kind != self.ref.kind:
            raise ValueError("Slot kind must equal its exact reference kind")
        if self.action_id != reference_action_id(self.exam, self.ref):
            raise ValueError("Action ID must match its exam and exact learning reference")
        if self.occurrence_id != reference_occurrence_id(self.action_id, self.local_date):
            raise ValueError("Occurrence ID must match its action, local date and ordinal zero")
        if isinstance(self.ref, LessonRef) and self.planned_minutes != 20:
            raise ValueError("A current lesson retains its exact 20-minute planning allocation")
        return self


class WeekCapacity(Base):
    iso_week_monday: LocalDate
    weekly_budget_minutes: int = Field(ge=30, le=1260, strict=True)
    allocated_minutes: int = Field(ge=0, le=1260, strict=True)
    remaining_minutes: int = Field(ge=0, le=1260, strict=True)

    @model_validator(mode="after")
    def _ledger(self) -> Self:
        if self.iso_week_monday.weekday() != 0:
            raise ValueError("A local week ledger must start on Monday")
        if self.allocated_minutes + self.remaining_minutes != self.weekly_budget_minutes:
            raise ValueError("A week ledger must preserve the single entered budget")
        return self


UnallocatedReason = Literal[
    "insufficient_capacity",
    "window_elapsed",
    "too_long_for_day",
    "too_long_for_week",
    "slot_limit",
    "version_unavailable",
]


class UnallocatedAction(Base):
    action_id: Digest
    ref: SchedulableRef
    exam: Exam
    requested_minutes: int = Field(ge=1, le=1260, strict=True)
    reason: UnallocatedReason

    @model_validator(mode="after")
    def _identity(self) -> Self:
        if self.action_id != reference_action_id(self.exam, self.ref):
            raise ValueError("Action ID must match its exam and exact learning reference")
        if isinstance(self.ref, LessonRef) and self.requested_minutes != 20:
            raise ValueError("A current lesson retains its exact 20-minute planning allocation")
        return self


class ExamTiming(Base):
    exam: Exam
    first_exam_on: LocalDate
    retake_on: LocalDate | None = None
    certificate_deadline: LocalDate
    result_wait_days: int = Field(ge=1, le=60, strict=True)
    delivery_days: int = Field(ge=0, le=30, strict=True)
    safety_days: int = Field(ge=0, le=30, strict=True)
    latest_safe_exam_on: LocalDate
    timing: TimingState


class SharedAllocationV1(Base):
    planner_version: Literal["shared-route-allocator-v1"] = "shared-route-allocator-v1"
    planned_on: LocalDate
    timezone: IanaZone
    ordered_exam_choices: list[ExamChoiceInput] = Field(min_length=1, max_length=2)
    lessons: list[StrictLessonRef] = Field(max_length=9)
    slots: list[DatedSlot] = Field(max_length=400)
    capacity: list[WeekCapacity] = Field(max_length=54)
    unallocated: list[UnallocatedAction] = Field(max_length=409)
    exam_timing: list[ExamTiming] = Field(min_length=1, max_length=2)
    readiness: Literal["not_assessed"] = "not_assessed"
    programme_applicability: Literal["unknown"] = "unknown"
    digest: Digest

    @model_validator(mode="after")
    def _allocation(self) -> Self:
        choices = {choice.exam: choice for choice in self.ordered_exam_choices}
        if len(choices) != len(self.ordered_exam_choices) or [
            c.priority for c in self.ordered_exam_choices
        ] != list(range(len(choices))):
            raise ValueError("Allocation exam order must be unique and contiguous")
        expected_lessons = [
            (lesson_id, version)
            for lesson_id, track, version in EXACT_LESSONS
            if ("ielts_academic" if track == "ielts_reading" else "digital_sat") in choices
        ]
        if [(ref.lesson_id, ref.content_version) for ref in self.lessons] != expected_lessons:
            raise ValueError("Allocation must retain every selected pinned lesson once")
        all_actions: list[DatedSlot | UnallocatedAction] = [*self.slots, *self.unallocated]
        if len({action.action_id for action in all_actions}) != len(all_actions):
            raise ValueError("Each exact action must be either scheduled or unallocated once")
        if len({slot.occurrence_id for slot in self.slots}) != len(self.slots):
            raise ValueError("Scheduled occurrences must be unique")
        projected_lessons = [
            (action.ref.lesson_id, action.ref.content_version)
            for action in all_actions
            if isinstance(action.ref, LessonRef)
        ]
        if len(projected_lessons) != len(expected_lessons) or set(projected_lessons) != set(
            expected_lessons
        ):
            raise ValueError("Every selected exact lesson must retain one action")
        if any(action.exam not in choices for action in all_actions):
            raise ValueError("An action must belong to a selected personal exam")
        lesson_exams = {
            (lesson_id, version): "ielts_academic" if track == "ielts_reading" else "digital_sat"
            for lesson_id, track, version in EXACT_LESSONS
        }
        if any(
            isinstance(action.ref, LessonRef)
            and action.exam != lesson_exams[(action.ref.lesson_id, action.ref.content_version)]
            for action in all_actions
        ):
            raise ValueError("An exact current lesson must retain its known track/exam association")
        weeks = [week.iso_week_monday for week in self.capacity]
        if (
            weeks != sorted(set(weeks))
            or len({week.weekly_budget_minutes for week in self.capacity}) > 1
        ):
            raise ValueError("There is one ascending, shared weekly ledger")
        day_minutes: dict[date, int] = {}
        week_minutes: dict[date, int] = {}
        exam_days = {choice.first_exam_on for choice in choices.values()} | {
            choice.retake_on for choice in choices.values() if choice.retake_on is not None
        }
        for slot in self.slots:
            choice = choices[slot.exam]
            end = (
                (choice.retake_on or choice.first_exam_on)
                if slot.kind == "attempt_review"
                else choice.first_exam_on
            )
            if not self.planned_on <= slot.local_date < end or slot.local_date in exam_days:
                raise ValueError("A slot must remain in its entered personal window")
            day_minutes[slot.local_date] = (
                day_minutes.get(slot.local_date, 0) + slot.planned_minutes
            )
            monday = slot.local_date - timedelta(days=slot.local_date.weekday())
            week_minutes[monday] = week_minutes.get(monday, 0) + slot.planned_minutes
        if any(minutes > MAX_DAILY_MINUTES for minutes in day_minutes.values()):
            raise ValueError("All exam streams share the 180-minute daily cap")
        if not set(week_minutes).issubset(weeks) or any(
            week.allocated_minutes != week_minutes.get(week.iso_week_monday, 0)
            for week in self.capacity
        ):
            raise ValueError("Week capacity must match all scheduled minutes")
        if [timing.exam for timing in self.exam_timing] != [
            choice.exam for choice in self.ordered_exam_choices
        ]:
            raise ValueError("Timing must preserve the entered exam order")
        for timing in self.exam_timing:
            choice = choices[timing.exam]
            for name in (
                "first_exam_on",
                "retake_on",
                "certificate_deadline",
                "result_wait_days",
                "delivery_days",
                "safety_days",
            ):
                if getattr(timing, name) != getattr(choice, name):
                    raise ValueError("Timing must preserve entered dates and buffers")
            days = choice.result_wait_days + choice.delivery_days + choice.safety_days
            expected_safe = choice.certificate_deadline - timedelta(days=days)
            late = (choice.retake_on or choice.first_exam_on) + timedelta(days=days)
            expected_timing = (
                "deadline_passed"
                if self.planned_on > choice.certificate_deadline
                else "at_risk"
                if late > choice.certificate_deadline
                else "within_buffers"
            )
            if timing.latest_safe_exam_on != expected_safe or timing.timing != expected_timing:
                raise ValueError("Timing is only the entered buffer calculation")
        return self
