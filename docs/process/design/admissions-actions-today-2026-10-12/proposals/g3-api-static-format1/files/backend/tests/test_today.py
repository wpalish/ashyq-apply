"""Read-only Today controls using native accepted preparation and G3 HTTP state.

Both databases are migrated by the existing native lab. Source data and plans
are synthetic; no provider, source fetch, booking, official admissions outcome
or new allocation is performed. External source author has not run this file.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import delete

from app.models import (
    Entitlement,
    ProgramResultRow,
    SharedRouteCurrentRow,
    StudyScheduleRow,
    Subscription,
)
from app.models.admissions_actions import AdmissionsActionsCurrentRow
from app.models.base import utcnow
from app.schemas import admissions_actions as s
from tests.test_admissions_actions_api import (
    accepted,
    bind,
    command,
    details,
    interleave_once,
    new_personal,
    preview_source,
    safe_error,
    seed_source,
    target,
)
from tests.test_admissions_actions_concurrency import native_snapshot, stored
from tests.test_learning_schedule_api import preview as learning_preview
from tests.test_learning_schedule_api import save as learning_save
from tests.test_preparation_api import body as attempt_body
from tests.test_preparation_api import grant, url
from tests.test_preparation_graph_api import _capture
from tests.test_shared_route_api import accepted as shared_accepted
from tests.test_shared_route_api import (
    assert_no_dml,
    assert_no_premium_reads,
    own_review,
    route_input,
    stored_routes,
)
from tests.test_study_schedule_api import write as write_schedule

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")


def endpoint(lab):
    return f"/api/profiles/{lab['case']}/today"


def today(lab, *, timezone=None):
    params = {} if timezone is None else {"timezone": timezone}
    response = lab["client"].get(endpoint(lab), params=params)
    assert response.status_code == 200, response.text
    value = response.json()
    projection = s.TodayProjectionV1.model_validate(value)
    assert set(value) == set(s.TodayProjectionV1.model_fields)
    assert projection.profile_id == lab["case"]
    assert projection.personal_minutes == "not_estimated"
    assert projection.readiness == "not_assessed"
    return value


def cards(value):
    return [
        *value["overdue_personal"],
        *value["today_study"],
        *value["today_personal"],
        *value["future"],
        *value["undated_personal"],
    ]


def assert_one_ledger(value):
    plan = value["active_plan"]
    assert value["allocated_study_minutes"] == plan["allocated_minutes"]
    assert plan["allocated_minutes"] == sum(t["planned_minutes"] for t in plan["study_actions"])
    for card in cards(value):
        if card["reason"] == "accepted_study_action":
            assert card["workload_origin"] == plan["origin"]
            assert card["planned_minutes"] is not None
        else:
            assert (
                card["workload_origin"] == "personal_unallocated"
                and card["planned_minutes"] is None
            )


def make_v2(lab):
    assert write_schedule(lab).status_code == 200
    response = learning_save(lab, learning_preview(lab, 1))
    assert response.status_code == 200, response.text
    with lab["factory"]() as session:
        row = session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).one()
        return row.revision, deepcopy(row.learning_path), deepcopy(row.settings)


def test_genuine_no_plan_is_unknown_workload_and_no_allocation_or_backfill(shared_route_lab):
    lab = shared_route_lab
    before = native_snapshot(lab), stored(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert response.status_code == 200, response.text
    value = today(lab)
    assert value["action_state"] == "absent" and value["action_revision"] == 0
    assert value["active_plan"]["origin"] == "none" and value["active_plan"]["state"] == "absent"
    assert value["active_plan"]["selection_source"] == "derived_backward_default"
    assert value["active_plan"]["study_actions"] == []
    assert value["workload"] == "unknown" and value["allocated_study_minutes"] is None
    assert cards(value) == [] and value["application_summaries"] == []
    assert value["display_timezone"] == "UTC"
    assert_no_dml(sql)
    assert_no_premium_reads(sql)
    assert (native_snapshot(lab), stored(lab)) == before


def test_g2_default_retains_exact_saved_slot_order_versions_reviews_and_single_budget(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab, status="exhausted", quota=0)
    make_v2(lab)  # Both backward-compatible legacy origins also exist.
    attempt = attempt_body(lesson="ielts-reading-1")
    response = lab["client"].post(url(lab, "attempts"), json=attempt)
    assert response.status_code == 200, response.text
    input_value = route_input(lab, weekly_minutes=90, own_reviews=[own_review(attempt)])
    _, receipt = shared_accepted(lab, input_value)
    before = native_snapshot(lab), stored(lab), stored_routes(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert response.status_code == 200, response.text
    value = today(lab)
    plan = value["active_plan"]
    assert plan["origin"] == "g2" and plan["selection_source"] == "derived_backward_default"
    assert plan["goal_result_ids"] == input_value["selected_result_ids"]
    head = plan["current_observed_head"]
    assert head["snapshot_digest"] == receipt["snapshot_digest"]
    assert head["allocation_digest"] == receipt["allocation_digest"]
    assert head["client_write_uuid"] == receipt["client_write_uuid"]
    assert [
        (t["id"], t["local_date"], t["timezone"], t["ref"], t["planned_minutes"])
        for t in plan["study_actions"]
    ] == [
        (
            slot["occurrence_id"],
            slot["local_date"],
            input_value["timezone"],
            slot["ref"],
            slot["planned_minutes"],
        )
        for slot in receipt["allocation"]["slots"]
    ]
    assert any(
        t["ref"]["kind"] == "attempt_review" and t["ref"]["attempt_id"] == attempt["attempt_id"]
        for t in plan["study_actions"]
    )
    assert {t["ref"]["content_version"] for t in plan["study_actions"]} == {attempt["version"]}
    assert_one_ledger(value)
    assert_no_dml(sql)
    assert_no_premium_reads(sql)  # No full-research entitlement was granted.
    assert (native_snapshot(lab), stored(lab), stored_routes(lab)) == before


@pytest.mark.parametrize("presence", ["current_and_history", "history_only"])
def test_g2_presence_including_history_never_falls_back_to_legacy(shared_route_lab, presence):
    lab = shared_route_lab
    grant(lab)
    make_v2(lab)
    shared_accepted(lab, route_input(lab))
    if presence == "history_only":
        with lab["factory"]() as session:
            session.delete(session.get(SharedRouteCurrentRow, lab["case"]))
            session.commit()
    before = native_snapshot(lab), stored(lab)
    value = today(lab)
    assert value["active_plan"]["origin"] == "g2"
    assert value["active_plan"]["selection_source"] == "derived_backward_default"
    if presence == "history_only":
        assert value["active_plan"]["state"] == "unavailable"
        assert value["active_plan"]["study_actions"] == []
        assert value["allocated_study_minutes"] is None
    assert (native_snapshot(lab), stored(lab)) == before


@pytest.mark.parametrize("malformed", [{}, {"synthetic_unknown_sidecar": True}])
def test_raw_nonnull_v2_marker_is_unavailable_and_personal_tasks_survive(
    shared_route_lab, malformed
):
    lab = shared_route_lab
    grant(lab)
    assert write_schedule(lab).status_code == 200
    task = new_personal(lab)
    task_id = task["applied_delta"]["document_tasks"][0]["id"]
    with lab["factory"]() as session:
        session.query(StudyScheduleRow).filter_by(
            profile_id=lab["case"]
        ).one().learning_path = deepcopy(malformed)
        session.commit()
    before = native_snapshot(lab), stored(lab)
    value = today(lab)
    assert value["active_plan"]["origin"] == "legacy_v2"
    assert value["active_plan"]["state"] == "unavailable"
    assert value["allocated_study_minutes"] is None and value["workload"] == "unknown"
    assert value["active_plan"]["study_actions"] == []
    assert any(
        c["target"] == {"kind": "document_task", "id": task_id} for c in value["undated_personal"]
    )
    assert {n["code"] for n in value["notices"]} >= {"plan_unavailable"}
    assert (native_snapshot(lab), stored(lab)) == before


def test_v1_retains_native_saved_settings_ticks_ids_minutes_order_without_version_guess(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    original = write_schedule(lab)
    assert original.status_code == 200, original.text
    settings = deepcopy(original.json()["settings"])
    tick = original.json()["schedule"]["tasks"][0]["id"]
    settings["completed_task_ids"] = [tick]
    assert write_schedule(lab, revision=1, plan=settings).status_code == 200
    native_view = lab["client"].get(url(lab, "schedule")).json()
    before = native_snapshot(lab), stored(lab)
    value = today(lab)
    plan = value["active_plan"]
    assert plan["origin"] == "legacy_v1"
    assert plan["current_observed_head"]["revision"] == native_view["revision"]
    assert [(t["id"], t["local_date"], t["planned_minutes"]) for t in plan["study_actions"]] == [
        (t["id"], t["due_on"], t["minutes"]) for t in native_view["schedule"]["tasks"]
    ]
    assert all(
        t["ref"] is None and t["availability"] == "unsupported" for t in plan["study_actions"]
    )
    assert (
        next(t for t in plan["study_actions"] if t["id"] == tick)["completion"]
        == "self_reported_complete"
    )
    assert tick not in {c["id"] for c in cards(value)}
    assert_one_ledger(value)
    assert (native_snapshot(lab), stored(lab)) == before


def test_v2_uses_persisted_sidecar_head_and_exact_frozen_dates_refs_minutes(shared_route_lab):
    lab = shared_route_lab
    grant(lab)
    revision, snapshot, settings = make_v2(lab)
    before = native_snapshot(lab), stored(lab)
    value = today(lab)
    plan = value["active_plan"]
    assert plan["origin"] == "legacy_v2" and plan["current_observed_head"]["revision"] == revision
    assert plan["current_observed_head"]["persisted_sidecar_digest"] == s.reference_digest(
        "g3-native-v2-sidecar-v1", snapshot
    )
    assert plan["current_observed_head"]["draft_fingerprint"] == snapshot["draft"]["fingerprint"]
    assert [
        (t["id"], t["local_date"], t["timezone"], t["ref"], t["planned_minutes"])
        for t in plan["study_actions"]
    ] == [
        (t["id"], t["due_on"], settings["timezone"], t["learning_ref"], t["minutes"])
        for t in snapshot["schedule"]["tasks"]
    ]
    assert_one_ledger(value)
    assert (native_snapshot(lab), stored(lab)) == before


def test_explicit_selected_origin_wins_and_failed_selected_plan_preserves_personal_summary(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    result_id = seed_source(lab)
    assert write_schedule(lab).status_code == 200
    head = today(lab)["active_plan"]["current_observed_head"]
    selected = accepted(
        lab,
        command(
            "select_active_preparation",
            origin="legacy_v1",
            policy="follow_current_accepted",
            observed_head=head,
        ),
    )
    app = accepted(
        lab,
        command(
            "create_application",
            1,
            target=target(result_id),
            label="Synthetic saved application",
            details=details(),
        ),
    )
    app_id = app["applied_delta"]["applications"][0]["id"]
    task = new_personal(lab, revision=2)
    shared_accepted(lab, route_input(lab))
    value = today(lab)
    assert value["active_plan"]["origin"] == "legacy_v1"
    assert value["active_plan"]["selection_source"] == "accepted_g3_event"
    assert value["active_plan"]["selection"]["event_ref"]["event_id"] == selected["event_id"]
    with lab["factory"]() as session:
        session.delete(session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).one())
        session.commit()
    before = native_snapshot(lab), stored(lab)
    value = today(lab)
    assert (
        value["active_plan"]["origin"] == "legacy_v1"
        and value["active_plan"]["state"] == "unavailable"
    )
    assert value["active_plan"]["selection"]["event_ref"]["event_id"] == selected["event_id"]
    assert value["action_state"] == "readable" and value["action_revision"] == task["revision"]
    assert value["application_summaries"][0]["id"] == app_id
    assert {c["target"]["id"] for c in value["undated_personal"]} == {
        app_id,
        task["applied_delta"]["document_tasks"][0]["id"],
    }
    assert (native_snapshot(lab), stored(lab)) == before


def test_unreadable_g3_cannot_derive_a_fallback_native_plan(shared_route_lab):
    lab = shared_route_lab
    grant(lab)
    make_v2(lab)
    new_personal(lab)
    with lab["factory"]() as session:
        session.get(AdmissionsActionsCurrentRow, lab["case"]).state_digest = "0" * 64
        session.commit()
    before = native_snapshot(lab), stored(lab)
    value = today(lab)
    assert value["action_state"] == "unavailable"
    assert value["action_revision"] is None and value["action_digest"] is None
    assert (
        value["active_plan"]["origin"] == "unknown"
        and value["active_plan"]["state"] == "unavailable"
    )
    assert value["allocated_study_minutes"] is None and cards(value) == []
    assert (native_snapshot(lab), stored(lab)) == before


@pytest.mark.parametrize("research_allowed,preparation_allowed", [(True, False), (False, True)])
def test_research_and_preparation_permissions_are_independent(
    shared_route_lab, research_allowed, preparation_allowed
):
    lab = shared_route_lab
    term_id = grant(lab)
    result_id = seed_source(lab)
    bound = bind(lab, preview_source(lab, result_id))
    shared_accepted(lab, route_input(lab))
    with lab["factory"]() as session:
        if not research_allowed:
            session.execute(delete(Entitlement).where(Entitlement.profile_id == lab["case"]))
        if not preparation_allowed:
            session.get(Subscription, term_id).ends_at = utcnow() - timedelta(days=1)
        session.commit()
    before = native_snapshot(lab), stored(lab)
    response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert response.status_code == 200, response.text
    value = today(lab)
    assert value["preparation_access"]["allowed"] is preparation_allowed
    statuses = {item["result_id"]: item for item in value["current_source_statuses"]}
    # This synthetic checklist has no resolved official document claim. Full
    # access permits an honest unknown proof observation; it does not certify it.
    assert statuses[result_id]["source_state"] == (
        "evidence_unknown" if research_allowed else "research_locked"
    )
    if not research_allowed:
        assert all(
            item["current_digest"] is None and item["reasons"] == [] for item in statuses.values()
        )
        assert_no_premium_reads(sql)
    lesson_cards = [
        c
        for c in cards(value)
        if c["reason"] == "accepted_study_action"
        and c["target"] is not None
        and c["target"]["kind"] == "lesson"
    ]
    assert lesson_cards and all(c["actionable"] is preparation_allowed for c in lesson_cards)
    assert any(
        c["target"]
        == {"kind": "document_task", "id": bound["applied_delta"]["document_tasks"][0]["id"]}
        for c in value["undated_personal"]
    )
    assert_one_ledger(value)
    assert_no_dml(sql)
    assert (native_snapshot(lab), stored(lab)) == before


@pytest.mark.parametrize("timezone", ["Pacific/Kiritimati", "America/Los_Angeles"])
def test_iana_dates_uncertainty_dependencies_and_stable_personal_id_order(
    shared_route_lab, timezone
):
    lab = shared_route_lab
    instant = utcnow().astimezone(ZoneInfo(timezone)).date()
    overdue = new_personal(
        lab, due={"local_date": (instant - timedelta(days=1)).isoformat(), "timezone": None}
    )
    due = new_personal(
        lab, revision=1, due={"local_date": instant.isoformat(), "timezone": timezone}
    )
    missing_dependency = "f" * 32
    undated = new_personal(lab, revision=2, dependencies=[missing_dependency])
    new_personal(lab, revision=3, label="Synthetic other undated task")
    before = native_snapshot(lab), stored(lab)
    value = today(lab, timezone=timezone)
    observed_day = (
        datetime.fromisoformat(value["as_of"].replace("Z", "+00:00"))
        .astimezone(ZoneInfo(timezone))
        .date()
    )
    assert value["display_timezone"] == timezone
    old_card = next(
        c
        for c in value["overdue_personal"]
        if c["target"]["id"] == overdue["applied_delta"]["document_tasks"][0]["id"]
    )
    assert old_card["date"]["certainty"] == "date_only_timezone_unknown"
    assert old_card["date"]["timezone"] is None and old_card["date"]["comparison_zone"] == timezone
    assert old_card["date"]["fallback_display_only"] is True
    due_section = "today_personal" if instant == observed_day else "overdue_personal"
    now_card = next(
        c
        for c in value[due_section]
        if c["target"]["id"] == due["applied_delta"]["document_tasks"][0]["id"]
    )
    assert now_card["date"]["certainty"] == "applicant_entered"
    other = next(
        c
        for c in value["undated_personal"]
        if c["target"]["id"] == undated["applied_delta"]["document_tasks"][0]["id"]
    )
    assert other["dependency_reasons"] == ["dependency_missing"]
    assert all(
        c["date"]["official_closure"] == "not_assessed" and c["planned_minutes"] is None
        for c in cards(value)
    )
    for section in ("today_personal", "undated_personal"):
        assert [c["target"]["id"] for c in value[section]] == sorted(
            c["target"]["id"] for c in value[section]
        )
    assert (native_snapshot(lab), stored(lab)) == before


def test_invalid_timezone_is_safe_route_error_and_cannot_mutate_native_plan(shared_route_lab):
    lab = shared_route_lab
    before = native_snapshot(lab), stored(lab)
    safe_error(
        lab["client"].get(
            endpoint(lab), params={"timezone": "SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO"}
        ),
        "input_invalid",
    )
    assert (native_snapshot(lab), stored(lab)) == before


@pytest.mark.parametrize(
    "change", ["research_lock", "decision", "g3_head", "native_plan", "preparation_expiry"]
)
def test_one_real_metadata_recheck_withholds_mixed_joins_and_clears_newly_locked_proof(
    shared_route_lab, change
):
    lab = shared_route_lab
    term_id = grant(lab)
    result_id = seed_source(lab)
    app = accepted(
        lab,
        command(
            "create_application",
            target=target(result_id),
            label="Synthetic race application",
            details=details(),
        ),
    )
    app_id = app["applied_delta"]["applications"][0]["id"]
    bind(lab, preview_source(lab, result_id), revision=1, application_id=app_id)
    assert write_schedule(lab).status_code == 200
    native_before = native_snapshot(lab)

    def second_transaction():
        if change == "g3_head":
            return new_personal(lab, revision=2)
        with lab["factory"]() as session:
            if change == "research_lock":
                session.execute(delete(Entitlement).where(Entitlement.profile_id == lab["case"]))
            elif change == "decision":
                session.get(ProgramResultRow, result_id).user_decision = "rejected"
            elif change == "native_plan":
                row = session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).one()
                settings = deepcopy(row.settings)
                settings["weekly_minutes"] += 30
                row.settings = settings
                row.revision += 1
            else:
                session.get(Subscription, term_id).ends_at = utcnow() - timedelta(days=1)
            session.commit()
        return True

    with interleave_once(
        lab,
        lambda q: q.startswith("select")
        and "from program_results" in q
        and "program_results.checklist" in q
        and "research_runs.demo_mode" in q,
        second_transaction,
    ) as race:
        response, sql = _capture(lab, lambda: lab["client"].get(endpoint(lab)))
    assert race["fired"] and race["callback_result"]
    assert response.status_code == 200, response.text
    value = response.json()
    s.TodayProjectionV1.model_validate(value)
    assert value["consistency"] == "mixed_revision" and value["needs_refresh"] is True
    assert {n["code"] for n in value["notices"]} >= {"mixed_revision"}
    assert cards(value) == []
    assert value["application_summaries"][0]["id"] == app_id
    assert value["workload"] == "unknown" and value["allocated_study_minutes"] is None
    if change == "research_lock":
        assert all(
            item["current_digest"] is None and item["reasons"] == []
            for item in value["current_source_statuses"]
        )
        assert all(
            item["source_state"] == "research_locked" for item in value["current_source_statuses"]
        )
    if change == "g3_head":
        assert native_snapshot(lab) == native_before
        assert stored(lab)["current"]["revision"] == 3
    # Finite recheck does not allocate or repeat the premium source assembly.
    premium_queries = [
        q
        for q in sql
        if "from program_results" in q.lower() and "program_results.checklist" in q.lower()
    ]
    assert len(premium_queries) == 2  # Native G1 body then its exact raw checklist observation.
    after = native_snapshot(lab), stored(lab)
    refreshed = today(lab)
    assert refreshed["consistency"] == "component_reads"
    assert (native_snapshot(lab), stored(lab)) == after
