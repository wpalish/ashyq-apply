"""Actual cookie principals, namespace deletion and additive profile migration."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, text

from app.main import app
from app.models import ApplicantProfileRow, AuditEvent, Organization, OrganizationMembership, User

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")
PASSWORD = "synthetic-profile-passphrase-2026"


@pytest.fixture
def authorities(shared_route_lab):
    from app.config import get_settings

    lab = shared_route_lab
    # Capture the valid synthetic input before switching the same isolated lab to auth.
    with lab["factory"]() as session:
        body = deepcopy(session.get(ApplicantProfileRow, lab["case"]).payload)
    lab["monkeypatch"].setenv("UNIMATCH_AUTH_ENABLED", "true")
    lab["monkeypatch"].setenv("UNIMATCH_AUTH_RATE_LIMIT_PER_MINUTE", "10000")
    get_settings.cache_clear()
    clients = [TestClient(app), TestClient(app)]
    people = []
    try:
        for client in clients:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": f"profile-{uuid4().hex}@synthetic.invalid",
                    "password": PASSWORD,
                    "display_name": "Synthetic profile owner",
                    "organization_name": "Synthetic workspace",
                },
            )
            assert response.status_code == 201, response.text
            people.append(response.json())
        yield {**lab, "clients": clients, "people": people, "body": body}
    finally:
        for client in clients:
            client.close()
        get_settings.cache_clear()


def create(lab):
    key = {"Idempotency-Key": str(uuid4()), "X-Profile-Creation-Identity": str(uuid4())}
    response = lab["clients"][0].post("/api/profiles", json=lab["body"], headers=key)
    assert response.status_code == 201, response.text
    return response.json(), key


def test_foreign_target_is_404_before_known_command_identity(authorities):
    lab = authorities
    current, key = create(lab)
    path = f"/api/profiles/{current['id']}"
    response = lab["clients"][1].put(
        path, json=lab["body"], headers={**key, "X-Expected-Profile-Revision": "1"}
    )
    assert response.status_code == 404, response.text
    assert "write_receipt" not in response.json()
    assert lab["clients"][0].get(path).json()["revision"] == 1


def test_full_actor_identity_blocks_another_member_from_receipt_replay(authorities):
    lab = authorities
    current, key = create(lab)
    first, second = lab["people"]
    with lab["factory"]() as session:
        session.add(
            OrganizationMembership(
                user_id=second["user_id"], organization_id=first["organization_id"], role="owner"
            )
        )
        session.commit()
    response = lab["clients"][1].post(
        "/api/auth/session/organization", json={"organization_id": first["organization_id"]}
    )
    assert response.status_code == 200, response.text
    replay = lab["clients"][1].post("/api/profiles", json=lab["body"], headers=key)
    assert replay.status_code == 409, replay.text
    assert "write_receipt" not in replay.json()
    assert lab["clients"][1].get(f"/api/profiles/{current['id']}").status_code == 200


@pytest.mark.parametrize("fk_off", [False, True])
def test_account_erase_removes_command_namespace_and_cannot_recreate_old_case(
    authorities, fk_off, record_property
):
    lab = authorities
    current, key = create(lab)
    first = lab["people"][0]
    sqlite_off = fk_off and lab["engine"].dialect.name == "sqlite"

    def off(connection, _record):
        connection.execute("PRAGMA foreign_keys=OFF")

    if sqlite_off:
        event.listen(lab["engine"], "connect", off)
        lab["engine"].dispose()
    try:
        if sqlite_off:
            with lab["engine"].connect() as connection:
                assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 0
        removed = lab["clients"][0].post(
            "/api/auth/me/delete", json={"password": PASSWORD, "confirm_delete_data": True}
        )
        assert removed.status_code == 204, removed.text
        with lab["factory"]() as session:
            assert session.get(User, first["user_id"]) is None
            assert session.get(Organization, first["organization_id"]) is None
            assert session.get(ApplicantProfileRow, current["id"]) is None
            assert session.get(AuditEvent, key["Idempotency-Key"].replace("-", "")) is None
        old = lab["clients"][0].post("/api/profiles", json=lab["body"], headers=key)
        assert old.status_code == 401, old.text
        record_property("native_driver", lab["engine"].dialect.name)
        record_property("sqlite_fk_off", sqlite_off)
    finally:
        if sqlite_off:
            event.remove(lab["engine"], "connect", off)
            lab["engine"].dispose()


def test_legacy_revision_upgrade_downgrade_roundtrip_preserves_exact_profile(shared_route_lab):
    from alembic import command

    from app.db import _alembic_config, migrate_to_head

    lab = shared_route_lab
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        original = deepcopy(row.payload)
        assert row.revision == 1
    url = lab["engine"].url.render_as_string(hide_password=False)
    command.downgrade(_alembic_config(url), "a0d94e902027")
    assert "revision" not in {
        c["name"] for c in inspect(lab["engine"]).get_columns("applicant_profiles")
    }
    with lab["engine"].connect() as connection:
        assert (
            connection.execute(
                text("SELECT id FROM applicant_profiles WHERE id=:id"), {"id": lab["case"]}
            ).scalar_one()
            == lab["case"]
        )
    migrate_to_head(url)
    with lab["factory"]() as session:
        restored = session.get(ApplicantProfileRow, lab["case"])
        assert restored.payload == original and restored.revision == 1


def test_downgrade_refuses_discarding_accepted_profile_revisions(shared_route_lab):
    from alembic import command

    from app.db import _alembic_config

    lab = shared_route_lab
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        body = deepcopy(row.payload)
    accepted = lab["client"].put(
        f"/api/profiles/{lab['case']}", json=body, headers={"X-Expected-Profile-Revision": "1"}
    )
    assert accepted.status_code == 200, accepted.text
    with pytest.raises(RuntimeError, match="Cannot discard accepted profile revisions"):
        command.downgrade(
            _alembic_config(lab["engine"].url.render_as_string(hide_password=False)), "a0d94e902027"
        )
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        assert row.revision == 2 and row.payload == body
