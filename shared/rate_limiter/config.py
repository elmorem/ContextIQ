"""
Configuration settings for rate limiter.

Defines default rate limits and algorithm settings.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RateLimiterSettings(BaseSettings):
    """Settings for rate limiting."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RATE_LIMITER_",
        case_sensitive=False,
    )

    # Default rate limits
    default_rate_limit: int = Field(
        default=100,
        ge=1,
        description="Default requests per window",
    )

    default_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Default time window in seconds",
    )

    # Token bucket settings
    token_bucket_capacity: int = Field(
        default=100,
        ge=1,
        description="Maximum tokens in bucket",
    )

    token_refill_rate: float = Field(
        default=10.0,
        ge=0.1,
        description="Tokens added per second",
    )

    # Sliding window settings
    sliding_window_size: int = Field(
        default=60,
        ge=1,
        description="Sliding window size in seconds",
    )

    sliding_window_precision: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of sub-windows for sliding window",
    )

    # Fixed window settings
    fixed_window_size: int = Field(
        default=60,
        ge=1,
        description="Fixed window size in seconds",
    )

    # Storage settings
    use_redis_backend: bool = Field(
        default=False,
        description="Use Redis for distributed rate limiting",
    )


@lru_cache
def get_rate_limiter_settings() -> RateLimiterSettings:
    """
    Get cached rate limiter settings instance.

    Returns:
        RateLimiterSettings: Cached settings instance
    """
    return RateLimiterSettings()
