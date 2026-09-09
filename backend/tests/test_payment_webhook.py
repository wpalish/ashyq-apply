"""The webhook: signed, size-capped, idempotent, and never trusted blindly."""

from __future__ import annotations

import json

import pytest

from tests.conftest import sign_webhook


@pytest.fixture
def order(paid_client, case_id) -> dict:
    return paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()


def _body(order: dict, status: str = "paid", event: str = "invoice.status_changed") -> bytes:
    """The shape ApiPay documents: invoice fields at the top level."""
    return json.dumps({"event": event, "id": order["id"], "status": status}).encode()


def _nested_body(order: dict, status: str = "paid") -> bytes:
    """The nested repeat of the same fields, which we also accept."""
    return json.dumps(
        {"event": "invoice.status_changed", "invoice": {"id": order["id"], "status": status}}
    ).encode()


def _post(client, body: bytes, signature: str | None = None):
    return client.post(
        "/webhooks/apipay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": sign_webhook(body) if signature is None else signature,
        },
    )


def _full_access(client, profile_id: str) -> bool:
    return client.get(f"/api/billing/entitlements?profile_id={profile_id}").json()["full_access"]


def test_a_signed_paid_event_unlocks_the_case(paid_client, order) -> None:
    assert _post(paid_client, _body(order)).status_code == 200
    assert _full_access(paid_client, order["profile_id"]) is True


def test_an_unsigned_event_is_refused(paid_client, order) -> None:
    assert _post(paid_client, _body(order), signature="").status_code == 401


def test_a_wrong_signature_is_refused(paid_client, order) -> None:
    assert _post(paid_client, _body(order), signature="sha256=deadbeef").status_code == 401


def test_a_tampered_body_is_refused(paid_client, order) -> None:
    body = _body(order)
    response = paid_client.post(
        "/webhooks/apipay",
        content=body.replace(b"paid", b"pai0"),
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sign_webhook(body)},
    )
    assert response.status_code == 401


def test_a_refused_event_does_not_unlock_anything(paid_client, order) -> None:
    _post(paid_client, _body(order), signature="sha256=deadbeef")
    assert _full_access(paid_client, order["profile_id"]) is False


def test_a_replayed_event_unlocks_once(paid_client, order) -> None:
    for _ in range(3):
        assert _post(paid_client, _body(order)).status_code == 200

    from app.db import session_scope
    from app.models.billing import Entitlement

    with session_scope() as session:
        assert session.query(Entitlement).count() == 1


def test_the_nested_payload_shape_also_unlocks(paid_client, order) -> None:
    assert _post(paid_client, _nested_body(order)).status_code == 200
    assert _full_access(paid_client, order["profile_id"]) is True


def test_an_unknown_order_is_acknowledged_but_ignored(paid_client) -> None:
    body = json.dumps(
        {"event": "invoice.status_changed", "id": "no-such-order", "status": "paid"}
    ).encode()
    assert _post(paid_client, body).status_code == 200


def test_an_unknown_event_type_is_acknowledged_and_not_acted_on(paid_client, order) -> None:
    assert _post(paid_client, _body(order, event="catalog.item_processed")).status_code == 200
    assert _full_access(paid_client, order["profile_id"]) is False


def test_an_oversized_body_is_refused(paid_client) -> None:
    body = b'{"padding":"' + b"x" * 70_000 + b'"}'
    assert _post(paid_client, body).status_code == 413


def test_malformed_json_with_a_good_signature_is_a_bad_request(paid_client) -> None:
    assert _post(paid_client, b"{not json").status_code == 400


def test_an_expired_event_settles_the_order_without_granting(paid_client, order) -> None:
    assert _post(paid_client, _body(order, status="expired")).status_code == 200
    assert paid_client.get(f"/api/billing/orders/{order['id']}").json()["status"] == "expired"
    assert _full_access(paid_client, order["profile_id"]) is False


class TestAnUnconfiguredSecretIsNotASecret:
    """Payments on, no webhook secret: the callback must verify nothing.

    The fake provider used to be handed the literal string ``test-secret`` when
    ``UNIMATCH_APIPAY_WEBHOOK_SECRET`` was unset, so a deployment that turned
    payments on and forgot the secret accepted a forged ``paid`` event from
    anyone who had read this repository — and a forged ``paid`` event grants
    the entitlement and queues a full research run.
    """

    @pytest.fixture
    def unsigned_client(self, tmp_path, monkeypatch, corpus_dir):
        from fastapi.testclient import TestClient

        from app.config import get_settings
        from app.payments.fake import reset_shared_fake
        from tests.conftest import configure_from_env

        configure_from_env(
            monkeypatch,
            tmp_path,
            corpus_dir,
            UNIMATCH_PAYMENTS_ENABLED="true",
            UNIMATCH_PAYMENTS_PROVIDER="fake",
            UNIMATCH_APIPAY_WEBHOOK_SECRET="",
        )
        reset_shared_fake()
        settings = get_settings()

        import app.db as db_module

        engine = db_module.create_engine(
            settings.database_url, connect_args={"check_same_thread": False}
        )
        monkeypatch.setattr(db_module, "engine", engine)
        monkeypatch.setattr(
            db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True)
        )
        db_module.migrate_to_head(settings.database_url)

        from app.main import app

        with TestClient(app) as client:
            yield client
        get_settings.cache_clear()
        reset_shared_fake()

    def test_the_old_default_secret_no_longer_signs_anything(self, unsigned_client) -> None:
        import hashlib
        import hmac

        from app.corpus.demo_profile import DEMO_PROFILE

        profile_id = unsigned_client.post(
            "/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")
        ).json()["id"]
        order = unsigned_client.post(
            "/api/billing/orders", json={"profile_id": profile_id, "method": "qr"}
        ).json()

        body = json.dumps(
            {"event": "invoice.status_changed", "id": order["id"], "status": "paid"}
        ).encode()
        forged = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

        response = unsigned_client.post(
            "/webhooks/apipay", content=body, headers={"X-Webhook-Signature": forged}
        )

        assert response.status_code == 401
        assert _full_access(unsigned_client, profile_id) is False

    def test_an_empty_key_signature_is_refused_too(self, unsigned_client) -> None:
        import hashlib
        import hmac

        body = json.dumps({"event": "invoice.status_changed", "id": "x", "status": "paid"}).encode()
        forged = "sha256=" + hmac.new(b"", body, hashlib.sha256).hexdigest()

        response = unsigned_client.post(
            "/webhooks/apipay", content=body, headers={"X-Webhook-Signature": forged}
        )

        assert response.status_code == 401
