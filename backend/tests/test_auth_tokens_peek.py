from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import auth_tokens

LIFETIME = timedelta(hours=1)
RESET = auth_tokens.RESET_PASSWORD
VERIFY = auth_tokens.VERIFY_EMAIL


def _issue(app_engine, user_id, purpose=RESET):
    with Session(app_engine) as session:
        raw = auth_tokens.issue(session, user_id, purpose, LIFETIME)
        session.commit()
    return raw


def _peek(app_engine, raw, purpose=RESET):
    with Session(app_engine) as session:
        return auth_tokens.peek(session, raw, purpose)


def test_looking_at_a_token_does_not_use_it_up(migrated, app_engine, add_user):
    user_id = add_user()
    raw = _issue(app_engine, user_id)
    assert _peek(app_engine, raw) == user_id
    assert _peek(app_engine, raw) == user_id
    with Session(app_engine) as session:
        assert auth_tokens.consume(session, raw, RESET) == user_id
        session.commit()


def test_a_used_token_can_no_longer_be_seen(migrated, app_engine, add_user):
    raw = _issue(app_engine, add_user())
    with Session(app_engine) as session:
        auth_tokens.consume(session, raw, RESET)
        session.commit()
    assert _peek(app_engine, raw) is None


def test_an_expired_unknown_or_wrong_kind_token_cannot_be_seen(migrated, app_engine, owner_engine, add_user):
    user_id = add_user()
    raw = _issue(app_engine, user_id)
    assert _peek(app_engine, raw, VERIFY) is None
    assert _peek(app_engine, "x" * 43) is None
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE auth_tokens SET expires_at = now() - interval '1 minute'"))
    assert _peek(app_engine, raw) is None


def test_the_reset_link_lasts_one_hour():
    assert auth_tokens.RESET_LIFETIME == timedelta(hours=1)
    assert auth_tokens.VERIFICATION_LIFETIME == timedelta(hours=24)