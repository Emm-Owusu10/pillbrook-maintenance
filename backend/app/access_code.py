"""The farm access code: making it, checking it, and encrypting it (decision D62).

Pure code with no database, so it is easy to test.
"""
import base64
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0 or 1, which are easy to confuse
CODE_LENGTH = 12
MIN_CUSTOM_LENGTH = 10
MAX_CUSTOM_LENGTH = 32


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalise_code(value: str) -> str:
    """Capital letters and digits only, so case, spaces and hyphens never matter."""
    return "".join(ch for ch in value.upper() if ch.isascii() and ch.isalnum())


def format_code(code: str) -> str:
    """K7QM4TRX9WBH becomes K7QM-4TRX-9WBH, which is easier to read out and to type."""
    code = normalise_code(code)
    return "-".join(code[i : i + 4] for i in range(0, len(code), 4))


def check_new_code(value: str) -> str:
    """Return the code in its stored form, or raise ValueError with a message that is safe to show."""
    code = normalise_code(value)
    if not MIN_CUSTOM_LENGTH <= len(code) <= MAX_CUSTOM_LENGTH:
        raise ValueError(f"The code must be {MIN_CUSTOM_LENGTH} to {MAX_CUSTOM_LENGTH} letters or digits.")
    return code


def codes_match(stored: str, supplied: str) -> bool:
    return hmac.compare_digest(normalise_code(stored).encode(), normalise_code(supplied).encode())


def _fernet(secret_key: str) -> Fernet:
    # A key made only for this purpose, derived from SECRET_KEY, so the same secret is never used twice.
    raw = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"pillbrook farm settings v1").derive(
        secret_key.encode("utf-8")
    )
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_code(secret_key: str, code: str) -> str:
    return _fernet(secret_key).encrypt(normalise_code(code).encode("utf-8")).decode("ascii")


def decrypt_code(secret_key: str, token: str) -> str | None:
    """The code, or None if the token is damaged or was made with a different SECRET_KEY."""
    try:
        return _fernet(secret_key).decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError):
        return None