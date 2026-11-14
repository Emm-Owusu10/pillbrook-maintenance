import re

from app.access_code import (
    ALPHABET,
    check_new_code,
    codes_match,
    decrypt_code,
    encrypt_code,
    format_code,
    generate_code,
    normalise_code,
)

KEY = "k" * 40


def test_generated_codes_are_twelve_characters_from_the_safe_alphabet_and_never_repeat():
    codes = {generate_code() for _ in range(500)}
    assert len(codes) == 500
    assert all(len(code) == 12 and set(code) <= set(ALPHABET) for code in codes)


def test_the_alphabet_leaves_out_characters_that_are_easy_to_confuse():
    assert not set("IO01") & set(ALPHABET)


def test_a_code_is_shown_in_groups_of_four():
    assert format_code("K7QM4TRX9WBH") == "K7QM-4TRX-9WBH"
    assert format_code("k7qm-4trx-9wbh") == "K7QM-4TRX-9WBH"


def test_normalising_ignores_case_spaces_hyphens_and_other_characters():
    assert normalise_code(" k7qm-4trx 9wbh!\n") == "K7QM4TRX9WBH"
    assert normalise_code("k7\u00e9m") == "K7M"


def test_codes_match_whatever_the_case_spaces_or_hyphens():
    assert codes_match("K7QM4TRX9WBH", "k7qm-4trx-9wbh")
    assert codes_match("K7QM4TRX9WBH", " K7QM 4TRX 9WBH ")
    assert not codes_match("K7QM4TRX9WBH", "K7QM4TRX9WBJ")
    assert not codes_match("K7QM4TRX9WBH", "K7QM4TRX9WB")
    assert not codes_match("K7QM4TRX9WBH", "")


def test_a_chosen_code_must_be_ten_to_thirty_two_letters_or_digits():
    assert check_new_code("farm-gate-2026") == "FARMGATE2026"
    for bad in ("", "short", "a" * 33, "!!! --- !!!"):
        try:
            check_new_code(bad)
        except ValueError as error:
            assert "10 to 32" in str(error)
        else:
            raise AssertionError(f"{bad!r} was accepted")


def test_encrypting_and_decrypting_returns_the_code():
    assert decrypt_code(KEY, encrypt_code(KEY, "K7QM4TRX9WBH")) == "K7QM4TRX9WBH"


def test_the_stored_form_is_the_normalised_code():
    assert decrypt_code(KEY, encrypt_code(KEY, "k7qm-4trx-9wbh")) == "K7QM4TRX9WBH"


def test_the_encrypted_form_hides_the_code_and_differs_every_time():
    first = encrypt_code(KEY, "K7QM4TRX9WBH")
    second = encrypt_code(KEY, "K7QM4TRX9WBH")
    assert "K7QM" not in first and "9WBH" not in first
    assert first != second
    assert re.fullmatch(r"[A-Za-z0-9_=-]+", first)


def test_a_different_secret_key_or_a_damaged_value_cannot_be_decrypted():
    token = encrypt_code(KEY, "K7QM4TRX9WBH")
    assert decrypt_code("j" * 40, token) is None
    assert decrypt_code(KEY, token[:-4] + "AAAA") is None
    assert decrypt_code(KEY, "not-a-token") is None
    assert decrypt_code(KEY, "") is None