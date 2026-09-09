"""Outbound mail: what actually travels, and over what.

The only mail this product sends is a password-reset link, which is a
credential in a URL. Where it goes and how it is protected on the way is
therefore a security property, not a delivery detail.
"""

from __future__ import annotations

import ssl
from typing import ClassVar

from app.config import Settings
from app.mail import ConsoleSender, Message, SmtpSender, get_sender


class _FakeSmtp:
    """Enough of ``smtplib.SMTP`` to record how it was driven."""

    instances: ClassVar[list[_FakeSmtp]] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls_context: ssl.SSLContext | None = None
        self.started_tls = False
        self.login_with: tuple[str, str] | None = None
        self.sent: list[object] = []
        _FakeSmtp.instances.append(self)

    def __enter__(self) -> _FakeSmtp:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def starttls(self, context: ssl.SSLContext | None = None) -> None:
        self.started_tls = True
        self.tls_context = context

    def login(self, username: str, password: str) -> None:
        self.login_with = (username, password)

    def send_message(self, message: object) -> None:
        self.sent.append(message)


def _send(monkeypatch, **overrides):
    settings = Settings(
        email_sender="smtp",
        smtp_host="smtp.example",
        smtp_username="postmaster",
        smtp_password="mail-password-value",
        **overrides,
    )
    _FakeSmtp.instances.clear()
    monkeypatch.setattr("smtplib.SMTP", _FakeSmtp)
    SmtpSender(settings).send(Message(to="a@example.test", subject="s", body="b"))
    return _FakeSmtp.instances[-1]


def test_starttls_verifies_the_certificate_and_the_hostname(monkeypatch) -> None:
    """Called with no context, smtplib builds one with verification switched off.

    ``ssl._create_stdlib_context()`` sets ``CERT_NONE`` and
    ``check_hostname=False``, so the session was encrypted to whoever answered
    on port 587 — and both the SMTP password and every password-reset link
    travelled through it.
    """
    smtp = _send(monkeypatch)

    assert smtp.started_tls is True
    assert smtp.tls_context is not None
    assert smtp.tls_context.verify_mode == ssl.CERT_REQUIRED
    assert smtp.tls_context.check_hostname is True


def test_the_password_reaches_smtp_and_nowhere_else(monkeypatch) -> None:
    smtp = _send(monkeypatch)
    assert smtp.login_with == ("postmaster", "mail-password-value")


def test_tls_is_established_before_the_credentials_are_offered(monkeypatch) -> None:
    """Ordering, not just presence: a login before STARTTLS is in the clear."""

    order: list[str] = []

    class _Ordered(_FakeSmtp):
        def starttls(self, context: ssl.SSLContext | None = None) -> None:
            order.append("starttls")
            super().starttls(context)

        def login(self, username: str, password: str) -> None:
            order.append("login")
            super().login(username, password)

    settings = Settings(
        email_sender="smtp",
        smtp_host="smtp.example",
        smtp_username="postmaster",
        smtp_password="mail-password-value",
    )
    monkeypatch.setattr("smtplib.SMTP", _Ordered)
    SmtpSender(settings).send(Message(to="a@example.test", subject="s", body="b"))

    assert order == ["starttls", "login"]


def test_the_console_sender_is_the_only_other_option() -> None:
    assert isinstance(get_sender(Settings(email_sender="console")), ConsoleSender)
    assert isinstance(get_sender(Settings(email_sender="anything-else")), ConsoleSender)
