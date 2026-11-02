"""Login, logout and the signed-in user (requirements FR4, FR6, SR3, SR4)."""
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, sessions
from .database import get_db
from .emails import normalise_email
from .models import User, UserSession
from .passwords import hash_password, needs_rehash, verify_password
from .schemas import AuthOut, LoginIn, UserOut
from .throttle import LOCK_DURATION, is_locked, reaches_limit
from .tokens import csrf_matches, csrf_token_for

router = APIRouter(prefix="/auth", tags=["auth"])

CSRF_HEADER = "X-CSRF-Token"
GENERIC_FAILURE = "Incorrect email or password."
LOCKED_MESSAGE = f"Too many failed attempts. Try again in {int(LOCK_DURATION.total_seconds() // 60)} minutes."


@dataclass
class Auth:
    user: User
    session: UserSession
    raw_token: str  # the session code from the cookie; used only to derive the CSRF token


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    # Checked when the email is unknown, so a login takes about as long either way.
    return hash_password("a placeholder used only to spend the same time as a real check")


def get_auth(request: Request, db: Session = Depends(get_db)) -> Auth:
    """For endpoints that only read: the caller must hold a live session."""
    raw = request.cookies.get(request.app.state.settings.session_cookie_name)
    found = sessions.find_valid(db, raw) if raw else None
    if found is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    session, user = found
    return Auth(user=user, session=session, raw_token=raw)


def get_auth_with_csrf(request: Request, auth: Auth = Depends(get_auth)) -> Auth:
    """For endpoints that change something: a live session AND the matching CSRF token."""
    supplied = request.headers.get(CSRF_HEADER)
    if not csrf_matches(request.app.state.settings.secret_key, auth.raw_token, supplied):
        raise HTTPException(status_code=403, detail="The request could not be verified. Reload the page and try again.")
    return auth


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
    return AuthOut(user=UserOut.model_validate(user), csrf_token=csrf_token_for(settings.secret_key, raw))


@router.get("/me", response_model=AuthOut)
def me(request: Request, auth: Auth = Depends(get_auth)):
    settings = request.app.state.settings
    return AuthOut(
        user=UserOut.model_validate(auth.user),
        csrf_token=csrf_token_for(settings.secret_key, auth.raw_token),
    )


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = request.app.state.settings
    raw = request.cookies.get(settings.session_cookie_name)
    found = sessions.find_valid(db, raw) if raw else None
    if found is not None:
        _session, user = found
        if not csrf_matches(settings.secret_key, raw, request.headers.get(CSRF_HEADER)):
            raise HTTPException(
                status_code=403, detail="The request could not be verified. Reload the page and try again."
            )
        sessions.end_session(db, raw)
        audit.record(db, audit.LOGOUT, actor_id=user.user_id, target=user.email)
        db.commit()
    _clear_session_cookie(response, settings)  # harmless when nobody was signed in