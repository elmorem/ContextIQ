"""
SQLAlchemy models for memory service.

Defines models for episodic memory storage with vector embeddings and revision tracking.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Relationships
    revisions: Mapped[list["MemoryRevision"]] = relationship(
        "MemoryRevision",
        back_populates="memory",
        cascade="all, delete-orphan",
        order_by="MemoryRevision.revision_number.desc()",
    )

    def __repr__(self) -> str:
        """String representation of Memory."""
        return f"<Memory(id={self.id}, topic={self.topic}, fact={self.fact[:50]}...)>"


class MemoryRevision(Base):
    """Model for tracking memory revision history."""

    __tablename__ = "memory_revisions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    memory_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent memory",
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential revision number for this memory",
    )
    previous_fact: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The fact before this revision",
    )
    new_fact: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The fact after this revision",
    )
    change_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional reason for the change",
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

    # Relationships
    memory: Mapped["Memory"] = relationship("Memory", back_populates="revisions")

    def __repr__(self) -> str:
        """String representation of MemoryRevision."""
        return f"<MemoryRevision(id={self.id}, memory_id={self.memory_id}, revision={self.revision_number})>"
