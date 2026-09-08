"""What an unpaid case may and may not reach."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.corpus.demo_profile import DEMO_PROFILE
from tests.conftest import configure_from_env, sign_webhook


async def drain(limit: int = 10) -> int:
    """Run queued jobs to completion, as the worker process would."""
    from app.jobs.worker import Worker

    worker = Worker()
    executed = 0
    for _ in range(limit):
        job_id = worker.claim_one()
        if job_id is None:
            break
        await worker.execute(job_id)
        executed += 1
    return executed


@pytest.fixture
def free_run(paid_client, case_id):
    run = paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True}).json()
    asyncio.run(drain())
    return {"case_id": case_id, "run_id": run["id"]}


def _unlock(client, case_id: str) -> None:
    order = client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()
    body = json.dumps(
        {"event": "invoice.status_changed", "data": {"id": order["id"], "status": "paid"}}
    ).encode()
    client.post(
        "/webhooks/apipay",
        content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sign_webhook(body)},
    )


def test_a_free_run_is_capped_at_the_free_candidate_limit(paid_client, free_run) -> None:
    run = paid_client.get(f"/api/runs/{free_run['run_id']}").json()
    assert run["candidate_limit"] == 5


def test_a_free_run_records_its_tier(paid_client, free_run) -> None:
    from app.db import session_scope
    from app.models import ResearchRun

    with session_scope() as session:
        run = session.get(ResearchRun, free_run["run_id"])
        assert run is not None
        assert run.access_tier == "free"


def test_the_shortlist_is_cut_and_stripped(paid_client, free_run) -> None:
    rows = paid_client.get(f"/api/runs/{free_run['run_id']}/results").json()
    assert len(rows) <= 5
    for row in rows:
        assert row["university"]
        assert row["source_urls"] == []
        assert row["claims"] == []
        assert row["scholarships"] == []


def test_the_summary_stays_open(paid_client, free_run) -> None:
    """Counts are not evidence, and a free user must see there is more to buy."""
    response = paid_client.get(f"/api/runs/{free_run['run_id']}/summary")
    assert response.status_code == 200
    assert response.json()["total"] >= 0


@pytest.mark.parametrize(
    "path",
    [
        "/claims",
        "/conflicts",
        "/questions",
        "/export.csv",
        "/export.json",
        # Added by the ranking and calendar work after the paywall existed.
        # Each one returns whole-run material, so each one had to be gated when
        # the two branches met — a new read route is how a paywall quietly
        # stops being one.
        "/deadlines",
        "/deadlines.ics",
        "/shortlist",
    ],
)
def test_the_paid_routes_answer_402(paid_client, free_run, path: str) -> None:
    response = paid_client.get(f"/api/runs/{free_run['run_id']}{path}")
    assert response.status_code == 402
    body = response.json()
    assert body["code"] == "payment_required"
    assert body["profile_id"] == free_run["case_id"]
    assert body["price_kzt"] == 4990


def test_a_result_detail_answers_402(paid_client, free_run) -> None:
    rows = paid_client.get(f"/api/runs/{free_run['run_id']}/results").json()
    if not rows:
        pytest.skip("the demo corpus produced no rows for this profile")
    response = paid_client.get(f"/api/runs/{free_run['run_id']}/results/{rows[0]['id']}")
    assert response.status_code == 402


def test_document_collection_answers_402(paid_client, free_run) -> None:
    response = paid_client.post(f"/api/runs/{free_run['run_id']}/collect-documents")
    assert response.status_code == 402


def test_paying_opens_every_gated_route(paid_client, free_run) -> None:
    _unlock(paid_client, free_run["case_id"])
    for path in (
        "/claims",
        "/conflicts",
        "/questions",
        "/export.csv",
        "/deadlines",
        "/deadlines.ics",
        "/shortlist",
    ):
        response = paid_client.get(f"/api/runs/{free_run['run_id']}{path}")
        assert response.status_code == 200, path


def test_reranking_stays_free(paid_client, free_run) -> None:
    """It returns counts, fetches nothing, and reorders what is already shown.

    Gating it would charge for arithmetic on data the user can already see.
    """
    response = paid_client.post(
        f"/api/runs/{free_run['run_id']}/rerank",
        json={"priorities": None, "preferences": None, "funding": None},
    )
    assert response.status_code == 200, response.text


def test_paying_restores_the_full_shortlist_fields(paid_client, free_run) -> None:
    _unlock(paid_client, free_run["case_id"])
    rows = paid_client.get(f"/api/runs/{free_run['run_id']}/results").json()
    if not rows:
        pytest.skip("the demo corpus produced no rows for this profile")
    assert any(row["source_urls"] for row in rows)


def test_paying_queues_a_full_run(paid_client, free_run) -> None:
    _unlock(paid_client, free_run["case_id"])
    runs = paid_client.get("/api/runs").json()
    assert any(r["candidate_limit"] > 5 for r in runs)


def test_paying_leaves_nothing_for_the_user_to_start(paid_client, free_run) -> None:
    """The full run is queued by the payment, and a duplicate is refused.

    Both halves matter. Paying enqueues the run itself, so asking the user to
    press start again would be busywork; and because that run is in progress,
    the guard against concurrent research on one case answers 409 rather than
    quietly starting a second crawl of the same twenty universities.
    """
    _unlock(paid_client, free_run["case_id"])

    queued = [r for r in paid_client.get("/api/runs").json() if r["candidate_limit"] > 5]
    assert queued, "paying should have queued an uncapped run"

    duplicate = paid_client.post(
        "/api/runs", json={"profile_id": free_run["case_id"], "demo_mode": True}
    )
    assert duplicate.status_code == 409
    assert "already running" in duplicate.json()["detail"]


def test_with_payments_disabled_nothing_is_gated(tmp_path, monkeypatch, corpus_dir) -> None:
    """The flag must restore the pre-payments product exactly."""
    from fastapi.testclient import TestClient

    from app.config import get_settings

    configure_from_env(monkeypatch, tmp_path, corpus_dir, UNIMATCH_PAYMENTS_ENABLED="false")
    settings = get_settings()

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from app.main import app

    with TestClient(app) as client:
        case = client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()
        run = client.post("/api/runs", json={"profile_id": case["id"], "demo_mode": True}).json()
        asyncio.run(drain())
        assert run["candidate_limit"] > 5
        assert client.get(f"/api/runs/{run['id']}/claims").status_code == 200
        assert client.get(f"/api/runs/{run['id']}/export.csv").status_code == 200
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# T33 A1 (S1+S2): the decision/notes write routes and the GDPR export must
# answer an organization without the case entitlement with the free view, not
# with the stored payload. Written in post-fix form: on the baseline these are
# RED (the routes return full material), and they flip green when the fix
# projects through free_view. The last test guards the other direction: the
# fix must not trim what a paying organization receives.
# ---------------------------------------------------------------------------


def _canonical(body) -> str:
    """The contract's byte-identity method: canonical JSON, sorted keys."""
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def _seed_paid_material_into_first_row(run_id: str) -> str:
    """Make one row of this run carry paid material, deterministically.

    The demo corpus usually produces evidence on its own; seeding pins the RED
    to the paywall defect rather than to whatever the corpus shuffle produced.
    Test data only: schema-valid values written into the test database.
    """
    from app.db import SessionLocal
    from app.domain.enums import ClaimType
    from app.models import ClaimRow, ConflictRow, ProgramResultRow
    from app.schemas.claim import ClaimOut, Conflict
    from app.schemas.money import Money
    from app.schemas.result import FundingGap, ProgramResult, Scholarship
    from tests.conftest import make_claim

    url = "https://example.edu/programme"
    claim_out = ClaimOut(id="claim-seed-1", **make_claim("tuition", 5000, url=url).model_dump())
    conflict = Conflict(
        claim_type=ClaimType.TUITION,
        subject="Published tuition for the intake",
        claim_ids=["claim-seed-1"],
        values=[5000, 6500],
        source_urls=[url],
        question_for_admissions="Which tuition figure applies to this intake?",
    )
    with SessionLocal() as session:
        row = (
            session.query(ProgramResultRow)
            .filter(ProgramResultRow.run_id == run_id)
            .order_by(ProgramResultRow.score_total.desc(), ProgramResultRow.university)
            .first()
        )
        assert row is not None, "the demo corpus produced no rows to protect"
        result = ProgramResult.model_validate(row.payload)
        result.source_urls = [url]
        result.claims = [claim_out]
        result.conflicts = [conflict]
        result.scholarships = [Scholarship(id="scholarship-seed-1", name="Merit award (seeded)")]
        result.funding_gap = FundingGap(
            computable=True,
            gap=Money(amount=1200),
            total_cost=Money(amount=6200),
            confirmed_aid=Money(amount=5000),
        )
        result.verification_completeness = 1.0
        result.admission_deadline_raw = "2027-06-01 (seeded)"
        result.career_notes = "Alumni place into regional fintech (seeded)."
        row.payload = result.model_dump(mode="json")
        session.add(
            ClaimRow(
                run_id=run_id,
                result_id=row.id,
                claim_type=claim_out.claim_type.value,
                status=claim_out.status.value,
                source_url=url,
                source_specificity=claim_out.source_specificity.value,
                payload=claim_out.model_dump(mode="json"),
            )
        )
        session.add(
            ConflictRow(
                run_id=run_id,
                result_id=row.id,
                claim_type=ClaimType.TUITION.value,
                unresolved=True,
                payload=conflict.model_dump(mode="json"),
            )
        )
        session.commit()
        return row.id


def _assert_free_view_material_withheld(body: dict) -> None:
    """Every field free_view strips must arrive stripped."""
    assert body["claims"] == []
    assert body["conflicts"] == []
    assert body["scholarships"] == []
    assert body["requirement_checks"] == []
    assert body["missing_prerequisites"] == []
    assert body["hard_filter_failures"] == []
    assert body["unresolved"] == []
    assert body["source_urls"] == []
    assert body["funding_gap"] is None
    assert body["checklist"] is None
    assert body["verification_completeness"] == 0.0
    assert body["career_notes"] == ""
    assert body["post_study_work"] == ""
    assert body["work_during_study"] == ""
    assert body["admission_deadline_raw"] is None


def _stored_free_view(result_id: str) -> dict:
    """What the free shortlist shows for this row after the write."""
    from app.db import SessionLocal
    from app.models import ProgramResultRow
    from app.payments.entitlements import free_view
    from app.schemas.result import ProgramResult

    with SessionLocal() as session:
        row = session.get(ProgramResultRow, result_id)
        assert row is not None
        return free_view(ProgramResult.model_validate(row.payload)).model_dump(mode="json")


def test_decision_for_free_org_returns_the_free_view_projection(paid_client, free_run) -> None:
    """Recording a decision must not upgrade a free row to paid material.

    The defect: set_decision guards ownership only, so a free organization
    POSTs a decision and receives the full stored result back - claims,
    conflicts, funding gap, everything the paywall withholds on read.
    """
    result_id = _seed_paid_material_into_first_row(free_run["run_id"])
    response = paid_client.post(
        f"/api/runs/{free_run['run_id']}/results/{result_id}/decision",
        json={"decision": "approved", "reason": "fits the budget", "notes": "ask about housing"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    # The user's own fields are applied to the record first...
    assert body["user_decision"] == "approved"
    assert body["user_decision_reason"] == "fits the budget"
    assert body["user_notes"] == "ask about housing"
    assert body["decided_at"] is not None
    # ...then the answer is projected down to the free view, byte for byte.
    _assert_free_view_material_withheld(body)
    assert _canonical(body) == _canonical(_stored_free_view(result_id))


def test_notes_for_free_org_returns_the_free_view_projection(paid_client, free_run) -> None:
    """Saving a note must not upgrade a free row to paid material either.

    The twin defect: set_notes has the same ownership-only guard, so PATCHing
    a note leaks the same stored payload a decision leaks.
    """
    result_id = _seed_paid_material_into_first_row(free_run["run_id"])
    response = paid_client.patch(
        f"/api/runs/{free_run['run_id']}/results/{result_id}/notes",
        json={"notes": "call the admissions office in June"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["user_notes"] == "call the admissions office in June"
    assert body["user_decision"] == "undecided"  # a note never stamps a decision
    assert body["decided_at"] is None
    _assert_free_view_material_withheld(body)
    assert _canonical(body) == _canonical(_stored_free_view(result_id))


def test_gdpr_export_for_free_org_withholds_paid_material(paid_client, free_run) -> None:
    """The data-right export must not become a side door around the paywall.

    The defect: export_profile guards ownership only, so the GDPR document
    carries every full payload, claim and conflict of a case this organization
    never bought, while the same body promises "every claim and conflict".
    """
    result_id = _seed_paid_material_into_first_row(free_run["run_id"])
    response = paid_client.get(f"/api/profiles/{free_run['case_id']}/export")
    assert response.status_code == 200, response.text
    body = response.json()

    # The evidence tables are withheld wholesale. The counts stay, so the
    # document still says how much was withheld (PD-2), and the note stops
    # promising what it no longer contains.
    assert body["claims"] == []
    assert body["conflicts"] == []
    counts = body["counts"]
    assert counts["claims"] >= 1
    assert counts["conflicts"] >= 1
    assert counts["results"] >= 1
    assert "every claim and conflict" not in body["note"]

    rows = {row["id"]: row for row in body["results"]}
    assert result_id in rows, "the seeded row must still appear in the export"
    for row in rows.values():
        _assert_free_view_material_withheld(row)
        assert row["paid_content_withheld"] is True


def test_paying_opens_full_decision_notes_and_export(paid_client, free_run) -> None:
    """The guard: the fix must trim free answers, never the paid ones."""
    result_id = _seed_paid_material_into_first_row(free_run["run_id"])
    _unlock(paid_client, free_run["case_id"])

    decision = paid_client.post(
        f"/api/runs/{free_run['run_id']}/results/{result_id}/decision",
        json={"decision": "approved", "reason": "fits the budget", "notes": "ask about housing"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["user_decision"] == "approved"
    assert decision.json()["claims"], "a paying org must still receive the claims"
    assert decision.json()["source_urls"]
    assert decision.json()["funding_gap"] is not None

    notes = paid_client.patch(
        f"/api/runs/{free_run['run_id']}/results/{result_id}/notes",
        json={"notes": "call the admissions office in June"},
    )
    assert notes.status_code == 200, notes.text
    assert notes.json()["user_notes"] == "call the admissions office in June"
    assert notes.json()["claims"]

    export = paid_client.get(f"/api/profiles/{free_run['case_id']}/export")
    assert export.status_code == 200, export.text
    body = export.json()
    assert body["claims"], "a paying org's export still carries every claim"
    assert body["conflicts"]
    row = next(r for r in body["results"] if r["id"] == result_id)
    assert row["claims"]
    assert row["source_urls"]
    assert "paid_content_withheld" not in row, "paid export output is unchanged (PD-4)"
