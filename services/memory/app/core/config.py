"""
Configuration for memory service.

Manages service settings using Pydantic Settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryServiceSettings(BaseSettings):
    """Settings for the memory service."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service info
    service_name: str = Field("memory", description="Service name")
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
        "redis://localhost:6379/1",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(50, ge=1, description="Maximum Redis connections")
    redis_decode_responses: bool = Field(True, description="Decode responses to strings")
    redis_socket_timeout: float = Field(5.0, ge=0, description="Socket timeout in seconds")

    # Memory defaults
    default_confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Default confidence for new memories",
    )
    default_importance: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Default importance for new memories",
    )
    confidence_decay_rate: float = Field(
        0.1,
        ge=0.0,
        le=1.0,
        description="Rate at which confidence decays on updates",
    )
    min_confidence_threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence before memory is flagged",
    )

    # Memory expiration
    default_memory_ttl_days: int = Field(
        365,
        ge=1,
        description="Default TTL for memories in days (1 year)",
    )
    max_memory_ttl_days: int = Field(
        730,
        ge=1,
        description="Maximum TTL for memories in days (2 years)",
    )
    memory_cleanup_batch_size: int = Field(
        100,
        ge=1,
        description="Batch size for memory cleanup",
    )

    # Revision settings
    max_revisions_per_memory: int = Field(
        50,
        ge=1,
        description="Maximum number of revisions to keep per memory",
    )
    enable_revision_tracking: bool = Field(
        True,
        description="Enable revision tracking for memory updates",
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


def get_settings() -> MemoryServiceSettings:
    """
    Get service settings singleton.

    Returns:
        Configured settings instance
    """
    return MemoryServiceSettings()
