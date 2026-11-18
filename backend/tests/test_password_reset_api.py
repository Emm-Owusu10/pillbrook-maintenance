import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import auth_tokens
from app.mailer import OutboxMailer
from app.models import User
from tests.conftest import LOGIN_PASSWORD

PERSON = "ama@farm-mail.org"
NEW = "orange pepper mountain cloud"
INVALID_LINK = {"detail": "This link is not valid or has expired."}
FORGOT = {"message": "If that address belongs to an account, an email with a link is on its way."}


@pytest.fixture()
def emailing(make_db_app, add_user, small_list, tmp_path):
    """Email is on. Emails land in a temporary outbox, never your real one."""
    add_user(email=PERSON, role="user")
    app = make_db_app(mail_mode="outbox")
    outbox = tmp_path / "outbox"
    app.state.mailer = OutboxMailer(outbox)
    return app, TestClient(app), outbox


def _forgot(client, email=PERSON):
    return client.post("/api/auth/forgot-password", json={"email": email})


def _use_link(client, token, password=NEW):
    return client.post("/api/auth/reset-password", json={"token": token, "new_password": password})


def _emails(outbox):
    files = list(outbox.glob("*.txt")) if outbox.exists() else []
    return sorted(files, key=lambda path: path.stat().st_mtime_ns)


def _token_in(path):
    return re.search(r"#token=([A-Za-z0-9_-]+)", path.read_text(encoding="utf-8")).group(1)


def _sign_in(client, password, email=PERSON):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _link_code(app_engine, email, purpose):
    with Session(app_engine) as session:
        user_id = session.scalar(select(User.user_id).where(User.email == email))
        raw = auth_tokens.issue(session, user_id, purpose, timedelta(hours=1))
        session.commit()
    return raw


def test_the_screens_can_ask_whether_reset_by_email_is_available(make_db_app):
    assert TestClient(make_db_app()).get("/api/auth/options").json() == {"email_reset_available": False}
    assert TestClient(make_db_app(mail_mode="outbox")).get("/api/auth/options").json() == {"email_reset_available": True}


def test_asking_gets_the_same_answer_for_every_address(emailing, add_user):
    _app, client, _outbox = emailing
    add_user(email="gone@farm-mail.org", active=False)
    answers = [_forgot(client, address) for address in (PERSON, "nobody@farm-mail.org", "gone@farm-mail.org", "not an address")]
    assert {answer.status_code for answer in answers} == {202}
    assert all(answer.json() == FORGOT for answer in answers)


def test_only_an_active_known_address_receives_an_email(emailing, add_user):
    _app, client, outbox = emailing
    add_user(email="gone@farm-mail.org", active=False)
    for address in ("nobody@farm-mail.org", "gone@farm-mail.org", "not an address", PERSON):
        _forgot(client, address)
    [email] = _emails(outbox)
    content = email.read_text(encoding="utf-8")
    assert "To: ama@farm-mail.org" in content
    assert "http://127.0.0.1:5173/reset-password#token=" in content


def test_nothing_is_sent_or_recorded_when_email_is_off(make_db_app, add_user, tmp_path, owner_engine):
    add_user(email=PERSON, role="user")
    client = TestClient(make_db_app())  # email is off
    assert _forgot(client).json() == FORGOT
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM audit_log WHERE event_type = 'password_reset_requested'")).scalar_one() == 0


def test_at_most_three_emails_per_address_per_hour(emailing):
    _app, client, outbox = emailing
    for _ in range(4):
        assert _forgot(client).status_code == 202
    assert len(_emails(outbox)) == 3


def test_the_emailed_link_sets_a_new_password_once(emailing, owner_engine):
    app, client, outbox = emailing
    signed_in = TestClient(app)
    assert _sign_in(signed_in, LOGIN_PASSWORD).status_code == 200
    _forgot(client)
    token = _token_in(_emails(outbox)[-1])
    assert _use_link(client, token).status_code == 204
    assert signed_in.get("/api/auth/me").status_code == 401  # every sign-in ended
    assert _sign_in(TestClient(app), NEW).status_code == 200
    assert _sign_in(TestClient(app), LOGIN_PASSWORD).status_code == 401
    again = _use_link(client, token)
    assert (again.status_code, again.json()) == (400, INVALID_LINK)
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM audit_log WHERE event_type = 'password_reset_by_link'")).scalar_one() == 1


def test_unknown_expired_and_wrong_kind_links_are_all_refused_alike(emailing, owner_engine, app_engine):
    _app, client, outbox = emailing
    _forgot(client)
    token = _token_in(_emails(outbox)[-1])
    verify_code = _link_code(app_engine, PERSON, auth_tokens.VERIFY_EMAIL)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE auth_tokens SET expires_at = now() - interval '1 minute' WHERE purpose = 'reset_password'"))
    for candidate in ("x" * 43, token, verify_code):
        response = _use_link(client, candidate)
        assert (response.status_code, response.json()) == (400, INVALID_LINK), candidate


def test_a_weak_password_is_refused_and_the_link_is_not_wasted(emailing):
    _app, client, outbox = emailing
    _forgot(client)
    token = _token_in(_emails(outbox)[-1])
    weak = _use_link(client, token, "short")
    assert weak.status_code == 422
    assert {problem["field"] for problem in weak.json()["detail"]} == {"new_password"}
    assert _use_link(client, token).status_code == 204


def test_asking_again_cancels_the_earlier_link(emailing, owner_engine):
    _app, client, outbox = emailing
    _forgot(client)
    first = _token_in(_emails(outbox)[-1])
    _forgot(client)
    second = _token_in(_emails(outbox)[-1])
    assert first != second
    assert _use_link(client, first).status_code == 400
    assert _use_link(client, second).status_code == 204


def test_a_deactivated_account_cannot_use_a_link(emailing, owner_engine):
    _app, client, outbox = emailing
    _forgot(client)
    token = _token_in(_emails(outbox)[-1])
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET is_active = false"))
    assert _use_link(client, token).status_code == 400


def test_a_reset_clears_a_pending_temporary_password(emailing, owner_engine):
    _app, client, outbox = emailing
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET must_change_password = true, temporary_password_expires_at = now() + interval '1 hour'"))
    _forgot(client)
    assert _use_link(client, _token_in(_emails(outbox)[-1])).status_code == 204
    with owner_engine.connect() as connection:
        row = connection.execute(text("SELECT must_change_password, temporary_password_expires_at FROM users")).one()
    assert row.must_change_password is False
    assert row.temporary_password_expires_at is None


def test_no_reply_and_no_audit_entry_holds_a_password_or_a_link_code(emailing, owner_engine):
    _app, client, outbox = emailing
    replies = [_forgot(client)]
    token = _token_in(_emails(outbox)[-1])
    replies += [_use_link(client, "short-not-used-" + token[:5], NEW), _use_link(client, token)]
    with owner_engine.connect() as connection:
        audit_text = " ".join(str(v) for row in connection.execute(text("SELECT * FROM audit_log")).all() for v in row)
    for secret in (NEW, token, LOGIN_PASSWORD):
        assert secret not in audit_text
        assert all(secret not in reply.text for reply in replies)