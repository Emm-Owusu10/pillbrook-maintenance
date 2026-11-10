"""Sending email (decision D56). For now emails are either switched off or saved as files.

A real email service is added in a later step. Nothing here ever logs an email's content, because a
message can hold a one-time link.
"""
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .config import DEFAULT_OUTBOX_DIR, Settings
from .emails import normalise_email

logger = logging.getLogger("pillbrook.mail")

MAX_SUBJECT_LENGTH = 200
MAX_BODY_LENGTH = 20_000


class MailerError(Exception):
    """An email could not be sent. The message is safe to show and never contains the email's content."""


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str


class Mailer(Protocol):
    enabled: bool

    def send(self, message: EmailMessage) -> None: ...


def check_message(message: EmailMessage) -> EmailMessage:
    """Return the message with a checked, lowercase recipient, or raise MailerError."""
    # A line break in a header field is the classic way to smuggle in extra recipients or headers.
    for label, value in (("recipient", message.to), ("subject", message.subject)):
        if "\r" in value or "\n" in value:
            raise MailerError(f"The {label} must not contain line breaks.")
    try:
        recipient = normalise_email(message.to)
    except ValueError:
        raise MailerError("The recipient address is not valid.") from None
    subject = message.subject.strip()
    if not 1 <= len(subject) <= MAX_SUBJECT_LENGTH:
        raise MailerError(f"The subject must be 1 to {MAX_SUBJECT_LENGTH} characters.")
    if not 1 <= len(message.text) <= MAX_BODY_LENGTH:
        raise MailerError(f"The message must be 1 to {MAX_BODY_LENGTH} characters.")
    return EmailMessage(to=recipient, subject=subject, text=message.text)


class DisabledMailer:
    """Email is switched off. Features that need email must check `enabled` first."""

    enabled = False

    def send(self, message: EmailMessage) -> None:
        raise MailerError("Email sending is turned off.")


class OutboxMailer:
    """Development only: each email is saved as a text file instead of being sent."""

    enabled = True

    def __init__(self, directory: Path):
        self.directory = directory

    def send(self, message: EmailMessage) -> None:
        checked = check_message(message)
        self.directory.mkdir(parents=True, exist_ok=True)
        # The file name holds the time and a random part, never the address.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = self.directory / f"{stamp}-{secrets.token_hex(3)}.txt"
        content = f"To: {checked.to}\nSubject: {checked.subject}\n\n{checked.text}\n"
        with path.open("x", encoding="utf-8") as handle:  # "x": never overwrite an existing file
            handle.write(content)
        logger.info("Email saved to %s", path)


def make_mailer(settings: Settings, outbox_dir: Path = DEFAULT_OUTBOX_DIR) -> Mailer:
    if settings.mail_mode == "outbox":
        return OutboxMailer(outbox_dir)
    return DisabledMailer()