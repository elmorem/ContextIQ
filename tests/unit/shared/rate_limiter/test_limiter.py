"""
Unit tests for rate limiter implementations.
"""

from unittest.mock import patch

import pytest

from shared.rate_limiter import (
    FixedWindowRateLimiter,
    RateLimiterSettings,
    RateLimitExceeded,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)


class TestTokenBucketRateLimiter:
    """Tests for token bucket rate limiter."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return RateLimiterSettings(
            token_bucket_capacity=10,
            token_refill_rate=5.0,  # 5 tokens per second
        )

    @pytest.fixture
    def limiter(self, settings):
        """Create token bucket limiter."""
        return TokenBucketRateLimiter(settings=settings)

    def test_initialization(self, limiter, settings):
        """Test limiter initialization."""
        assert limiter.settings == settings
        assert len(limiter._buckets) == 0

    def test_first_request_allowed(self, limiter):
        """Test that first request is allowed."""
        result = limiter.check_rate_limit("user_123")
        assert result is True

    def test_get_remaining_initial(self, limiter):
        """Test getting remaining requests on first check."""
        remaining = limiter.get_remaining("user_123")
        assert remaining == 10  # Full capacity

    def test_get_remaining_after_request(self, limiter):
        """Test getting remaining requests after consuming tokens."""
        limiter.check_rate_limit("user_123")
        remaining = limiter.get_remaining("user_123")
        assert remaining == 9  # One token consumed

    def test_exhaust_bucket(self, limiter):
        """Test exhausting all tokens raises exception."""
        # Consume all 10 tokens
        for _ in range(10):
            limiter.check_rate_limit("user_123")

        # Next request should fail
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit("user_123")

        assert "user_123" in str(exc_info.value)
        assert exc_info.value.retry_after is not None
        assert exc_info.value.retry_after > 0

    def test_token_refill(self, limiter):
        """Test that tokens refill over time."""
        with patch("time.time") as mock_time:
            # Set initial time
            mock_time.return_value = 1000.0

            # Initialize bucket and consume all tokens
            for _ in range(10):
                limiter.check_rate_limit("user_123")

            # Verify exhausted
            remaining = limiter.get_remaining("user_123")
            assert remaining == 0

            # Advance time by 1 second (should refill 5 tokens at 5 tokens/sec)
            mock_time.return_value = 1001.0

            # Should have ~5 tokens available now
            remaining = limiter.get_remaining("user_123")
            assert remaining == 5

    def test_reset(self, limiter):
        """Test resetting a rate limit."""
        # Consume some tokens
        for _ in range(5):
            limiter.check_rate_limit("user_123")

        # Reset
        limiter.reset("user_123")

        # Should have full capacity again
        remaining = limiter.get_remaining("user_123")
        assert remaining == 10

    def test_different_keys_independent(self, limiter):
        """Test that different keys have independent buckets."""
        # Exhaust user_123
        for _ in range(10):
            limiter.check_rate_limit("user_123")

        # user_456 should still work
        result = limiter.check_rate_limit("user_456")
        assert result is True

    def test_capacity_limit(self, limiter):
        """Test that tokens don't exceed capacity."""
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            limiter.check_rate_limit("user_123")

            # Advance time by 10 seconds (would refill 50 tokens, but cap is 10)
            mock_time.return_value = 1010.0

            remaining = limiter.get_remaining("user_123")
            assert remaining == 10  # Capped at capacity


class TestSlidingWindowRateLimiter:
    """Tests for sliding window rate limiter."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return RateLimiterSettings(
            default_rate_limit=5,
            sliding_window_size=10,  # 10 second window
        )

    @pytest.fixture
    def limiter(self, settings):
        """Create sliding window limiter."""
        return SlidingWindowRateLimiter(settings=settings)

    def test_initialization(self, limiter, settings):
        """Test limiter initialization."""
        assert limiter.settings == settings
        assert len(limiter._windows) == 0

    def test_first_request_allowed(self, limiter):
        """Test that first request is allowed."""
        result = limiter.check_rate_limit("user_123")
        assert result is True

    def test_get_remaining_initial(self, limiter):
        """Test getting remaining requests initially."""
        remaining = limiter.get_remaining("user_123")
        assert remaining == 5

    def test_get_remaining_after_requests(self, limiter):
        """Test getting remaining requests after some requests."""
        limiter.check_rate_limit("user_123")
        limiter.check_rate_limit("user_123")
        remaining = limiter.get_remaining("user_123")
        assert remaining == 3

    def test_exhaust_window(self, limiter):
        """Test exhausting rate limit raises exception."""
        # Use all 5 requests
        for _ in range(5):
            limiter.check_rate_limit("user_123")

        # Next request should fail
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit("user_123")

        assert "user_123" in str(exc_info.value)
        assert exc_info.value.retry_after is not None

    def test_old_requests_expire(self, limiter):
        """Test that old requests outside window are cleaned up."""
        with patch("time.time") as mock_time:
            # Time 0: make 5 requests
            mock_time.return_value = 1000.0
            for _ in range(5):
                limiter.check_rate_limit("user_123")

            # Time 11: window should have cleared (window is 10 seconds)
            mock_time.return_value = 1011.0

            # Should be able to make requests again
            result = limiter.check_rate_limit("user_123")
            assert result is True
            remaining = limiter.get_remaining("user_123")
            assert remaining == 4

    def test_reset(self, limiter):
        """Test resetting a rate limit."""
        # Make some requests
        for _ in range(3):
            limiter.check_rate_limit("user_123")

        # Reset
        limiter.reset("user_123")

        # Should have full capacity
        remaining = limiter.get_remaining("user_123")
        assert remaining == 5

    def test_different_keys_independent(self, limiter):
        """Test that different keys have independent windows."""
        # Exhaust user_123
        for _ in range(5):
            limiter.check_rate_limit("user_123")

        # user_456 should still work
        result = limiter.check_rate_limit("user_456")
        assert result is True

    def test_partial_window_expiry(self, limiter):
        """Test that requests expire individually as they age out."""
        with patch("time.time") as mock_time:
            # Time 0: make 2 requests
            mock_time.return_value = 1000.0
            limiter.check_rate_limit("user_123")
            limiter.check_rate_limit("user_123")

            # Time 5: make 3 more requests (now at limit)
            mock_time.return_value = 1005.0
            limiter.check_rate_limit("user_123")
            limiter.check_rate_limit("user_123")
            limiter.check_rate_limit("user_123")

            # Time 11: first 2 requests should have expired
            mock_time.return_value = 1011.0
            remaining = limiter.get_remaining("user_123")
            assert remaining == 2  # 5 total - 3 recent requests


class TestFixedWindowRateLimiter:
    """Tests for fixed window rate limiter."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return RateLimiterSettings(
            default_rate_limit=5,
            fixed_window_size=10,  # 10 second window
        )

    @pytest.fixture
    def limiter(self, settings):
        """Create fixed window limiter."""
        return FixedWindowRateLimiter(settings=settings)

    def test_initialization(self, limiter, settings):
        """Test limiter initialization."""
        assert limiter.settings == settings
        assert len(limiter._windows) == 0

    def test_first_request_allowed(self, limiter):
        """Test that first request is allowed."""
        result = limiter.check_rate_limit("user_123")
        assert result is True

    def test_get_remaining_initial(self, limiter):
        """Test getting remaining requests initially."""
        remaining = limiter.get_remaining("user_123")
        assert remaining == 5

    def test_get_remaining_after_requests(self, limiter):
        """Test getting remaining requests after some requests."""
        limiter.check_rate_limit("user_123")
        limiter.check_rate_limit("user_123")
        remaining = limiter.get_remaining("user_123")
        assert remaining == 3

    def test_exhaust_window(self, limiter):
        """Test exhausting rate limit raises exception."""
        # Use all 5 requests
        for _ in range(5):
            limiter.check_rate_limit("user_123")

        # Next request should fail
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit("user_123")

        assert "user_123" in str(exc_info.value)
        assert exc_info.value.retry_after is not None

    def test_window_reset(self, limiter):
        """Test that window resets at fixed intervals."""
        with patch("time.time") as mock_time:
            # Time 1005 (within first 10-second window: 1000-1009)
            mock_time.return_value = 1005.0
            for _ in range(5):
                limiter.check_rate_limit("user_123")

            # Time 1008 (still in same window) - should be exhausted
            mock_time.return_value = 1008.0
            with pytest.raises(RateLimitExceeded):
                limiter.check_rate_limit("user_123")

            # Time 1010 (new window: 1010-1019) - should reset
            mock_time.return_value = 1010.0
            result = limiter.check_rate_limit("user_123")
            assert result is True
            remaining = limiter.get_remaining("user_123")
            assert remaining == 4

    def test_reset(self, limiter):
        """Test resetting a rate limit."""
        # Make some requests
        for _ in range(3):
            limiter.check_rate_limit("user_123")

        # Reset
        limiter.reset("user_123")

        # Should have full capacity
        remaining = limiter.get_remaining("user_123")
        assert remaining == 5

    def test_different_keys_independent(self, limiter):
        """Test that different keys have independent windows."""
        # Exhaust user_123
        for _ in range(5):
            limiter.check_rate_limit("user_123")

        # user_456 should still work
        result = limiter.check_rate_limit("user_456")
        assert result is True

    def test_window_boundary_alignment(self, limiter):
        """Test that windows align to fixed boundaries."""
        with patch("time.time") as mock_time:
            # Time 1007 - window is 1000-1009
            mock_time.return_value = 1007.0
            window_start = limiter._get_current_window_start()
            assert window_start == 1000.0

            # Time 1015 - window is 1010-1019
            mock_time.return_value = 1015.0
            window_start = limiter._get_current_window_start()
            assert window_start == 1010.0

            # Time 1020 - window is 1020-1029
            mock_time.return_value = 1020.0
            window_start = limiter._get_current_window_start()
            assert window_start == 1020.0


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_default_message(self):
        """Test exception with default message."""
        exc = RateLimitExceeded()
        assert str(exc) == "Rate limit exceeded"
        assert exc.retry_after is None

    def test_custom_message(self):
        """Test exception with custom message."""
        exc = RateLimitExceeded("Custom error")
        assert str(exc) == "Custom error"

    def test_retry_after(self):
        """Test exception with retry_after."""
        exc = RateLimitExceeded("Too many requests", retry_after=30.5)
        assert exc.retry_after == 30.5
