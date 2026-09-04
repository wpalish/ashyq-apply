"""The backstop for a webhook that never arrives."""

from __future__ import annotations

import pytest

from app.models.billing import Entitlement, OrderStatus
from app.payments.entitlements import has_full_access
from app.payments.fake import FakeProvider
from app.payments.provider import get_provider
from app.payments.service import apply_status, create_order


def fake_provider() -> FakeProvider:
    """The configured provider, narrowed. ``simulate`` is the fake's own."""
    provider = get_provider()
    assert isinstance(provider, FakeProvider)
    return provider


@pytest.fixture(autouse=True)
def payments_on(monkeypatch, tmp_path):
    """Configure through the environment, for the reason conftest explains."""
    from app.config import get_settings
    from app.payments.fake import reset_shared_fake

    monkeypatch.setenv("UNIMATCH_PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("UNIMATCH_PAYMENTS_PROVIDER", "fake")
    monkeypatch.setenv("UNIMATCH_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("UNIMATCH_EXPORT_DIR", str(tmp_path / "exports"))
    get_settings.cache_clear()
    reset_shared_fake()
    yield
    get_settings.cache_clear()
    reset_shared_fake()


@pytest.fixture
def tenant(pg_session):
    from app.models import ApplicantProfileRow, Organization

    org = Organization(name="Test org", slug="test-org")
    pg_session.add(org)
    pg_session.flush()
    case = ApplicantProfileRow(organization_id=org.id, payload={})
    pg_session.add(case)
    pg_session.flush()
    return {"organization_id": org.id, "profile_id": case.id}


def _order(session, tenant, *, method: str = "phone", phone: str | None = "87071234455"):
    order = create_order(
        session,
        organization_id=tenant["organization_id"],
        profile_id=tenant["profile_id"],
        method=method,
        phone=phone,
    )
    session.flush()
    return order


def test_polling_finds_a_payment_no_webhook_reported(pg_session, tenant) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    order = _order(pg_session, tenant)
    fake_provider().simulate(order.provider_invoice_id, "paid")

    assert reconcile_order(pg_session, order.id) == OrderStatus.PAID.value
    pg_session.flush()
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is True


def test_polling_a_still_pending_order_changes_nothing(pg_session, tenant) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    order = _order(pg_session, tenant)
    assert reconcile_order(pg_session, order.id) == OrderStatus.PENDING.value
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is False


def test_polling_after_the_webhook_already_granted_is_harmless(pg_session, tenant) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    fake_provider().simulate(order.provider_invoice_id, "paid")
    reconcile_order(pg_session, order.id)
    pg_session.flush()
    assert pg_session.query(Entitlement).count() == 1


def test_an_expired_invoice_settles_the_order(pg_session, tenant) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    order = _order(pg_session, tenant, method="qr", phone=None)
    fake_provider().simulate(order.provider_invoice_id, "expired")
    assert reconcile_order(pg_session, order.id) == OrderStatus.EXPIRED.value


def test_an_order_past_its_life_expires_without_asking(pg_session, tenant) -> None:
    from datetime import timedelta

    from app.jobs.payment_reconcile import reconcile_order
    from app.models.base import utcnow

    order = _order(pg_session, tenant, method="qr", phone=None)
    order.qr_expires_at = utcnow() - timedelta(hours=1)
    pg_session.flush()
    assert reconcile_order(pg_session, order.id) == OrderStatus.EXPIRED.value


def test_a_provider_outage_leaves_the_order_alone(pg_session, tenant, monkeypatch) -> None:
    from app.jobs import payment_reconcile
    from app.payments.errors import ProviderUnavailable

    order = _order(pg_session, tenant)

    class Down:
        def get_invoice(self, _invoice_id):
            raise ProviderUnavailable("down")

    monkeypatch.setattr(payment_reconcile, "get_provider", lambda: Down())
    assert payment_reconcile.reconcile_order(pg_session, order.id) == OrderStatus.PENDING.value


def test_a_missing_order_is_not_an_error(pg_session) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    assert reconcile_order(pg_session, "0" * 32) == ""
