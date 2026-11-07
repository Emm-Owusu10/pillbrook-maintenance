"""The audit log: who did what, and when. Never put passwords or session codes in here."""
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
    rows = db.scalars(
        select(AuditLog.created_at)
        .where(AuditLog.event_type == LOGIN_FAILURE, AuditLog.target == email, AuditLog.created_at > since)
        .order_by(AuditLog.created_at.desc())
        .limit(MAX_FAILURES + 1)
    )
    return list(rows)