"""Creating an order, and the one place an order's status may change.

``apply_status`` is the single writer. The webhook and the reconciler both call
it, so idempotence and order-insensitivity live in exactly one function rather
than being re-argued at each call site.
"""

from __future__ import annotations

import json
import uuid
from contextlib import suppress

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.jobs.store import JobStore
from app.models.base import utcnow
from app.models.billing import (
    TERMINAL_ORDER_STATUSES,
    Order,
    OrderKind,
    OrderStatus,
    PaymentEvent,
    PaymentMethod,
)
from app.payments.entitlements import grant_case_access, has_full_access
from app.payments.errors import PaymentError
from app.payments.provider import (
    PROVIDER_CANCELLED,
    PROVIDER_EXPIRED,
    PROVIDER_PAID,
    get_provider,
    mask_phone,
)
from app.pipeline.state import RunState


class AlreadyEntitled(PaymentError):
    """The case is already unlocked. Selling it twice would be a bug."""

    code = "already_entitled"


class InvalidPaymentRequest(PaymentError):
    code = "invalid_payment_request"


def to_order_status(provider_status: str) -> str:
    """Translate the provider's vocabulary into ours, once.

    An unrecognised status is treated as pending: the reconciler will ask
    again, which is safer than inventing a terminal state from a word we do
    not recognise.
    """
    if provider_status in PROVIDER_PAID:
        return OrderStatus.PAID.value
    if provider_status in PROVIDER_CANCELLED:
        return OrderStatus.CANCELLED.value
    if provider_status in PROVIDER_EXPIRED:
        return OrderStatus.EXPIRED.value
    return OrderStatus.PENDING.value


def _open_order(session: Session, organization_id: str, profile_id: str) -> Order | None:
    return session.scalar(
        select(Order).where(
            Order.organization_id == organization_id,
            Order.profile_id == profile_id,
            Order.kind == OrderKind.CASE_UNLOCK.value,
            Order.status.notin_(tuple(TERMINAL_ORDER_STATUSES)),
        )
    )


def create_order(
    session: Session,
    *,
    organization_id: str,
    profile_id: str,
    method: str,
    phone: str | None,
) -> Order:
    """Open an invoice for this case, or hand back the one already open."""
    if has_full_access(session, organization_id, profile_id):
        raise AlreadyEntitled("This case is already unlocked.")

    if method not in {PaymentMethod.PHONE.value, PaymentMethod.QR.value}:
        raise InvalidPaymentRequest("Choose payment by phone or by QR.")
    if method == PaymentMethod.PHONE.value and not phone:
        raise InvalidPaymentRequest("Enter the phone number registered with Kaspi.")

    existing = _open_order(session, organization_id, profile_id)
    if existing is not None:
        return existing

    settings = get_settings()
    provider = get_provider()
    external_order_id = f"case-{profile_id[:12]}-{uuid.uuid4().hex[:8]}"
    description = "ASHYQ Apply — full report for one case"

    if method == PaymentMethod.PHONE.value:
        # Narrowed by the guard above; restated for the type checker.
        assert phone is not None
        invoice = provider.create_phone_invoice(
            amount_kzt=settings.case_unlock_price_kzt,
            phone=phone,
            description=description,
            external_order_id=external_order_id,
        )
    else:
        invoice = provider.create_qr_invoice(
            amount_kzt=settings.case_unlock_price_kzt,
            description=description,
            external_order_id=external_order_id,
        )

    order = Order(
        organization_id=organization_id,
        profile_id=profile_id,
        kind=OrderKind.CASE_UNLOCK.value,
        amount_kzt=settings.case_unlock_price_kzt,
        status=to_order_status(invoice.status),
        provider=settings.payments_provider,
        provider_invoice_id=invoice.invoice_id,
        external_order_id=external_order_id,
        method=method,
        phone_masked=mask_phone(phone) if phone else "",
        qr_payload=invoice.qr_payload,
        qr_expires_at=invoice.qr_expires_at,
    )
    session.add(order)
    session.flush()

    # The provider may never call us back. Something must keep asking.
    JobStore(session).enqueue(
        "payment_reconcile",
        payload={"order_id": order.id},
        idempotency_key=f"payment_reconcile:{order.id}",
        priority=1,
        max_attempts=30,
    )
    return order


def apply_status(
    session: Session,
    order: Order,
    provider_status: str,
    *,
    source: str,
    event_type: str = "",
) -> Order:
    """The only place an order's status changes. Safe to call repeatedly.

    Rules, in order of precedence:
      1. Every call is journalled, including calls that change nothing.
      2. ``paid`` always wins, even after a local cancellation — money moved.
      3. A terminal status is never replaced by a non-terminal one.
    """
    target = to_order_status(provider_status)

    session.add(
        PaymentEvent(
            order_id=order.id,
            source=source,
            event_type=event_type,
            provider_status=provider_status,
            signature_valid=True,
            detail=json.dumps({"from": order.status, "to": target}),
        )
    )

    if order.status == target:
        return order
    if target == OrderStatus.PAID.value:
        order.status = OrderStatus.PAID.value
        order.paid_at = order.paid_at or utcnow()
        _grant_and_schedule(session, order)
        return order
    if order.status in TERMINAL_ORDER_STATUSES:
        # A late non-terminal update cannot reopen a settled order.
        return order

    order.status = target
    return order


def _grant_and_schedule(session: Session, order: Order) -> None:
    """Unlock the case, then queue the full run the customer just bought."""
    from app.models import ResearchRun

    grant_case_access(
        session,
        organization_id=order.organization_id,
        profile_id=order.profile_id,
        order_id=order.id,
    )

    run = ResearchRun(
        profile_id=order.profile_id,
        stage="queued",
        access_tier="full",
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    JobStore(session).enqueue(
        "research",
        run_id=run.id,
        idempotency_key=f"research:{run.id}",
        priority=0,
    )


def cancel_order(session: Session, order: Order) -> Order:
    """Stop chasing this order.

    ApiPay cannot cancel a QR invoice, so for QR this is local only: if the
    customer pays it anyway, ``apply_status`` still grants on the webhook.
    """
    if order.status in TERMINAL_ORDER_STATUSES:
        return order

    if order.method == PaymentMethod.PHONE.value and order.provider_invoice_id:
        # The provider refusing does not stop us closing our own side.
        with suppress(PaymentError):
            get_provider().cancel_invoice(order.provider_invoice_id)

    order.status = OrderStatus.CANCELLED.value
    session.add(
        PaymentEvent(
            order_id=order.id,
            source="local",
            event_type="order.cancelled",
            provider_status="cancelled",
            signature_valid=True,
        )
    )
    return order
