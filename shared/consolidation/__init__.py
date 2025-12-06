"""
Consolidation engine for memory deduplication and merging.

This module provides functionality for detecting and merging similar memories,
resolving conflicts, and maintaining memory consistency.
"""

from shared.consolidation.config import ConsolidationSettings, get_consolidation_settings
from shared.consolidation.engine import ConsolidationEngine, ConsolidationResult

__all__ = [
    "ConsolidationEngine",
    "ConsolidationResult",
    "ConsolidationSettings",
    "get_consolidation_settings",
]
