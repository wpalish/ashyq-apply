"""The billing tables, and the constraints that make double-charging hard."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.billing import (
    Entitlement,
    EntitlementKind,
    EntitlementSource,
    Order,
    OrderKind,
    OrderStatus,
    PaymentEvent,
    PaymentMethod,
)


@pytest.fixture
def tenant(pg_session):
    """A real organization and case, because both are foreign keys."""
    from app.models import ApplicantProfileRow, Organization

    org = Organization(name="Test org", slug="test-org")
    pg_session.add(org)
    pg_session.flush()
    case = ApplicantProfileRow(organization_id=org.id, payload={})
    pg_session.add(case)
    pg_session.flush()
    return {"organization_id": org.id, "profile_id": case.id}


def _order(session, tenant, **overrides) -> Order:
    fields = {
        "organization_id": tenant["organization_id"],
        "profile_id": tenant["profile_id"],
        "kind": OrderKind.CASE_UNLOCK.value,
        "amount_kzt": 4990,
        "status": OrderStatus.PENDING.value,
        "provider": "fake",
        "external_order_id": "ext-1",
        "method": PaymentMethod.PHONE.value,
        "phone_masked": "8707***4455",
    }
    fields.update(overrides)
    row = Order(**fields)
    session.add(row)
    session.flush()
    return row


def test_external_order_id_is_unique(pg_session, tenant) -> None:
    _order(pg_session, tenant, external_order_id="ext-dup")
    with pytest.raises(IntegrityError):
        _order(pg_session, tenant, external_order_id="ext-dup")


def test_one_case_entitlement_per_organization(pg_session, tenant) -> None:
    pg_session.add(
        Entitlement(
            organization_id=tenant["organization_id"],
            profile_id=tenant["profile_id"],
            kind=EntitlementKind.CASE_FULL.value,
            source=EntitlementSource.PURCHASE.value,
        )
    )
    pg_session.flush()
    pg_session.add(
        Entitlement(
            organization_id=tenant["organization_id"],
            profile_id=tenant["profile_id"],
            kind=EntitlementKind.CASE_FULL.value,
            source=EntitlementSource.MANUAL.value,
        )
    )
    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_one_organization_wide_entitlement_despite_null_profile(pg_session, tenant) -> None:
    """A plain unique constraint would let unlimited null rows through."""
    for _ in range(2):
        pg_session.add(
            Entitlement(
                organization_id=tenant["organization_id"],
                profile_id=None,
                kind=EntitlementKind.ORG_SUBSCRIPTION.value,
                source=EntitlementSource.SUBSCRIPTION.value,
            )
        )
    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_payment_events_accumulate_against_an_order(pg_session, tenant) -> None:
    order = _order(pg_session, tenant, external_order_id="ext-events")
    for source in ("webhook", "poll"):
        pg_session.add(
            PaymentEvent(
                order_id=order.id,
                source=source,
                event_type="invoice.status_changed",
                provider_status="paid",
                signature_valid=True,
            )
        )
    pg_session.flush()
    assert pg_session.query(PaymentEvent).filter(PaymentEvent.order_id == order.id).count() == 2


def test_runs_record_the_tier_they_were_allowed(pg_session, tenant) -> None:
    from app.models import ResearchRun

    run = ResearchRun(profile_id=tenant["profile_id"], stage="queued", access_tier="free")
    pg_session.add(run)
    pg_session.flush()
    assert run.access_tier == "free"


def test_a_run_is_full_tier_unless_told_otherwise(pg_session, tenant) -> None:
    from app.models import ResearchRun

    run = ResearchRun(profile_id=tenant["profile_id"], stage="queued")
    pg_session.add(run)
    pg_session.flush()
    assert run.access_tier == "full"
