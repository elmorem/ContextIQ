"""
Extraction engine for ContextIQ.

This module provides extraction capabilities for generating memories from conversations,
including LLM integration, prompt templates, and extraction logic.
"""

from shared.extraction.config import ExtractionSettings, get_extraction_settings
from shared.extraction.engine import ExtractionEngine, ExtractionResult
from shared.extraction.llm_client import LLMClient

__all__ = [
    "ExtractionSettings",
    "get_extraction_settings",
    "ExtractionEngine",
    "ExtractionResult",
    "LLMClient",
]
