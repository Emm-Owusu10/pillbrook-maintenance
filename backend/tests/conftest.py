from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import passwords
from app.config import DEFAULT_ENV_FILE, Settings, merged_environment
from app.main import create_app

TEST_KEY = "k" * 40  # test-only value
BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture()
def make_app():
    def _make(**overrides):
        values = {"environment": "development", "secret_key": TEST_KEY, "cors_origins": ()}
        values.update(overrides)
        return create_app(Settings(**values))

    return _make


@pytest.fixture()
def client(make_app):
    return TestClient(make_app(), raise_server_exceptions=False)


@pytest.fixture()
def small_list(tmp_path, monkeypatch):
    """A tiny common-password list, so the password tests do not depend on the downloaded file."""
    path = tmp_path / "common.txt"
    path.write_text("password\niloveyou\nQwerty123456789\nabc\n\n  spaced  \n", encoding="utf-8")
    monkeypatch.setattr(passwords, "BLOCKLIST_FILE", path)
    passwords._common_passwords.cache_clear()
    yield
    passwords._common_passwords.cache_clear()


# ---- Database fixtures (need PostgreSQL and the *_test database from the README) ----

def _test_database_url(name: str) -> str:
    value = merged_environment(env_file=DEFAULT_ENV_FILE).get(name, "")
    if not value:
        pytest.fail(f"{name} is not set. Add it to .env (see .env.example).", pytrace=False)
    # These tests run migrations up and down, so they must never touch the real database.
    if not urlsplit(value).path.lstrip("/").endswith("_test"):
        pytest.fail(f"{name} must point at a database whose name ends in _test.", pytrace=False)
    return value


@pytest.fixture(scope="session")
def owner_engine():
    engine = create_engine(_test_database_url("TEST_MIGRATION_DATABASE_URL"), pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app_engine():
    engine = create_engine(_test_database_url("TEST_DATABASE_URL"), pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def alembic_config():
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["migration_url"] = _test_database_url("TEST_MIGRATION_DATABASE_URL")
    app_url = _test_database_url("TEST_DATABASE_URL")
    config.attributes["app_role"] = unquote(urlsplit(app_url).username)
    return config


def _drop_probe_table(engine):
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS probe_table"))


@pytest.fixture()
def migrated(alembic_config, owner_engine):
    """Apply all migrations before the test and undo them afterwards."""
    _drop_probe_table(owner_engine)
    command.upgrade(alembic_config, "head")
    yield
    _drop_probe_table(owner_engine)
    command.downgrade(alembic_config, "base")