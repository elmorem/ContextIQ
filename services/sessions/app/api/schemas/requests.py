"""
Request schemas for sessions API.

Defines Pydantic models for API request validation.
"""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session."""

    scope: dict = Field(..., description="Session scope for isolation (e.g., {'user_id': '123'})")
    title: str | None = Field(None, description="Optional session title", max_length=500)
    description: str | None = Field(None, description="Optional session description")
    state: dict | None = Field(None, description="Initial session state")
    ttl: int | None = Field(
        None,
        description="Time to live in seconds",
        gt=0,
        le=86400,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scope": {"user_id": "user_123", "org_id": "org_456"},
                "title": "Debugging Session",
                "description": "Working on authentication bug",
                "state": {"step": 1},
                "ttl": 3600,
            }
        }
    }


class UpdateSessionStateRequest(BaseModel):
    """Request model for updating session state."""

    state: dict = Field(..., description="New session state")
    merge: bool = Field(
        False,
        description="If True, merge with existing state; if False, replace",
    )

    model_config = {
        "json_schema_extra": {
            "example": {"state": {"current_file": "auth.py", "line_number": 42}, "merge": True}
        }
    }


class CreateEventRequest(BaseModel):
    """Request model for creating an event."""

    event_type: str = Field(..., description="Type of event", max_length=100)
    data: dict = Field(..., description="Event data payload")
    input_tokens: int = Field(0, description="Number of input tokens", ge=0)
    output_tokens: int = Field(0, description="Number of output tokens", ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_type": "user_message",
                "data": {"content": "How do I fix this authentication bug?"},
                "input_tokens": 15,
                "output_tokens": 0,
            }
        }
    }


class ListSessionsQuery(BaseModel):
    """Query parameters for listing sessions."""

    limit: int = Field(100, description="Maximum number of sessions to return", ge=1, le=1000)
    offset: int = Field(0, description="Number of sessions to skip", ge=0)

    model_config = {"json_schema_extra": {"example": {"limit": 50, "offset": 0}}}


class ListEventsQuery(BaseModel):
    """Query parameters for listing events."""

    limit: int = Field(100, description="Maximum number of events to return", ge=1, le=1000)
    offset: int = Field(0, description="Number of events to skip", ge=0)
    event_type: str | None = Field(None, description="Filter by event type")

    model_config = {
        "json_schema_extra": {"example": {"limit": 100, "offset": 0, "event_type": "user_message"}}
    }
