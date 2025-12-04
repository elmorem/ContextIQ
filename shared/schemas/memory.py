"""
Memory Pydantic schemas for API.
"""

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas.base import BaseSchema, TimestampSchema

# Declarative Memory Schemas


class MemoryCreate(BaseSchema):
    """Schema for creating a memory."""

    scope: dict[str, str] = Field(
        ..., description="Memory scope (max 5 key-value pairs)", max_length=5
    )
    fact: str = Field(..., description="Memory fact in first person", min_length=1)
    topic: str | None = Field(None, description="Memory topic/category", max_length=200)
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")
    source_type: str = Field(
        "direct", description="Source type: extracted, consolidated, or direct", max_length=50
    )
    source_id: uuid.UUID | None = Field(None, description="Source entity ID")
    expires_at: datetime | None = Field(None, description="Memory expiration time")


class MemoryUpdate(BaseSchema):
    """Schema for updating a memory."""

    fact: str | None = Field(None, description="Updated memory fact", min_length=1)
    topic: str | None = Field(None, description="Updated topic", max_length=200)
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Updated confidence")
    importance: float | None = Field(None, ge=0.0, le=1.0, description="Updated importance")
    expires_at: datetime | None = Field(None, description="Updated expiration time")


class MemorySchema(TimestampSchema):
    """Schema for memory response."""

    id: uuid.UUID = Field(..., description="Memory unique identifier")
    scope: dict[str, str] = Field(..., description="Memory scope")
    fact: str = Field(..., description="Memory fact")
    topic: str | None = Field(None, description="Memory topic")
    confidence: float = Field(..., description="Confidence score")
    importance: float = Field(..., description="Importance score")
    access_count: int = Field(..., description="Number of times accessed")
    last_accessed_at: datetime | None = Field(None, description="Last access timestamp")
    source_type: str = Field(..., description="Source type")
    source_id: uuid.UUID | None = Field(None, description="Source entity ID")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp")


class MemoryRevisionSchema(TimestampSchema):
    """Schema for memory revision."""

    id: uuid.UUID = Field(..., description="Revision unique identifier")
    memory_id: uuid.UUID = Field(..., description="Parent memory ID")
    revision_number: int = Field(..., description="Revision number")
    previous_fact: str = Field(..., description="Previous fact value")
    new_fact: str = Field(..., description="New fact value")
    change_reason: str | None = Field(None, description="Reason for change")


# Procedural Memory Schemas


class ProceduralMemoryCreate(BaseSchema):
    """Schema for creating a procedural memory."""

    scope: dict[str, str] = Field(..., description="Memory scope", max_length=5)
    memory_type: str = Field(
        ..., description="Type: workflow, skill, pattern, tool_usage", max_length=50
    )
    name: str = Field(..., description="Memory name", max_length=200)
    description: str | None = Field(None, description="Memory description")
    content: dict = Field(..., description="Structured content (steps, code, template)")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")


class ProceduralMemoryUpdate(BaseSchema):
    """Schema for updating a procedural memory."""

    name: str | None = Field(None, description="Updated name", max_length=200)
    description: str | None = Field(None, description="Updated description")
    content: dict | None = Field(None, description="Updated content")
    expires_at: datetime | None = Field(None, description="Updated expiration")
    is_validated: bool | None = Field(None, description="Validation status")


class ProceduralMemorySchema(TimestampSchema):
    """Schema for procedural memory response."""

    id: uuid.UUID = Field(..., description="Memory unique identifier")
    scope: dict[str, str] = Field(..., description="Memory scope")
    memory_type: str = Field(..., description="Memory type")
    name: str = Field(..., description="Memory name")
    description: str | None = Field(None, description="Memory description")
    content: dict = Field(..., description="Structured content")
    success_count: int = Field(..., description="Number of successful executions")
    failure_count: int = Field(..., description="Number of failed executions")
    avg_execution_time: float | None = Field(None, description="Average execution time")
    usage_count: int = Field(..., description="Number of times used")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")
    is_validated: bool = Field(..., description="Whether memory is validated")
    validated_at: datetime | None = Field(None, description="Validation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp")


class ProceduralMemoryExecutionSchema(TimestampSchema):
    """Schema for procedural memory execution."""

    id: uuid.UUID = Field(..., description="Execution unique identifier")
    procedural_memory_id: uuid.UUID = Field(..., description="Parent memory ID")
    success: bool = Field(..., description="Execution success status")
    execution_time: float = Field(..., description="Execution time in seconds")
    error_message: str | None = Field(None, description="Error message if failed")
    input_data: dict = Field(..., description="Input data for execution")
    output_data: dict | None = Field(None, description="Output data from execution")
    executed_at: datetime = Field(..., description="Execution timestamp")


# Extraction and Consolidation Job Schemas


class ExtractionJobSchema(TimestampSchema):
    """Schema for extraction job."""

    id: uuid.UUID = Field(..., description="Job unique identifier")
    session_id: uuid.UUID = Field(..., description="Session ID")
    scope: dict[str, str] = Field(..., description="Job scope")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    input_events: list = Field(..., description="Input events for extraction")
    extracted_memories: list | None = Field(None, description="Extracted memories")
    memory_count: int = Field(..., description="Number of memories extracted")
    error_message: str | None = Field(None, description="Error message if failed")
    retry_count: int = Field(..., description="Number of retries")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    model_used: str | None = Field(None, description="LLM model used")
    input_tokens: int = Field(..., description="Input tokens used")
    output_tokens: int = Field(..., description="Output tokens used")


class ConsolidationJobSchema(TimestampSchema):
    """Schema for consolidation job."""

    id: uuid.UUID = Field(..., description="Job unique identifier")
    scope: dict[str, str] = Field(..., description="Job scope")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    input_memory_ids: list = Field(..., description="Input memory IDs")
    output_memory_ids: list | None = Field(None, description="Output memory IDs")
    memories_processed: int = Field(..., description="Number of memories processed")
    memories_merged: int = Field(..., description="Number of memories merged")
    memories_deleted: int = Field(..., description="Number of memories deleted")
    error_message: str | None = Field(None, description="Error message if failed")
    retry_count: int = Field(..., description="Number of retries")
    started_at: datetime | None = Field(None, description="Job start time")
    completed_at: datetime | None = Field(None, description="Job completion time")
    model_used: str | None = Field(None, description="LLM model used")
    input_tokens: int = Field(..., description="Input tokens used")
    output_tokens: int = Field(..., description="Output tokens used")
