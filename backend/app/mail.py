"""Outbound email, with a sender you can actually run locally.

There are two senders and no third. The console sender logs the message and is
what development and the demo use; the SMTP sender is what production must be
configured with, and startup refuses `console` there — a reset link that is
silently written to a log nobody reads is worse than no reset at all.

Nothing here formats applicant data into a message. The only mail this product
sends is about the account itself.
"""

from __future__ import annotations

import logging
import smtplib
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
            smtp.starttls()
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(mail)


def get_sender(settings: Settings) -> EmailSender:
    return SmtpSender(settings) if settings.email_sender == "smtp" else ConsoleSender()
