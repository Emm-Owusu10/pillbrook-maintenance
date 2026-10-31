"""Email address checking and normalising."""
from email_validator import EmailNotValidError, validate_email

MAX_EMAIL_LENGTH = 254
_MESSAGE = "Enter a valid email address."


def normalise_email(value: str) -> str:
    """Return the checked, lowercase address, or raise ValueError with a safe message.

    No internet lookups are made, and the message never repeats what was typed.
    """
    try:
        result = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError:
        raise ValueError(_MESSAGE) from None
    email = result.normalized.lower()
    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(_MESSAGE)
    return email