"""
Tests for datetime utilities.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from shared.utils.datetime_utils import (
    ensure_utc,
    format_datetime,
    format_timedelta,
    get_utc_now,
    is_expired,
    parse_datetime,
)


class TestGetUtcNow:
    """Tests for get_utc_now."""

    def test_returns_datetime_with_utc_timezone(self):
        """Test that get_utc_now returns datetime with UTC timezone."""
        now = get_utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo == UTC

    def test_returns_current_time(self):
        """Test that get_utc_now returns current time."""
        before = datetime.now(UTC)
        now = get_utc_now()
        after = datetime.now(UTC)
        assert before <= now <= after


class TestFormatDatetime:
    """Tests for format_datetime."""

    def test_default_format(self):
        """Test formatting with default format."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        result = format_datetime(dt)
        assert result == "2024-01-15 14:30:45"

    def test_custom_format(self):
        """Test formatting with custom format."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        result = format_datetime(dt, "%Y/%m/%d")
        assert result == "2024/01/15"


class TestParseDatetime:
    """Tests for parse_datetime."""

    def test_parse_iso_format(self):
        """Test parsing ISO format."""
        result = parse_datetime("2024-01-15T14:30:45")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_parse_common_format(self):
        """Test parsing common format."""
        result = parse_datetime("2024-01-15 14:30:45")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_only(self):
        """Test parsing date only."""
        result = parse_datetime("2024-01-15")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_custom_format(self):
        """Test parsing with custom format."""
        result = parse_datetime("15/01/2024", "%d/%m/%Y")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_invalid_datetime_raises_error(self):
        """Test that invalid datetime raises ValueError."""
        with pytest.raises(ValueError):
            parse_datetime("invalid")


class TestFormatTimedelta:
    """Tests for format_timedelta."""

    def test_format_days(self):
        """Test formatting days."""
        td = timedelta(days=2, hours=3)
        result = format_timedelta(td)
        assert "2 days" in result
        assert "3 hours" in result

    def test_format_hours(self):
        """Test formatting hours."""
        td = timedelta(hours=5, minutes=30)
        result = format_timedelta(td)
        assert "5 hours" in result
        assert "30 minutes" in result

    def test_format_minutes(self):
        """Test formatting minutes."""
        td = timedelta(minutes=45, seconds=30)
        result = format_timedelta(td)
        assert "45 minutes" in result
        assert "30 seconds" in result

    def test_format_seconds(self):
        """Test formatting seconds."""
        td = timedelta(seconds=30)
        result = format_timedelta(td)
        assert "30 seconds" in result

    def test_format_zero(self):
        """Test formatting zero timedelta."""
        td = timedelta(seconds=0)
        result = format_timedelta(td)
        assert result == "0 seconds"

    def test_format_negative(self):
        """Test formatting negative timedelta."""
        td = timedelta(seconds=-30)
        result = format_timedelta(td)
        assert result == "0 seconds"

    def test_singular_units(self):
        """Test singular units (no 's')."""
        td = timedelta(days=1, hours=1, minutes=1, seconds=1)
        result = format_timedelta(td)
        assert "1 day," in result
        assert "1 hour," in result
        assert "1 minute," in result
        assert "1 second" in result


class TestEnsureUtc:
    """Tests for ensure_utc."""

    def test_naive_datetime_assumes_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = ensure_utc(dt)
        assert result.tzinfo == UTC
        assert result.year == 2024

    def test_utc_datetime_unchanged(self):
        """Test that UTC datetime is unchanged."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        result = ensure_utc(dt)
        assert result == dt

    def test_non_utc_datetime_converted(self):
        """Test that non-UTC datetime is converted."""
        # Create timezone with +5 hours offset
        tz = timezone(timedelta(hours=5))
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=tz)
        result = ensure_utc(dt)
        assert result.tzinfo == UTC
        # Should be 5 hours earlier in UTC
        assert result.hour == 9


class TestIsExpired:
    """Tests for is_expired."""

    def test_no_ttl_never_expires(self):
        """Test that datetime with no TTL never expires."""
        dt = datetime(2020, 1, 1, tzinfo=UTC)
        assert is_expired(dt, ttl=None) is False

    def test_not_expired(self):
        """Test datetime that has not expired."""
        dt = get_utc_now()
        assert is_expired(dt, ttl=3600) is False

    def test_expired(self):
        """Test datetime that has expired."""
        dt = datetime(2020, 1, 1, tzinfo=UTC)
        assert is_expired(dt, ttl=3600) is True

    def test_just_expired(self):
        """Test datetime that just expired."""
        dt = get_utc_now() - timedelta(seconds=61)
        assert is_expired(dt, ttl=60) is True

    def test_not_quite_expired(self):
        """Test datetime that has not quite expired."""
        dt = get_utc_now() - timedelta(seconds=59)
        assert is_expired(dt, ttl=60) is False
