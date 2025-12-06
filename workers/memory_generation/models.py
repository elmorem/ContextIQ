"""
Data models for memory generation worker.

Defines message formats and processing results for the memory generation pipeline.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryGenerationRequest(BaseModel):
    """Request to generate memories from session events."""

    session_id: UUID = Field(..., description="Session ID to process")
    user_id: UUID = Field(..., description="User ID who owns the session")
    scope: str = Field(default="user", description="Scope for memory (user/org/global)")
    min_events: int = Field(default=3, description="Minimum events required for extraction")
    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When generation was requested",
    )


class ExtractedMemory(BaseModel):
    """Memory extracted from conversation."""

    fact: str = Field(..., description="Atomic fact extracted")
    category: str = Field(..., description="Memory category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    source_context: str | None = Field(None, description="Source context")


class MemoryGenerationResult(BaseModel):
    """Result of memory generation processing."""

    session_id: UUID = Field(..., description="Session ID processed")
    user_id: UUID = Field(..., description="User ID")
    memories_extracted: int = Field(default=0, description="Number of memories extracted")
    memories_saved: int = Field(default=0, description="Number of memories saved")
    embeddings_generated: int = Field(default=0, description="Number of embeddings generated")
    success: bool = Field(default=False, description="Whether processing succeeded")
    error: str | None = Field(None, description="Error message if failed")
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When processing completed",
    )
