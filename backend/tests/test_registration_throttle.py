from datetime import datetime, timedelta, timezone

from app.throttle import (
    CODE_PAUSE,
    CODE_WINDOW,
    MAX_WRONG_CODES,
    RESEND_LIMIT,
    RESEND_WINDOW,
    code_limit_reached,
    may_send_verification,
    registration_paused,
)

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def _ago(*minutes):
    return [NOW - timedelta(minutes=m) for m in minutes]


def test_the_agreed_limits():
    assert MAX_WRONG_CODES == 10
    assert CODE_WINDOW == CODE_PAUSE == timedelta(minutes=10)
    assert RESEND_LIMIT == 3
    assert RESEND_WINDOW == timedelta(hours=1)


def test_registration_pauses_after_ten_wrong_codes_in_ten_minutes():
    assert registration_paused(_ago(*range(1, 10)), NOW) is False
    assert registration_paused(_ago(*range(0, 10)), NOW) is True


def test_old_wrong_codes_do_not_count():
    assert registration_paused(_ago(*range(0, 9), 11), NOW) is False
    assert registration_paused(_ago(*range(0, 9), 10), NOW) is False  # exactly ten minutes ago has expired


def test_the_pause_is_logged_only_when_the_limit_is_first_reached():
    assert code_limit_reached(_ago(*range(0, 9)), NOW) is False
    assert code_limit_reached(_ago(*range(0, 10)), NOW) is True
    assert code_limit_reached([NOW] * 11, NOW) is False


def test_three_verification_emails_per_address_per_hour():
    assert may_send_verification([], NOW) is True
    assert may_send_verification(_ago(5, 10), NOW) is True
    assert may_send_verification(_ago(5, 10, 20), NOW) is False
    assert may_send_verification(_ago(5, 10, 61), NOW) is True  # one is more than an hour old