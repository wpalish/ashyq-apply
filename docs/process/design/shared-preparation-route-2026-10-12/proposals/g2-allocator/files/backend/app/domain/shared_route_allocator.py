"""Finite whole-unit personal allocation over caller-validated exact references."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.schemas.learning_schedule import AttemptReviewRef, LessonRef
from app.schemas.shared_route import (
    PLANNER_VERSION,
    DatedSlot,
    ExamTiming,
    FrozenExactCatalogue,
    SharedAllocationV1,
    SharedRouteInputV1,
    TimingState,
    UnallocatedAction,
    UnallocatedReason,
    ValidatedOwnedReviewV1,
    WeekCapacity,
    reference_action_id,
    reference_occurrence_id,
)
from app.schemas.study_schedule import MAX_DAILY_MINUTES, Exam


def _digest(value: object) -> str:
    wire = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def canonical_input(value: SharedRouteInputV1) -> dict:
    """Keep user array/partial-target intent; weekdays alone have set semantics."""
    checked = SharedRouteInputV1.model_validate(value.model_dump(mode="python"))
    values = checked.model_dump(mode="json")
    values["study_days"] = sorted(checked.study_days)
    return values


def action_id(exam: Exam, ref: LessonRef | AttemptReviewRef) -> str:
    """Content and own receipt identity; programmes and dates are not identity."""
    return reference_action_id(exam, ref)


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


@dataclass(frozen=True)
class _Action:
    action_id: str
    ref: LessonRef | AttemptReviewRef
    exam: Exam
    minutes: int
    window_end: date
    available: bool

    def unallocated(self, reason: UnallocatedReason) -> UnallocatedAction:
        return UnallocatedAction(
            action_id=self.action_id,
            ref=self.ref,
            exam=self.exam,
            requested_minutes=self.minutes,
            reason=reason,
        )


def _review_map(
    value: SharedRouteInputV1,
    catalogue: FrozenExactCatalogue,
    supplied: Sequence[ValidatedOwnedReviewV1],
) -> dict:
    reviews = [
        ValidatedOwnedReviewV1.model_validate(item.model_dump(mode="python")) for item in supplied
    ]
    by_uuid = {review.ref.attempt_id: review for review in reviews}
    if len(by_uuid) != len(reviews) or set(by_uuid) != {
        requested.ref.attempt_id for requested in value.own_reviews
    }:
        raise ValueError("Supply one upstream-validated exact own review for each requested UUID")
    current_exams = {
        (unit.ref.lesson_id, unit.ref.content_version): (
            "ielts_academic" if unit.track == "ielts_reading" else "digital_sat"
        )
        for unit in catalogue.lessons
    }
    for requested in value.own_reviews:
        accepted = by_uuid[requested.ref.attempt_id]
        if accepted.ref != requested.ref or accepted.exam != requested.exam:
            raise ValueError("Owned review UUID, exact lesson/version and validated exam must agree")
        known_exam = current_exams.get((requested.ref.lesson_id, requested.ref.content_version))
        if known_exam is not None and known_exam != accepted.exam:
            raise ValueError("A current exact review must retain its known lesson track/exam")
    return by_uuid


def _exam_refs(catalogue: FrozenExactCatalogue, exam: Exam) -> list[LessonRef]:
    if exam == "ielts_academic":
        return [unit.ref for unit in catalogue.lessons if unit.track == "ielts_reading"]
    math_refs = [unit.ref for unit in catalogue.lessons if unit.track == "sat_math"]
    rw_refs = [unit.ref for unit in catalogue.lessons if unit.track == "sat_reading_writing"]
    refs = []
    for index in range(max(len(math_refs), len(rw_refs))):
        for track in (math_refs, rw_refs):
            if index < len(track):
                refs.append(track[index])
    return refs


def _actions(
    value: SharedRouteInputV1, catalogue: FrozenExactCatalogue, reviews: dict
) -> list[list[_Action]]:
    availability = {(unit.ref.lesson_id, unit.ref.content_version): unit.available for unit in catalogue.lessons}
    streams = []
    for choice in value.exam_choices:
        refs = _exam_refs(catalogue, choice.exam)
        current = {(ref.lesson_id, ref.content_version) for ref in refs}
        own = [review for review in value.own_reviews if review.exam == choice.exam]
        units = []
        for ref in refs:
            units.append(
                _Action(action_id(choice.exam, ref), ref, choice.exam, 20, choice.first_exam_on,
                        availability[(ref.lesson_id, ref.content_version)])
            )
            for selected in own:
                if (selected.ref.lesson_id, selected.ref.content_version) == (
                    ref.lesson_id, ref.content_version
                ):
                    units.append(
                        _Action(action_id(choice.exam, selected.ref), selected.ref, choice.exam,
                                selected.planned_minutes, choice.retake_on or choice.first_exam_on,
                                reviews[selected.ref.attempt_id].available)
                    )
        for selected in own:
            if (selected.ref.lesson_id, selected.ref.content_version) not in current:
                units.append(
                    _Action(action_id(choice.exam, selected.ref), selected.ref, choice.exam,
                            selected.planned_minutes, choice.retake_on or choice.first_exam_on,
                            reviews[selected.ref.attempt_id].available)
                )
        streams.append(units)
    return streams


def _dates(value: SharedRouteInputV1, start: date, end: date) -> list[date]:
    exam_days = {choice.first_exam_on for choice in value.exam_choices} | {
        choice.retake_on for choice in value.exam_choices if choice.retake_on is not None
    }
    days = []
    cursor = start
    while cursor < end:
        if cursor.weekday() in value.study_days and cursor not in exam_days:
            days.append(cursor)
        # end is an exclusive, validated date. At most date.max is reached;
        # no iteration ever increments date.max itself.
        cursor += timedelta(days=1)
    return days


def _drain(
    stream: deque[_Action], day: date, unallocated: list[UnallocatedAction]
) -> None:
    while stream and stream[0].window_end <= day:
        unallocated.append(stream.popleft().unallocated("window_elapsed"))


def _timing(value: SharedRouteInputV1, planned_on: date) -> list[ExamTiming]:
    timings = []
    for choice in value.exam_choices:
        days = choice.result_wait_days + choice.delivery_days + choice.safety_days
        safe = choice.certificate_deadline - timedelta(days=days)
        latest_buffered = (choice.retake_on or choice.first_exam_on) + timedelta(days=days)
        timing: TimingState = (
            "deadline_passed" if planned_on > choice.certificate_deadline else
            "at_risk" if latest_buffered > choice.certificate_deadline else "within_buffers"
        )
        timings.append(
            ExamTiming(
                exam=choice.exam,
                first_exam_on=choice.first_exam_on,
                retake_on=choice.retake_on,
                certificate_deadline=choice.certificate_deadline,
                result_wait_days=choice.result_wait_days,
                delivery_days=choice.delivery_days,
                safety_days=choice.safety_days,
                latest_safe_exam_on=safe,
                timing=timing,
            )
        )
    return timings


def allocate_shared_v1(
    value: SharedRouteInputV1,
    *,
    catalogue: FrozenExactCatalogue,
    own_reviews: Sequence[ValidatedOwnedReviewV1],
    planned_on: date,
) -> SharedAllocationV1:
    """Allocate personal practice without consulting clocks, DB or any resolver.

    Upstream supplies exact owned receipt availability and a trusted historical
    exam association. A review receipt with lesson=None can still be available.
    Unknown historical association must be rejected upstream, never guessed here.
    """
    if type(planned_on) is not date:
        raise ValueError("planned_on must be an explicitly supplied local date")
    # Python snapshots preserve nonfinite numbers for validators, unlike a JSON
    # conversion. Revalidation/copy also isolates inherited mutable ref/list DTOs.
    value = SharedRouteInputV1.model_validate(value.model_dump(mode="python"))
    catalogue = FrozenExactCatalogue.model_validate(catalogue.model_dump(mode="python"))
    reviews = _review_map(value, catalogue, own_reviews)
    original = _actions(value, catalogue, reviews)
    order = {unit.action_id: index for index, unit in enumerate(unit for stream in original for unit in stream)}
    unallocated: list[UnallocatedAction] = []
    streams: list[deque[_Action]] = []
    for original_stream in original:
        stream: deque[_Action] = deque()
        for unit in original_stream:
            reason: UnallocatedReason | None = (
                "version_unavailable" if not unit.available else
                "too_long_for_day" if unit.minutes > MAX_DAILY_MINUTES else
                "too_long_for_week" if unit.minutes > value.shared_weekly_minutes else None
            )
            if reason is not None:
                unallocated.append(unit.unallocated(reason))
            else:
                stream.append(unit)
        streams.append(stream)
    start = max(value.starts_on, planned_on)
    end = max((unit.window_end for stream in streams for unit in stream), default=start)
    dates = _dates(value, start, end)
    week_keys = sorted({_monday(day) for day in dates})
    spent = {week: 0 for week in week_keys}
    slots: list[DatedSlot] = []
    cursor = 0
    boundary = start
    for day in dates:
        boundary = day
        monday = _monday(day)
        daily_spent = 0
        # Drain on every actual date, including a day with no remaining budget.
        for stream in streams:
            _drain(stream, day, unallocated)
        while len(slots) < 400:
            placed = False
            for offset in range(len(streams)):
                index = (cursor + offset) % len(streams)
                stream = streams[index]
                _drain(stream, day, unallocated)
                if not stream:
                    continue
                unit = stream[0]
                if unit.minutes > min(
                    MAX_DAILY_MINUTES - daily_spent, value.shared_weekly_minutes - spent[monday]
                ):
                    continue
                stream.popleft()
                slots.append(
                    DatedSlot(
                        occurrence_id=reference_occurrence_id(unit.action_id, day),
                        action_id=unit.action_id,
                        ref=unit.ref,
                        exam=unit.exam,
                        kind=unit.ref.kind,
                        local_date=day,
                        planned_minutes=unit.minutes,
                    )
                )
                daily_spent += unit.minutes
                spent[monday] += unit.minutes
                cursor = (index + 1) % len(streams)
                placed = True
                break
            if not placed:
                break
        if len(slots) == 400:
            break
    for stream in streams:
        _drain(stream, boundary, unallocated)
        for unit in stream:
            remaining_reason: UnallocatedReason = (
                "window_elapsed" if unit.window_end <= boundary else
                "slot_limit" if len(slots) == 400 else "insufficient_capacity"
            )
            unallocated.append(unit.unallocated(remaining_reason))
    selected = {choice.exam for choice in value.exam_choices}
    allocation = SharedAllocationV1(
        planner_version=PLANNER_VERSION,
        planned_on=planned_on,
        timezone=value.timezone,
        ordered_exam_choices=value.exam_choices,
        lessons=[
            unit.ref for unit in catalogue.lessons
            if ("ielts_academic" if unit.track == "ielts_reading" else "digital_sat") in selected
        ],
        slots=slots,
        capacity=[
            WeekCapacity(iso_week_monday=week, weekly_budget_minutes=value.shared_weekly_minutes,
                         allocated_minutes=spent[week], remaining_minutes=value.shared_weekly_minutes - spent[week])
            for week in week_keys
        ],
        unallocated=sorted(unallocated, key=lambda item: order[item.action_id]),
        exam_timing=_timing(value, planned_on),
        digest="0" * 64,
    )
    digest = _digest({
        "input": canonical_input(value),
        "catalogue": catalogue.model_dump(mode="json"),
        "owned_review_availability": [
            reviews[item.ref.attempt_id].model_dump(mode="json") for item in value.own_reviews
        ],
        "allocation": allocation.model_dump(mode="json", exclude={"digest"}),
    })
    return allocation.model_copy(update={"digest": digest})
