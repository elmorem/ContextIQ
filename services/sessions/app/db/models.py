"""
Database models for sessions service.

This module re-exports shared models and adds service-specific model logic.
"""

from shared.models.session import Event, Session

__all__ = ["Session", "Event"]
