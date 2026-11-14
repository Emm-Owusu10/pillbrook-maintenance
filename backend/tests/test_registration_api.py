import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.farm import set_access_code
from app.mailer import MailerError, OutboxMailer
from tests.conftest import TEST_KEY

CODE = "K7QM4TRX9WBH"
PASSWORD = "correct horse battery staple"
EMAIL = "ama@farm-mail.org"
WRONG_CODE = {"detail": "The farm access code is not correct."}
INVALID_LINK = {"detail": "This link is not valid or has expired."}


class FailingMailer:
    enabled = True

    def send(self, message):
        raise MailerError("The mail service is down.")


@pytest.fixture()
def open_registration(migrated, app_engine, small_list):
    """The farm access code is set, so registration is open."""
    with Session(app_engine) as session:
        set_access_code(session, TEST_KEY, CODE)


@pytest.fixture()
def api(open_registration, make_db_app):
    return TestClient(make_db_app())


@pytest.fixture()
def verifying(open_registration, make_db_app, tmp_path):
    """Email is on and verification is required. Emails land in a temporary outbox, never your real one."""
    app = make_db_app(mail_mode="outbox", require_email_verification=True)
    outbox = tmp_path / "outbox"
    app.state.mailer = OutboxMailer(outbox)
    return TestClient(app), outbox


def _register(client, **overrides):
    body = {"name": "Ama Mensah", "email": EMAIL, "password": PASSWORD, "access_code": CODE}
    body.update(overrides)
    return client.post("/api/auth/register", json=body)


def _sign_in(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _count(owner_engine, sql):
    with owner_engine.connect() as connection:
        return connection.execute(text(sql)).scalar_one()


def _emails(outbox):
    files = list(outbox.glob("*.txt")) if outbox.exists() else []
    return sorted(files, key=lambda path: path.stat().st_mtime_ns)


def _token_in(path):
    return re.search(r"#token=([A-Za-z0-9_-]+)", path.read_text(encoding="utf-8")).group(1)


def _verify(client, token):
    return client.post("/api/auth/verify-email", json={"token": token})


# ---- The access code ----

def test_registration_stays_closed_until_a_code_is_set(make_db_app):
    response = _register(TestClient(make_db_app()))
    assert response.status_code == 403
    assert response.json() == {"detail": "Registration is not open yet. Ask the Administrator."}


def test_the_right_code_creates_a_farm_user(api, owner_engine):
    response = _register(api)
    assert response.status_code == 201
    assert response.json() == {"verification_required": False, "verification_email_sent": False}
    with owner_engine.connect() as connection:
        row = connection.execute(
            text("SELECT role, email_verified_at, is_active, password_hash FROM users")
        ).one()
    assert row.role == "user"
    assert row.email_verified_at is None
    assert row.is_active is True
    assert row.password_hash.startswith("$argon2id$")
    assert PASSWORD not in row.password_hash


def test_the_code_works_in_any_case_with_or_without_hyphens_and_spaces(api):
    variants = ["k7qm-4trx-9wbh", " K7QM 4TRX 9WBH ", "k7qm4trx9wbh"]
    for number, variant in enumerate(variants):
        response = _register(api, email=f"person{number}@farm-mail.org", access_code=variant)
        assert response.status_code == 201, variant


def test_a_wrong_code_creates_nothing_and_is_recorded_without_the_code(api, owner_engine):
    response = _register(api, access_code="WRONGCODE123")
    assert response.status_code == 403
    assert response.json() == WRONG_CODE
    assert _count(owner_engine, "SELECT count(*) FROM users") == 0
    assert _count(owner_engine, "SELECT count(*) FROM audit_log WHERE event_type = 'registration_code_failure'") == 1
    with owner_engine.connect() as connection:
        everything = " ".join(str(v) for row in connection.execute(text("SELECT * FROM audit_log")).all() for v in row)
    assert "WRONGCODE123" not in everything


def test_the_code_is_checked_before_anything_else(api):
    _register(api)  # the address is now registered
    taken = _register(api, access_code="WRONGCODE123", password="short")
    free = _register(api, email="new@farm-mail.org", access_code="WRONGCODE123", password="short")
    assert (taken.status_code, taken.json()) == (free.status_code, free.json()) == (403, WRONG_CODE)


def test_ten_wrong_codes_pause_registration_for_everyone(api, owner_engine):
    for _ in range(10):
        assert _register(api, access_code="WRONGCODE123").status_code == 403
    paused = _register(api)  # even the right code is refused while paused
    assert paused.status_code == 429
    assert paused.headers["retry-after"] == "600"
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT event_type, count(*) AS n FROM audit_log "
                "WHERE event_type IN ('registration_code_failure', 'registration_paused') "
                "GROUP BY event_type"
            )
        ).all()
    assert {row.event_type: row.n for row in rows} == {"registration_code_failure": 10, "registration_paused": 1}
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE audit_log SET created_at = now() - interval '11 minutes'"))
    assert _register(api).status_code == 201


# ---- The details ----

def test_every_problem_with_the_details_is_reported_together(api):
    response = _register(api, name="", email="not-an-email", password="short")
    assert response.status_code == 422
    assert {problem["field"] for problem in response.json()["detail"]} == {"name", "email", "password"}


def test_a_name_may_not_hold_line_breaks_or_be_too_long(api):
    for name in ("Ama\nMensah", "n" * 101):
        response = _register(api, name=name)
        assert response.status_code == 422
        assert [problem["field"] for problem in response.json()["detail"]] == ["name"]


def test_the_password_may_not_contain_the_email_name(api):
    response = _register(api, email="mensahfarm@farm-mail.org", password="my-mensahfarm-secret-phrase")
    assert response.status_code == 422
    assert any("Do not include" in problem["message"] for problem in response.json()["detail"])


def test_nothing_is_created_when_the_details_are_wrong(api, owner_engine):
    assert _register(api, password="short").status_code == 422
    assert _count(owner_engine, "SELECT count(*) FROM users") == 0


def test_an_address_that_is_already_registered_is_refused_whatever_its_case(api, owner_engine):
    assert _register(api).status_code == 201
    again = _register(api, email="AMA@Farm-Mail.org")
    assert again.status_code == 409
    assert again.json() == {"detail": "An account with this email address already exists."}
    assert _count(owner_engine, "SELECT count(*) FROM users") == 1


def test_a_new_account_can_sign_in_when_verification_is_not_required(api):
    _register(api)
    response = _sign_in(api)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "user"


# ---- Email verification ----

def test_registration_sends_a_verification_email_when_it_is_required(verifying):
    client, outbox = verifying
    response = _register(client)
    assert response.status_code == 201
    assert response.json() == {"verification_required": True, "verification_email_sent": True}
    [email] = _emails(outbox)
    content = email.read_text(encoding="utf-8")
    assert "To: ama@farm-mail.org" in content
    assert "Hello Ama Mensah" in content
    assert "http://127.0.0.1:5173/verify-email#token=" in content
    assert _sign_in(client).status_code == 401  # not confirmed yet


def test_the_emailed_link_confirms_the_address_once(verifying, owner_engine):
    client, outbox = verifying
    _register(client)
    token = _token_in(_emails(outbox)[-1])
    response = _verify(client, token)
    assert response.status_code == 200
    assert response.json() == {"verified": True}
    assert _count(owner_engine, "SELECT count(*) FROM users WHERE email_verified_at IS NOT NULL") == 1
    assert _sign_in(client).status_code == 200
    again = _verify(client, token)
    assert again.status_code == 400
    assert again.json() == INVALID_LINK


def test_unknown_used_and_expired_links_are_all_refused_alike(verifying, owner_engine):
    client, outbox = verifying
    _register(client)
    token = _token_in(_emails(outbox)[-1])
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE auth_tokens SET expires_at = now() - interval '1 minute'"))
    for candidate in (token, "x" * 43):
        response = _verify(client, candidate)
        assert response.status_code == 400
        assert response.json() == INVALID_LINK


def test_only_a_fingerprint_of_the_link_code_is_stored(verifying, owner_engine):
    client, outbox = verifying
    _register(client)
    token = _token_in(_emails(outbox)[-1])
    with owner_engine.connect() as connection:
        stored = connection.execute(text("SELECT token_hash FROM auth_tokens")).scalar_one()
    assert stored != token
    assert len(stored) == 64
    assert token not in stored


def test_asking_again_gets_the_same_answer_for_every_address(verifying):
    client, outbox = verifying
    _register(client)  # unverified
    _register(client, name="Kofi Boateng", email="kofi@farm-mail.org")
    assert _verify(client, _token_in(_emails(outbox)[-1])).status_code == 200  # kofi is now verified
    answers = [
        client.post("/api/auth/resend-verification", json={"email": address})
        for address in (EMAIL, "kofi@farm-mail.org", "nobody@farm-mail.org", "not an address")
    ]
    assert {answer.status_code for answer in answers} == {202}
    assert len({answer.text for answer in answers}) == 1


def test_asking_again_sends_a_new_email_and_the_old_link_stops_working(verifying):
    client, outbox = verifying
    _register(client)
    old = _token_in(_emails(outbox)[-1])
    assert client.post("/api/auth/resend-verification", json={"email": EMAIL}).status_code == 202
    emails = _emails(outbox)
    assert len(emails) == 2
    new = _token_in(emails[-1])
    assert new != old
    assert _verify(client, old).status_code == 400
    assert _verify(client, new).status_code == 200


def test_at_most_three_more_emails_per_address_per_hour(verifying):
    client, outbox = verifying
    _register(client)  # the first email
    for _ in range(4):
        assert client.post("/api/auth/resend-verification", json={"email": EMAIL}).status_code == 202
    assert len(_emails(outbox)) == 4  # the first, plus three; the fourth request sent nothing


def test_nothing_is_sent_when_verification_is_not_required(open_registration, make_db_app, tmp_path, owner_engine):
    app = make_db_app(mail_mode="outbox", require_email_verification=False)
    outbox = tmp_path / "outbox"
    app.state.mailer = OutboxMailer(outbox)
    client = TestClient(app)
    assert _register(client).json() == {"verification_required": False, "verification_email_sent": False}
    assert client.post("/api/auth/resend-verification", json={"email": EMAIL}).status_code == 202
    assert _emails(outbox) == []
    assert _count(owner_engine, "SELECT count(*) FROM audit_log WHERE event_type = 'verification_requested'") == 0


def test_a_failed_email_does_not_lose_the_account(open_registration, make_db_app, owner_engine):
    app = make_db_app(mail_mode="outbox", require_email_verification=True)
    app.state.mailer = FailingMailer()
    response = _register(TestClient(app))
    assert response.status_code == 201
    assert response.json() == {"verification_required": True, "verification_email_sent": False}
    assert _count(owner_engine, "SELECT count(*) FROM users") == 1
    assert _count(owner_engine, "SELECT count(*) FROM audit_log WHERE event_type = 'verification_email_failed'") == 1


def test_no_reply_and_no_audit_entry_holds_the_code_the_password_or_a_link_code(verifying, owner_engine):
    client, outbox = verifying
    replies = [_register(client, access_code="WRONGCODE123"), _register(client)]
    token = _token_in(_emails(outbox)[-1])
    replies.append(client.post("/api/auth/resend-verification", json={"email": EMAIL}))
    replies.append(_verify(client, token))
    with owner_engine.connect() as connection:
        audit_text = " ".join(str(v) for row in connection.execute(text("SELECT * FROM audit_log")).all() for v in row)
    for secret in (CODE, "WRONGCODE123", PASSWORD, token):
        assert secret not in audit_text
    for reply in replies:
        assert CODE not in reply.text
        assert PASSWORD not in reply.text