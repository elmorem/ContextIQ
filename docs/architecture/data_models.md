# ContextIQ Data Models & Database Schemas

## Document Overview

**Version**: 1.0
**Date**: December 4, 2025
**Status**: Design Phase

This document defines the complete data models, database schemas, and storage architecture for ContextIQ.

---

## 1. Database Architecture

### 1.1 Primary Database: PostgreSQL

**Version**: 15+

**Extensions Required**:
- `uuid-ossp`: UUID generation
- `pgcrypto`: Cryptographic functions
- `pg_trgm`: Trigram similarity for text search
- `btree_gin`: GIN indexes for composite queries
- **Optional**: `pgvector`: Vector storage (if not using separate vector store)

**Connection Pooling**: PgBouncer (max 100 connections per service)

### 1.2 Vector Store: Qdrant

**Purpose**: Store embeddings for similarity search

**Collections**:
- `memories`: Memory embeddings
- `workflows`: Procedural memory workflow embeddings
- `skills`: Skill embeddings

**Configuration**:
```yaml
collection_config:
  vector_size: 1536  # OpenAI text-embedding-3-large
  distance: Cosine
  hnsw_config:
    m: 16
    ef_construct: 100
```

### 1.3 Cache: Redis

**Purpose**: Fast access to hot data

**Data Structures**:
- Strings: Session cache, memory cache
- Hashes: Scope-based memory indexes
- Sets: Active session tracking
- Sorted Sets: Rate limiting

**TTL Strategy**:
- Sessions: 1 hour (sliding window)
- Memories: 30 minutes
- API rate limits: 1 minute

### 1.4 Object Storage: S3-Compatible

**Purpose**: Large payloads, archives, backups

**Buckets**:
- `contextiq-session-archives`: Old session data
- `contextiq-audit-logs`: Audit trail
- `contextiq-backups`: Database backups

---

## 2. Core Data Models

### 2.1 Sessions

#### Session Model

```python
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

class Session(BaseModel):
    """
    Represents a single conversation session between user and agent(s).
    """
    id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    user_id: str = Field(..., description="User identifier", max_length=255)
    agent_id: Optional[str] = Field(None, description="Primary agent identifier", max_length=255)
    scope: Dict[str, str] = Field(
        default_factory=dict,
        description="Scope for memory isolation (max 5 key-value pairs)"
    )
    state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Temporary session state"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")
    is_active: bool = Field(True, description="Whether session is currently active")
    parent_session_id: Optional[UUID] = Field(None, description="Parent session for hierarchical sessions")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user_123",
                "agent_id": "coordinator_agent",
                "scope": {
                    "user_id": "user_123",
                    "project": "alpha"
                },
                "state": {
                    "current_task": "summarize_docs",
                    "progress": 0.5
                },
                "metadata": {
                    "client_type": "web",
                    "version": "1.0"
                },
                "created_at": "2025-12-04T10:00:00Z",
                "is_active": True
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    parent_session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,

    -- Indexes
    CONSTRAINT scope_max_keys CHECK (jsonb_object_keys_count(scope) <= 5)
);

-- Indexes for common queries
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_agent_id ON sessions(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_sessions_scope ON sessions USING GIN(scope);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_sessions_parent ON sessions(parent_session_id) WHERE parent_session_id IS NOT NULL;

-- Function to count JSONB keys
CREATE OR REPLACE FUNCTION jsonb_object_keys_count(jsonb) RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER FROM jsonb_object_keys($1);
$$ LANGUAGE SQL IMMUTABLE;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.2 Events

#### Event Model

```python
class EventActions(BaseModel):
    """Actions associated with an event."""
    state_delta: Optional[Dict[str, Any]] = Field(
        None,
        description="State changes to apply"
    )
    tool_calls: Optional[List['ToolCall']] = Field(
        None,
        description="Tool calls made during this event"
    )
    tool_outputs: Optional[List['ToolOutput']] = Field(
        None,
        description="Tool outputs received"
    )

class ToolCall(BaseModel):
    """Tool call made by agent."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str

class ToolOutput(BaseModel):
    """Output from tool execution."""
    call_id: str
    output: Any
    error: Optional[str] = None

class Event(BaseModel):
    """
    Individual event within a session (user message, agent response, tool call, etc.)
    """
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Parent session ID")
    author: str = Field(..., description="Event author: 'user', 'agent', 'tool', 'system'")
    invocation_id: str = Field(..., description="Invocation identifier for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    content: Dict[str, Any] = Field(..., description="Event content (format depends on author)")
    actions: Optional[EventActions] = Field(None, description="Actions associated with event")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "author": "user",
                "invocation_id": "inv_1",
                "timestamp": "2025-12-04T10:01:00Z",
                "content": {
                    "role": "user",
                    "parts": [{"text": "What's the weather today?"}]
                },
                "actions": None
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    author VARCHAR(50) NOT NULL CHECK (author IN ('user', 'agent', 'tool', 'system')),
    invocation_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    content JSONB NOT NULL,
    actions JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_session_id ON events(session_id);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_author ON events(author);
CREATE INDEX idx_events_invocation_id ON events(invocation_id);

-- Composite index for session timeline queries
CREATE INDEX idx_events_session_timeline ON events(session_id, timestamp DESC);

-- Partitioning by timestamp (optional, for high volume)
-- CREATE TABLE events_2025_12 PARTITION OF events FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

### 2.3 Memories

#### Memory Model

```python
class Memory(BaseModel):
    """
    Long-term memory fact associated with a scope.
    """
    id: UUID = Field(default_factory=uuid4)
    scope: Dict[str, str] = Field(
        ...,
        description="Scope for memory isolation (max 5 key-value pairs)"
    )
    fact: str = Field(..., description="Memory fact in first person", max_length=2000)
    topic: str = Field(..., description="Memory topic/category", max_length=255)
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this memory"
    )
    source_session_id: Optional[UUID] = Field(
        None,
        description="Session from which this memory was extracted"
    )
    source_type: str = Field(
        "generated",
        description="How memory was created: 'generated', 'direct', 'imported'"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Memory expiration time (TTL)")
    revision_count: int = Field(0, description="Number of times memory has been updated")
    is_deleted: bool = Field(False, description="Soft delete flag")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174002",
                "scope": {"user_id": "user_123"},
                "fact": "I prefer dark mode interfaces.",
                "topic": "USER_PREFERENCES",
                "confidence": 0.95,
                "source_session_id": "123e4567-e89b-12d3-a456-426614174000",
                "source_type": "generated",
                "created_at": "2025-12-04T10:05:00Z",
                "revision_count": 0
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope JSONB NOT NULL,
    fact TEXT NOT NULL CHECK (char_length(fact) <= 2000),
    topic VARCHAR(255) NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    source_session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'generated' CHECK (source_type IN ('generated', 'direct', 'imported')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    revision_count INTEGER NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT scope_max_keys CHECK (jsonb_object_keys_count(scope) <= 5)
);

-- Indexes
CREATE INDEX idx_memories_scope ON memories USING GIN(scope);
CREATE INDEX idx_memories_topic ON memories(topic);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_expires_at ON memories(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_memories_source_session ON memories(source_session_id) WHERE source_session_id IS NOT NULL;
CREATE INDEX idx_memories_active ON memories(is_deleted) WHERE is_deleted = FALSE;

-- Full-text search index on facts
CREATE INDEX idx_memories_fact_fts ON memories USING GIN(to_tsvector('english', fact));

-- Composite index for scope + topic queries
CREATE INDEX idx_memories_scope_topic ON memories USING GIN(scope) WHERE topic IS NOT NULL;

-- Update trigger
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.4 Memory Revisions

#### MemoryRevision Model

```python
class MemoryRevision(BaseModel):
    """
    Historical snapshot of a memory at a specific point in time.
    """
    id: UUID = Field(default_factory=uuid4)
    memory_id: UUID = Field(..., description="Parent memory ID")
    revision_number: int = Field(..., description="Sequential revision number", ge=1)
    fact: str = Field(..., description="Memory fact at this revision", max_length=2000)
    action: str = Field(
        ...,
        description="Action that created this revision: 'CREATED', 'UPDATED', 'DELETED'"
    )
    source_session_id: Optional[UUID] = Field(
        None,
        description="Session that triggered this revision"
    )
    extracted_memories: Optional[List[str]] = Field(
        None,
        description="Raw extracted facts before consolidation"
    )
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "423e4567-e89b-12d3-a456-426614174003",
                "memory_id": "323e4567-e89b-12d3-a456-426614174002",
                "revision_number": 1,
                "fact": "I prefer dark mode interfaces.",
                "action": "CREATED",
                "source_session_id": "123e4567-e89b-12d3-a456-426614174000",
                "confidence": 0.95,
                "created_at": "2025-12-04T10:05:00Z"
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE memory_revisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
    fact TEXT NOT NULL CHECK (char_length(fact) <= 2000),
    action VARCHAR(20) NOT NULL CHECK (action IN ('CREATED', 'UPDATED', 'DELETED')),
    source_session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    extracted_memories JSONB,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    UNIQUE(memory_id, revision_number)
);

-- Indexes
CREATE INDEX idx_revisions_memory_id ON memory_revisions(memory_id);
CREATE INDEX idx_revisions_created_at ON memory_revisions(created_at DESC);
CREATE INDEX idx_revisions_action ON memory_revisions(action);

-- Composite index for memory history queries
CREATE INDEX idx_revisions_memory_timeline ON memory_revisions(memory_id, revision_number DESC);
```

### 2.5 Memory Generation Jobs

#### MemoryGenerationJob Model

```python
class GenerationConfig(BaseModel):
    """Configuration for memory generation."""
    wait_for_completion: bool = Field(False, description="Wait for job to complete synchronously")
    disable_consolidation: bool = Field(False, description="Skip consolidation step")
    topics: Optional[List[str]] = Field(None, description="Specific topics to extract")
    extraction_model: Optional[str] = Field(None, description="LLM model for extraction")
    embedding_model: Optional[str] = Field(None, description="Embedding model")

class GenerationResult(BaseModel):
    """Result of memory generation job."""
    memories_created: int = 0
    memories_updated: int = 0
    memories_deleted: int = 0
    extracted_count: int = 0
    errors: List[str] = Field(default_factory=list)

class MemoryGenerationJob(BaseModel):
    """
    Asynchronous job for memory generation.
    """
    id: UUID = Field(default_factory=uuid4)
    status: str = Field(
        "pending",
        description="Job status: 'pending', 'processing', 'completed', 'failed'"
    )
    source_type: str = Field(
        ...,
        description="Source type: 'session', 'events', 'facts'"
    )
    source_reference: str = Field(..., description="Reference to source (session_id, etc.)")
    scope: Dict[str, str] = Field(..., description="Scope for generated memories")
    config: GenerationConfig = Field(default_factory=GenerationConfig)
    result: Optional[GenerationResult] = Field(None)
    error_message: Optional[str] = Field(None)
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Job progress (0.0 to 1.0)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "523e4567-e89b-12d3-a456-426614174004",
                "status": "completed",
                "source_type": "session",
                "source_reference": "123e4567-e89b-12d3-a456-426614174000",
                "scope": {"user_id": "user_123"},
                "config": {"wait_for_completion": False},
                "result": {
                    "memories_created": 3,
                    "memories_updated": 1,
                    "memories_deleted": 0
                },
                "progress": 1.0,
                "created_at": "2025-12-04T10:05:00Z",
                "completed_at": "2025-12-04T10:05:10Z"
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE memory_generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('session', 'events', 'facts')),
    source_reference TEXT NOT NULL,
    scope JSONB NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    error_message TEXT,
    progress REAL NOT NULL DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 1),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_jobs_status ON memory_generation_jobs(status);
CREATE INDEX idx_jobs_created_at ON memory_generation_jobs(created_at DESC);
CREATE INDEX idx_jobs_scope ON memory_generation_jobs USING GIN(scope);

-- Composite index for polling queries
CREATE INDEX idx_jobs_status_created ON memory_generation_jobs(status, created_at DESC);
```

---

## 3. Procedural Memory Models

### 3.1 Workflows

#### Workflow Model

```python
class WorkflowStep(BaseModel):
    """Single step in a workflow."""
    order: int = Field(..., description="Step order", ge=1)
    action: str = Field(..., description="Action description")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = Field(None, description="Reasoning for this step")
    tool_used: Optional[str] = Field(None)
    success_criteria: Optional[Dict[str, Any]] = Field(None)

class Workflow(BaseModel):
    """
    Reusable workflow pattern captured from successful agent trajectories.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=255)
    description: str = Field(...)
    scope: Dict[str, str] = Field(default_factory=dict)
    steps: List[WorkflowStep] = Field(...)
    success_metrics: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = Field(None)
    tags: List[str] = Field(default_factory=list)
    usage_count: int = Field(0, description="Times this workflow was reused")
    success_rate: float = Field(1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "623e4567-e89b-12d3-a456-426614174005",
                "name": "document_summarization",
                "description": "Multi-step workflow for summarizing long documents",
                "scope": {"user_id": "user_123"},
                "steps": [
                    {
                        "order": 1,
                        "action": "Split document into chunks",
                        "reasoning": "Document too large for single LLM call"
                    },
                    {
                        "order": 2,
                        "action": "Summarize each chunk independently"
                    },
                    {
                        "order": 3,
                        "action": "Combine chunk summaries into final summary"
                    }
                ],
                "usage_count": 15,
                "success_rate": 0.93
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    steps JSONB NOT NULL,
    success_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    agent_id VARCHAR(255),
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    usage_count INTEGER NOT NULL DEFAULT 0,
    success_rate REAL NOT NULL DEFAULT 1.0 CHECK (success_rate >= 0 AND success_rate <= 1),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_workflows_scope ON workflows USING GIN(scope);
CREATE INDEX idx_workflows_agent_id ON workflows(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_workflows_tags ON workflows USING GIN(tags);
CREATE INDEX idx_workflows_usage_count ON workflows(usage_count DESC);
CREATE INDEX idx_workflows_success_rate ON workflows(success_rate DESC);

-- Full-text search
CREATE INDEX idx_workflows_name_desc_fts ON workflows USING GIN(
    to_tsvector('english', name || ' ' || description)
);

-- Update trigger
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 3.2 Skills

#### Skill Model

```python
class Skill(BaseModel):
    """
    Reusable skill learned by agents.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=255)
    description: str = Field(...)
    skill_type: str = Field(
        ...,
        description="Skill type: 'tool_usage', 'reasoning_pattern', 'coordination', 'other'"
    )
    implementation: str = Field(..., description="Code, prompt template, or procedure")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    prerequisites: List[str] = Field(default_factory=list, description="Required skills/tools")
    scope: Dict[str, str] = Field(default_factory=dict)
    success_rate: float = Field(1.0, ge=0.0, le=1.0)
    usage_count: int = Field(0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "723e4567-e89b-12d3-a456-426614174006",
                "name": "parallel_api_calls",
                "description": "Make multiple API calls in parallel for efficiency",
                "skill_type": "coordination",
                "implementation": "Use asyncio.gather() to execute API calls concurrently",
                "prerequisites": ["http_request_tool"],
                "success_rate": 0.98,
                "usage_count": 42
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    skill_type VARCHAR(50) NOT NULL CHECK (skill_type IN ('tool_usage', 'reasoning_pattern', 'coordination', 'other')),
    implementation TEXT NOT NULL,
    input_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    prerequisites TEXT[] DEFAULT ARRAY[]::TEXT[],
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    success_rate REAL NOT NULL DEFAULT 1.0 CHECK (success_rate >= 0 AND success_rate <= 1),
    usage_count INTEGER NOT NULL DEFAULT 0,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_skills_skill_type ON skills(skill_type);
CREATE INDEX idx_skills_scope ON skills USING GIN(scope);
CREATE INDEX idx_skills_tags ON skills USING GIN(tags);
CREATE INDEX idx_skills_success_rate ON skills(success_rate DESC);
CREATE INDEX idx_skills_usage_count ON skills(usage_count DESC);

-- Full-text search
CREATE INDEX idx_skills_fts ON skills USING GIN(
    to_tsvector('english', name || ' ' || description)
);

-- Update trigger
CREATE TRIGGER update_skills_updated_at
    BEFORE UPDATE ON skills
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 3.3 Agent Trajectories

#### AgentTrajectory Model

```python
class TrajectoryStep(BaseModel):
    """Single step in agent trajectory."""
    order: int
    action: str
    reasoning: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    observation: Optional[str] = None
    duration_ms: Optional[int] = None

class AgentTrajectory(BaseModel):
    """
    Complete trajectory of agent execution for learning purposes.
    """
    id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(...)
    task_description: str = Field(...)
    session_id: Optional[UUID] = Field(None)
    steps: List[TrajectoryStep] = Field(...)
    outcome: str = Field(..., description="'success', 'failure', 'partial'")
    success_metrics: Dict[str, Any] = Field(default_factory=dict)
    learning_points: List[str] = Field(default_factory=list)
    extracted_workflow_id: Optional[UUID] = Field(None)
    scope: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "823e4567-e89b-12d3-a456-426614174007",
                "agent_id": "research_agent",
                "task_description": "Find recent papers on transformer architecture",
                "steps": [
                    {
                        "order": 1,
                        "action": "search_arxiv",
                        "reasoning": "ArXiv is best source for ML papers"
                    }
                ],
                "outcome": "success",
                "learning_points": ["ArXiv search more effective than Google Scholar"]
            }
        }
```

#### PostgreSQL Schema

```sql
CREATE TABLE agent_trajectories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) NOT NULL,
    task_description TEXT NOT NULL,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    steps JSONB NOT NULL,
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('success', 'failure', 'partial')),
    success_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    learning_points TEXT[] DEFAULT ARRAY[]::TEXT[],
    extracted_workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_trajectories_agent_id ON agent_trajectories(agent_id);
CREATE INDEX idx_trajectories_outcome ON agent_trajectories(outcome);
CREATE INDEX idx_trajectories_session_id ON agent_trajectories(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_trajectories_workflow_id ON agent_trajectories(extracted_workflow_id) WHERE extracted_workflow_id IS NOT NULL;
CREATE INDEX idx_trajectories_scope ON agent_trajectories USING GIN(scope);

-- Full-text search
CREATE INDEX idx_trajectories_task_fts ON agent_trajectories USING GIN(
    to_tsvector('english', task_description)
);
```

---

## 4. Configuration Models

### 4.1 Memory Bank Configuration

#### MemoryBankConfig Model

```python
class ManagedMemoryTopic(BaseModel):
    """Managed (predefined) memory topic."""
    managed_topic_enum: str = Field(
        ...,
        description="One of: USER_PERSONAL_INFO, USER_PREFERENCES, KEY_CONVERSATION_DETAILS, EXPLICIT_INSTRUCTIONS"
    )

class CustomMemoryTopic(BaseModel):
    """Custom memory topic defined by user."""
    label: str = Field(..., max_length=100)
    description: str = Field(...)

class MemoryTopic(BaseModel):
    """Memory topic configuration."""
    managed_memory_topic: Optional[ManagedMemoryTopic] = None
    custom_memory_topic: Optional[CustomMemoryTopic] = None

class TTLConfig(BaseModel):
    """Time-to-live configuration for memories."""
    default_ttl: Optional[str] = Field(None, description="Default TTL (e.g., '365d')")
    create_ttl: Optional[str] = Field(None, description="TTL for directly created memories")
    generate_created_ttl: Optional[str] = Field(None, description="TTL for newly generated memories")
    generate_updated_ttl: Optional[str] = Field(None, description="TTL for updated memories")

class SimilaritySearchConfig(BaseModel):
    """Similarity search configuration."""
    embedding_model: str = Field("text-embedding-3-large", description="Embedding model name")
    vector_size: int = Field(1536, description="Vector dimension")
    distance_metric: str = Field("cosine", description="Distance metric: cosine, euclidean, dot")

class GenerationConfig(BaseModel):
    """Memory generation configuration."""
    model: str = Field("gpt-4o-mini", description="LLM model for extraction/consolidation")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4000)

class MemoryBankConfig(BaseModel):
    """
    Configuration for a Memory Bank instance.
    """
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=255)
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenancy")
    memory_topics: List[MemoryTopic] = Field(default_factory=list)
    few_shot_examples: Optional[Dict[str, Any]] = Field(None)
    ttl_config: TTLConfig = Field(default_factory=TTLConfig)
    similarity_search_config: SimilaritySearchConfig = Field(default_factory=SimilaritySearchConfig)
    generation_config: GenerationConfig = Field(default_factory=GenerationConfig)
    enable_revisions: bool = Field(True)
    scope_keys: List[str] = Field(default_factory=lambda: ["user_id"])
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(True)
```

#### PostgreSQL Schema

```sql
CREATE TABLE memory_bank_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255),
    memory_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    few_shot_examples JSONB,
    ttl_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    similarity_search_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    generation_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    enable_revisions BOOLEAN NOT NULL DEFAULT TRUE,
    scope_keys TEXT[] NOT NULL DEFAULT ARRAY['user_id']::TEXT[],
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE(tenant_id, name)
);

-- Indexes
CREATE INDEX idx_memory_bank_configs_tenant ON memory_bank_configs(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX idx_memory_bank_configs_active ON memory_bank_configs(is_active) WHERE is_active = TRUE;

-- Update trigger
CREATE TRIGGER update_memory_bank_configs_updated_at
    BEFORE UPDATE ON memory_bank_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 5. Vector Store Schemas (Qdrant)

### 5.1 Memories Collection

```python
from qdrant_client.models import Distance, VectorParams, PointStruct

# Collection configuration
MEMORIES_COLLECTION = "memories"
MEMORIES_CONFIG = VectorParams(
    size=1536,  # text-embedding-3-large dimension
    distance=Distance.COSINE
)

# Point structure
memory_point = PointStruct(
    id=str(memory.id),  # UUID as string
    vector=embedding,   # List[float] with 1536 dimensions
    payload={
        "memory_id": str(memory.id),
        "scope": memory.scope,
        "topic": memory.topic,
        "confidence": memory.confidence,
        "created_at": memory.created_at.isoformat(),
        "fact": memory.fact[:500]  # Truncated for payload
    }
)
```

### 5.2 Workflows Collection

```python
WORKFLOWS_COLLECTION = "workflows"
WORKFLOWS_CONFIG = VectorParams(
    size=1536,
    distance=Distance.COSINE
)

workflow_point = PointStruct(
    id=str(workflow.id),
    vector=embedding,
    payload={
        "workflow_id": str(workflow.id),
        "name": workflow.name,
        "description": workflow.description,
        "scope": workflow.scope,
        "tags": workflow.tags,
        "success_rate": workflow.success_rate,
        "usage_count": workflow.usage_count
    }
)
```

### 5.3 Skills Collection

```python
SKILLS_COLLECTION = "skills"
SKILLS_CONFIG = VectorParams(
    size=1536,
    distance=Distance.COSINE
)

skill_point = PointStruct(
    id=str(skill.id),
    vector=embedding,
    payload={
        "skill_id": str(skill.id),
        "name": skill.name,
        "description": skill.description,
        "skill_type": skill.type,
        "scope": skill.scope,
        "success_rate": skill.success_rate
    }
)
```

---

## 6. Redis Cache Schemas

### 6.1 Session Cache

```python
# Key format: session:{session_id}
# Value: JSON serialized Session object
# TTL: 3600 seconds (1 hour)

redis_key = f"session:{session.id}"
redis_value = session.model_dump_json()
redis.setex(redis_key, 3600, redis_value)
```

### 6.2 Memory Cache

```python
# Key format: memory:{memory_id}
# Value: JSON serialized Memory object
# TTL: 1800 seconds (30 minutes)

redis_key = f"memory:{memory.id}"
redis_value = memory.model_dump_json()
redis.setex(redis_key, 1800, redis_value)
```

### 6.3 Scope-based Memory Index

```python
# Key format: scope_memories:{scope_hash}
# Value: Set of memory IDs
# TTL: 1800 seconds

import hashlib
import json

scope_hash = hashlib.md5(json.dumps(scope, sort_keys=True).encode()).hexdigest()
redis_key = f"scope_memories:{scope_hash}"

# Add memory ID to set
redis.sadd(redis_key, str(memory.id))
redis.expire(redis_key, 1800)
```

### 6.4 Rate Limiting

```python
# Key format: ratelimit:{api_key}:{minute}
# Value: Request count
# TTL: 60 seconds

import time

minute = int(time.time() / 60)
redis_key = f"ratelimit:{api_key}:{minute}"

# Increment and check
count = redis.incr(redis_key)
redis.expire(redis_key, 60)

if count > RATE_LIMIT:
    raise RateLimitExceeded()
```

---

## 7. Database Migrations

### 7.1 Migration Strategy

**Tool**: Alembic (Python database migration tool)

**Directory Structure**:
```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_procedural_memory.py
│   └── 003_add_indexes.py
├── env.py
└── script.py.mako
```

### 7.2 Initial Migration

```python
"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-12-04 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin"')

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('agent_id', sa.String(255)),
        sa.Column('scope', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('state', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('TRUE')),
        sa.Column('parent_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'))
    )

    # Create indexes
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_sessions_scope', 'sessions', ['scope'], postgresql_using='gin')
    # ... more indexes

    # Create helper function
    op.execute("""
        CREATE OR REPLACE FUNCTION jsonb_object_keys_count(jsonb) RETURNS INTEGER AS $$
            SELECT COUNT(*)::INTEGER FROM jsonb_object_keys($1);
        $$ LANGUAGE SQL IMMUTABLE;
    """)

    # Create update trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER update_sessions_updated_at
            BEFORE UPDATE ON sessions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # Continue with other tables...

def downgrade():
    op.drop_table('sessions')
    # ... drop other tables
```

---

## 8. Data Integrity & Constraints

### 8.1 Foreign Key Constraints

- `events.session_id` → `sessions.id` (CASCADE DELETE)
- `memories.source_session_id` → `sessions.id` (SET NULL)
- `memory_revisions.memory_id` → `memories.id` (CASCADE DELETE)
- `sessions.parent_session_id` → `sessions.id` (CASCADE DELETE)

### 8.2 Check Constraints

- `scope` fields: Max 5 key-value pairs
- `confidence`: Between 0.0 and 1.0
- `progress`: Between 0.0 and 1.0
- `fact`: Max 2000 characters
- Enum fields: Valid values only

### 8.3 Unique Constraints

- `(memory_id, revision_number)` in `memory_revisions`
- `(tenant_id, name)` in `memory_bank_configs`

---

## 9. Performance Optimizations

### 9.1 Indexing Strategy

**B-tree Indexes**: Primary keys, foreign keys, timestamps
**GIN Indexes**: JSONB fields (scope, metadata), text arrays (tags)
**GiST Indexes**: Full-text search (tsvector)
**Composite Indexes**: Common query patterns

### 9.2 Partitioning (Optional)

For very high volume deployments:

```sql
-- Partition events by month
CREATE TABLE events (
    ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE events_2025_12 PARTITION OF events
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE events_2026_01 PARTITION OF events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### 9.3 Query Optimization

**Prepared Statements**: For frequent queries
**Connection Pooling**: PgBouncer with 100 connections
**Read Replicas**: For read-heavy operations
**Query Plan Analysis**: Regular EXPLAIN ANALYZE

---

## 10. Backup & Recovery

### 10.1 Backup Strategy

**PostgreSQL**:
- Full backup: Daily at 2 AM UTC
- Incremental backup: Every 6 hours
- Point-in-time recovery: WAL archiving
- Retention: 30 days

**Qdrant**:
- Snapshot export: Daily
- Retention: 30 days

**Redis**:
- RDB snapshot: Every hour
- AOF log: For durability
- Retention: 7 days

### 10.2 Recovery Procedures

```bash
# PostgreSQL restore
pg_restore -d contextiq backup.dump

# Qdrant restore
curl -X POST 'http://localhost:6333/collections/{collection_name}/snapshots/upload' \
  --form 'snapshot=@snapshot.snapshot'

# Redis restore
redis-cli --rdb dump.rdb
```

---

## Document Status

**Current Phase**: Data Models Design Complete ✅

**Next Document**: [API Specification](./api_specification.md)

**Related Documents**:
- [System Architecture](./system_architecture.md)
- [Agent Engine Memory Bank Research](../agent_engine_memory_bank_research.md)
