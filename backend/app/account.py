"""Changing a password, and resetting a forgotten one (requirements FR7, SR1, SR2, SR9)."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import account_security, audit, auth_tokens
from .access import Auth, require_signed_in_with_csrf
from .auth import LOCKED_MESSAGE
from .database import get_db
from .emails import normalise_email
from .mailer import EmailMessage, Mailer, MailerError
from .models import User
from .passwords import check_policy, verify_password
from .schemas import ChangePasswordIn, ForgotIn, MessageOut, OptionsOut, ResetIn
from .temp_password import normalise_temporary_password
from .throttle import LOCK_DURATION, RESEND_LIMIT, RESEND_WINDOW, is_locked, reaches_limit
from .throttle import may_send_verification as may_send_email

logger = logging.getLogger("pillbrook.account")
router = APIRouter(prefix="/auth", tags=["account"])

WRONG_CURRENT_MESSAGE = "The current password is not correct."
SAME_AS_CURRENT_MESSAGE = "Choose a password different from your current one."
FORGOT_MESSAGE = "If that address belongs to an account, an email with a link is on its way."
INVALID_LINK_MESSAGE = "This link is not valid or has expired."


def _problem(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def _reset_message(settings, name: str, email: str, raw_token: str) -> EmailMessage:
    # The code sits after a "#", which browsers never send to any server, so it stays out of server logs.
    link = f"{settings.public_base_url}/reset-password#token={raw_token}"
    minutes = int(auth_tokens.RESET_LIFETIME.total_seconds() // 60)
    body = (
        f"Hello {name},\n\n"
        "Someone, hopefully you, asked to reset the password for your Pill Brook Facility Maintenance account.\n"
        f"To choose a new password, open this link within {minutes} minutes:\n\n{link}\n\n"
        "If you did not ask for this, you can ignore this message. Your password has not changed.\n"
    )
    return EmailMessage(to=email, subject="Reset your password", text=body)


def _deliver(mailer: Mailer, message: EmailMessage) -> None:
    """Runs after the reply has been sent, so a visitor cannot tell from the speed whether an email was sent."""
    try:
        mailer.send(message)
    except MailerError:
        logger.warning("A password reset email could not be sent")


@router.get("/options", response_model=OptionsOut)
def options(request: Request):
    """What the screens need to know before sign-in: whether a reset by email is possible."""
    return OptionsOut(email_reset_available=request.app.state.mailer.enabled)


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordIn,
    db: Session = Depends(get_db),
    auth: Auth = Depends(require_signed_in_with_csrf),
):
    """Allowed even while a temporary password must be replaced: this is how it is replaced."""
    user = auth.user
    now = datetime.now(timezone.utc)

    # Someone holding a stolen session could try to guess the current password, so wrong guesses here
    # count towards the same lock as sign-in.
    if is_locked(audit.failures_since_last_success(db, user.email, now), now):
        raise HTTPException(
            status_code=429,
            detail=LOCKED_MESSAGE,
            headers={"Retry-After": str(int(LOCK_DURATION.total_seconds()))},
        )
    current = normalise_temporary_password(body.current_password) if user.must_change_password else body.current_password
    if not verify_password(user.password_hash, current):
        audit.record(db, audit.LOGIN_FAILURE, actor_id=user.user_id, target=user.email, detail="wrong current password")
        db.flush()
        if reaches_limit(audit.failures_since_last_success(db, user.email, now), now):
            audit.record(db, audit.LOGIN_LOCKED, target=user.email)
        db.commit()
        raise HTTPException(status_code=403, detail=WRONG_CURRENT_MESSAGE)

    problems = [
        _problem("new_password", message)
        for message in check_policy(body.new_password, name=user.name, email=user.email)
    ]
    if not problems and verify_password(user.password_hash, body.new_password):
        problems.append(_problem("new_password", SAME_AS_CURRENT_MESSAGE))
    if problems:
        raise HTTPException(status_code=422, detail=problems)

    account_security.set_chosen_password(db, user, body.new_password, keep_session_id=auth.session.session_id)
    audit.record(db, audit.OWN_CHANGE, actor_id=user.user_id, target=user.email)
    db.commit()


@router.post("/forgot-password", status_code=202, response_model=MessageOut)
def forgot_password(body: ForgotIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Always answers the same way, so it cannot be used to find out which addresses are registered."""
    settings = request.app.state.settings
    mailer = request.app.state.mailer
    if mailer.enabled:
        try:
            email = normalise_email(body.email)
        except ValueError:
            email = None
        if email is not None:
            now = datetime.now(timezone.utc)
            earlier = audit.recent_times(
                db, audit.RESET_REQUESTED, now - RESEND_WINDOW, target=email, limit=RESEND_LIMIT + 1
            )
            audit.record(db, audit.RESET_REQUESTED, target=email)
            user = db.scalar(select(User).where(User.email == email))
            if may_send_email(earlier, now) and user is not None and user.is_active:
                raw = auth_tokens.issue(db, user.user_id, auth_tokens.RESET_PASSWORD, auth_tokens.RESET_LIFETIME)
                db.commit()
                background.add_task(_deliver, mailer, _reset_message(settings, user.name, email, raw))
            else:
                db.commit()
    return MessageOut(message=FORGOT_MESSAGE)


@router.post("/reset-password", status_code=204)
def reset_password_with_link(body: ResetIn, db: Session = Depends(get_db)):
    """Choose a new password with the one-time code from an emailed link."""
    user_id = auth_tokens.peek(db, body.token, auth_tokens.RESET_PASSWORD)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail=INVALID_LINK_MESSAGE)  # unknown, used and expired look alike

    # The password is checked before the link is used up, so a typo does not waste it.
    problems = [
        _problem("new_password", message)
        for message in check_policy(body.new_password, name=user.name, email=user.email)
    ]
    if problems:
        raise HTTPException(status_code=422, detail=problems)

    if auth_tokens.consume(db, body.token, auth_tokens.RESET_PASSWORD) is None:  # someone used it a moment ago
        raise HTTPException(status_code=400, detail=INVALID_LINK_MESSAGE)
    account_security.set_chosen_password(db, user, body.new_password)
    audit.record(db, audit.RESET_BY_LINK, actor_id=user.user_id, target=user.email)
    db.commit()