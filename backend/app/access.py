"""Who may do what: the guards every protected function must use (requirements FR5, SR5).

Every address under /api that is not listed in permissions.PUBLIC_ROUTES must depend on one of the
guards below. A test sends a request with no sign-in to every address the application advertises
and fails unless each one answers 401.
"""
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import audit, sessions
from .database import get_db
from .models import User, UserSession
from .permissions import Permission, has_permission
from .tokens import csrf_matches

CSRF_HEADER = "X-CSRF-Token"
DENIED_MESSAGE = "You do not have permission to do this."
CSRF_MESSAGE = "The request could not be verified. Reload the page and try again."


@dataclass
class Auth:
    user: User
    session: UserSession
    raw_token: str  # the session code from the cookie; used only to derive the CSRF token


def get_auth(request: Request, db: Session = Depends(get_db)) -> Auth:
    """The caller must hold a live session. The role is read from the database on every request."""
    raw = request.cookies.get(request.app.state.settings.session_cookie_name)
    found = sessions.find_valid(db, raw) if raw else None
    if found is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    session, user = found
    return Auth(user=user, session=session, raw_token=raw)


def get_auth_with_csrf(request: Request, auth: Auth = Depends(get_auth)) -> Auth:
    """A live session AND the matching CSRF token, for anything that changes data."""
    supplied = request.headers.get(CSRF_HEADER)
    if not csrf_matches(request.app.state.settings.secret_key, auth.raw_token, supplied):
        raise HTTPException(status_code=403, detail=CSRF_MESSAGE)
    return auth


def require_signed_in(auth: Auth = Depends(get_auth)) -> Auth:
    """For functions every signed-in person may use, whatever their role."""
    return auth


def require_permission(permission: Permission, *, changes_data: bool = False) -> Callable[..., Auth]:
    """A guard for one function. Use changes_data=True for anything that is not a plain read."""
    authenticate = get_auth_with_csrf if changes_data else get_auth

    def guard(
        request: Request,
        auth: Auth = Depends(authenticate),
        db: Session = Depends(get_db),
    ) -> Auth:
        if not has_permission(auth.user.role, permission):
            # Recorded so that repeated attempts show up. The reply never says what was needed.
            audit.record(
                db,
                audit.ACCESS_DENIED,
                actor_id=auth.user.user_id,
                target=permission.value,
                detail=f"{request.method} {request.url.path}"[:255],
            )
            db.commit()
            raise HTTPException(status_code=403, detail=DENIED_MESSAGE)
        return auth

    return guard