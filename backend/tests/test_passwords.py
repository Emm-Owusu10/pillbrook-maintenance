import pytest
from argon2 import PasswordHasher

from app import passwords
from app.passwords import MAX_LENGTH, MIN_LENGTH, check_policy, hash_password, needs_rehash, verify_password

PASSPHRASE = "correct horse battery staple"


def _filler(length):
    return ("kiwi-lemon-" * 20)[:length]


# ---- The password rules ----

def test_a_long_passphrase_with_spaces_is_accepted(small_list):
    assert check_policy(PASSPHRASE) == []


def test_the_minimum_length_is_enforced(small_list):
    assert any("at least" in problem for problem in check_policy(_filler(MIN_LENGTH - 1)))
    assert check_policy(_filler(MIN_LENGTH)) == []


def test_the_maximum_length_is_enforced(small_list):
    assert any("no more than" in problem for problem in check_policy(_filler(MAX_LENGTH + 1)))
    assert check_policy(_filler(MAX_LENGTH)) == []


def test_a_listed_password_is_refused_whatever_its_case(small_list):
    assert any("too common" in problem for problem in check_policy("QWERTY123456789"))


def test_a_listed_word_with_digits_added_is_refused(small_list):
    assert any("too common" in problem for problem in check_policy("iloveyou1234567890"))


def test_a_very_short_listed_stem_is_not_over_matched(small_list):
    assert check_policy("abc123456789012345") == []


def test_the_list_is_cleaned_when_it_is_loaded(small_list):
    words = passwords._common_passwords()
    assert "spaced" in words
    assert "qwerty123456789" in words
    assert "" not in words


def test_a_missing_list_stops_the_check_instead_of_skipping_it(tmp_path, monkeypatch):
    monkeypatch.setattr(passwords, "BLOCKLIST_FILE", tmp_path / "missing.txt")
    passwords._common_passwords.cache_clear()
    with pytest.raises(RuntimeError):
        check_policy(PASSPHRASE)
    passwords._common_passwords.cache_clear()


def test_a_name_in_the_password_is_refused(small_list):
    problems = check_policy("my-mensah-farm-phrase-1", name="Ama Mensah")
    assert any("Do not include" in problem for problem in problems)


def test_the_email_name_in_the_password_is_refused(small_list):
    problems = check_policy("my-eowusu-secret-phrase", email="eowusu@farm-mail.org")
    assert any("Do not include" in problem for problem in problems)


def test_the_farm_name_is_refused_whatever_its_case(small_list):
    assert any("Do not include" in problem for problem in check_policy("I work at PillBrook farm"))


def test_short_name_parts_are_ignored(small_list):
    assert check_policy("bo-and-al-ride-together-today", name="Al Bo") == []


def test_problem_messages_never_contain_the_password(small_list):
    problems = check_policy("hunter-two-mensah", name="Ama Mensah")
    assert problems
    assert all("hunter" not in p and "mensah" not in p.lower() for p in problems)


# ---- Hashing ----

def test_hash_uses_argon2id_with_the_agreed_settings():
    hashed = hash_password("a throwaway test passphrase")
    assert hashed.startswith("$argon2id$")
    assert "m=19456,t=2,p=1" in hashed


def test_hash_does_not_contain_the_password():
    assert "throwaway" not in hash_password("a throwaway test passphrase")


def test_each_hash_gets_its_own_salt():
    assert hash_password("same passphrase here") != hash_password("same passphrase here")


def test_verify_accepts_the_right_password_and_refuses_others():
    hashed = hash_password("right passphrase here")
    assert verify_password(hashed, "right passphrase here")
    assert not verify_password(hashed, "wrong passphrase here")


def test_verify_refuses_a_damaged_hash_without_raising():
    assert verify_password("not-a-hash", "anything at all") is False


def test_different_unicode_spellings_of_a_password_match():
    composed = "caf\u00e9 caf\u00e9 caf\u00e9 caf\u00e9"
    decomposed = "cafe\u0301 cafe\u0301 cafe\u0301 cafe\u0301"
    assert verify_password(hash_password(composed), decomposed)


def test_overlong_passwords_are_not_hashed_or_accepted():
    with pytest.raises(ValueError):
        hash_password("x" * (MAX_LENGTH + 1))
    stored = hash_password("normal passphrase here")
    assert verify_password(stored, "x" * (MAX_LENGTH + 1)) is False


def test_hashes_made_with_old_settings_are_flagged_for_upgrade():
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("some passphrase here")
    assert needs_rehash(weak)
    assert not needs_rehash(hash_password("some passphrase here"))