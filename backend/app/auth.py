"""Login, logout and the signed-in user (requirements FR4, FR6, SR3, SR4)."""
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, sessions
from .access import CSRF_HEADER, CSRF_MESSAGE, Auth, require_signed_in
from .database import get_db
from .emails import normalise_email
from .models import User
from .passwords import hash_password, needs_rehash, verify_password
from .permissions import permissions_for
from .schemas import AuthOut, LoginIn, UserOut
from .throttle import LOCK_DURATION, is_locked, reaches_limit
from .tokens import csrf_matches, csrf_token_for

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_FAILURE = "Incorrect email or password."
LOCKED_MESSAGE = f"Too many failed attempts. Try again in {int(LOCK_DURATION.total_seconds() // 60)} minutes."


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    # Checked when the email is unknown, so a login takes about as long either way.
    return hash_password("a placeholder used only to spend the same time as a real check")


def _auth_reply(settings, user: User, raw_token: str) -> AuthOut:
    """Who the person is, what their role allows, and the handshake word for this session."""
    return AuthOut(
        user=UserOut.model_validate(user),
        permissions=sorted(permission.value for permission in permissions_for(user.role)),
        csrf_token=csrf_token_for(settings.secret_key, raw_token),
    )


def _set_session_cookie(response: Response, settings, raw: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw,
        max_age=int(sessions.ABSOLUTE_LIFETIME.total_seconds()),
        httponly=True,          # page scripts cannot read it
        secure=settings.cookie_secure,  # sent over HTTPS only (switched off in development)
        samesite="strict",      # never sent because of a link or form on another website
        path="/",
    )


def _clear_session_cookie(response: Response, settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)

    try:
        email = normalise_email(body.email)
    except ValueError:
        email = None  # not an email address: it can match no account and is never stored

    if email is not None and is_locked(audit.failures_since_last_success(db, email, now), now):
        raise HTTPException(
            status_code=429,
            detail=LOCKED_MESSAGE,
            headers={"Retry-After": str(int(LOCK_DURATION.total_seconds()))},
        )

    user = db.scalar(select(User).where(User.email == email)) if email is not None else None
    password_ok = verify_password(user.password_hash if user else _dummy_hash(), body.password)
    allowed = bool(user and password_ok and user.is_active and user.email_verified_at is not None)

    if not allowed:
        detail = None
        if user is not None and password_ok:
            detail = "inactive account" if not user.is_active else "email not verified"
        audit.record(db, audit.LOGIN_FAILURE, target=email, detail=detail)
        db.flush()
        if email is not None and reaches_limit(audit.failures_since_last_success(db, email, now), now):
            audit.record(db, audit.LOGIN_LOCKED, target=email)
        db.commit()
        raise HTTPException(status_code=401, detail=GENERIC_FAILURE)  # the same answer for every failure

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)  # upgrade to the current settings
    old_code = request.cookies.get(settings.session_cookie_name)
    if old_code:
        sessions.end_session(db, old_code)  # a new login never reuses an old session
    sessions.purge_expired(db)
    raw = sessions.start_session(db, user)
    audit.record(db, audit.LOGIN_SUCCESS, actor_id=user.user_id, target=email)
    db.commit()

    _set_session_cookie(response, settings, raw)
    return _auth_reply(settings, user, raw)


@router.get("/me", response_model=AuthOut)
def me(request: Request, auth: Auth = Depends(require_signed_in)):
    return _auth_reply(request.app.state.settings, auth.user, auth.raw_token)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = request.app.state.settings
    raw = request.cookies.get(settings.session_cookie_name)
    found = sessions.find_valid(db, raw) if raw else None
    if found is not None:
        _session, user = found
        if not csrf_matches(settings.secret_key, raw, request.headers.get(CSRF_HEADER)):
            raise HTTPException(status_code=403, detail=CSRF_MESSAGE)
        sessions.end_session(db, raw)
        audit.record(db, audit.LOGOUT, actor_id=user.user_id, target=user.email)
        db.commit()
    _clear_session_cookie(response, settings)  # harmless when nobody was signed in