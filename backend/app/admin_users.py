"""Administrator functions on other people's accounts (requirements FR8, FR9)."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import account_security, audit
from .access import Auth, require_permission
from .database import get_db
from .emails import normalise_email
from .models import User
from .permissions import Permission
from .schemas import AdminResetIn, TemporaryPasswordOut

router = APIRouter(prefix="/admin/users", tags=["admin"])

NOT_FOUND_MESSAGE = "No account has that email address."
OWN_ACCOUNT_MESSAGE = "Use Change password for your own account."
INACTIVE_MESSAGE = "That account is deactivated."


@router.post("/reset-password", response_model=TemporaryPasswordOut)
def reset_password(
    body: AdminResetIn,
    response: Response,
    db: Session = Depends(get_db),
    auth: Auth = Depends(require_permission(Permission.MANAGE_USERS, changes_data=True)),
):
    """Give a person a one-time temporary password. It is shown here once and never stored in readable form."""
    response.headers["Cache-Control"] = "no-store"  # this reply holds a secret
    try:
        email = normalise_email(body.email)
    except ValueError:
        email = None
    user = db.scalar(select(User).where(User.email == email)) if email is not None else None
    if user is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    if user.user_id == auth.user.user_id:
        raise HTTPException(status_code=400, detail=OWN_ACCOUNT_MESSAGE)
    if not user.is_active:
        raise HTTPException(status_code=409, detail=INACTIVE_MESSAGE)

    temporary, expires_at = account_security.issue_temporary_password(db, user)
    audit.record(db, audit.RESET_BY_ADMIN, actor_id=auth.user.user_id, target=user.email)  # never the password
    db.commit()
    return TemporaryPasswordOut(
        name=user.name, email=user.email, temporary_password=temporary, expires_at=expires_at
    )