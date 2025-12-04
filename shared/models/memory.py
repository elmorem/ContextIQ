"""
Memory database models.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base, TimestampMixin


class Memory(Base, TimestampMixin):
    """Memory model for storing declarative memories (facts and preferences)."""

    __tablename__ = "memories"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Scope for isolation (e.g., {"user_id": "123", "agent_id": "abc"})
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Memory content
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    # Vector embedding for similarity search (1536 dimensions for OpenAI embeddings)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Memory metadata
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Provenance tracking
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "extracted", "consolidated", "direct"
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Time to live (timestamp when memory expires)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    revisions: Mapped[list["MemoryRevision"]] = relationship(
        "MemoryRevision", back_populates="memory", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_memories_scope", "scope", postgresql_using="gin"),
        Index("idx_memories_expires_at", "expires_at"),
        Index("idx_memories_deleted_at", "deleted_at"),
        Index("idx_memories_embedding", "embedding", postgresql_using="ivfflat"),
    )

    def __repr__(self) -> str:
        return f"<Memory(id={self.id}, topic={self.topic})>"


class MemoryRevision(Base, TimestampMixin):
    """Memory revision history for tracking changes."""

    __tablename__ = "memory_revisions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Foreign keys
    memory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Revision data
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_fact: Mapped[str] = mapped_column(Text, nullable=False)
    new_fact: Mapped[str] = mapped_column(Text, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    memory: Mapped["Memory"] = relationship("Memory", back_populates="revisions")

    # Indexes
    __table_args__ = (Index("idx_memory_revisions_memory_id", "memory_id", "revision_number"),)

    def __repr__(self) -> str:
        return f"<MemoryRevision(id={self.id}, memory_id={self.memory_id}, rev={self.revision_number})>"


class ProceduralMemory(Base, TimestampMixin):
    """Procedural memory model for storing agent workflows, skills, and patterns."""

    __tablename__ = "procedural_memories"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Scope for isolation
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Memory type (workflow, skill, pattern, tool_usage)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Memory content
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured data (workflow steps, skill code, pattern template, etc.)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Vector embedding for similarity search
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Effectiveness metrics
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_execution_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Validation
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Time to live
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    executions: Mapped[list["ProceduralMemoryExecution"]] = relationship(
        "ProceduralMemoryExecution",
        back_populates="procedural_memory",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_procedural_memories_scope", "scope", postgresql_using="gin"),
        Index("idx_procedural_memories_type_name", "memory_type", "name"),
        Index("idx_procedural_memories_embedding", "embedding", postgresql_using="ivfflat"),
        Index("idx_procedural_memories_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<ProceduralMemory(id={self.id}, type={self.memory_type}, name={self.name})>"


class ProceduralMemoryExecution(Base, TimestampMixin):
    """Track execution history of procedural memories."""

    __tablename__ = "procedural_memory_executions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Foreign keys
    procedural_memory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("procedural_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution details
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    execution_time: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Context
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamp
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relationships
    procedural_memory: Mapped["ProceduralMemory"] = relationship(
        "ProceduralMemory", back_populates="executions"
    )

    # Indexes
    __table_args__ = (
        Index("idx_pm_executions_memory_time", "procedural_memory_id", "executed_at"),
        Index("idx_pm_executions_success", "success"),
    )

    def __repr__(self) -> str:
        return f"<ProceduralMemoryExecution(id={self.id}, success={self.success})>"
