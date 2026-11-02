import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

INSERT_SESSION = text(
    "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (:user_id, :hash, now() + interval '1 hour')"
)


def test_the_new_tables_follow_the_migration(alembic_config, owner_engine):
    command.upgrade(alembic_config, "head")
    try:
        names = set(inspect(owner_engine).get_table_names())
        assert {"users", "sessions", "audit_log"} <= names
    finally:
        command.downgrade(alembic_config, "base")
    names = set(inspect(owner_engine).get_table_names())
    assert "sessions" not in names
    assert "audit_log" not in names


def test_the_app_account_can_add_and_read_audit_entries_but_never_change_or_remove_them(migrated, app_engine):
    with app_engine.begin() as connection:
        connection.execute(text("INSERT INTO audit_log (event_type, target) VALUES ('test_event', 'x')"))
        assert connection.execute(text("SELECT count(*) FROM audit_log")).scalar_one() == 1

    for statement in ("UPDATE audit_log SET target = 'changed'", "DELETE FROM audit_log", "TRUNCATE audit_log"):
        with pytest.raises(ProgrammingError, match="permission denied"):
            with app_engine.begin() as connection:
                connection.execute(text(statement))


def test_the_app_account_manages_sessions_but_cannot_change_the_table(migrated, app_engine, add_user):
    user_id = add_user()
    with app_engine.begin() as connection:
        connection.execute(INSERT_SESSION, {"user_id": user_id, "hash": "a" * 64})
        connection.execute(text("UPDATE sessions SET last_seen_at = now()"))
        connection.execute(text("DELETE FROM sessions"))

    for statement in ("ALTER TABLE sessions ADD COLUMN extra integer", "DROP TABLE sessions"):
        with pytest.raises(ProgrammingError, match="permission denied|must be owner"):
            with app_engine.begin() as connection:
                connection.execute(text(statement))


def test_two_sessions_cannot_share_a_fingerprint(migrated, app_engine, add_user):
    user_id = add_user()
    with app_engine.begin() as connection:
        connection.execute(INSERT_SESSION, {"user_id": user_id, "hash": "b" * 64})
    with pytest.raises(IntegrityError):
        with app_engine.begin() as connection:
            connection.execute(INSERT_SESSION, {"user_id": user_id, "hash": "b" * 64})


def test_removing_a_user_removes_their_sessions(migrated, app_engine, owner_engine, add_user):
    user_id = add_user()
    with app_engine.begin() as connection:
        connection.execute(INSERT_SESSION, {"user_id": user_id, "hash": "c" * 64})
    with owner_engine.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": user_id})
        assert connection.execute(text("SELECT count(*) FROM sessions")).scalar_one() == 0


def test_audit_entries_survive_the_removal_of_the_user_they_name(migrated, app_engine, owner_engine, add_user):
    user_id = add_user()
    with app_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO audit_log (event_type, actor_id) VALUES ('test_event', :id)"), {"id": user_id}
        )
    with owner_engine.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": user_id})
        row = connection.execute(text("SELECT actor_id FROM audit_log")).one()
    assert row.actor_id is None