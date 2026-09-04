"""ApiPay (Kaspi Pay) over HTTP.

Contract reconciled against ApiPay's published OpenAPI document on 2026-09-04
(bazarbaykz/apipay-docs, openapi.yaml). Field names below are copied from it:

* ``POST /invoices``      request ``amount``, ``phone``, ``description``,
                          ``external_order_id``; response ``id``, ``status``
                          (``processing``), ``amount``, ``created_at``
* ``POST /invoices/qr``   response adds ``qr_token``, ``qr_image_url``,
                          ``qr_expires_at``; status is ``pending``
* ``GET  /invoices/{id}`` response ``id``, ``status``, ``amount``, ``paid_at``

Two rules this file exists to keep:
  * the API key travels in a header, never in a URL or a log line;
  * the payer's phone never appears in an exception message.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Any

import httpx

from app.payments.errors import (
    DuplicateOrderError,
    PaymentError,
    ProviderRejected,
    ProviderUnavailable,
    RateLimited,
    SessionExpired,
    TariffInactive,
)
from app.payments.provider import ProviderInvoice

#: error_code values that deserve their own class. Everything else becomes a
#: ProviderRejected carrying the provider's code verbatim.
_ERRORS: dict[str, type[PaymentError]] = {
    "duplicate_idempotency_key": DuplicateOrderError,
    "tariff_inactive": TariffInactive,
    "kaspi_session_expired": SessionExpired,
    "kaspi_session_not_configured": SessionExpired,
}


class ApiPayProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        webhook_secret: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._secret = webhook_secret.encode()
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=timeout_seconds,
            transport=transport,
        )

    # -- transport -----------------------------------------------------
    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict:
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("The payment provider could not be reached.") from exc

        if response.status_code >= 500:
            raise ProviderUnavailable(f"The payment provider returned {response.status_code}.")

        if response.status_code == 429:
            raise RateLimited(
                "The payment provider is rate limiting us.",
                retry_after=int(response.headers.get("Retry-After", "1") or 1),
            )

        try:
            body: dict[str, Any] = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            raise self._to_error(response.status_code, body)
        return body

    def _to_error(self, status: int, body: dict[str, Any]) -> PaymentError:
        code = str(body.get("error_code", "") or "")
        if code in _ERRORS:
            return _ERRORS[code](f"The payment provider refused the request ({code}).", code=code)
        if status == 422:
            # Name the fields, never their values: one of them is the phone.
            fields = ", ".join(sorted((body.get("errors") or {}).keys())) or "request"
            return ProviderRejected(
                f"The payment provider rejected these fields: {fields}.", code="validation_failed"
            )
        return ProviderRejected(
            f"The payment provider refused the request ({code or status}).",
            code=code or "rejected",
        )

    # -- invoices ------------------------------------------------------
    def create_phone_invoice(
        self, *, amount_kzt: int, phone: str, description: str, external_order_id: str
    ) -> ProviderInvoice:
        body = self._call(
            "POST",
            "/invoices",
            {
                "amount": amount_kzt,
                "phone": phone,
                "description": description,
                "external_order_id": external_order_id,
            },
        )
        return self._to_invoice(body)

    def create_qr_invoice(
        self, *, amount_kzt: int, description: str, external_order_id: str
    ) -> ProviderInvoice:
        body = self._call(
            "POST",
            "/invoices/qr",
            {
                "amount": amount_kzt,
                "description": description,
                "external_order_id": external_order_id,
            },
        )
        return self._to_invoice(body)

    def get_invoice(self, invoice_id: str) -> ProviderInvoice:
        return self._to_invoice(self._call("GET", f"/invoices/{invoice_id}"))

    def cancel_invoice(self, invoice_id: str) -> None:
        self._call("POST", f"/invoices/{invoice_id}/cancel")

    @staticmethod
    def _to_invoice(body: dict[str, Any]) -> ProviderInvoice:
        expires_raw = body.get("qr_expires_at")
        expires = None
        if isinstance(expires_raw, str) and expires_raw:
            expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        return ProviderInvoice(
            invoice_id=str(body.get("id", "")),
            status=str(body.get("status", "")),
            # The image is what a browser can render; the token is the fallback
            # for a client that draws its own QR.
            qr_payload=str(body.get("qr_image_url") or body.get("qr_token") or ""),
            qr_expires_at=expires,
        )

    # -- webhooks ------------------------------------------------------
    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected = "sha256=" + hmac.new(self._secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
