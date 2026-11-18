"""One-time links for confirming an email address or resetting a password (requirement SR9).

The link holds a random code; the database holds only its fingerprint, so a leaked database holds
nothing usable. A token works once and expires.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .models import AuthToken
from .tokens import hash_token, new_session_token

VERIFY_EMAIL = "verify_email"
# A label for the kind of one-time link, not a password (bandit's B105 reacts to the word).
RESET_PASSWORD = "reset_password"  # nosec B105
VERIFICATION_LIFETIME = timedelta(hours=24)
RESET_LIFETIME = timedelta(hours=1)


def issue(db: Session, user_id: uuid.UUID, purpose: str, lifetime: timedelta) -> str:
    """Create a token and return its secret code. Older unused tokens of the same kind stop working.

    The caller commits.
    """
    db.execute(
        delete(AuthToken).where(
            AuthToken.user_id == user_id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None)
        )
    )
    raw = new_session_token()  # 256 random bits
    db.add(
        AuthToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + lifetime,
        )
    )
    return raw


def peek(db: Session, raw_token: str, purpose: str) -> uuid.UUID | None:
    """Whose token this is, if it is still usable, without using it up."""
    return db.scalar(
        select(AuthToken.user_id).where(
            AuthToken.token_hash == hash_token(raw_token),
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > datetime.now(timezone.utc),
        )
    )


def consume(db: Session, raw_token: str, purpose: str) -> uuid.UUID | None:
    """Use a token once. Returns the user's id, or None if it is unknown, used, expired or for another purpose.

    One database statement checks and marks the token together, so two requests can never both use it.
    The caller commits.
    """
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(AuthToken)
        .where(
            AuthToken.token_hash == hash_token(raw_token),
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(AuthToken.user_id)
    )
    return result.scalar_one_or_none()