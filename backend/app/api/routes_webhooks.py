"""Provider callbacks.

This is the only unauthenticated write endpoint in the service, so it gets the
most suspicion: the body is size-capped before it is parsed, the signature is
checked against the raw bytes, an unrecognised event is recorded and ignored,
and nothing here trusts a field it did not verify.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.billing import Order, PaymentEvent
from app.payments.provider import get_provider
from app.payments.service import apply_status

log = logging.getLogger("unimatch.payments")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

#: A status callback is a few hundred bytes. Anything this size is not one.
MAX_WEBHOOK_BYTES = 64 * 1024
#: The only events allowed to change an order.
ACTIONABLE_EVENTS = frozenset({"invoice.status_changed", "invoice.qr_scanned"})


@router.post("/apipay")
async def apipay_webhook(
    request: Request,
    x_webhook_signature: str = Header(default=""),
) -> dict[str, str]:
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(413, "Payload too large")

    if not get_provider().verify_webhook(raw, x_webhook_signature):
        # Deliberately uninformative: a probe learns nothing about why.
        log.warning("rejected an ApiPay webhook with an invalid signature")
        raise HTTPException(401, "Invalid signature")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Malformed JSON") from exc

    event_type = str(payload.get("event", ""))
    data = payload.get("data") or {}
    provider_status = str(data.get("status", ""))
    invoice_id = str(data.get("id", ""))
    external_order_id = data.get("external_order_id")

    session: Session = next(get_session())
    try:
        order = _find_order(session, invoice_id, external_order_id)
        if order is None:
            # Acknowledged, so the provider stops retrying something unusable.
            log.info("ApiPay webhook for an unknown invoice, ignored")
            return {"status": "ignored"}

        if event_type not in ACTIONABLE_EVENTS:
            session.add(
                PaymentEvent(
                    order_id=order.id,
                    source="webhook",
                    event_type=event_type,
                    provider_status=provider_status,
                    signature_valid=True,
                    detail="event type not actionable",
                )
            )
            session.commit()
            return {"status": "recorded"}

        apply_status(session, order, provider_status, source="webhook", event_type=event_type)
        session.commit()
        return {"status": "applied"}
    finally:
        session.close()


def _find_order(session: Session, invoice_id: str, external_order_id: str | None) -> Order | None:
    """Match on the provider's invoice id, then on ours, then on our own key.

    The last of those exists because a caller that knows only our order id —
    a test, or an operator replaying an event by hand — should still land on
    the right row.
    """
    if invoice_id:
        found = session.query(Order).filter(Order.provider_invoice_id == invoice_id).one_or_none()
        if found is not None:
            return found
    if external_order_id:
        found = (
            session.query(Order)
            .filter(Order.external_order_id == str(external_order_id))
            .one_or_none()
        )
        if found is not None:
            return found
    return session.get(Order, invoice_id) if invoice_id else None
