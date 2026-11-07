import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.access import CSRF_MESSAGE, DENIED_MESSAGE, require_permission
from app.permissions import Permission, has_permission, permissions_for
from tests.conftest import LOGIN_PASSWORD

ROLES = ["user", "manager", "admin"]


def _ok():
    return {"ok": True}


@pytest.fixture()
def guarded(make_db_app):
    """An application with one guarded test route per permission, for reading and for changing."""

    def _build():
        app = make_db_app()
        for permission in Permission:
            app.add_api_route(
                f"/api/test/read/{permission.value}", _ok, methods=["GET"],
                dependencies=[Depends(require_permission(permission))],
            )
            app.add_api_route(
                f"/api/test/change/{permission.value}", _ok, methods=["POST"],
                dependencies=[Depends(require_permission(permission, changes_data=True))],
            )
        return app

    return _build


def _signed_in(app, add_user, role):
    email = f"{role}@farm-mail.org"
    add_user(email=email, role=role)
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": email, "password": LOGIN_PASSWORD})
    assert response.status_code == 200
    return client


@pytest.mark.parametrize("role", ROLES)
def test_each_role_can_use_exactly_its_own_functions(guarded, add_user, role):
    client = _signed_in(guarded(), add_user, role)
    for permission in Permission:
        expected = 200 if has_permission(role, permission) else 403
        response = client.get(f"/api/test/read/{permission.value}")
        assert response.status_code == expected, f"{role} / {permission.value}"


def test_a_signed_out_visitor_gets_401_not_403(guarded):
    client = TestClient(guarded())
    assert client.get("/api/test/read/submit_request").status_code == 401


def test_the_refusal_does_not_reveal_what_would_have_been_needed(guarded, add_user):
    client = _signed_in(guarded(), add_user, "user")
    response = client.get("/api/test/read/manage_users")
    assert response.status_code == 403
    assert response.json() == {"detail": DENIED_MESSAGE}
    assert "manage_users" not in response.text


def test_a_refused_attempt_is_recorded_and_an_allowed_one_is_not(guarded, add_user, owner_engine):
    client = _signed_in(guarded(), add_user, "user")
    assert client.get("/api/test/read/submit_request").status_code == 200
    assert client.get("/api/test/read/manage_users").status_code == 403
    with owner_engine.connect() as connection:
        rows = connection.execute(
            text("SELECT actor_id, target, detail FROM audit_log WHERE event_type = 'access_denied'")
        ).all()
    assert len(rows) == 1
    assert rows[0].actor_id is not None
    assert rows[0].target == "manage_users"
    assert rows[0].detail == "GET /api/test/read/manage_users"


def test_changes_need_the_handshake_word_as_well_as_the_permission(guarded, add_user):
    client = _signed_in(guarded(), add_user, "manager")
    token = client.get("/api/auth/me").json()["csrf_token"]

    no_token = client.post("/api/test/change/handle_requests")
    assert no_token.status_code == 403
    assert no_token.json() == {"detail": CSRF_MESSAGE}

    assert client.post("/api/test/change/handle_requests", headers={"X-CSRF-Token": token}).status_code == 200

    denied = client.post("/api/test/change/manage_users", headers={"X-CSRF-Token": token})
    assert denied.status_code == 403
    assert denied.json() == {"detail": DENIED_MESSAGE}


def test_a_changed_role_applies_to_the_very_next_request(guarded, add_user, owner_engine):
    client = _signed_in(guarded(), add_user, "user")
    path = "/api/test/read/manage_users"
    assert client.get(path).status_code == 403
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = 'admin'"))
    assert client.get(path).status_code == 200
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = 'user'"))
    assert client.get(path).status_code == 403


@pytest.mark.parametrize("role", ROLES)
def test_login_and_me_report_the_roles_permissions(make_db_app, add_user, role):
    email = f"{role}@farm-mail.org"
    add_user(email=email, role=role)
    client = TestClient(make_db_app())
    expected = sorted(permission.value for permission in permissions_for(role))
    login = client.post("/api/auth/login", json={"email": email, "password": LOGIN_PASSWORD})
    assert login.json()["permissions"] == expected
    assert client.get("/api/auth/me").json()["permissions"] == expected