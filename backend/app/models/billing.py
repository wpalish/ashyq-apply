"""Orders, the journal of what the provider told us, and what was granted.

Only ``Entitlement`` is consulted by the rest of the application. ``Order`` and
``PaymentEvent`` exist so that a disputed payment can be reconstructed from the
database rather than from memory.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedBase, new_id, utcnow


class OrderKind(str, Enum):
    CASE_UNLOCK = "case_unlock"


class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


#: A settled order is never reopened by a later, lesser status.
TERMINAL_ORDER_STATUSES = frozenset(
    {
        OrderStatus.PAID.value,
        OrderStatus.CANCELLED.value,
        OrderStatus.EXPIRED.value,
        OrderStatus.FAILED.value,
    }
)


class PaymentMethod(str, Enum):
    PHONE = "phone"
    QR = "qr"


class EntitlementKind(str, Enum):
    #: The only kind. Phase 1 reserved an org-wide kind for a subscription that
    #: granted blanket access; phase 2 made a subscription a right to *spend*,
    #: so that shape was removed rather than left to be misread.
    CASE_FULL = "case_full"


class EntitlementSource(str, Enum):
    PURCHASE = "purchase"
    MANUAL = "manual"
    SUBSCRIPTION = "subscription"


class Order(TimestampedBase):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_org_profile", "organization_id", "profile_id"),
        Index("ix_orders_provider_invoice", "provider_invoice_id"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30), default=OrderKind.CASE_UNLOCK.value)

    #: Whole tenge, decided by the server from configuration.
    amount_kzt: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.CREATED.value, index=True)

    provider: Mapped[str] = mapped_column(String(20), default="fake")
    provider_invoice_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    #: Our idempotency key to the provider. Unique, so a retried request cannot
    #: open a second invoice for the same purchase.
    external_order_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)

    method: Mapped[str] = mapped_column(String(10), default=PaymentMethod.PHONE.value)
    #: Masked at the boundary. The full number is never stored.
    phone_masked: Mapped[str] = mapped_column(String(20), default="")

    qr_payload: Mapped[str] = mapped_column(Text, default="")
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str] = mapped_column(String(60), default="")


class PaymentEvent(Base):
    """Append-only. Written even when the status did not change."""

    __tablename__ = "payment_events"
    __table_args__ = (Index("ix_payment_events_order", "order_id", "received_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(60), default="")
    provider_status: Mapped[str] = mapped_column(String(30), default="")
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Redacted before it reaches here. No phone, no key, no signature.
    detail: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Entitlement(TimestampedBase):
    """What an organization may see. The only table the routes consult."""

    __tablename__ = "entitlements"
    __table_args__ = (
        # One case is granted once per organization. The partial predicate is
        # what remains of phase 1's pair: the org-wide index guarded a blanket
        # entitlement that no longer exists.
        Index(
            "uq_entitlements_case",
            "organization_id",
            "profile_id",
            "kind",
            unique=True,
            postgresql_where=text("profile_id IS NOT NULL"),
            sqlite_where=text("profile_id IS NOT NULL"),
        ),
    )

    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(20), default=EntitlementSource.PURCHASE.value)
    order_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: Which subscription paid for this case, when one did. Counting these rows
    #: is how a subscription's remaining quota is known.
    subscription_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
