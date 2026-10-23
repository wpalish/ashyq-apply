"""Exact material bindings within the unchanged legacy timing and workload envelope."""

from collections import defaultdict
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.domain.learning_schedule import build_learning_schedule, draft_for, settings_fingerprint
from app.domain.study_schedule import build_schedule
from app.preparation.catalogue import CONTENT_VERSION
from app.preparation.learning_pack import PACK_VERSION, pack_catalogue
from app.schemas.learning_schedule import (
    AttemptReviewRef,
    LearningPathSettings,
    LearningUnit,
    LessonRef,
)
from tests.test_study_schedule import sat, settings


def plan(config):
    skills = {
        "ielts_reading": "reading",
        "sat_math": "math",
        "sat_reading_writing": "reading_writing",
    }
    tracks = (
        {"ielts_reading"}
        if config.exam == "ielts_academic"
        else {"sat_math", "sat_reading_writing"}
    )
    return LearningPathSettings(
        catalogue_version=PACK_VERSION,
        schedule_settings=config,
        lessons=[
            LearningUnit(
                ref=LessonRef(
                    id=f"lesson:{unit.id}:{unit.version}",
                    lesson_id=unit.id,
                    content_version=unit.version,
                ),
                title=unit.title,
                skill=skills[unit.track_id],
            )
            for unit in pack_catalogue().lessons
            if unit.track_id in tracks
        ],
    )


@pytest.mark.parametrize(
    "config",
    [
        settings(study_days=list(range(7)), weekly_minutes=420),
        sat(study_days=list(range(7)), weekly_minutes=420),
    ],
)
def test_all_exam_units_exact_track_order_with_same_dates_and_shared_time(config):
    original = build_schedule(config, today=date(2026, 10, 12))
    bound = build_learning_schedule(plan(config), today=date(2026, 10, 12))
    assert not bound.unallocated_lesson_ids
    assert [(t.due_on, t.minutes) for t in bound.tasks] == [
        (t.due_on, t.minutes) for t in original.tasks
    ]
    assert bound.readiness == original.readiness == "not_assessed"
    observed = defaultdict(list)
    for task in bound.tasks:
        if isinstance(task.learning_ref, LessonRef):
            ids = observed[task.skill]
            if not ids or ids[-1] != task.learning_ref.lesson_id:
                ids.append(task.learning_ref.lesson_id)
            assert task.kind == "skill"
            assert task.learning_ref.content_version == (
                CONTENT_VERSION
                if task.learning_ref.lesson_id in {"ielts-reading-1", "sat-math-1", "sat-rw-1"}
                else PACK_VERSION
            )
        assert not task.completed and task.id.startswith("schedule-v2:")
    for skill in observed:
        assert observed[skill] == [
            unit.ref.lesson_id for unit in plan(config).lessons if unit.skill == skill
        ]
    assert bound.latest_safe_exam_on == original.latest_safe_exam_on
    if config.exam == "ielts_academic":
        assert all(
            t.availability == "unavailable"
            for t in bound.tasks
            if t.skill in {"listening", "writing", "speaking"}
        )


def test_small_blocks_accumulate_without_cramming_or_claiming_full_coverage():
    config = sat(weekly_minutes=30, study_days=list(range(7)), first_exam_on="2026-10-19")
    bound = build_learning_schedule(plan(config), today=date(2026, 10, 12))
    weeks = defaultdict(int)
    for task in bound.tasks:
        weeks[task.due_on - timedelta(days=task.due_on.weekday())] += task.minutes
        assert task.minutes <= 180
    assert all(minutes <= 30 for minutes in weeks.values())
    assert bound.unallocated_lesson_ids
    assert any("do not fit" in warning for warning in bound.warnings)


def test_early_owned_attempt_is_dated_for_review_even_when_last_unit_is_unsubmitted():
    config = settings(study_days=list(range(7)), weekly_minutes=420)
    learning = plan(config)
    attempt = uuid4()
    ref = AttemptReviewRef(
        id=f"attempt:{attempt}",
        attempt_id=attempt,
        lesson_id="ielts-reading-1",
        content_version=CONTENT_VERSION,
    )
    learning.reviews = [ref]
    bound = build_learning_schedule(learning, today=date(2026, 10, 12))
    reviews = [t for t in bound.tasks if isinstance(t.learning_ref, AttemptReviewRef)]
    assert reviews and all(t.learning_ref == ref and t.kind == "review" for t in reviews)


def test_legacy_ticks_do_not_change_v1_fingerprint_or_import_into_new_plan():
    config = settings()
    before = build_schedule(config, today=date(2026, 10, 12)).model_dump(mode="json")
    marked = config.model_copy(deep=True, update={"completed_task_ids": [before["tasks"][0]["id"]]})
    assert settings_fingerprint(config) == settings_fingerprint(marked)
    assert build_schedule(config, today=date(2026, 10, 12)).model_dump(mode="json") == before
    with pytest.raises(ValueError, match="Legacy checkmarks"):
        plan(marked)
    first = draft_for(plan(config), today=date(2026, 10, 12))
    assert first == draft_for(plan(config), today=date(2026, 10, 12))
