from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import account_security, auth_tokens
from app.access import CSRF_MESSAGE
from app.models import User
from tests.conftest import LOGIN_PASSWORD

PERSON = "ama@farm-mail.org"
OLD = LOGIN_PASSWORD
NEW = "orange pepper mountain cloud"
WRONG_CURRENT = {"detail": "The current password is not correct."}


def _sign_in(client, password=OLD, email=PERSON):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _csrf(client):
    return client.get("/api/auth/me").json()["csrf_token"]


def _change(client, current=OLD, new=NEW):
    return client.post(
        "/api/auth/change-password",
        json={"current_password": current, "new_password": new},
        headers={"X-CSRF-Token": _csrf(client)},
    )


@pytest.fixture()
def person(make_db_app, add_user, small_list):
    add_user(email=PERSON, role="user")
    app = make_db_app()
    client = TestClient(app)
    assert _sign_in(client).status_code == 200
    return app, client


def test_changing_the_password_works_and_signs_out_every_other_browser(person, owner_engine):
    app, client = person
    other = TestClient(app)
    assert _sign_in(other).status_code == 200
    assert _change(client).status_code == 204
    assert client.get("/api/auth/me").status_code == 200  # the browser that made the change stays signed in
    assert other.get("/api/auth/me").status_code == 401
    assert _sign_in(TestClient(app), NEW).status_code == 200
    assert _sign_in(TestClient(app), OLD).status_code == 401
    with owner_engine.connect() as connection:
        rows = connection.execute(text("SELECT event_type FROM audit_log WHERE event_type = 'password_changed'")).all()
        everything = " ".join(str(v) for row in connection.execute(text("SELECT * FROM audit_log")).all() for v in row)
    assert len(rows) == 1
    assert NEW not in everything and OLD not in everything


def test_a_wrong_current_password_changes_nothing(person, owner_engine):
    app, client = person
    response = _change(client, current="not the current password")
    assert response.status_code == 403
    assert response.json() == WRONG_CURRENT
    assert _sign_in(TestClient(app), OLD).status_code == 200
    with owner_engine.connect() as connection:
        details = connection.execute(text("SELECT detail FROM audit_log WHERE event_type = 'login_failure'")).scalars().all()
    assert details == ["wrong current password"]


def test_wrong_guesses_at_the_current_password_lock_the_account_like_sign_in(person):
    app, client = person
    for _ in range(4):
        assert _change(client, current="not the current password").status_code == 403
    locked = _change(client, current=OLD)  # even the right password is refused while locked
    assert locked.status_code == 429
    assert locked.headers["retry-after"] == "600"
    assert _sign_in(TestClient(app), OLD).status_code == 429


def test_a_weak_new_password_is_refused_with_its_reasons(person):
    app, client = person
    response = _change(client, new="short")
    assert response.status_code == 422
    assert {problem["field"] for problem in response.json()["detail"]} == {"new_password"}
    assert _sign_in(TestClient(app), OLD).status_code == 200


def test_the_new_password_must_differ_from_the_current_one(person):
    _app, client = person
    assert _change(client).status_code == 204
    again = _change(client, current=NEW, new=NEW)
    assert again.status_code == 422
    assert again.json()["detail"] == [{"field": "new_password", "message": "Choose a password different from your current one."}]


def test_it_needs_a_sign_in_and_the_handshake_word(person):
    app, client = person
    body = {"current_password": OLD, "new_password": NEW}
    assert TestClient(app).post("/api/auth/change-password", json=body).status_code == 401
    no_token = client.post("/api/auth/change-password", json=body)
    assert no_token.status_code == 403
    assert no_token.json() == {"detail": CSRF_MESSAGE}


def test_a_temporary_password_is_replaced_at_first_sign_in(make_db_app, add_user, small_list, app_engine, owner_engine):
    add_user(email=PERSON, role="user")
    app = make_db_app()
    with Session(app_engine) as session:
        user = session.scalar(select(User).where(User.email == PERSON))
        temporary, _expires = account_security.issue_temporary_password(session, user)
        session.commit()
    client = TestClient(app)
    typed = temporary.replace("-", "")  # typed without its dashes
    signed_in = _sign_in(client, typed)
    assert signed_in.status_code == 200
    assert signed_in.json()["must_change_password"] is True

    assert _change(client, current=typed).status_code == 204
    assert client.get("/api/auth/me").json()["must_change_password"] is False
    with owner_engine.connect() as connection:
        row = connection.execute(text("SELECT must_change_password, temporary_password_expires_at FROM users")).one()
    assert row.must_change_password is False
    assert row.temporary_password_expires_at is None
    assert _sign_in(TestClient(app), NEW).status_code == 200
    assert _sign_in(TestClient(app), temporary).status_code == 401  # the temporary password is spent


def test_changing_the_password_cancels_a_reset_link_already_emailed(person, app_engine):
    _app, client = person
    with Session(app_engine) as session:
        user_id = session.scalar(select(User.user_id).where(User.email == PERSON))
        link_code = auth_tokens.issue(session, user_id, auth_tokens.RESET_PASSWORD, timedelta(hours=1))
        session.commit()
    assert _change(client).status_code == 204
    with Session(app_engine) as session:
        assert auth_tokens.peek(session, link_code, auth_tokens.RESET_PASSWORD) is None