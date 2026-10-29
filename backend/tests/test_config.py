import pytest

from app.config import ConfigError, load_migration_settings, load_settings

APP_URL = "postgresql+psycopg://pillbrook_app:app-secret-pw@localhost:5432/pillbrook"
OWNER_URL = "postgresql+psycopg://pillbrook_owner:owner-secret-pw@localhost:5432/pillbrook"
GOOD = {"SECRET_KEY": "s" * 40, "ENVIRONMENT": "development", "DATABASE_URL": APP_URL}


def test_valid_settings_load():
    settings = load_settings(GOOD)
    assert settings.environment == "development"
    assert settings.is_development
    assert settings.database_url == APP_URL


def test_environment_defaults_to_production():
    settings = load_settings({"SECRET_KEY": "s" * 40, "DATABASE_URL": APP_URL})
    assert settings.environment == "production"
    assert not settings.is_development


def test_missing_secret_key_is_refused():
    with pytest.raises(ConfigError, match="SECRET_KEY is not set"):
        load_settings({})


def test_empty_secret_key_is_refused():
    with pytest.raises(ConfigError, match="SECRET_KEY is not set"):
        load_settings({"SECRET_KEY": ""})


def test_short_secret_key_is_refused():
    with pytest.raises(ConfigError, match="at least 32"):
        load_settings({"SECRET_KEY": "too-short"})


def test_error_message_never_contains_the_secret():
    secret = "short-but-secret"
    with pytest.raises(ConfigError) as error:
        load_settings({"SECRET_KEY": secret})
    assert secret not in str(error.value)


def test_invalid_environment_is_refused():
    with pytest.raises(ConfigError, match="ENVIRONMENT"):
        load_settings({**GOOD, "ENVIRONMENT": "staging"})


def test_wildcard_cors_origin_is_refused():
    with pytest.raises(ConfigError, match="CORS_ORIGINS"):
        load_settings({**GOOD, "CORS_ORIGINS": "*"})


def test_cors_origin_with_trailing_slash_is_refused():
    with pytest.raises(ConfigError, match="CORS_ORIGINS"):
        load_settings({**GOOD, "CORS_ORIGINS": "http://localhost:5173/"})


def test_cors_origin_without_scheme_is_refused():
    with pytest.raises(ConfigError, match="CORS_ORIGINS"):
        load_settings({**GOOD, "CORS_ORIGINS": "localhost:5173"})


def test_http_cors_origin_is_refused_in_production():
    with pytest.raises(ConfigError, match="https"):
        load_settings({**GOOD, "ENVIRONMENT": "production", "CORS_ORIGINS": "http://example.org"})


def test_cors_origins_are_parsed_into_a_tuple():
    settings = load_settings({**GOOD, "CORS_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173"})
    assert settings.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_repr_hides_the_secret_key_and_database_password():
    text = repr(load_settings(GOOD))
    assert GOOD["SECRET_KEY"] not in text
    assert "app-secret-pw" not in text


def test_env_file_is_read(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n\nSECRET_KEY=" + "a" * 40 + "\nENVIRONMENT=development\n"
        "CORS_ORIGINS='http://localhost:5173'\nDATABASE_URL=" + APP_URL + "\n",
        encoding="utf-8",
    )
    settings = load_settings({}, env_file=env_file)
    assert settings.secret_key == "a" * 40
    assert settings.cors_origins == ("http://localhost:5173",)
    assert settings.database_url == APP_URL


def test_real_environment_overrides_the_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SECRET_KEY=" + "a" * 40 + "\nENVIRONMENT=development\nDATABASE_URL=" + APP_URL + "\n",
        encoding="utf-8",
    )
    settings = load_settings({"ENVIRONMENT": "production"}, env_file=env_file)
    assert settings.environment == "production"


def test_malformed_env_file_line_is_refused_without_echoing_it(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("this-line-looks-like-a-secret\n", encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        load_settings({}, env_file=env_file)
    assert "this-line-looks-like-a-secret" not in str(error.value)


def test_missing_database_url_is_refused():
    with pytest.raises(ConfigError, match="DATABASE_URL is not set"):
        load_settings({"SECRET_KEY": "s" * 40})


def test_database_url_must_use_the_psycopg_driver():
    with pytest.raises(ConfigError, match="DATABASE_URL must look like"):
        load_settings({**GOOD, "DATABASE_URL": "sqlite:///local.db"})


def test_database_url_without_a_password_is_refused():
    with pytest.raises(ConfigError, match="DATABASE_URL must look like"):
        load_settings({**GOOD, "DATABASE_URL": "postgresql+psycopg://pillbrook_app@localhost/pillbrook"})


def test_database_url_must_not_use_the_superuser():
    with pytest.raises(ConfigError, match="superuser"):
        load_settings({**GOOD, "DATABASE_URL": "postgresql+psycopg://postgres:pw@localhost:5432/pillbrook"})


def test_database_account_with_odd_characters_is_refused():
    with pytest.raises(ConfigError, match="letters, digits and underscores"):
        load_settings({**GOOD, "DATABASE_URL": "postgresql+psycopg://bad%20name:pw@localhost/pillbrook"})


def test_database_error_messages_never_contain_the_password():
    password = "hunter-two-secret"
    with pytest.raises(ConfigError) as error:
        load_settings({**GOOD, "DATABASE_URL": f"mysql://someone:{password}@localhost/db"})
    assert password not in str(error.value)


def test_migration_url_must_use_a_different_account():
    with pytest.raises(ConfigError, match="different accounts"):
        load_settings({**GOOD, "MIGRATION_DATABASE_URL": APP_URL})


def test_running_application_does_not_keep_the_owner_password():
    settings = load_settings({**GOOD, "MIGRATION_DATABASE_URL": OWNER_URL})
    assert "owner-secret-pw" not in str(vars(settings))


def test_migration_settings_return_the_url_and_the_app_account():
    env = {"DATABASE_URL": APP_URL, "MIGRATION_DATABASE_URL": OWNER_URL}
    assert load_migration_settings(env) == (OWNER_URL, "pillbrook_app")


def test_migration_settings_require_both_urls():
    with pytest.raises(ConfigError, match="MIGRATION_DATABASE_URL is not set"):
        load_migration_settings({"DATABASE_URL": APP_URL})
    with pytest.raises(ConfigError, match="DATABASE_URL is not set"):
        load_migration_settings({"MIGRATION_DATABASE_URL": OWNER_URL})


def test_migration_settings_refuse_the_same_account_twice():
    with pytest.raises(ConfigError, match="different accounts"):
        load_migration_settings({"DATABASE_URL": APP_URL, "MIGRATION_DATABASE_URL": APP_URL})