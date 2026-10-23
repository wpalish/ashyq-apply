"""Pure projection onto existing, budgeted slots; no scores, network or DB writes."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date

from app.domain.study_schedule import build_schedule
from app.schemas.learning_schedule import (
    AssessmentRef,
    LearningPathDraft,
    LearningPathSettings,
    LearningSchedule,
    LearningTask,
    LearningUnit,
)
from app.schemas.study_schedule import ScheduleSettings


def settings_fingerprint(settings: ScheduleSettings) -> str:
    values = settings.model_dump(mode="json", exclude={"completed_task_ids"})
    values["study_days"] = sorted(settings.study_days)
    return fingerprint(values)


def fingerprint(values: object) -> str:
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_learning_schedule(plan: LearningPathSettings, *, today: date) -> LearningSchedule:
    original = build_schedule(plan.schedule_settings, today=today)
    identity = fingerprint(plan.model_dump(mode="json"))[:20]
    units: dict[str, list[LearningUnit]] = defaultdict(list)
    for unit in plan.lessons:
        units[unit.skill].append(unit)
    spent: dict[str, int] = defaultdict(int)
    reviews = {ref.lesson_id: ref for ref in plan.reviews}
    review_indexes: dict[str, int] = defaultdict(int)
    indexes: dict[str, int] = defaultdict(int)
    last_unit: dict[str, LearningUnit] = {}
    tasks = []
    for slot in original.tasks:
        task = LearningTask.model_validate(slot.model_dump())
        task.id = slot.id.replace("schedule-v1:", "schedule-v2:").replace(
            slot.id.split(":")[1], identity, 1
        )
        task.lesson_id = None
        task.completed = False  # v1 self-ticks never become v2 assessed completion.
        task.overdue = slot.due_on < today
        if slot.kind in {"diagnostic", "mock"}:
            task.learning_ref = AssessmentRef(
                id=f"{slot.kind}:{plan.schedule_settings.exam}", version="unimplemented-v1"
            )
            task.unavailable_reason = "not_implemented"
        elif slot.minutes and slot.skill in units:
            skill = slot.skill
            available = units[skill]
            index = indexes[skill]
            if index < len(available):
                unit = available[index]
                task.learning_ref = unit.ref
                task.kind = "skill"
                task.title = unit.title
                task.availability = "available"
                spent[unit.ref.id] += slot.minutes
                last_unit[skill] = unit
                if spent[unit.ref.id] >= unit.planned_minutes:
                    indexes[skill] += 1
            else:
                review_units = [
                    candidate for candidate in available if candidate.ref.lesson_id in reviews
                ]
                unit = (
                    review_units[review_indexes[skill] % len(review_units)]
                    if review_units
                    else last_unit[skill]
                )
                review_indexes[skill] += 1
                task.title = f"Review saved work: {unit.title}"
                task.kind = "review"
                task.learning_ref = reviews.get(unit.ref.lesson_id)
                if task.learning_ref:
                    task.availability = "available"
                else:
                    task.unavailable_reason = "attempt_required"
        else:
            task.unavailable_reason = "no_local_content" if slot.minutes else None
        tasks.append(task)
    unallocated = [
        unit.ref.lesson_id for unit in plan.lessons if spent[unit.ref.id] < unit.planned_minutes
    ]
    scheduled = {task.learning_ref.id for task in tasks if task.learning_ref}
    unallocated_reviews = [ref.id for ref in plan.reviews if ref.id not in scheduled]
    warnings = [
        *original.warnings,
        "Each unit has a minimum 20-minute planning allocation across its dated slots, not a learning-time or score-growth promise. Saved submissions are separate from reported activity and mastery.",
        "Review references are pinned on explicit preview/save; a new attempt does not automatically rebuild this calendar.",
    ]
    if unallocated:
        warnings.append(
            "Some practice units do not fit the entered dates and workload; unallocated work remains visible."
        )
    if unallocated_reviews:
        warnings.append(
            "Some selected saved reviews have no dated slot within this plan; they remain accessible in your own history."
        )
    return LearningSchedule(
        **original.model_dump(exclude={"tasks", "warnings"}),
        tasks=tasks,
        warnings=warnings,
        unallocated_lesson_ids=unallocated,
        unallocated_review_ids=unallocated_reviews,
    )


def draft_for(plan: LearningPathSettings, *, today: date) -> LearningPathDraft:
    schedule = build_learning_schedule(plan, today=today)
    return LearningPathDraft(
        plan=plan, planned_on=today, fingerprint=fingerprint(schedule.model_dump(mode="json"))
    )
