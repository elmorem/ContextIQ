"""
Vector store utilities for ContextIQ.

This module provides utilities for managing vector storage with Qdrant,
including collection configuration and initialization.
"""

from shared.vector_store.collections import (
    CollectionConfig,
    get_collection_configs,
    get_memory_collection_config,
)
from shared.vector_store.config import QdrantSettings, get_qdrant_settings
from shared.vector_store.qdrant_client import QdrantClientWrapper

__all__ = [
    "CollectionConfig",
    "get_collection_configs",
    "get_memory_collection_config",
    "QdrantSettings",
    "get_qdrant_settings",
    "QdrantClientWrapper",
]
