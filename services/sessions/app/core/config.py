"""
Configuration for sessions service.

Manages service settings using Pydantic Settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SessionsServiceSettings(BaseSettings):
    """Settings for the sessions service."""

    model_config = SettingsConfigDict(
        env_prefix="SESSIONS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service info
    service_name: str = Field("sessions", description="Service name")
    service_version: str = Field("0.1.0", description="Service version")
    environment: str = Field("development", description="Environment")
    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")

    # Database configuration
    database_url: str = Field(
        "postgresql+asyncpg://contextiq_user:contextiq_pass@localhost:5432/contextiq",
        description="Database connection URL",
    )
    database_pool_size: int = Field(5, ge=1, description="Database connection pool size")
    database_max_overflow: int = Field(10, ge=0, description="Max overflow connections")
    database_pool_timeout: float = Field(30.0, ge=0, description="Pool timeout in seconds")
    database_pool_recycle: int = Field(3600, ge=0, description="Pool recycle time in seconds")
    database_echo: bool = Field(False, description="Echo SQL statements")

    # Redis configuration
    redis_url: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(50, ge=1, description="Maximum Redis connections")
    redis_decode_responses: bool = Field(True, description="Decode responses to strings")
    redis_socket_timeout: float = Field(5.0, ge=0, description="Socket timeout in seconds")

    # Session defaults
    default_session_ttl: int = Field(
        3600,
        ge=60,
        description="Default TTL for sessions in seconds (1 hour)",
    )
    max_session_ttl: int = Field(
        86400,
        ge=3600,
        description="Maximum TTL for sessions in seconds (24 hours)",
    )
    session_cleanup_batch_size: int = Field(
        100,
        ge=1,
        description="Batch size for session cleanup",
    )
    session_cleanup_days: int = Field(
        30,
        ge=1,
        description="Delete sessions older than this many days",
    )

    # Cache configuration
    enable_cache: bool = Field(True, description="Enable caching")
    cache_ttl: int = Field(300, ge=0, description="Cache TTL in seconds (5 minutes)")
    cache_max_size: int = Field(1000, ge=1, description="Maximum cache size")

    @property
    def database_settings(self) -> dict:
        """Get database connection settings."""
        return {
            "url": self.database_url,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "pool_timeout": self.database_pool_timeout,
            "pool_recycle": self.database_pool_recycle,
            "echo": self.database_echo,
        }

    @property
    def redis_settings(self) -> dict:
        """Get Redis connection settings."""
        return {
            "url": self.redis_url,
            "max_connections": self.redis_max_connections,
            "decode_responses": self.redis_decode_responses,
            "socket_timeout": self.redis_socket_timeout,
        }


def get_settings() -> SessionsServiceSettings:
    """
    Get service settings singleton.

    Returns:
        Configured settings instance
    """
    return SessionsServiceSettings()
