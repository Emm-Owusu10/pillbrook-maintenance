import re

from fastapi.testclient import TestClient

from app.permissions import PUBLIC_ROUTES

DUMMY_ID = "00000000-0000-0000-0000-000000000000"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _advertised(app):
    """Every (METHOD, address) the application lists in its own public description of itself."""
    found = []
    for template, operations in app.openapi()["paths"].items():
        for method in operations:
            if method in HTTP_METHODS:
                found.append((method.upper(), template))
    return found


def _unprotected(app):
    """Routes that are not on the open list and still answer someone who is not signed in."""
    client = TestClient(app, raise_server_exceptions=False)
    problems = []
    for method, template in _advertised(app):
        if (method, template) in PUBLIC_ROUTES:
            continue
        concrete = re.sub(r"\{[^}]+\}", DUMMY_ID, template)
        status = client.request(method, concrete).status_code
        if status != 401:
            problems.append(f"{method} {template} answered {status} instead of 401")
    return problems


def _open_route():
    return {"open": True}


def test_the_check_can_see_the_routes(make_db_app):
    names = set(_advertised(make_db_app()))
    assert {
        ("GET", "/api/health"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/auth/me"),
    } <= names


def test_every_route_that_is_not_open_turns_away_a_visitor_who_is_not_signed_in(make_db_app):
    assert _unprotected(make_db_app()) == []


def test_the_check_notices_a_route_that_was_added_without_a_guard(make_db_app):
    app = make_db_app()
    app.add_api_route("/api/test/forgotten", _open_route, methods=["GET"])
    problems = _unprotected(app)
    assert len(problems) == 1
    assert problems[0].startswith("GET /api/test/forgotten")


def test_the_list_of_open_routes_has_no_stale_entries(make_db_app):
    assert set(PUBLIC_ROUTES) <= set(_advertised(make_db_app()))