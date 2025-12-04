"""
Extraction job database models.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base, TimestampMixin


class ExtractionJob(Base, TimestampMixin):
    """Extraction job model for tracking memory extraction from sessions."""

    __tablename__ = "extraction_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Reference to session
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    # Scope from session
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Job status: "pending", "processing", "completed", "failed"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    # Input data (events to extract from)
    input_events: Mapped[list] = mapped_column(JSON, nullable=False)

    # Output data (extracted memories)
    extracted_memories: Mapped[list | None] = mapped_column(JSON, nullable=True)
    memory_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # LLM metadata
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_extraction_jobs_scope", "scope", postgresql_using="gin"),
        Index("idx_extraction_jobs_status", "status"),
        Index("idx_extraction_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ExtractionJob(id={self.id}, session_id={self.session_id}, status={self.status})>"


class ConsolidationJob(Base, TimestampMixin):
    """Consolidation job model for merging and deduplicating memories."""

    __tablename__ = "consolidation_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )

    # Scope for memories to consolidate
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Job status: "pending", "processing", "completed", "failed"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    # Input data (memories to consolidate)
    input_memory_ids: Mapped[list] = mapped_column(JSON, nullable=False)

    # Output data (consolidated memories)
    output_memory_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    memories_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    memories_merged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    memories_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # LLM metadata
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_consolidation_jobs_scope", "scope", postgresql_using="gin"),
        Index("idx_consolidation_jobs_status", "status"),
        Index("idx_consolidation_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsolidationJob(id={self.id}, status={self.status}, merged={self.memories_merged})>"
        )
