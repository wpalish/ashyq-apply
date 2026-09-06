"""The order lifecycle: one writer, idempotent, and indifferent to arrival order."""

from __future__ import annotations

import pytest

from app.models.billing import Entitlement, Order, OrderStatus, PaymentEvent
from app.payments.entitlements import has_full_access
from app.payments.service import (
    AlreadyEntitled,
    InvalidPaymentRequest,
    apply_status,
    cancel_order,
    create_order,
    to_order_status,
)


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    settings = Settings(payments_enabled=True, payments_provider="fake")
    get_settings.cache_clear()
    reset_shared_fake()
    for target in (
        "app.config.get_settings",
        "app.payments.entitlements.get_settings",
        "app.payments.service.get_settings",
        "app.payments.provider.get_settings",
    ):
        monkeypatch.setattr(target, lambda: settings, raising=False)
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


def _order(session, tenant, *, method: str = "phone", phone: str | None = "87071234455") -> Order:
    return create_order(
        session,
        organization_id=tenant["organization_id"],
        profile_id=tenant["profile_id"],
        method=method,
        phone=phone,
    )


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        ("processing", OrderStatus.PENDING.value),
        ("pending", OrderStatus.PENDING.value),
        ("qr_scanned", OrderStatus.PENDING.value),
        ("paid", OrderStatus.PAID.value),
        ("cancelled", OrderStatus.CANCELLED.value),
        ("expired", OrderStatus.EXPIRED.value),
        ("something_new", OrderStatus.PENDING.value),
    ],
)
def test_provider_vocabulary_maps_to_ours(provider_status: str, expected: str) -> None:
    assert to_order_status(provider_status) == expected


def test_creating_a_phone_order_stores_a_masked_number(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    assert order.phone_masked == "8707***4455"
    assert "1234455" not in order.phone_masked
    assert order.amount_kzt == 4990
    assert order.status == OrderStatus.PENDING.value
    assert order.provider_invoice_id


def test_creating_a_qr_order_stores_the_payload_and_expiry(pg_session, tenant) -> None:
    order = _order(pg_session, tenant, method="qr", phone=None)
    assert order.qr_payload
    assert order.qr_expires_at is not None
    assert order.phone_masked == ""


def test_a_phone_order_without_a_phone_is_refused(pg_session, tenant) -> None:
    with pytest.raises(InvalidPaymentRequest):
        _order(pg_session, tenant, phone=None)


def test_an_unknown_method_is_refused(pg_session, tenant) -> None:
    with pytest.raises(InvalidPaymentRequest):
        _order(pg_session, tenant, method="carrier-pigeon")


def test_a_second_order_for_the_same_case_reuses_the_open_one(pg_session, tenant) -> None:
    first = _order(pg_session, tenant)
    pg_session.flush()
    second = _order(pg_session, tenant)
    assert second.id == first.id
    assert pg_session.query(Order).count() == 1


def test_an_already_unlocked_case_cannot_be_bought_again(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    with pytest.raises(AlreadyEntitled):
        _order(pg_session, tenant)


def test_paying_grants_access_and_records_the_moment(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    assert order.status == OrderStatus.PAID.value
    assert order.paid_at is not None
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is True


def test_a_replayed_paid_event_grants_once(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    for _ in range(3):
        apply_status(pg_session, order, "paid", source="webhook")
        pg_session.flush()
    assert pg_session.query(Entitlement).count() == 1


def test_a_late_pending_cannot_undo_a_paid(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    apply_status(pg_session, order, "processing", source="poll")
    pg_session.flush()
    assert order.status == OrderStatus.PAID.value
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is True


def test_paid_after_a_local_cancellation_still_grants(pg_session, tenant) -> None:
    """A QR cannot be cancelled at ApiPay, so a paid webhook can follow ours."""
    order = _order(pg_session, tenant, method="qr", phone=None)
    cancel_order(pg_session, order)
    assert order.status == OrderStatus.CANCELLED.value
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    assert order.status == OrderStatus.PAID.value
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is True


def test_every_call_is_journalled_even_when_nothing_changed(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    apply_status(pg_session, order, "paid", source="poll")
    pg_session.flush()
    events = (
        pg_session.query(PaymentEvent)
        .filter(PaymentEvent.order_id == order.id, PaymentEvent.event_type != "order.cancelled")
        .all()
    )
    assert len(events) == 2
    assert {e.source for e in events} == {"webhook", "poll"}


def test_the_journal_never_holds_a_phone_number(pg_session, tenant) -> None:
    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    for event in pg_session.query(PaymentEvent).all():
        assert "87071234455" not in (event.detail or "")


def test_paying_queues_a_full_run_for_the_case(pg_session, tenant) -> None:
    from app.models import Job, ResearchRun

    order = _order(pg_session, tenant)
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()

    run = pg_session.query(ResearchRun).filter(ResearchRun.profile_id == order.profile_id).one()
    assert run.access_tier == "full"
    assert pg_session.query(Job).filter(Job.kind == "research", Job.run_id == run.id).count() == 1


def test_opening_an_order_queues_its_reconciler(pg_session, tenant) -> None:
    from app.models import Job

    order = _order(pg_session, tenant)
    pg_session.flush()
    job = pg_session.query(Job).filter(Job.kind == "payment_reconcile").one()
    assert job.payload["order_id"] == order.id
