"""Password rules, hashing and the common-password list (decision D12; requirements SR1, SR2)."""
import unicodedata
from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MIN_LENGTH = 15
MAX_LENGTH = 128
MIN_CONTEXT_WORD_LENGTH = 4  # shorter name parts would reject too many harmless passwords
SERVICE_WORDS = ("pillbrook",)
BLOCKLIST_FILE = Path(__file__).resolve().parent / "data" / "common_passwords.txt"

# OWASP's recommended minimum for Argon2id: 19 MiB of memory, 2 rounds, 1 lane.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def normalise(password: str) -> str:
    """Different keyboards can produce the same visible text in different ways; make them equal."""
    return unicodedata.normalize("NFKC", password)


@lru_cache(maxsize=1)
def _common_passwords() -> frozenset[str]:
    if not BLOCKLIST_FILE.is_file():
        # Fail closed: without the list, accepting passwords would silently weaken the rules.
        raise RuntimeError("The common-password list is missing. See app/data/README.md.")
    with BLOCKLIST_FILE.open(encoding="utf-8", errors="ignore") as handle:
        return frozenset(normalise(line.strip()).casefold() for line in handle if line.strip())


def _is_common(candidate: str) -> bool:
    words = _common_passwords()
    folded = candidate.casefold()
    if folded in words:
        return True
    # A listed word with digits or symbols added at the end is just as guessable.
    stem = folded.rstrip("0123456789!@#$%^&*()-_=+.?")
    return len(stem) >= MIN_CONTEXT_WORD_LENGTH and stem in words


def _context_words(name: str, email: str) -> list[str]:
    words = [w for w in "".join(c if c.isalpha() else " " for c in name).split()]
    local_part = email.split("@", 1)[0]
    words.append(local_part)
    words.extend(SERVICE_WORDS)
    return [w.casefold() for w in words if len(w) >= MIN_CONTEXT_WORD_LENGTH]


def check_policy(password: str, *, name: str = "", email: str = "") -> list[str]:
    """Return every problem with the password. An empty list means it is acceptable.

    The messages never contain the password.
    """
    candidate = normalise(password)
    problems: list[str] = []

    if len(candidate) < MIN_LENGTH:
        problems.append(f"Use at least {MIN_LENGTH} characters.")
    if len(candidate) > MAX_LENGTH:
        problems.append(f"Use no more than {MAX_LENGTH} characters.")
    if _is_common(candidate):
        problems.append("This password is too common. Choose something more unusual.")
    folded = candidate.casefold()
    if any(word in folded for word in _context_words(name, email)):
        problems.append("Do not include your name, your email name, or the farm's name.")
    return problems


def hash_password(password: str) -> str:
    candidate = normalise(password)
    if len(candidate) > MAX_LENGTH:
        raise ValueError("Password is too long to hash.")
    return _hasher.hash(candidate)


def verify_password(stored_hash: str, password: str) -> bool:
    candidate = normalise(password)
    if len(candidate) > MAX_LENGTH:
        return False  # refuse huge inputs before doing any expensive work
    try:
        return _hasher.verify(stored_hash, candidate)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True when the hash was made with older settings and should be upgraded at the next login."""
    return _hasher.check_needs_rehash(stored_hash)