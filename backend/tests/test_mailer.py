import pytest

from app.config import Settings
from app.mailer import (
    DisabledMailer,
    EmailMessage,
    MailerError,
    OutboxMailer,
    make_mailer,
)

GOOD = EmailMessage(to="Ama@Farm-Mail.org", subject="Confirm your email", text="Open this link: https://example.invalid/x")


def _files(directory):
    return sorted(directory.glob("*.txt"))


def test_an_email_is_saved_as_a_readable_file(tmp_path):
    OutboxMailer(tmp_path / "outbox").send(GOOD)
    [saved] = _files(tmp_path / "outbox")
    assert saved.read_text(encoding="utf-8") == (
        "To: ama@farm-mail.org\nSubject: Confirm your email\n\nOpen this link: https://example.invalid/x\n"
    )


def test_the_outbox_folder_is_created_when_missing(tmp_path):
    directory = tmp_path / "does" / "not" / "exist"
    OutboxMailer(directory).send(GOOD)
    assert len(_files(directory)) == 1


def test_the_file_name_never_contains_the_address(tmp_path):
    OutboxMailer(tmp_path).send(GOOD)
    [saved] = _files(tmp_path)
    assert "ama" not in saved.name.lower()
    assert "farm-mail" not in saved.name.lower()


def test_two_emails_never_share_a_file(tmp_path):
    mailer = OutboxMailer(tmp_path)
    for _ in range(20):
        mailer.send(GOOD)
    assert len(_files(tmp_path)) == 20


def test_unicode_text_is_kept_exactly(tmp_path):
    message = EmailMessage(to="ama@farm-mail.org", subject="Caf\u00e9", text="Mensah \u2013 \u00e9\u00e8 \U0001f642")
    OutboxMailer(tmp_path).send(message)
    [saved] = _files(tmp_path)
    assert "Mensah \u2013 \u00e9\u00e8 \U0001f642" in saved.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "subject",
    ["Hello\r\nBcc: attacker@farm-mail.org", "Hello\nX-Header: 1", "Hello\rWorld"],
)
def test_line_breaks_in_the_subject_are_refused(tmp_path, subject):
    with pytest.raises(MailerError, match="line breaks"):
        OutboxMailer(tmp_path).send(EmailMessage(to="ama@farm-mail.org", subject=subject, text="x"))
    assert _files(tmp_path) == []


def test_line_breaks_in_the_recipient_are_refused(tmp_path):
    with pytest.raises(MailerError, match="line breaks"):
        OutboxMailer(tmp_path).send(EmailMessage(to="ama@farm-mail.org\nbcc: x@farm-mail.org", subject="Hi", text="x"))
    assert _files(tmp_path) == []


@pytest.mark.parametrize("recipient", ["", "not-an-address", "a@@farm-mail.org", "ama@localhost"])
def test_an_invalid_recipient_is_refused(tmp_path, recipient):
    with pytest.raises(MailerError, match="not valid"):
        OutboxMailer(tmp_path).send(EmailMessage(to=recipient, subject="Hi", text="x"))
    assert _files(tmp_path) == []


def test_empty_and_oversized_messages_are_refused(tmp_path):
    mailer = OutboxMailer(tmp_path)
    for subject, text in (("", "x"), ("   ", "x"), ("s" * 201, "x"), ("Hi", ""), ("Hi", "b" * 20_001)):
        with pytest.raises(MailerError):
            mailer.send(EmailMessage(to="ama@farm-mail.org", subject=subject, text=text))
    assert _files(tmp_path) == []


def test_error_messages_never_repeat_the_content():
    secret = "https://example.invalid/one-time-link-secret"
    with pytest.raises(MailerError) as error:
        DisabledMailer().send(EmailMessage(to="ama@farm-mail.org", subject="Hi", text=secret))
    assert "one-time-link-secret" not in str(error.value)


def test_a_switched_off_mailer_refuses_to_send():
    mailer = DisabledMailer()
    assert mailer.enabled is False
    with pytest.raises(MailerError, match="turned off"):
        mailer.send(GOOD)


def test_the_mode_decides_which_mailer_is_used(tmp_path):
    off = make_mailer(Settings(environment="development", secret_key="k" * 40), tmp_path)
    outbox = make_mailer(Settings(environment="development", secret_key="k" * 40, mail_mode="outbox"), tmp_path)
    assert isinstance(off, DisabledMailer)
    assert isinstance(outbox, OutboxMailer)
    assert outbox.enabled is True


def test_the_application_starts_with_the_mailer_its_settings_ask_for(make_app):
    assert make_app().state.mailer.enabled is False
    assert make_app(mail_mode="outbox").state.mailer.enabled is True