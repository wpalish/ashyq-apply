"""Actual-input provenance on supplied pure data and native owned stores, no network."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from app.domain.profile_input_provenance import (
    INPUT_OBSERVATION_KEY,
    input_status,
    observe_actual_inputs,
    pending_input_observation,
    profile_fingerprint,
)
from app.models import ApplicantProfileRow, Job, ResearchRun
from app.pipeline.control import LeaseLost
from tests.test_preparation_graph_api import _capture
from tests.test_programme_observation_publication import claimed_runner, seed_run
from tests.test_shared_route_api import assert_no_dml

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")
NOW = datetime(2026, 10, 14, tzinfo=UTC)


def test_closed_inputs_exclude_only_local_label_and_preserve_real_changed_sections(profile):
    first = profile_fingerprint(profile)
    renamed = profile.model_copy(deep=True)
    renamed.display_name = "A different private local label"
    assert profile_fingerprint(renamed) == first
    changed = profile.model_copy(deep=True)
    changed.context.citizenship = "Different synthetic citizenship"
    second = profile_fingerprint(changed)
    assert first.digest != second.digest
    assert [name for name in first.sections if first.sections[name] != second.sections[name]] == [
        "context"
    ]
    assert changed.context.citizenship not in first.model_dump_json()


@pytest.mark.parametrize(
    "raw", [None, [], {}, {"schema_version": "wrong", "private": "synthetic_do_not_echo"}]
)
def test_legacy_and_corrupt_observations_stay_unknown_without_backfill(profile, raw):
    before = deepcopy(raw)
    assert observe_actual_inputs(raw, profile) is None
    read = input_status(raw, profile, NOW)
    assert (
        read.state == "unknown"
        and read.changed_sections == []
        and ("synthetic_do_not_echo" not in read.model_dump_json())
    )
    assert raw == before


def test_pending_actual_A_then_B_then_A_cannot_regress_mixed_to_current(profile):
    pending = pending_input_observation()
    assert input_status(pending, profile, NOW).state == "pending"
    first = observe_actual_inputs(pending, profile)
    assert first is not None and input_status(first, profile, NOW).state == "current"
    changed = profile.model_copy(deep=True)
    changed.funding.requires_full_ride = not changed.funding.requires_full_ride
    assert input_status(first, changed, NOW).state == "changed"
    mixed = observe_actual_inputs(first, changed)
    assert mixed is not None
    again = observe_actual_inputs(mixed, profile)
    assert again is not None
    read = input_status(again, profile, NOW)
    assert (
        read.state == "mixed"
        and read.changed_sections == ["funding"]
        and (read.applicability == "not_assessed")
    )


def test_native_checkpoint_input_read_is_owned_readonly_and_corrupt_metadata_does_not_echo(
    prep_lab,
):
    lab = prep_lab
    run_id, job_id = seed_run(lab)
    with lab["factory"]() as session:
        session.get(ResearchRun, run_id).settings_snapshot = {
            INPUT_OBSERVATION_KEY: pending_input_observation()
        }
        session.commit()
    runner = claimed_runner(lab, run_id, job_id)
    try:
        runner._save()
    finally:
        runner.session.close()
    response, sql = _capture(lab, lambda: lab["client"].get(f"/api/runs/{run_id}"))
    assert (
        response.status_code == 200
        and response.json()["profile_input_status"]["state"] == "current"
    )
    assert_no_dml(sql)
    assert INPUT_OBSERVATION_KEY not in response.json()["settings"]
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        payload = deepcopy(row.payload)
        payload["context"]["citizenship"] = "Different synthetic nationality"
        row.payload = payload
        session.commit()
    response = lab["client"].get(f"/api/runs/{run_id}")
    assert response.json()["profile_input_status"]["state"] == "changed"
    assert response.json()["profile_input_status"]["changed_sections"] == ["context"]
    with lab["factory"]() as session:
        session.get(ResearchRun, run_id).settings_snapshot = {
            INPUT_OBSERVATION_KEY: {"private": "synthetic_do_not_echo"}
        }
        session.commit()
    response = lab["client"].get(f"/api/runs/{run_id}")
    assert (
        response.json()["profile_input_status"]["state"] == "unknown"
        and "synthetic_do_not_echo" not in response.text
    )


def test_native_lost_attempt_rolls_back_actual_inputs_with_the_progress_transaction(prep_lab):
    lab = prep_lab
    run_id, job_id = seed_run(lab)
    with lab["factory"]() as session:
        session.get(ResearchRun, run_id).settings_snapshot = {
            INPUT_OBSERVATION_KEY: pending_input_observation()
        }
        session.commit()
    runner = claimed_runner(lab, run_id, job_id)
    with lab["factory"]() as session:
        session.get(Job, job_id).attempts += 1
        session.commit()
    try:
        with pytest.raises(LeaseLost):
            runner._save()
    finally:
        runner.session.close()
    with lab["factory"]() as session:
        raw = session.get(ResearchRun, run_id).settings_snapshot[INPUT_OBSERVATION_KEY]
        assert raw == pending_input_observation()
