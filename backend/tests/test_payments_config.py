"""Payment configuration: safe defaults, and secrets that do not leak."""

from __future__ import annotations

from typing import Any

import pytest

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


# -- T34 A1 (security campaign c3): payments fail closed at config time ------
# The three refusal tests are RED on baseline edf546d: validate_runtime() has
# no payments checks, so a typo'd provider name, short apipay credentials, or
# production billing through the fake provider all start up silently. The two
# guards construct valid configurations and must pass both before and after
# the fix. Secret material is synthetic ("a"*20 / "b"*32), never real values.

_PRODUCTION_BASE: dict[str, Any] = {
    "environment": "production",
    "auth_enabled": True,
    "cookie_secure": True,
    "database_url": "postgresql+psycopg://u:p@db/unimatch",
    "cors_origins": "https://apply.example.com",
    "email_sender": "smtp",
    "smtp_host": "smtp.example.com",
    "public_base_url": "https://apply.example.com",
    # From test_metrics.py:263: metrics off keeps this base otherwise valid,
    # so the checks under test here are the payments ones and nothing else.
    "metrics_enabled": False,
    "metrics_token": "",
}


def test_an_unknown_provider_name_is_refused_at_startup() -> None:
    """A typo like "apipy" must not fall back to the silent fake provider."""
    with pytest.raises(RuntimeError, match="UNIMATCH_PAYMENTS_PROVIDER"):
        Settings(payments_provider="apipy").validate_runtime()


@pytest.mark.parametrize(
    ("api_key", "webhook_secret", "message"),
    [
        ("a" * 19, "b" * 32, "UNIMATCH_APIPAY_API_KEY"),
        ("a" * 20, "b" * 31, "UNIMATCH_APIPAY_WEBHOOK_SECRET"),
    ],
)
def test_apipay_with_short_credentials_is_refused_at_startup(
    api_key: str, webhook_secret: str, message: str
) -> None:
    """With provider=apipay the real credentials are required, not optional."""
    with pytest.raises(RuntimeError, match=message):
        Settings(
            payments_provider="apipay",
            apipay_api_key=api_key,
            apipay_webhook_secret=webhook_secret,
        ).validate_runtime()


def test_production_never_takes_payments_through_the_fake_provider() -> None:
    with pytest.raises(RuntimeError, match="fake provider"):
        Settings(
            **_PRODUCTION_BASE,
            payments_enabled=True,
            payments_provider="fake",
        ).validate_runtime()


def test_a_valid_production_apipay_configuration_starts() -> None:
    """Guard: a fully configured apipay production deployment is accepted."""
    settings = Settings(
        **_PRODUCTION_BASE,
        payments_enabled=True,
        payments_provider="apipay",
        apipay_api_key="a" * 20,
        apipay_webhook_secret="b" * 32,
    )
    settings.validate_runtime()


def test_development_keeps_the_fake_provider_available() -> None:
    """Guard: local dev with payments on and the fake provider still starts."""
    Settings(payments_enabled=True, payments_provider="fake").validate_runtime()
