"""Pure finite calendar planning; no evidence changes or score/readiness forecast."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta

from app.schemas.study_schedule import (
    IELTS_KEYS,
    MAX_DAILY_MINUTES,
    SAT_KEYS,
    GeneratedSchedule,
    ScheduleSettings,
    ScheduleTask,
    TaskKind,
)

_IELTS_SKILLS = ("listening", "reading", "writing", "speaking")
_SAT_SKILLS = ("math", "reading_writing")
_LESSONS = {
    ("ielts_academic", "reading"): "ielts-reading-1",
    ("digital_sat", "math"): "sat-math-1",
    ("digital_sat", "reading_writing"): "sat-rw-1",
}
_STUDY_KINDS = frozenset({"diagnostic", "skill", "review", "timed_practice", "mock"})


def _deficit(settings: ScheduleSettings, skill: str) -> float:
    if skill not in settings.baseline_scores:
        return 1.0
    width = 9 if settings.exam == "ielts_academic" else 600
    return min(
        1.0, max(0.0, (settings.target_scores[skill] - settings.baseline_scores[skill]) / width)
    )


def build_schedule(settings: ScheduleSettings, *, today: date) -> GeneratedSchedule:
    """Build the original calendar; today changes only status and remaining workload.

    Buffers and dates describe the applicant's plan, not official result delivery.
    Completion is self-reported, never a new test result or admission verdict.
    """
    if settings.baseline_on is not None and settings.baseline_on > today:
        raise ValueError("baseline_on cannot be after today")
    skills = _IELTS_SKILLS if settings.exam == "ielts_academic" else _SAT_SKILLS
    keys = IELTS_KEYS if settings.exam == "ielts_academic" else SAT_KEYS
    missing = sorted(keys - settings.baseline_scores.keys())
    outdated = settings.baseline_on is not None and (today - settings.baseline_on).days > 30
    diagnostic_required = bool(missing) or outdated
    latest = settings.retake_on or settings.first_exam_on
    results = latest + timedelta(days=settings.result_wait_days)
    delivery = results + timedelta(days=settings.delivery_days)
    buffered = delivery + timedelta(days=settings.safety_days)
    latest_safe = settings.certificate_deadline - timedelta(
        days=settings.result_wait_days + settings.delivery_days + settings.safety_days
    )
    timing = (
        "deadline_passed"
        if today > settings.certificate_deadline
        else "at_risk"
        if buffered > settings.certificate_deadline
        else "within_entered_buffers"
    )
    warnings = [
        "Dates, score targets and buffers are applicant-entered planning assumptions, not verified programme requirements or certificate deadlines.",
        "Application closing dates do not establish when exam evidence must be received. Confirm the recipient's evidence deadline, accepted test type and delivery method.",
        "Results available to the student do not prove recipient receipt or processing. Exam dates do not prove a booking, available seat or permitted retake.",
        "Study completion and starter correct/total never establish an official score, readiness or admission eligibility.",
    ]
    if missing:
        warnings.append("Diagnostic required; baseline is missing: " + ", ".join(missing) + ".")
    if outdated:
        warnings.append(
            "The entered baseline is more than 30 days old; reassess skills before relying on its practice priorities."
        )
    gaps = [
        f"{key.replace('_', ' ')} {value:g} to {settings.target_scores[key]:g}"
        for key, value in sorted(settings.baseline_scores.items())
        if value < settings.target_scores[key]
    ]
    if gaps:
        warnings.append(
            "Entered planning gaps: "
            + "; ".join(gaps)
            + ". Time to close these gaps has not been assessed; an overall value cannot establish component readiness."
        )
    if settings.exam == "ielts_academic":
        warnings.append(
            "IELTS Listening, Writing and Speaking require professional feedback or suitable official practice; this catalogue has no starter lesson for those skills."
        )
        warnings.append(
            "IELTS overall and four component targets are separate; no band-growth rate or overall result is predicted."
        )
    if timing == "at_risk":
        warnings.append(
            f"The latest entered exam is later than the buffer-based latest safe planning date {latest_safe.isoformat()}; entered result, delivery and safety buffers overrun the certificate deadline."
        )
    elif timing == "deadline_passed":
        warnings.append(
            "The entered certificate deadline has passed; past tasks and timing events remain visible."
        )
    if settings.retake_on is not None and settings.retake_on <= settings.first_exam_on + timedelta(
        days=settings.result_wait_days
    ):
        warnings.append(
            "The entered retake is no later than expected first results; first-result feedback may not be available to guide it. Confirm retake rules separately."
        )

    # Include past slots. Filtering by today would silently erase incomplete work
    # and invalidate completion IDs when the date advances.
    dates = []
    cursor = settings.starts_on
    exam_days = {settings.first_exam_on, latest}
    while cursor < latest:
        if cursor.weekday() in settings.study_days and cursor not in exam_days:
            dates.append(cursor)
        cursor += timedelta(days=1)
    # Reserve a nominal share per selected weekday. Partial weeks and exam days
    # leave capacity unused rather than cramming it into the remaining day.
    weekdays = sorted(settings.study_days)
    budget = min(settings.weekly_minutes, len(weekdays) * MAX_DAILY_MINUTES)
    quotient, remainder = divmod(budget, len(weekdays))
    shares = {weekday: quotient + (index < remainder) for index, weekday in enumerate(weekdays)}
    allocated = {day: shares[day.weekday()] for day in dates}
    if any(value < 15 for value in allocated.values()):
        warnings.append(
            "Some daily blocks are under 15 minutes; consider fewer chosen days for longer practice or feedback sessions."
        )
    if settings.weekly_minutes > len(settings.study_days) * MAX_DAILY_MINUTES:
        warnings.append(
            "The 180-minute daily planning cap leaves some entered weekly budget unallocated; choose additional days if appropriate."
        )

    # Changing planning structure requires explicit completion reset. Today and
    # self-reported checkmarks are deliberately excluded from this fingerprint.
    structure = settings.model_dump(mode="json", exclude={"completed_task_ids"})
    structure["study_days"] = sorted(structure["study_days"])
    fingerprint = hashlib.sha256(
        json.dumps(structure, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]
    tasks: list[ScheduleTask] = []

    def add(
        day: date,
        token: str,
        kind: TaskKind,
        title: str,
        *,
        skill: str | None = None,
        minutes: int = 0,
        lesson_id: str | None = None,
    ) -> None:
        tasks.append(
            ScheduleTask(
                id=f"schedule-v1:{fingerprint}:{token}:{day.isoformat()}",
                due_on=day,
                title=title,
                kind=kind,
                skill=skill,
                minutes=minutes,
                lesson_id=lesson_id,
            )
        )

    priority = sorted(skills, key=lambda skill: (-_deficit(settings, skill), skills.index(skill)))
    weights = {skill: 1 + math.ceil(4 * _deficit(settings, skill)) for skill in skills}
    counters = {skill: 0 for skill in skills}
    linked: set[str] = set()
    diagnostic_day = dates[0] if dates and missing else None
    if (
        not missing
        and settings.baseline_on is not None
        and (latest - settings.baseline_on).days > 30
    ):
        reassess_on = settings.baseline_on + timedelta(days=31)
        diagnostic_day = next((day for day in dates if day >= reassess_on), None)
    phase_last = {
        phase: max((d for d in dates if (d > settings.first_exam_on) == phase), default=None)
        for phase in (False, True)
    }
    for index, day in enumerate(dates):
        minutes = allocated[day]
        if day == diagnostic_day:
            add(
                day,
                "study-diagnostic",
                "diagnostic",
                "Arrange a component diagnostic and record its dated baseline; starter totals are not official scores",
                minutes=minutes,
            )
            continue
        phase = day > settings.first_exam_on
        if day == phase_last[phase] and minutes == MAX_DAILY_MINUTES and all(counters.values()):
            add(
                day,
                "study-external-mock",
                "mock",
                "External full-format mock: confirm test format, duration and assessor; this is not the starter quiz",
                minutes=minutes,
            )
            continue
        skill = min(
            priority, key=lambda name: (counters[name] / weights[name], priority.index(name))
        )
        counters[skill] += 1
        kind: TaskKind = (
            "review"
            if phase
            else "timed_practice"
            if index % 5 == 4
            else "review"
            if index % 3 == 2
            else "skill"
        )
        label = skill.replace("_", " ").title()
        lesson = _LESSONS.get((settings.exam, skill))
        if not phase and lesson is not None and lesson not in linked:
            linked.add(lesson)
            kind = "skill"
            title = f"{label}: introductory starter, followed by error review; target {settings.target_scores[skill]:g} is a planning goal"
        else:
            lesson = None
            title = f"{label}: {'focused retake review' if phase else kind.replace('_', ' ')} and error log; planning goal {settings.target_scores[skill]:g}"
        add(
            day,
            f"study-{kind}-{skill}",
            kind,
            title,
            skill=skill,
            minutes=minutes,
            lesson_id=lesson,
        )
    if not any(task.kind == "mock" for task in tasks):
        warnings.append(
            "No full-format external mock fits the final daily reserve; arrange an adequately long assessment separately. Timed practice is not a score estimate."
        )

    add(
        settings.first_exam_on,
        "first-exam",
        "exam",
        "First entered exam date; booking and accepted test type must be confirmed",
    )
    if settings.retake_on is not None:
        add(
            settings.retake_on,
            "retake-exam",
            "exam",
            "Entered retake date; permission, booking and any feedback window must be confirmed",
        )
        add(
            settings.first_exam_on + timedelta(days=settings.result_wait_days),
            "first-results",
            "results",
            "First results planning estimate; no certificate or recipient receipt is guaranteed",
        )
    add(
        results,
        "latest-results",
        "results",
        "Latest results planning estimate from entered result buffer",
    )
    add(
        delivery,
        "latest-delivery",
        "delivery",
        "Recipient delivery planning estimate; actual processing must be confirmed",
    )
    add(
        buffered,
        "safety-buffer-end",
        "delivery",
        "Entered safety buffer ends; verify recipient receipt and outstanding conditions",
    )
    add(
        settings.certificate_deadline,
        "evidence-deadline",
        "submit",
        "Applicant-entered certificate deadline; verify actual receipt and submission requirements",
    )

    known = {task.id for task in tasks}
    if not set(settings.completed_task_ids) <= known:
        raise ValueError(
            "Unknown or structurally outdated completion IDs; explicitly clear completion when changing the plan"
        )
    completed = set(settings.completed_task_ids)
    for task in tasks:
        task.completed = task.id in completed
        task.overdue = not task.completed and task.due_on < today
    tasks.sort(key=lambda task: (task.due_on, task.id))
    remaining = [
        task
        for task in tasks
        if task.kind in _STUDY_KINDS
        and task.minutes > 0
        and task.due_on >= today
        and not task.completed
    ]
    if len(remaining) < len(skills) + int(diagnostic_required):
        warnings.append(
            "Insufficient future study slots for a component diagnostic and balanced skill coverage; revise the plan or seek professional advice. Target attainability remains unassessed."
        )
    return GeneratedSchedule(
        as_of=today,
        latest_exam_on=latest,
        latest_safe_exam_on=latest_safe,
        result_expected_on=results,
        delivery_expected_on=delivery,
        study_minutes_remaining=sum(task.minutes for task in remaining),
        remaining_study_days=len(remaining),
        diagnostic_required=diagnostic_required,
        timing=timing,
        warnings=warnings,
        tasks=tasks,
    )
