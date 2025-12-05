"""
Response schemas for sessions API.

Defines Pydantic models for API response serialization.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    """Response model for session data."""

    id: UUID = Field(..., description="Session ID")
    scope: dict = Field(..., description="Session scope")
    title: str | None = Field(None, description="Session title")
    description: str | None = Field(None, description="Session description")
    state: dict = Field(..., description="Current session state")
    started_at: datetime = Field(..., description="Session start timestamp")
    last_activity_at: datetime = Field(..., description="Last activity timestamp")
    ended_at: datetime | None = Field(None, description="Session end timestamp")
    ttl: int | None = Field(None, description="Time to live in seconds")
    event_count: int = Field(..., description="Number of events in session")
    total_input_tokens: int = Field(..., description="Total input tokens used")
    total_output_tokens: int = Field(..., description="Total output tokens used")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "scope": {"user_id": "user_123"},
                "title": "Debugging Session",
                "description": "Working on auth bug",
                "state": {"step": 2, "file": "auth.py"},
                "started_at": "2024-12-05T10:00:00Z",
                "last_activity_at": "2024-12-05T10:15:00Z",
                "ended_at": None,
                "ttl": 3600,
                "event_count": 5,
                "total_input_tokens": 150,
                "total_output_tokens": 300,
            }
        },
    }


class EventResponse(BaseModel):
    """Response model for event data."""

    id: UUID = Field(..., description="Event ID")
    session_id: UUID = Field(..., description="Parent session ID")
    event_type: str = Field(..., description="Event type")
    data: dict = Field(..., description="Event data payload")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    timestamp: datetime = Field(..., description="Event timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "event_type": "user_message",
                "data": {"content": "How do I fix this?"},
                "input_tokens": 15,
                "output_tokens": 0,
                "timestamp": "2024-12-05T10:00:00Z",
            }
        },
    }


class SessionListResponse(BaseModel):
    """Response model for list of sessions."""

    sessions: list[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")

    model_config = {
        "json_schema_extra": {"example": {"sessions": [], "total": 0, "limit": 100, "offset": 0}}
    }


class EventListResponse(BaseModel):
    """Response model for list of events."""

    events: list[EventResponse] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")

    model_config = {
        "json_schema_extra": {"example": {"events": [], "total": 0, "limit": 100, "offset": 0}}
    }


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Success message")

    model_config = {
        "json_schema_extra": {
            "example": {"success": True, "message": "Session deleted successfully"}
        }
    }
