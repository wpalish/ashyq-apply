"""The provider seam: a fake that behaves the way ApiPay documents."""

from __future__ import annotations

import pytest

from app.payments.errors import DuplicateOrderError, ProviderRejected
from app.payments.fake import FakeProvider
from app.payments.provider import mask_phone


def test_a_phone_invoice_starts_pending() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    invoice = provider.create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
    )
    assert invoice.status == "pending"
    assert invoice.invoice_id
    assert provider.get_invoice(invoice.invoice_id).status == "pending"


def test_a_qr_invoice_carries_a_payload_and_an_expiry() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    invoice = provider.create_qr_invoice(
        amount_kzt=4990, description="Case", external_order_id="ext-2"
    )
    assert invoice.qr_payload
    assert invoice.qr_expires_at is not None


def test_the_same_external_order_id_is_refused() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    provider.create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-dup"
    )
    with pytest.raises(DuplicateOrderError):
        provider.create_phone_invoice(
            amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-dup"
        )


def test_an_amount_below_one_tenge_is_refused_as_apipay_refuses_it() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    with pytest.raises(ProviderRejected) as caught:
        provider.create_phone_invoice(
            amount_kzt=0, phone="87071234455", description="Case", external_order_id="ext-3"
        )
    assert caught.value.code == "amount_must_be_whole_tenge"


def test_a_malformed_phone_is_refused() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    with pytest.raises(ProviderRejected) as caught:
        provider.create_phone_invoice(
            amount_kzt=4990, phone="+77071234455", description="Case", external_order_id="ext-4"
        )
    assert caught.value.code == "validation_failed"


def test_simulation_moves_an_invoice_to_paid() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    invoice = provider.create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-5"
    )
    provider.simulate(invoice.invoice_id, "paid")
    assert provider.get_invoice(invoice.invoice_id).status == "paid"


def test_a_valid_signature_is_accepted_and_a_tampered_body_is_not() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    body = b'{"event":"invoice.status_changed","status":"paid"}'
    signature = provider.sign(body)
    assert provider.verify_webhook(body, signature) is True
    assert provider.verify_webhook(body + b" ", signature) is False
    assert provider.verify_webhook(body, "sha256=deadbeef") is False
    assert provider.verify_webhook(body, "") is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("87071234455", "8707***4455"),
        ("87010000000", "8701***0000"),
    ],
)
def test_a_phone_is_stored_masked(raw: str, expected: str) -> None:
    assert mask_phone(raw) == expected


def test_masking_never_returns_the_original() -> None:
    assert mask_phone("87071234455") != "87071234455"


def test_masking_a_number_too_short_to_mask_reveals_nothing() -> None:
    assert mask_phone("8707") == "***"
