import pytest

from app.config import ConfigError, load_settings

APP_URL = "postgresql+psycopg://pillbrook_app:app-secret-pw@localhost:5432/pillbrook"
GOOD = {"SECRET_KEY": "s" * 40, "ENVIRONMENT": "development", "DATABASE_URL": APP_URL}


def test_the_public_address_has_a_development_default():
    assert load_settings(GOOD).public_base_url == "http://127.0.0.1:5173"


def test_the_public_address_must_be_exact():
    for bad in ("pbafish.com", "https://pbafish.com/", "ftp://pbafish.com"):
        with pytest.raises(ConfigError, match="PUBLIC_BASE_URL"):
            load_settings({**GOOD, "PUBLIC_BASE_URL": bad})


def test_a_proper_public_address_is_accepted():
    settings = load_settings({**GOOD, "PUBLIC_BASE_URL": "https://app.pbafish.com"})
    assert settings.public_base_url == "https://app.pbafish.com"


def test_development_may_use_a_plain_http_address_even_when_verification_is_required():
    settings = load_settings({**GOOD, "MAIL_MODE": "outbox", "REQUIRE_EMAIL_VERIFICATION": "true"})
    assert settings.public_base_url.startswith("http://")