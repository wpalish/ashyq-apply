"""Subscriptions: what is left, and which one is in force.

Everything here is a read. Retiring an exhausted subscription and starting the
next one are writes, and they live in ``consume_for_case`` — a GET must never
spend a customer's quota.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import ensure_utc, utcnow
from app.models.billing import Entitlement
from app.models.subscription import Subscription, SubscriptionStatus


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
