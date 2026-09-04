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
    return json.dumps(
        {"event": event, "data": {"id": order["id"], "status": status}}
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


def test_an_unknown_order_is_acknowledged_but_ignored(paid_client) -> None:
    body = json.dumps(
        {"event": "invoice.status_changed", "data": {"id": "no-such-order", "status": "paid"}}
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
