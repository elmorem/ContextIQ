"""
Configuration for memory generation worker.

Settings for worker behavior, queue configuration, and processing parameters.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Settings for memory generation worker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Worker Configuration
    worker_name: str = Field(
        default="memory-generation-worker",
        description="Worker instance name for logging",
    )
    worker_concurrency: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of concurrent message handlers",
    )
    worker_prefetch_count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of messages to prefetch from queue",
    )

    # Queue Configuration
    memory_generation_queue: str = Field(
        default="memory.generation",
        description="Queue name for memory generation tasks",
    )
    memory_generation_exchange: str = Field(
        default="memory",
        description="Exchange for memory-related messages",
    )
    memory_generation_routing_key: str = Field(
        default="generation.request",
        description="Routing key for memory generation requests",
    )

    # Processing Configuration
    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed messages",
    )
    retry_delay_seconds: int = Field(
        default=5,
        ge=1,
        le=300,
        description="Delay in seconds before retrying failed message",
    )
    message_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Message time-to-live in seconds",
    )


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """
    Get cached worker settings instance.

    Returns:
        Cached WorkerSettings instance
    """
    return WorkerSettings()  # type: ignore[call-arg]
