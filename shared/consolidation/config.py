"""
Configuration settings for consolidation engine.

Defines settings for similarity detection, merging strategies,
and conflict resolution policies.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConsolidationSettings(BaseSettings):
    """Settings for memory consolidation engine."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONSOLIDATION_",
        case_sensitive=False,
    )

    # Similarity detection
    similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for considering memories as duplicates",
    )

    # Merging strategy
    merge_strategy: str = Field(
        default="highest_confidence",
        description="Strategy for merging duplicate memories: "
        "'highest_confidence', 'most_recent', 'longest', 'manual'",
    )

    # Conflict detection
    conflict_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for detecting conflicting memories",
    )

    # Batch processing
    consolidation_batch_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of memories to consolidate in one batch",
    )

    # Confidence adjustments
    merged_confidence_boost: float = Field(
        default=0.05,
        ge=0.0,
        le=0.2,
        description="Confidence boost for merged memories (multiple sources)",
    )

    conflicting_confidence_penalty: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Confidence penalty for memories with detected conflicts",
    )

    # Retention policy
    keep_superseded_memories: bool = Field(
        default=True,
        description="Whether to keep superseded memories in revision history",
    )

    max_merge_candidates: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of similar memories to consider for merging",
    )


@lru_cache
def get_consolidation_settings() -> ConsolidationSettings:
    """
    Get cached consolidation settings instance.

    Returns:
        ConsolidationSettings: Cached settings instance
    """
    return ConsolidationSettings()
