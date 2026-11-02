import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.passwords import needs_rehash
from tests.conftest import LOGIN_PASSWORD

EMAIL = "ama@farm-mail.org"
GENERIC = {"detail": "Incorrect email or password."}


def _login(client, email=EMAIL, password=LOGIN_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _csrf(client):
    return client.get("/api/auth/me").json()["csrf_token"]


@pytest.fixture()
def api(make_db_app, add_user):
    add_user()
    return TestClient(make_db_app())


# ---- Logging in ----

def test_a_correct_login_returns_the_user_and_a_csrf_token(api):
    response = _login(api)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == EMAIL
    assert body["user"]["role"] == "user"
    assert set(body["user"]) == {"user_id", "name", "email", "role"}
    assert len(body["csrf_token"]) == 64
    assert LOGIN_PASSWORD not in response.text


def test_the_session_cookie_is_protected_in_development(api):
    cookie = _login(api).headers["set-cookie"].lower()
    assert cookie.startswith("session=")
    for flag in ("httponly", "samesite=strict", "path=/", "max-age=43200"):
        assert flag in cookie
    assert "secure" not in cookie


def test_the_session_cookie_is_locked_down_in_production(make_db_app, add_user):
    add_user()
    production = TestClient(make_db_app(environment="production"))
    cookie = _login(production).headers["set-cookie"].lower()
    assert cookie.startswith("__host-session=")
    for flag in ("secure", "httponly", "samesite=strict", "path=/"):
        assert flag in cookie
    assert "domain=" not in cookie


@pytest.mark.parametrize(
    "email, password",
    [
        (EMAIL, "wrong password entirely"),
        ("nobody@farm-mail.org", LOGIN_PASSWORD),
        ("not an email", LOGIN_PASSWORD),
        ("", ""),
    ],
)
def test_every_kind_of_failed_login_gets_the_same_answer(api, email, password):
    response = _login(api, email, password)
    assert response.status_code == 401
    assert response.json() == GENERIC
    assert "set-cookie" not in response.headers


def test_unverified_and_deactivated_accounts_cannot_log_in(make_db_app, add_user):
    add_user(email="new@farm-mail.org", verified=False)
    add_user(email="gone@farm-mail.org", active=False)
    client = TestClient(make_db_app())
    for email in ("new@farm-mail.org", "gone@farm-mail.org"):
        response = _login(client, email)
        assert response.status_code == 401
        assert response.json() == GENERIC


def test_login_needs_a_json_body(api):
    response = api.post("/api/auth/login", data={"email": EMAIL, "password": LOGIN_PASSWORD})
    assert response.status_code == 422


def test_an_enormous_password_is_rejected_before_any_hashing(api):
    assert _login(api, password="x" * 5000).status_code == 422


def test_an_old_hash_is_upgraded_at_login(make_db_app, add_user, owner_engine):
    add_user()
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(LOGIN_PASSWORD)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET password_hash = :hash"), {"hash": weak})
    client = TestClient(make_db_app())
    assert _login(client).status_code == 200
    with owner_engine.connect() as connection:
        stored = connection.execute(text("SELECT password_hash FROM users")).scalar_one()
    assert stored != weak
    assert not needs_rehash(stored)


# ---- The signed-in user ----

def test_me_needs_a_session(api):
    assert api.get("/api/auth/me").status_code == 401


def test_me_returns_the_user_and_the_same_csrf_token_each_time(api):
    first = _login(api).json()
    me = api.get("/api/auth/me").json()
    assert me["user"]["email"] == EMAIL
    assert me["csrf_token"] == first["csrf_token"] == api.get("/api/auth/me").json()["csrf_token"]


def test_only_a_fingerprint_of_the_session_code_is_stored(api, owner_engine):
    _login(api)
    code = api.cookies.get("session")
    with owner_engine.connect() as connection:
        stored = connection.execute(text("SELECT token_hash FROM sessions")).scalar_one()
    assert stored != code
    assert len(stored) == 64
    assert code not in stored


def test_logging_in_again_replaces_the_old_session(api, owner_engine):
    _login(api)
    first_code = api.cookies.get("session")
    _login(api)
    assert api.cookies.get("session") != first_code
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 1


def test_expired_sessions_are_cleaned_up_at_login(api, owner_engine):
    _login(api)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE sessions SET expires_at = now() - interval '1 hour'"))
    api.cookies.clear()
    _login(api)
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 1


# ---- Ending sessions ----

def test_logout_needs_the_csrf_token(api):
    _login(api)
    assert api.post("/api/auth/logout").status_code == 403
    assert api.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert api.get("/api/auth/me").status_code == 200  # still signed in


def test_a_csrf_token_from_another_session_is_refused(make_db_app, add_user):
    add_user()
    one = TestClient(make_db_app())
    two = TestClient(make_db_app())
    _login(one)
    _login(two)
    assert one.post("/api/auth/logout", headers={"X-CSRF-Token": _csrf(two)}).status_code == 403


def test_logout_ends_the_session(api, owner_engine):
    _login(api)
    response = api.post("/api/auth/logout", headers={"X-CSRF-Token": _csrf(api)})
    assert response.status_code == 204
    assert api.get("/api/auth/me").status_code == 401
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 0
        count = connection.execute(text("SELECT count(*) FROM audit_log WHERE event_type = 'logout'"))
        assert count.scalar_one() == 1


def test_logout_without_a_session_is_harmless(api):
    assert api.post("/api/auth/logout").status_code == 204


def test_a_session_ends_after_an_hour_of_inactivity(api, owner_engine):
    _login(api)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE sessions SET last_seen_at = now() - interval '61 minutes'"))
    assert api.get("/api/auth/me").status_code == 401
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 0
        count = connection.execute(text("SELECT count(*) FROM audit_log WHERE event_type = 'session_expired'"))
        assert count.scalar_one() == 1


def test_activity_keeps_a_session_alive(api, owner_engine):
    _login(api)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE sessions SET last_seen_at = now() - interval '59 minutes'"))
    assert api.get("/api/auth/me").status_code == 200
    with owner_engine.connect() as connection:
        age = connection.execute(text("SELECT now() - last_seen_at FROM sessions")).scalar_one()
    assert age.total_seconds() < 120


def test_a_session_ends_after_twelve_hours_even_if_active(api, owner_engine):
    _login(api)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE sessions SET expires_at = now() - interval '1 minute'"))
    assert api.get("/api/auth/me").status_code == 401


def test_deactivating_a_user_ends_their_session_at_once(api, owner_engine):
    _login(api)
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET is_active = false"))
    assert api.get("/api/auth/me").status_code == 401


# ---- Throttling and the audit log ----

def test_four_wrong_passwords_lock_the_account_for_ten_minutes(api, owner_engine):
    for _ in range(4):
        assert _login(api, password="wrong password entirely").status_code == 401
    blocked = _login(api)  # even the right password is refused while locked
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "600"
    assert "Too many" in blocked.json()["detail"]
    _login(api, password="another wrong one")  # refused, and not counted
    with owner_engine.connect() as connection:
        rows = connection.execute(text("SELECT event_type, count(*) AS n FROM audit_log GROUP BY event_type")).all()
    assert {row.event_type: row.n for row in rows} == {"login_failure": 4, "login_locked": 1}


def test_the_lock_lifts_after_ten_minutes(api, owner_engine):
    for _ in range(4):
        _login(api, password="wrong password entirely")
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE audit_log SET created_at = now() - interval '11 minutes'"))
    assert _login(api).status_code == 200


def test_unknown_emails_are_throttled_the_same_way(api):
    for _ in range(4):
        _login(api, "nobody@farm-mail.org", "whatever password here")
    assert _login(api, "nobody@farm-mail.org").status_code == 429


def test_a_successful_login_clears_earlier_failures(api):
    for _ in range(3):
        _login(api, password="wrong password entirely")
    assert _login(api).status_code == 200
    for _ in range(3):
        assert _login(api, password="wrong password entirely").status_code == 401
    assert _login(api).status_code == 200


def test_the_audit_log_records_events_but_never_passwords(api, owner_engine):
    wrong = "wrong password entirely"
    _login(api, password=wrong)
    _login(api, email="typed-a-password-here-by-mistake")
    _login(api)
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text("SELECT event_type, actor_id, target, detail FROM audit_log ORDER BY created_at")
        ).all()
    assert [row.event_type for row in rows] == ["login_failure", "login_failure", "login_success"]
    assert rows[0].target == EMAIL
    assert rows[1].target is None  # not a valid email address, so it is not stored
    assert rows[2].actor_id is not None
    assert rows[2].target == EMAIL
    everything = " ".join(str(value) for row in rows for value in row)
    assert wrong not in everything
    assert LOGIN_PASSWORD not in everything
    assert "typed-a-password" not in everything