"""What a school bought, and how much of it is left.

Deliberately no ``used_count``: remaining is counted from the entitlement rows
that claim to have spent it. A counter can drift from those rows, and the day
it drifts is the day a customer disputes the bill.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class SubscriptionStatus(str, Enum):
    #: Sold, not yet started. Every grant begins here.
    PENDING = "pending"
    ACTIVE = "active"
    #: The quota ran out.
    EXHAUSTED = "exhausted"
    #: The term ended, whatever was left unspent.
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_SUBSCRIPTION_STATUSES = frozenset(
    {
        SubscriptionStatus.EXHAUSTED.value,
        SubscriptionStatus.EXPIRED.value,
        SubscriptionStatus.CANCELLED.value,
    }
)


class Subscription(TimestampedBase):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_org_status", "organization_id", "status"),)

    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    #: Cases included. Null means an unlimited contract.
    case_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: The term, applied when the subscription activates. A queued renewal has
    #: no start date until the one before it finishes.
    duration_days: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SubscriptionStatus.PENDING.value, index=True
    )
    #: The contract or invoice this row corresponds to, so it can be explained
    #: a year later.
    invoice_note: Mapped[str] = mapped_column(String(200), default="")
