"""
Datetime utility functions.
"""

from datetime import UTC, datetime, timedelta


def get_utc_now() -> datetime:
    """
    Get current UTC datetime with timezone info.

    Returns:
        Current UTC datetime
    """
    return datetime.now(UTC)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.

    Args:
        dt: Datetime to format
        fmt: Format string (default: ISO-like format)

    Returns:
        Formatted datetime string
    """
    return dt.strftime(fmt)


def parse_datetime(dt_str: str, fmt: str | None = None) -> datetime:
    """
    Parse datetime from string.

    Args:
        dt_str: Datetime string
        fmt: Format string (if None, uses ISO format)

    Returns:
        Parsed datetime

    Raises:
        ValueError: If parsing fails
    """
    if fmt:
        return datetime.strptime(dt_str, fmt)

    # Try ISO format
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Try common formats
        for common_fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ]:
            try:
                return datetime.strptime(dt_str, common_fmt)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse datetime: {dt_str}") from None


def format_timedelta(td: timedelta) -> str:
    """
    Format timedelta to human-readable string.

    Args:
        td: Timedelta to format

    Returns:
        Formatted string (e.g., "2 hours, 30 minutes")
    """
    total_seconds = int(td.total_seconds())

    if total_seconds < 0:
        return "0 seconds"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts)


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure datetime has UTC timezone.

    Args:
        dt: Datetime to convert

    Returns:
        Datetime with UTC timezone
    """
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        return dt.replace(tzinfo=UTC)
    elif dt.tzinfo != UTC:
        # Convert to UTC
        return dt.astimezone(UTC)
    return dt


def is_expired(dt: datetime, ttl: int | None = None) -> bool:
    """
    Check if datetime has expired.

    Args:
        dt: Datetime to check
        ttl: Time to live in seconds (if None, never expires)

    Returns:
        True if expired, False otherwise
    """
    if ttl is None:
        return False

    dt_utc = ensure_utc(dt)
    now = get_utc_now()
    age = (now - dt_utc).total_seconds()

    return age > ttl
