"""Sessions kept in the database (decision D36): a random code in the cookie, a fingerprint in the table."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import audit
from .models import User, UserSession
from .tokens import hash_token, new_session_token

IDLE_TIMEOUT = timedelta(minutes=60)      # signed out after this long without activity
ABSOLUTE_LIFETIME = timedelta(hours=12)   # signed out after this long whatever happens
TOUCH_INTERVAL = timedelta(minutes=1)     # activity is recorded at most this often


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_session(db: Session, user: User) -> str:
    """Create a session and return its secret code for the cookie. The caller commits."""
    raw = new_session_token()
    now = _now()
    db.add(
        UserSession(
            user_id=user.user_id,
            token_hash=hash_token(raw),
            created_at=now,
            last_seen_at=now,
            expires_at=now + ABSOLUTE_LIFETIME,
        )
    )
    return raw


def end_session(db: Session, raw_token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(raw_token)))


def end_all_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))


def purge_expired(db: Session) -> None:
    now = _now()
    db.execute(
        delete(UserSession).where(
            (UserSession.expires_at < now) | (UserSession.last_seen_at < now - IDLE_TIMEOUT)
        )
    )


def find_valid(db: Session, raw_token: str) -> tuple[UserSession, User] | None:
    """Return the live session and its user, or None.

    A session that has run out is removed and logged. A session whose user has been deactivated
    is removed at once.
    """
    now = _now()
    row = db.execute(
        select(UserSession, User)
        .join(User, User.user_id == UserSession.user_id)
        .where(UserSession.token_hash == hash_token(raw_token))
    ).first()
    if row is None:
        return None
    session, user = row

    if session.expires_at <= now or session.last_seen_at <= now - IDLE_TIMEOUT:
        db.delete(session)
        audit.record(db, audit.SESSION_EXPIRED, actor_id=user.user_id)
        db.commit()
        return None
    if not user.is_active:
        db.delete(session)
        db.commit()
        return None
    if now - session.last_seen_at >= TOUCH_INTERVAL:
        session.last_seen_at = now
        db.commit()
    return session, user