"""Additive opt-in staged research API intent and cancellation controls."""

import pytest

from app.corpus.demo_profile import DEMO_PROFILE
from app.models import ResearchRun
from app.research import runtime, staging
from tests import test_api


@pytest.fixture
def client(tmp_path, monkeypatch, corpus_dir):
    yield from test_api.client.__wrapped__(tmp_path, monkeypatch, corpus_dir)


def profile_id(client):
    response = client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json"))
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def config(client, monkeypatch):
    from app.api import routes_research
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(routes_research, "get_settings", lambda: settings)
    return settings


def test_default_off_and_deep_request_rejected(client, config):
    pid = profile_id(client)
    response = client.post(
        "/api/runs", json={"profile_id": pid, "research_mode": "fast_then_deep", "demo_mode": False}
    )
    assert response.status_code == 422
    response = client.post("/api/runs", json={"profile_id": pid})
    assert response.status_code == 202
    assert response.json()["research_phase"] is None
    assert response.json()["question_states"] == {}
    assert response.json()["preliminary"] is False


def test_live_intent_and_idempotent_replay_survive_feature_change(client, config):
    config.research_staged = True
    pid = profile_id(client)
    payload = {
        "profile_id": pid,
        "research_mode": "fast_then_deep",
        "deep_tier": 900,
        "demo_mode": False,
    }
    response = client.post("/api/runs", json=payload, headers={"Idempotency-Key": "staged-click"})
    assert response.status_code == 202, response.text
    value = response.json()
    assert value["research_phase"] == "fast" and value["preliminary"] is True
    assert value["settings"][runtime.INTENT_KEY] == {
        "enabled": True,
        "mode": "fast_then_deep",
        "deep_tier": 900,
    }
    config.research_staged = False
    replay = client.post("/api/runs", json=payload, headers={"Idempotency-Key": "staged-click"})
    assert replay.status_code == 202 and replay.json()["id"] == value["id"]


def test_deep_demo_request_is_explicitly_rejected(client, config):
    config.research_staged = True
    response = client.post(
        "/api/runs",
        json={
            "profile_id": profile_id(client),
            "research_mode": "fast_then_deep",
            "demo_mode": True,
        },
    )
    assert response.status_code == 422


def test_cancel_preserves_budget_and_closed_episode_cannot_reset(client, config):
    from app.db import SessionLocal

    config.research_staged = True
    response = client.post(
        "/api/runs",
        json={
            "profile_id": profile_id(client),
            "research_mode": "fast_then_deep",
            "demo_mode": False,
        },
    )
    run_id = response.json()["id"]
    with SessionLocal() as session:
        run = session.get(ResearchRun, run_id)
        ledger = runtime.load(run.settings_snapshot)
        ledger = staging.StagedResearch.model_validate(
            {
                **ledger.model_dump(),
                "universities": (
                    staging.UniversityUsage(
                        university="catalogue:test", reads=12, queries=2, elapsed_ms=1000
                    ),
                ),
            }
        )
        run.settings_snapshot = runtime.replace(run.settings_snapshot, ledger)
        session.commit()
    cancelled = client.post(f"/api/runs/{run_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["research_phase"] == "cancelled"
    ledger = runtime.load(cancelled.json()["settings"])
    assert ledger.universities[0].reads == 12 and ledger.universities[0].queries == 2
    assert client.post(f"/api/runs/{run_id}/retry").status_code == 409


def test_preliminary_deep_queue_blocks_duplicate_run_and_documents(client, config):
    from app.db import SessionLocal
    from app.jobs.store import JobStore
    from app.models import Job

    config.research_staged = True
    pid = profile_id(client)
    response = client.post(
        "/api/runs", json={"profile_id": pid, "research_mode": "fast_then_deep", "demo_mode": False}
    )
    run_id = response.json()["id"]
    with SessionLocal() as session:
        run = session.get(ResearchRun, run_id)
        ledger = staging.advance(
            runtime.load(run.settings_snapshot), "deep_queued", **runtime.clock()
        )
        run.settings_snapshot = runtime.replace(run.settings_snapshot, ledger)
        run.stage = "awaiting_user_decision"
        session.query(Job).filter_by(run_id=run_id, kind="research").update({"status": "succeeded"})
        JobStore(session).enqueue(
            "research_deep", run_id=run_id, idempotency_key=ledger.enqueue_key
        )
        session.commit()
    duplicate = client.post("/api/runs", json={"profile_id": pid})
    assert duplicate.status_code == 409
    # The free entitlement may refuse first; neither path may enqueue documents.
    assert client.post(f"/api/runs/{run_id}/collect-documents").status_code in {402, 403, 409}
    with SessionLocal() as session:
        assert session.query(Job).filter_by(run_id=run_id, kind="documents").count() == 0
