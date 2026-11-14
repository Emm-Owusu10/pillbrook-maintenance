import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.access_code import decrypt_code
from app.farm import get_access_code, set_access_code
from tests.conftest import TEST_KEY


def test_with_no_code_set_there_is_nothing_to_read(migrated, app_engine):
    with Session(app_engine) as session:
        assert get_access_code(session, TEST_KEY) is None


def test_a_code_is_stored_encrypted_and_read_back(migrated, app_engine, owner_engine):
    with Session(app_engine) as session:
        assert set_access_code(session, TEST_KEY, "k7qm-4trx-9wbh") == "K7QM4TRX9WBH"
        assert get_access_code(session, TEST_KEY) == "K7QM4TRX9WBH"
    with owner_engine.connect() as connection:
        stored = connection.execute(text("SELECT value_encrypted FROM farm_settings")).scalar_one()
    assert stored != "K7QM4TRX9WBH"
    assert "K7QM" not in stored
    assert decrypt_code(TEST_KEY, stored) == "K7QM4TRX9WBH"


def test_a_new_code_replaces_the_old_one(migrated, app_engine, owner_engine):
    with Session(app_engine) as session:
        set_access_code(session, TEST_KEY, "FIRSTCODE123")
        set_access_code(session, TEST_KEY, "SECONDCODE45")
        assert get_access_code(session, TEST_KEY) == "SECONDCODE45"
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM farm_settings")).scalar_one() == 1


def test_a_different_secret_key_cannot_read_the_code(migrated, app_engine):
    with Session(app_engine) as session:
        set_access_code(session, TEST_KEY, "K7QM4TRX9WBH")
        assert get_access_code(session, "j" * 40) is None


def test_an_unsuitable_code_is_refused_and_nothing_is_stored(migrated, app_engine, owner_engine):
    with Session(app_engine) as session:
        with pytest.raises(ValueError):
            set_access_code(session, TEST_KEY, "short")
    with owner_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM farm_settings")).scalar_one() == 0


def test_the_change_is_recorded_but_never_the_code(migrated, app_engine, owner_engine):
    with Session(app_engine) as session:
        set_access_code(session, TEST_KEY, "K7QM4TRX9WBH")
    with owner_engine.connect() as connection:
        rows = connection.execute(text("SELECT event_type, target, detail FROM audit_log")).all()
    assert [row.event_type for row in rows] == ["access_code_changed"]
    assert "K7QM" not in " ".join(str(value) for row in rows for value in row)


def test_the_app_account_uses_the_table_but_cannot_change_it(migrated, app_engine):
    with Session(app_engine) as session:
        set_access_code(session, TEST_KEY, "K7QM4TRX9WBH")
    for statement in ("ALTER TABLE farm_settings ADD COLUMN extra integer", "DROP TABLE farm_settings", "TRUNCATE farm_settings"):
        with pytest.raises(ProgrammingError, match="permission denied|must be owner"):
            with app_engine.begin() as connection:
                connection.execute(text(statement))