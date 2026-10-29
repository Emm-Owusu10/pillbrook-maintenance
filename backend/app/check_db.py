"""Check that the application can reach its database: python -m app.check_db"""
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import DEFAULT_ENV_FILE, ConfigError, load_settings
from .database import make_engine


def main() -> int:
    try:
        settings = load_settings(env_file=DEFAULT_ENV_FILE)
    except ConfigError as error:
        print(f"Configuration problem: {error}")
        return 2

    engine = make_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            account, database, version = connection.execute(
                text("SELECT current_user, current_database(), version()")
            ).one()
    except SQLAlchemyError as error:
        # First line of the driver's message only. It never contains the password.
        reason = str(getattr(error, "orig", error)).splitlines()[0]
        print(f"Could not connect: {type(error).__name__}: {reason}")
        return 1
    finally:
        engine.dispose()

    print(f"Connected as {account} to database {database}")
    print(version.split(",")[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())