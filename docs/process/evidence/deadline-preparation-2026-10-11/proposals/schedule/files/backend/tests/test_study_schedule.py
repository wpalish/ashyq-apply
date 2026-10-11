"""Finite synthetic planner controls: no database, network or official score prediction."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

import pytest
from app.domain.study_schedule import build_schedule
from app.schemas.study_schedule import (
    GeneratedSchedule,
    ScheduleSettings,
    ScheduleTask,
    ScheduleWrite,
)
from pydantic import ValidationError


def settings(**changes: Any) -> ScheduleSettings:
    values: dict[str, Any] = {
        "exam": "ielts_academic",
        "starts_on": "2026-10-12",
        "certificate_deadline": "2026-11-30",
        "first_exam_on": "2026-11-17",
        "result_wait_days": 7,
        "delivery_days": 2,
        "safety_days": 3,
        "timezone": "Asia/Almaty",
        "weekly_minutes": 180,
        "study_days": [0, 2, 4],
        "target_scores": {
            "overall": 7,
            "listening": 7,
            "reading": 7,
            "writing": 6.5,
            "speaking": 6.5,
        },
        "baseline_scores": {
            "overall": 6,
            "listening": 6,
            "reading": 6,
            "writing": 5.5,
            "speaking": 6,
        },
        "baseline_on": "2026-10-10",
        "confirmed_planning_dates": True,
    }
    values.update(changes)
    return ScheduleSettings.model_validate(values)


def study(schedule: GeneratedSchedule) -> list[ScheduleTask]:
    return [task for task in schedule.tasks if task.minutes > 0]


def sat(**changes: Any) -> ScheduleSettings:
    return settings(
        exam="digital_sat",
        target_scores={"total": 1400, "math": 720, "reading_writing": 700},
        baseline_scores={"total": 1250, "math": 650, "reading_writing": 600},
        **changes,
    )


def test_backwards_boundary_and_forward_events_are_exact_entered_buffers() -> None:
    plan = build_schedule(settings(), today=date(2026, 10, 11))
    assert plan.latest_exam_on == date(2026, 11, 17)
    assert plan.latest_safe_exam_on == date(2026, 11, 18)
    assert plan.result_expected_on == date(2026, 11, 24)
    assert plan.delivery_expected_on == date(2026, 11, 26)
    assert plan.timing == "within_entered_buffers"
    assert plan.readiness == "not_assessed"
    assert any("applicant-entered" in text for text in plan.warnings)
    assert any("recipient receipt" in text for text in plan.warnings)


def test_retake_risk_retains_late_events_and_focused_review() -> None:
    plan = build_schedule(
        settings(retake_on="2026-11-25", study_days=list(range(7))), today=date(2026, 10, 11)
    )
    assert plan.latest_exam_on == date(2026, 11, 25)
    assert plan.timing == "at_risk"
    assert plan.result_expected_on == date(2026, 12, 2)
    assert plan.delivery_expected_on == date(2026, 12, 4)
    assert any(task.due_on == date(2026, 12, 7) and "safety" in task.title for task in plan.tasks)
    assert len([task for task in plan.tasks if task.kind == "exam"]) == 2
    assert all(task.due_on not in {date(2026, 11, 17), date(2026, 11, 25)} for task in study(plan))
    assert any(
        date(2026, 11, 17) < task.due_on < date(2026, 11, 25) and task.kind == "review"
        for task in study(plan)
    )


def test_no_retake_is_invented() -> None:
    plan = build_schedule(settings(), today=date(2026, 10, 11))
    assert len([task for task in plan.tasks if task.kind == "exam"]) == 1
    assert not any("retake-exam" in task.id for task in plan.tasks)
    assert not any(task.due_on > date(2026, 11, 17) for task in study(plan))


@pytest.mark.parametrize(
    "budget,days", [(30, list(range(7))), (130, [0, 2, 4]), (1260, [0]), (1260, list(range(7)))]
)
def test_integer_shared_weekly_budget_and_daily_cap_across_both_exam_phases(
    budget: int, days: list[int]
) -> None:
    config = settings(weekly_minutes=budget, study_days=days, retake_on="2026-11-25")
    plan = build_schedule(config, today=date(2026, 10, 11))
    totals: dict[date, int] = defaultdict(int)
    dates = []
    for task in study(plan):
        assert task.due_on.weekday() in days
        assert task.due_on not in {config.first_exam_on, config.retake_on}
        assert isinstance(task.minutes, int) and 0 < task.minutes <= 180
        totals[task.due_on - timedelta(days=task.due_on.weekday())] += task.minutes
        dates.append(task.due_on)
    assert all(value <= budget for value in totals.values())
    assert len(dates) == len(set(dates))
    assert len(plan.tasks) <= 400


def test_missing_component_diagnostic_does_not_infer_it_from_overall() -> None:
    plan = build_schedule(settings(baseline_scores={"overall": 7}), today=date(2026, 10, 11))
    assert plan.diagnostic_required
    assert study(plan)[0].kind == "diagnostic"
    assert {task.skill for task in study(plan) if task.skill} == {
        "listening",
        "reading",
        "writing",
        "speaking",
    }
    assert any("baseline is missing" in text and "writing" in text for text in plan.warnings)
    assert plan.readiness == "not_assessed"


def test_weak_components_get_priority_without_starving_other_ielts_skills() -> None:
    plan = build_schedule(
        settings(
            baseline_scores={
                "overall": 6,
                "listening": 6,
                "reading": 6.5,
                "writing": 4,
                "speaking": 6.5,
            }
        ),
        today=date(2026, 10, 11),
    )
    skill_tasks = [task for task in study(plan) if task.skill]
    counts = Counter(task.skill for task in skill_tasks)
    assert skill_tasks[0].skill == "writing"
    assert set(counts) == {"listening", "reading", "writing", "speaking"}
    assert counts["writing"] > counts["speaking"]
    assert any("overall 6 to 7" in text and "writing 4 to 6.5" in text for text in plan.warnings)


def test_starter_links_are_once_and_never_substitute_other_components_or_mocks() -> None:
    ielts = build_schedule(settings(), today=date(2026, 10, 11))
    linked = [task for task in ielts.tasks if task.lesson_id]
    assert len(linked) == 1 and linked[0].lesson_id == "ielts-reading-1"
    assert linked[0].skill == "reading" and linked[0].kind == "skill"
    assert any("Listening, Writing and Speaking require" in text for text in ielts.warnings)
    digital = build_schedule(sat(), today=date(2026, 10, 11))
    assert Counter(task.lesson_id for task in digital.tasks if task.lesson_id) == {
        "sat-math-1": 1,
        "sat-rw-1": 1,
    }
    assert all(task.lesson_id is None for task in digital.tasks if task.kind == "mock")


def test_mock_needs_full_reserved_block_and_preserves_component_coverage() -> None:
    small = build_schedule(sat(), today=date(2026, 10, 11))
    assert not any(task.kind == "mock" for task in small.tasks)
    assert any("No full-format external mock fits" in text for text in small.warnings)
    large = build_schedule(sat(weekly_minutes=540), today=date(2026, 10, 11))
    mocks = [task for task in large.tasks if task.kind == "mock"]
    assert mocks and all(task.minutes == 180 and task.lesson_id is None for task in mocks)
    assert {task.skill for task in study(large) if task.skill} == {"math", "reading_writing"}


def test_baseline_at_target_does_not_assess_readiness() -> None:
    config = sat()
    config = ScheduleSettings.model_validate(
        {**config.model_dump(), "baseline_scores": config.target_scores | {"total": 1420}}
    )
    plan = build_schedule(config, today=date(2026, 10, 11))
    assert plan.readiness == "not_assessed"
    assert plan.study_minutes_remaining > 0


def test_advancing_today_retains_calendar_ids_past_tasks_and_completion() -> None:
    config = settings()
    before = build_schedule(config, today=date(2026, 10, 11))
    first = study(before)[0]
    completed = ScheduleSettings.model_validate(
        {**config.model_dump(), "completed_task_ids": [first.id]}
    )
    after = build_schedule(completed, today=date(2026, 10, 26))
    assert [task.id for task in before.tasks] == [task.id for task in after.tasks]
    same = next(task for task in after.tasks if task.id == first.id)
    assert same.completed and not same.overdue
    assert any(task.overdue and task.due_on < date(2026, 10, 26) for task in study(after))
    remaining = [
        task for task in study(after) if not task.completed and task.due_on >= date(2026, 10, 26)
    ]
    assert after.study_minutes_remaining == sum(task.minutes for task in remaining)
    assert after.remaining_study_days == len(remaining)


def test_baseline_aging_changes_diagnostic_flag_without_rewriting_calendar() -> None:
    before = build_schedule(settings(), today=date(2026, 11, 9))
    after = build_schedule(settings(), today=date(2026, 11, 10))
    assert not before.diagnostic_required and after.diagnostic_required
    assert [task.model_dump(exclude={"overdue", "completed"}) for task in before.tasks] == [
        task.model_dump(exclude={"overdue", "completed"}) for task in after.tasks
    ]
    assert any(
        task.kind == "diagnostic" and task.due_on == date(2026, 11, 11) for task in after.tasks
    )
    assert any("more than 30 days" in text for text in after.warnings)


def test_baseline_progress_after_start_is_allowed_but_future_baseline_is_not() -> None:
    config = settings(baseline_on="2026-10-20")
    assert build_schedule(config, today=date(2026, 10, 21)).as_of == date(2026, 10, 21)
    with pytest.raises(ValueError, match="baseline_on cannot be after today"):
        build_schedule(config, today=date(2026, 10, 19))


def test_unknown_and_structurally_changed_completion_ids_are_rejected() -> None:
    config = settings()
    first = study(build_schedule(config, today=date(2026, 10, 11)))[0]
    with pytest.raises(ValueError, match="completion IDs"):
        build_schedule(
            settings(completed_task_ids=["unrelated-case-task"]), today=date(2026, 10, 11)
        )
    with pytest.raises(ValueError, match="completion IDs"):
        build_schedule(
            settings(weekly_minutes=210, completed_task_ids=[first.id]), today=date(2026, 10, 11)
        )


def test_past_deadline_preserves_all_events_and_exposes_overdue_work() -> None:
    plan = build_schedule(settings(), today=date(2026, 12, 5))
    assert plan.timing == "deadline_passed"
    assert plan.study_minutes_remaining == 0 and plan.remaining_study_days == 0
    assert plan.tasks and all(task.overdue for task in plan.tasks)
    assert any(task.kind == "submit" and task.due_on == date(2026, 11, 30) for task in plan.tasks)


def test_zero_study_window_warns_without_inventing_exam_day_work() -> None:
    plan = build_schedule(settings(first_exam_on="2026-10-12"), today=date(2026, 10, 11))
    assert not study(plan)
    assert any("Insufficient future study slots" in text for text in plan.warnings)
    assert plan.readiness == "not_assessed"


def test_365_day_horizon_and_maximum_buffers_keep_bounded_complete_response() -> None:
    config = settings(
        starts_on="2026-01-01",
        first_exam_on="2026-12-31",
        certificate_deadline="2027-01-01",
        baseline_on="2026-01-01",
        weekly_minutes=1260,
        study_days=list(range(7)),
        result_wait_days=60,
        delivery_days=30,
        safety_days=30,
    )
    plan = build_schedule(config, today=date(2026, 1, 1))
    assert len(plan.tasks) <= 400
    assert len(study(plan)) <= 365
    assert plan.timing == "at_risk"
    assert plan.delivery_expected_on > config.certificate_deadline
    assert any(task.due_on > config.certificate_deadline for task in plan.tasks)


@pytest.mark.parametrize(
    "changes",
    [
        {"target_scores": {"overall": 7}},
        {
            "target_scores": {
                "overall": 7,
                "listening": 7,
                "reading": 7,
                "writing": 6.25,
                "speaking": 6.5,
            }
        },
        {
            "target_scores": {
                "overall": float("nan"),
                "listening": 7,
                "reading": 7,
                "writing": 6.5,
                "speaking": 6.5,
            }
        },
        {
            "target_scores": {
                "overall": True,
                "listening": 7,
                "reading": 7,
                "writing": 6.5,
                "speaking": 6.5,
            }
        },
        {"baseline_scores": {"invented": 6}},
        {"baseline_scores": {}, "baseline_on": "2026-10-10"},
        {"baseline_on": None},
        {"study_days": [0, 0]},
        {"study_days": [True]},
        {"study_days": [7]},
        {"timezone": "Not/A_Zone"},
        {"confirmed_planning_dates": 1},
        {"result_wait_days": 0},
        {"result_wait_days": 61},
        {"delivery_days": 31},
        {"safety_days": -1},
        {"weekly_minutes": 29},
        {"weekly_minutes": 1261},
        {"retake_on": "2026-11-17"},
        {"certificate_deadline": "2027-10-13"},
        {"completed_task_ids": [""]},
        {"completed_task_ids": ["x" * 161]},
        {"completed_task_ids": ["x", "x"]},
        {"completed_task_ids": [str(index) for index in range(401)]},
    ],
)
def test_invalid_or_unbounded_planning_settings_fail_validation(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        settings(**changes)


@pytest.mark.parametrize(
    "target,baseline",
    [
        (
            {"total": 1400, "math": 600, "reading_writing": 600},
            {"total": 1250, "math": 650, "reading_writing": 600},
        ),
        (
            {"total": 1400.5, "math": 720, "reading_writing": 700},
            {"total": 1250, "math": 650, "reading_writing": 600},
        ),
        (
            {"total": 1400, "math": 720, "reading_writing": 700},
            {"total": 1260, "math": 650, "reading_writing": 600},
        ),
    ],
)
def test_sat_goal_and_complete_baseline_arithmetic_are_validated(
    target: dict[str, float], baseline: dict[str, float]
) -> None:
    with pytest.raises(ValidationError):
        settings(exam="digital_sat", target_scores=target, baseline_scores=baseline)


@pytest.mark.parametrize("revision", [-1, 2147483647, True])
def test_revision_cannot_overflow_next_database_integer(revision: int) -> None:
    with pytest.raises(ValidationError):
        ScheduleWrite(expected_revision=revision, settings=settings())


@pytest.mark.parametrize(
    "start,exam,deadline",
    [("0001-01-01", "0001-01-01", "0001-01-02"), ("9999-12-01", "9999-12-30", "9999-12-31")],
)
def test_calendar_overflow_fails_validation_before_builder(
    start: str, exam: str, deadline: str
) -> None:
    with pytest.raises(ValidationError, match="supported calendar"):
        settings(
            starts_on=start, first_exam_on=exam, certificate_deadline=deadline, result_wait_days=60
        )
