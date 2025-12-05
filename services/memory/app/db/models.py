"""
SQLAlchemy models for memory service.

Defines the Memory model for episodic memory storage with vector embeddings.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base


class Memory(Base):
    """Model for storing episodic memories with embeddings."""

    __tablename__ = "memories"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    scope: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        index=True,
        comment="User/session scope for memory isolation",
    )
    fact: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The memory fact or statement",
    )
    topic: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
        comment="Topic category for memory",
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float),
        nullable=True,
        comment="Vector embedding for similarity search",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
        comment="Confidence score for memory accuracy",
    )
    importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default="0.5",
        comment="Importance score for memory prioritization",
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of times memory was accessed",
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time memory was accessed",
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Source of memory (conversation, extraction, manual)",
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        comment="ID of source (e.g., session_id, event_id)",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When memory should be removed",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft delete timestamp",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """String representation of Memory."""
        return f"<Memory(id={self.id}, topic={self.topic}, fact={self.fact[:50]}...)>"
