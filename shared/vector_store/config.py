"""
Qdrant configuration for ContextIQ.

This module provides configuration settings for the Qdrant vector database,
including connection parameters and retry logic.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class QdrantSettings(BaseSettings):
    """Qdrant connection and configuration settings."""

    # Connection settings
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL",
    )
    qdrant_api_key: str | None = Field(
        default=None,
        description="Qdrant API key for authentication (optional)",
    )
    qdrant_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300,
    )

    # Connection pool settings
    qdrant_grpc: bool = Field(
        default=False,
        description="Use gRPC for better performance (requires gRPC port)",
    )
    qdrant_grpc_port: int = Field(
        default=6334,
        description="Qdrant gRPC port",
    )
    qdrant_prefer_grpc: bool = Field(
        default=False,
        description="Prefer gRPC over HTTP when available",
    )

    # Retry settings
    qdrant_max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10,
    )
    qdrant_retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds",
        ge=0.1,
        le=10.0,
    )

    # Performance settings
    qdrant_batch_size: int = Field(
        default=100,
        description="Default batch size for bulk operations",
        ge=1,
        le=1000,
    )

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_qdrant_settings() -> QdrantSettings:
    """
    Get Qdrant settings instance.

    Returns:
        QdrantSettings instance with configuration loaded from environment
    """
    return QdrantSettings()
