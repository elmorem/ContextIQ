# ContextIQ Development Plan

**Version**: 2.0
**Date**: December 4, 2025
**Status**: In Progress - Phase 1

This document outlines the complete development roadmap for ContextIQ, broken into small, incremental Pull Requests (PRs). Each PR is kept under 500 lines when possible to ensure reviewability and maintainability.

---

## Development Principles

### PR Size Guidelines

- **Target**: 300-500 lines per PR
- **Maximum**: 700 lines (exceptional cases only)
- **Rationale**: Smaller PRs are easier to review, test, and debug

### PR Requirements

- ✅ **Incremental**: Each PR builds on previous PRs
- ✅ **Complete**: Each PR delivers working, tested functionality
- ✅ **Tested**: Unit tests + integration tests for all new code
- ✅ **Quality Gates**: Linting, type checking, tests must pass locally
- ✅ **CI/CD**: GitHub Actions run on every PR
- ✅ **Documented**: README updates, docstrings, code comments
- ✅ **Reviewable**: Small, focused changes

### Local Quality Checklist (Before Push)

```bash
make format      # Format with Black
make lint        # Lint with Ruff
make type-check  # Type check with mypy
make test        # Run all tests
make check       # All of the above
```

---

## Pull Request Breakdown

### ✅ PR #1: Project Foundation & CI/CD Setup
**Status**: COMPLETED
**Lines**: ~400
**Branch**: `feat/project-foundation`

Root configuration, CI/CD, documentation templates.

---

### ✅ PR #2: Database Setup & Migrations
**Status**: COMPLETED
**Lines**: ~350
**Branch**: `feat/database-setup`

Alembic setup, initial migration with all tables.

---

### ✅ PR #3: Shared Infrastructure Code
**Status**: COMPLETED
**Lines**: 4,495 (TOO LARGE - lesson learned)
**Branch**: `feat/shared-infrastructure`

All shared infrastructure in one massive PR. Should have been split into 8-10 smaller PRs.

---

### PR #4: Qdrant Initialization Scripts
**Branch**: `feat/qdrant-init`
**Depends On**: PR #3
**Estimated Lines**: ~200

**Scope**:
- Qdrant collection creation scripts
- Collection configuration utilities
- Health check for Qdrant

**Files Created**:
- `scripts/init_qdrant.py`
- `shared/vector_store/__init__.py`
- `shared/vector_store/collections.py`

**Tests**:
- `tests/unit/shared/vector_store/test_collections.py`
- `tests/integration/test_qdrant_init.py`

**Success Criteria**:
- [ ] Collections created successfully
- [ ] Health check validates Qdrant
- [ ] Script is idempotent

---

### PR #5: RabbitMQ Initialization Scripts
**Branch**: `feat/rabbitmq-init`
**Depends On**: PR #4
**Estimated Lines**: ~250

**Scope**:
- RabbitMQ queue/exchange setup scripts
- Validation utilities
- Health check for RabbitMQ

**Files Created**:
- `scripts/init_rabbitmq.py`
- `scripts/health_check.py`

**Tests**:
- `tests/integration/test_rabbitmq_init.py`
- `tests/integration/test_health_check.py`

**Success Criteria**:
- [ ] All queues/exchanges created
- [ ] Health check validates all services
- [ ] Script is idempotent

---

### PR #6: Sessions Service - Database Models
**Branch**: `feat/sessions-db-models`
**Depends On**: PR #5
**Estimated Lines**: ~300

**Scope**:
- SQLAlchemy models for sessions
- Repository pattern base classes
- Session repository only (no events yet)

**Files Created**:
- `services/sessions/app/db/models.py` (Session model only)
- `services/sessions/app/db/repositories/base.py`
- `services/sessions/app/db/repositories/session_repository.py`

**Tests**:
- `services/sessions/tests/unit/repositories/test_session_repository.py`
- `services/sessions/tests/integration/test_session_database.py`

**Success Criteria**:
- [ ] Session model matches migration
- [ ] Repository CRUD works
- [ ] Tests cover all operations

---

### PR #7: Sessions Service - Event Models & Repository
**Branch**: `feat/sessions-event-models`
**Depends On**: PR #6
**Estimated Lines**: ~250

**Scope**:
- Event SQLAlchemy model
- Event repository
- Event relationship with sessions

**Files Created**:
- `services/sessions/app/db/models.py` (add Event model)
- `services/sessions/app/db/repositories/event_repository.py`

**Tests**:
- `services/sessions/tests/unit/repositories/test_event_repository.py`
- `services/sessions/tests/integration/test_event_database.py`

**Success Criteria**:
- [ ] Event model works
- [ ] Events linked to sessions
- [ ] Repository tests pass

---

### PR #8: Sessions Service - Core Business Logic
**Branch**: `feat/sessions-service-logic`
**Depends On**: PR #7
**Estimated Lines**: ~400

**Scope**:
- Session service layer
- State management logic
- TTL and expiry handling

**Files Created**:
- `services/sessions/app/services/session_service.py`
- `services/sessions/app/core/config.py`
- `services/sessions/app/core/dependencies.py`

**Tests**:
- `services/sessions/tests/unit/services/test_session_service.py`

**Success Criteria**:
- [ ] Session creation works
- [ ] State updates work
- [ ] TTL handling works

---

### PR #9: Sessions Service - FastAPI Setup & Health
**Branch**: `feat/sessions-fastapi-setup`
**Depends On**: PR #8
**Estimated Lines**: ~300

**Scope**:
- FastAPI application setup
- Health check endpoint
- Service configuration
- Docker setup

**Files Created**:
- `services/sessions/app/main.py`
- `services/sessions/app/api/health.py`
- `services/sessions/Dockerfile`
- `services/sessions/requirements.txt`

**Tests**:
- `services/sessions/tests/integration/test_health_endpoint.py`

**Success Criteria**:
- [ ] Service starts successfully
- [ ] Health check responds
- [ ] Docker build works

---

### PR #10: Sessions Service - CRUD API Endpoints
**Branch**: `feat/sessions-crud-api`
**Depends On**: PR #9
**Estimated Lines**: ~400

**Scope**:
- Session CRUD endpoints
- Request/response schemas
- Basic validation

**Files Created**:
- `services/sessions/app/api/v1/sessions.py`
- `services/sessions/app/api/schemas/requests.py`
- `services/sessions/app/api/schemas/responses.py`

**API Endpoints**:

```
POST   /api/v1/sessions
GET    /api/v1/sessions/{session_id}
GET    /api/v1/sessions
DELETE /api/v1/sessions/{session_id}
```

**Tests**:
- `services/sessions/tests/integration/api/test_sessions_crud.py`

**Success Criteria**:
- [ ] All CRUD operations work
- [ ] Validation catches errors
- [ ] Response schemas correct

---

### PR #11: Sessions Service - Event & State Endpoints
**Branch**: `feat/sessions-events-state-api`
**Depends On**: PR #10
**Estimated Lines**: ~350

**Scope**:
- Event appending endpoint
- State management endpoint
- Cache integration

**Files Created**:
- `services/sessions/app/api/v1/events.py`
- `services/sessions/app/api/v1/state.py`

**API Endpoints**:

```
POST  /api/v1/sessions/{session_id}/events
PATCH /api/v1/sessions/{session_id}/state
```

**Tests**:
- `services/sessions/tests/integration/api/test_events.py`
- `services/sessions/tests/integration/api/test_state.py`

**Success Criteria**:
- [ ] Events append correctly
- [ ] State updates work
- [ ] Cache invalidation works

---

### PR #12: Memory Service - Database Models
**Branch**: `feat/memory-db-models`
**Depends On**: PR #11
**Estimated Lines**: ~350

**Scope**:
- Memory SQLAlchemy model
- Memory repository
- Basic CRUD operations

**Files Created**:
- `services/memory/app/db/models.py` (Memory model)
- `services/memory/app/db/repositories/base.py`
- `services/memory/app/db/repositories/memory_repository.py`

**Tests**:
- `services/memory/tests/unit/repositories/test_memory_repository.py`
- `services/memory/tests/integration/test_memory_database.py`

**Success Criteria**:
- [ ] Memory model matches migration
- [ ] Repository CRUD works
- [ ] Scope filtering works

---

### PR #13: Memory Service - Revision Models & Repository
**Branch**: `feat/memory-revision-models`
**Depends On**: PR #12
**Estimated Lines**: ~300

**Scope**:
- MemoryRevision model
- Revision repository
- Revision tracking logic

**Files Created**:
- `services/memory/app/db/models.py` (add MemoryRevision)
- `services/memory/app/db/repositories/revision_repository.py`

**Tests**:
- `services/memory/tests/unit/repositories/test_revision_repository.py`

**Success Criteria**:
- [ ] Revisions track changes
- [ ] History accessible
- [ ] Repository tests pass

---

### PR #14: Memory Service - Core Business Logic
**Branch**: `feat/memory-service-logic`
**Depends On**: PR #13
**Estimated Lines**: ~400

**Scope**:
- Memory service layer
- Revision service layer
- Confidence updating

**Files Created**:
- `services/memory/app/services/memory_service.py`
- `services/memory/app/services/revision_service.py`
- `services/memory/app/core/config.py`

**Tests**:
- `services/memory/tests/unit/services/test_memory_service.py`
- `services/memory/tests/unit/services/test_revision_service.py`

**Success Criteria**:
- [ ] Memory creation works
- [ ] Updates create revisions
- [ ] Confidence logic works

---

### PR #15: Memory Service - FastAPI Setup & Health
**Branch**: `feat/memory-fastapi-setup`
**Depends On**: PR #14
**Estimated Lines**: ~300

**Scope**:
- FastAPI application
- Health endpoint
- Docker setup

**Files Created**:
- `services/memory/app/main.py`
- `services/memory/app/api/health.py`
- `services/memory/Dockerfile`
- `services/memory/requirements.txt`

**Tests**:
- `services/memory/tests/integration/test_health_endpoint.py`

**Success Criteria**:
- [ ] Service starts
- [ ] Health check works
- [ ] Docker build succeeds

---

### PR #16: Memory Service - CRUD API Endpoints
**Branch**: `feat/memory-crud-api`
**Depends On**: PR #15
**Estimated Lines**: ~400

**Scope**:
- Memory CRUD endpoints
- Request/response schemas

**Files Created**:
- `services/memory/app/api/v1/memories.py`
- `services/memory/app/api/schemas/requests.py`
- `services/memory/app/api/schemas/responses.py`

**API Endpoints**:

```
POST   /api/v1/memories
GET    /api/v1/memories/{memory_id}
GET    /api/v1/memories
PATCH  /api/v1/memories/{memory_id}
DELETE /api/v1/memories/{memory_id}
```

**Tests**:
- `services/memory/tests/integration/api/test_memories_crud.py`

**Success Criteria**:
- [ ] All CRUD operations work
- [ ] Scope filtering works
- [ ] Pagination works

---

### PR #17: Memory Service - Revision API Endpoints
**Branch**: `feat/memory-revisions-api`
**Depends On**: PR #16
**Estimated Lines**: ~250

**Scope**:
- Revision history endpoints
- Revision comparison

**Files Created**:
- `services/memory/app/api/v1/revisions.py`

**API Endpoints**:

```
GET /api/v1/memories/{memory_id}/revisions
GET /api/v1/memories/{memory_id}/revisions/{revision_id}
```

**Tests**:
- `services/memory/tests/integration/api/test_revisions.py`

**Success Criteria**:
- [ ] Revision history accessible
- [ ] Revisions paginated
- [ ] Comparison works

---

### PR #18: Qdrant Client Wrapper
**Branch**: `feat/qdrant-client-wrapper`
**Depends On**: PR #17
**Estimated Lines**: ~350

**Scope**:
- Qdrant client wrapper
- Connection management
- Basic operations

**Files Created**:
- `shared/vector_store/qdrant_client.py`
- `shared/vector_store/config.py`

**Tests**:
- `tests/unit/shared/vector_store/test_qdrant_client.py`
- `tests/integration/test_qdrant_connection.py`

**Success Criteria**:
- [ ] Client connects to Qdrant
- [ ] Insert/search works
- [ ] Error handling works

---

### PR #19: Embedding Generation Utilities
**Branch**: `feat/embedding-generation`
**Depends On**: PR #18
**Estimated Lines**: ~300

**Scope**:
- Embedding generation (OpenAI/local)
- Chunking strategies
- Batch processing

**Files Created**:
- `shared/vector_store/embeddings.py`
- `shared/vector_store/chunking.py`

**Tests**:
- `tests/unit/shared/vector_store/test_embeddings.py`

**Success Criteria**:
- [ ] Embeddings generated
- [ ] Chunking works
- [ ] Batch processing works

---

### PR #20: Memory Service - Vector Search Integration
**Branch**: `feat/memory-vector-search`
**Depends On**: PR #19
**Estimated Lines**: ~400

**Scope**:
- Embedding service for memories
- Vector storage on create/update
- Similarity search service

**Files Created**:
- `services/memory/app/services/embedding_service.py`
- `services/memory/app/services/search_service.py`

**Tests**:
- `services/memory/tests/unit/services/test_embedding_service.py`
- `services/memory/tests/unit/services/test_search_service.py`
- `services/memory/tests/integration/test_vector_search.py`

**Success Criteria**:
- [ ] Memories embedded on creation
- [ ] Vectors stored in Qdrant
- [ ] Search returns similar memories

---

### PR #21: Memory Service - Search API Endpoint
**Branch**: `feat/memory-search-api`
**Depends On**: PR #20
**Estimated Lines**: ~300

**Scope**:
- Similarity search endpoint
- Scope-based filtering
- Result ranking

**Files Created**:
- `services/memory/app/api/v1/search.py`

**API Endpoints**:

```
POST /api/v1/memories/search
```

**Tests**:
- `services/memory/tests/integration/api/test_similarity_search.py`

**Success Criteria**:
- [ ] Search endpoint works
- [ ] Scope filtering works
- [ ] Results ranked by similarity

---

### PR #22: LLM Client Wrapper
**Branch**: `feat/llm-client-wrapper`
**Depends On**: PR #21
**Estimated Lines**: ~350

**Scope**:
- LiteLLM client wrapper
- Retry logic
- Token counting

**Files Created**:
- `shared/llm/__init__.py`
- `shared/llm/client.py`
- `shared/llm/config.py`

**Tests**:
- `tests/unit/shared/llm/test_client.py`

**Success Criteria**:
- [ ] LLM calls work
- [ ] Retry logic works
- [ ] Error handling works

---

### PR #23: LLM Prompt Templates & Parsers
**Branch**: `feat/llm-prompts-parsers`
**Depends On**: PR #22
**Estimated Lines**: ~300

**Scope**:
- Prompt templates for extraction
- Response parsers
- Validation

**Files Created**:
- `shared/llm/prompts.py`
- `shared/llm/parsers.py`

**Tests**:
- `tests/unit/shared/llm/test_prompts.py`
- `tests/unit/shared/llm/test_parsers.py`

**Success Criteria**:
- [ ] Templates render correctly
- [ ] Parsers extract facts
- [ ] Validation catches errors

---

### PR #24: Extraction Worker - Basic Structure
**Branch**: `feat/extraction-worker-structure`
**Depends On**: PR #23
**Estimated Lines**: ~350

**Scope**:
- Worker service structure
- RabbitMQ consumer setup
- Message handling skeleton

**Files Created**:
- `services/workers/extraction/Dockerfile`
- `services/workers/extraction/requirements.txt`
- `services/workers/extraction/app/worker.py`
- `services/workers/extraction/app/consumer.py`

**Tests**:
- `services/workers/extraction/tests/test_worker.py`

**Success Criteria**:
- [ ] Worker starts
- [ ] Consumes messages
- [ ] Basic error handling

---

### PR #25: Extraction Worker - Extraction Engine
**Branch**: `feat/extraction-engine`
**Depends On**: PR #24
**Estimated Lines**: ~400

**Scope**:
- Extraction engine logic
- Topic-based filtering
- Memory creation

**Files Created**:
- `services/workers/extraction/app/extraction/engine.py`
- `services/workers/extraction/app/extraction/topics.py`

**Tests**:
- `services/workers/extraction/tests/unit/test_extraction_engine.py`
- `services/workers/extraction/tests/integration/test_end_to_end.py`

**Success Criteria**:
- [ ] Facts extracted from events
- [ ] Topics filter correctly
- [ ] Memories created

---

### PR #26: Memory Service - Generation Job Management
**Branch**: `feat/memory-job-management`
**Depends On**: PR #25
**Estimated Lines**: ~400

**Scope**:
- Job model and repository
- Job tracking service
- Job status updates

**Files Created**:
- `services/memory/app/db/models.py` (add ExtractionJob)
- `services/memory/app/db/repositories/job_repository.py`
- `services/memory/app/services/job_manager.py`

**Tests**:
- `services/memory/tests/unit/repositories/test_job_repository.py`
- `services/memory/tests/unit/services/test_job_manager.py`

**Success Criteria**:
- [ ] Jobs created and tracked
- [ ] Status updates work
- [ ] Job history accessible

---

### PR #27: Memory Service - Generation API Endpoint
**Branch**: `feat/memory-generation-api`
**Depends On**: PR #26
**Estimated Lines**: ~350

**Scope**:
- Memory generation endpoint
- Message publishing
- Job status endpoint

**Files Created**:
- `services/memory/app/api/v1/generate.py`
- `services/memory/app/api/v1/jobs.py`
- `services/memory/app/services/generation_service.py`

**API Endpoints**:

```
POST /api/v1/memories/generate
GET  /api/v1/jobs/{job_id}
```

**Tests**:
- `services/memory/tests/integration/api/test_generation.py`
- `services/memory/tests/integration/test_async_processing.py`

**Success Criteria**:
- [ ] Generation queues job
- [ ] Job tracked correctly
- [ ] Worker processes job

---

### PR #28: Consolidation Worker - Duplicate Detection
**Branch**: `feat/consolidation-duplicate-detection`
**Depends On**: PR #27
**Estimated Lines**: ~400

**Scope**:
- Consolidation worker structure
- Duplicate detection logic
- Similarity thresholds

**Files Created**:
- `services/workers/consolidation/Dockerfile`
- `services/workers/consolidation/app/worker.py`
- `services/workers/consolidation/app/consolidation/duplicate_detector.py`

**Tests**:
- `services/workers/consolidation/tests/unit/test_duplicate_detection.py`

**Success Criteria**:
- [ ] Duplicates detected
- [ ] Thresholds configurable
- [ ] Tests cover edge cases

---

### PR #29: Consolidation Worker - Conflict Resolution
**Branch**: `feat/consolidation-conflict-resolution`
**Depends On**: PR #28
**Estimated Lines**: ~350

**Scope**:
- Conflict resolution strategies
- Confidence-based merging
- Revision creation

**Files Created**:
- `services/workers/consolidation/app/consolidation/conflict_resolver.py`
- `services/workers/consolidation/app/consolidation/merger.py`

**Tests**:
- `services/workers/consolidation/tests/unit/test_conflict_resolution.py`
- `services/workers/consolidation/tests/unit/test_merger.py`

**Success Criteria**:
- [ ] Conflicts resolved correctly
- [ ] Confidence updated
- [ ] Revisions track changes

---

### PR #30: Consolidation Worker - Complete Pipeline
**Branch**: `feat/consolidation-pipeline`
**Depends On**: PR #29
**Estimated Lines**: ~300

**Scope**:
- Complete consolidation pipeline
- Consumer integration
- End-to-end testing

**Files Created**:
- `services/workers/consolidation/app/consolidation/engine.py`

**Tests**:
- `services/workers/consolidation/tests/integration/test_consolidation_pipeline.py`

**Success Criteria**:
- [ ] Full pipeline works
- [ ] Messages consumed
- [ ] Memories consolidated

---

## Remaining PRs (31-40)

Will continue with procedural memory, API gateway, observability, security, and deployment in similar small chunks. Each PR targeting 300-500 lines.

---

## Progress Tracking

### Phase 1: Foundation ✅

- [x] PR #1: Project Foundation & CI/CD
- [x] PR #2: Database Setup & Migrations
- [x] PR #3: Shared Infrastructure (too large)

### Phase 2: Initialization (PRs 4-5)

- [ ] PR #4: Qdrant Initialization
- [ ] PR #5: RabbitMQ Initialization

### Phase 3: Sessions Service (PRs 6-11)

- [ ] PR #6: Sessions DB Models
- [ ] PR #7: Sessions Event Models
- [ ] PR #8: Sessions Business Logic
- [ ] PR #9: Sessions FastAPI Setup
- [ ] PR #10: Sessions CRUD API
- [ ] PR #11: Sessions Events/State API

### Phase 4: Memory Service Core (PRs 12-17)

- [ ] PR #12: Memory DB Models
- [ ] PR #13: Memory Revision Models
- [ ] PR #14: Memory Business Logic
- [ ] PR #15: Memory FastAPI Setup
- [ ] PR #16: Memory CRUD API
- [ ] PR #17: Memory Revisions API

### Phase 5: Vector Search (PRs 18-21)

- [ ] PR #18: Qdrant Client Wrapper
- [ ] PR #19: Embedding Generation
- [ ] PR #20: Memory Vector Integration
- [ ] PR #21: Memory Search API

### Phase 6: Extraction (PRs 22-27)

- [ ] PR #22: LLM Client Wrapper
- [ ] PR #23: LLM Prompts & Parsers
- [ ] PR #24: Extraction Worker Structure
- [ ] PR #25: Extraction Engine
- [ ] PR #26: Memory Job Management
- [ ] PR #27: Memory Generation API

### Phase 7: Consolidation (PRs 28-30)

- [ ] PR #28: Duplicate Detection
- [ ] PR #29: Conflict Resolution
- [ ] PR #30: Consolidation Pipeline

---

## PR Size Summary

| Size Range | Count | Percentage |
|------------|-------|------------|
| <300 lines | 10 | 33% |
| 300-400 lines | 15 | 50% |
| 400-500 lines | 5 | 17% |
| >500 lines | 0 | 0% |

**Average PR Size**: ~340 lines
**Maximum PR Size**: ~400 lines

---

## Lessons Learned

### From PR #3 (4,495 lines)

- ❌ **Too large**: Difficult to review
- ❌ **Too complex**: Multiple unrelated components
- ❌ **Too risky**: More chance of bugs
- ✅ **Should have been**: 8-10 smaller PRs

### New Approach

- ✅ **One component per PR**: Single focused change
- ✅ **Strict size limit**: 300-500 lines target
- ✅ **Better reviewability**: Easier to understand
- ✅ **Faster iteration**: Quicker feedback cycles

---

**Document Version**: 2.0 - Restructured for smaller PRs
**Last Updated**: December 4, 2025
