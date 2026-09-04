"""The seam every payment provider sits behind.

The application never imports a provider directly; it asks ``get_provider``.
That is what makes the fake usable in every test, and what makes swapping in
the real adapter a configuration change rather than a code change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

#: Statuses as the provider words them. Translation into our own vocabulary
#: happens once, in app.payments.service.
PROVIDER_PENDING = frozenset({"pending", "processing", "qr_scanned"})
PROVIDER_PAID = frozenset({"paid"})
PROVIDER_CANCELLED = frozenset({"cancelled"})
PROVIDER_EXPIRED = frozenset({"expired"})


def mask_phone(phone: str) -> str:
    """``87071234455`` -> ``8707***4455``. The most of a payer's number we keep.

    Lives here rather than beside the fake because production code calls it,
    and production code must never import from a test double.
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return "***"
    return f"{digits[:4]}***{digits[-4:]}"


@dataclass(frozen=True)
class ProviderInvoice:
    invoice_id: str
    status: str
    qr_payload: str = ""
    qr_expires_at: datetime | None = None


@runtime_checkable
class PaymentProvider(Protocol):
    def create_phone_invoice(
        self, *, amount_kzt: int, phone: str, description: str, external_order_id: str
    ) -> ProviderInvoice: ...

    def create_qr_invoice(
        self, *, amount_kzt: int, description: str, external_order_id: str
    ) -> ProviderInvoice: ...

    def get_invoice(self, invoice_id: str) -> ProviderInvoice: ...

    def cancel_invoice(self, invoice_id: str) -> None: ...

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool: ...


def get_provider() -> PaymentProvider:
    """The configured provider. Called per request; construction is cheap."""
    from app.config import get_settings

    settings = get_settings()
    if settings.payments_provider == "apipay":
        from app.payments.apipay import ApiPayProvider

        return ApiPayProvider(
            base_url=settings.apipay_base_url,
            api_key=settings.apipay_api_key.get_secret_value(),
            webhook_secret=settings.apipay_webhook_secret.get_secret_value(),
            timeout_seconds=settings.apipay_timeout_seconds,
        )

    from app.payments.fake import get_shared_fake

    return get_shared_fake(settings.apipay_webhook_secret.get_secret_value() or "test-secret")
