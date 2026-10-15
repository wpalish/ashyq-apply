"""Current read age does not rewrite original native result/claim/evaluation history."""

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
    return ClaimOut(
        id="synthetic-claim",
        claim_type="admission_deadline",
        normalized_value="2027-01-15",
        source_url="https://example.edu/synthetic-date",
        official_domain=True,
        accessed_at=at,
        status=status,
        source_specificity="program_intake",
        original_text_excerpt="Synthetic date: 15 January 2027.",
    )


def result(run_id="synthetic-run", result_id="synthetic-result", claims=None):
    return ProgramResult(
        id=result_id,
        run_id=run_id,
        university="Synthetic Uni",
        university_id="synthetic-uni",
        country="Synthetic",
        city="Synthetic city",
        program="BSc",
        degree="bachelor",
        intake="fall 2027",
        claims=claims or [],
    )


def test_exact_window_updates_detached_age_and_preserves_original_assessment():
    original = result(claims=[claim()])
    before = original.model_dump(mode="json")
    early = result_read(original, NOW - timedelta(microseconds=1))
    at = result_read(original, NOW)
    assert early.claims[0].status == "VERIFIED_CURRENT" and (not early.claims[0].is_stale)
    assert at.claims[0].status == "POSSIBLY_STALE" and at.claims[0].is_stale
    assert (
        at.read_freshness.stale_claim_count == 1
        and at.read_freshness.assessment == "stored_evaluation"
    )
    assert (
        original.model_dump(mode="json") == before
        and at.eligibility == original.eligibility
        and (at.ranking == original.ranking)
    )


@pytest.mark.parametrize(
    "status",
    ["CONFLICTING", "SUPERSEDED", "UNVERIFIED", "NOT_FOUND", "NEEDS_OFFICIAL_CLARIFICATION"],
)
def test_age_never_rewrites_other_claim_lifecycle_states(status):
    old = claim(status=status)
    before = old.model_dump(mode="json")
    read = claim_read(old, NOW)
    assert read.status == status and old.model_dump(mode="json") == before


def test_unavailable_evidence_has_no_invented_freshness_count():
    read = result_read(result(), NOW, evidence_available=False)
    assert (
        read.read_freshness.evidence == "not_available"
        and read.read_freshness.stale_claim_count is None
    )


def test_native_current_results_and_claims_read_leave_every_saved_payload_exact(prep_lab):
    lab = prep_lab
    full_case(lab)
    run_id, _ = seed_run(lab)
    old_claim = claim(at=datetime.now(UTC) - timedelta(days=31))
    with lab["factory"]() as session:
        row = ProgramResultRow(
            run_id=run_id,
            dedupe_key="synthetic-freshness",
            university="Synthetic Uni",
            university_key="synthetic-uni",
            country="Synthetic",
            program="BSc",
            payload={},
        )
        session.add(row)
        session.flush()
        result_id = row.id
        c = ClaimRow(
            run_id=run_id,
            result_id=result_id,
            claim_type=old_claim.claim_type.value,
            status=old_claim.status.value,
            source_url=old_claim.source_url,
            accessed_at=old_claim.accessed_at,
            source_specificity=old_claim.source_specificity.value,
            payload={},
        )
        session.add(c)
        session.flush()
        old_claim.id = c.id
        c.payload = old_claim.model_dump(mode="json")
        row.payload = result(run_id, result_id, [old_claim]).model_dump(mode="json")
        session.commit()
        payload_before = deepcopy(row.payload)
        claim_before = deepcopy(c.payload)
        c_id = c.id
    for path in [
        f"/api/runs/{run_id}/results",
        f"/api/runs/{run_id}/results/{result_id}",
        f"/api/runs/{run_id}/claims",
    ]:
        response, sql = _capture(lab, lambda path=path: lab["client"].get(path))
        assert response.status_code == 200, response.text
        assert_no_dml(sql)
        value = response.json()
        value = value[0] if isinstance(value, list) else value
        source = value["claims"][0] if "claims" in value else value
        assert source["status"] == "POSSIBLY_STALE" and source["age_days"] >= 31
    with lab["factory"]() as session:
        assert session.get(ProgramResultRow, result_id).payload == payload_before
        assert session.get(ClaimRow, c_id).payload == claim_before
        assert (
            session.get(ResearchRun, run_id).settings_snapshot.get("profile_input_observation_v1")
            is None
        )
