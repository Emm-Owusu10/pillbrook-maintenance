import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.access import MUST_CHANGE_MESSAGE, require_permission
from app.permissions import Permission
from tests.conftest import LOGIN_PASSWORD


def _ok():
    return {"ok": True}


@pytest.fixture()
def guarded(make_db_app):
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


@pytest.fixture()
def must_change(guarded, add_user, owner_engine):
    """An Administrator who signed in with a temporary password and has not yet replaced it."""
    add_user(email="admin@farm-mail.org", role="admin")
    client = TestClient(guarded())
    assert client.post("/api/auth/login", json={"email": "admin@farm-mail.org", "password": LOGIN_PASSWORD}).status_code == 200
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET must_change_password = true, temporary_password_expires_at = now() + interval '1 hour'")
        )
    return client


def test_every_function_is_refused_until_a_new_password_is_chosen(must_change):
    token = must_change.get("/api/auth/me").json()["csrf_token"]
    for permission in Permission:
        read = must_change.get(f"/api/test/read/{permission.value}")
        assert (read.status_code, read.json()) == (403, {"detail": MUST_CHANGE_MESSAGE}), permission.value
        change = must_change.post(f"/api/test/change/{permission.value}", headers={"X-CSRF-Token": token})
        assert (change.status_code, change.json()) == (403, {"detail": MUST_CHANGE_MESSAGE}), permission.value


def test_the_person_can_still_see_who_they_are_and_that_a_new_password_is_needed(must_change):
    response = must_change.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_the_person_can_still_sign_out(must_change):
    token = must_change.get("/api/auth/me").json()["csrf_token"]
    assert must_change.post("/api/auth/logout", headers={"X-CSRF-Token": token}).status_code == 204
    assert must_change.get("/api/auth/me").status_code == 401