import pytest

from app.config import ConfigError, load_settings

APP_URL = "postgresql+psycopg://pillbrook_app:app-secret-pw@localhost:5432/pillbrook"
GOOD = {"SECRET_KEY": "s" * 40, "ENVIRONMENT": "development", "DATABASE_URL": APP_URL}


def test_email_is_off_unless_it_is_turned_on():
    settings = load_settings(GOOD)
    assert settings.mail_mode == "off"
    assert settings.require_email_verification is False


def test_outbox_mode_is_accepted_in_development():
    assert load_settings({**GOOD, "MAIL_MODE": "outbox"}).mail_mode == "outbox"


def test_outbox_mode_is_refused_in_production():
    with pytest.raises(ConfigError, match="development only"):
        load_settings({**GOOD, "ENVIRONMENT": "production", "MAIL_MODE": "outbox"})


def test_production_may_run_with_email_off():
    settings = load_settings({**GOOD, "ENVIRONMENT": "production", "MAIL_MODE": "off"})
    assert settings.mail_mode == "off"


def test_the_real_mail_provider_is_not_available_yet():
    with pytest.raises(ConfigError, match="not available yet"):
        load_settings({**GOOD, "MAIL_MODE": "provider"})


def test_an_unknown_mail_mode_is_refused():
    with pytest.raises(ConfigError, match="MAIL_MODE must be"):
        load_settings({**GOOD, "MAIL_MODE": "smtp"})


def test_verification_can_be_required_when_email_is_on():
    settings = load_settings({**GOOD, "MAIL_MODE": "outbox", "REQUIRE_EMAIL_VERIFICATION": "True"})
    assert settings.require_email_verification is True


def test_verification_cannot_be_required_when_email_is_off():
    with pytest.raises(ConfigError, match="needs email to be turned on"):
        load_settings({**GOOD, "REQUIRE_EMAIL_VERIFICATION": "true"})


def test_the_verification_setting_must_be_true_or_false():
    with pytest.raises(ConfigError, match="'true' or 'false'"):
        load_settings({**GOOD, "MAIL_MODE": "outbox", "REQUIRE_EMAIL_VERIFICATION": "maybe"})