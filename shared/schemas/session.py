"""
Session and Event Pydantic schemas for API.
"""

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseSchema, TimestampSchema


class EventCreate(BaseSchema):
    """Schema for creating an event."""

    event_type: str = Field(..., description="Type of event", max_length=100)
    data: dict = Field(..., description="Event data payload")
    input_tokens: int = Field(0, ge=0, description="Number of input tokens")
    output_tokens: int = Field(0, ge=0, description="Number of output tokens")
    timestamp: datetime | None = Field(None, description="Event timestamp (defaults to now)")


class EventSchema(TimestampSchema):
    """Schema for event response."""

    id: uuid.UUID = Field(..., description="Event unique identifier")
    session_id: uuid.UUID = Field(..., description="Parent session ID")
    event_type: str = Field(..., description="Type of event")
    data: dict = Field(..., description="Event data payload")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    timestamp: datetime = Field(..., description="Event timestamp")


class SessionCreate(BaseSchema):
    """Schema for creating a session."""

    scope: dict[str, str] = Field(
        ...,
        description="Session scope for isolation (max 5 key-value pairs)",
        max_length=5,
    )
    title: str | None = Field(None, description="Session title", max_length=500)
    description: str | None = Field(None, description="Session description")
    state: dict = Field(default_factory=dict, description="Initial session state")
    ttl: int | None = Field(None, ge=0, description="Time to live in seconds")


class SessionUpdate(BaseSchema):
    """Schema for updating a session."""

    title: str | None = Field(None, description="Session title", max_length=500)
    description: str | None = Field(None, description="Session description")
    state: dict | None = Field(None, description="Updated session state")
    ttl: int | None = Field(None, ge=0, description="Time to live in seconds")


class SessionSchema(TimestampSchema):
    """Schema for session response."""

    id: uuid.UUID = Field(..., description="Session unique identifier")
    scope: dict[str, str] = Field(..., description="Session scope")
    title: str | None = Field(None, description="Session title")
    description: str | None = Field(None, description="Session description")
    state: dict = Field(..., description="Current session state")
    event_count: int = Field(..., description="Number of events in session")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")
    started_at: datetime = Field(..., description="Session start time")
    last_activity_at: datetime = Field(..., description="Last activity timestamp")
    ended_at: datetime | None = Field(None, description="Session end time")
    ttl: int | None = Field(None, description="Time to live in seconds")


class SessionWithEvents(SessionSchema):
    """Schema for session with events included."""

    events: list[EventSchema] = Field(..., description="Session events")
