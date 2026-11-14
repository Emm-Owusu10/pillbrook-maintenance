"""Throttling rules for login, registration and verification emails (SR3, SR8).

Pure logic with no database, so it is easy to test.
"""
from datetime import datetime, timedelta

# ---- Login ----
MAX_FAILURES = 4                       # wrong attempts allowed...
FAILURE_WINDOW = timedelta(minutes=10)  # ...within this time
LOCK_DURATION = timedelta(minutes=10)   # then login for that email is refused for this long


def is_locked(failure_times: list[datetime], now: datetime) -> bool:
    """failure_times: when wrong logins happened for one email since its last success."""
    recent = sorted((t for t in failure_times if t > now - FAILURE_WINDOW), reverse=True)
    return len(recent) >= MAX_FAILURES and recent[0] > now - LOCK_DURATION


def reaches_limit(failure_times: list[datetime], now: datetime) -> bool:
    """True when the failure just recorded is the one that triggers the lock (so it is logged once)."""
    return sum(1 for t in failure_times if t > now - FAILURE_WINDOW) == MAX_FAILURES


# ---- Registration and verification emails ----
MAX_WRONG_CODES = 10                     # wrong farm access codes, counted for the whole farm...
CODE_WINDOW = timedelta(minutes=10)      # ...within this time pause registration
CODE_PAUSE = timedelta(minutes=10)       # how long registration stays paused (shown as Retry-After)
RESEND_LIMIT = 3                         # verification emails per address...
RESEND_WINDOW = timedelta(hours=1)       # ...per hour


def registration_paused(wrong_code_times: list[datetime], now: datetime) -> bool:
    return sum(1 for t in wrong_code_times if t > now - CODE_WINDOW) >= MAX_WRONG_CODES


def code_limit_reached(wrong_code_times: list[datetime], now: datetime) -> bool:
    """True when the wrong code just recorded is the one that triggers the pause (so it is logged once)."""
    return sum(1 for t in wrong_code_times if t > now - CODE_WINDOW) == MAX_WRONG_CODES


def may_send_verification(earlier_request_times: list[datetime], now: datetime) -> bool:
    return sum(1 for t in earlier_request_times if t > now - RESEND_WINDOW) < RESEND_LIMIT