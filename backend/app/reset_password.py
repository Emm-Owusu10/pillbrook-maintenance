"""Give a person a one-time temporary password from the server: python -m app.reset_password

Use it when the Administrator cannot sign in, so that nobody can be locked out for good. It needs the
server's own credentials (the .env file), which is why it is safe to keep outside the website.
"""
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import account_security, audit
from .config import DEFAULT_ENV_FILE, ConfigError, load_settings
from .database import make_engine
from .emails import normalise_email
from .models import User


def main() -> int:
    try:
        settings = load_settings(env_file=DEFAULT_ENV_FILE)
    except ConfigError as error:
        print(f"Configuration problem: {error}")
        return 2

    typed = input("Email address of the account: ").strip()
    try:
        email = normalise_email(typed)
    except ValueError:
        print("That is not a valid email address.")
        return 1

    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session:
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                print("No account has that email address.")
                return 1
            temporary, expires_at = account_security.issue_temporary_password(session, user)
            audit.record(session, audit.RESET_BY_COMMAND, target=user.email)  # never the password
            session.commit()
            name = user.name
    except SQLAlchemyError as error:
        reason = str(getattr(error, "orig", error)).splitlines()[0]
        print(f"Database problem: {type(error).__name__}: {reason}")
        return 1
    finally:
        engine.dispose()

    print(f"Temporary password for {name}: {temporary}")
    print(f"It is valid until {expires_at:%Y-%m-%d %H:%M} UTC and must be replaced at the person's first sign-in.")
    print("Everything they were signed in to has ended. Give them the password in person and do not keep a copy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())