"""Registration and email verification (requirements FR1 to FR3, SR8, SR9)."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import audit, auth_tokens, farm
from .access_code import codes_match
from .database import get_db
from .emails import normalise_email
from .mailer import EmailMessage, Mailer, MailerError
from .models import User
from .passwords import check_policy, hash_password
from .schemas import MessageOut, RegisterIn, RegisterOut, ResendIn, VerifiedOut, VerifyIn
from .throttle import (
    CODE_PAUSE,
    CODE_WINDOW,
    MAX_WRONG_CODES,
    RESEND_LIMIT,
    RESEND_WINDOW,
    code_limit_reached,
    may_send_verification,
    registration_paused,
)

logger = logging.getLogger("pillbrook.registration")
router = APIRouter(prefix="/auth", tags=["registration"])

CLOSED_MESSAGE = "Registration is not open yet. Ask the Administrator."
WRONG_CODE_MESSAGE = "The farm access code is not correct."
PAUSED_MESSAGE = f"Registration is paused for a few minutes. Try again in {int(CODE_PAUSE.total_seconds() // 60)} minutes."
DUPLICATE_MESSAGE = "An account with this email address already exists."
INVALID_LINK_MESSAGE = "This link is not valid or has expired."
RESEND_MESSAGE = "If that address still needs confirming, a new email is on its way."


def _problem(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def _verification_message(settings, name: str, email: str, raw_token: str) -> EmailMessage:
    # The code sits after a "#", which browsers never send to any server, so it stays out of server logs.
    link = f"{settings.public_base_url}/verify-email#token={raw_token}"
    hours = int(auth_tokens.VERIFICATION_LIFETIME.total_seconds() // 3600)
    text = (
        f"Hello {name},\n\n"
        "Someone, hopefully you, created an account at Pill Brook Facility Maintenance with this email address.\n"
        f"To confirm it, open this link within {hours} hours:\n\n{link}\n\n"
        "If you did not create an account, you can ignore this message.\n"
    )
    return EmailMessage(to=email, subject="Confirm your email address", text=text)


def _deliver(mailer: Mailer, message: EmailMessage) -> None:
    """Runs after the reply has been sent, so a visitor cannot tell from the speed whether an email was sent."""
    try:
        mailer.send(message)
    except MailerError:
        logger.warning("A verification email could not be sent")


@router.post("/register", response_model=RegisterOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    settings = request.app.state.settings
    mailer = request.app.state.mailer
    now = datetime.now(timezone.utc)

    # 1. Too many wrong codes recently: registration is paused for everyone.
    wrong_codes = audit.recent_times(
        db, audit.REGISTRATION_CODE_FAILURE, now - CODE_WINDOW, limit=MAX_WRONG_CODES + 1
    )
    if registration_paused(wrong_codes, now):
        raise HTTPException(
            status_code=429,
            detail=PAUSED_MESSAGE,
            headers={"Retry-After": str(int(CODE_PAUSE.total_seconds()))},
        )

    # 2. The farm access code comes before anything else, so a visitor without it learns nothing.
    stored_code = farm.get_access_code(db, settings.secret_key)
    if stored_code is None:
        raise HTTPException(status_code=403, detail=CLOSED_MESSAGE)
    if not codes_match(stored_code, body.access_code):
        audit.record(db, audit.REGISTRATION_CODE_FAILURE)  # the wrong code itself is never recorded
        db.flush()
        wrong_codes = audit.recent_times(
            db, audit.REGISTRATION_CODE_FAILURE, now - CODE_WINDOW, limit=MAX_WRONG_CODES + 1
        )
        if code_limit_reached(wrong_codes, now):
            audit.record(db, audit.REGISTRATION_PAUSED)
        db.commit()
        raise HTTPException(status_code=403, detail=WRONG_CODE_MESSAGE)

    # 3. The details, with every problem reported at once.
    name = body.name.strip()
    problems = []
    if not 1 <= len(name) <= 100 or any(ord(ch) < 32 for ch in name):
        problems.append(_problem("name", "Enter your name (1 to 100 characters)."))
    try:
        email = normalise_email(body.email)
    except ValueError:
        email = None
        problems.append(_problem("email", "Enter a valid email address."))
    for message in check_policy(body.password, name=name, email=email or ""):
        problems.append(_problem("password", message))
    if problems:
        raise HTTPException(status_code=422, detail=problems)

    # 4. Only now is the address looked up.
    if db.scalar(select(User.user_id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail=DUPLICATE_MESSAGE)

    user = User(name=name, email=email, password_hash=hash_password(body.password), role="user")
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # someone registered the same address a moment ago
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_MESSAGE) from None

    verification_required = settings.require_email_verification and mailer.enabled
    raw_token = None
    if verification_required:
        raw_token = auth_tokens.issue(
            db, user.user_id, auth_tokens.VERIFY_EMAIL, auth_tokens.VERIFICATION_LIFETIME
        )
    audit.record(db, audit.REGISTRATION_SUCCESS, actor_id=user.user_id, target=email)
    db.commit()

    sent = False
    if verification_required:
        try:
            mailer.send(_verification_message(settings, name, email, raw_token))
            sent = True
        except MailerError:  # the account stays; the person can ask for another email
            audit.record(db, audit.VERIFICATION_EMAIL_FAILED, actor_id=user.user_id, target=email)
            db.commit()
    return RegisterOut(verification_required=verification_required, verification_email_sent=sent)


@router.post("/verify-email", response_model=VerifiedOut)
def verify_email(body: VerifyIn, db: Session = Depends(get_db)):
    user_id = auth_tokens.consume(db, body.token, auth_tokens.VERIFY_EMAIL)
    if user_id is None:
        raise HTTPException(status_code=400, detail=INVALID_LINK_MESSAGE)  # unknown, used and expired look alike
    user = db.get(User, user_id)
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    audit.record(db, audit.EMAIL_VERIFIED, actor_id=user.user_id, target=user.email)
    db.commit()
    return VerifiedOut(verified=True)


@router.post("/resend-verification", status_code=202, response_model=MessageOut)
def resend_verification(
    body: ResendIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)
):
    """Always answers the same way, so it cannot be used to find out which addresses are registered."""
    settings = request.app.state.settings
    mailer = request.app.state.mailer
    if settings.require_email_verification and mailer.enabled:
        try:
            email = normalise_email(body.email)
        except ValueError:
            email = None
        if email is not None:
            now = datetime.now(timezone.utc)
            earlier = audit.recent_times(
                db, audit.VERIFICATION_REQUESTED, now - RESEND_WINDOW, target=email, limit=RESEND_LIMIT + 1
            )
            audit.record(db, audit.VERIFICATION_REQUESTED, target=email)
            user = db.scalar(select(User).where(User.email == email))
            if may_send_verification(earlier, now) and user is not None and user.is_active and user.email_verified_at is None:
                raw = auth_tokens.issue(
                    db, user.user_id, auth_tokens.VERIFY_EMAIL, auth_tokens.VERIFICATION_LIFETIME
                )
                db.commit()
                background.add_task(_deliver, mailer, _verification_message(settings, user.name, email, raw))
            else:
                db.commit()
    return MessageOut(message=RESEND_MESSAGE)