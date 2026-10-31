"""Alembic environment: how migrations connect and what they compare against."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import DEFAULT_ENV_FILE, load_migration_settings
from app.database import Base

from app import models  # noqa: F401  (registers the tables)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# The tests pass the connection details in directly; the command line reads them from .env.
migration_url = config.attributes.get("migration_url")
if migration_url is None:
    migration_url, app_account = load_migration_settings(env_file=DEFAULT_ENV_FILE)
    config.attributes["app_role"] = app_account

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(migration_url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()