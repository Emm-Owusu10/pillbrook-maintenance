"""Application settings, read once at startup from environment variables.

Rules enforced here (fail fast, fail safe):
- A missing or weak SECRET_KEY stops the application from starting.
- ENVIRONMENT defaults to "production", so a forgotten setting never turns on development features.
- CORS origins must be exact; "*" is rejected.
- The application's database account must exist, must not be the "postgres" superuser, and must
  differ from the account used for migrations.
- Error messages name the setting that is wrong but never print its value (database URLs hold passwords).
"""
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlsplit

DEFAULT_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
MIN_SECRET_LENGTH = 32
VALID_ENVIRONMENTS = ("development", "production")
DATABASE_SCHEME = "postgresql+psycopg"
_ACCOUNT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}")


class ConfigError(RuntimeError):
    """Configuration is missing or unsafe. The message never contains a secret value."""


@dataclass(frozen=True)
class Settings:
    environment: str
    secret_key: str = field(repr=False)  # repr=False keeps secrets out of logs and tracebacks
    cors_origins: tuple[str, ...] = ()
    database_url: str | None = field(default=None, repr=False)

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


def _read_env_file(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE lines. Blank lines and lines starting with # are ignored."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            # Report the line number only: the line itself might be a secret.
            raise ConfigError(f"{path.name} line {number} is not in KEY=VALUE form")
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def merged_environment(
    environ: Mapping[str, str] | None = None, env_file: Path | None = None
) -> dict[str, str]:
    """The .env file first, then real environment variables on top (they win)."""
    env: dict[str, str] = _read_env_file(env_file) if env_file else {}
    env.update(os.environ if environ is None else environ)
    return env


def _check_database_url(name: str, url: str) -> str:
    """Validate a database URL and return its account name. Never echoes the URL."""
    try:
        parts = urlsplit(url)
        account = unquote(parts.username or "")
        password = parts.password
        host = parts.hostname
        database = parts.path.lstrip("/")
    except ValueError:
        raise ConfigError(f"{name} is not a valid URL") from None
    if parts.scheme != DATABASE_SCHEME or not (host and database and account and password):
        raise ConfigError(
            f"{name} must look like {DATABASE_SCHEME}://account:password@host:port/database"
        )
    if not _ACCOUNT_NAME.fullmatch(account):
        raise ConfigError(f"{name} account name may use only letters, digits and underscores")
    if account.lower() == "postgres":
        raise ConfigError(f"{name} must not use the 'postgres' superuser account")
    return account


def load_settings(
    environ: Mapping[str, str] | None = None, env_file: Path | None = None
) -> Settings:
    """Build validated settings for the running application."""
    env = merged_environment(environ, env_file)

    environment = env.get("ENVIRONMENT", "production").strip().lower()
    if environment not in VALID_ENVIRONMENTS:
        raise ConfigError("ENVIRONMENT must be 'development' or 'production'")

    secret_key = env.get("SECRET_KEY", "")
    if not secret_key:
        raise ConfigError("SECRET_KEY is not set. Copy .env.example to .env and set it.")
    if len(secret_key) < MIN_SECRET_LENGTH:
        raise ConfigError(f"SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters long")

    origins = tuple(o.strip() for o in env.get("CORS_ORIGINS", "").split(",") if o.strip())
    for origin in origins:
        if origin == "*" or not origin.startswith(("http://", "https://")) or origin.endswith("/"):
            raise ConfigError(
                "CORS_ORIGINS must list exact origins such as http://localhost:5173 "
                "(no '*', no trailing slash)"
            )
    if environment == "production" and any(o.startswith("http://") for o in origins):
        raise ConfigError("CORS_ORIGINS must use https:// in production")

    database_url = env.get("DATABASE_URL", "")
    if not database_url:
        raise ConfigError("DATABASE_URL is not set. Copy .env.example to .env and set it.")
    app_account = _check_database_url("DATABASE_URL", database_url)

    # If the migration URL is present (development), check it, but never keep it: the running
    # application should not hold the schema owner's password.
    migration_url = env.get("MIGRATION_DATABASE_URL", "")
    if migration_url and _check_database_url("MIGRATION_DATABASE_URL", migration_url) == app_account:
        raise ConfigError("MIGRATION_DATABASE_URL and DATABASE_URL must use different accounts")

    return Settings(
        environment=environment,
        secret_key=secret_key,
        cors_origins=origins,
        database_url=database_url,
    )


def load_migration_settings(
    environ: Mapping[str, str] | None = None, env_file: Path | None = None
) -> tuple[str, str]:
    """For Alembic only: return (migration URL, name of the application's database account)."""
    env = merged_environment(environ, env_file)
    migration_url = env.get("MIGRATION_DATABASE_URL", "")
    database_url = env.get("DATABASE_URL", "")
    if not migration_url:
        raise ConfigError("MIGRATION_DATABASE_URL is not set. Copy .env.example to .env and set it.")
    if not database_url:
        raise ConfigError("DATABASE_URL is not set. Copy .env.example to .env and set it.")
    owner_account = _check_database_url("MIGRATION_DATABASE_URL", migration_url)
    app_account = _check_database_url("DATABASE_URL", database_url)
    if owner_account == app_account:
        raise ConfigError("MIGRATION_DATABASE_URL and DATABASE_URL must use different accounts")
    return migration_url, app_account