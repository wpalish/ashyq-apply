"""A provider that behaves the way ApiPay documents, without a network.

Every rejection it raises corresponds to an error code in ApiPay's published
OpenAPI document. If this file and the real adapter ever disagree about what a
failure looks like, one of them is wrong about the provider — and the document
decides which.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from datetime import timedelta

from app.models.base import utcnow
from app.payments.errors import DuplicateOrderError, ProviderRejected
from app.payments.provider import ProviderInvoice

#: ApiPay accepts a payer phone as 11 digits beginning with 8.
PHONE_PATTERN = re.compile(r"^8\d{10}$")
#: A QR invoice lives minutes, not hours.
QR_TTL = timedelta(minutes=10)


class FakeProvider:
    def __init__(self, *, webhook_secret: str) -> None:
        self.secret = webhook_secret.encode()
        self._invoices: dict[str, ProviderInvoice] = {}
        self._by_external: dict[str, str] = {}

    # -- creation ------------------------------------------------------
    def _create(self, *, amount_kzt: int, external_order_id: str, qr: bool) -> ProviderInvoice:
        if amount_kzt < 1:
            raise ProviderRejected(
                "Amount must be at least one whole tenge.", code="amount_must_be_whole_tenge"
            )
        if external_order_id in self._by_external:
            raise DuplicateOrderError("An invoice already exists for this order.")

        invoice = ProviderInvoice(
            invoice_id=uuid.uuid4().hex[:16],
            status="pending",
            qr_payload=f"https://pay.kaspi.invalid/{uuid.uuid4().hex[:12]}" if qr else "",
            qr_expires_at=utcnow() + QR_TTL if qr else None,
        )
        self._invoices[invoice.invoice_id] = invoice
        self._by_external[external_order_id] = invoice.invoice_id
        return invoice

    def create_phone_invoice(
        self, *, amount_kzt: int, phone: str, description: str, external_order_id: str
    ) -> ProviderInvoice:
        if not PHONE_PATTERN.fullmatch(phone):
            raise ProviderRejected("Enter the number as 8XXXXXXXXXX.", code="validation_failed")
        return self._create(amount_kzt=amount_kzt, external_order_id=external_order_id, qr=False)

    def create_qr_invoice(
        self, *, amount_kzt: int, description: str, external_order_id: str
    ) -> ProviderInvoice:
        return self._create(amount_kzt=amount_kzt, external_order_id=external_order_id, qr=True)

    # -- reading and control -------------------------------------------
    def get_invoice(self, invoice_id: str) -> ProviderInvoice:
        invoice = self._invoices.get(invoice_id)
        if invoice is None:
            raise ProviderRejected("No such invoice.", code="not_found")
        return invoice

    def cancel_invoice(self, invoice_id: str) -> None:
        self.simulate(invoice_id, "cancelled")

    def simulate(self, invoice_id: str, status: str) -> ProviderInvoice:
        """ApiPay's sandbox simulate-status, without the sandbox."""
        current = self.get_invoice(invoice_id)
        moved = ProviderInvoice(
            invoice_id=current.invoice_id,
            status=status,
            qr_payload=current.qr_payload,
            qr_expires_at=current.qr_expires_at,
        )
        self._invoices[invoice_id] = moved
        return moved

    # -- webhooks ------------------------------------------------------
    def sign(self, raw_body: bytes) -> str:
        return "sha256=" + hmac.new(self.secret, raw_body, hashlib.sha256).hexdigest()

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        return hmac.compare_digest(self.sign(raw_body), signature)


_shared: FakeProvider | None = None


def get_shared_fake(secret: str) -> FakeProvider:
    """One instance per process, so a test can simulate what a route created."""
    global _shared
    if _shared is None or _shared.secret != secret.encode():
        _shared = FakeProvider(webhook_secret=secret)
    return _shared


def reset_shared_fake() -> None:
    """Drop the shared instance. Test fixtures call this between cases."""
    global _shared
    _shared = None
