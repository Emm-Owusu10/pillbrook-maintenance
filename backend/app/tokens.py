"""Session and CSRF tokens. Standard-library code only, so it is easy to test."""
import hashlib
import hmac
import secrets

TOKEN_BYTES = 32  # 256 bits of randomness


def new_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(raw_token: str) -> str:
    """What the database stores. A leaked database then holds no usable session codes."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def csrf_token_for(secret_key: str, raw_token: str) -> str:
    """The secret handshake word for one session, derived from the session code and SECRET_KEY."""
    message = b"csrf:" + raw_token.encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def csrf_matches(secret_key: str, raw_token: str, supplied: str | None) -> bool:
    if not supplied:
        return False
    expected = csrf_token_for(secret_key, raw_token).encode("utf-8")
    return hmac.compare_digest(expected, supplied.encode("utf-8"))