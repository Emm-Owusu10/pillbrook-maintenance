import re

from app.tokens import csrf_matches, csrf_token_for, hash_token, new_session_token

KEY = "k" * 40


def test_session_tokens_are_long_and_never_repeat():
    tokens = {new_session_token() for _ in range(1000)}
    assert len(tokens) == 1000
    assert all(len(token) >= 43 for token in tokens)  # 32 random bytes need 43 characters


def test_session_tokens_use_only_url_safe_characters():
    assert re.fullmatch(r"[A-Za-z0-9_-]+", new_session_token())


def test_the_stored_fingerprint_is_a_64_character_hash_not_the_token():
    fingerprint = hash_token("abc")
    assert len(fingerprint) == 64
    assert re.fullmatch(r"[0-9a-f]+", fingerprint)
    assert fingerprint != "abc"
    assert fingerprint == hash_token("abc")
    assert fingerprint != hash_token("abd")


def test_a_csrf_token_is_stable_for_one_session_and_differs_between_sessions():
    assert csrf_token_for(KEY, "session-one") == csrf_token_for(KEY, "session-one")
    assert csrf_token_for(KEY, "session-one") != csrf_token_for(KEY, "session-two")


def test_a_csrf_token_depends_on_the_secret_key():
    assert csrf_token_for(KEY, "session-one") != csrf_token_for("j" * 40, "session-one")


def test_only_the_exact_csrf_token_is_accepted():
    good = csrf_token_for(KEY, "session-one")
    assert csrf_matches(KEY, "session-one", good) is True
    assert csrf_matches(KEY, "session-one", good[:-1] + "0") is False
    assert csrf_matches(KEY, "session-two", good) is False
    assert csrf_matches(KEY, "session-one", None) is False
    assert csrf_matches(KEY, "session-one", "") is False


def test_the_csrf_check_copes_with_unusual_characters():
    assert csrf_matches(KEY, "session-one", "\u00fcn\u00efcode-\U0001f642") is False