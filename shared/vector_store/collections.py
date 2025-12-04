"""
Qdrant collection configuration utilities.

This module provides configuration for Qdrant collections used by ContextIQ,
including collection schemas, distance metrics, and indexing parameters.
"""

from dataclasses import dataclass
from enum import Enum


class DistanceMetric(str, Enum):
    """Distance metrics for vector similarity."""

    COSINE = "Cosine"
    EUCLIDEAN = "Euclid"
    DOT = "Dot"


@dataclass
class CollectionConfig:
    """Configuration for a Qdrant collection."""

    name: str
    vector_size: int
    distance: DistanceMetric
    on_disk: bool = False
    hnsw_config: dict | None = None
    optimizers_config: dict | None = None

    def to_dict(self) -> dict:
        """Convert configuration to dictionary format for Qdrant API."""
        config = {
            "vectors": {
                "size": self.vector_size,
                "distance": self.distance.value,
                "on_disk": self.on_disk,
            }
        }

        if self.hnsw_config:
            config["hnsw_config"] = self.hnsw_config

        if self.optimizers_config:
            config["optimizers_config"] = self.optimizers_config

        return config


def get_memory_collection_config() -> CollectionConfig:
    """
    Get configuration for the memories collection.

    Uses OpenAI text-embedding-ada-002 dimensions (1536).
    Cosine similarity for semantic search.

    Returns:
        CollectionConfig for memories collection
    """
    return CollectionConfig(
        name="memories",
        vector_size=1536,  # OpenAI ada-002 embedding size
        distance=DistanceMetric.COSINE,
        on_disk=False,  # Keep in memory for faster search
        hnsw_config={
            "m": 16,  # Number of edges per node in the graph
            "ef_construct": 100,  # Size of dynamic candidate list for construction
            "full_scan_threshold": 10000,  # Switch to exact search for small collections
        },
        optimizers_config={
            "indexing_threshold": 20000,  # Start indexing after this many vectors
        },
    )


def get_collection_configs() -> list[CollectionConfig]:
    """
    Get all collection configurations for ContextIQ.

    Returns:
        List of CollectionConfig objects
    """
    return [
        get_memory_collection_config(),
    ]
