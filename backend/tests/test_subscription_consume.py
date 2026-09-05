"""Spending a unit: once per case, and never past zero."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.base import utcnow
from app.models.billing import Entitlement
from app.models.subscription import Subscription, SubscriptionStatus
from app.payments.entitlements import has_full_access
from app.payments.subscriptions import consume_for_case, quota_remaining


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("UNIMATCH_PAYMENTS_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def _case(session, org) -> str:
    from app.models import ApplicantProfileRow

    row = ApplicantProfileRow(organization_id=org.id, payload={})
    session.add(row)
    session.flush()
    return row.id


def _sub(session, org, **overrides) -> Subscription:
    fields = {
        "organization_id": org.id,
        "case_quota": 3,
        "duration_days": 365,
        "status": SubscriptionStatus.PENDING.value,
    }
    fields.update(overrides)
    row = Subscription(**fields)
    session.add(row)
    session.flush()
    return row


def test_without_a_subscription_nothing_is_spent(pg_session, org) -> None:
    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    assert result.granted is False
    assert result.reason == "no_subscription"


def test_the_first_use_activates_a_pending_subscription(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    pg_session.flush()
    pg_session.refresh(sub)

    assert result.granted is True
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.starts_at is not None
    assert sub.ends_at is not None
    assert (sub.ends_at - sub.starts_at).days == 365


def test_spending_opens_the_case(pg_session, org) -> None:
    _sub(pg_session, org)
    case_id = _case(pg_session, org)
    consume_for_case(pg_session, organization_id=org.id, profile_id=case_id)
    pg_session.flush()
    assert has_full_access(pg_session, org.id, case_id) is True


def test_the_same_case_is_never_charged_twice(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    case_id = _case(pg_session, org)
    first = consume_for_case(pg_session, organization_id=org.id, profile_id=case_id)
    pg_session.flush()
    second = consume_for_case(pg_session, organization_id=org.id, profile_id=case_id)
    pg_session.flush()

    assert first.granted is True
    assert second.granted is True
    assert second.reason == "already_entitled"
    pg_session.refresh(sub)
    assert quota_remaining(pg_session, sub) == 2


def test_the_quota_runs_out_and_stops(pg_session, org) -> None:
    sub = _sub(pg_session, org, case_quota=2)
    for _ in range(2):
        assert consume_for_case(
            pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
        ).granted
        pg_session.flush()

    last = consume_for_case(pg_session, organization_id=org.id, profile_id=_case(pg_session, org))
    pg_session.flush()
    assert last.granted is False
    assert last.reason == "no_subscription"
    pg_session.refresh(sub)
    assert sub.status == SubscriptionStatus.EXHAUSTED.value


def test_an_early_renewal_takes_over_when_the_first_runs_out(pg_session, org) -> None:
    """The point of the queue: unspent cases are not destroyed by renewing."""
    first = _sub(pg_session, org, case_quota=1)
    renewal = _sub(pg_session, org, case_quota=5)

    consume_for_case(pg_session, organization_id=org.id, profile_id=_case(pg_session, org))
    pg_session.flush()
    consume_for_case(pg_session, organization_id=org.id, profile_id=_case(pg_session, org))
    pg_session.flush()

    pg_session.refresh(first)
    pg_session.refresh(renewal)
    assert first.status == SubscriptionStatus.EXHAUSTED.value
    assert renewal.status == SubscriptionStatus.ACTIVE.value
    assert quota_remaining(pg_session, renewal) == 4


def test_an_expired_term_hands_over_to_the_renewal(pg_session, org) -> None:
    expiring = _sub(
        pg_session,
        org,
        case_quota=10,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=utcnow() - timedelta(days=400),
        ends_at=utcnow() - timedelta(days=1),
    )
    renewal = _sub(pg_session, org, case_quota=5)

    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    pg_session.flush()

    pg_session.refresh(expiring)
    pg_session.refresh(renewal)
    assert result.granted is True
    assert expiring.status == SubscriptionStatus.EXPIRED.value
    assert renewal.status == SubscriptionStatus.ACTIVE.value


def test_an_unlimited_contract_keeps_granting(pg_session, org) -> None:
    _sub(pg_session, org, case_quota=None)
    for _ in range(20):
        assert consume_for_case(
            pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
        ).granted
        pg_session.flush()


def test_a_cancelled_subscription_is_never_spent(pg_session, org) -> None:
    _sub(pg_session, org, status=SubscriptionStatus.CANCELLED.value)
    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    assert result.granted is False


def test_another_organization_cannot_spend_our_quota(pg_session, org) -> None:
    from app.models import ApplicantProfileRow, Organization

    _sub(pg_session, org, case_quota=5)
    other = Organization(name="Other", slug="other")
    pg_session.add(other)
    pg_session.flush()
    their_case = ApplicantProfileRow(organization_id=other.id, payload={})
    pg_session.add(their_case)
    pg_session.flush()

    result = consume_for_case(pg_session, organization_id=other.id, profile_id=their_case.id)
    assert result.granted is False
    assert pg_session.query(Entitlement).count() == 0


def test_a_second_transaction_is_blocked_while_the_first_holds_the_row(pg_engine) -> None:
    """The lock, asserted deterministically rather than by racing.

    Two threads started at a barrier finish too fast to collide reliably — an
    earlier version of this test passed with the lock removed, which means it
    proved nothing. So instead: hold the claim open in one transaction and give
    the second a short lock_timeout. With FOR UPDATE the second waits and times
    out; without it, it sails through and this test fails.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    from app.models import Organization
    from app.payments.subscriptions import _claim_usable_subscription

    Session = sessionmaker(bind=pg_engine, future=True)

    with Session() as setup:
        school = Organization(name="Race school", slug="race-school")
        setup.add(school)
        setup.flush()
        setup.add(
            Subscription(
                organization_id=school.id,
                case_quota=1,
                duration_days=365,
                status=SubscriptionStatus.ACTIVE.value,
                starts_at=utcnow() - timedelta(days=1),
                ends_at=utcnow() + timedelta(days=364),
            )
        )
        school_id = school.id
        setup.commit()

    holder = Session()
    try:
        claimed = _claim_usable_subscription(holder, school_id)
        assert claimed is not None  # holder now owns the row lock, uncommitted

        with Session() as contender:
            contender.execute(text("SET LOCAL lock_timeout = '500ms'"))
            with pytest.raises(OperationalError):
                _claim_usable_subscription(contender, school_id)
    finally:
        holder.rollback()
        holder.close()


#: A threaded version of the above was written and then deleted: eight threads
#: released from a barrier finish too fast to collide, so it passed with the
#: lock removed. A test that cannot fail is not evidence.
