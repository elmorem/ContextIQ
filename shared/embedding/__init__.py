"""
Embedding service for ContextIQ.

This module provides embedding generation capabilities for converting
text memories into vector representations for similarity search.
"""

from shared.embedding.config import EmbeddingSettings, get_embedding_settings
from shared.embedding.service import EmbeddingService

__all__ = [
    "EmbeddingSettings",
    "get_embedding_settings",
    "EmbeddingService",
]
