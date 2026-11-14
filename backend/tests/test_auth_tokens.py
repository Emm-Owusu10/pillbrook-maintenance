from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app import auth_tokens
from app.tokens import hash_token

LIFETIME = timedelta(hours=24)
VERIFY = auth_tokens.VERIFY_EMAIL
RESET = auth_tokens.RESET_PASSWORD


def _issue(app_engine, user_id, purpose=VERIFY):
    with Session(app_engine) as session:
        raw = auth_tokens.issue(session, user_id, purpose, LIFETIME)
        session.commit()
    return raw


def _consume(app_engine, raw, purpose=VERIFY):
    with Session(app_engine) as session:
        user_id = auth_tokens.consume(session, raw, purpose)
        session.commit()
    return user_id


def test_tokens_are_long_and_never_repeat(migrated, app_engine, add_user):
    user_id = add_user()
    first = _issue(app_engine, user_id)
    second = _issue(app_engine, user_id, RESET)
    assert first != second
    assert len(first) >= 43 and len(second) >= 43


def test_only_a_fingerprint_of_the_token_is_stored(migrated, app_engine, owner_engine, add_user):
    raw = _issue(app_engine, add_user())
    with owner_engine.connect() as connection:
        row = connection.execute(text("SELECT token_hash, purpose FROM auth_tokens")).one()
    assert row.token_hash == hash_token(raw)
    assert raw not in row.token_hash
    assert row.purpose == VERIFY


def test_a_token_gives_back_its_user_once(migrated, app_engine, add_user):
    user_id = add_user()
    raw = _issue(app_engine, user_id)
    assert _consume(app_engine, raw) == user_id
    assert _consume(app_engine, raw) is None


def test_an_expired_token_is_refused(migrated, app_engine, owner_engine, add_user):
    raw = _issue(app_engine, add_user())
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE auth_tokens SET expires_at = now() - interval '1 minute'"))
    assert _consume(app_engine, raw) is None


def test_a_token_for_another_purpose_is_refused_and_stays_usable_for_its_own(migrated, app_engine, add_user):
    user_id = add_user()
    raw = _issue(app_engine, user_id, VERIFY)
    assert _consume(app_engine, raw, RESET) is None
    assert _consume(app_engine, raw, VERIFY) == user_id


def test_an_unknown_token_is_refused(migrated, app_engine):
    assert _consume(app_engine, "x" * 43) is None


def test_a_new_token_cancels_older_unused_ones_of_the_same_kind(migrated, app_engine, add_user):
    user_id = add_user()
    old = _issue(app_engine, user_id)
    new = _issue(app_engine, user_id)
    assert _consume(app_engine, old) is None
    assert _consume(app_engine, new) == user_id


def test_tokens_of_different_kinds_live_side_by_side(migrated, app_engine, add_user):
    user_id = add_user()
    verify = _issue(app_engine, user_id, VERIFY)
    reset = _issue(app_engine, user_id, RESET)
    assert _consume(app_engine, verify, VERIFY) == user_id
    assert _consume(app_engine, reset, RESET) == user_id


def test_removing_a_user_removes_their_tokens(migrated, app_engine, owner_engine, add_user):
    user_id = add_user()
    _issue(app_engine, user_id)
    with owner_engine.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": user_id})
        assert connection.execute(text("SELECT count(*) FROM auth_tokens")).scalar_one() == 0


def test_an_unknown_purpose_is_refused_by_the_database(migrated, app_engine, add_user):
    user_id = add_user()
    with pytest.raises(IntegrityError):
        with app_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO auth_tokens (user_id, purpose, token_hash, expires_at) "
                    "VALUES (:user_id, 'other', :hash, now() + interval '1 hour')"
                ),
                {"user_id": user_id, "hash": "d" * 64},
            )


def test_two_tokens_cannot_share_a_fingerprint(migrated, app_engine, add_user):
    user_id = add_user()
    statement = text(
        "INSERT INTO auth_tokens (user_id, purpose, token_hash, expires_at) "
        "VALUES (:user_id, 'verify_email', :hash, now() + interval '1 hour')"
    )
    with app_engine.begin() as connection:
        connection.execute(statement, {"user_id": user_id, "hash": "e" * 64})
    with pytest.raises(IntegrityError):
        with app_engine.begin() as connection:
            connection.execute(statement, {"user_id": user_id, "hash": "e" * 64})


def test_the_app_account_uses_the_table_but_cannot_change_it(migrated, app_engine, add_user):
    _issue(app_engine, add_user())
    for statement in ("ALTER TABLE auth_tokens ADD COLUMN extra integer", "DROP TABLE auth_tokens", "TRUNCATE auth_tokens"):
        with pytest.raises(ProgrammingError, match="permission denied|must be owner"):
            with app_engine.begin() as connection:
                connection.execute(text(statement))