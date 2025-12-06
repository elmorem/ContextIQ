"""
Configuration settings for consolidation worker.

Defines worker configuration including queue names, batch sizes,
and consolidation scheduling.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConsolidationWorkerSettings(BaseSettings):
    """Settings for consolidation worker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONSOLIDATION_WORKER_",
        case_sensitive=False,
    )

    # Worker identification
    worker_name: str = Field(
        default="consolidation-worker",
        description="Name of the worker instance",
    )

    # Concurrency settings
    worker_concurrency: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of concurrent consolidation tasks",
    )

    worker_prefetch_count: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of messages to prefetch from queue",
    )

    # Queue configuration
    consolidation_queue: str = Field(
        default="memory.consolidation",
        description="RabbitMQ queue name for consolidation requests",
    )

    # Retry configuration
    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed consolidations",
    )

    retry_backoff_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Backoff time in seconds between retry attempts",
    )

    # Processing limits
    max_memories_per_batch: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum number of memories to consolidate in one batch",
    )

    consolidation_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Timeout for consolidation processing in seconds",
    )

    # Scheduling (for periodic consolidation)
    enable_periodic_consolidation: bool = Field(
        default=False,
        description="Enable periodic background consolidation",
    )

    consolidation_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Interval in hours for periodic consolidation",
    )


@lru_cache
def get_consolidation_worker_settings() -> ConsolidationWorkerSettings:
    """
    Get cached consolidation worker settings instance.

    Returns:
        ConsolidationWorkerSettings: Cached settings instance
    """
    return ConsolidationWorkerSettings()
