from datetime import datetime, timedelta, timezone

from app.throttle import FAILURE_WINDOW, LOCK_DURATION, MAX_FAILURES, is_locked, reaches_limit

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def _ago(*minutes):
    return [NOW - timedelta(minutes=m) for m in minutes]


def test_the_agreed_limits():
    assert MAX_FAILURES == 4
    assert FAILURE_WINDOW == timedelta(minutes=10)
    assert LOCK_DURATION == timedelta(minutes=10)


def test_no_failures_means_no_lock():
    assert is_locked([], NOW) is False


def test_below_the_limit_is_not_locked():
    assert is_locked(_ago(1, 2, 3), NOW) is False


def test_the_limit_locks():
    assert is_locked(_ago(1, 2, 3, 4), NOW) is True


def test_old_failures_do_not_count():
    assert is_locked(_ago(1, 2, 3, 11), NOW) is False
    assert is_locked(_ago(1, 2, 3, 10), NOW) is False  # exactly ten minutes ago has expired


def test_the_lock_is_logged_only_when_the_limit_is_first_reached():
    assert reaches_limit(_ago(1, 2, 3), NOW) is False
    assert reaches_limit(_ago(1, 2, 3, 4), NOW) is True
    assert reaches_limit(_ago(1, 2, 3, 4, 5), NOW) is False