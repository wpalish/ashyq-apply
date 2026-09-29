"""Reject unsafe runtime settings before a process starts doing work."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.jobs import worker as worker_module
from app.mail import ConsoleSender, SmtpSender, get_sender


def _settings(**overrides: object) -> Settings:
    """A valid production configuration with no real service credentials."""
    values: dict[str, Any] = {
        "environment": "production",
        "demo_mode": False,
        "auth_enabled": True,
        "cookie_secure": True,
        "database_url": "postgresql+psycopg://test:unused@database.invalid/test",
        "cors_origins": "https://apply.example.test",
        "public_base_url": "https://apply.example.test",
        "email_sender": "smtp",
        "smtp_host": "smtp.example.test",
        "smtp_from": "no-reply@example.test",
        "password_scrypt_log2": 17,
        "metrics_enabled": False,
        "payments_enabled": False,
        "search_provider": "exa_mcp",
        "decision_provider": "none",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("environment", ["development", "production"])
@pytest.mark.parametrize("sender", ["smpt", ""])
def test_unknown_email_sender_is_rejected_by_runtime_validation(
    environment: str, sender: str
) -> None:
    with pytest.raises(RuntimeError, match="UNIMATCH_EMAIL_SENDER"):
        _settings(environment=environment, email_sender=sender).validate_runtime()


@pytest.mark.parametrize("sender", ["smpt", ""])
def test_unknown_email_sender_cannot_fall_back_to_logging_mail(sender: str) -> None:
    with pytest.raises(RuntimeError, match="UNIMATCH_EMAIL_SENDER"):
        get_sender(_settings(environment="development", email_sender=sender))


@pytest.mark.parametrize("sender", ["console", "smtp"])
def test_documented_development_email_senders_remain_allowed(sender: str) -> None:
    settings = _settings(environment="development", email_sender=sender)
    settings.validate_runtime()
    expected = ConsoleSender if sender == "console" else SmtpSender
    assert isinstance(get_sender(settings), expected)


def test_valid_production_smtp_remains_allowed() -> None:
    settings = _settings()
    settings.validate_runtime()
    assert isinstance(get_sender(settings), SmtpSender)


@pytest.mark.parametrize(
    "sender",
    ["", "   ", "no-reply@ashyq.example", "not-an-email", "no-reply@", "no-reply@EXAMPLE"],
)
def test_production_refuses_unusable_smtp_from(sender: str) -> None:
    with pytest.raises(RuntimeError, match="UNIMATCH_SMTP_FROM"):
        _settings(smtp_from=sender).validate_runtime()


def test_production_accepts_explicit_display_name_sender() -> None:
    _settings(smtp_from="ASHYQ Apply <no-reply@example.test>").validate_runtime()


def test_development_console_keeps_its_placeholder_sender() -> None:
    _settings(
        environment="development", email_sender="console", smtp_from="no-reply@ashyq.example"
    ).validate_runtime()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"auth_enabled": False}, "UNIMATCH_AUTH_ENABLED"),
        ({"database_url": "sqlite:///:memory:"}, "PostgreSQL"),
        ({"email_sender": "smpt"}, "UNIMATCH_EMAIL_SENDER"),
    ],
)
def test_worker_refuses_unsafe_settings_before_startup_side_effects(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, object], message: str
) -> None:
    settings = _settings(**overrides)
    configure = Mock()
    schema = Mock(return_value=False)
    reconcile = Mock()
    constructor = Mock()
    logger = Mock()
    create_loop = Mock()
    install_loop = Mock()
    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "configure_logging", configure)
    monkeypatch.setattr(worker_module, "wait_for_schema", schema)
    monkeypatch.setattr(worker_module, "reconcile_startup", reconcile)
    monkeypatch.setattr(worker_module, "Worker", constructor)
    monkeypatch.setattr(worker_module, "log", logger)
    monkeypatch.setattr(worker_module.asyncio, "new_event_loop", create_loop)
    monkeypatch.setattr(worker_module.asyncio, "set_event_loop", install_loop)

    with pytest.raises(RuntimeError, match=message):
        worker_module.main()

    configure.assert_not_called()
    schema.assert_not_called()
    reconcile.assert_not_called()
    constructor.assert_not_called()
    assert logger.mock_calls == []
    create_loop.assert_not_called()
    install_loop.assert_not_called()


def test_worker_validates_before_logging_and_schema_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid worker still honours the schema-wait failure without running jobs."""
    settings = _settings()
    order: list[str] = []
    original_validate = Settings.validate_runtime

    def validate(actual: Settings) -> None:
        assert actual is settings
        order.append("validate")
        original_validate(actual)

    def configure(*_args: object) -> None:
        order.append("configure_logging")

    def schema() -> bool:
        order.append("wait_for_schema")
        return False

    reconcile = Mock()
    constructor = Mock()
    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(Settings, "validate_runtime", validate)
    monkeypatch.setattr(worker_module, "configure_logging", configure)
    monkeypatch.setattr(worker_module, "wait_for_schema", schema)
    monkeypatch.setattr(worker_module, "reconcile_startup", reconcile)
    monkeypatch.setattr(worker_module, "Worker", constructor)

    assert worker_module.main() == 1
    assert order == ["validate", "configure_logging", "wait_for_schema"]
    reconcile.assert_not_called()
    constructor.assert_not_called()
