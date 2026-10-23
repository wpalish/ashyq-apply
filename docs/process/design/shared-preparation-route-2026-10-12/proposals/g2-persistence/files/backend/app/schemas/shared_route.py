"""Strict personal shared planning; no admissions proof or persistence authority."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, date, datetime, timedelta
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
from app.schemas.preparation_graph import Digest, PreparationGraph, ResultId
from app.schemas.preparation_graph_loader import assert_finite_floats
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
        if (
            self.total is not None
            and self.math is not None
            and self.reading_writing is not None
            and self.math + self.reading_writing < self.total
        ):
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


# Persistence DTOs append to the qualified personal allocator contract above.
# A digest verifies a saved observation; it is not admissions or scoring proof.
def _utc_timestamp(value: object) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Use an explicit UTC timestamp") from exc
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Use an explicit UTC timestamp")
    if value.utcoffset() != timedelta(0):
        raise ValueError("Receipt timestamps must be UTC")
    return value.astimezone(UTC)


UtcTimestamp = Annotated[datetime, BeforeValidator(_utc_timestamp)]
WriteUuid = Annotated[UUID, BeforeValidator(_canonical_uuid)]


def shared_input_wire(value: SharedRouteInputV1) -> dict:
    """Same canonical input wire as the unchanged pure allocator."""
    checked = SharedRouteInputV1.model_validate(value.model_dump(mode="python"))
    assert_finite_floats(checked.model_dump(mode="python"))
    wire = checked.model_dump(mode="json")
    wire["study_days"] = sorted(checked.study_days)
    return wire


def allocation_snapshot_digest(
    value: SharedRouteInputV1,
    catalogue: FrozenExactCatalogue,
    own_reviews: list[ValidatedOwnedReviewV1],
    allocation: SharedAllocationV1,
) -> str:
    """Verify the allocator's exact saved wire without allocating or resolving."""
    assert_finite_floats(value.model_dump(mode="python"))
    assert_finite_floats(catalogue.model_dump(mode="python"))
    assert_finite_floats(allocation.model_dump(mode="python"))
    return _identity_digest(
        {
            "input": shared_input_wire(value),
            "catalogue": catalogue.model_dump(mode="json"),
            "owned_review_availability": [item.model_dump(mode="json") for item in own_reviews],
            "allocation": allocation.model_dump(mode="json", exclude={"digest"}),
        }
    )


class LegacyAnchor(Base):
    technical_revision: int = Field(ge=0, le=2147483646, strict=True)
    structural_fingerprint: Digest | None
    imported_learning_refs_fingerprint: Literal[None] = None

    @model_validator(mode="after")
    def _legacy_presence(self) -> Self:
        if (self.technical_revision == 0) != (self.structural_fingerprint is None):
            raise ValueError("Only an absent legacy calendar has a null structural fingerprint")
        return self


class SharedRoutePreviewRequestV1(Base):
    applicant_input: SharedRouteInputV1
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)


class SharedRouteWriteV1(SharedRoutePreviewRequestV1):
    client_write_uuid: WriteUuid
    preview_fingerprint: Digest
    source_fingerprint: Digest
    legacy_anchor: LegacyAnchor
    planned_on: LocalDate


class PerGoalDigest(Base):
    result_id: ResultId
    reference_digest: Digest | None


GoalState = Literal[
    "eligible", "decision_changed", "result_unavailable", "research_locked",
    "source_changed", "evidence_unknown",
]
GoalReason = Literal[
    "decision_changed", "result_unavailable", "research_locked", "source_changed",
    "evidence_unknown",
]
ContentState = Literal["available", "version_unavailable", "review_unavailable", "unknown"]
ReviewCode = Literal[
    "goal_decision_changed", "goal_result_unavailable", "goal_research_locked",
    "goal_source_changed", "goal_evidence_unknown", "legacy_structure_changed",
    "legacy_structure_unknown", "imported_refs_changed", "imported_refs_unknown",
    "content_version_unavailable", "own_review_unavailable", "content_unknown",
]


class GoalStatusV1(Base):
    result_id: ResultId
    state: GoalState
    safe_reason_code: GoalReason | None

    @model_validator(mode="after")
    def _fixed_reason(self) -> Self:
        if self.safe_reason_code != (None if self.state == "eligible" else self.state):
            raise ValueError("Goal status exposes only its fixed safe reason code")
        return self


class ContentStatusV1(Base):
    action_id: Digest
    state: ContentState


class ReviewReasonV1(Base):
    code: ReviewCode
    result_id: ResultId | None = None
    action_id: Digest | None = None

    @model_validator(mode="after")
    def _reason_identity(self) -> Self:
        if self.code.startswith("goal_"):
            valid = self.result_id is not None and self.action_id is None
        elif self.code.startswith("content_") or self.code == "own_review_unavailable":
            valid = self.action_id is not None and self.result_id is None
        else:
            valid = self.result_id is None and self.action_id is None
        if not valid:
            raise ValueError("A review reason retains only its applicable safe identity")
        return self


def shared_preview_fingerprint(
    profile_id: str,
    value: SharedRouteInputV1,
    expected_revision: int,
    legacy_anchor: LegacyAnchor,
    planned_on: date,
    source_fingerprint: str,
    source_references: list[PerGoalDigest],
    allocation: SharedAllocationV1,
) -> str:
    return _identity_digest(
        {
            "schema_version": "shared-route-preview-v1",
            "profile_id": profile_id,
            "input": shared_input_wire(value),
            "expected_revision": expected_revision,
            "legacy_anchor": legacy_anchor.model_dump(mode="json"),
            "planned_on": planned_on.isoformat(),
            "source_fingerprint": source_fingerprint,
            "source_reference_digests": [item.model_dump(mode="json") for item in source_references],
            "catalogue_version": CATALOGUE_VERSION,
            "allocation_digest": allocation.digest,
        }
    )


def shared_request_digest(profile_id: str, payload: SharedRouteWriteV1) -> str:
    wire = payload.model_dump(mode="json")
    wire["applicant_input"] = shared_input_wire(payload.applicant_input)
    return _identity_digest(
        {"schema_version": "shared-route-write-v1", "profile_id": profile_id, "request": wire}
    )


class SharedRoutePreviewOutV1(Base):
    profile_id: ResultId
    expected_shared_revision: int = Field(ge=0, le=2147483646, strict=True)
    legacy_anchor: LegacyAnchor
    planned_on: LocalDate
    expires_on_local_date: LocalDate
    requested_result_ids: list[ResultId] = Field(min_length=2, max_length=20)
    selected_result_ids: list[ResultId] = Field(min_length=2, max_length=20)
    selection_source: Literal["server_verified_owned_explicit"] = "server_verified_owned_explicit"
    source_fingerprint: Digest
    allocation: SharedAllocationV1
    preview_fingerprint: Digest
    review_reasons: list[ReviewReasonV1]
    saved: Literal[False] = False

    @model_validator(mode="after")
    def _unsaved_identity(self) -> Self:
        if self.requested_result_ids != self.selected_result_ids or len(set(self.selected_result_ids)) != len(self.selected_result_ids):
            raise ValueError("An unsaved preview retains the exact ordered whole selection")
        if self.planned_on != self.allocation.planned_on or self.expires_on_local_date != self.planned_on:
            raise ValueError("A preview expires after its exact local planning date")
        if any(item.result_id is not None and item.result_id not in self.selected_result_ids for item in self.review_reasons):
            raise ValueError("Preview review reasons belong to the explicit selection")
        return self


class SharedRouteWriteReceiptV1(Base):
    schema_version: Literal["shared-route-v1"] = "shared-route-v1"
    profile_id: ResultId
    revision: int = Field(ge=1, le=2147483647, strict=True)
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)
    client_write_uuid: WriteUuid
    canonical_request_digest: Digest
    accepted_at: UtcTimestamp
    selected_result_ids: list[ResultId] = Field(min_length=2, max_length=20)
    applicant_input: SharedRouteInputV1
    accepted_planned_on: LocalDate
    catalogue_version: Literal["learning-pack-2026-10-11-v1"] = "learning-pack-2026-10-11-v1"
    planner_version: Literal["shared-route-allocator-v1"] = "shared-route-allocator-v1"
    catalogue_snapshot: FrozenExactCatalogue
    owned_review_snapshot: list[ValidatedOwnedReviewV1] = Field(max_length=400)
    allocation: SharedAllocationV1
    allocation_digest: Digest
    source_fingerprint: Digest
    source_reference_digests: list[PerGoalDigest] = Field(min_length=2, max_length=20)
    preview_fingerprint: Digest
    legacy_anchor: LegacyAnchor
    snapshot_digest: Digest

    @model_validator(mode="before")
    @classmethod
    def _raw_finite(self, value: object) -> object:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        assert_finite_floats(value)
        return value

    @model_validator(mode="after")
    def _immutable_binding(self) -> Self:
        assert_finite_floats(self.model_dump(mode="python"))
        value = self.applicant_input
        if self.revision != self.expected_revision + 1:
            raise ValueError("An accepted revision advances the exact requested revision once")
        if self.selected_result_ids != value.selected_result_ids or [item.result_id for item in self.source_reference_digests] != self.selected_result_ids:
            raise ValueError("The receipt binds the full ordered applicant selection")
        if self.accepted_planned_on != self.allocation.planned_on or self.planner_version != self.allocation.planner_version or self.catalogue_version != self.catalogue_snapshot.version:
            raise ValueError("Accepted planner date and versions are immutable bindings")
        if self.allocation.timezone != value.timezone or self.allocation.ordered_exam_choices != value.exam_choices:
            raise ValueError("Allocation must preserve every personal exam choice and timezone")
        if len(self.owned_review_snapshot) != len(value.own_reviews):
            raise ValueError("Every requested own review needs exactly one ordered snapshot")
        for requested, accepted in zip(value.own_reviews, self.owned_review_snapshot, strict=True):
            if requested.ref != accepted.ref or requested.exam != accepted.exam:
                raise ValueError("Owned review snapshots bind the exact request order and exam")
        expected_actions: dict[str, tuple[LessonRef | AttemptReviewRef, Exam, int, bool]] = {
            reference_action_id("ielts_academic" if unit.track == "ielts_reading" else "digital_sat", unit.ref): (unit.ref, "ielts_academic" if unit.track == "ielts_reading" else "digital_sat", 20, unit.available)
            for unit in self.catalogue_snapshot.lessons
            if ("ielts_academic" if unit.track == "ielts_reading" else "digital_sat") in {choice.exam for choice in value.exam_choices}
        }
        for requested, accepted in zip(value.own_reviews, self.owned_review_snapshot, strict=True):
            expected_actions[reference_action_id(requested.exam, requested.ref)] = (requested.ref, requested.exam, requested.planned_minutes, accepted.available)
        all_actions = [*self.allocation.slots, *self.allocation.unallocated]
        if set(expected_actions) != {item.action_id for item in all_actions}:
            raise ValueError("The receipt conserves every selected exact lesson and own review")
        for item in all_actions:
            ref, exam, minutes, available = expected_actions[item.action_id]
            actual_minutes = item.planned_minutes if isinstance(item, DatedSlot) else item.requested_minutes
            if item.ref != ref or item.exam != exam or actual_minutes != minutes:
                raise ValueError("Saved action must preserve its exact requested identity and duration")
            if not available and (isinstance(item, DatedSlot) or item.reason != "version_unavailable"):
                raise ValueError("An unavailable accepted reference cannot gain a dated action")
            if available and isinstance(item, UnallocatedAction) and item.reason == "version_unavailable":
                raise ValueError("An available accepted reference cannot be silently unavailable")
        if any(week.weekly_budget_minutes != value.shared_weekly_minutes for week in self.allocation.capacity):
            raise ValueError("All saved exam streams use the one accepted weekly budget")
        if any(slot.local_date < max(value.starts_on, self.accepted_planned_on) or slot.local_date.weekday() not in value.study_days for slot in self.allocation.slots):
            raise ValueError("Saved dates must remain on the accepted local study days and start")
        if self.allocation_digest != self.allocation.digest or self.allocation_digest != allocation_snapshot_digest(value, self.catalogue_snapshot, self.owned_review_snapshot, self.allocation):
            raise ValueError("The saved allocation must match its exact full frozen digest")
        expected_preview = shared_preview_fingerprint(self.profile_id, value, self.expected_revision, self.legacy_anchor, self.accepted_planned_on, self.source_fingerprint, self.source_reference_digests, self.allocation)
        if self.preview_fingerprint != expected_preview:
            raise ValueError("The receipt binds the exact accepted preview")
        request = SharedRouteWriteV1(applicant_input=value, expected_revision=self.expected_revision, client_write_uuid=self.client_write_uuid, preview_fingerprint=self.preview_fingerprint, source_fingerprint=self.source_fingerprint, legacy_anchor=self.legacy_anchor, planned_on=self.accepted_planned_on)
        if self.canonical_request_digest != shared_request_digest(self.profile_id, request):
            raise ValueError("The receipt binds the original canonical write intent")
        if self.snapshot_digest != _identity_digest(self.model_dump(mode="json", exclude={"snapshot_digest"})):
            raise ValueError("The immutable receipt snapshot digest does not match")
        return self


class CurrentRouteStatusV1(Base):
    as_of: UtcTimestamp
    goal_statuses: list[GoalStatusV1] = Field(min_length=2, max_length=20)
    legacy_structure: Literal["unchanged", "changed", "unknown"]
    imported_refs: Literal["not_used", "unchanged", "changed", "unknown"]
    content_statuses: list[ContentStatusV1] = Field(max_length=409)
    preparation_access: Literal["active", "expired", "unknown"]
    needs_review: bool = Field(strict=True)
    review_reasons: list[ReviewReasonV1]

    @model_validator(mode="after")
    def _status_reasons(self) -> Self:
        if len({goal.result_id for goal in self.goal_statuses}) != len(self.goal_statuses) or len({item.action_id for item in self.content_statuses}) != len(self.content_statuses):
            raise ValueError("Each saved goal and action receives exactly one current status")
        reasons: list[ReviewReasonV1] = []
        goal_codes: dict[GoalReason, ReviewCode] = {
            "decision_changed": "goal_decision_changed",
            "result_unavailable": "goal_result_unavailable",
            "research_locked": "goal_research_locked",
            "source_changed": "goal_source_changed",
            "evidence_unknown": "goal_evidence_unknown",
        }
        for goal in self.goal_statuses:
            if goal.safe_reason_code is not None:
                reasons.append(ReviewReasonV1(code=goal_codes[goal.safe_reason_code], result_id=goal.result_id))
        legacy_codes: dict[Literal["changed", "unknown"], ReviewCode] = {
            "changed": "legacy_structure_changed",
            "unknown": "legacy_structure_unknown",
        }
        if self.legacy_structure != "unchanged":
            reasons.append(ReviewReasonV1(code=legacy_codes[self.legacy_structure]))
        imported_codes: dict[Literal["changed", "unknown"], ReviewCode] = {
            "changed": "imported_refs_changed",
            "unknown": "imported_refs_unknown",
        }
        if self.imported_refs in {"changed", "unknown"}:
            reasons.append(ReviewReasonV1(code=imported_codes[self.imported_refs]))
        content_codes: dict[ContentState, ReviewCode] = {
            "version_unavailable": "content_version_unavailable",
            "review_unavailable": "own_review_unavailable",
            "unknown": "content_unknown",
            "available": "content_unknown",
        }
        for item in self.content_statuses:
            if item.state != "available":
                reasons.append(ReviewReasonV1(code=content_codes[item.state], action_id=item.action_id))
        if self.review_reasons != reasons or self.needs_review != bool(reasons):
            raise ValueError("Current review reasons derive from ordered safe statuses only")
        return self


class SharedRouteViewV1(Base):
    receipt: SharedRouteWriteReceiptV1
    current_status: CurrentRouteStatusV1
    visible_evidence: list[PreparationGraph] = Field(max_length=20)

    @model_validator(mode="before")
    @classmethod
    def _finite_view(self, value: object) -> object:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        if isinstance(value, dict):
            for graph in value.get("visible_evidence", []):
                assert_finite_floats(graph.model_dump(mode="python") if isinstance(graph, BaseModel) else graph)
        return value

    @model_validator(mode="after")
    def _owned_current_slices(self) -> Self:
        if [goal.result_id for goal in self.current_status.goal_statuses] != self.receipt.selected_result_ids:
            raise ValueError("Current goal statuses preserve the immutable selection order")
        actions = [*self.receipt.allocation.slots, *self.receipt.allocation.unallocated]
        if [item.action_id for item in self.current_status.content_statuses] != [item.action_id for item in actions]:
            raise ValueError("Current action status preserves each accepted exact action")
        states = {goal.result_id: goal.state for goal in self.current_status.goal_statuses}
        visible_ids = []
        for graph in self.visible_evidence:
            assert_finite_floats(graph.model_dump(mode="python"))
            if graph.profile_id != self.receipt.profile_id or len(graph.selected_result_ids) != 1:
                raise ValueError("Visible evidence must be a current singleton of the owned profile")
            result_id = graph.selected_result_ids[0]
            if states.get(result_id) not in {"eligible", "source_changed", "evidence_unknown"} or not graph.programmes[0].research_access:
                raise ValueError("A current evidence slice cannot reveal an unavailable or locked goal")
            visible_ids.append(result_id)
        if visible_ids != [result_id for result_id in self.receipt.selected_result_ids if result_id in visible_ids] or len(set(visible_ids)) != len(visible_ids):
            raise ValueError("Current singleton evidence preserves selected order and identity")
        if any(goal.state == "research_locked" for goal in self.current_status.goal_statuses) and self.visible_evidence:
            raise ValueError("A final observed research lock clears every premium evidence slice")
        return self


class SharedRouteCurrentOutV1(Base):
    profile_id: ResultId
    revision: int = Field(ge=0, le=2147483647, strict=True)
    view: SharedRouteViewV1 | None

    @model_validator(mode="after")
    def _current_pointer(self) -> Self:
        if self.view is None:
            if self.revision != 0:
                raise ValueError("An absent shared route has revision zero")
        elif self.view.receipt.profile_id != self.profile_id or self.view.receipt.revision != self.revision:
            raise ValueError("The current pointer must match its immutable owned receipt")
        return self
