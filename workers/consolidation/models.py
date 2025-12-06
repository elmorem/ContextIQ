"""
Data models for consolidation worker.

Defines message formats and processing results for the consolidation pipeline.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConsolidationRequest(BaseModel):
    """Request to consolidate memories for a scope."""

    scope: dict[str, str] = Field(..., description="Scope for consolidation (user/org/global)")
    user_id: UUID | None = Field(None, description="User ID (for user scope)")
    max_memories: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum memories to process",
    )
    detect_conflicts: bool = Field(
        default=True,
        description="Whether to detect conflicts during consolidation",
    )
    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When consolidation was requested",
    )


class ConsolidationResult(BaseModel):
    """Result of consolidation processing."""

    scope: dict[str, str] = Field(..., description="Scope that was consolidated")
    memories_processed: int = Field(default=0, description="Number of memories processed")
    memories_merged: int = Field(default=0, description="Number of memories merged")
    conflicts_detected: int = Field(default=0, description="Number of conflicts detected")
    memories_updated: int = Field(default=0, description="Number of memory records updated")
    success: bool = Field(default=False, description="Whether consolidation succeeded")
    error: str | None = Field(None, description="Error message if failed")
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When processing completed",
    )
