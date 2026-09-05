"""What a sold subscription looks like in the database."""

from __future__ import annotations

import pytest

from app.models.subscription import (
    TERMINAL_SUBSCRIPTION_STATUSES,
    Subscription,
    SubscriptionStatus,
)


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def test_a_grant_starts_pending_and_undated(pg_session, org) -> None:
    """Activation belongs to consume_for_case, so a grant has no dates yet."""
    sub = Subscription(
        organization_id=org.id, case_quota=50, duration_days=365, invoice_note="Contract 14/26"
    )
    pg_session.add(sub)
    pg_session.flush()
    assert sub.status == SubscriptionStatus.PENDING.value
    assert sub.starts_at is None
    assert sub.ends_at is None


def test_an_unlimited_contract_has_no_quota(pg_session, org) -> None:
    sub = Subscription(organization_id=org.id, case_quota=None, duration_days=365)
    pg_session.add(sub)
    pg_session.flush()
    assert sub.case_quota is None


def test_exhausted_expired_and_cancelled_are_terminal() -> None:
    assert frozenset(
        {
            SubscriptionStatus.EXHAUSTED.value,
            SubscriptionStatus.EXPIRED.value,
            SubscriptionStatus.CANCELLED.value,
        }
    ) == TERMINAL_SUBSCRIPTION_STATUSES


def test_an_entitlement_can_name_the_subscription_that_paid_for_it(pg_session, org) -> None:
    from app.models import ApplicantProfileRow
    from app.models.billing import Entitlement, EntitlementKind, EntitlementSource

    case = ApplicantProfileRow(organization_id=org.id, payload={})
    sub = Subscription(organization_id=org.id, case_quota=50, duration_days=365)
    pg_session.add_all([case, sub])
    pg_session.flush()

    pg_session.add(
        Entitlement(
            organization_id=org.id,
            profile_id=case.id,
            kind=EntitlementKind.CASE_FULL.value,
            source=EntitlementSource.SUBSCRIPTION.value,
            subscription_id=sub.id,
        )
    )
    pg_session.flush()
    spent = pg_session.query(Entitlement).filter(Entitlement.subscription_id == sub.id).count()
    assert spent == 1


def test_the_org_wide_entitlement_kind_is_gone() -> None:
    """A quota grants the right to spend, not blanket access."""
    from app.models.billing import EntitlementKind

    assert not hasattr(EntitlementKind, "ORG_SUBSCRIPTION")
