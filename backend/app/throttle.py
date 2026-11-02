"""Login throttling rules (requirement SR3). Pure logic, so it is easy to test."""
from datetime import datetime, timedelta

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