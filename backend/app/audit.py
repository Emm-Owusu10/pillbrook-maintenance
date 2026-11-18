"""The audit log: who did what, and when. Never put passwords, codes or one-time links in here."""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AuditLog
from .throttle import FAILURE_WINDOW, MAX_FAILURES

LOGIN_SUCCESS = "login_success"
LOGIN_FAILURE = "login_failure"
LOGIN_LOCKED = "login_locked"
LOGOUT = "logout"
SESSION_EXPIRED = "session_expired"
ACCESS_DENIED = "access_denied"
REGISTRATION_SUCCESS = "registration_success"
REGISTRATION_CODE_FAILURE = "registration_code_failure"
REGISTRATION_PAUSED = "registration_paused"
EMAIL_VERIFIED = "email_verified"
VERIFICATION_REQUESTED = "verification_requested"
VERIFICATION_EMAIL_FAILED = "verification_email_failed"
ACCESS_CODE_CHANGED = "access_code_changed"
RESET_BY_ADMIN = "password_reset_by_admin"
RESET_BY_COMMAND = "password_reset_by_command"
RESET_REQUESTED = "password_reset_requested"
RESET_BY_LINK = "password_reset_by_link"
OWN_CHANGE = "password_changed"


def record(
    db: Session,
    event_type: str,
    *,
    actor_id: uuid.UUID | None = None,
    target: str | None = None,
    detail: str | None = None,
) -> None:
    """Add an entry. The caller commits, so the entry stands or falls with the action it describes."""
    db.add(AuditLog(event_type=event_type, actor_id=actor_id, target=target, detail=detail))


def recent_times(
    db: Session, event_type: str, since: datetime, *, target: str | None = None, limit: int = 50
) -> list[datetime]:
    """Times of recent events of one kind (newest first), optionally for one target only."""
    query = select(AuditLog.created_at).where(AuditLog.event_type == event_type, AuditLog.created_at > since)
    if target is not None:
        query = query.where(AuditLog.target == target)
    return list(db.scalars(query.order_by(AuditLog.created_at.desc()).limit(limit)))


def failures_since_last_success(db: Session, email: str, now: datetime) -> list[datetime]:
    """Times of recent wrong logins for this email, ignoring any before its last successful login."""
    since = now - FAILURE_WINDOW
    last_success = db.scalar(
        select(func.max(AuditLog.created_at)).where(
            AuditLog.event_type == LOGIN_SUCCESS, AuditLog.target == email, AuditLog.created_at > since
        )
    )
    if last_success is not None:
        since = last_success
    return recent_times(db, LOGIN_FAILURE, since, target=email, limit=MAX_FAILURES + 1)