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


def _payments_on(
    *,
    payments_provider: str = "apipay",
    apipay_webhook_secret: str = "a-real-webhook-secret-value",
    apipay_api_key: str = "live-key",
) -> Settings:
    """A production configuration that is correct except where a test says otherwise.

    Everything unrelated to payments is set to what production already
    demands, so the failure a test asserts on is the payment rule and not one
    of the older guards firing first.
    """
    return Settings(
        payments_enabled=True,
        payments_provider=payments_provider,
        apipay_webhook_secret=apipay_webhook_secret,
        apipay_api_key=apipay_api_key,
        environment="production",
        auth_enabled=True,
        cookie_secure=True,
        database_url="postgresql+psycopg://u:p@db/ashyq",
        cors_origins="https://ashyq.example",
        email_sender="smtp",
        smtp_host="smtp.example",
        public_base_url="https://ashyq.example",
        metrics_enabled=False,
    )


class TestPaymentsRefuseAnUnverifiableCallback:
    """The webhook signature is the whole boundary around a paid unlock.

    Every case below used to start happily and accept a forged `paid` event.
    """

    def test_a_correct_production_configuration_starts(self) -> None:
        _payments_on().validate_runtime()

    def test_production_refuses_the_test_double(self) -> None:
        import pytest

        with pytest.raises(RuntimeError, match="must be 'apipay'"):
            _payments_on(payments_provider="fake").validate_runtime()

    def test_an_unset_webhook_secret_is_refused_everywhere(self) -> None:
        import pytest

        with pytest.raises(RuntimeError, match="WEBHOOK_SECRET must be set"):
            Settings(
                payments_enabled=True, payments_provider="fake", apipay_webhook_secret=""
            ).validate_runtime()

    def test_production_refuses_a_placeholder_secret(self) -> None:
        import pytest

        with pytest.raises(RuntimeError, match="at least 16 characters"):
            _payments_on(apipay_webhook_secret="short").validate_runtime()

    def test_production_refuses_a_missing_api_key(self) -> None:
        import pytest

        with pytest.raises(RuntimeError, match="API_KEY must be set"):
            _payments_on(apipay_api_key="").validate_runtime()

    def test_an_unknown_provider_is_refused(self) -> None:
        import pytest

        with pytest.raises(RuntimeError, match="not a payment provider"):
            _payments_on(payments_provider="stripe").validate_runtime()

    def test_payments_off_leaves_every_other_default_alone(self) -> None:
        # The whole block is skipped when nobody is being charged.
        Settings(payments_enabled=False, payments_provider="fake").validate_runtime()


def test_the_smtp_password_is_a_secret_like_every_other_credential() -> None:
    settings = Settings(smtp_password="mail-password-value")
    assert "mail-password-value" not in repr(settings.model_dump())
    assert settings.smtp_password.get_secret_value() == "mail-password-value"
