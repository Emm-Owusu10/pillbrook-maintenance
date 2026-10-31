"""Create the first Administrator: python -m app.create_admin"""
import sys
from datetime import datetime, timezone
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .config import DEFAULT_ENV_FILE, ConfigError, load_settings
from .database import make_engine
from .emails import normalise_email
from .models import User
from .passwords import check_policy, hash_password


class SetupError(ValueError):
    """The Administrator cannot be created. The message is safe to show."""


def administrator_exists(session: Session) -> bool:
    return session.scalar(select(User.user_id).where(User.role == "admin").limit(1)) is not None


def create_first_admin(session: Session, name: str, email: str, password: str) -> User:
    if administrator_exists(session):
        raise SetupError("An Administrator already exists.")

    name = name.strip()
    if not 1 <= len(name) <= 100:
        raise SetupError("The name must be 1 to 100 characters.")
    try:
        email = normalise_email(email)
    except ValueError as error:
        raise SetupError(str(error)) from None
    problems = check_policy(password, name=name, email=email)
    if problems:
        raise SetupError(" ".join(problems))

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        email_verified_at=datetime.now(timezone.utc),  # no email is sent for this account
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise SetupError("That email address is already registered.") from None
    return user


def main() -> int:
    try:
        settings = load_settings(env_file=DEFAULT_ENV_FILE)
    except ConfigError as error:
        print(f"Configuration problem: {error}")
        return 2

    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session:
            if administrator_exists(session):
                print("An Administrator already exists. Add more through user management.")
                return 1
            print("Creating the first Administrator. The password is not shown while you type.")
            name = input("Full name: ")
            email = input("Email address: ")
            password = getpass("Password: ")
            if getpass("Repeat the password: ") != password:
                print("The passwords do not match. Nothing was created.")
                return 1
            try:
                user = create_first_admin(session, name, email, password)
            except SetupError as error:
                print(f"Not created: {error}")
                return 1
            print(f"Administrator created: {user.email}")
    except SQLAlchemyError as error:
        reason = str(getattr(error, "orig", error)).splitlines()[0]
        print(f"Database problem: {type(error).__name__}: {reason}")
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())