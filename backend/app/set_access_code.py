"""Set or change the farm access code: python -m app.set_access_code"""
import sys

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .access_code import check_new_code, format_code, generate_code
from .config import DEFAULT_ENV_FILE, ConfigError, load_settings
from .database import make_engine
from .farm import set_access_code


def main() -> int:
    try:
        settings = load_settings(env_file=DEFAULT_ENV_FILE)
    except ConfigError as error:
        print(f"Configuration problem: {error}")
        return 2

    typed = input("Press Enter to generate a code, or type your own (10 to 32 letters or digits): ").strip()
    try:
        code = check_new_code(typed) if typed else generate_code()
    except ValueError as error:
        print(f"Not changed: {error}")
        return 1

    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session:
            stored = set_access_code(session, settings.secret_key, code)
    except SQLAlchemyError as error:
        reason = str(getattr(error, "orig", error)).splitlines()[0]
        print(f"Database problem: {type(error).__name__}: {reason}")
        return 1
    finally:
        engine.dispose()

    print(f"The farm access code is now: {format_code(stored)}")
    print("Share it only with people on the farm. Anyone who has it can create an account.")
    return 0


if __name__ == "__main__":
    sys.exit(main())