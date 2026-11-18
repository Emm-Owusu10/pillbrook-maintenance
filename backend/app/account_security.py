"""Password changes and resets, shared by the Administrator's reset, the server command and the screens."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from . import auth_tokens
from .models import AuthToken, User, UserSession
from .passwords import hash_password
from .temp_password import generate_temporary_password

TEMPORARY_PASSWORD_LIFETIME = timedelta(hours=24)


def end_sessions(db: Session, user_id: uuid.UUID, keep_session_id: uuid.UUID | None = None) -> None:
    """Sign a person out everywhere, except (optionally) the browser that is making the change."""
    statement = delete(UserSession).where(UserSession.user_id == user_id)
    if keep_session_id is not None:
        statement = statement.where(UserSession.session_id != keep_session_id)
    db.execute(statement)


def cancel_reset_links(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        delete(AuthToken).where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == auth_tokens.RESET_PASSWORD,
            AuthToken.used_at.is_(None),
        )
    )


def issue_temporary_password(db: Session, user: User) -> tuple[str, datetime]:
    """Give a person a one-time password they must change at first sign-in. The caller commits.

    Everything they are signed in to ends now, and any reset link already emailed stops working.
    """
    temporary = generate_temporary_password()
    expires_at = datetime.now(timezone.utc) + TEMPORARY_PASSWORD_LIFETIME
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    user.temporary_password_expires_at = expires_at
    end_sessions(db, user.user_id)
    cancel_reset_links(db, user.user_id)
    return temporary, expires_at


def set_chosen_password(
    db: Session, user: User, new_password: str, keep_session_id: uuid.UUID | None = None
) -> None:
    """Store a password the person chose. Other sign-ins and old reset links stop working. The caller commits."""
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.temporary_password_expires_at = None
    end_sessions(db, user.user_id, keep_session_id)
    cancel_reset_links(db, user.user_id)