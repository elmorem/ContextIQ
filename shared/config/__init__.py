"""
Configuration management.
"""

from shared.config.logging import setup_logging
from shared.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "setup_logging"]
