import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import auth_tokens
from app.access import CSRF_MESSAGE, DENIED_MESSAGE
from app.models import User
from tests.conftest import LOGIN_PASSWORD

ADMIN = "admin@farm-mail.org"
PERSON = "ama@farm-mail.org"
SHAPE = re.compile(r"^[a-hjkmnp-z2-9]{4}(-[a-hjkmnp-z2-9]{4}){3}$")
GENERIC = {"detail": "Incorrect email or password."}


def _sign_in(client, email, password=LOGIN_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _csrf(client):
    return client.get("/api/auth/me").json()["csrf_token"]


def _reset(client, email=PERSON):
    return client.post(
        "/api/admin/users/reset-password", json={"email": email}, headers={"X-CSRF-Token": _csrf(client)}
    )


@pytest.fixture()
def world(make_db_app, add_user):
    """An Administrator who is signed in, and an ordinary person with an account."""
    add_user(email=ADMIN, role="admin")
    add_user(email=PERSON, role="user")
    app = make_db_app()
    admin = TestClient(app)
    assert _sign_in(admin, ADMIN).status_code == 200
    return app, admin


def test_the_administrator_gets_a_temporary_password_that_lasts_a_day(world, owner_engine):
    _app, admin = world
    response = _reset(admin)
    assert response.status_code == 200
    body = response.json()
    assert SHAPE.match(body["temporary_password"])
    assert body["email"] == PERSON
    assert body["name"]
    assert response.headers["cache-control"] == "no-store"
    with owner_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT must_change_password, "
                "temporary_password_expires_at > now() + interval '23 hours' AS long_enough, "
                "temporary_password_expires_at < now() + interval '25 hours' AS not_too_long "
                "FROM users WHERE email = :email"
            ),
            {"email": PERSON},
        ).one()
    assert row.must_change_password is True
    assert row.long_enough and row.not_too_long


def test_the_old_password_stops_working_and_every_sign_in_ends(world):
    app, admin = world
    person = TestClient(app)
    assert _sign_in(person, PERSON).status_code == 200
    assert person.get("/api/auth/me").status_code == 200
    _reset(admin)
    assert person.get("/api/auth/me").status_code == 401
    assert _sign_in(TestClient(app), PERSON).json() == GENERIC


def test_the_temporary_password_signs_the_person_in_and_says_a_new_one_is_needed(world):
    app, admin = world
    temporary = _reset(admin).json()["temporary_password"]
    for typed in (temporary, temporary.replace("-", ""), temporary.upper(), " " + temporary + " "):
        response = _sign_in(TestClient(app), PERSON, typed)
        assert response.status_code == 200, typed
        assert response.json()["must_change_password"] is True


def test_a_wrong_guess_at_the_temporary_password_is_refused(world):
    app, admin = world
    _reset(admin)
    assert _sign_in(TestClient(app), PERSON, "abcd-efgh-jkmn-pqrs").json() == GENERIC


def test_an_expired_temporary_password_is_refused_and_recorded(world, owner_engine):
    app, admin = world
    temporary = _reset(admin).json()["temporary_password"]
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET temporary_password_expires_at = now() - interval '1 minute' WHERE email = :e"), {"e": PERSON})
    response = _sign_in(TestClient(app), PERSON, temporary)
    assert response.status_code == 401
    assert response.json() == GENERIC
    with owner_engine.connect() as connection:
        details = connection.execute(text("SELECT detail FROM audit_log WHERE event_type = 'login_failure'")).scalars().all()
    assert details == ["temporary password expired"]


def test_the_reset_is_recorded_but_never_the_password(world, owner_engine):
    _app, admin = world
    temporary = _reset(admin).json()["temporary_password"]
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text("SELECT event_type, actor_id, target, detail FROM audit_log WHERE event_type = 'password_reset_by_admin'")
        ).all()
        everything = " ".join(str(v) for row in connection.execute(text("SELECT * FROM audit_log")).all() for v in row)
    assert len(rows) == 1
    assert rows[0].target == PERSON
    assert rows[0].actor_id is not None
    assert temporary not in everything
    assert temporary.replace("-", "") not in everything


def test_other_roles_may_not_reset_passwords(make_db_app, add_user):
    add_user(email=PERSON, role="user")
    add_user(email="manager@farm-mail.org", role="manager")
    add_user(email="user@farm-mail.org", role="user")
    app = make_db_app()
    for email in ("manager@farm-mail.org", "user@farm-mail.org"):
        client = TestClient(app)
        assert _sign_in(client, email).status_code == 200
        response = _reset(client)
        assert response.status_code == 403, email
        assert response.json() == {"detail": DENIED_MESSAGE}


def test_a_signed_out_visitor_and_a_missing_handshake_are_refused(world):
    app, admin = world
    anonymous = TestClient(app).post("/api/admin/users/reset-password", json={"email": PERSON})
    assert anonymous.status_code == 401
    no_token = admin.post("/api/admin/users/reset-password", json={"email": PERSON})
    assert no_token.status_code == 403
    assert no_token.json() == {"detail": CSRF_MESSAGE}


def test_the_administrator_cannot_reset_their_own_account(world):
    _app, admin = world
    response = _reset(admin, ADMIN)
    assert response.status_code == 400
    assert response.json() == {"detail": "Use Change password for your own account."}


def test_unknown_and_deactivated_accounts_are_refused(world, owner_engine):
    _app, admin = world
    assert _reset(admin, "nobody@farm-mail.org").status_code == 404
    assert _reset(admin, "not an address").status_code == 404
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET is_active = false WHERE email = :e"), {"e": PERSON})
    response = _reset(admin)
    assert response.status_code == 409
    assert response.json() == {"detail": "That account is deactivated."}


def test_a_reset_cancels_a_reset_link_that_was_already_emailed(world, app_engine):
    _app, admin = world
    with Session(app_engine) as session:
        user_id = session.scalar(select(User.user_id).where(User.email == PERSON))
        link_code = auth_tokens.issue(session, user_id, auth_tokens.RESET_PASSWORD, timedelta(hours=1))
        session.commit()
        assert auth_tokens.peek(session, link_code, auth_tokens.RESET_PASSWORD) == user_id
    _reset(admin)
    with Session(app_engine) as session:
        assert auth_tokens.peek(session, link_code, auth_tokens.RESET_PASSWORD) is None