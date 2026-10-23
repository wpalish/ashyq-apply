"""Owned native profile commands: actual HTTP, sessions, transactions and receipts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier, Lock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.api.profile_commands import command_binding
from app.main import app
from app.models import ApplicantProfileRow, AuditEvent

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")


def profile(lab):
    response = lab["client"].get(f"/api/profiles/{lab['case']}")
    assert response.status_code == 200, response.text
    value = response.json()
    return {
        k: v
        for k, v in value.items()
        if k not in {"id", "revision", "write_receipt", "created_at", "updated_at"}
    }


def headers(revision=1, key=None):
    return {"X-Expected-Profile-Revision": str(revision), "Idempotency-Key": str(key or uuid4())}


def test_normalized_uuid_replay_is_immutable_and_current(shared_route_lab):
    lab = shared_route_lab
    path = f"/api/profiles/{lab['case']}"
    body = profile(lab)
    body["funding"]["max_annual_budget"] = 12500
    original = headers()
    first = lab["client"].put(path, json=body, headers=original)
    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 2
    assert first.json()["write_receipt"]["accepted_revision"] == 2
    # Later real edit proves replay doesn't reapply the historical command.
    newer = deepcopy(body)
    newer["display_name"] = "Synthetic later edit"
    second = lab["client"].put(path, json=newer, headers=headers(2))
    assert second.status_code == 200, second.text
    replay = lab["client"].put(path, json=body, headers=original)
    assert replay.status_code == 200, replay.text
    assert replay.json()["revision"] == 3
    assert replay.json()["display_name"] == newer["display_name"]
    assert replay.json()["write_receipt"] == first.json()["write_receipt"]
    changed = lab["client"].put(path, json=newer, headers=original)
    assert changed.status_code == 409, changed.text
    with lab["factory"]() as session:
        receipt = session.get(AuditEvent, original["Idempotency-Key"].replace("-", ""))
        assert receipt is not None
        assert "payload" not in receipt.detail and "body" not in receipt.detail
        assert len(receipt.detail["digest"]) == 64
        assert session.get(ApplicantProfileRow, lab["case"]).revision == 3
    exported = lab["client"].get(path + "/export")
    assert exported.status_code == 200
    assert exported.json()["profile_revision"] == 3


def test_missing_malformed_stale_headers_and_legacy_create(shared_route_lab):
    lab = shared_route_lab
    path = f"/api/profiles/{lab['case']}"
    body = profile(lab)
    for revision, code in [(None, 428), ("bad", 422), ("0", 422), ("2", 409)]:
        response = lab["client"].put(
            path,
            json=body,
            headers={} if revision is None else {"X-Expected-Profile-Revision": revision},
        )
        assert response.status_code == code, response.text
    assert lab["client"].get(path).json()["revision"] == 1
    legacy = lab["client"].post("/api/profiles", json=body)
    assert legacy.status_code == 201 and legacy.json()["revision"] == 1
    assert legacy.json()["write_receipt"] is None
    incomplete = lab["client"].post(
        "/api/profiles", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert incomplete.status_code == 400


def test_creation_commit_replay_does_not_duplicate_or_resurrect(shared_route_lab):
    lab = shared_route_lab
    body = profile(lab)
    original = {"Idempotency-Key": str(uuid4()), "X-Profile-Creation-Identity": str(uuid4())}
    first = lab["client"].post("/api/profiles", json=body, headers=original)
    assert first.status_code == 201, first.text
    identity = first.json()["id"]
    replay = lab["client"].post("/api/profiles", json=body, headers=original)
    assert replay.status_code == 201 and replay.json()["id"] == identity
    with lab["factory"]() as session:
        assert session.query(ApplicantProfileRow).count() == 2
        assert (
            session.query(AuditEvent)
            .filter(AuditEvent.id == original["Idempotency-Key"].replace("-", ""))
            .count()
            == 1
        )
    changed = {**body, "display_name": "Synthetic changed body"}
    assert lab["client"].post("/api/profiles", json=changed, headers=original).status_code == 409
    assert lab["client"].delete(f"/api/profiles/{identity}").status_code == 204
    gone = lab["client"].post("/api/profiles", json=body, headers=original)
    assert gone.status_code == 410, gone.text
    with lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, identity) is None
        assert session.get(AuditEvent, original["Idempotency-Key"].replace("-", "")) is not None


def contend(lab, calls, record_property):
    """Barrier BEFORE each actual first guarded SQL; both connections coexist.

    SQLite barrier precedes BEGIN IMMEDIATE, PostgreSQL precedes isolation SET.
    Do not wait for the blocked second writer while holding the first row lock.
    """
    barrier = Barrier(2, timeout=15)
    connections = set()
    gate = Lock()
    arrived = 0
    prefix = (
        "BEGIN IMMEDIATE" if lab["engine"].dialect.name == "sqlite" else "SET LOCAL lock_timeout"
    )

    def before(connection, _cursor, statement, _params, _context, _many):
        nonlocal arrived
        if statement.startswith(prefix):
            with gate:
                connections.add(id(connection))
                arrived += 1
                meet = arrived <= 2
            if meet:
                barrier.wait()

    event.listen(lab["engine"], "before_cursor_execute", before)
    clients = [TestClient(app), TestClient(app)]
    for client in clients:
        client.cookies.update(lab["client"].cookies)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(call, client) for call, client in zip(calls, clients, strict=True)
            ]
            responses = [future.result(timeout=40) for future in futures]
        assert len(connections) >= 2
        record_property("native_driver", lab["engine"].dialect.name)
        record_property("distinct_native_connections_at_first_write", len(connections))
        return responses
    finally:
        event.remove(lab["engine"], "before_cursor_execute", before)
        for client in clients:
            client.close()


@pytest.mark.parametrize("kind", ["put_put", "put_persisted_rerank"])
def test_two_actual_concurrent_profile_writers(shared_route_lab, kind, record_property):
    from app.models import ResearchRun

    lab = shared_route_lab
    body = profile(lab)
    path = f"/api/profiles/{lab['case']}"
    first = deepcopy(body)
    first["funding"]["max_annual_budget"] = 13500
    second = deepcopy(body)
    second["display_name"] = "Synthetic concurrent edit"
    if kind == "put_put":

        def second_call(client):
            return client.put(path, json=second, headers=headers())
    else:
        with lab["factory"]() as session:
            run = ResearchRun(profile_id=lab["case"], stage="completed", demo_mode=True)
            session.add(run)
            session.commit()
            run_id = run.id

        def second_call(client):
            return client.post(
                f"/api/runs/{run_id}/rerank",
                json={"persist": True, "funding": second["funding"]},
                headers=headers(),
            )

    responses = contend(
        lab,
        [lambda client: client.put(path, json=first, headers=headers()), second_call],
        record_property,
    )
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    current = lab["client"].get(path).json()
    assert current["revision"] == 2
    if responses[0].status_code == 200:
        assert current["funding"]["max_annual_budget"] == 13500
    elif kind == "put_put":
        assert current["display_name"] == second["display_name"]
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        assert row.display_name == row.payload["display_name"]
        assert row.revision == 2


def test_concurrent_create_exact_original_is_one_atomic_acceptance(
    shared_route_lab, record_property
):
    lab = shared_route_lab
    body = profile(lab)
    original = {"Idempotency-Key": str(uuid4()), "X-Profile-Creation-Identity": str(uuid4())}
    responses = contend(
        lab, [lambda c: c.post("/api/profiles", json=body, headers=original)] * 2, record_property
    )
    assert [r.status_code for r in responses] == [201, 201], [r.text for r in responses]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    with lab["factory"]() as session:
        assert session.query(ApplicantProfileRow).count() == 2


def test_persisted_rerank_replays_without_reapplying_and_default_does_not_write(shared_route_lab):
    from app.models import ResearchRun

    lab = shared_route_lab
    with lab["factory"]() as session:
        run = ResearchRun(profile_id=lab["case"], stage="completed", demo_mode=True)
        session.add(run)
        session.commit()
        run_id = run.id
    path = f"/api/runs/{run_id}/rerank"
    original = headers()
    body = {"persist": True, "priorities": ["academic", "funding"]}
    assert lab["client"].post(path, json=body).status_code == 428
    assert lab["client"].post(path, json={"gamma": 1}).status_code == 200
    assert lab["client"].get(f"/api/profiles/{lab['case']}").json()["revision"] == 1
    first = lab["client"].post(path, json=body, headers=original)
    assert first.status_code == 200, first.text
    assert first.json()["profile"]["revision"] == 2
    replay = lab["client"].post(path, json=body, headers=original)
    assert (
        replay.status_code == 200
        and replay.json()["write_receipt"] == first.json()["write_receipt"]
    )
    assert replay.json()["profile"]["revision"] == 2


def test_canonical_binding_has_semantic_object_order_and_exact_null_target_revision():
    def digest(body, **kw):
        return command_binding(
            "update", body, target=kw.get("target", "p"), expected_revision=kw.get("revision", 1)
        )

    assert digest({"a": 1, "b": {"c": None}}) == digest({"b": {"c": None}, "a": 1})
    assert (
        len({digest({}), digest({"a": None}), digest({}, revision=2), digest({}, target="q")}) == 4
    )
