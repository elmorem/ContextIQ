"""
Configuration settings for Redis cache.

Defines connection settings and cache behavior.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisCacheSettings(BaseSettings):
    """Settings for Redis cache."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REDIS_",
        case_sensitive=False,
    )

    # Connection settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    redis_host: str = Field(
        default="localhost",
        description="Redis host",
    )

    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis port",
    )

    redis_db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database number",
    )

    redis_password: str | None = Field(
        default=None,
        description="Redis password",
    )

    # Connection pool settings
    max_connections: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of connections in pool",
    )

    socket_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Socket timeout in seconds",
    )

    socket_connect_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Socket connect timeout in seconds",
    )

    # Cache behavior settings
    default_ttl: int = Field(
        default=3600,
        ge=0,
        description="Default TTL for cache entries in seconds (0 = no expiration)",
    )

    session_ttl: int = Field(
        default=86400,  # 24 hours
        ge=0,
        description="TTL for session cache entries in seconds",
    )

    memory_ttl: int = Field(
        default=7200,  # 2 hours
        ge=0,
        description="TTL for memory cache entries in seconds",
    )

    job_ttl: int = Field(
        default=3600,  # 1 hour
        ge=0,
        description="TTL for job status cache entries in seconds",
    )

    # Feature flags
    decode_responses: bool = Field(
        default=True,
        description="Decode Redis responses to strings",
    )

    enable_cache: bool = Field(
        default=True,
        description="Enable caching (useful for disabling in tests)",
    )

    @property
    def connection_url(self) -> str:
        """
        Build Redis connection URL from components.

        Returns:
            Redis connection URL
        """
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_effective_url(self) -> str:
        """
        Get the effective Redis URL (prefer redis_url if set, otherwise build from components).

        Returns:
            Redis connection URL
        """
        if self.redis_url and self.redis_url != "redis://localhost:6379/0":
            return self.redis_url
        return self.connection_url


@lru_cache
def get_redis_cache_settings() -> RedisCacheSettings:
    """
    Get cached Redis cache settings instance.

    Returns:
        RedisCacheSettings: Cached settings instance
    """
    return RedisCacheSettings()
