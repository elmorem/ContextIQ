"""
Rate limiter implementations.

Provides multiple rate limiting algorithms for protecting APIs and services.
"""

import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any

from shared.rate_limiter.config import RateLimiterSettings, get_rate_limiter_settings


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
    ):
        """
        Initialize rate limit exception.

        Args:
            message: Error message
            retry_after: Seconds until rate limit resets
        """
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter(ABC):
    """Base class for rate limiters."""

    def __init__(self, settings: RateLimiterSettings | None = None):
        """
        Initialize rate limiter.

        Args:
            settings: Rate limiter configuration
        """
        self.settings = settings or get_rate_limiter_settings()

    @abstractmethod
    def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for the rate limit (e.g., user_id, ip_address)

        Returns:
            True if request is allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Identifier to reset
        """
        pass

    @abstractmethod
    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests allowed.

        Args:
            key: Identifier to check

        Returns:
            Number of requests remaining
        """
        pass


class TokenBucketRateLimiter(RateLimiter):
    """
    Token bucket rate limiter.

    Tokens are added to a bucket at a constant rate up to a maximum capacity.
    Each request consumes one token. If the bucket is empty, the request is denied.
    """

    def __init__(self, settings: RateLimiterSettings | None = None):
        """
        Initialize token bucket rate limiter.

        Args:
            settings: Rate limiter configuration
        """
        super().__init__(settings)
        self._buckets: dict[str, dict[str, Any]] = {}

    def _get_or_create_bucket(self, key: str) -> dict[str, Any]:
        """
        Get or create a bucket for a key.

        Args:
            key: Identifier for the bucket

        Returns:
            Bucket state dictionary
        """
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": float(self.settings.token_bucket_capacity),
                "last_refill": time.time(),
            }
        return self._buckets[key]

    def _refill_tokens(self, bucket: dict[str, Any]) -> None:
        """
        Refill tokens based on elapsed time.

        Args:
            bucket: Bucket state to refill
        """
        now = time.time()
        elapsed = now - bucket["last_refill"]
        tokens_to_add = elapsed * self.settings.token_refill_rate

        bucket["tokens"] = min(
            bucket["tokens"] + tokens_to_add,
            float(self.settings.token_bucket_capacity),
        )
        bucket["last_refill"] = now

    def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for the rate limit

        Returns:
            True if request is allowed

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        bucket = self._get_or_create_bucket(key)
        self._refill_tokens(bucket)

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        else:
            # Calculate retry_after based on refill rate
            tokens_needed = 1.0 - bucket["tokens"]
            retry_after = tokens_needed / self.settings.token_refill_rate
            raise RateLimitExceeded(
                f"Rate limit exceeded for {key}",
                retry_after=retry_after,
            )

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Identifier to reset
        """
        if key in self._buckets:
            del self._buckets[key]

    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests allowed.

        Args:
            key: Identifier to check

        Returns:
            Number of requests remaining (floored to integer)
        """
        bucket = self._get_or_create_bucket(key)
        self._refill_tokens(bucket)
        return int(bucket["tokens"])


class SlidingWindowRateLimiter(RateLimiter):
    """
    Sliding window rate limiter.

    Tracks requests in a sliding time window. The window is divided into
    sub-windows for more granular tracking.
    """

    def __init__(self, settings: RateLimiterSettings | None = None):
        """
        Initialize sliding window rate limiter.

        Args:
            settings: Rate limiter configuration
        """
        super().__init__(settings)
        self._windows: dict[str, deque[float]] = {}

    def _get_or_create_window(self, key: str) -> deque[float]:
        """
        Get or create a window for a key.

        Args:
            key: Identifier for the window

        Returns:
            Deque of request timestamps
        """
        if key not in self._windows:
            self._windows[key] = deque()
        return self._windows[key]

    def _cleanup_old_requests(self, window: deque[float], now: float) -> None:
        """
        Remove requests outside the current window.

        Args:
            window: Request timestamp queue
            now: Current timestamp
        """
        cutoff = now - self.settings.sliding_window_size
        while window and window[0] < cutoff:
            window.popleft()

    def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for the rate limit

        Returns:
            True if request is allowed

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        now = time.time()
        window = self._get_or_create_window(key)
        self._cleanup_old_requests(window, now)

        if len(window) < self.settings.default_rate_limit:
            window.append(now)
            return True
        else:
            # Calculate retry_after as time until oldest request expires
            oldest_request = window[0]
            retry_after = oldest_request + self.settings.sliding_window_size - now
            raise RateLimitExceeded(
                f"Rate limit exceeded for {key}",
                retry_after=max(0, retry_after),
            )

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Identifier to reset
        """
        if key in self._windows:
            del self._windows[key]

    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests allowed.

        Args:
            key: Identifier to check

        Returns:
            Number of requests remaining
        """
        now = time.time()
        window = self._get_or_create_window(key)
        self._cleanup_old_requests(window, now)
        return max(0, self.settings.default_rate_limit - len(window))


class FixedWindowRateLimiter(RateLimiter):
    """
    Fixed window rate limiter.

    Counts requests in fixed time windows. The window resets at regular intervals.
    """

    def __init__(self, settings: RateLimiterSettings | None = None):
        """
        Initialize fixed window rate limiter.

        Args:
            settings: Rate limiter configuration
        """
        super().__init__(settings)
        self._windows: dict[str, dict[str, Any]] = {}

    def _get_current_window_start(self) -> float:
        """
        Get the start time of the current window.

        Returns:
            Timestamp of current window start
        """
        now = time.time()
        return now - (now % self.settings.fixed_window_size)

    def _get_or_create_window(self, key: str) -> dict[str, Any]:
        """
        Get or create a window for a key.

        Args:
            key: Identifier for the window

        Returns:
            Window state dictionary
        """
        current_window_start = self._get_current_window_start()

        if key not in self._windows:
            self._windows[key] = {
                "count": 0,
                "window_start": current_window_start,
            }
        else:
            # Reset if we're in a new window
            window = self._windows[key]
            if window["window_start"] < current_window_start:
                window["count"] = 0
                window["window_start"] = current_window_start

        return self._windows[key]

    def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for the rate limit

        Returns:
            True if request is allowed

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        window = self._get_or_create_window(key)

        if window["count"] < self.settings.default_rate_limit:
            window["count"] += 1
            return True
        else:
            # Calculate retry_after as time until window resets
            window_end = window["window_start"] + self.settings.fixed_window_size
            retry_after = window_end - time.time()
            raise RateLimitExceeded(
                f"Rate limit exceeded for {key}",
                retry_after=max(0, retry_after),
            )

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Identifier to reset
        """
        if key in self._windows:
            del self._windows[key]

    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests allowed.

        Args:
            key: Identifier to check

        Returns:
            Number of requests remaining
        """
        window = self._get_or_create_window(key)
        return max(0, self.settings.default_rate_limit - window["count"])
