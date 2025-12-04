"""initial_schema

Revision ID: 001
Revises:
Create Date: 2025-12-04 13:12:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ttl", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sessions_scope", "sessions", ["scope"], postgresql_using="gin")
    op.create_index("idx_sessions_last_activity", "sessions", ["last_activity_at"])
    op.create_index("idx_sessions_ended_at", "sessions", ["ended_at"])

    # Create events table
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
        ),
    )
    op.create_index("idx_events_session_timestamp", "events", ["session_id", "timestamp"])
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("ix_events_session_id", "events", ["session_id"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])

    # Create memories table
    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_memories_scope", "memories", ["scope"], postgresql_using="gin")
    op.create_index("idx_memories_expires_at", "memories", ["expires_at"])
    op.create_index("idx_memories_deleted_at", "memories", ["deleted_at"])
    op.create_index("ix_memories_topic", "memories", ["topic"])

    # Create vector index using raw SQL for pgvector
    op.execute(
        "CREATE INDEX idx_memories_embedding ON memories "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # Create memory_revisions table
    op.create_table(
        "memory_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_fact", sa.Text(), nullable=False),
        sa.Column("new_fact", sa.Text(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_memory_revisions_memory_id", "memory_revisions", ["memory_id", "revision_number"]
    )
    op.create_index("ix_memory_revisions_memory_id", "memory_revisions", ["memory_id"])

    # Create procedural_memories table
    op.create_table(
        "procedural_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("memory_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_execution_time", sa.Float(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_procedural_memories_scope", "procedural_memories", ["scope"], postgresql_using="gin"
    )
    op.create_index(
        "idx_procedural_memories_type_name", "procedural_memories", ["memory_type", "name"]
    )
    op.create_index("idx_procedural_memories_deleted_at", "procedural_memories", ["deleted_at"])
    op.create_index("ix_procedural_memories_memory_type", "procedural_memories", ["memory_type"])

    # Create vector index for procedural memories
    op.execute(
        "CREATE INDEX idx_procedural_memories_embedding ON procedural_memories "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # Create procedural_memory_executions table
    op.create_table(
        "procedural_memory_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("procedural_memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("execution_time", sa.Float(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["procedural_memory_id"], ["procedural_memories.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_pm_executions_memory_time",
        "procedural_memory_executions",
        ["procedural_memory_id", "executed_at"],
    )
    op.create_index("idx_pm_executions_success", "procedural_memory_executions", ["success"])
    op.create_index(
        "ix_procedural_memory_executions_procedural_memory_id",
        "procedural_memory_executions",
        ["procedural_memory_id"],
    )
    op.create_index(
        "ix_procedural_memory_executions_executed_at",
        "procedural_memory_executions",
        ["executed_at"],
    )

    # Create extraction_jobs table
    op.create_table(
        "extraction_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("input_events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extracted_memories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("memory_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_extraction_jobs_scope", "extraction_jobs", ["scope"], postgresql_using="gin"
    )
    op.create_index("idx_extraction_jobs_status", "extraction_jobs", ["status"])
    op.create_index("idx_extraction_jobs_created_at", "extraction_jobs", ["created_at"])
    op.create_index("ix_extraction_jobs_session_id", "extraction_jobs", ["session_id"])

    # Create consolidation_jobs table
    op.create_table(
        "consolidation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("input_memory_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_memory_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("memories_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("memories_merged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("memories_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_consolidation_jobs_scope", "consolidation_jobs", ["scope"], postgresql_using="gin"
    )
    op.create_index("idx_consolidation_jobs_status", "consolidation_jobs", ["status"])
    op.create_index("idx_consolidation_jobs_created_at", "consolidation_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("consolidation_jobs")
    op.drop_table("extraction_jobs")
    op.drop_table("procedural_memory_executions")
    op.drop_table("procedural_memories")
    op.drop_table("memory_revisions")
    op.drop_table("memories")
    op.drop_table("events")
    op.drop_table("sessions")

    # Drop extensions
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
    op.execute("DROP EXTENSION IF EXISTS vector")
