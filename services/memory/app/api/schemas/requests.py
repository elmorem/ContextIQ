"""
Request schemas for memory API.

Defines Pydantic models for API request validation.
"""

from pydantic import BaseModel, Field


class CreateMemoryRequest(BaseModel):
    """Request model for creating a new memory."""

    scope: dict = Field(..., description="Memory scope for isolation (e.g., {'user_id': '123'})")
    fact: str = Field(..., description="The memory fact or statement", min_length=1)
    source_type: str = Field(
        ..., description="Source of memory (conversation, extraction, manual)", max_length=50
    )
    topic: str | None = Field(None, description="Optional topic category", max_length=200)
    embedding: list[float] | None = Field(None, description="Optional vector embedding")
    confidence: float | None = Field(None, description="Confidence score (0-1)", ge=0.0, le=1.0)
    importance: float | None = Field(None, description="Importance score (0-1)", ge=0.0, le=1.0)
    source_id: str | None = Field(None, description="Optional source ID reference")
    ttl_days: int | None = Field(None, description="Time to live in days", gt=0, le=730)

    model_config = {
        "json_schema_extra": {
            "example": {
                "scope": {"user_id": "user_123", "org_id": "org_456"},
                "fact": "User prefers dark mode for coding",
                "source_type": "conversation",
                "topic": "preferences",
                "confidence": 0.9,
                "importance": 0.7,
                "ttl_days": 365,
            }
        }
    }


class UpdateMemoryRequest(BaseModel):
    """Request model for updating a memory."""

    fact: str | None = Field(None, description="Updated fact", min_length=1)
    topic: str | None = Field(None, description="Updated topic", max_length=200)
    embedding: list[float] | None = Field(None, description="Updated embedding")
    confidence: float | None = Field(None, description="Updated confidence (0-1)", ge=0.0, le=1.0)
    importance: float | None = Field(None, description="Updated importance (0-1)", ge=0.0, le=1.0)
    change_reason: str | None = Field(None, description="Reason for the change")

    model_config = {
        "json_schema_extra": {
            "example": {
                "fact": "User prefers light mode for coding",
                "confidence": 0.95,
                "change_reason": "User corrected their preference",
            }
        }
    }


class ListMemoriesQuery(BaseModel):
    """Query parameters for listing memories."""

    limit: int = Field(100, description="Maximum number of memories to return", ge=1, le=1000)
    offset: int = Field(0, description="Number of memories to skip", ge=0)
    topic: str | None = Field(None, description="Filter by topic")
    include_deleted: bool = Field(False, description="Include soft-deleted memories")

    model_config = {
        "json_schema_extra": {"example": {"limit": 50, "offset": 0, "topic": "preferences"}}
    }
