"""Subscriptions: what is left, and which one is in force.

Everything here is a read. Retiring an exhausted subscription and starting the
next one are writes, and they live in ``consume_for_case`` — a GET must never
spend a customer's quota.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import ensure_utc, utcnow
from app.models.billing import Entitlement, EntitlementSource
from app.models.subscription import Subscription, SubscriptionStatus
from app.payments.entitlements import grant_case_access, has_full_access


def is_expired(subscription: Subscription, now: datetime | None = None) -> bool:
    """True when the term has passed. A subscription that never started has not."""
    ends_at = ensure_utc(subscription.ends_at)
    if ends_at is None:
        return False
    return (now or utcnow()) > ends_at


def spent(session: Session, subscription: Subscription) -> int:
    """How many cases this subscription has paid for, counted from the rows.

    Counted, never stored. A ``used_count`` column can drift from the rows it
    claims to describe, and the day it drifts is a dispute with a customer.
    """
    return (
        session.query(Entitlement).filter(Entitlement.subscription_id == subscription.id).count()
    )


def quota_remaining(session: Session, subscription: Subscription) -> int | None:
    """Cases left, or None for an unlimited contract."""
    if subscription.case_quota is None:
        return None
    return max(0, subscription.case_quota - spent(session, subscription))


def is_usable(session: Session, subscription: Subscription) -> bool:
    """Active, still within its term, and with something left to spend."""
    if subscription.status != SubscriptionStatus.ACTIVE.value:
        return False
    if is_expired(subscription):
        return False
    remaining = quota_remaining(session, subscription)
    return remaining is None or remaining > 0


def current_subscription(session: Session, organization_id: str) -> Subscription | None:
    """The active subscription, if it can still be spent. Never mutates."""
    active = session.scalar(
        select(Subscription).where(
            Subscription.organization_id == organization_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    if active is None or not is_usable(session, active):
        return None
    return active


def queued_subscriptions(session: Session, organization_id: str) -> list[Subscription]:
    """Bought but not started, oldest first — the order they will be used in."""
    return list(
        session.scalars(
            select(Subscription)
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status == SubscriptionStatus.PENDING.value,
            )
            .order_by(Subscription.created_at, Subscription.id)
        )
    )


@dataclass(frozen=True)
class ConsumeResult:
    granted: bool
    #: "granted", "already_entitled" or "no_subscription".
    reason: str
    subscription_id: str | None = None
    remaining: int | None = None


def consume_for_case(session: Session, *, organization_id: str, profile_id: str) -> ConsumeResult:
    """Spend one unit of the organization's quota on this case.

    The only place a unit is spent, and the only place a subscription changes
    state. It runs in this order:

      1. lock the organization's non-terminal subscriptions, so two counsellors
         clicking at once cannot both take the last unit;
      2. retire the active one if its term ended or its quota is gone;
      3. start the oldest queued one if nothing is active;
      4. grant the case, carrying the subscription that paid for it.
    """
    if has_full_access(session, organization_id, profile_id):
        # Already open. Re-running or re-reading a case costs nothing more.
        return ConsumeResult(granted=True, reason="already_entitled")

    subscription = _claim_usable_subscription(session, organization_id)
    if subscription is None:
        return ConsumeResult(granted=False, reason="no_subscription")

    grant_case_access(
        session,
        organization_id=organization_id,
        profile_id=profile_id,
        order_id=None,
        source=EntitlementSource.SUBSCRIPTION.value,
        subscription_id=subscription.id,
    )
    session.flush()

    remaining = quota_remaining(session, subscription)
    if remaining == 0:
        subscription.status = SubscriptionStatus.EXHAUSTED.value

    return ConsumeResult(
        granted=True,
        reason="granted",
        subscription_id=subscription.id,
        remaining=remaining,
    )


def _claim_usable_subscription(session: Session, organization_id: str) -> Subscription | None:
    """Retire what is finished, start what is next, return what can be spent."""
    query = select(Subscription).where(
        Subscription.organization_id == organization_id,
        Subscription.status.in_(
            (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.PENDING.value)
        ),
    )
    # Row locking is PostgreSQL's; SQLite serialises writers anyway.
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    rows = list(session.scalars(query))

    active = next((r for r in rows if r.status == SubscriptionStatus.ACTIVE.value), None)
    if active is not None:
        if is_expired(active):
            active.status = SubscriptionStatus.EXPIRED.value
            active = None
        elif not is_usable(session, active):
            active.status = SubscriptionStatus.EXHAUSTED.value
            active = None

    if active is not None:
        return active

    pending = sorted(
        (r for r in rows if r.status == SubscriptionStatus.PENDING.value),
        key=lambda r: (r.created_at, r.id),
    )
    if not pending:
        return None

    started = pending[0]
    started.status = SubscriptionStatus.ACTIVE.value
    started.starts_at = utcnow()
    started.ends_at = started.starts_at + timedelta(days=started.duration_days)
    session.flush()
    return started if is_usable(session, started) else None
