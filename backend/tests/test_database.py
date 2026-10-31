import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError


def _role_flags(engine):
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user")
        ).one()
    return tuple(row)


def test_the_migrations_are_registered_in_order(alembic_config):
       # Fails at once if Alembic cannot see a migration file.
       script = ScriptDirectory.from_config(alembic_config)
       assert script.get_current_head() == "0002"
       assert [revision.revision for revision in script.walk_revisions()] == ["0002", "0001"]


def test_app_account_has_no_administrative_powers(app_engine):
    assert _role_flags(app_engine) == (False, False, False)


def test_owner_account_is_not_a_superuser(owner_engine):
    assert _role_flags(owner_engine) == (False, False, False)


def test_app_account_cannot_create_tables(app_engine):
    with pytest.raises(ProgrammingError, match="permission denied"):
        with app_engine.begin() as connection:
            connection.execute(text("CREATE TABLE should_not_exist (id integer)"))


def test_owner_account_can_create_and_drop_tables(owner_engine):
    with owner_engine.begin() as connection:
        connection.execute(text("CREATE TABLE owner_probe (id integer)"))
        connection.execute(text("DROP TABLE owner_probe"))


def test_app_account_can_use_data_but_not_change_the_structure(migrated, owner_engine, app_engine):
    with owner_engine.begin() as connection:
        connection.execute(text("CREATE TABLE probe_table (id integer)"))

    with app_engine.begin() as connection:
        connection.execute(text("INSERT INTO probe_table (id) VALUES (1)"))
        connection.execute(text("UPDATE probe_table SET id = 2"))
        assert connection.execute(text("SELECT id FROM probe_table")).scalar_one() == 2
        connection.execute(text("DELETE FROM probe_table"))

    for statement in (
        "ALTER TABLE probe_table ADD COLUMN extra integer",
        "TRUNCATE probe_table",
        "DROP TABLE probe_table",
    ):
        with pytest.raises(ProgrammingError, match="permission denied|must be owner"):
            with app_engine.begin() as connection:
                connection.execute(text(statement))


def test_downgrade_removes_the_default_privileges(alembic_config, owner_engine, app_engine):
    command.upgrade(alembic_config, "head")
    try:
        # While migrated, a new table is usable by the app account...
        with owner_engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS probe_table"))
            connection.execute(text("CREATE TABLE probe_table (id integer)"))
        with app_engine.begin() as connection:
            connection.execute(text("SELECT id FROM probe_table"))
        # ...and after the downgrade, a new table is not.
        with owner_engine.begin() as connection:
            connection.execute(text("DROP TABLE probe_table"))
        command.downgrade(alembic_config, "base")
        with owner_engine.begin() as connection:
            connection.execute(text("CREATE TABLE probe_table (id integer)"))
        with pytest.raises(ProgrammingError, match="permission denied"):
            with app_engine.begin() as connection:
                connection.execute(text("SELECT id FROM probe_table"))
    finally:
        with owner_engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS probe_table"))
        command.downgrade(alembic_config, "base")