import pytest

from app.emails import normalise_email


def test_a_normal_address_is_lowercased():
    assert normalise_email("Ama.Mensah@Farm-Mail.ORG") == "ama.mensah@farm-mail.org"


def test_surrounding_spaces_are_removed():
    assert normalise_email("  ama@farm-mail.org ") == "ama@farm-mail.org"


@pytest.mark.parametrize(
    "bad",
    ["", "no-at-sign", "a@@farm-mail.org", "a b@farm-mail.org", "@farm-mail.org", "ama@", "ama@localhost"],
)
def test_invalid_addresses_are_refused(bad):
    with pytest.raises(ValueError, match="valid email"):
        normalise_email(bad)


def test_the_error_message_does_not_repeat_the_input():
    with pytest.raises(ValueError) as error:
        normalise_email("secret-not-an-email")
    assert "secret" not in str(error.value)


def test_overlong_addresses_are_refused():
    with pytest.raises(ValueError, match="valid email"):
        normalise_email("a" * 60 + "@" + "b" * 200 + ".org")