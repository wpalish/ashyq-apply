from pathlib import Path
s=Path(__file__).resolve().parent;out=s/'inputs6a-proposal'
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
put('backend/tests/test_research_input_provenance.py','''"""Actual-input provenance on supplied pure data and native owned stores, no network."""
from copy import deepcopy
from datetime import UTC, datetime
import pytest
from app.domain.profile_input_provenance import INPUT_OBSERVATION_KEY, input_status, observe_actual_inputs, pending_input_observation, profile_fingerprint
from app.models import ApplicantProfileRow, Job, ResearchRun
from app.pipeline.control import LeaseLost
from app.schemas.profile import ApplicantProfileIn
from tests.test_programme_observation_publication import claimed_runner, seed_run
from tests.test_preparation_graph_api import _capture
from tests.test_shared_route_api import assert_no_dml
pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")
NOW = datetime(2026, 10, 14, tzinfo=UTC)
def test_closed_inputs_exclude_only_local_label_and_preserve_real_changed_sections(profile):
    first = profile_fingerprint(profile)
    renamed = profile.model_copy(deep=True); renamed.display_name = "A different private local label"
    assert profile_fingerprint(renamed) == first
    changed = profile.model_copy(deep=True); changed.context.citizenship = "Different synthetic citizenship"
    second = profile_fingerprint(changed)
    assert first.digest != second.digest
    assert [name for name in first.sections if first.sections[name] != second.sections[name]] == ["context"]
    assert changed.context.citizenship not in first.model_dump_json()
@pytest.mark.parametrize("raw", [None, [], {}, {"schema_version": "wrong", "private": "synthetic_do_not_echo"}])
def test_legacy_and_corrupt_observations_stay_unknown_without_backfill(profile, raw):
    before = deepcopy(raw)
    assert observe_actual_inputs(raw, profile) is None
    read = input_status(raw, profile, NOW)
    assert read.state == "unknown" and read.changed_sections == [] and "synthetic_do_not_echo" not in read.model_dump_json()
    assert raw == before
def test_pending_actual_A_then_B_then_A_cannot_regress_mixed_to_current(profile):
    pending = pending_input_observation(); assert input_status(pending, profile, NOW).state == "pending"
    first = observe_actual_inputs(pending, profile); assert first is not None and input_status(first, profile, NOW).state == "current"
    changed = profile.model_copy(deep=True); changed.funding.requires_full_ride = not changed.funding.requires_full_ride
    assert input_status(first, changed, NOW).state == "changed"
    mixed = observe_actual_inputs(first, changed); assert mixed is not None
    again = observe_actual_inputs(mixed, profile); assert again is not None
    read = input_status(again, profile, NOW); assert read.state == "mixed" and read.changed_sections == ["funding"] and read.applicability == "not_assessed"
def test_native_checkpoint_input_read_is_owned_readonly_and_corrupt_metadata_does_not_echo(prep_lab):
    lab = prep_lab; run_id, job_id = seed_run(lab)
    with lab["factory"]() as session:
        session.get(ResearchRun, run_id).settings_snapshot = {INPUT_OBSERVATION_KEY: pending_input_observation()}; session.commit()
    runner = claimed_runner(lab, run_id, job_id)
    try:
        runner._save()
    finally:
        runner.session.close()
    response, sql = _capture(lab, lambda: lab["client"].get(f"/api/runs/{run_id}"))
    assert response.status_code == 200 and response.json()["profile_input_status"]["state"] == "current"; assert_no_dml(sql)
    assert INPUT_OBSERVATION_KEY not in response.json()["settings"]
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"]); payload = deepcopy(row.payload); payload["context"]["citizenship"] = "Different synthetic nationality"; row.payload = payload; session.commit()
    response = lab["client"].get(f"/api/runs/{run_id}")
    assert response.json()["profile_input_status"]["state"] == "changed"
    assert response.json()["profile_input_status"]["changed_sections"] == ["context"]
    with lab["factory"]() as session:
        session.get(ResearchRun, run_id).settings_snapshot = {INPUT_OBSERVATION_KEY: {"private": "synthetic_do_not_echo"}}; session.commit()
    response = lab["client"].get(f"/api/runs/{run_id}")
    assert response.json()["profile_input_status"]["state"] == "unknown" and "synthetic_do_not_echo" not in response.text
def test_native_lost_attempt_rolls_back_actual_inputs_with_the_progress_transaction(prep_lab):
    lab = prep_lab; run_id, job_id = seed_run(lab)
    with lab["factory"]() as session:
        session.get(ResearchRun, run_id).settings_snapshot = {INPUT_OBSERVATION_KEY: pending_input_observation()}; session.commit()
    runner = claimed_runner(lab, run_id, job_id)
    with lab["factory"]() as session:
        session.get(Job, job_id).attempts += 1; session.commit()
    try:
        with pytest.raises(LeaseLost): runner._save()
    finally:
        runner.session.close()
    with lab["factory"]() as session:
        raw = session.get(ResearchRun, run_id).settings_snapshot[INPUT_OBSERVATION_KEY]
        assert raw == pending_input_observation()
''')
put('backend/tests/test_result_read_freshness.py','''"""Current read age does not rewrite original native result/claim/evaluation history."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import pytest
from app.domain.result_read import claim_read, result_read
from app.models import ClaimRow, ProgramResultRow, ResearchRun
from app.schemas.claim import ClaimOut
from app.schemas.result import ProgramResult
from tests.test_preparation_api import full_case
from tests.test_preparation_graph_api import _capture
from tests.test_programme_observation_publication import seed_run
from tests.test_shared_route_api import assert_no_dml
pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")
NOW = datetime(2026, 10, 14, tzinfo=UTC)
def claim(*, status="VERIFIED_CURRENT", at=NOW - timedelta(days=30)):
    return ClaimOut(id="synthetic-claim", claim_type="admission_deadline", normalized_value="2027-01-15", source_url="https://example.edu/synthetic-date", official_domain=True,
        accessed_at=at, status=status, source_specificity="program_intake", original_text_excerpt="Synthetic date: 15 January 2027.")
def result(run_id="synthetic-run", result_id="synthetic-result", claims=None):
    return ProgramResult(id=result_id, run_id=run_id, university="Synthetic Uni", university_id="synthetic-uni", country="Synthetic", city="Synthetic city", program="BSc", degree="bachelor", intake="fall 2027", claims=claims or [])
def test_exact_window_updates_detached_age_and_preserves_original_assessment():
    original = result(claims=[claim()]); before = original.model_dump(mode="json")
    early = result_read(original, NOW - timedelta(microseconds=1)); at = result_read(original, NOW)
    assert early.claims[0].status == "VERIFIED_CURRENT" and not early.claims[0].is_stale
    assert at.claims[0].status == "POSSIBLY_STALE" and at.claims[0].is_stale
    assert at.read_freshness.stale_claim_count == 1 and at.read_freshness.assessment == "stored_evaluation"
    assert original.model_dump(mode="json") == before and at.eligibility == original.eligibility and at.ranking == original.ranking
@pytest.mark.parametrize("status", ["CONFLICTING", "SUPERSEDED", "UNVERIFIED", "NOT_FOUND", "NEEDS_OFFICIAL_CLARIFICATION"])
def test_age_never_rewrites_other_claim_lifecycle_states(status):
    old = claim(status=status); before = old.model_dump(mode="json"); read = claim_read(old, NOW)
    assert read.status == status and old.model_dump(mode="json") == before
def test_unavailable_evidence_has_no_invented_freshness_count():
    read = result_read(result(), NOW, evidence_available=False)
    assert read.read_freshness.evidence == "not_available" and read.read_freshness.stale_claim_count is None
def test_native_current_results_and_claims_read_leave_every_saved_payload_exact(prep_lab):
    lab = prep_lab; full_case(lab); run_id, _ = seed_run(lab)
    old_claim = claim(at=datetime.now(UTC) - timedelta(days=31))
    with lab["factory"]() as session:
        row = ProgramResultRow(run_id=run_id, dedupe_key="synthetic-freshness", university="Synthetic Uni", university_key="synthetic-uni", country="Synthetic", program="BSc", payload={})
        session.add(row); session.flush(); result_id = row.id
        c = ClaimRow(run_id=run_id, result_id=result_id, claim_type=old_claim.claim_type.value, status=old_claim.status.value, source_url=old_claim.source_url,
            accessed_at=old_claim.accessed_at, source_specificity=old_claim.source_specificity.value, payload={})
        session.add(c); session.flush(); old_claim.id = c.id; c.payload = old_claim.model_dump(mode="json"); row.payload = result(run_id, result_id, [old_claim]).model_dump(mode="json"); session.commit()
        payload_before = deepcopy(row.payload); claim_before = deepcopy(c.payload); c_id = c.id
    for path in [f"/api/runs/{run_id}/results", f"/api/runs/{run_id}/results/{result_id}", f"/api/runs/{run_id}/claims"]:
        response, sql = _capture(lab, lambda: lab["client"].get(path)); assert response.status_code == 200, response.text; assert_no_dml(sql)
        value = response.json(); value = value[0] if isinstance(value, list) else value
        source = value["claims"][0] if "claims" in value else value
        assert source["status"] == "POSSIBLY_STALE" and source["age_days"] >= 31
    with lab["factory"]() as session:
        assert session.get(ProgramResultRow, result_id).payload == payload_before
        assert session.get(ClaimRow, c_id).payload == claim_before
        assert session.get(ResearchRun, run_id).settings_snapshot.get("profile_input_observation_v1") is None
''')
print('External meaningful pure/native controls proposed; no source import/application or execution.')
