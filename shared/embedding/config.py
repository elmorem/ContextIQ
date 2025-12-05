"""
Configuration for embedding service.

Settings for OpenAI API integration and embedding generation parameters.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    """Settings for embedding generation service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI API Configuration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for embeddings",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model to use",
    )
    openai_embedding_dimensions: int = Field(
        default=1536,
        ge=256,
        le=3072,
        description="Embedding vector dimensions",
    )
    openai_timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for API requests in seconds",
    )
    openai_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests",
    )

    # Batch Processing Configuration
    embedding_batch_size: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Number of texts to embed in a single batch",
    )
    embedding_max_input_length: int = Field(
        default=8191,
        ge=1,
        le=8191,
        description="Maximum input token length for embeddings",
    )


@lru_cache
def get_embedding_settings() -> EmbeddingSettings:
    """
    Get cached embedding settings instance.

    Returns:
        Cached EmbeddingSettings instance
    """
    return EmbeddingSettings()  # type: ignore[call-arg]
