"""Outbound email, with a sender you can actually run locally.

``get_sender`` returns one of two senders and no third. The console sender
logs the message and is what development and the demo use; the SMTP sender is
what production must be configured with, and startup refuses `console` there —
a reset link that is silently written to a log nobody reads is worse than no
reset at all. The one other class here, ``RecordingSender``, is a test sink:
it keeps the messages instead of sending them, and ``get_sender`` never
selects it — a test has to install it explicitly at the seam the routes use.

Nothing here formats applicant data into a message. The only mail this product
sends is about the account itself.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from app.config import Settings

log = logging.getLogger("unimatch.mail")


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    body: str


class EmailSender:
    """The interface the routes depend on."""

    def send(self, message: Message) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleSender(EmailSender):
    """Logs instead of sending. Honest about being a stub."""

    def send(self, message: Message) -> None:
        log.info(
            "email not sent (console sender): to=%s subject=%s\n%s",
            message.to,
            message.subject,
            message.body,
        )


class SmtpSender(EmailSender):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: Message) -> None:
        mail = EmailMessage()
        mail["From"] = self.settings.smtp_from
        mail["To"] = message.to
        mail["Subject"] = message.subject
        mail.set_content(message.body)
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
            # The default context verifies the relay's certificate; without one
            # smtplib would silently negotiate an encrypted but unauthenticated
            # connection, and a machine on the path could relay the reset link.
            ctx = ssl.create_default_context()
            if not self.settings.smtp_tls_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            smtp.starttls(context=ctx)
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(mail)


class RecordingSender(EmailSender):
    """Collects every message the product would send, for tests to read.

    A stand-in for the user's mailbox, not a sender: nothing leaves the
    process. ``get_sender`` never returns it — a test injects it where the
    route resolves its sender (``app.api.routes_account.get_sender``) — so no
    environment, however misconfigured, can deliver mail through this class.
    """

    def __init__(self) -> None:
        self.messages: list[Message] = []

    def send(self, message: Message) -> None:
        self.messages.append(message)


def get_sender(settings: Settings) -> EmailSender:
    return SmtpSender(settings) if settings.email_sender == "smtp" else ConsoleSender()
