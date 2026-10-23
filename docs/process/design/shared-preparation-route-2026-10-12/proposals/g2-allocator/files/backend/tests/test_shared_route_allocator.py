"""Literal personal-capacity controls, not programme/score or live-source tests."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.shared_route_allocator import allocate_shared_v1, canonical_input
from app.schemas.learning_schedule import AttemptReviewRef
from app.schemas.shared_route import (
    FrozenExactCatalogue,
    PersonalIeltsTargets,
    SharedAllocationV1,
    SharedRouteInputV1,
    ValidatedOwnedReviewV1,
)

STARTER = "starter-2026-10-11-v1"
PACK = "learning-pack-2026-10-11-v1"
# Independent literal public identities; never derive expected queues from app
# constants or call the allocation function to produce its own expectations.
ROWS = (
    ("ielts-reading-1", "ielts_reading", STARTER),
    ("ielts-reading-headings-1", "ielts_reading", PACK),
    ("ielts-reading-completion-1", "ielts_reading", PACK),
    ("ielts-reading-features-1", "ielts_reading", PACK),
    ("sat-math-1", "sat_math", STARTER),
    ("sat-quadratic-structure-1", "sat_math", PACK),
    ("sat-data-interpretation-1", "sat_math", PACK),
    ("sat-rw-1", "sat_reading_writing", STARTER),
    ("sat-grammar-transitions-1", "sat_reading_writing", PACK),
)
IELTS_ORDER = [
    "ielts-reading-1", "ielts-reading-headings-1",
    "ielts-reading-completion-1", "ielts-reading-features-1",
]
SAT_ORDER = [
    "sat-math-1", "sat-rw-1", "sat-quadratic-structure-1",
    "sat-grammar-transitions-1", "sat-data-interpretation-1",
]


def choice(exam="ielts_academic", priority=0, **changes):
    value = {
        "exam": exam,
        "priority": priority,
        "first_exam_on": "2026-03-01" if exam == "ielts_academic" else "2026-03-02",
        "retake_on": None,
        "certificate_deadline": "2026-03-25",
        "result_wait_days": 3,
        "delivery_days": 1,
        "safety_days": 1,
        "personal_targets": None,
        "confirmed_exam_dates_and_buffers": True,
    }
    value.update(changes)
    return value


def raw_input(**changes):
    value = {
        "selected_result_ids": ["own-A", "own-B"],
        "starts_on": "2026-01-05",
        "timezone": "America/New_York",
        "study_days": [0, 1, 2, 3, 4, 5, 6],
        "shared_weekly_minutes": 60,
        "exam_choices": [choice(), choice("digital_sat", 1)],
        "own_reviews": [],
        "confirmed_shared_planning_inputs": True,
    }
    value.update(changes)
    return value


def catalogue(unavailable=()):
    return FrozenExactCatalogue.model_validate({
        "version": PACK,
        "lessons": [
            {"ref": {"kind": "lesson", "id": f"lesson:{lesson_id}:{version}",
                     "lesson_id": lesson_id, "content_version": version},
             "track": track, "available": lesson_id not in unavailable}
            for lesson_id, track, version in ROWS
        ],
    })


def review(number=1, *, lesson_id="ielts-reading-1", version=STARTER,
           exam="ielts_academic", minutes=20):
    attempt_uuid = str(UUID(int=number))
    return {
        "ref": {"kind": "attempt_review", "id": f"attempt:{attempt_uuid}",
                "attempt_id": attempt_uuid, "lesson_id": lesson_id, "content_version": version},
        "exam": exam, "planned_minutes": minutes,
    }


def owned(request, *, unavailable=()):
    # Synthetic trusted upstream association/receipt availability, not a mocked
    # claim that an actual DB ownership or review route was exercised here.
    return [
        ValidatedOwnedReviewV1.model_validate({
            "ref": selected.ref.model_dump(mode="python"), "exam": selected.exam,
            "available": selected.ref.attempt_id.int not in unavailable,
        })
        for selected in request.own_reviews
    ]


def allocate(raw=None, *, planned_on=date(2026, 1, 5), unavailable=(), review_unavailable=()):
    request = SharedRouteInputV1.model_validate(raw_input() if raw is None else raw)
    return allocate_shared_v1(request, catalogue=catalogue(unavailable),
                              own_reviews=owned(request, unavailable=review_unavailable),
                              planned_on=planned_on)


def assert_conservation(allocation, requested_reviews=()):
    actions = [*allocation.slots, *allocation.unallocated]
    literal_refs = {ref.id for ref in allocation.lessons} | {
        selected["ref"]["id"] for selected in requested_reviews
    }
    assert len(actions) == len(literal_refs)
    assert Counter(action.ref.id for action in actions) == Counter(literal_refs)
    assert len({action.action_id for action in actions}) == len(actions)
    assert not ({s.action_id for s in allocation.slots} & {u.action_id for u in allocation.unallocated})


def test_two_exams_have_nine_literal_exact_refs_no_invented_applicability():
    allocation = allocate()
    assert [(ref.lesson_id, ref.content_version) for ref in allocation.lessons] == [
        (lesson_id, version) for lesson_id, _track, version in ROWS
    ]
    assert len(allocation.slots) == 9
    assert allocation.unallocated == []
    assert all(slot.planned_minutes == 20 for slot in allocation.slots)
    assert all(slot.origin == "personal_practice" and slot.completion == "not_projected"
               for slot in allocation.slots)
    assert allocation.readiness == "not_assessed"
    assert allocation.programme_applicability == "unknown"
    assert_conservation(allocation)


@pytest.mark.parametrize("exam,expected", [
    ("ielts_academic", IELTS_ORDER), ("digital_sat", SAT_ORDER),
])
def test_one_exam_uses_only_its_literal_queue(exam, expected):
    allocation = allocate(raw_input(exam_choices=[choice(exam)]))
    assert [slot.ref.lesson_id for slot in allocation.slots] == expected
    assert {slot.exam for slot in allocation.slots} == {exam}
    assert_conservation(allocation)


@pytest.mark.parametrize("exams,expected", [
    (["ielts_academic", "digital_sat"], ["ielts_academic", "digital_sat", "ielts_academic", "digital_sat"]),
    (["digital_sat", "ielts_academic"], ["digital_sat", "ielts_academic", "digital_sat", "ielts_academic"]),
])
def test_round_robin_cursor_survives_dates_and_uses_the_entered_priority(exams, expected):
    allocation = allocate(raw_input(shared_weekly_minutes=30,
                                   exam_choices=[choice(exam, i) for i, exam in enumerate(exams)]))
    assert [slot.exam for slot in allocation.slots[:4]] == expected
    assert [slot.local_date for slot in allocation.slots[:4]] == [
        date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19), date(2026, 1, 26),
    ]
    assert all(week.allocated_minutes <= 30 and week.remaining_minutes >= 10
               for week in allocation.capacity if week.allocated_minutes)
    assert_conservation(allocation)


def test_daily_cap_is_one_ledger_and_whole_units_spill_without_splitting():
    selected = review(minutes=20)
    allocation = allocate(raw_input(shared_weekly_minutes=1260, own_reviews=[selected]))
    daily = Counter()
    for slot in allocation.slots:
        daily[slot.local_date] += slot.planned_minutes
    assert dict(daily) == {date(2026, 1, 5): 180, date(2026, 1, 6): 20}
    assert sum(week.allocated_minutes for week in allocation.capacity) == 200
    assert all(slot.planned_minutes == 20 for slot in allocation.slots)
    assert_conservation(allocation, [selected])


def test_local_monday_capacity_crosses_iso_year_once_for_all_exam_streams():
    allocation = allocate(raw_input(
        starts_on="2026-12-28", exam_choices=[
            choice(first_exam_on="2027-01-12", certificate_deadline="2027-01-31"),
            choice("digital_sat", 1, first_exam_on="2027-01-13", certificate_deadline="2027-01-31"),
        ]), planned_on=date(2026, 12, 28))
    assert [week.iso_week_monday for week in allocation.capacity] == [
        date(2026, 12, 28), date(2027, 1, 4), date(2027, 1, 11),
    ]
    assert [week.allocated_minutes for week in allocation.capacity] == [60, 60, 60]
    for week in allocation.capacity:
        assert sum(slot.planned_minutes for slot in allocation.slots
                   if slot.local_date - timedelta(days=slot.local_date.weekday()) == week.iso_week_monday) == 60
    assert_conservation(allocation)


def test_dst_does_not_change_the_local_date_or_weekly_budget():
    allocation = allocate(raw_input(
        starts_on="2026-03-02", timezone="America/New_York",
        exam_choices=[choice(first_exam_on="2026-03-16", certificate_deadline="2026-04-01"),
                      choice("digital_sat", 1, first_exam_on="2026-03-17", certificate_deadline="2026-04-01")],
    ), planned_on=date(2026, 3, 2))
    assert [week.iso_week_monday for week in allocation.capacity] == [date(2026, 3, 2), date(2026, 3, 9)]
    assert [week.allocated_minutes for week in allocation.capacity] == [60, 60]
    assert [slot.local_date for slot in allocation.slots] == [date(2026, 3, 2)] * 3 + [date(2026, 3, 9)] * 3
    assert_conservation(allocation)


def test_zero_used_eligible_weeks_remain_in_the_ledger():
    allocation = allocate(raw_input(shared_weekly_minutes=1260))
    assert allocation.capacity[0].allocated_minutes == 180
    assert len(allocation.capacity) > 1
    assert all(week.allocated_minutes == 0 and week.remaining_minutes == 1260
               for week in allocation.capacity[1:])
    assert [week.iso_week_monday for week in allocation.capacity] == sorted(
        {week.iso_week_monday for week in allocation.capacity})


@pytest.mark.parametrize("duration,weekly,available,reason", [
    (200, 60, True, "too_long_for_day"),
    (100, 60, True, "too_long_for_week"),
    (200, 60, False, "version_unavailable"),
    (1260, 1260, True, "too_long_for_day"),
])
def test_oversized_or_unavailable_review_is_whole_and_cannot_block_valid_tail(duration, weekly, available, reason):
    selected = review(minutes=duration)
    allocation = allocate(raw_input(shared_weekly_minutes=weekly, own_reviews=[selected]),
                          review_unavailable=() if available else (1,))
    assert len(allocation.slots) == 9
    assert len(allocation.unallocated) == 1
    missing = allocation.unallocated[0]
    assert missing.ref.id == selected["ref"]["id"]
    assert (missing.reason, missing.requested_minutes) == (reason, duration)
    assert_conservation(allocation, [selected])


def test_review_minutes_are_explicit_and_not_the_lesson_default():
    selected = review(minutes=85)
    allocation = allocate(raw_input(shared_weekly_minutes=1260, own_reviews=[selected]))
    slots = [slot for slot in allocation.slots if slot.kind == "attempt_review"]
    assert len(slots) == 1 and slots[0].planned_minutes == 85
    assert_conservation(allocation, [selected])
    del selected["planned_minutes"]
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(own_reviews=[selected]))


def test_current_reviews_follow_the_exact_lesson_in_explicit_order():
    selections = [review(2, minutes=3), review(1, minutes=4)]
    allocation = allocate(raw_input(exam_choices=[choice()], shared_weekly_minutes=1260,
                                   own_reviews=selections))
    assert [slot.ref.id for slot in allocation.slots[:3]] == [
        f"lesson:ielts-reading-1:{STARTER}", selections[0]["ref"]["id"], selections[1]["ref"]["id"],
    ]
    assert [slot.planned_minutes for slot in allocation.slots[:3]] == [20, 3, 4]
    assert_conservation(allocation, selections)


def test_owned_old_version_receipt_can_be_available_without_current_lesson_content():
    selected = review(version="retired-historical-v1", minutes=7)
    allocation = allocate(raw_input(exam_choices=[choice()], shared_weekly_minutes=1260,
                                   own_reviews=[selected]))
    assert [slot.ref.lesson_id for slot in allocation.slots[:4]] == IELTS_ORDER
    last = allocation.slots[-1]
    assert isinstance(last.ref, AttemptReviewRef)
    assert last.kind == "attempt_review" and last.ref.content_version == "retired-historical-v1"
    assert last.ref.attempt_id == UUID(int=1) and last.planned_minutes == 7
    assert len(allocation.lessons) == 4 and allocation.unallocated == []
    assert_conservation(allocation, [selected])


def test_old_reviews_follow_all_current_lessons_and_keep_the_requested_order():
    selections = [review(8, version="retired-v2", minutes=2), review(3, version="retired-v1", minutes=3)]
    allocation = allocate(raw_input(exam_choices=[choice()], shared_weekly_minutes=1260,
                                   own_reviews=selections))
    assert [slot.ref.lesson_id for slot in allocation.slots[:4]] == IELTS_ORDER
    assert [slot.ref.id for slot in allocation.slots[4:]] == [s["ref"]["id"] for s in selections]
    assert_conservation(allocation, selections)


@pytest.mark.parametrize("version", [STARTER, "retired-historical-v1"])
def test_expired_lesson_heads_are_drained_before_a_still_open_retake_review(version):
    selected = review(version=version)
    allocation = allocate(raw_input(exam_choices=[choice(first_exam_on="2026-01-06", retake_on="2026-01-20",
                                                       certificate_deadline="2026-02-02")],
                                   own_reviews=[selected]), planned_on=date(2026, 1, 12))
    assert [(slot.kind, slot.local_date, slot.planned_minutes) for slot in allocation.slots] == [
        ("attempt_review", date(2026, 1, 12), 20),
    ]
    assert [action.ref.lesson_id for action in allocation.unallocated] == IELTS_ORDER
    assert {action.reason for action in allocation.unallocated} == {"window_elapsed"}
    assert sum(week.allocated_minutes for week in allocation.capacity) == 20
    assert_conservation(allocation, [selected])


def test_retake_alone_never_extends_a_lesson_window():
    allocation = allocate(raw_input(exam_choices=[choice(first_exam_on="2026-01-06", retake_on="2026-01-20",
                                                       certificate_deadline="2026-02-02")]),
                          planned_on=date(2026, 1, 12))
    assert allocation.slots == [] and allocation.capacity == []
    assert len(allocation.unallocated) == 4
    assert {item.reason for item in allocation.unallocated} == {"window_elapsed"}


def test_other_exams_entered_exam_day_is_also_excluded_for_a_live_review():
    selected = review(version="retired-historical-v1")
    allocation = allocate(raw_input(
        exam_choices=[choice(first_exam_on="2026-01-06", retake_on="2026-01-20", certificate_deadline="2026-02-02"),
                      choice("digital_sat", 1, first_exam_on="2026-01-12", retake_on="2026-01-19",
                             certificate_deadline="2026-02-02")], own_reviews=[selected]),
        planned_on=date(2026, 1, 12))
    assert [slot.local_date for slot in allocation.slots] == [date(2026, 1, 13)]
    assert not {slot.local_date for slot in allocation.slots} & {
        date(2026, 1, 6), date(2026, 1, 12), date(2026, 1, 19), date(2026, 1, 20),
    }
    assert_conservation(allocation, [selected])


@pytest.mark.parametrize("planned_on,reason", [
    (date(2026, 1, 5), "insufficient_capacity"), (date(2026, 1, 6), "window_elapsed"),
])
def test_no_eligible_weekday_in_an_open_window_is_not_a_past_window(planned_on, reason):
    allocation = allocate(raw_input(study_days=[2], exam_choices=[choice("digital_sat", first_exam_on="2026-01-06",
                                                                     certificate_deadline="2026-01-20")]),
                          planned_on=planned_on)
    assert allocation.slots == [] and allocation.capacity == []
    assert len(allocation.unallocated) == 5
    assert {action.reason for action in allocation.unallocated} == {reason}


def test_end_of_future_capacity_does_not_fabricate_a_horizon_plus_one_expiry():
    allocation = allocate(raw_input(study_days=[0], shared_weekly_minutes=30,
                                   exam_choices=[choice(first_exam_on="2026-01-06", certificate_deadline="2026-01-20")]))
    assert len(allocation.slots) == 1 and allocation.slots[0].local_date == date(2026, 1, 5)
    assert len(allocation.unallocated) == 3
    assert {action.reason for action in allocation.unallocated} == {"insufficient_capacity"}


def test_four_hundred_slot_cap_preserves_all_four_hundred_nine_actions():
    selections = [review(i, version="retired-historical-v1", minutes=1) for i in range(1, 401)]
    allocation = allocate(raw_input(shared_weekly_minutes=1260, own_reviews=selections))
    assert len(allocation.slots) == 400
    assert len(allocation.unallocated) == 9
    assert {action.reason for action in allocation.unallocated} == {"slot_limit"}
    assert sum(slot.planned_minutes for slot in allocation.slots) + sum(
        action.requested_minutes for action in allocation.unallocated) == 580
    assert_conservation(allocation, selections)


def test_unavailable_exact_current_content_keeps_its_ref_without_substitution():
    selected = review()
    allocation = allocate(raw_input(own_reviews=[selected]), unavailable=("ielts-reading-1",))
    missing = [a for a in allocation.unallocated if a.ref.kind == "lesson"]
    assert len(missing) == 1
    assert missing[0].ref.id == f"lesson:ielts-reading-1:{STARTER}"
    assert (missing[0].reason, missing[0].requested_minutes) == ("version_unavailable", 20)
    assert any(slot.ref.id == selected["ref"]["id"] for slot in allocation.slots)
    assert_conservation(allocation, [selected])


@pytest.mark.parametrize("targets", [None, {}, {"reading": 7.5}, {"writing": 0, "overall": 6.5}])
def test_optional_partial_personal_targets_roundtrip_without_filling_missing_fields(targets):
    request = SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice(personal_targets=targets)]))
    wire = request.model_dump(mode="json")
    assert wire["exam_choices"][0]["personal_targets"] == targets
    assert SharedRouteInputV1.model_validate(wire).model_dump(mode="json") == wire
    assert canonical_input(request)["exam_choices"][0]["personal_targets"] == targets
    allocation = allocate_shared_v1(request, catalogue=catalogue(), own_reviews=[], planned_on=date(2026, 1, 5))
    assert SharedAllocationV1.model_validate(allocation.model_dump(mode="json")).model_dump(mode="json") == allocation.model_dump(mode="json")
    assert allocation.readiness == "not_assessed"


def test_sat_partial_targets_are_preserved_but_a_complete_insufficient_sum_is_rejected():
    partial = {"total": 1400}
    request = SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice("digital_sat", personal_targets=partial)]))
    assert canonical_input(request)["exam_choices"][0]["personal_targets"] == partial
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice("digital_sat", personal_targets={
            "total": 1500, "math": 700, "reading_writing": 700})]))
    accepted = SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice("digital_sat", personal_targets={
        "total": 1400, "math": 800, "reading_writing": 700})]))
    assert canonical_input(accepted)["exam_choices"][0]["personal_targets"] == {
        "total": 1400, "math": 800, "reading_writing": 700,
    }


@pytest.mark.parametrize("target", [
    {"overall": 0}, {"reading": 9.5}, {"reading": -0.5}, {"reading": 7.25},
    {"reading": True}, {"reading": "7.5"}, {"reading": None}, {"vocabulary": 7},
    {"reading": float("nan")}, {"reading": float("inf")}, {"reading": float("-inf")},
])
def test_invalid_provided_ielts_targets_are_rejected_as_personal_input(target):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice(personal_targets=target)]))


@pytest.mark.parametrize("target", [
    {"total": 399}, {"math": 801}, {"reading_writing": 199}, {"math": 700.0},
    {"total": True}, {"math": "700"}, {"reading": 700}, {"math": None},
])
def test_invalid_provided_sat_targets_are_rejected_without_coercion(target):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice("digital_sat", personal_targets=target)]))


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_confirmations_require_literal_true_at_both_boundaries(value):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(confirmed_shared_planning_inputs=value))
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice(confirmed_exam_dates_and_buffers=value)]))


@pytest.mark.parametrize("value", ["2026-1-05", "2026-01-05T00:00:00Z", 1767571200, datetime(2026, 1, 5), "2026-02-30"])
def test_dates_are_local_iso_dates_without_datetime_or_timestamp_coercion(value):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(starts_on=value))


@pytest.mark.parametrize("change", [
    {"timezone": "Not/AZone"}, {"timezone": 1}, {"selected_result_ids": ["A"]},
    {"selected_result_ids": ["A", "A"]}, {"selected_result_ids": [1, "A"]},
    {"study_days": [0, 0]}, {"study_days": [True]}, {"study_days": [7]},
    {"shared_weekly_minutes": 29}, {"shared_weekly_minutes": 1261},
    {"shared_weekly_minutes": True}, {"shared_weekly_minutes": "60"},
    {"official_minimum": 7},
])
def test_shared_inputs_are_bounded_exact_and_not_official_fields(change):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(**change))


@pytest.mark.parametrize("ids", [[" own-A", "own-B"], ["own-A", "own-B "], ["\town-A\n", "own-B"]])
def test_selected_programme_ids_reject_whitespace_without_trimming_the_selection(ids):
    with pytest.raises(ValidationError, match="exact, unique and ordered"):
        SharedRouteInputV1.model_validate(raw_input(selected_result_ids=ids))
    accepted = SharedRouteInputV1.model_validate(raw_input(selected_result_ids=["own-B", "own-A"]))
    assert accepted.selected_result_ids == ["own-B", "own-A"]


@pytest.mark.parametrize("choices", [
    [], [choice(), choice(priority=1)], [choice(priority=1)],
    [choice(), choice("digital_sat", 0)], [choice(), choice("digital_sat", 1), choice(priority=2)],
    [choice("toefl")], [choice(priority=True)],
])
def test_exam_selection_is_one_or_two_unique_contiguous_explicit_choices(choices):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=choices))


@pytest.mark.parametrize("changes", [
    {"first_exam_on": "2026-01-04"}, {"certificate_deadline": "2026-03-01"},
    {"retake_on": "2026-03-01"}, {"retake_on": "2026-03-25"},
    {"result_wait_days": 0}, {"delivery_days": -1}, {"safety_days": 31},
])
def test_date_order_and_buffers_are_validated_without_deadline_inference(changes):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice(**changes)]))


def test_horizon_365_is_accepted_and_366_is_rejected():
    raw = raw_input(starts_on="2026-01-01", exam_choices=[choice(first_exam_on="2026-12-29",
                                                              certificate_deadline="2027-01-01")])
    assert SharedRouteInputV1.model_validate(raw).starts_on == date(2026, 1, 1)
    raw["exam_choices"][0]["certificate_deadline"] = "2027-01-02"
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw)


def test_late_buffer_plan_is_reported_as_risk_without_rewriting_the_exam():
    raw = raw_input(exam_choices=[choice(first_exam_on="2026-01-29", certificate_deadline="2026-01-30")])
    timing = allocate(raw).exam_timing[0]
    assert timing.first_exam_on == date(2026, 1, 29)
    assert timing.latest_safe_exam_on == date(2026, 1, 25)
    assert timing.timing == "at_risk"
    assert allocate(raw, planned_on=date(2026, 2, 1)).exam_timing[0].timing == "deadline_passed"


@pytest.mark.parametrize("start,first,deadline,planned", [
    ("0001-01-01", "0001-01-03", "0001-01-10", date(1, 1, 1)),
    ("9999-12-26", "9999-12-28", "9999-12-31", date(9999, 12, 26)),
    ("9999-12-26", "9999-12-28", "9999-12-31", date(9999, 12, 31)),
])
def test_valid_calendar_extremes_never_increment_beyond_date_max(start, first, deadline, planned):
    allocation = allocate(raw_input(starts_on=start, exam_choices=[choice(first_exam_on=first,
                              certificate_deadline=deadline, result_wait_days=1, delivery_days=0,
                              safety_days=0)]), planned_on=planned)
    assert all(planned <= slot.local_date < date.fromisoformat(first) for slot in allocation.slots)
    assert_conservation(allocation)


@pytest.mark.parametrize("start,first,deadline,buffers", [
    ("0001-01-01", "0001-01-02", "0001-01-03", 60),
    ("9999-12-20", "9999-12-30", "9999-12-31", 60),
])
def test_buffer_arithmetic_overflow_is_a_controlled_validation_error(start, first, deadline, buffers):
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(starts_on=start, exam_choices=[choice(
            first_exam_on=first, certificate_deadline=deadline, result_wait_days=buffers)]))


@pytest.mark.parametrize("planned", [datetime(2026, 1, 5), "2026-01-05", None])
def test_pure_planned_on_is_explicit_date_not_clock_or_timestamp(planned):
    with pytest.raises(ValueError, match="explicitly supplied local date"):
        allocate(planned_on=planned)


def test_catalogue_ref_identity_and_availability_cannot_be_faked():
    wire = catalogue().model_dump(mode="python")
    invalid = deepcopy(wire)
    invalid["lessons"][0]["ref"]["id"] = "alias"
    with pytest.raises(ValidationError):
        FrozenExactCatalogue.model_validate(invalid)
    invalid = deepcopy(wire)
    invalid["lessons"][0]["ref"]["content_version"] = "replacement-v1"
    invalid["lessons"][0]["ref"]["id"] = "lesson:ielts-reading-1:replacement-v1"
    with pytest.raises(ValidationError):
        FrozenExactCatalogue.model_validate(invalid)
    invalid = deepcopy(wire)
    invalid["lessons"][0]["available"] = 1
    with pytest.raises(ValidationError):
        FrozenExactCatalogue.model_validate(invalid)
    for broken in (wire["lessons"][:-1], [wire["lessons"][0]] * 9, list(reversed(wire["lessons"]))):
        with pytest.raises(ValidationError):
            FrozenExactCatalogue.model_validate({"version": PACK, "lessons": broken})


def test_exact_review_reference_duplicate_and_exam_selection_are_strict():
    selected = review()
    for field, replacement in (("id", "alias"), ("attempt_id", 1), ("lesson_id", True),
                               ("content_version", " padded ")):
        invalid = deepcopy(selected)
        invalid["ref"][field] = replacement
        with pytest.raises(ValidationError):
            SharedRouteInputV1.model_validate(raw_input(own_reviews=[invalid]))
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(own_reviews=[selected, deepcopy(selected)]))
    with pytest.raises(ValidationError):
        SharedRouteInputV1.model_validate(raw_input(exam_choices=[choice("digital_sat")], own_reviews=[selected]))


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate", "version", "exam", "current_track"])
def test_supplied_own_review_boundary_matches_exact_request_and_known_current_track(change):
    raw = raw_input(own_reviews=[review()])
    if change == "current_track":
        raw["own_reviews"][0]["exam"] = "digital_sat"
    request = SharedRouteInputV1.model_validate(raw)
    supplied = owned(request)
    if change == "missing":
        supplied = []
    elif change == "extra":
        other = SharedRouteInputV1.model_validate(raw_input(own_reviews=[review(2)]))
        supplied += owned(other)
    elif change == "duplicate":
        supplied *= 2
    elif change == "version":
        supplied[0].ref.content_version = "retired-historical-v1"
    elif change == "exam":
        supplied[0] = supplied[0].model_copy(update={"exam": "digital_sat"})
    with pytest.raises(ValueError):
        allocate_shared_v1(request, catalogue=catalogue(), own_reviews=supplied, planned_on=date(2026, 1, 5))


def test_owned_availability_read_order_is_not_a_tie_breaker():
    request = SharedRouteInputV1.model_validate(raw_input(own_reviews=[review(2), review(1)]))
    supplied = owned(request)
    first = allocate_shared_v1(request, catalogue=catalogue(), own_reviews=supplied, planned_on=date(2026, 1, 5))
    second = allocate_shared_v1(request, catalogue=catalogue(), own_reviews=list(reversed(supplied)), planned_on=date(2026, 1, 5))
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_action_and_occurrence_ids_match_independent_literal_sha256_anchors():
    first = allocate().slots[0]
    assert first.action_id == "df5b79f9106a5583b48bc5187f2fe2c900c73139951fdd98aa9c4226970e4a0b"
    assert first.occurrence_id == "b51bb9d4837306fa13805f19cdc2b65434d19541fbfc4393879a10dd6288b01b"
    assert first.local_date == date(2026, 1, 5)


def test_action_identity_is_independent_of_programmes_date_and_other_insertions():
    original = allocate(raw_input(shared_weekly_minutes=1260))
    changed = allocate(raw_input(selected_result_ids=["another-B", "another-A"],
                                 shared_weekly_minutes=1260), planned_on=date(2026, 1, 6))
    assert {slot.ref.id: slot.action_id for slot in original.slots} == {
        slot.ref.id: slot.action_id for slot in changed.slots}
    assert original.digest != changed.digest
    assert original.slots[0].occurrence_id != changed.slots[0].occurrence_id
    added = allocate(raw_input(exam_choices=[choice()], shared_weekly_minutes=1260,
                               own_reviews=[review(minutes=1)]))
    unchanged_lesson = next(slot for slot in original.slots if slot.ref.lesson_id == "ielts-reading-headings-1")
    inserted_lesson = next(slot for slot in added.slots if slot.ref.lesson_id == "ielts-reading-headings-1")
    assert unchanged_lesson.local_date == inserted_lesson.local_date
    assert unchanged_lesson.occurrence_id == inserted_lesson.occurrence_id


def test_distinct_versions_and_attempt_uuids_never_collapse_into_one_action():
    first = allocate(raw_input(own_reviews=[review(version="retired-v1"), review(2, version="retired-v1")]))
    second = allocate(raw_input(own_reviews=[review(version="retired-v2"), review(2, version="retired-v1")]))
    first_ids = {slot.ref.id: slot.action_id for slot in first.slots if slot.kind == "attempt_review"}
    second_ids = {slot.ref.id: slot.action_id for slot in second.slots if slot.kind == "attempt_review"}
    assert len(set(first_ids.values())) == 2
    assert first_ids[f"attempt:{UUID(int=1)}"] != second_ids[f"attempt:{UUID(int=1)}"]
    assert first_ids[f"attempt:{UUID(int=2)}"] == second_ids[f"attempt:{UUID(int=2)}"]


def test_canonical_input_keeps_ordered_intent_and_sorts_only_weekday_set():
    raw = raw_input(selected_result_ids=["B", "A"], study_days=[6, 0, 2],
                    exam_choices=[choice("digital_sat", 0, personal_targets={"math": 700}),
                                  choice(priority=1, personal_targets={"reading": 7.5})],
                    own_reviews=[review(2), review(1)])
    request = SharedRouteInputV1.model_validate(raw)
    values = canonical_input(request)
    assert values["selected_result_ids"] == ["B", "A"]
    assert values["study_days"] == [0, 2, 6]
    assert [c["exam"] for c in values["exam_choices"]] == ["digital_sat", "ielts_academic"]
    assert [c["personal_targets"] for c in values["exam_choices"]] == [{"math": 700}, {"reading": 7.5}]
    assert [r["ref"]["attempt_id"] for r in values["own_reviews"]] == [str(UUID(int=2)), str(UUID(int=1))]
    equivalent = deepcopy(raw)
    equivalent["study_days"] = [2, 6, 0]
    assert allocate(raw).model_dump(mode="json") == allocate(equivalent).model_dump(mode="json")
    reordered = deepcopy(raw)
    reordered["selected_result_ids"] = ["A", "B"]
    assert allocate(raw).digest != allocate(reordered).digest


def test_personal_target_change_binds_digest_but_does_not_reweight_work():
    empty = allocate(raw_input(exam_choices=[choice(personal_targets=None)]))
    supplied = allocate(raw_input(exam_choices=[choice(personal_targets={"reading": 9})]))
    assert empty.digest != supplied.digest
    assert [slot.model_dump(mode="json") for slot in empty.slots] == [slot.model_dump(mode="json") for slot in supplied.slots]
    assert supplied.readiness == "not_assessed" and supplied.programme_applicability == "unknown"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_allocator_revalidates_typed_nonfinite_targets_before_any_json_conversion(bad):
    request = SharedRouteInputV1.model_validate(raw_input())
    target = PersonalIeltsTargets.model_construct(reading=bad)
    unsafe_choice = request.exam_choices[0].model_copy(update={"personal_targets": target})
    unsafe_request = request.model_copy(update={"exam_choices": [unsafe_choice, request.exam_choices[1]]})
    with pytest.raises(ValidationError):
        allocate_shared_v1(unsafe_request, catalogue=catalogue(), own_reviews=[], planned_on=date(2026, 1, 5))


def test_allocator_does_not_mutate_or_alias_caller_refs_lists_and_targets():
    request = SharedRouteInputV1.model_validate(raw_input(own_reviews=[review()],
                                                       exam_choices=[choice(personal_targets={"reading": 7.5})]))
    registry = catalogue()
    supplied = owned(request)
    before = (request.model_dump(mode="python"), registry.model_dump(mode="python"),
              [item.model_dump(mode="python") for item in supplied])
    result = allocate_shared_v1(request, catalogue=registry, own_reviews=supplied, planned_on=date(2026, 1, 5))
    assert before == (request.model_dump(mode="python"), registry.model_dump(mode="python"),
                      [item.model_dump(mode="python") for item in supplied])
    result.lessons[0].content_version = "mutated-returned-ref"
    result.slots[-1].ref.content_version = "mutated-returned-slot"
    assert before == (request.model_dump(mode="python"), registry.model_dump(mode="python"),
                      [item.model_dump(mode="python") for item in supplied])


@pytest.mark.parametrize("location", ["slots", "unallocated"])
def test_output_rejects_known_lesson_under_another_selected_exam(location):
    allocation = allocate(unavailable=("ielts-reading-1",) if location == "unallocated" else ())
    wire = allocation.model_dump(mode="json")
    item = next(item for item in wire[location] if item["ref"]["kind"] == "lesson"
                and item["ref"]["lesson_id"] == "ielts-reading-1")
    item["exam"] = "digital_sat"
    # These literals were computed independently from the specified canonical
    # JSON, so the track control is not masked by an invalid identity guard.
    item["action_id"] = "48745e20d0be23b1527de4a271d744cfa6dc1c7818b95644b5a26eee29e29898"
    if location == "slots":
        item["occurrence_id"] = "db1a3f83a530ea4ac0fb7af6a0859a97b9e985f78c63b449dc34b4cf9d6d20e9"
    with pytest.raises(ValidationError, match="track/exam association"):
        SharedAllocationV1.model_validate(wire)


@pytest.mark.parametrize("location", ["slots", "unallocated"])
@pytest.mark.parametrize("kind", ["lesson", "attempt_review"])
def test_output_rejects_forged_action_hash_even_when_its_shape_is_valid(location, kind):
    selected = review()
    allocation = allocate(raw_input(own_reviews=[selected]),
                          unavailable=("ielts-reading-1",) if location == "unallocated" else (),
                          review_unavailable=(1,) if location == "unallocated" else ())
    wire = allocation.model_dump(mode="json")
    item = next(item for item in wire[location] if item["ref"]["kind"] == kind)
    item["action_id"] = "f" * 64
    with pytest.raises(ValidationError, match="Action ID must match"):
        SharedAllocationV1.model_validate(wire)


@pytest.mark.parametrize("kind", ["lesson", "attempt_review"])
def test_output_rejects_forged_occurrence_hash_even_when_its_shape_is_valid(kind):
    wire = allocate(raw_input(own_reviews=[review()])).model_dump(mode="json")
    item = next(item for item in wire["slots"] if item["ref"]["kind"] == kind)
    item["occurrence_id"] = "f" * 64
    with pytest.raises(ValidationError, match="Occurrence ID must match"):
        SharedAllocationV1.model_validate(wire)


@pytest.mark.parametrize("location", ["slots", "unallocated"])
@pytest.mark.parametrize("minutes", [1, 19, 21, 180])
def test_output_current_lesson_minutes_cannot_be_rewritten(location, minutes):
    wire = allocate(unavailable=("ielts-reading-1",) if location == "unallocated" else ()).model_dump(mode="json")
    item = next(item for item in wire[location] if item["ref"]["kind"] == "lesson")
    item["planned_minutes" if location == "slots" else "requested_minutes"] = minutes
    with pytest.raises(ValidationError, match="exact 20-minute planning allocation"):
        SharedAllocationV1.model_validate(wire)


@pytest.mark.parametrize("fault", ["duplicate", "missing", "day_cap", "ledger", "exam_day", "kind", "readiness", "timing"])
def test_output_conservation_budget_and_personal_status_guards(fault):
    wire = allocate(raw_input(shared_weekly_minutes=1260, own_reviews=[review(minutes=1)])).model_dump(mode="json")
    if fault == "duplicate":
        wire["slots"].append(deepcopy(wire["slots"][0]))
    elif fault == "missing":
        wire["slots"].pop()
    elif fault == "day_cap":
        item = next(item for item in wire["slots"] if item["ref"]["lesson_id"] == "sat-data-interpretation-1")
        item["local_date"] = "2026-01-05"
        item["occurrence_id"] = "4e0f85bfb5619f2278eb699687131fb34552ad2b49c2076b414a32713a16e5dd"
    elif fault == "ledger":
        wire["capacity"][0]["allocated_minutes"] -= 1
        wire["capacity"][0]["remaining_minutes"] += 1
    elif fault == "exam_day":
        wire["slots"][0]["local_date"] = "2026-03-01"
        wire["slots"][0]["occurrence_id"] = "7c19a983fdae96eb79431b7fede3c1c5f35ad7b0d381b23496e599ae614e0cc1"
    elif fault == "kind":
        wire["slots"][0]["kind"] = "attempt_review"
    elif fault == "readiness":
        wire["readiness"] = "ready"
    else:
        wire["exam_timing"][0]["latest_safe_exam_on"] = "2026-03-21"
    with pytest.raises(ValidationError):
        SharedAllocationV1.model_validate(wire)


def test_external_resources_assessments_and_premium_proofs_are_not_allocator_content():
    wire = allocate().model_dump(mode="json")
    for kind in ("assessment", "external_resource"):
        broken = deepcopy(wire)
        broken["slots"][0]["ref"] = {"kind": kind, "id": "not-local-course", "version": "v1"}
        with pytest.raises(ValidationError):
            SharedAllocationV1.model_validate(broken)
    wire["official_requirement_proof"] = {"programme_name": "Not an allocator source"}
    with pytest.raises(ValidationError):
        SharedAllocationV1.model_validate(wire)
