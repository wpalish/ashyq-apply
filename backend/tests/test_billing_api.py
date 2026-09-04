"""The billing endpoints, and the 402 the frontend keys off."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.corpus.demo_profile import DEMO_PROFILE


@pytest.fixture
def paid_client(tmp_path, monkeypatch, corpus_dir):
    """A client with payments switched on and the fake provider behind them."""
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    # Modules bind `get_settings` by name at import time, so patching
    # app.config.get_settings only reaches modules imported after the patch —
    # which makes it depend on which test ran first. The environment reaches
    # every one of them, whenever they were imported.
    monkeypatch.setenv("UNIMATCH_PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("UNIMATCH_PAYMENTS_PROVIDER", "fake")
    monkeypatch.setenv("UNIMATCH_APIPAY_WEBHOOK_SECRET", "whsec-test")

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'billing.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
        payments_enabled=True,
        payments_provider="fake",
        apipay_webhook_secret="whsec-test",
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    reset_shared_fake()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    reset_shared_fake()


@pytest.fixture
def case_id(paid_client) -> str:
    return paid_client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()["id"]


def test_pricing_states_the_amount_and_the_currency(paid_client) -> None:
    body = paid_client.get("/api/billing/pricing").json()
    assert body["case_unlock_price_kzt"] == 4990
    assert body["currency"] == "KZT"
    assert isinstance(body["includes"], list)
    assert body["includes"]


def test_a_new_case_has_no_entitlement(paid_client, case_id) -> None:
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["full_access"] is False


def test_creating_a_phone_order(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["phone_masked"] == "8707***4455"
    assert body["amount_kzt"] == 4990


def test_the_client_cannot_choose_the_price(paid_client, case_id) -> None:
    body = paid_client.post(
        "/api/billing/orders",
        json={
            "profile_id": case_id,
            "method": "phone",
            "phone": "87071234455",
            "amount_kzt": 1,
            "price_kzt": 1,
        },
    ).json()
    assert body["amount_kzt"] == 4990


def test_the_full_phone_number_never_comes_back(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    )
    assert "87071234455" not in response.text


def test_creating_a_qr_order_returns_a_payload(paid_client, case_id) -> None:
    body = paid_client.post(
        "/api/billing/orders", json={"profile_id": case_id, "method": "qr"}
    ).json()
    assert body["qr_payload"]
    assert body["qr_expires_at"]


def test_a_phone_order_without_a_number_is_rejected(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/orders", json={"profile_id": case_id, "method": "phone"}
    )
    assert response.status_code == 400


def test_an_unknown_case_is_not_purchasable(paid_client) -> None:
    response = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": "0" * 32, "method": "phone", "phone": "87071234455"},
    )
    assert response.status_code == 404


def test_an_order_can_be_read_back_and_cancelled(paid_client, case_id) -> None:
    order = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()
    assert paid_client.get(f"/api/billing/orders/{order['id']}").json()["id"] == order["id"]
    cancelled = paid_client.post(f"/api/billing/orders/{order['id']}/cancel").json()
    assert cancelled["status"] == "cancelled"


def test_another_tenants_order_is_invisible(paid_client, case_id) -> None:
    """404, not 403 — the same convention the rest of the API follows."""
    order = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()

    from app.db import session_scope
    from app.models.billing import Order

    with session_scope() as session:
        row = session.get(Order, order["id"])
        assert row is not None
        row.organization_id = "ffffffffffffffffffffffffffffffff"

    assert paid_client.get(f"/api/billing/orders/{order['id']}").status_code == 404
