"""Reads never spend, and never change a row."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.base import utcnow
from app.models.subscription import Subscription, SubscriptionStatus
from app.payments.subscriptions import (
    current_subscription,
    is_expired,
    queued_subscriptions,
    quota_remaining,
    spent,
)


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def _sub(session, org, **overrides) -> Subscription:
    fields = {
        "organization_id": org.id,
        "case_quota": 50,
        "duration_days": 365,
        "status": SubscriptionStatus.ACTIVE.value,
        "starts_at": utcnow() - timedelta(days=1),
        "ends_at": utcnow() + timedelta(days=364),
    }
    fields.update(overrides)
    row = Subscription(**fields)
    session.add(row)
    session.flush()
    return row


def _spend(session, org, sub, n: int) -> None:
    from app.models import ApplicantProfileRow
    from app.models.billing import Entitlement, EntitlementKind, EntitlementSource

    for _ in range(n):
        case = ApplicantProfileRow(organization_id=org.id, payload={})
        session.add(case)
        session.flush()
        session.add(
            Entitlement(
                organization_id=org.id,
                profile_id=case.id,
                kind=EntitlementKind.CASE_FULL.value,
                source=EntitlementSource.SUBSCRIPTION.value,
                subscription_id=sub.id,
            )
        )
    session.flush()


def test_a_fresh_subscription_has_its_whole_quota(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    assert spent(pg_session, sub) == 0
    assert quota_remaining(pg_session, sub) == 50


def test_remaining_counts_the_rows_that_spent_it(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    _spend(pg_session, org, sub, 3)
    assert spent(pg_session, sub) == 3
    assert quota_remaining(pg_session, sub) == 47


def test_an_unlimited_contract_never_runs_out(pg_session, org) -> None:
    sub = _sub(pg_session, org, case_quota=None)
    _spend(pg_session, org, sub, 100)
    assert quota_remaining(pg_session, sub) is None


def test_a_term_that_has_passed_is_expired(pg_session, org) -> None:
    sub = _sub(pg_session, org, ends_at=utcnow() - timedelta(days=1))
    assert is_expired(sub) is True


def test_a_pending_subscription_is_not_expired(pg_session, org) -> None:
    """It has no end date yet, because it has not started."""
    sub = _sub(
        pg_session, org, status=SubscriptionStatus.PENDING.value, starts_at=None, ends_at=None
    )
    assert is_expired(sub) is False


def test_the_current_subscription_is_the_active_usable_one(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    found = current_subscription(pg_session, org.id)
    assert found is not None
    assert found.id == sub.id


def test_an_exhausted_subscription_is_not_current(pg_session, org) -> None:
    sub = _sub(pg_session, org, case_quota=2)
    _spend(pg_session, org, sub, 2)
    assert current_subscription(pg_session, org.id) is None


def test_an_expired_subscription_is_not_current(pg_session, org) -> None:
    _sub(pg_session, org, ends_at=utcnow() - timedelta(days=1))
    assert current_subscription(pg_session, org.id) is None


def test_a_cancelled_subscription_is_not_current(pg_session, org) -> None:
    _sub(pg_session, org, status=SubscriptionStatus.CANCELLED.value)
    assert current_subscription(pg_session, org.id) is None


def test_an_organization_without_one_has_none(pg_session, org) -> None:
    assert current_subscription(pg_session, org.id) is None


def test_queued_subscriptions_are_the_pending_ones_oldest_first(pg_session, org) -> None:
    # Explicit timestamps: two rows created in the same microsecond tie on
    # created_at and fall back to a random id, which is not an order.
    _sub(pg_session, org)
    first = _sub(
        pg_session,
        org,
        status=SubscriptionStatus.PENDING.value,
        starts_at=None,
        ends_at=None,
        created_at=utcnow() - timedelta(hours=2),
    )
    second = _sub(
        pg_session,
        org,
        status=SubscriptionStatus.PENDING.value,
        starts_at=None,
        ends_at=None,
        created_at=utcnow() - timedelta(hours=1),
    )
    queued = queued_subscriptions(pg_session, org.id)
    assert [q.id for q in queued] == [first.id, second.id]


def test_reading_does_not_change_a_subscription(pg_session, org) -> None:
    """The read path must never retire or activate anything."""
    sub = _sub(pg_session, org, ends_at=utcnow() - timedelta(days=1))
    current_subscription(pg_session, org.id)
    pg_session.refresh(sub)
    assert sub.status == SubscriptionStatus.ACTIVE.value
