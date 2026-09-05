"""Buying the full report for one case."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.tenancy import owned_profile
from app.config import get_settings
from app.db import get_session
from app.models import AuditEvent
from app.models.billing import Order
from app.payments.entitlements import has_full_access
from app.payments.errors import PaymentError
from app.payments.service import AlreadyEntitled, InvalidPaymentRequest, cancel_order, create_order
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/billing", tags=["billing"])


class Pricing(BaseModel):
    case_unlock_price_kzt: int
    currency: str = "KZT"
    payments_enabled: bool
    includes: list[str]


class EntitlementView(BaseModel):
    profile_id: str
    full_access: bool
    #: Cases left on the current subscription; null when there is none.
    subscription_cases_left: int | None = None
    #: How many bought-but-not-started subscriptions are waiting behind it.
    subscription_queued: int = 0


class UnlockFromSubscriptionIn(BaseModel):
    profile_id: str


class CreateOrderIn(BaseModel):
    """Note what is absent: the price. The server decides that."""

    profile_id: str
    method: str = "phone"
    phone: str | None = None


class OrderView(BaseModel):
    id: str
    profile_id: str
    status: str
    method: str
    amount_kzt: int
    phone_masked: str
    qr_payload: str
    qr_expires_at: datetime | None
    created_at: datetime


def _view(order: Order) -> OrderView:
    return OrderView(
        id=order.id,
        profile_id=order.profile_id,
        status=order.status,
        method=order.method,
        amount_kzt=order.amount_kzt,
        phone_masked=order.phone_masked,
        qr_payload=order.qr_payload,
        qr_expires_at=order.qr_expires_at,
        created_at=order.created_at,
    )


def _owned_order(session: Session, order_id: str, principal: Principal) -> Order:
    order = session.get(Order, order_id)
    if order is None or order.organization_id != principal.organization_id:
        # 404, not 403: another tenant's order does not exist as far as this one knows.
        raise HTTPException(404, "Order not found")
    return order


@router.get("/pricing", response_model=Pricing)
def pricing(_principal: Principal = Depends(get_principal)) -> Pricing:
    settings = get_settings()
    return Pricing(
        case_unlock_price_kzt=settings.case_unlock_price_kzt,
        payments_enabled=settings.payments_enabled,
        includes=[
            "Full programme coverage rather than the first few matches",
            "Every value traced to its official source",
            "Funding, costs and the gap between them",
            "Document checklist and export",
        ],
    )


def _entitlement_view(session: Session, principal: Principal, profile_id: str) -> EntitlementView:
    from app.payments.subscriptions import (
        current_subscription,
        queued_subscriptions,
        quota_remaining,
    )

    subscription = current_subscription(session, principal.organization_id)
    return EntitlementView(
        profile_id=profile_id,
        full_access=has_full_access(session, principal.organization_id, profile_id),
        subscription_cases_left=(
            None if subscription is None else quota_remaining(session, subscription)
        ),
        subscription_queued=len(queued_subscriptions(session, principal.organization_id)),
    )


@router.get("/entitlements", response_model=EntitlementView)
def entitlements(
    profile_id: str = Query(...),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> EntitlementView:
    owned_profile(session, profile_id, principal)
    return _entitlement_view(session, principal, profile_id)


@router.post("/unlock-from-subscription", response_model=EntitlementView)
def unlock_from_subscription(
    payload: UnlockFromSubscriptionIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> EntitlementView:
    """Open a case out of the organization's subscription quota."""
    from app.payments.subscriptions import consume_for_case

    owned_profile(session, payload.profile_id, principal)
    result = consume_for_case(
        session, organization_id=principal.organization_id, profile_id=payload.profile_id
    )
    if not result.granted:
        # 409, not 402: the case is purchasable, just not from the subscription.
        raise HTTPException(409, "No subscription cases remain.")

    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="case_unlocked_from_subscription",
            entity_type="profile",
            entity_id=payload.profile_id,
            detail={"subscription_id": result.subscription_id, "remaining": result.remaining},
        )
    )
    session.commit()
    return _entitlement_view(session, principal, payload.profile_id)


@router.post("/orders", response_model=OrderView, status_code=201)
def open_order(
    payload: CreateOrderIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> OrderView:
    owned_profile(session, payload.profile_id, principal)
    try:
        order = create_order(
            session,
            organization_id=principal.organization_id,
            profile_id=payload.profile_id,
            method=payload.method,
            phone=payload.phone,
        )
    except AlreadyEntitled as exc:
        raise HTTPException(409, str(exc)) from exc
    except InvalidPaymentRequest as exc:
        raise HTTPException(400, str(exc)) from exc
    except PaymentError as exc:
        # Deliberately generic: the payer's number must not travel in an error body.
        raise HTTPException(502, "The payment provider could not open an invoice.") from exc

    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="order_opened",
            entity_type="order",
            entity_id=order.id,
            detail={"method": order.method, "amount_kzt": order.amount_kzt},
        )
    )
    session.commit()
    session.refresh(order)
    return _view(order)


@router.get("/orders/{order_id}", response_model=OrderView)
def read_order(
    order_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> OrderView:
    return _view(_owned_order(session, order_id, principal))


@router.post("/orders/{order_id}/cancel", response_model=OrderView)
def stop_order(
    order_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> OrderView:
    order = cancel_order(session, _owned_order(session, order_id, principal))
    session.commit()
    session.refresh(order)
    return _view(order)
