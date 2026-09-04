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
    ["/claims", "/conflicts", "/questions", "/export.csv", "/export.json"],
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
    for path in ("/claims", "/conflicts", "/questions", "/export.csv"):
        response = paid_client.get(f"/api/runs/{free_run['run_id']}{path}")
        assert response.status_code == 200, path


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


def test_a_run_started_after_paying_is_not_capped(paid_client, free_run) -> None:
    _unlock(paid_client, free_run["case_id"])
    run = paid_client.post(
        "/api/runs", json={"profile_id": free_run["case_id"], "demo_mode": True}
    ).json()
    assert run["candidate_limit"] > 5


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
