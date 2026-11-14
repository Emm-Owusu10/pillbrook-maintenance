"""The farm's shared settings, starting with the access code (requirement FR1, decision D62)."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import audit
from .access_code import check_new_code, decrypt_code, encrypt_code
from .models import FarmSetting

logger = logging.getLogger("pillbrook.farm")

ACCESS_CODE_KEY = "farm_access_code"


def get_access_code(db: Session, secret_key: str) -> str | None:
    """The current code, or None if none is set (registration stays closed) or it cannot be read."""
    row = db.get(FarmSetting, ACCESS_CODE_KEY)
    if row is None:
        return None
    code = decrypt_code(secret_key, row.value_encrypted)
    if code is None:
        # Usually SECRET_KEY was changed. Registration stays closed until a new code is set.
        logger.warning("The stored farm access code cannot be read. Set a new one.")
    return code


def set_access_code(db: Session, secret_key: str, code: str, updated_by: uuid.UUID | None = None) -> str:
    """Store a new code (encrypted) and return it in its stored form. Raises ValueError if it is unsuitable."""
    stored_form = check_new_code(code)
    encrypted = encrypt_code(secret_key, stored_form)
    now = datetime.now(timezone.utc)
    row = db.get(FarmSetting, ACCESS_CODE_KEY)
    if row is None:
        db.add(FarmSetting(setting_key=ACCESS_CODE_KEY, value_encrypted=encrypted, updated_by=updated_by, updated_at=now))
    else:
        row.value_encrypted = encrypted
        row.updated_by = updated_by
        row.updated_at = now
    audit.record(db, audit.ACCESS_CODE_CHANGED, actor_id=updated_by)  # the code itself is never recorded
    db.commit()
    return stored_form