"""
Session database models.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base, TimestampMixin


class Session(Base, TimestampMixin):
    """Session model for managing conversation contexts."""

    __tablename__ = "sessions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Scope for isolation (e.g., {"user_id": "123", "agent_id": "abc"})
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Session metadata
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Current state (stored as JSON)
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Session metrics
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Session timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Time to live (seconds until session expires)
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="session", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_sessions_scope", "scope", postgresql_using="gin"),
        Index("idx_sessions_last_activity", "last_activity_at"),
        Index("idx_sessions_ended_at", "ended_at"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, scope={self.scope})>"


class Event(Base, TimestampMixin):
    """Event model for session history."""

    __tablename__ = "events"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Foreign keys
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Event data
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Token usage
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Event metadata
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="events")

    # Indexes
    __table_args__ = (
        Index("idx_events_session_timestamp", "session_id", "timestamp"),
        Index("idx_events_type", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, session_id={self.session_id}, type={self.event_type})>"
