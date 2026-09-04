"""The ApiPay adapter, driven against a stubbed transport.

Response shapes here are the ones ApiPay's OpenAPI document defines, not ones
we found convenient.
"""

from __future__ import annotations

import httpx
import pytest

from app.payments.apipay import ApiPayProvider
from app.payments.errors import (
    DuplicateOrderError,
    ProviderRejected,
    ProviderUnavailable,
    RateLimited,
    SessionExpired,
    TariffInactive,
)


def provider_with(handler) -> ApiPayProvider:
    return ApiPayProvider(
        base_url="https://api.apipay.test/api/v1",
        api_key="key-123",
        webhook_secret="whsec",
        timeout_seconds=5.0,
        transport=httpx.MockTransport(handler),
    )


def test_the_api_key_travels_in_the_header_and_never_in_the_url() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("X-API-Key", "")
        seen["url"] = str(request.url)
        return httpx.Response(201, json={"id": "inv1", "status": "processing", "amount": 4990})

    provider_with(handler).create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
    )
    assert seen["key"] == "key-123"
    assert "key-123" not in seen["url"]


def test_a_phone_invoice_is_parsed() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"id": "inv1", "status": "processing", "amount": 4990})

    invoice = provider_with(handler).create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
    )
    assert invoice.invoice_id == "inv1"
    assert invoice.status == "processing"


def test_a_qr_invoice_carries_its_image_and_expiry() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "id": "inv2",
                "status": "pending",
                "amount": 4990,
                "qr_token": "tok-abc",
                "qr_image_url": "https://api.apipay.test/qr/inv2.png",
                "qr_expires_at": "2026-09-04T10:05:00+00:00",
            },
        )

    invoice = provider_with(handler).create_qr_invoice(
        amount_kzt=4990, description="Case", external_order_id="ext-2"
    )
    assert invoice.qr_payload == "https://api.apipay.test/qr/inv2.png"
    assert invoice.qr_expires_at is not None
    assert invoice.qr_expires_at.tzinfo is not None


def test_a_qr_invoice_falls_back_to_the_token() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"id": "inv2", "status": "pending", "qr_token": "tok-abc"})

    invoice = provider_with(handler).create_qr_invoice(
        amount_kzt=4990, description="Case", external_order_id="ext-2"
    )
    assert invoice.qr_payload == "tok-abc"


def test_a_zulu_expiry_is_still_timezone_aware() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={"id": "i", "status": "pending", "qr_expires_at": "2026-09-04T10:05:00Z"},
        )

    invoice = provider_with(handler).create_qr_invoice(
        amount_kzt=4990, description="Case", external_order_id="ext-2"
    )
    assert invoice.qr_expires_at is not None
    assert invoice.qr_expires_at.tzinfo is not None


def test_a_duplicate_order_id_raises_its_own_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "error": "duplicate",
                "error_code": "duplicate_idempotency_key",
                "message": "already exists",
            },
        )

    with pytest.raises(DuplicateOrderError):
        provider_with(handler).create_phone_invoice(
            amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
        )


def test_our_own_lapsed_tariff_is_distinguishable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"error": "tariff", "error_code": "tariff_inactive", "message": "expired"}
        )

    with pytest.raises(TariffInactive):
        provider_with(handler).get_invoice("inv1")


def test_an_expired_kaspi_session_is_distinguishable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": "session", "error_code": "kaspi_session_expired", "message": "re-auth"},
        )

    with pytest.raises(SessionExpired):
        provider_with(handler).get_invoice("inv1")


def test_rate_limiting_carries_retry_after() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error_code": "request_rate_limited", "message": "slow down"},
            headers={"Retry-After": "7"},
        )

    with pytest.raises(RateLimited) as caught:
        provider_with(handler).get_invoice("inv1")
    assert caught.value.retry_after == 7


def test_a_validation_failure_names_the_field() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422, json={"message": "Validation failed", "errors": {"phone": ["bad format"]}}
        )

    with pytest.raises(ProviderRejected) as caught:
        provider_with(handler).create_phone_invoice(
            amount_kzt=4990, phone="123", description="Case", external_order_id="ext-1"
        )
    assert "phone" in str(caught.value)


def test_an_error_never_repeats_the_payer_phone() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"message": "Validation failed", "errors": {"phone": ["87071234455 is bad"]}},
        )

    with pytest.raises(ProviderRejected) as caught:
        provider_with(handler).create_phone_invoice(
            amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
        )
    assert "87071234455" not in str(caught.value)


def test_a_server_error_is_retryable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream down")

    with pytest.raises(ProviderUnavailable):
        provider_with(handler).get_invoice("inv1")


def test_a_transport_failure_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(ProviderUnavailable):
        provider_with(handler).get_invoice("inv1")


def test_the_webhook_signature_is_verified_against_the_raw_bytes() -> None:
    import hashlib
    import hmac

    provider = provider_with(lambda _r: httpx.Response(200, json={}))
    body = b'{"event":"invoice.status_changed"}'
    good = "sha256=" + hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert provider.verify_webhook(body, good) is True
    assert provider.verify_webhook(body + b" ", good) is False
    assert provider.verify_webhook(body, "") is False


def test_the_adapter_satisfies_the_provider_protocol() -> None:
    from app.payments.provider import PaymentProvider

    assert isinstance(provider_with(lambda _r: httpx.Response(200, json={})), PaymentProvider)
