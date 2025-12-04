"""
Validation utility functions.
"""

import re
import uuid
from typing import Any


def validate_uuid(value: str | uuid.UUID) -> uuid.UUID:
    """
    Validate and convert UUID string to UUID object.

    Args:
        value: UUID string or UUID object

    Returns:
        UUID object

    Raises:
        ValueError: If value is not a valid UUID
    """
    if isinstance(value, uuid.UUID):
        return value

    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid UUID: {value}") from e


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: str, schemes: list[str] | None = None) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate
        schemes: Allowed schemes (default: ['http', 'https'])

    Returns:
        True if valid, False otherwise
    """
    if schemes is None:
        schemes = ["http", "https"]

    pattern = r"^(" + "|".join(schemes) + r")://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url, re.IGNORECASE))


def validate_length(
    value: str,
    min_length: int | None = None,
    max_length: int | None = None,
) -> bool:
    """
    Validate string length.

    Args:
        value: String to validate
        min_length: Minimum length (inclusive)
        max_length: Maximum length (inclusive)

    Returns:
        True if valid, False otherwise
    """
    length = len(value)

    if min_length is not None and length < min_length:
        return False

    if max_length is not None and length > max_length:
        return False

    return True


def validate_range(
    value: int | float,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
) -> bool:
    """
    Validate numeric range.

    Args:
        value: Number to validate
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)

    Returns:
        True if valid, False otherwise
    """
    if min_value is not None and value < min_value:
        return False

    if max_value is not None and value > max_value:
        return False

    return True


def validate_non_empty(value: Any) -> bool:
    """
    Validate that value is not empty.

    Args:
        value: Value to validate (string, list, dict, etc.)

    Returns:
        True if not empty, False otherwise
    """
    if value is None:
        return False

    if isinstance(value, str | list | dict | tuple | set):
        return len(value) > 0

    return True


def sanitize_string(value: str, allow_unicode: bool = True) -> str:
    """
    Sanitize string by removing control characters.

    Args:
        value: String to sanitize
        allow_unicode: Whether to allow unicode characters

    Returns:
        Sanitized string
    """
    if allow_unicode:
        # Remove only control characters
        return "".join(char for char in value if not _is_control_char(char))
    else:
        # Keep only ASCII printable characters
        return "".join(char for char in value if 32 <= ord(char) <= 126)


def _is_control_char(char: str) -> bool:
    """
    Check if character is a control character.

    Args:
        char: Character to check

    Returns:
        True if control character, False otherwise
    """
    code = ord(char)
    # Control characters: 0-31 and 127-159
    return (0 <= code <= 31) or (127 <= code <= 159)


def validate_dict_keys(
    data: dict,
    required_keys: list[str] | None = None,
    allowed_keys: list[str] | None = None,
) -> bool:
    """
    Validate dictionary keys.

    Args:
        data: Dictionary to validate
        required_keys: Keys that must be present
        allowed_keys: Only these keys are allowed (if specified)

    Returns:
        True if valid, False otherwise
    """
    if required_keys:
        for key in required_keys:
            if key not in data:
                return False

    if allowed_keys:
        for key in data:
            if key not in allowed_keys:
                return False

    return True
