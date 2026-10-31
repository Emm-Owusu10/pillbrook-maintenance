import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.passwords import hash_password

INSERT = text("INSERT INTO users (name, email, password_hash, role) VALUES (:name, :email, :hash, :role)")


def _row(**overrides):
    values = {"name": "Ama Mensah", "email": "ama@farm-mail.org", "hash": "x", "role": "user"}
    values.update(overrides)
    return values


def test_the_users_table_follows_the_migration(alembic_config, owner_engine):
    command.upgrade(alembic_config, "head")
    try:
        assert "users" in inspect(owner_engine).get_table_names()
    finally:
        command.downgrade(alembic_config, "base")
    assert "users" not in inspect(owner_engine).get_table_names()


def test_new_rows_get_sensible_defaults(migrated, app_engine):
    with app_engine.begin() as connection:
        connection.execute(INSERT, _row())
    with app_engine.connect() as connection:
        row = connection.execute(
            text("SELECT user_id, is_active, email_verified_at, created_at FROM users")
        ).one()
    assert row.user_id is not None
    assert row.is_active is True
    assert row.email_verified_at is None
    assert row.created_at is not None


def test_a_duplicate_email_is_refused(migrated, app_engine):
    with app_engine.begin() as connection:
        connection.execute(INSERT, _row())
    with pytest.raises(IntegrityError):
        with app_engine.begin() as connection:
            connection.execute(INSERT, _row(name="Someone Else"))


def test_an_unknown_role_is_refused(migrated, app_engine):
    with pytest.raises(IntegrityError):
        with app_engine.begin() as connection:
            connection.execute(INSERT, _row(role="owner"))


def test_an_email_with_capital_letters_is_refused(migrated, app_engine):
    with pytest.raises(IntegrityError):
        with app_engine.begin() as connection:
            connection.execute(INSERT, _row(email="Ama@Farm-Mail.org"))


def test_a_real_password_hash_fits_the_column(migrated, app_engine):
    hashed = hash_password("a throwaway test passphrase")
    with app_engine.begin() as connection:
        connection.execute(INSERT, _row(hash=hashed))
    with app_engine.connect() as connection:
        assert connection.execute(text("SELECT password_hash FROM users")).scalar_one() == hashed


def test_the_app_account_manages_user_rows_but_cannot_change_the_table(migrated, app_engine):
    with app_engine.begin() as connection:
        connection.execute(INSERT, _row())
        connection.execute(text("UPDATE users SET is_active = false"))
        assert connection.execute(text("SELECT is_active FROM users")).scalar_one() is False
        connection.execute(text("DELETE FROM users"))

    for statement in (
        "ALTER TABLE users ADD COLUMN extra integer",
        "TRUNCATE users",
        "DROP TABLE users",
    ):
        with pytest.raises(ProgrammingError, match="permission denied|must be owner"):
            with app_engine.begin() as connection:
                connection.execute(text(statement))