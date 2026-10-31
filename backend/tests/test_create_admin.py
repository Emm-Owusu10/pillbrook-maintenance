import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.create_admin import SetupError, administrator_exists, create_first_admin
from app.passwords import verify_password

GOOD_PASSWORD = "correct horse battery staple"


def test_the_first_administrator_is_created_correctly(migrated, app_engine, small_list):
    with Session(app_engine) as session:
        assert administrator_exists(session) is False
        user = create_first_admin(session, "  Ama Mensah ", "Ama@Farm-Mail.org", GOOD_PASSWORD)
        assert user.role == "admin"
        assert user.name == "Ama Mensah"
        assert user.email == "ama@farm-mail.org"
        assert user.is_active is True
        assert user.email_verified_at is not None
        assert user.password_hash != GOOD_PASSWORD
        assert verify_password(user.password_hash, GOOD_PASSWORD)
        assert administrator_exists(session) is True


def test_a_second_administrator_is_refused(migrated, app_engine, small_list):
    with Session(app_engine) as session:
        create_first_admin(session, "Ama Mensah", "ama@farm-mail.org", GOOD_PASSWORD)
        with pytest.raises(SetupError, match="already exists"):
            create_first_admin(session, "Kofi Boateng", "kofi@farm-mail.org", GOOD_PASSWORD)


def test_a_weak_password_creates_nothing(migrated, app_engine, small_list):
    with Session(app_engine) as session:
        with pytest.raises(SetupError, match="at least"):
            create_first_admin(session, "Ama Mensah", "ama@farm-mail.org", "short")
        assert administrator_exists(session) is False


def test_a_bad_email_creates_nothing(migrated, app_engine, small_list):
    with Session(app_engine) as session:
        with pytest.raises(SetupError, match="valid email"):
            create_first_admin(session, "Ama Mensah", "not-an-email", GOOD_PASSWORD)
        assert administrator_exists(session) is False


@pytest.mark.parametrize("name", ["", "   ", "n" * 101])
def test_an_empty_or_overlong_name_creates_nothing(migrated, app_engine, small_list, name):
    with Session(app_engine) as session:
        with pytest.raises(SetupError, match="1 to 100"):
            create_first_admin(session, name, "ama@farm-mail.org", GOOD_PASSWORD)
        assert administrator_exists(session) is False


def test_an_email_that_is_already_registered_is_refused(migrated, app_engine, small_list):
    with Session(app_engine) as session:
        session.execute(
            text("INSERT INTO users (name, email, password_hash, role) VALUES ('Old', 'ama@farm-mail.org', 'x', 'user')")
        )
        session.commit()
        with pytest.raises(SetupError, match="already registered"):
            create_first_admin(session, "Ama Mensah", "ama@farm-mail.org", GOOD_PASSWORD)
        assert administrator_exists(session) is False


def test_error_messages_never_contain_the_password(migrated, app_engine, small_list):
    with Session(app_engine) as session:
        with pytest.raises(SetupError) as error:
            create_first_admin(session, "Ama Mensah", "ama@farm-mail.org", "tiny-secret-pw")
        assert "secret" not in str(error.value)