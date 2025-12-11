# ContextIQ Architecture

Complete architecture documentation for the ContextIQ context engineering platform.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Services](#core-services)
- [Background Workers](#background-workers)
- [Data Layer](#data-layer)
- [Message Queue](#message-queue)
- [Observability](#observability)
- [Authentication & Security](#authentication--security)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Decisions](#design-decisions)

## Overview

ContextIQ is a production-ready context engineering platform built as a microservices architecture. It provides persistent memory and session management for AI agents through REST APIs, making it framework-agnostic and suitable for integration with any agent framework.

### Design Principles

1. **Separation of Concerns**: Clear boundaries between sessions (temporary) and memory (persistent)
2. **Framework Agnostic**: Direct API access enables integration with any agent framework
3. **Async by Default**: Non-blocking operations for memory generation and heavy processing
4. **Cloud-Native**: Containerized, stateless services with managed state
5. **Observable**: Comprehensive metrics, logging, and tracing
6. **Secure**: Authentication, authorization, and encrypted communications

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                             │
│  - Request routing          - Health aggregation                │
│  - Authentication           - Correlation tracking              │
│  - Metrics & tracing        - CORS handling                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐  ┌───▼────────┐  ┌───▼────────────┐
│    Sessions    │  │   Memory   │  │   Procedural   │
│    Service     │  │  Service   │  │  (Planned)     │
│                │  │            │  │                │
│ - Create       │  │ - Generate │  │ - Workflows    │
│ - Events       │  │ - Search   │  │ - Skills       │
│ - State        │  │ - CRUD     │  │ - Learning     │
└────────┬───────┘  └─────┬──────┘  └────────────────┘
         │                │
         │    ┌───────────┴───────────┐
         │    │                       │
    ┌────▼────▼─────┐        ┌───────▼────────┐
    │   RabbitMQ    │        │   PostgreSQL   │
    │ Message Queue │        │   Database     │
    │               │        │                │
    │ - Memory Gen  │        │ - Sessions     │
    │ - Consolidate │        │ - Memories     │
    └────┬────┬─────┘        │ - Revisions    │
         │    │              └────────────────┘
    ┌────▼────▼─────┐
    │   Background  │        ┌────────────────┐
    │    Workers    │        │     Qdrant     │
    │               │        │  Vector Store  │
    │ - Memory Gen  │◄───────┤                │
    │ - Consolidate │        │ - Embeddings   │
    └───────────────┘        │ - Similarity   │
                             └────────────────┘
         ┌───────────────────────┐
         │        Redis          │
         │    Cache Layer        │
         │                       │
         │ - Session cache       │
         │ - Memory cache        │
         │ - Rate limiting       │
         └───────────────────────┘
```

## Core Services

### API Gateway

**Responsibility**: Unified entry point for all client requests

**Features**:
- Request routing to backend services
- Authentication middleware (JWT/API keys)
- Correlation ID tracking across services
- Health check aggregation
- Metrics collection
- CORS handling

**Technology**: FastAPI, httpx for proxying

**Key Files**:
- `/services/gateway/app/main.py`

### Sessions Service

**Responsibility**: Manage conversation sessions and event tracking

**Features**:
- Create and retrieve sessions
- Append events to sessions
- Manage session state
- Support multi-agent coordination
- TTL-based session expiration

**API Endpoints**:
```
POST   /api/v1/sessions              # Create session
GET    /api/v1/sessions/{id}         # Get session
GET    /api/v1/sessions              # List sessions
POST   /api/v1/sessions/{id}/events  # Append event
PATCH  /api/v1/sessions/{id}/state   # Update state
DELETE /api/v1/sessions/{id}         # Delete session
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
```

**Storage**:
- Primary: PostgreSQL (JSONB for events/state)
- Cache: Redis (hot sessions)

**Key Files**:
- `/services/sessions/app/main.py`
- `/services/sessions/app/api/v1/sessions.py`
- `/services/sessions/app/services/session_service.py`

### Memory Service

**Responsibility**: Orchestrate memory generation, storage, and retrieval

**Features**:
- Generate memories from sessions
- Direct memory CRUD operations
- Semantic similarity search
- Memory consolidation
- Revision tracking

**API Endpoints**:
```
POST   /api/v1/memories/generate     # Generate from session
POST   /api/v1/memories              # Create memory
GET    /api/v1/memories/{id}         # Get memory
GET    /api/v1/memories              # List memories
POST   /api/v1/memories/search       # Similarity search
PATCH  /api/v1/memories/{id}         # Update memory
DELETE /api/v1/memories/{id}         # Delete memory
GET    /api/v1/memories/{id}/revisions  # Get history
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
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime (optional)
}
```

**Storage**:
- Primary: PostgreSQL (metadata, facts)
- Vector Store: Qdrant (embeddings)
- Cache: Redis (frequently accessed)

**Key Files**:
- `/services/memory/app/main.py`
- `/services/memory/app/api/v1/memories.py`
- `/services/memory/app/services/memory_service.py`

## Background Workers

### Memory Generation Worker

**Responsibility**: Extract memories from conversation content using LLMs

**Process**:
1. Consume message from RabbitMQ queue
2. Fetch session/events from Sessions Service
3. Call LLM (via LiteLLM) to extract facts
4. Generate embeddings for facts
5. Store memories in database and vector store
6. Update job status

**Technology**:
- LiteLLM for LLM integration
- OpenAI/Anthropic APIs
- Qdrant client for vector storage

**Configuration**:
```python
WORKER_CONCURRENCY=5           # Parallel workers
WORKER_PREFETCH_COUNT=10       # Messages to prefetch
OPENAI_API_KEY=...            # LLM provider keys
ANTHROPIC_API_KEY=...
```

**Key Files**:
- `/workers/memory_generation/worker.py`
- `/workers/memory_generation/processor.py`
- `/shared/extraction/engine.py`

### Consolidation Worker

**Responsibility**: Merge new memories with existing ones

**Process**:
1. Consume consolidation request from RabbitMQ
2. Retrieve existing memories in scope
3. Use LLM to detect duplicates/contradictions
4. Merge, update, or delete memories
5. Create revision records
6. Update vector store

**Technology**:
- LiteLLM for semantic comparison
- Qdrant for similarity search

**Key Files**:
- `/workers/consolidation/worker.py`
- `/workers/consolidation/processor.py`
- `/shared/consolidation/engine.py`

## Data Layer

### PostgreSQL Database

**Purpose**: Primary data store for all persistent data

**Schema**:
- `sessions` - Session records
- `events` - Session events
- `memories` - Memory records
- `memory_revisions` - Revision history
- `memory_generation_jobs` - Background job tracking

**Features**:
- JSONB columns for flexible data
- Indexes on user_id, scope, timestamps
- Foreign key constraints
- UUID primary keys

**Migration Management**:
- Alembic for schema versioning
- Migration scripts in `/alembic/versions/`
- See [Database Migrations Guide](DATABASE_MIGRATIONS.md)

**Connection Pooling**:
```python
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_RECYCLE=3600
```

### Qdrant Vector Store

**Purpose**: Store and search memory embeddings

**Collections**:
- `memories` - Memory fact embeddings

**Configuration**:
```python
QDRANT_URL=http://localhost:6333
QDRANT_GRPC_PORT=6334
QDRANT_TIMEOUT=60
```

**Vector Dimensions**: 1536 (OpenAI text-embedding-3-small)

**Key Files**:
- `/shared/vector_store/qdrant_client.py`
- `/shared/vector_store/collections.py`

### Redis Cache

**Purpose**: High-speed caching and rate limiting

**Usage**:
- Session caching (TTL: 24 hours)
- Memory caching (TTL: 2 hours)
- Job status caching (TTL: 1 hour)
- Rate limiting counters

**Configuration**:
```python
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5.0
```

**Key Files**:
- `/shared/cache/redis_client.py`
- `/shared/cache/cache_manager.py`

## Message Queue

### RabbitMQ

**Purpose**: Asynchronous task processing and service decoupling

**Queues**:
- `memory_generation` - Memory extraction jobs
- `memory_consolidation` - Memory merge jobs

**Features**:
- Durable queues (survive restarts)
- Message acknowledgment
- Dead letter queues for failures
- Prefetch for load balancing

**Configuration**:
```python
RABBITMQ_URL=amqp://contextiq:password@localhost:5672/
RABBITMQ_HEARTBEAT=60
RABBITMQ_CONNECTION_ATTEMPTS=3
```

**Message Format**:
```python
{
    "job_id": "uuid",
    "source_type": "session",
    "source_reference": "session_id",
    "scope": {"user_id": "123"},
    "config": {...}
}
```

**Key Files**:
- `/shared/messaging/rabbitmq_client.py`
- `/shared/messaging/consumer.py`
- `/shared/messaging/publisher.py`

## Observability

### Prometheus Metrics

**Collected Metrics**:
- HTTP request rate, latency, errors
- Database operation latency
- Queue depth and processing rate
- Worker job completion time
- Cache hit/miss rates

**Metrics Endpoint**: `GET /metrics`

**Example Metrics**:
```
http_requests_total{service="api-gateway",method="GET",endpoint="/health",status_code="200"} 1234
http_request_duration_seconds{service="sessions",method="POST",endpoint="/sessions"} 0.123
db_operations_total{service="memory",operation="insert",table="memories",status="success"} 567
```

**Key Files**:
- `/shared/observability/metrics.py`
- `/shared/observability/middleware.py`

### OpenTelemetry Tracing

**Purpose**: Distributed request tracing across services

**Features**:
- Automatic FastAPI instrumentation
- Correlation ID propagation
- Span attributes (user_id, session_id, etc.)
- Context propagation across services

**Trace Example**:
```
POST /api/v1/memories/generate (API Gateway)
├─► POST /api/v1/sessions/{id} (Sessions Service) [50ms]
├─► Publish to RabbitMQ (Memory Service) [10ms]
└─► Background Worker Processing
    ├─► LLM API Call [2000ms]
    ├─► Generate Embeddings [300ms]
    └─► Store in Database [50ms]
```

**Key Files**:
- `/shared/observability/tracing.py`

### Structured Logging

**Format**: JSON with consistent fields

**Log Fields**:
```json
{
    "timestamp": "2025-12-11T10:30:00Z",
    "level": "INFO",
    "service": "memory-service",
    "correlation_id": "abc123",
    "user_id": "user_123",
    "message": "Memory generated",
    "duration_ms": 1234
}
```

**Log Levels**:
- DEBUG: Detailed diagnostic information
- INFO: General informational messages
- WARNING: Warning messages
- ERROR: Error messages (recoverable)
- CRITICAL: Critical errors (service crash)

**Key Files**:
- `/shared/config/logging.py`

## Authentication & Security

### JWT Tokens

**Purpose**: User authentication

**Features**:
- HS256 signing algorithm
- Configurable expiration (default: 60 minutes)
- User identity and permissions in payload
- Issuer validation

**Token Payload**:
```json
{
    "sub": "user_123",
    "org_id": "org_456",
    "email": "user@example.com",
    "name": "John Doe",
    "permissions": ["SESSION_READ", "MEMORY_READ"],
    "iss": "contextiq",
    "exp": 1234567890
}
```

**Usage**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/sessions
```

### API Keys

**Purpose**: Service-to-service and programmatic access

**Features**:
- SHA-256 hashed storage
- Configurable permissions
- Expiration dates
- Rate limiting
- Revocation support

**Format**: `ck_<random_string>`

**Usage**:
```bash
curl -H "X-API-Key: ck_xxxxx" \
  http://localhost:8000/api/v1/memories
```

### Authentication Middleware

**Process**:
1. Extract token from Authorization header or API key from X-API-Key header
2. Validate and decode token/key
3. Verify permissions
4. Attach user identity to request
5. Allow/deny request

**Exempt Paths**:
- `/health`, `/health/*`
- `/docs`, `/redoc`, `/openapi.json`
- `/metrics`

**Configuration**:
```python
AUTH_REQUIRE_AUTH=true                # Enable/disable globally
AUTH_JWT_SECRET_KEY=...              # JWT signing key
AUTH_REQUIRE_AUTH_EXCEPTIONS=...     # Comma-separated exempt paths
```

**Key Files**:
- `/shared/auth/jwt.py`
- `/shared/auth/api_key.py`
- `/shared/auth/middleware.py`
- `/shared/auth/models.py`

See [Authentication Guide](AUTHENTICATION.md) for details.

## Data Flow

### Session Creation Flow

```
1. Client → API Gateway
   POST /api/v1/sessions
   {user_id, agent_id, scope}

2. API Gateway → Sessions Service
   - Authenticate request
   - Add correlation ID
   - Forward request

3. Sessions Service
   - Validate request
   - Generate UUID
   - Insert into PostgreSQL
   - Cache in Redis
   - Return response

4. Response → Client
   {id, user_id, ...}
```

### Memory Generation Flow (Async)

```
1. Client → Memory Service
   POST /api/v1/memories/generate
   {source_type, source_reference, scope}

2. Memory Service
   - Create job record (status: pending)
   - Publish to RabbitMQ queue
   - Return job ID

3. Memory Generation Worker
   - Consume message from queue
   - Fetch session data
   - Call LLM to extract facts
   - Generate embeddings
   - Store in PostgreSQL + Qdrant
   - Update job status (completed)

4. Client polls or subscribes for job status
```

### Memory Search Flow

```
1. Client → Memory Service
   POST /api/v1/memories/search
   {scope, search_query, top_k}

2. Memory Service
   - Check Redis cache (cache key: scope + query)
   - If cache miss:
     a. Generate query embedding
     b. Search Qdrant for similar vectors
     c. Fetch full records from PostgreSQL
     d. Cache results in Redis
   - Return memories

3. Response → Client
   [{id, fact, topic, confidence}, ...]
```

## Technology Stack

### Backend

- **Language**: Python 3.11+
- **Web Framework**: FastAPI (async, high performance)
- **Validation**: Pydantic v2
- **HTTP Client**: httpx (async)
- **ASGI Server**: Uvicorn

### Database & Storage

- **Primary Database**: PostgreSQL 15+ (with uuid-ossp, pgcrypto extensions)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Vector Store**: Qdrant
- **Cache**: Redis 7+

### Message Queue

- **Queue**: RabbitMQ 3.x
- **Client**: aio-pika (async)

### LLM Integration

- **Unified Interface**: LiteLLM
- **Supported Providers**: OpenAI, Anthropic, Google, Azure
- **Embedding**: OpenAI text-embedding-3-small/large

### Observability

- **Metrics**: Prometheus (prometheus-client)
- **Tracing**: OpenTelemetry
- **Logging**: structlog (structured JSON)

### Development Tools

- **Code Formatting**: Black (100 char line length)
- **Linting**: Ruff
- **Type Checking**: mypy
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Pre-commit**: pre-commit hooks

### Deployment

- **Containerization**: Docker
- **Orchestration**: Docker Compose (development), Kubernetes (production planned)
- **CI/CD**: GitHub Actions (planned)

## Design Decisions

### Why FastAPI?

- **Async Support**: Native async/await for high concurrency
- **Automatic Docs**: OpenAPI/Swagger generation
- **Type Safety**: Pydantic integration for validation
- **Performance**: One of the fastest Python frameworks
- **Developer Experience**: Excellent DX with type hints

### Why PostgreSQL?

- **JSONB Support**: Flexible schema for events and state
- **ACID Compliance**: Strong consistency guarantees
- **Extensions**: uuid-ossp, pgcrypto for built-in functions
- **Mature Ecosystem**: Well-understood, battle-tested
- **Vector Support**: pgvector available if needed

### Why Qdrant?

- **Open Source**: Self-hostable alternative to Pinecone
- **Performance**: Optimized for billion-scale vectors
- **Features**: Filtering, payload storage, HNSW algorithm
- **gRPC Support**: High-performance option
- **Easy Deployment**: Single Docker container

### Why RabbitMQ?

- **Reliability**: Durable queues, message acknowledgment
- **Features**: Dead letter queues, priority queues
- **Management UI**: Easy monitoring and debugging
- **Simplicity**: Easier than Kafka for moderate scale
- **Python Client**: Excellent aio-pika library

### Why Microservices?

- **Separation of Concerns**: Sessions and Memory are distinct domains
- **Independent Scaling**: Scale services based on load
- **Technology Flexibility**: Use best tool for each job
- **Team Autonomy**: Teams can work independently
- **Resilience**: Service failures are isolated

### Async vs Sync Processing

**Synchronous** (Sessions):
- Low latency required (<100ms)
- Simple CRUD operations
- Immediate feedback needed

**Asynchronous** (Memory Generation):
- Long-running operations (2-5 seconds)
- LLM API calls with variable latency
- Client doesn't need immediate result
- Better resource utilization

### Caching Strategy

**L1 Cache** (In-memory): Not implemented (stateless services)

**L2 Cache** (Redis):
- Sessions: 24 hour TTL
- Memories: 2 hour TTL
- Search results: 1 hour TTL

**Cache Invalidation**:
- Write-through: Update cache on write
- TTL-based expiration
- Manual invalidation on delete

### Security Considerations

1. **Environment Variables**: All secrets in .env (never committed)
2. **HTTPS**: Required in production (TLS 1.3)
3. **Authentication**: JWT/API keys for all requests (configurable)
4. **Authorization**: Permission-based access control
5. **SQL Injection**: SQLAlchemy ORM prevents injection
6. **Input Validation**: Pydantic models validate all input
7. **Rate Limiting**: Planned (Redis-based)

## Future Enhancements

### Planned Features

1. **Procedural Memory Service**
   - Workflow storage
   - Skill library
   - Agent learning from trajectories

2. **Enhanced Observability**
   - Grafana dashboards
   - Jaeger tracing backend
   - ELK stack for log aggregation

3. **Kubernetes Deployment**
   - Helm charts
   - Auto-scaling policies
   - Service mesh (Istio)

4. **Rate Limiting**
   - Redis-based distributed rate limiting
   - Per-user and per-API-key limits
   - Burst allowance

5. **SDK Development**
   - Python SDK
   - TypeScript SDK
   - Framework adapters (ADK, LangGraph, CrewAI)

### Scalability Improvements

1. **Database**
   - Read replicas for read-heavy operations
   - Connection pooling (PgBouncer)
   - Table partitioning by user_id

2. **Vector Store**
   - Qdrant cluster mode
   - Collection sharding
   - Separate collections per tenant

3. **Caching**
   - Redis Cluster for HA
   - Multi-region replication
   - Advanced eviction policies

4. **Message Queue**
   - RabbitMQ cluster
   - Queue partitioning
   - Priority queues

## References

- [Database Migrations Guide](DATABASE_MIGRATIONS.md)
- [Authentication Guide](AUTHENTICATION.md)
- [API Usage Guide](API_USAGE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Development Guide](DEVELOPMENT.md)
- [Agent Engine Memory Bank Research](agent_engine_memory_bank_research.md)
