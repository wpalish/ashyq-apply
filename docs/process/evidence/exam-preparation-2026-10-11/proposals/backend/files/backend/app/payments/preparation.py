"""Learning access reads a started term, never consumes research case quota."""

from __future__ import annotations

from datetime import datetime

from app.config import get_settings
from app.models.base import ensure_utc, utcnow
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.preparation import PreparationAccess
from sqlalchemy.orm import Session


def preparation_access(
    session: Session, organization_id: str, *, now: datetime | None = None
) -> PreparationAccess:
    if not get_settings().payments_enabled:
        return PreparationAccess(allowed=True, reason="development_mode", development_only=True)
    moment = ensure_utc(now or utcnow())
    assert moment is not None
    subscriptions = (
        session.query(Subscription)
        .filter(
            Subscription.organization_id == organization_id,
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.EXHAUSTED.value]
            ),
        )
        .order_by(Subscription.starts_at.desc(), Subscription.id)
        .all()
    )
    for subscription in subscriptions:
        starts = ensure_utc(subscription.starts_at)
        ends = ensure_utc(subscription.ends_at)
        if starts is not None and ends is not None and starts <= moment < ends:
            return PreparationAccess(
                allowed=True,
                reason="subscription_term",
                subscription_id=subscription.id,
                starts_at=starts,
                ends_at=ends,
            )
    return PreparationAccess(allowed=False, reason="no_eligible_subscription")
