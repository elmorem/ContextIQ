"""
Tests for validation utilities.
"""

import uuid

import pytest

from shared.utils.validation import (
    sanitize_string,
    validate_dict_keys,
    validate_email,
    validate_length,
    validate_non_empty,
    validate_range,
    validate_url,
    validate_uuid,
)


class TestValidateUuid:
    """Tests for validate_uuid."""

    def test_valid_uuid_string(self):
        """Test validating valid UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(uuid_str)
        assert isinstance(result, uuid.UUID)
        assert str(result) == uuid_str

    def test_uuid_object(self):
        """Test validating UUID object."""
        uuid_obj = uuid.uuid4()
        result = validate_uuid(uuid_obj)
        assert result == uuid_obj

    def test_invalid_uuid_raises_error(self):
        """Test that invalid UUID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID"):
            validate_uuid("not-a-uuid")

    def test_none_raises_error(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError):
            validate_uuid(None)


class TestValidateEmail:
    """Tests for validate_email."""

    def test_valid_email(self):
        """Test valid email addresses."""
        assert validate_email("user@example.com") is True
        assert validate_email("user.name@example.com") is True
        assert validate_email("user+tag@example.co.uk") is True

    def test_invalid_email(self):
        """Test invalid email addresses."""
        assert validate_email("not-an-email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user@.com") is False


class TestValidateUrl:
    """Tests for validate_url."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://example.com") is True
        assert validate_url("http://example.com/path") is True

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://example.com") is True
        assert validate_url("https://example.com/path?query=value") is True

    def test_invalid_url(self):
        """Test invalid URLs."""
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is False
        assert validate_url("example.com") is False

    def test_custom_schemes(self):
        """Test custom URL schemes."""
        assert validate_url("ftp://example.com", schemes=["ftp"]) is True
        assert validate_url("http://example.com", schemes=["ftp"]) is False


class TestValidateLength:
    """Tests for validate_length."""

    def test_valid_length(self):
        """Test valid string length."""
        assert validate_length("hello", min_length=1, max_length=10) is True

    def test_min_length(self):
        """Test minimum length validation."""
        assert validate_length("hi", min_length=3) is False
        assert validate_length("hello", min_length=3) is True

    def test_max_length(self):
        """Test maximum length validation."""
        assert validate_length("hello world", max_length=5) is False
        assert validate_length("hello", max_length=5) is True

    def test_no_limits(self):
        """Test with no length limits."""
        assert validate_length("any length string") is True


class TestValidateRange:
    """Tests for validate_range."""

    def test_valid_range(self):
        """Test valid numeric range."""
        assert validate_range(5, min_value=1, max_value=10) is True

    def test_min_value(self):
        """Test minimum value validation."""
        assert validate_range(5, min_value=10) is False
        assert validate_range(10, min_value=10) is True

    def test_max_value(self):
        """Test maximum value validation."""
        assert validate_range(15, max_value=10) is False
        assert validate_range(10, max_value=10) is True

    def test_float_values(self):
        """Test with float values."""
        assert validate_range(5.5, min_value=5.0, max_value=6.0) is True
        assert validate_range(4.5, min_value=5.0) is False

    def test_no_limits(self):
        """Test with no range limits."""
        assert validate_range(999999) is True


class TestValidateNonEmpty:
    """Tests for validate_non_empty."""

    def test_non_empty_string(self):
        """Test non-empty string."""
        assert validate_non_empty("hello") is True

    def test_empty_string(self):
        """Test empty string."""
        assert validate_non_empty("") is False

    def test_non_empty_list(self):
        """Test non-empty list."""
        assert validate_non_empty([1, 2, 3]) is True

    def test_empty_list(self):
        """Test empty list."""
        assert validate_non_empty([]) is False

    def test_non_empty_dict(self):
        """Test non-empty dict."""
        assert validate_non_empty({"key": "value"}) is True

    def test_empty_dict(self):
        """Test empty dict."""
        assert validate_non_empty({}) is False

    def test_none(self):
        """Test None value."""
        assert validate_non_empty(None) is False

    def test_numeric_values(self):
        """Test numeric values."""
        assert validate_non_empty(0) is True
        assert validate_non_empty(42) is True


class TestSanitizeString:
    """Tests for sanitize_string."""

    def test_clean_string(self):
        """Test string with no control characters."""
        result = sanitize_string("hello world")
        assert result == "hello world"

    def test_remove_control_characters(self):
        """Test removing control characters."""
        result = sanitize_string("hello\x00world\x1f")
        assert result == "helloworld"

    def test_keep_unicode(self):
        """Test keeping unicode characters."""
        result = sanitize_string("hello 世界", allow_unicode=True)
        assert result == "hello 世界"

    def test_remove_unicode(self):
        """Test removing unicode characters."""
        result = sanitize_string("hello 世界", allow_unicode=False)
        assert result == "hello "

    def test_keep_printable_ascii(self):
        """Test keeping printable ASCII."""
        result = sanitize_string("hello!@#", allow_unicode=False)
        assert result == "hello!@#"


class TestValidateDictKeys:
    """Tests for validate_dict_keys."""

    def test_valid_required_keys(self):
        """Test with valid required keys."""
        data = {"name": "John", "age": 30}
        assert validate_dict_keys(data, required_keys=["name", "age"]) is True

    def test_missing_required_keys(self):
        """Test with missing required keys."""
        data = {"name": "John"}
        assert validate_dict_keys(data, required_keys=["name", "age"]) is False

    def test_valid_allowed_keys(self):
        """Test with valid allowed keys."""
        data = {"name": "John"}
        assert validate_dict_keys(data, allowed_keys=["name", "age"]) is True

    def test_invalid_allowed_keys(self):
        """Test with invalid allowed keys."""
        data = {"name": "John", "email": "john@example.com"}
        assert validate_dict_keys(data, allowed_keys=["name", "age"]) is False

    def test_both_required_and_allowed(self):
        """Test with both required and allowed keys."""
        data = {"name": "John", "age": 30}
        assert (
            validate_dict_keys(data, required_keys=["name"], allowed_keys=["name", "age", "email"])
            is True
        )

    def test_no_constraints(self):
        """Test with no constraints."""
        data = {"any": "keys"}
        assert validate_dict_keys(data) is True
