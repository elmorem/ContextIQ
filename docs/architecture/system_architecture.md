# ContextIQ System Architecture

## Document Overview

**Version**: 1.0
**Date**: December 4, 2025
**Status**: Architecture Design Phase

This document defines the complete system architecture for ContextIQ, a context engineering engine providing Sessions and Memory management services for AI agents.

---

## 1. Architecture Vision

### 1.1 Core Principles

1. **Separation of Concerns**: Clear boundaries between Sessions (temporary) and Memory (persistent)
2. **Framework Agnostic**: Direct API access enables integration with any agent framework
3. **Scale-First Design**: Built for production multi-agent systems from day one
4. **Open and Extensible**: Open source with plugin architecture for custom logic
5. **Cloud-Native**: Containerized, stateless services with managed state
6. **API-First**: All functionality exposed via well-defined REST APIs
7. **Async by Default**: Non-blocking operations for memory generation and heavy processing

### 1.2 Design Goals

- **Performance**: <100ms p95 latency for synchronous operations
- **Scalability**: Support 100k+ concurrent sessions, 1M+ memories per user
- **Availability**: 99.9% uptime SLA
- **Framework Support**: ADK, LangGraph, CrewAI, custom frameworks
- **Multi-Tenancy**: Secure isolation between users, tenants, applications
- **Observability**: Comprehensive metrics, logging, tracing

---

## 2. High-Level Architecture

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API Gateway Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   REST API   │  │   GraphQL    │  │   WebSocket  │             │
│  │   Gateway    │  │   Gateway    │  │   Gateway    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Core Services Layer                          │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Sessions Service   │◄────────┤  Memory Service     │          │
│  │  - Create/Get/List  │         │  - Generate         │          │
│  │  - Events/State     │         │  - Retrieve/Search  │          │
│  │  - Multi-agent      │         │  - Consolidate      │          │
│  └──────────┬──────────┘         └──────────┬──────────┘          │
│             │                               │                      │
│             │                               │                      │
│  ┌──────────▼──────────────────────────────▼──────────┐          │
│  │         Procedural Memory Service                   │          │
│  │  - Workflow Storage    - Agent Learning            │          │
│  │  - Pattern Recognition - Skill Library             │          │
│  └─────────────────────────────────────────────────────┘          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Processing Layer                               │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Extraction Engine  │         │ Consolidation Engine│          │
│  │  - LLM Integration  │         │  - Merge Logic      │          │
│  │  - Topic Matching   │         │  - Conflict Detect  │          │
│  │  - Few-shot Learning│         │  - Update/Delete    │          │
│  └─────────────────────┘         └─────────────────────┘          │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Embedding Service  │         │   Revision Tracker  │          │
│  │  - Vector Generation│         │  - Snapshot Creation│          │
│  │  - Similarity Search│         │  - Provenance Track │          │
│  └─────────────────────┘         └─────────────────────┘          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Message Queue Layer                            │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Memory Generation  │         │  Consolidation      │          │
│  │  Queue              │         │  Queue              │          │
│  └─────────────────────┘         └─────────────────────┘          │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Embedding          │         │  Revision           │          │
│  │  Queue              │         │  Queue              │          │
│  └─────────────────────┘         └─────────────────────┘          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Storage Layer                                │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  PostgreSQL         │         │   Vector Store      │          │
│  │  - Sessions         │         │  (Qdrant/Pinecone)  │          │
│  │  - Events/State     │         │  - Memory Embeddings│          │
│  │  - Memories         │         │  - Similarity Search│          │
│  │  - Revisions        │         │                     │          │
│  └─────────────────────┘         └─────────────────────┘          │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Redis Cache        │         │  S3/Object Storage  │          │
│  │  - Session Cache    │         │  - Large Payloads   │          │
│  │  - Memory Cache     │         │  - Audit Logs       │          │
│  │  - Rate Limiting    │         │  - Backups          │          │
│  └─────────────────────┘         └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Patterns

#### Pattern 1: Session Creation and Event Appending
```
Client Request
    │
    ▼
API Gateway (Auth/Validation)
    │
    ▼
Sessions Service
    │
    ├──► PostgreSQL (Write Session)
    └──► Redis (Cache Session)
    │
    ▼
Response to Client
```

#### Pattern 2: Async Memory Generation
```
Client Request (Generate Memory)
    │
    ▼
API Gateway
    │
    ▼
Memory Service
    │
    ├──► Memory Generation Queue (Async)
    └──► Response 202 Accepted (Job ID)
    │
    ▼
Background Worker
    │
    ├──► Extraction Engine (LLM)
    ├──► Consolidation Engine
    ├──► Embedding Service
    └──► PostgreSQL + Vector Store
```

#### Pattern 3: Similarity Search Retrieval
```
Client Request (Search Query)
    │
    ▼
API Gateway
    │
    ▼
Memory Service
    │
    ├──► Redis Cache (Check)
    │    └──► Cache Hit? Return
    │
    ├──► Embedding Service (Generate Query Vector)
    ├──► Vector Store (Similarity Search)
    ├──► PostgreSQL (Fetch Full Memory Objects)
    └──► Redis Cache (Store Results)
    │
    ▼
Response to Client
```

---

## 3. Component Architecture

### 3.1 Sessions Service

**Responsibilities**:
- Manage session lifecycle (create, retrieve, update, delete)
- Handle event appending with state management
- Support multi-agent session coordination
- Enforce TTL and cleanup policies

**API Operations**:
```
POST   /api/v1/sessions                    # Create session
GET    /api/v1/sessions/{session_id}       # Get session
GET    /api/v1/sessions                    # List sessions (filtered)
DELETE /api/v1/sessions/{session_id}       # Delete session
POST   /api/v1/sessions/{session_id}/events # Append event
PATCH  /api/v1/sessions/{session_id}/state  # Update state
```

**Data Model**:
```python
Session {
    id: UUID
    user_id: str
    agent_id: str (optional)
    scope: Dict[str, str]
    events: List[Event]
    state: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime (optional)
}

Event {
    id: UUID
    session_id: UUID
    author: str  # "user", "agent", "tool", "system"
    invocation_id: str
    timestamp: datetime
    content: Dict[str, Any]
    actions: EventActions (optional)
}

EventActions {
    state_delta: Dict[str, Any]
    tool_calls: List[ToolCall] (optional)
    tool_outputs: List[ToolOutput] (optional)
}
```

**Storage Strategy**:
- **Primary**: PostgreSQL (JSONB for events/state)
- **Cache**: Redis (hot sessions, TTL-based)
- **Archive**: S3 (old sessions for audit)

### 3.2 Memory Service

**Responsibilities**:
- Orchestrate memory generation pipeline
- Handle memory retrieval (all or similarity search)
- Manage memory CRUD operations
- Coordinate with extraction and consolidation engines

**API Operations**:
```
POST   /api/v1/memories/generate            # Generate from session/events
POST   /api/v1/memories                     # Create memory directly
GET    /api/v1/memories/{memory_id}         # Get single memory
GET    /api/v1/memories                     # List memories (paginated)
POST   /api/v1/memories/search              # Similarity search
PATCH  /api/v1/memories/{memory_id}         # Update memory
DELETE /api/v1/memories/{memory_id}         # Delete memory
GET    /api/v1/memories/{memory_id}/revisions # List revisions
```

**Data Model**:
```python
Memory {
    id: UUID
    scope: Dict[str, str]
    fact: str
    topic: str
    confidence: float
    source_session_id: UUID (optional)
    embedding: List[float] (stored in vector DB)
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime (optional)
    revision_count: int
}

MemoryRevision {
    id: UUID
    memory_id: UUID
    revision_number: int
    fact: str
    action: str  # "CREATED", "UPDATED", "DELETED"
    source_session_id: UUID (optional)
    extracted_memories: List[str] (optional)
    created_at: datetime
}

MemoryGenerationJob {
    id: UUID
    status: str  # "pending", "processing", "completed", "failed"
    source_type: str  # "session", "events", "facts"
    source_reference: str
    scope: Dict[str, str]
    config: GenerationConfig
    result: GenerationResult (optional)
    created_at: datetime
    completed_at: datetime (optional)
}
```

**Storage Strategy**:
- **Primary**: PostgreSQL (memory metadata, facts, revisions)
- **Vector Store**: Qdrant/Pinecone (embeddings for similarity search)
- **Cache**: Redis (frequently accessed memories)

### 3.3 Procedural Memory Service

**Responsibilities**:
- Store agent workflows and execution patterns
- Capture reasoning chains and decision trees
- Enable agent learning from trajectories
- Manage skill library and reusable patterns

**API Operations**:
```
POST   /api/v1/procedural/workflows         # Store workflow pattern
GET    /api/v1/procedural/workflows/{id}    # Retrieve workflow
POST   /api/v1/procedural/skills            # Store reusable skill
GET    /api/v1/procedural/skills            # List skills (filtered)
POST   /api/v1/procedural/trajectories      # Store agent trajectory
POST   /api/v1/procedural/search            # Search similar patterns
```

**Data Model**:
```python
Workflow {
    id: UUID
    name: str
    description: str
    scope: Dict[str, str]
    steps: List[WorkflowStep]
    success_metrics: Dict[str, Any]
    agent_id: str (optional)
    embedding: List[float]
    created_at: datetime
    usage_count: int
}

WorkflowStep {
    order: int
    action: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    reasoning: str (optional)
}

Skill {
    id: UUID
    name: str
    description: str
    skill_type: str  # "tool_usage", "reasoning_pattern", "coordination"
    implementation: str  # Code or prompt template
    success_rate: float
    scope: Dict[str, str]
    embedding: List[float]
    created_at: datetime
}

AgentTrajectory {
    id: UUID
    agent_id: str
    task_description: str
    steps: List[TrajectoryStep]
    outcome: str  # "success", "failure", "partial"
    learning_points: List[str]
    created_at: datetime
}
```

**Storage Strategy**:
- **Primary**: PostgreSQL (workflow definitions, skills)
- **Vector Store**: Qdrant (workflow/skill embeddings)
- **Cache**: Redis (frequently used patterns)

### 3.4 Extraction Engine

**Responsibilities**:
- Integrate with LLM providers (OpenAI, Anthropic, etc.)
- Extract meaningful information based on memory topics
- Apply few-shot learning for customization
- Handle multimodal content extraction

**Core Logic**:
```python
class ExtractionEngine:
    def extract_memories(
        self,
        content: List[Event],
        topics: List[MemoryTopic],
        few_shot_examples: List[Example] = None
    ) -> List[ExtractedMemory]:
        """
        Extract memories from conversation content.

        Process:
        1. Build extraction prompt with topics and examples
        2. Call LLM with conversation context
        3. Parse LLM response into structured memories
        4. Validate and score confidence
        """
        pass

    def match_topics(
        self,
        extracted_fact: str,
        topics: List[MemoryTopic]
    ) -> List[str]:
        """
        Match extracted fact to configured topics.
        """
        pass
```

**Configuration**:
```python
ExtractionConfig {
    model: str  # "gpt-4", "claude-3-5-sonnet", etc.
    temperature: float
    max_tokens: int
    topics: List[MemoryTopic]
    few_shot_examples: List[Example]
    multimodal: bool
}

MemoryTopic {
    id: str
    type: str  # "managed" or "custom"
    label: str
    description: str
    extraction_prompt: str (optional)
}
```

### 3.5 Consolidation Engine

**Responsibilities**:
- Merge new memories with existing ones
- Detect duplicates and contradictions
- Update or delete existing memories
- Preserve information integrity

**Core Logic**:
```python
class ConsolidationEngine:
    def consolidate(
        self,
        new_memories: List[ExtractedMemory],
        existing_memories: List[Memory],
        scope: Dict[str, str]
    ) -> ConsolidationResult:
        """
        Consolidate new memories with existing.

        Process:
        1. Retrieve existing memories for scope
        2. Compare each new memory with existing
        3. Determine action: CREATE, UPDATE, DELETE
        4. Generate consolidated memory facts
        5. Create revision records
        """
        pass

    def detect_duplicates(
        self,
        new_memory: ExtractedMemory,
        existing_memories: List[Memory]
    ) -> Optional[Memory]:
        """
        Find duplicate or highly similar existing memory.
        """
        pass

    def detect_contradictions(
        self,
        new_memory: ExtractedMemory,
        existing_memories: List[Memory]
    ) -> List[Memory]:
        """
        Find memories that contradict new information.
        """
        pass

    def merge_memories(
        self,
        new_memory: ExtractedMemory,
        existing_memory: Memory
    ) -> Memory:
        """
        Intelligently merge new info into existing memory.
        """
        pass
```

**Storage**:
- Uses LLM for semantic comparison and merging
- Creates revision records for all mutations
- Maintains provenance trail

### 3.6 Embedding Service

**Responsibilities**:
- Generate embeddings for memories, workflows, skills
- Support multiple embedding models
- Cache embeddings for efficiency
- Handle batch processing

**Core Logic**:
```python
class EmbeddingService:
    def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-large"
    ) -> List[float]:
        """
        Generate embedding vector for text.
        """
        pass

    def generate_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-3-large"
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        """
        pass

    def similarity_search(
        self,
        query_embedding: List[float],
        scope: Dict[str, str],
        top_k: int = 10
    ) -> List[SimilarityResult]:
        """
        Search for similar embeddings in vector store.
        """
        pass
```

**Supported Models**:
- OpenAI: `text-embedding-3-small`, `text-embedding-3-large`
- Sentence Transformers: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`
- Custom models via plugin system

### 3.7 Revision Tracker

**Responsibilities**:
- Create snapshots on memory mutations
- Track provenance and lineage
- Enable historical queries
- Support rollback operations

**Core Logic**:
```python
class RevisionTracker:
    def create_revision(
        self,
        memory: Memory,
        action: str,
        source_session_id: Optional[UUID] = None,
        extracted_memories: Optional[List[str]] = None
    ) -> MemoryRevision:
        """
        Create revision snapshot for memory change.
        """
        pass

    def get_history(
        self,
        memory_id: UUID
    ) -> List[MemoryRevision]:
        """
        Retrieve complete revision history.
        """
        pass

    def rollback(
        self,
        memory_id: UUID,
        revision_number: int
    ) -> Memory:
        """
        Rollback memory to specific revision.
        """
        pass
```

---

## 4. Infrastructure Architecture

### 4.1 Technology Stack

**Core Services**:
- **Language**: Python 3.11+
- **Web Framework**: FastAPI (async, high performance)
- **API Documentation**: OpenAPI/Swagger (auto-generated)
- **Validation**: Pydantic v2

**Storage**:
- **Primary Database**: PostgreSQL 15+ (with pgvector extension)
- **Vector Store**: Qdrant (self-hosted) or Pinecone (managed)
- **Cache**: Redis 7+
- **Object Storage**: S3-compatible (MinIO for self-hosted, S3 for cloud)

**Message Queue**:
- **Queue System**: RabbitMQ or Apache Kafka
- **Task Processing**: Celery with Redis backend

**LLM Integration**:
- **Providers**: LiteLLM (unified interface for all providers)
- **Supported**: OpenAI, Anthropic, Google, Azure, local models

**Observability**:
- **Metrics**: Prometheus
- **Logging**: Structured logging (JSON) with ELK stack
- **Tracing**: OpenTelemetry with Jaeger
- **Monitoring**: Grafana dashboards

**Deployment**:
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **IaC**: Terraform

### 4.2 Deployment Architecture

#### Production Deployment (Kubernetes)

```
┌─────────────────────────────────────────────────────────────┐
│                     Ingress Controller                      │
│                (NGINX/Traefik with TLS)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
┌─────────▼─────┐ ┌─────▼──────┐ ┌────▼──────┐
│  API Gateway  │ │ GraphQL    │ │ WebSocket │
│  (3 replicas) │ │ (2 replicas│ │ (2 replicas)
└───────┬───────┘ └─────┬──────┘ └────┬──────┘
        │               │              │
        └───────────────┼──────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼────────┐ ┌───▼────────┐ ┌───▼───────────┐
│ Sessions Svc   │ │ Memory Svc │ │ Procedural Svc│
│ (5 replicas)   │ │(5 replicas)│ │ (3 replicas)  │
└────────┬───────┘ └─────┬──────┘ └───────┬───────┘
         │               │                │
         └───────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼────────┐ ┌────▼──────┐
│ Extraction     │ │Consolidation│ │ Embedding │
│ Workers        │ │ Workers     │ │ Workers   │
│ (10 replicas)  │ │(5 replicas) │ │(3 replicas)
└───────┬────────┘ └─────┬───────┘ └────┬──────┘
        │                │               │
        └────────────────┼───────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼────────┐ ┌────▼──────┐
│   PostgreSQL   │ │   Qdrant    │ │   Redis   │
│  (Primary +    │ │ (Cluster)   │ │ (Cluster) │
│   2 Replicas)  │ │             │ │           │
└────────────────┘ └─────────────┘ └───────────┘
```

#### Self-Hosted (Docker Compose)

```yaml
services:
  api-gateway:
    image: contextiq/api-gateway:latest
    replicas: 2

  sessions-service:
    image: contextiq/sessions-service:latest
    replicas: 3

  memory-service:
    image: contextiq/memory-service:latest
    replicas: 3

  extraction-worker:
    image: contextiq/extraction-worker:latest
    replicas: 5

  postgres:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine

  rabbitmq:
    image: rabbitmq:3-management
```

### 4.3 Scalability Strategy

**Horizontal Scaling**:
- All services are stateless and can scale horizontally
- Load balancing via Kubernetes Service or NGINX
- Auto-scaling based on CPU/memory metrics

**Database Scaling**:
- PostgreSQL: Read replicas for read-heavy operations
- Connection pooling (PgBouncer)
- Partitioning by scope/user_id for large datasets

**Vector Store Scaling**:
- Qdrant cluster mode with sharding
- Separate collections per tenant for isolation

**Cache Strategy**:
- Redis Cluster for high availability
- Multi-tier caching (L1: in-memory, L2: Redis)
- TTL-based expiration

**Message Queue Scaling**:
- RabbitMQ cluster or Kafka partitioning
- Separate queues for different priority levels
- Dead letter queues for failed jobs

### 4.4 Security Architecture

**Authentication & Authorization**:
- API Key authentication for service-to-service
- JWT tokens for user authentication
- OAuth2/OIDC integration
- Role-Based Access Control (RBAC)

**Data Security**:
- Encryption at rest (database encryption)
- Encryption in transit (TLS 1.3)
- Scope-based isolation
- Multi-tenancy support

**Network Security**:
- Network policies in Kubernetes
- Private subnets for databases
- WAF (Web Application Firewall)
- Rate limiting and DDoS protection

**Secrets Management**:
- Kubernetes Secrets or HashiCorp Vault
- Environment variable injection
- Rotation policies

---

## 5. API Architecture

### 5.1 REST API Design Principles

**Standards**:
- RESTful conventions (HTTP verbs, status codes)
- JSON request/response bodies
- Consistent error format
- Pagination for list endpoints
- Filtering, sorting, searching support

**Versioning**:
- URL-based versioning: `/api/v1/`, `/api/v2/`
- Deprecation policy: 6 months notice

**Rate Limiting**:
- Per API key: 1000 req/min (configurable)
- Per IP: 100 req/min (anonymous)
- Burst allowance: 2x sustained rate

**Error Format**:
```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid scope format",
        "details": {
            "field": "scope",
            "reason": "Maximum 5 key-value pairs allowed"
        },
        "trace_id": "abc123..."
    }
}
```

### 5.2 GraphQL API (Optional)

**Benefits**:
- Single endpoint for complex queries
- Client-defined response shape
- Reduced over-fetching

**Schema Example**:
```graphql
type Session {
    id: ID!
    userId: String!
    agentId: String
    scope: JSON!
    events: [Event!]!
    state: JSON!
    createdAt: DateTime!
    updatedAt: DateTime!
}

type Memory {
    id: ID!
    scope: JSON!
    fact: String!
    topic: String!
    confidence: Float!
    revisions: [MemoryRevision!]!
    createdAt: DateTime!
}

type Query {
    session(id: ID!): Session
    sessions(userId: String, limit: Int, offset: Int): [Session!]!
    memory(id: ID!): Memory
    searchMemories(scope: JSON!, query: String!, topK: Int): [Memory!]!
}

type Mutation {
    createSession(input: CreateSessionInput!): Session!
    appendEvent(sessionId: ID!, event: EventInput!): Event!
    generateMemories(input: GenerateMemoriesInput!): MemoryGenerationJob!
}
```

### 5.3 WebSocket API

**Use Cases**:
- Real-time memory generation updates
- Live session event streaming
- Multi-agent coordination notifications

**Events**:
```javascript
// Client subscribes to updates
ws.send({
    type: "subscribe",
    topic: "memory_generation",
    job_id: "abc123"
});

// Server sends updates
{
    type: "memory_generation.progress",
    job_id: "abc123",
    status: "extracting",
    progress: 0.5
}

{
    type: "memory_generation.completed",
    job_id: "abc123",
    result: {
        memories_created: 5,
        memories_updated: 2
    }
}
```

---

## 6. Multi-Agent Coordination Architecture

### 6.1 Session Patterns

#### Pattern A: Unified Session (Shared History)
```
┌──────────────────────────────────────┐
│         Single Session               │
│  user_id: "123"                      │
│  scope: {"project": "alpha"}         │
├──────────────────────────────────────┤
│  Event 1: User Input                 │
│  Event 2: Coordinator Agent Response │
│  Event 3: Tool Call (Specialist)     │
│  Event 4: Tool Output                │
│  Event 5: Coordinator Final Response │
└──────────────────────────────────────┘
```

**Use When**: Agents need full context of entire conversation

#### Pattern B: Separate Sessions (Individual Histories)
```
┌────────────────────┐       ┌────────────────────┐
│ Session: Main      │       │ Session: Specialist│
│ agent_id: "coord"  │◄─────►│ agent_id: "spec1"  │
│ user_id: "123"     │  A2A  │ user_id: "123"     │
└────────────────────┘       └────────────────────┘
```

**Use When**: Agents need isolated contexts or parallel execution

#### Pattern C: Hierarchical Sessions
```
┌──────────────────────────────┐
│   Root Session (Coordinator) │
├──────────────────────────────┤
│  ┌──────────┐   ┌──────────┐│
│  │ SubSess 1│   │ SubSess 2││
│  │(Agent A) │   │(Agent B) ││
│  └──────────┘   └──────────┘│
└──────────────────────────────┘
```

**Use When**: Parent agent orchestrates child agents

### 6.2 Memory Sharing Patterns

#### Pattern 1: Shared Memory Pool
```python
# All agents access same memory scope
scope = {"user_id": "123", "project": "alpha"}

# Coordinator reads/writes
coord_memories = retrieve_memories(scope)

# Specialists read/write same pool
specialist_memories = retrieve_memories(scope)
```

**Pros**: Simple, all agents have same context
**Cons**: Potential conflicts, no agent-specific memory

#### Pattern 2: Agent-Specific Memory
```python
# Each agent has own memory scope
coord_scope = {"user_id": "123", "agent_role": "coordinator"}
specialist_scope = {"user_id": "123", "agent_role": "specialist"}

# Memories isolated by agent_role
coord_memories = retrieve_memories(coord_scope)
specialist_memories = retrieve_memories(specialist_scope)
```

**Pros**: Clear ownership, no conflicts
**Cons**: Agents can't access each other's context

#### Pattern 3: Hybrid (Shared + Private)
```python
# Shared user memories
shared_scope = {"user_id": "123"}
shared_memories = retrieve_memories(shared_scope)

# Agent-specific operational memories
private_scope = {"user_id": "123", "agent_id": "coord_123"}
private_memories = retrieve_memories(private_scope)

# Combine for full context
all_memories = shared_memories + private_memories
```

**Pros**: Best of both worlds
**Cons**: More complex retrieval logic

### 6.3 Agent-to-Agent Protocol (A2A)

**Message Format**:
```python
A2AMessage {
    from_agent_id: str
    to_agent_id: str
    message_type: str  # "request", "response", "notification"
    content: Dict[str, Any]
    context: A2AContext
    timestamp: datetime
}

A2AContext {
    session_id: UUID
    user_id: str
    parent_invocation_id: str (optional)
    shared_state: Dict[str, Any]
}
```

**Implementation**:
- Store A2A messages as special events in sessions
- Use message queue for async communication
- Support both sync (blocking) and async (fire-and-forget)

**Example Flow**:
```
1. Coordinator receives user request
2. Coordinator sends A2A request to Specialist
   - Appends "agent_request" event to session
3. Specialist processes request
4. Specialist sends A2A response
   - Appends "agent_response" event to session
5. Coordinator incorporates response
```

---

## 7. Configuration Management

### 7.1 Configuration Hierarchy

```
Global Config (Application-wide)
    │
    ├─► Tenant Config (Per-tenant overrides)
    │       │
    │       └─► Agent Config (Per-agent overrides)
    │
    └─► Instance Config (Memory Bank instances)
```

### 7.2 Configuration Schema

```python
GlobalConfig {
    # LLM Settings
    default_extraction_model: str = "gpt-4o-mini"
    default_embedding_model: str = "text-embedding-3-large"
    max_tokens: int = 4000
    temperature: float = 0.7

    # Memory Settings
    default_ttl: str = "365d"
    enable_revisions: bool = True
    consolidation_enabled: bool = True

    # Performance
    max_concurrent_generations: int = 100
    cache_ttl: int = 3600

    # Security
    require_auth: bool = True
    rate_limit_per_key: int = 1000
}

MemoryBankConfig {
    id: UUID
    name: str
    tenant_id: str (optional)

    # Memory Topics
    topics: List[MemoryTopic]

    # Generation
    extraction_model: str
    embedding_model: str
    few_shot_examples: List[Example]

    # TTL
    ttl_config: TTLConfig

    # Revision
    enable_revisions: bool

    # Scope
    scope_keys: List[str]
}

TTLConfig {
    default_ttl: str (optional)
    create_ttl: str (optional)
    generate_created_ttl: str (optional)
    generate_updated_ttl: str (optional)
}
```

### 7.3 Configuration Storage

- **Global**: Environment variables + config file
- **Tenant/Instance**: PostgreSQL (config table)
- **Runtime**: Redis cache for fast access

---

## 8. Observability Architecture

### 8.1 Metrics

**Service Metrics**:
- Request rate, latency (p50, p95, p99)
- Error rate by endpoint
- Active sessions/connections
- Queue depth and processing rate

**Memory Metrics**:
- Memory generation latency
- Extraction success rate
- Consolidation actions (create/update/delete)
- Retrieval latency and cache hit rate

**Infrastructure Metrics**:
- CPU, memory, disk usage
- Database connection pool stats
- Queue consumer lag
- Cache hit/miss rates

**Collection**: Prometheus exporters in each service

### 8.2 Logging

**Log Levels**:
- DEBUG: Detailed diagnostic info
- INFO: General informational messages
- WARN: Warning messages (degraded performance, etc.)
- ERROR: Error messages (recoverable)
- FATAL: Fatal errors (service crash)

**Structured Logging**:
```json
{
    "timestamp": "2025-12-04T10:30:00Z",
    "level": "INFO",
    "service": "memory-service",
    "trace_id": "abc123",
    "span_id": "def456",
    "user_id": "user_123",
    "message": "Memory generation completed",
    "duration_ms": 1234,
    "memories_created": 5
}
```

**Log Aggregation**: ELK Stack (Elasticsearch, Logstash, Kibana)

### 8.3 Tracing

**Distributed Tracing**:
- OpenTelemetry instrumentation
- Trace entire request lifecycle across services
- Span attributes: user_id, session_id, memory_id

**Example Trace**:
```
POST /api/v1/memories/generate
├─► Sessions Service: Get Session (50ms)
├─► Memory Service: Enqueue Job (10ms)
└─► Background Worker
    ├─► Extraction Engine: Extract (2000ms)
    │   └─► LLM API Call (1800ms)
    ├─► Consolidation Engine: Consolidate (500ms)
    │   ├─► Vector Store: Similarity Search (100ms)
    │   └─► LLM API Call (300ms)
    └─► Storage: Write (50ms)
```

**Backend**: Jaeger for trace storage and visualization

### 8.4 Alerting

**Alert Rules**:
- High error rate (>1% for 5 minutes)
- High latency (p95 >1s for 10 minutes)
- Queue backlog (>1000 jobs for 5 minutes)
- Database connection pool exhaustion
- Service down (health check failure)

**Notification Channels**: Slack, PagerDuty, email

---

## 9. Development & Deployment Workflow

### 9.1 Development Workflow

```
Local Development
    │
    ├─► Unit Tests (pytest)
    ├─► Integration Tests (Docker Compose)
    └─► Linting/Formatting (ruff, black)
    │
    ▼
Feature Branch → Pull Request
    │
    ├─► CI Pipeline (GitHub Actions)
    │   ├─► Run Tests
    │   ├─► Security Scan
    │   ├─► Build Docker Images
    │   └─► Deploy to Preview Env
    │
    ▼
Merge to Main
    │
    ├─► CD Pipeline
    │   ├─► Run Full Test Suite
    │   ├─► Build & Tag Images
    │   └─► Deploy to Staging
    │
    ▼
Manual Approval
    │
    ▼
Deploy to Production
    │
    └─► Blue/Green Deployment
```

### 9.2 Testing Strategy

**Unit Tests**:
- Test individual functions and classes
- Mock external dependencies
- Target: >80% coverage

**Integration Tests**:
- Test service interactions
- Use test databases (Docker containers)
- Test API endpoints end-to-end

**Load Tests**:
- Simulate high traffic scenarios
- Measure latency under load
- Identify bottlenecks

**Security Tests**:
- Dependency vulnerability scanning
- Static analysis (Bandit)
- Penetration testing (periodic)

### 9.3 CI/CD Pipeline

**GitHub Actions Workflow**:
```yaml
name: CI/CD Pipeline

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/ --cov

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker images
        run: docker build -t contextiq/api:${{ github.sha }} .

      - name: Push to registry
        run: docker push contextiq/api:${{ github.sha }}

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: kubectl apply -f k8s/staging/
```

---

## 10. Cost Optimization Strategies

### 10.1 LLM Cost Optimization

**Model Selection**:
- Use cheaper models for extraction (gpt-4o-mini)
- Reserve expensive models for complex consolidation
- Consider local models for high-volume use cases

**Prompt Optimization**:
- Minimize prompt length
- Use few-shot examples sparingly
- Cache common extraction patterns

**Batching**:
- Batch multiple memory generations
- Amortize LLM call overhead

### 10.2 Infrastructure Cost

**Compute**:
- Auto-scaling: Scale down during low traffic
- Spot instances for background workers
- Right-size containers (CPU/memory)

**Storage**:
- TTL-based cleanup reduces database size
- Object storage for cold data (cheaper than database)
- Compression for archived data

**Network**:
- Cache aggressively to reduce database queries
- CDN for static assets
- Regional deployments to reduce cross-region traffic

---

## 11. Migration & Rollout Strategy

### 11.1 Phased Rollout

**Phase 1: Alpha (Week 1-2)**
- Deploy to internal testing environment
- Limited user base (5-10 developers)
- Focus on basic functionality

**Phase 2: Beta (Week 3-4)**
- Deploy to beta environment
- Invite 50-100 early adopters
- Collect feedback, iterate

**Phase 3: General Availability (Week 5+)**
- Full production deployment
- Public documentation
- Support channels active

### 11.2 Data Migration

**For users migrating from other systems**:

```python
# Migration script
class MemoryMigrator:
    def migrate_from_custom_db(
        self,
        source_db: Database,
        memory_bank_config: MemoryBankConfig
    ):
        """
        Migrate memories from custom database to ContextIQ.
        """
        # 1. Extract memories from source
        memories = source_db.query("SELECT * FROM memories")

        # 2. Transform to ContextIQ format
        for memory in memories:
            contextiq_memory = self.transform(memory)

            # 3. Create in ContextIQ
            api_client.create_memory(contextiq_memory)
```

---

## 12. Open Questions & Decisions Needed

### 12.1 Technical Decisions

1. **Vector Store Choice**:
   - Option A: Qdrant (self-hosted, open source)
   - Option B: Pinecone (managed, easier ops)
   - Option C: pgvector (PostgreSQL extension, simpler architecture)
   - **Recommendation**: Start with Qdrant for flexibility

2. **Message Queue**:
   - Option A: RabbitMQ (mature, feature-rich)
   - Option B: Kafka (high throughput, complex)
   - Option C: Redis Streams (simple, already using Redis)
   - **Recommendation**: RabbitMQ for balance of features and simplicity

3. **LLM Provider Strategy**:
   - Use LiteLLM for unified interface
   - Support OpenAI, Anthropic, Google as tier-1
   - Allow custom model configuration

### 12.2 Business Decisions

1. **Pricing Model**:
   - Open source with paid support?
   - Freemium (limited usage, paid for scale)?
   - Enterprise licensing?

2. **Hosting Options**:
   - Self-hosted only?
   - Managed cloud offering?
   - Both?

3. **Support Model**:
   - Community support (Discord, GitHub)?
   - Paid support tiers?
   - Professional services?

---

## 13. Next Steps

### 13.1 Immediate Actions

1. ✅ Architecture design complete
2. **Technology stack selection** - Finalize database, vector store, queue choices
3. **Data models and schemas** - Define database schemas
4. **API specification** - Create OpenAPI spec
5. **Repository setup** - Initialize monorepo with services

### 13.2 Development Phases

**Week 1-2: Foundation**
- Setup repository structure
- Define data models
- Implement database migrations
- Setup development environment (Docker Compose)

**Week 3-4: Sessions Service**
- Implement Sessions API
- Event appending logic
- State management
- Unit + integration tests

**Week 5-6: Memory Service (Basic)**
- Memory CRUD operations
- Direct memory creation
- Basic retrieval (no similarity search yet)

**Week 7-8: Extraction Engine**
- LLM integration (OpenAI initially)
- Topic-based extraction
- Few-shot learning support

**Week 9-10: Consolidation Engine**
- Duplicate detection
- Conflict resolution
- Memory merging logic

**Week 11-12: Similarity Search**
- Embedding service
- Vector store integration
- Similarity-based retrieval

**Week 13-14: Procedural Memory**
- Workflow storage
- Skill library
- Trajectory capture

**Week 15-16: Production Hardening**
- Observability setup
- Security hardening
- Performance optimization
- Documentation

---

## Document Status

**Current Phase**: Architecture Design Complete ✅

**Next Document**: [Data Models & Schemas](./data_models.md)

**Related Documents**:
- [Agent Engine Memory Bank Research](../agent_engine_memory_bank_research.md)
- [API Specification](./api_specification.md) (TBD)
- [Deployment Guide](./deployment_guide.md) (TBD)
