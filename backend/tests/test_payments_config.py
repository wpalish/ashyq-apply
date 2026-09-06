"""Payment configuration: safe defaults, and secrets that do not leak."""

from __future__ import annotations

from app.config import Settings


def test_payments_are_off_by_default() -> None:
    settings = Settings()
    assert settings.payments_enabled is False
    assert settings.payments_provider == "fake"


def test_price_and_free_tier_defaults() -> None:
    settings = Settings()
    assert settings.case_unlock_price_kzt == 4990
    assert settings.free_candidate_limit == 5
    assert settings.free_shortlist_rows == 5


def test_secrets_do_not_render_in_a_settings_dump() -> None:
    settings = Settings(apipay_api_key="live-key-value", apipay_webhook_secret="whsec-value")
    dumped = repr(settings.model_dump())
    assert "live-key-value" not in dumped
    assert "whsec-value" not in dumped
    assert settings.apipay_api_key.get_secret_value() == "live-key-value"


def test_secret_values_are_reachable_only_deliberately() -> None:
    settings = Settings(apipay_webhook_secret="whsec-value")
    assert "whsec-value" not in str(settings.apipay_webhook_secret)
