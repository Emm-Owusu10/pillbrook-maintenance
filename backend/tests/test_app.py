from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


def test_health_returns_ok_and_nothing_else(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_unexpected_error_returns_a_generic_500(make_app):
    app = make_app()

    @app.get("/boom")
    def boom():
        raise RuntimeError("database password is hunter2")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text


def test_validation_errors_do_not_echo_submitted_values(make_app):
    app = make_app()

    class Login(BaseModel):
        email: str
        password: str = Field(min_length=15)

    @app.post("/echo-test")
    def echo_test(body: Login):
        return {}

    response = TestClient(app, raise_server_exceptions=False).post(
        "/echo-test", json={"email": "a@example.org", "password": "short-secret"}
    )
    assert response.status_code == 422
    assert "short-secret" not in response.text
    assert response.json()["detail"][0]["field"] == "password"


def test_api_docs_are_available_in_development(make_app):
    client = TestClient(make_app(environment="development"))
    assert client.get("/docs").status_code == 200


def test_api_docs_are_hidden_in_production(make_app):
    client = TestClient(make_app(environment="production"))
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cors_allows_a_configured_origin(make_app):
    origin = "http://localhost:5173"
    client = TestClient(make_app(cors_origins=(origin,)))
    response = client.get("/health", headers={"Origin": origin})
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_refuses_an_unlisted_origin(make_app):
    client = TestClient(make_app(cors_origins=("http://localhost:5173",)))
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_no_cors_headers_when_no_origin_is_configured(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in response.headers