"""Ask the provider what happened, because a webhook can be lost.

A backstop rather than a fallback: it runs for every order, and it converges on
the same ``apply_status`` the webhook uses, so the two cannot disagree.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.base import ensure_utc, utcnow
from app.models.billing import TERMINAL_ORDER_STATUSES, Order, PaymentMethod
from app.payments.errors import PaymentError
from app.payments.provider import get_provider
from app.payments.service import apply_status

log = logging.getLogger("unimatch.payments")

#: How long we keep asking. A phone invoice can sit unanswered for a while; a
#: QR is dead within minutes of its own expiry.
PHONE_TTL = timedelta(hours=24)
QR_GRACE = timedelta(minutes=5)


def reconcile_order(session: Session, order_id: str) -> str:
    """Poll one order once. Returns its status, or "" when there is nothing to do."""
    order = session.get(Order, order_id)
    if order is None:
        log.info("reconcile: order %s no longer exists", order_id[:8])
        return ""
    if order.status in TERMINAL_ORDER_STATUSES or not order.provider_invoice_id:
        return order.status

    if _past_its_life(order):
        apply_status(session, order, "expired", source="poll", event_type="reconcile.timeout")
        return order.status

    try:
        invoice = get_provider().get_invoice(order.provider_invoice_id)
    except PaymentError as exc:
        # Leave the order alone; the queue's backoff will try again.
        log.warning("reconcile: provider refused for order %s (%s)", order.id[:8], exc.code)
        return order.status

    apply_status(session, order, invoice.status, source="poll", event_type="reconcile")
    return order.status


def _past_its_life(order: Order) -> bool:
    now = utcnow()
    if order.method == PaymentMethod.QR.value:
        expiry = ensure_utc(order.qr_expires_at)
        return expiry is not None and now > expiry + QR_GRACE
    created = ensure_utc(order.created_at)
    return created is not None and now > created + PHONE_TTL
