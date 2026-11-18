import re

from app.temp_password import (
    ALPHABET,
    LENGTH,
    format_temporary_password,
    generate_temporary_password,
    normalise_temporary_password,
)

SHAPE = re.compile(r"^[a-hjkmnp-z2-9]{4}(-[a-hjkmnp-z2-9]{4}){3}$")


def test_a_temporary_password_is_four_groups_of_four_from_the_safe_alphabet():
    for _ in range(200):
        assert SHAPE.match(generate_temporary_password())


def test_the_alphabet_leaves_out_characters_that_are_easy_to_confuse_and_capitals():
    assert not set("ilo01") & set(ALPHABET)
    assert ALPHABET == ALPHABET.lower()
    assert len(ALPHABET) == 31


def test_temporary_passwords_never_repeat_and_are_hard_to_guess():
    assert len({generate_temporary_password() for _ in range(1000)}) == 1000
    assert len(ALPHABET) ** LENGTH > 2**75  # about 79 bits


def test_it_is_shown_with_dashes():
    assert format_temporary_password("abcdefghjkmnpqrs") == "abcd-efgh-jkmn-pqrs"


def test_a_person_may_type_it_with_or_without_dashes_spaces_or_capitals():
    expected = "abcd-efgh-jkmn-pqrs"
    for typed in ("abcd-efgh-jkmn-pqrs", "abcdefghjkmnpqrs", "ABCD-EFGH-JKMN-PQRS", " abcd efgh jkmn pqrs ", "abcd--efgh-jkmn-pqrs"):
        assert normalise_temporary_password(typed) == expected, typed


def test_anything_else_is_left_exactly_as_typed():
    for typed in ("", "short", "kiwi lemon river stone", "abcd-efgh-jkmn-pqr", "abcd-efgh-jkmn-pqrst", "abcd-efgh-jkmn-pqr0"):
        assert normalise_temporary_password(typed) == typed