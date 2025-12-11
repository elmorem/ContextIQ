"""
Response schemas for memory API.

Defines Pydantic models for API response serialization.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryResponse(BaseModel):
    """Response model for memory data."""

    id: UUID = Field(..., description="Memory ID")
    scope: dict = Field(..., description="Memory scope")
    fact: str = Field(..., description="The memory fact or statement")
    topic: str | None = Field(None, description="Topic category")
    embedding: list[float] | None = Field(None, description="Vector embedding")
    confidence: float = Field(..., description="Confidence score")
    importance: float = Field(..., description="Importance score")
    access_count: int = Field(..., description="Number of times accessed")
    last_accessed_at: datetime | None = Field(None, description="Last access timestamp")
    source_type: str = Field(..., description="Source of memory")
    source_id: UUID | None = Field(None, description="Source ID reference")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "scope": {"user_id": "user_123"},
                "fact": "User prefers dark mode for coding",
                "topic": "preferences",
                "embedding": None,
                "confidence": 0.9,
                "importance": 0.7,
                "access_count": 3,
                "last_accessed_at": "2024-12-05T10:15:00Z",
                "source_type": "conversation",
                "source_id": None,
                "expires_at": None,
                "deleted_at": None,
                "created_at": "2024-12-05T10:00:00Z",
                "updated_at": "2024-12-05T10:00:00Z",
            }
        },
    }


class MemoryListResponse(BaseModel):
    """Response model for list of memories."""

    memories: list[MemoryResponse] = Field(..., description="List of memories")
    total: int = Field(..., description="Total number of memories")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")

    model_config = {
        "json_schema_extra": {"example": {"memories": [], "total": 0, "limit": 100, "offset": 0}}
    }


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Success message")

    model_config = {
        "json_schema_extra": {
            "example": {"success": True, "message": "Memory deleted successfully"}
        }
    }


class RevisionResponse(BaseModel):
    """Response model for memory revision data."""

    id: UUID = Field(..., description="Revision ID")
    memory_id: UUID = Field(..., description="Parent memory ID")
    revision_number: int = Field(..., description="Sequential revision number")
    previous_fact: str = Field(..., description="Fact before this revision")
    new_fact: str = Field(..., description="Fact after this revision")
    change_reason: str | None = Field(None, description="Reason for the change")
    created_at: datetime = Field(..., description="When revision was created")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440000",
                "memory_id": "550e8400-e29b-41d4-a716-446655440000",
                "revision_number": 1,
                "previous_fact": "User prefers dark mode for coding",
                "new_fact": "User prefers light mode for coding",
                "change_reason": "User corrected their preference",
                "created_at": "2024-12-05T11:00:00Z",
                "updated_at": "2024-12-05T11:00:00Z",
            }
        },
    }


class RevisionListResponse(BaseModel):
    """Response model for list of revisions."""

    revisions: list[RevisionResponse] = Field(..., description="List of revisions")
    total: int = Field(..., description="Total number of revisions")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")

    model_config = {
        "json_schema_extra": {"example": {"revisions": [], "total": 0, "limit": 10, "offset": 0}}
    }


class MemorySearchResult(BaseModel):
    """Individual search result with memory and similarity score."""

    memory: MemoryResponse = Field(..., description="Memory data")
    similarity_score: float = Field(..., description="Similarity score (0-1, higher is better)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "memory": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "scope": {"user_id": "user_123"},
                    "fact": "User prefers dark mode for coding",
                    "topic": "preferences",
                    "confidence": 0.9,
                    "importance": 0.7,
                },
                "similarity_score": 0.92,
            }
        }
    }


class SearchMemoriesResponse(BaseModel):
    """Response model for memory search results."""

    results: list[MemorySearchResult] = Field(
        ..., description="Search results with similarity scores"
    )
    total: int = Field(..., description="Total number of results returned")
    limit: int = Field(..., description="Limit applied")

    model_config = {"json_schema_extra": {"example": {"results": [], "total": 0, "limit": 10}}}
