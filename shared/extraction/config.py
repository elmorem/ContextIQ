"""
Configuration for extraction engine.

Settings for LLM integration, extraction parameters, and API configurations.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionSettings(BaseSettings):
    """Settings for extraction engine and LLM integration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic API Configuration
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude models",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use for extraction",
    )
    anthropic_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=8192,
        description="Maximum tokens for LLM response",
    )
    anthropic_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for LLM sampling (0.0 = deterministic)",
    )
    anthropic_timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for API requests in seconds",
    )
    anthropic_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests",
    )

    # Extraction Configuration
    extraction_batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of events to process in a single extraction batch",
    )
    extraction_min_events: int = Field(
        default=3,
        ge=1,
        le=50,
        description="Minimum number of events required for extraction",
    )
    extraction_max_facts: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of facts to extract per batch",
    )

    # Few-shot Learning Configuration
    use_few_shot: bool = Field(
        default=True,
        description="Enable few-shot learning with examples",
    )
    max_few_shot_examples: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of few-shot examples to include",
    )


@lru_cache
def get_extraction_settings() -> ExtractionSettings:
    """
    Get cached extraction settings instance.

    Returns:
        Cached ExtractionSettings instance
    """
    return ExtractionSettings()  # type: ignore[call-arg]
