"""One-time temporary passwords, given by the Administrator in person (decision D79).

Pure code with no database, so it is easy to test.
"""
import secrets

# Lowercase letters and digits, leaving out the characters that are easy to confuse: i, l, o, 0 and 1.
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
LENGTH = 16
GROUP = 4


def format_temporary_password(raw: str) -> str:
    """abcd efgh jkmn pqrs, joined with dashes, so it is easy to read out and to type."""
    return "-".join(raw[i : i + GROUP] for i in range(0, len(raw), GROUP))


def generate_temporary_password() -> str:
    return format_temporary_password("".join(secrets.choice(ALPHABET) for _ in range(LENGTH)))


def normalise_temporary_password(value: str) -> str:
    """Accept what a person might type: with or without dashes or spaces, in any case.

    Anything that is not a temporary password in disguise is returned unchanged.
    """
    compact = "".join(ch for ch in value if not ch.isspace() and ch != "-").lower()
    if len(compact) == LENGTH and set(compact) <= set(ALPHABET):
        return format_temporary_password(compact)
    return value