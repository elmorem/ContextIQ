# Memory Lifecycle Guide

**Complete guide to how ContextIQ transforms sessions into memories through extraction and consolidation**

## Table of Contents

- [Overview](#overview)
- [Architecture Overview](#architecture-overview)
- [Phase 1: Session Events Collection](#phase-1-session-events-collection)
- [Phase 2: Memory Extraction](#phase-2-memory-extraction)
- [Phase 3: Embedding Generation](#phase-3-embedding-generation)
- [Phase 4: Memory Storage](#phase-4-memory-storage)
- [Phase 5: Memory Consolidation](#phase-5-memory-consolidation)
- [Phase 6: Memory Retrieval](#phase-6-memory-retrieval)
- [End-to-End Flow Diagrams](#end-to-end-flow-diagrams)
- [Data Models](#data-models)
- [Configuration Reference](#configuration-reference)
- [Code Examples](#code-examples)
- [Memory Quality](#memory-quality)
- [Performance Considerations](#performance-considerations)
- [Monitoring & Observability](#monitoring-observability)
- [Production Best Practices](#production-best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)

## Overview

### What is the Memory Lifecycle?

The memory lifecycle in ContextIQ is the complete journey from raw conversation data to structured, consolidated long-term memories. This process transforms ephemeral session events into durable, searchable knowledge that can be retrieved and used across conversations.

### Why Memory Extraction and Consolidation Matter

**Memory Extraction** solves the problem of information overload. Rather than storing every word of every conversation, ContextIQ intelligently extracts key facts, preferences, and insights using LLM-powered analysis. This creates a compact, meaningful representation of what matters.

**Memory Consolidation** solves the problem of redundancy and conflicts. As conversations accumulate, similar memories emerge. Consolidation merges duplicates, detects contradictions, and maintains a clean, high-quality memory store.

### The Six Phases

The memory lifecycle consists of six distinct phases:

1. **Session Events Collection** - Conversations are captured as structured events
2. **Memory Extraction** - LLM analyzes conversations to extract key facts
3. **Embedding Generation** - Facts are converted to vector representations
4. **Memory Storage** - Memories are persisted with embeddings
5. **Memory Consolidation** - Similar memories are merged, conflicts detected
6. **Memory Retrieval** - Memories are searched and ranked by relevance

Each phase builds on the previous, creating a robust pipeline from conversation to knowledge.

### Key Benefits

- **Intelligent Extraction**: Only meaningful information is preserved
- **Semantic Understanding**: Vector embeddings enable similarity search
- **Deduplication**: Consolidation prevents memory bloat
- **Conflict Detection**: Contradictory information is identified
- **Scalability**: Asynchronous processing handles high volume
- **Quality**: Confidence scores ensure reliable memories

---

## Architecture Overview

### System Components

The memory lifecycle involves multiple services working together:

```
┌─────────────────┐
│  Sessions API   │  Stores conversation events
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    RabbitMQ     │  Message queue for async processing
│  EXTRACTION_    │
│   REQUESTS      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Memory          │  Extracts facts from conversations
│ Generation      │  using LLM (Anthropic Claude)
│ Worker          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embedding      │  Generates vector representations
│  Service        │  using OpenAI embeddings
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Memory API     │  Persists memories
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Qdrant Vector Store    │  Stores embeddings
└─────────────────────────┘

         │
         ▼
┌─────────────────┐
│    RabbitMQ     │  Consolidation trigger
│ CONSOLIDATION_  │
│   REQUESTS      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Consolidation   │  Merges similar memories
│ Worker          │  Detects conflicts
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Memory API     │  Updates with merged memories
└─────────────────┘
```

### Component Interactions

1. **Sessions Service** → **RabbitMQ** - When a session is ready for extraction, publishes to EXTRACTION_REQUESTS queue
2. **Memory Generation Worker** → **Sessions Service** - Fetches conversation events via HTTP API
3. **Memory Generation Worker** → **Extraction Engine** - Sends events to LLM for analysis
4. **Memory Generation Worker** → **Embedding Service** - Generates vectors for extracted memories
5. **Memory Generation Worker** → **Memory Service** - Saves memories with embeddings
6. **Memory Service** → **Qdrant** - Stores vector embeddings for similarity search
7. **Consolidation Worker** → **Memory Service** - Fetches memories for consolidation
8. **Consolidation Worker** → **Consolidation Engine** - Finds duplicates and merges
9. **Consolidation Worker** → **Memory Service** - Saves consolidated memories

### Message Flow Through RabbitMQ

The system uses RabbitMQ for asynchronous, reliable processing:

**Extraction Queue**:
- Queue: `extraction.requests`
- Exchange: `contextiq.extraction`
- Routing Key: `extraction.request`
- Message: `{session_id, user_id, scope}`

**Consolidation Queue**:
- Queue: `consolidation.requests`
- Exchange: `contextiq.consolidation`
- Routing Key: `consolidation.request`
- Message: `{scope, user_id, max_memories, detect_conflicts}`

---

## Phase 1: Session Events Collection

### How Conversations Are Captured

Every interaction in a conversation is stored as a structured event in the Sessions Service. Events capture both the content and metadata of each exchange.

### Event Structure

Each session event has this structure:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "event_type": "user_message",
  "data": {
    "content": "I really enjoy hiking in the mountains",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "created_at": "2025-01-15T10:30:01Z"
}
```

**Event Types**:
- `user_message` - User input
- `agent_message` - Agent response
- `system_message` - System notifications
- `tool_call` - Tool invocation
- `tool_result` - Tool output

### Sessions Service API

**Create Event**:
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/api/v1/sessions/{session_id}/events",
        json={
            "event_type": "user_message",
            "data": {
                "content": "I prefer dark roast coffee"
            }
        }
    )
```

**List Events**:
```python
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8001/api/v1/sessions/{session_id}/events",
        params={"limit": 1000}
    )
    events = response.json()["events"]
```

### When to Trigger Extraction

Extraction can be triggered:

1. **Manually** - API call to trigger extraction for a session
2. **Scheduled** - Periodic extraction of active sessions
3. **Event-based** - After N events or conversation end
4. **On-demand** - When user requests memory generation

---

## Phase 2: Memory Extraction

Memory extraction is the core intelligence of the lifecycle. It transforms raw conversation events into structured, meaningful memories using LLM-powered analysis.

### Memory Generation Worker

The Memory Generation Worker is a background service that consumes extraction requests from RabbitMQ and orchestrates the extraction pipeline.

#### Worker Architecture

Located in `workers/memory_generation/worker.py`:

```python
class MemoryGenerationWorker:
    """
    Worker for processing memory generation requests.

    Consumes messages from RabbitMQ and orchestrates the memory extraction,
    embedding generation, and storage pipeline.
    """

    def __init__(
        self,
        worker_settings: WorkerSettings | None = None,
        extraction_settings: ExtractionSettings | None = None,
        embedding_settings: EmbeddingSettings | None = None,
        qdrant_settings: QdrantSettings | None = None,
        messaging_settings: MessagingSettings | None = None,
        http_client_settings: HTTPClientSettings | None = None,
    ):
        # Initialize services
        self.extraction_engine = ExtractionEngine(settings=extraction_settings)
        self.embedding_service = EmbeddingService(settings=embedding_settings)
        self.vector_store = QdrantClientWrapper(settings=qdrant_settings)

        # Initialize HTTP service clients
        self.sessions_client = SessionsServiceClient(...)
        self.memory_client = MemoryServiceClient(...)

        # Initialize processor
        self.processor = MemoryGenerationProcessor(
            extraction_engine=self.extraction_engine,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            sessions_client=self.sessions_client,
            memory_client=self.memory_client,
        )

        # Initialize RabbitMQ
        self.rabbitmq_client = RabbitMQClient(url=messaging_settings.rabbitmq_url)
        self.consumer = MessageConsumer(client=self.rabbitmq_client)
```

#### Worker Lifecycle

**Start**:
```python
async def start(self) -> None:
    """Start the worker and begin consuming messages."""
    logger.info(f"Starting {self.worker_settings.worker_name}")

    # Connect to RabbitMQ
    await self.rabbitmq_client.connect()

    # Start consuming messages from extraction requests queue
    await self.consumer.run_consumer(
        queue_config=Queues.EXTRACTION_REQUESTS,
        handler=self.handle_message,
        auto_ack=False,
        prefetch_count=self.worker_settings.worker_prefetch_count,
    )
```

**Handle Message**:
```python
async def handle_message(
    self,
    message_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle incoming memory generation request message."""
    # Parse request
    request = MemoryGenerationRequest(**message_data)

    logger.info(f"Received memory generation request for session {request.session_id}")

    # Validate request
    is_valid, error = self.processor.validate_request(request)
    if not is_valid:
        raise ValueError(f"Invalid request: {error}")

    # Process the request
    result = await self.processor.process_request(request)

    if result.success:
        logger.info(
            f"Successfully processed session {request.session_id}: "
            f"{result.memories_extracted} memories extracted"
        )
        return {
            "session_id": str(result.session_id),
            "memories_extracted": result.memories_extracted,
            "success": True,
        }
    else:
        raise RuntimeError(f"Processing failed: {result.error}")
```

### Memory Generation Processor

The processor orchestrates the complete extraction pipeline. Located in `workers/memory_generation/processor.py`:

#### Step 1: Fetch Events from Sessions Service

```python
async def process_request(
    self,
    request: MemoryGenerationRequest,
) -> MemoryGenerationResult:
    """Process memory generation request."""

    # Step 1: Fetch conversation events
    logger.info(f"Fetching events for session {request.session_id}")

    events_response = await self.sessions_client.list_events(
        session_id=request.session_id,
        limit=1000  # Get all events for the session
    )

    # Transform events into format expected by extraction engine
    conversation_events = [
        {
            "speaker": event.get("event_type", "user"),
            "content": event.get("data", {}).get("content", ""),
        }
        for event in events_response.get("events", [])
        if event.get("data", {}).get("content")
    ]

    logger.info(
        f"Retrieved {len(conversation_events)} events from session {request.session_id}"
    )
```

#### Step 2: Extract Memories Using ExtractionEngine

```python
    # Step 2: Extract memories from conversation
    extraction_result = self.extraction_engine.extract_memories(
        conversation_events=conversation_events,
        min_confidence=0.5,
    )

    if extraction_result.error:
        return MemoryGenerationResult(
            session_id=request.session_id,
            user_id=request.user_id,
            success=False,
            error=f"Extraction failed: {extraction_result.error}",
        )

    if extraction_result.memory_count == 0:
        logger.info(f"No memories extracted for session {request.session_id}")
        return MemoryGenerationResult(
            session_id=request.session_id,
            user_id=request.user_id,
            success=True,
            memories_extracted=0,
        )

    logger.info(
        f"Extracted {extraction_result.memory_count} memories "
        f"for session {request.session_id}"
    )
```

#### Step 3: Generate Embeddings

```python
    # Step 3: Generate embeddings for extracted memories
    memory_texts = [mem["fact"] for mem in extraction_result.memories]
    embedding_result = self.embedding_service.generate_embeddings(memory_texts)

    if embedding_result.error:
        return MemoryGenerationResult(
            session_id=request.session_id,
            user_id=request.user_id,
            memories_extracted=extraction_result.memory_count,
            success=False,
            error=f"Embedding generation failed: {embedding_result.error}",
        )

    logger.info(
        f"Generated {embedding_result.count} embeddings "
        f"for session {request.session_id}"
    )
```

#### Step 4: Save to Memory Service

```python
    # Step 4: Store memories to Memory Service
    saved_count = 0

    # Build scope based on request
    scope = {}
    if request.scope == "user":
        scope["user_id"] = str(request.user_id)

    # Save each memory with its embedding
    for idx, memory_data in enumerate(extraction_result.memories):
        try:
            # Get corresponding embedding
            embedding = (
                embedding_result.embeddings[idx]
                if idx < len(embedding_result.embeddings)
                else None
            )

            # Create memory via Memory Service
            await self.memory_client.create_memory(
                scope=scope,
                fact=memory_data["fact"],
                source_type="extracted",
                source_id=str(request.session_id),
                topic=memory_data.get("topic"),
                embedding=embedding,
                confidence=memory_data.get("confidence", 1.0),
                importance=memory_data.get("importance", 0.5),
            )
            saved_count += 1

        except Exception as e:
            logger.error(f"Failed to save memory {idx + 1}: {e}")

    return MemoryGenerationResult(
        session_id=request.session_id,
        user_id=request.user_id,
        memories_extracted=extraction_result.memory_count,
        memories_saved=saved_count,
        embeddings_generated=embedding_result.count,
        success=True,
    )
```

### Extraction Engine

The Extraction Engine is the core LLM-powered component that analyzes conversations and extracts structured memories. Located in `shared/extraction/engine.py`:

#### Engine Architecture

```python
class ExtractionEngine:
    """
    Core engine for extracting memories from conversation events.

    Handles batching, LLM interaction, and result parsing for
    memory generation operations.
    """

    def __init__(
        self,
        settings: ExtractionSettings | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.settings = settings or get_extraction_settings()
        self.llm_client = llm_client or LLMClient(settings=self.settings)
```

#### Extract Memories Method

```python
def extract_memories(
    self,
    conversation_events: list[dict[str, str]],
    min_confidence: float = 0.5,
) -> ExtractionResult:
    """
    Extract memories from conversation events.

    Args:
        conversation_events: List of events with 'speaker' and 'content'
        min_confidence: Minimum confidence threshold for extracted memories

    Returns:
        ExtractionResult with extracted memories and metadata
    """
    # Validate input
    if not conversation_events:
        raise ValueError("conversation_events cannot be empty")

    if len(conversation_events) < self.settings.extraction_min_events:
        return ExtractionResult(
            memories=[],
            error=f"Insufficient events: need at least {self.settings.extraction_min_events}",
        )

    try:
        # Build extraction prompt
        prompt = build_extraction_prompt(
            conversation_events=conversation_events,
            include_few_shot=self.settings.use_few_shot,
            max_examples=self.settings.max_few_shot_examples,
        )

        # Call LLM for extraction
        response = self.llm_client.extract_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_message=prompt,
            response_schema=EXTRACTION_RESPONSE_SCHEMA,
        )

        # Extract and filter memories
        raw_memories = response.get("memories", [])
        filtered_memories = self._filter_by_confidence(
            memories=raw_memories,
            min_confidence=min_confidence,
        )

        # Limit to max facts
        if len(filtered_memories) > self.settings.extraction_max_facts:
            filtered_memories = filtered_memories[:self.settings.extraction_max_facts]

        return ExtractionResult(
            memories=filtered_memories,
            raw_response=str(response),
        )

    except Exception as e:
        return ExtractionResult(
            memories=[],
            error=f"Extraction failed: {e}",
        )
```

#### LLM-Powered Extraction with Anthropic Claude

The extraction engine uses Anthropic's Claude model for structured extraction:

**System Prompt** (from `shared/extraction/prompts.py`):
```python
EXTRACTION_SYSTEM_PROMPT = """
You are an expert at analyzing conversations and extracting key facts,
preferences, and insights about users. Your task is to identify memorable
information that would be useful in future conversations.

Extract facts that are:
- Specific and actionable
- Likely to remain relevant over time
- Verifiable from the conversation
- Useful for personalization

Categorize each fact appropriately and assign a confidence score based on
how certain you are about the information.
"""
```

**Response Schema**:
```python
EXTRACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "memories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "preference",
                            "fact",
                            "goal",
                            "habit",
                            "relationship",
                            "professional",
                            "location",
                            "temporal"
                        ]
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "topic": {"type": "string"},
                    "importance": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["fact", "category", "confidence"]
            }
        }
    },
    "required": ["memories"]
}
```

#### Memory Categories

The extraction engine classifies memories into 8 categories:

1. **preference** - User likes/dislikes, choices
   - Example: "User prefers dark roast coffee"

2. **fact** - Objective information about the user
   - Example: "User lives in Seattle"

3. **goal** - User aspirations and objectives
   - Example: "User wants to learn Spanish"

4. **habit** - Recurring behaviors and routines
   - Example: "User exercises every morning"

5. **relationship** - Information about user's relationships
   - Example: "User has a sister named Sarah"

6. **professional** - Work-related information
   - Example: "User works as a software engineer"

7. **location** - Geographic information
   - Example: "User frequently visits New York"

8. **temporal** - Time-based information
   - Example: "User's birthday is June 15th"

#### Confidence Filtering

```python
def _filter_by_confidence(
    self,
    memories: list[dict[str, Any]],
    min_confidence: float,
) -> list[dict[str, Any]]:
    """Filter memories by confidence threshold."""
    return [
        memory for memory in memories
        if memory.get("confidence", 0.0) >= min_confidence
    ]
```

#### Memory Validation

```python
def validate_memory(self, memory: dict[str, Any]) -> bool:
    """Validate a single memory dictionary."""
    required_fields = ["fact", "category", "confidence"]

    # Check required fields
    if not all(field in memory for field in required_fields):
        return False

    # Validate confidence range
    confidence = memory.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        return False

    # Validate category
    valid_categories = {
        "preference", "fact", "goal", "habit",
        "relationship", "professional", "location", "temporal"
    }
    if memory.get("category") not in valid_categories:
        return False

    # Validate fact is non-empty string
    fact = memory.get("fact")
    if not isinstance(fact, str) or not fact.strip():
        return False

    return True
```

### Example: Complete Extraction Flow

```python
# Example conversation events
conversation_events = [
    {
        "speaker": "user",
        "content": "I really enjoy hiking in the mountains on weekends"
    },
    {
        "speaker": "agent",
        "content": "That sounds wonderful! What's your favorite trail?"
    },
    {
        "speaker": "user",
        "content": "I love the Pacific Crest Trail. I try to go at least twice a month."
    },
    {
        "speaker": "agent",
        "content": "How long have you been hiking?"
    },
    {
        "speaker": "user",
        "content": "For about 5 years now. I started after moving to Oregon."
    }
]

# Extract memories
extraction_engine = ExtractionEngine()
result = extraction_engine.extract_memories(
    conversation_events=conversation_events,
    min_confidence=0.5
)

# Extracted memories would include:
# [
#     {
#         "fact": "User enjoys hiking in the mountains on weekends",
#         "category": "preference",
#         "confidence": 0.95,
#         "topic": "outdoor activities",
#         "importance": 0.7
#     },
#     {
#         "fact": "User loves the Pacific Crest Trail",
#         "category": "preference",
#         "confidence": 0.95,
#         "topic": "hiking",
#         "importance": 0.7
#     },
#     {
#         "fact": "User hikes at least twice a month",
#         "category": "habit",
#         "confidence": 0.9,
#         "topic": "hiking frequency",
#         "importance": 0.6
#     },
#     {
#         "fact": "User has been hiking for 5 years",
#         "category": "fact",
#         "confidence": 0.95,
#         "topic": "hiking experience",
#         "importance": 0.5
#     },
#     {
#         "fact": "User moved to Oregon 5 years ago",
#         "category": "location",
#         "confidence": 0.9,
#         "topic": "residence",
#         "importance": 0.6
#     }
# ]
```

---

## Phase 3: Embedding Generation

After memories are extracted, they need to be converted into vector representations for semantic search. This is handled by the Embedding Service.

### OpenAI text-embedding-3-small

ContextIQ uses OpenAI's `text-embedding-3-small` model for generating embeddings:

- **Model**: text-embedding-3-small
- **Dimensions**: 1536 (configurable 256-3072)
- **Max Input**: 8191 tokens
- **Cost**: $0.02 per 1M tokens
- **Speed**: ~1000 texts per second (batch)

### Integration with Extraction Pipeline

In the Memory Generation Processor (Phase 2, Step 3):

```python
# Generate embeddings for extracted memories
memory_texts = [mem["fact"] for mem in extraction_result.memories]
embedding_result = self.embedding_service.generate_embeddings(memory_texts)

# Result contains list of 1536-dimensional vectors
# embedding_result.embeddings = [[0.123, -0.456, ...], [0.789, ...], ...]
```

### Batch Processing

The embedding service efficiently handles batch processing:

```python
from shared.embedding import EmbeddingService

embedding_service = EmbeddingService()

# Batch of memory facts
facts = [
    "User prefers dark roast coffee",
    "User lives in Seattle",
    "User works as a software engineer"
]

# Generate embeddings for all facts at once
result = embedding_service.generate_embeddings(facts)

if result.success:
    print(f"Generated {result.count} embeddings")
    # result.embeddings is a list of 1536-dimensional vectors
    for idx, embedding in enumerate(result.embeddings):
        print(f"Memory {idx}: vector with {len(embedding)} dimensions")
```

### Why Embeddings Matter

Embeddings enable semantic search - finding memories based on meaning rather than exact keyword matches:

**Example**: If a user asks "What kind of beverages do I like?", the system can find the memory "User prefers dark roast coffee" even though the words "beverages" and "coffee" don't match exactly.

The embedding vectors capture semantic similarity:
- "coffee" and "beverages" have similar embeddings
- "dark roast" and "strong coffee" are semantically close
- Enables finding related memories even with different wording

---

## Phase 4: Memory Storage

Once memories are extracted and embeddings generated, they're persisted in two places: the Memory Service database and the Qdrant vector store.

### Memory Service API

The Memory Service provides a REST API for creating and managing memories:

**Create Memory**:
```python
await memory_client.create_memory(
    scope={"user_id": "user_123"},
    fact="User prefers dark roast coffee",
    source_type="extracted",
    source_id="session_456",
    topic="beverages",
    embedding=[0.123, -0.456, ...],  # 1536-dimensional vector
    confidence=0.95,
    importance=0.7,
)
```

**Response**:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "scope": {
    "user_id": "user_123"
  },
  "fact": "User prefers dark roast coffee",
  "source_type": "extracted",
  "source_id": "session_456",
  "topic": "beverages",
  "confidence": 0.95,
  "importance": 0.7,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Scope-Based Storage

Memories are organized by scope for multi-tenancy:

**User Scope**:
```python
scope = {"user_id": "user_123"}
```
- Memories belong to a specific user
- Most common scope type
- Used for personal preferences and facts

**Organization Scope**:
```python
scope = {"org_id": "org_456"}
```
- Shared across an organization
- Used for company-wide knowledge

**Global Scope**:
```python
scope = {"type": "global"}
```
- Available to all users
- Used for general knowledge

### Qdrant Vector Storage

Embeddings are stored in Qdrant for fast similarity search:

**Collection Configuration**:
```python
collection_name = "memories"
vector_size = 1536  # OpenAI text-embedding-3-small
distance_metric = "cosine"
```

**Storage Process**:
```python
# Memory Service automatically stores embedding in Qdrant
await vector_store.upsert_points(
    collection_name="memories",
    points=[
        {
            "id": str(memory.id),
            "vector": embedding,
            "payload": {
                "memory_id": str(memory.id),
                "user_id": "user_123",
                "fact": "User prefers dark roast coffee",
                "confidence": 0.95,
                "topic": "beverages"
            }
        }
    ]
)
```

### Database Persistence

The Memory Service stores structured memory data in PostgreSQL:

**Schema**:
```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    scope_user_id UUID,
    scope_org_id UUID,
    fact TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    topic VARCHAR(255),
    confidence FLOAT NOT NULL,
    importance FLOAT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
);
```

**Metadata Storage**:
```python
metadata = {
    "category": "preference",
    "source_session_id": "session_456",
    "extraction_timestamp": "2025-01-15T10:30:00Z",
    "llm_model": "claude-3-5-sonnet-20240620"
}
```

---

## Phase 5: Memory Consolidation

As conversations accumulate, similar memories emerge. Consolidation merges duplicates, detects conflicts, and maintains memory quality.

### Consolidation Worker

The Consolidation Worker is a background service that processes consolidation requests. Located in `workers/consolidation/worker.py`:

#### Worker Architecture

```python
class ConsolidationWorker:
    """
    Worker for processing consolidation requests.

    Consumes messages from RabbitMQ and orchestrates memory consolidation pipeline.
    """

    def __init__(
        self,
        worker_settings: ConsolidationWorkerSettings | None = None,
        consolidation_settings: ConsolidationSettings | None = None,
        embedding_settings: EmbeddingSettings | None = None,
        messaging_settings: MessagingSettings | None = None,
        http_client_settings: HTTPClientSettings | None = None,
    ):
        # Initialize services
        self.consolidation_engine = ConsolidationEngine(settings=consolidation_settings)
        self.embedding_service = EmbeddingService(settings=embedding_settings)

        # Initialize HTTP service client
        self.memory_client = MemoryServiceClient(...)

        # Initialize processor
        self.processor = ConsolidationProcessor(
            consolidation_engine=self.consolidation_engine,
            embedding_service=self.embedding_service,
            memory_client=self.memory_client,
        )

        # Initialize RabbitMQ
        self.rabbitmq_client = RabbitMQClient(url=messaging_settings.rabbitmq_url)
        self.consumer = MessageConsumer(client=self.rabbitmq_client)
```

#### Start Consuming

```python
async def start(self) -> None:
    """Start the worker and begin consuming messages."""
    # Connect to RabbitMQ
    await self.rabbitmq_client.connect()

    # Start consuming messages from consolidation requests queue
    await self.consumer.run_consumer(
        queue_config=Queues.CONSOLIDATION_REQUESTS,
        handler=self.handle_message,
        auto_ack=False,
        prefetch_count=self.worker_settings.worker_prefetch_count,
    )
```

### Consolidation Processor

The processor orchestrates the consolidation pipeline. Located in `workers/consolidation/processor.py`:

#### Step 1: Fetch Memories from Memory Service

```python
async def process_request(
    self,
    request: ConsolidationRequest,
) -> ConsolidationResult:
    """Process consolidation request."""

    # Step 1: Fetch memories for the scope
    logger.info(f"Fetching memories for scope {request.scope}")

    # Build query parameters based on scope
    scope_type = request.scope.get("type")
    query_params = {"limit": request.max_memories}

    if scope_type == "user" and request.user_id:
        query_params["scope_user_id"] = str(request.user_id)
    elif scope_type == "org" and request.scope.get("org_id"):
        query_params["scope_org_id"] = request.scope["org_id"]

    # Fetch memories from Memory Service
    memories_response = await self.memory_client.list_memories(**query_params)
    memories = memories_response.get("memories", [])

    logger.info(f"Retrieved {len(memories)} memories from Memory Service")
```

#### Step 2: Convert to Consolidation Format

```python
    # Convert to consolidation Memory format
    from shared.consolidation.engine import Memory

    consolidation_memories = [
        Memory(
            id=UUID(mem.get("id")),
            fact=mem.get("fact", ""),
            confidence=mem.get("confidence", 0.0),
            embedding=mem.get("embedding", []),
            source_session_id=(
                UUID(mem["source_session_id"])
                if mem.get("source_session_id")
                else None
            ),
            metadata=mem.get("metadata"),
        )
        for mem in memories
    ]
```

#### Step 3: Run Consolidation Engine

```python
    # Run consolidation engine
    consolidation_result = self.consolidation_engine.consolidate_memories(
        memories=consolidation_memories,
        detect_conflicts=request.detect_conflicts,
    )

    if not consolidation_result.success:
        return ConsolidationResult(
            scope=request.scope,
            memories_processed=len(memories),
            success=False,
            error=f"Consolidation failed: {consolidation_result.error}",
        )

    logger.info(
        f"Consolidation complete: {consolidation_result.merge_count} merges, "
        f"{consolidation_result.conflict_count} conflicts"
    )
```

#### Step 4: Generate Embeddings for Merged Memories

```python
    # Generate embeddings for merged memories
    merged_embeddings = []
    if consolidation_result.merged_memories:
        merged_facts = [m.fact for m in consolidation_result.merged_memories]
        embedding_result = self.embedding_service.generate_embeddings(merged_facts)

        if not embedding_result.error:
            merged_embeddings = embedding_result.embeddings
```

#### Step 5: Save Consolidated Memories

```python
    # Save consolidated memories to Memory Service
    memories_updated = 0

    # Build scope dict
    scope_dict = {}
    if scope_type == "user" and request.user_id:
        scope_dict["user_id"] = str(request.user_id)

    # Save each merged memory
    for idx, merged_memory in enumerate(consolidation_result.merged_memories):
        try:
            embedding = merged_embeddings[idx] if idx < len(merged_embeddings) else None

            # Create consolidated memory
            await self.memory_client.create_memory(
                scope=scope_dict,
                fact=merged_memory.fact,
                source_type="consolidated",
                embedding=embedding,
                confidence=merged_memory.confidence,
                importance=0.7,  # Consolidated memories are typically important
            )
            memories_updated += 1

        except Exception as e:
            logger.error(f"Failed to save consolidated memory {idx + 1}: {e}")
```

### Consolidation Engine

The Consolidation Engine implements similarity detection and memory merging. Located in `shared/consolidation/engine.py`:

#### Engine Architecture

```python
class ConsolidationEngine:
    """
    Engine for consolidating memories.

    Handles similarity detection, duplicate merging, and conflict resolution
    for memory management.
    """

    def __init__(self, settings: ConsolidationSettings | None = None):
        self.settings = settings or get_consolidation_settings()
        logger.info(
            f"Consolidation engine initialized with "
            f"similarity_threshold={self.settings.similarity_threshold}, "
            f"merge_strategy={self.settings.merge_strategy}"
        )
```

#### Consolidate Memories Method

```python
def consolidate_memories(
    self,
    memories: list[Memory],
    detect_conflicts: bool = True,
) -> ConsolidationResult:
    """Consolidate a list of memories by detecting and merging duplicates."""

    if len(memories) < 2:
        return ConsolidationResult(
            memories_processed=len(memories),
            success=True,
        )

    # Find merge candidates
    merge_candidates = self._find_merge_candidates(memories)

    if not merge_candidates:
        return ConsolidationResult(
            memories_processed=len(memories),
            success=True,
        )

    # Separate conflicts from mergeable pairs
    conflicts = []
    mergeable = []

    for candidate in merge_candidates:
        if detect_conflicts and candidate.is_conflict:
            conflicts.append(candidate)
        else:
            mergeable.append(candidate)

    # Merge similar memories
    merged_memories = []
    for candidate in mergeable:
        merged = self._merge_memories(candidate.memory1, candidate.memory2)
        merged_memories.append(merged)

    return ConsolidationResult(
        merged_memories=merged_memories,
        conflicts_detected=conflicts,
        memories_processed=len(memories),
        memories_merged=len(merged_memories) * 2,
        success=True,
    )
```

#### Find Merge Candidates

```python
def _find_merge_candidates(
    self,
    memories: list[Memory],
) -> list[MergeCandidate]:
    """Find pairs of memories that are candidates for merging."""
    candidates = []

    # Compare each pair of memories
    for i, memory1 in enumerate(memories):
        for memory2 in memories[i + 1:]:
            similarity = self._calculate_similarity(memory1, memory2)

            # Check if similar enough to merge
            if similarity >= self.settings.similarity_threshold:
                is_conflict = self._is_conflicting(memory1, memory2, similarity)

                candidates.append(
                    MergeCandidate(
                        memory1=memory1,
                        memory2=memory2,
                        similarity_score=similarity,
                        is_conflict=is_conflict,
                    )
                )

    return candidates
```

#### Calculate Similarity (Cosine Similarity)

```python
def _calculate_similarity(self, memory1: Memory, memory2: Memory) -> float:
    """Calculate cosine similarity between two memories."""
    if not memory1.embedding or not memory2.embedding:
        return 0.0

    # Cosine similarity formula:
    # similarity = (A · B) / (||A|| × ||B||)

    # Dot product
    dot_product = sum(
        a * b
        for a, b in zip(memory1.embedding, memory2.embedding, strict=False)
    )

    # Magnitudes
    magnitude1 = sum(a * a for a in memory1.embedding) ** 0.5
    magnitude2 = sum(b * b for b in memory2.embedding) ** 0.5

    if magnitude1 == 0.0 or magnitude2 == 0.0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)
```

**Cosine Similarity Explained**:

Cosine similarity measures the angle between two vectors:
- Score of 1.0 = Identical direction (very similar)
- Score of 0.0 = Perpendicular (unrelated)
- Score of -1.0 = Opposite direction (contradictory)

For memory consolidation:
- similarity ≥ 0.85 = Strong candidates for merging
- 0.7 ≤ similarity < 0.85 = Possible conflicts
- similarity < 0.7 = Different memories

#### Detect Conflicts

```python
def _is_conflicting(
    self,
    memory1: Memory,
    memory2: Memory,
    similarity: float,
) -> bool:
    """Determine if two similar memories are conflicting."""
    # Memories are conflicting if:
    # 1. Similarity is above conflict threshold but below merge threshold
    # 2. Facts are substantively different

    if self.settings.conflict_threshold <= similarity < self.settings.similarity_threshold:
        # Check if facts are different
        return memory1.fact.lower() != memory2.fact.lower()

    return False
```

**Example Conflict**:
- Memory 1: "User prefers morning coffee"
- Memory 2: "User avoids coffee in the morning"
- Similarity: 0.75 (similar topic, different meaning)
- Result: Flagged as conflict

#### Merge Memories

```python
def _merge_memories(self, memory1: Memory, memory2: Memory) -> MergedMemory:
    """Merge two similar memories into one."""
    strategy = self.settings.merge_strategy

    if strategy == "highest_confidence":
        if memory1.confidence >= memory2.confidence:
            selected_fact = memory1.fact
            base_confidence = memory1.confidence
        else:
            selected_fact = memory2.fact
            base_confidence = memory2.confidence

    elif strategy == "most_recent":
        # Assume memory1 is more recent if no timestamp
        selected_fact = memory1.fact
        base_confidence = memory1.confidence

    elif strategy == "longest":
        if len(memory1.fact) >= len(memory2.fact):
            selected_fact = memory1.fact
            base_confidence = memory1.confidence
        else:
            selected_fact = memory2.fact
            base_confidence = memory2.confidence

    # Apply confidence boost for merged memories
    merged_confidence = min(
        1.0,
        base_confidence + self.settings.merged_confidence_boost,
    )

    return MergedMemory(
        fact=selected_fact,
        confidence=merged_confidence,
        source_memory_ids=[memory1.id, memory2.id],
        merge_reason=f"Merged using {strategy} strategy",
    )
```

### Merge Strategies

Three strategies for choosing which memory to keep:

1. **highest_confidence** (default) - Keep the memory with higher confidence score
   ```python
   # Memory 1: confidence=0.9
   # Memory 2: confidence=0.7
   # Result: Keep Memory 1's fact
   ```

2. **most_recent** - Keep the most recently created memory
   ```python
   # Memory 1: created_at=2025-01-15
   # Memory 2: created_at=2025-01-10
   # Result: Keep Memory 1's fact
   ```

3. **longest** - Keep the memory with more detailed information
   ```python
   # Memory 1: "User likes coffee"
   # Memory 2: "User likes strong dark roast coffee in the morning"
   # Result: Keep Memory 2's fact
   ```

### Confidence Boost

Merged memories receive a confidence boost since they're supported by multiple observations:

```python
# Configuration
merged_confidence_boost = 0.1

# Example
original_confidence = 0.8
merged_confidence = min(1.0, 0.8 + 0.1)  # = 0.9
```

### Example: Complete Consolidation Flow

```python
# Example memories to consolidate
memories = [
    Memory(
        id=UUID("mem1"),
        fact="User enjoys hiking",
        confidence=0.8,
        embedding=[0.1, 0.2, ...],  # 1536 dimensions
    ),
    Memory(
        id=UUID("mem2"),
        fact="User loves hiking in mountains",
        confidence=0.9,
        embedding=[0.11, 0.21, ...],  # Similar to mem1
    ),
    Memory(
        id=UUID("mem3"),
        fact="User dislikes running",
        confidence=0.85,
        embedding=[-0.5, -0.3, ...],  # Different from hiking
    ),
]

# Run consolidation
consolidation_engine = ConsolidationEngine()
result = consolidation_engine.consolidate_memories(
    memories=memories,
    detect_conflicts=True
)

# Result:
# merged_memories = [
#     MergedMemory(
#         fact="User loves hiking in mountains",  # Higher confidence memory kept
#         confidence=1.0,  # 0.9 + 0.1 boost
#         source_memory_ids=[UUID("mem1"), UUID("mem2")],
#         merge_reason="Merged using highest_confidence strategy"
#     )
# ]
# conflicts_detected = []  # No conflicts found
# memories_processed = 3
# memories_merged = 2
```

---

## Phase 6: Memory Retrieval

After memories are stored with embeddings, they can be retrieved using semantic search.

### Vector Search with Qdrant

Qdrant enables fast similarity search:

```python
from shared.vector_store import QdrantClientWrapper

vector_store = QdrantClientWrapper()

# Search for memories related to "coffee preferences"
query_text = "What kind of coffee does the user like?"

# Generate embedding for query
embedding_service = EmbeddingService()
query_embedding_result = embedding_service.generate_embedding(query_text)
query_vector = query_embedding_result.embedding

# Search vector store
results = vector_store.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,
    score_threshold=0.7,  # Minimum similarity
    query_filter={"user_id": "user_123"}
)

# Results are ranked by similarity:
# [
#     {
#         "id": "mem1",
#         "score": 0.92,
#         "payload": {
#             "fact": "User prefers dark roast coffee",
#             "confidence": 0.95
#         }
#     },
#     {
#         "id": "mem2",
#         "score": 0.85,
#         "payload": {
#             "fact": "User drinks coffee every morning",
#             "confidence": 0.9
#         }
#     }
# ]
```

### Metadata Filtering

Combine semantic search with metadata filters:

```python
# Find memories from specific topic
results = vector_store.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,
    query_filter={
        "user_id": "user_123",
        "topic": "beverages",
        "confidence": {"$gte": 0.8}
    }
)
```

### Memory Service API

```python
# List memories with filters
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8002/api/v1/memories",
        params={
            "scope_user_id": "user_123",
            "topic": "hiking",
            "min_confidence": 0.8,
            "limit": 20
        }
    )
    memories = response.json()["memories"]

# Search memories semantically
response = await client.post(
    "http://localhost:8002/api/v1/memories/search",
    json={
        "query": "What outdoor activities does the user enjoy?",
        "scope": {"user_id": "user_123"},
        "limit": 10,
        "min_score": 0.7
    }
)
search_results = response.json()["results"]
```

### Ranking by Relevance

Retrieved memories are ranked by:
1. **Semantic similarity** - How close the embedding vectors are
2. **Confidence** - How certain we are about the memory
3. **Importance** - How significant the memory is
4. **Recency** - How recently the memory was created/updated

Combined relevance score:
```python
relevance_score = (
    0.6 * similarity_score +
    0.2 * confidence +
    0.1 * importance +
    0.1 * recency_score
)
```

---

## End-to-End Flow Diagrams

### Complete Memory Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         MEMORY LIFECYCLE                                 │
└──────────────────────────────────────────────────────────────────────────┘

PHASE 1: Session Events Collection
┌──────────────┐
│   User       │  "I love hiking in the mountains"
│ Conversation │
└──────┬───────┘
       │
       │ Store events
       ▼
┌──────────────┐
│  Sessions    │  {event_type: "user_message", data: {content: "..."}}
│  Service     │
└──────┬───────┘
       │
       │ Trigger extraction (manual/scheduled/automatic)
       ▼
┌──────────────┐
│  RabbitMQ    │  publish({session_id, user_id, scope})
│  EXTRACTION_ │
│  REQUESTS    │
└──────┬───────┘


PHASE 2: Memory Extraction
       │
       │ consume message
       ▼
┌──────────────┐
│  Memory      │  1. Fetch events from Sessions Service
│ Generation   │  2. Extract memories with ExtractionEngine (LLM)
│  Worker      │  3. Generate embeddings with EmbeddingService
│              │  4. Save to Memory Service
└──────┬───────┘
       │
       │ LLM extraction
       ▼
┌──────────────┐
│  Extraction  │  analyze conversation
│   Engine     │  → extract structured facts
│ (Anthropic   │  → assign categories & confidence
│   Claude)    │  → return ExtractionResult
└──────┬───────┘
       │
       │ extracted memories
       ▼
┌──────────────┐
│  Embedding   │  generate 1536-dim vectors
│   Service    │  (OpenAI text-embedding-3-small)
│              │
└──────┬───────┘
       │
       │ embeddings
       ▼


PHASE 3 & 4: Storage
┌──────────────┐
│  Memory      │  create_memory(fact, embedding, confidence, ...)
│  Service     │
└──────┬───────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │   Qdrant     │  vector storage for
│  Database    │  │ Vector Store │  semantic search
│              │  │              │
└──────────────┘  └──────────────┘


PHASE 5: Consolidation (periodic/on-demand)
       │
       │ trigger consolidation
       ▼
┌──────────────┐
│  RabbitMQ    │  publish({scope, user_id, detect_conflicts})
│CONSOLIDATION_│
│  REQUESTS    │
└──────┬───────┘
       │
       │ consume message
       ▼
┌──────────────┐
│Consolidation │  1. Fetch memories from Memory Service
│   Worker     │  2. Run ConsolidationEngine
│              │  3. Generate embeddings for merged memories
│              │  4. Save consolidated memories
└──────┬───────┘
       │
       │ find duplicates
       ▼
┌──────────────┐
│Consolidation │  1. Calculate similarity (cosine)
│   Engine     │  2. Find merge candidates (>0.85)
│              │  3. Detect conflicts (0.7-0.85)
│              │  4. Merge using strategy
│              │  5. Boost confidence
└──────┬───────┘
       │
       │ merged memories
       ▼
┌──────────────┐
│  Memory      │  create_memory(source_type="consolidated")
│  Service     │
└──────────────┘


PHASE 6: Retrieval (on user query)
┌──────────────┐
│  User Query  │  "What outdoor activities do I enjoy?"
└──────┬───────┘
       │
       │ generate query embedding
       ▼
┌──────────────┐
│  Embedding   │  convert query to vector
│   Service    │
└──────┬───────┘
       │
       │ search vector
       ▼
┌──────────────┐
│   Qdrant     │  similarity search (cosine)
│ Vector Store │  → filter by scope
│              │  → rank by relevance
└──────┬───────┘
       │
       │ memory IDs + scores
       ▼
┌──────────────┐
│  Memory      │  fetch full memory objects
│  Service     │  → return ranked results
└──────────────┘
```

### Memory Extraction Worker Flow

```
Memory Generation Worker Process
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────────────────────────┐
│         Worker Startup               │
│  1. Initialize services:             │
│     - ExtractionEngine (LLM)         │
│     - EmbeddingService (OpenAI)      │
│     - QdrantClientWrapper            │
│     - SessionsServiceClient          │
│     - MemoryServiceClient            │
│  2. Connect to RabbitMQ              │
│  3. Start consumer                   │
└─────────────┬────────────────────────┘
              │
              │ listen on EXTRACTION_REQUESTS queue
              ▼
┌─────────────────────────────────────┐
│      Message Received                │
│  {                                   │
│    "session_id": "sess_123",        │
│    "user_id": "user_456",           │
│    "scope": "user"                  │
│  }                                  │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│    Validation                        │
│  - Check session_id present          │
│  - Check user_id present             │
│  - Check scope valid (user/org/etc)  │
└─────────────┬───────────────────────┘
              │ valid ✓
              ▼
┌─────────────────────────────────────┐
│  Step 1: Fetch Events                │
│                                      │
│  sessions_client.list_events(        │
│    session_id=sess_123,              │
│    limit=1000                        │
│  )                                   │
│                                      │
│  Transform to conversation format:   │
│  [                                   │
│    {                                 │
│      "speaker": "user",              │
│      "content": "I love hiking"      │
│    },                                │
│    ...                               │
│  ]                                   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 2: Extract Memories            │
│                                      │
│  extraction_engine.extract_memories( │
│    conversation_events=events,       │
│    min_confidence=0.5                │
│  )                                   │
│                                      │
│  LLM returns:                        │
│  [                                   │
│    {                                 │
│      "fact": "User enjoys hiking",   │
│      "category": "preference",       │
│      "confidence": 0.9               │
│    },                                │
│    ...                               │
│  ]                                   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 3: Generate Embeddings         │
│                                      │
│  memory_texts = [                    │
│    "User enjoys hiking",             │
│    ...                               │
│  ]                                   │
│                                      │
│  embedding_service.generate_         │
│    embeddings(memory_texts)          │
│                                      │
│  Returns: [[0.1, 0.2, ...], ...]     │
│  (1536-dimensional vectors)          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 4: Save Memories               │
│                                      │
│  For each (memory, embedding):       │
│                                      │
│    memory_client.create_memory(      │
│      scope={user_id: "user_456"},    │
│      fact="User enjoys hiking",      │
│      source_type="extracted",        │
│      source_id="sess_123",           │
│      embedding=[0.1, 0.2, ...],      │
│      confidence=0.9,                 │
│      importance=0.7                  │
│    )                                 │
│                                      │
│  Memory Service:                     │
│    → Saves to PostgreSQL             │
│    → Stores embedding in Qdrant      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Return Success Result               │
│  {                                   │
│    "session_id": "sess_123",        │
│    "memories_extracted": 5,          │
│    "memories_saved": 5,              │
│    "embeddings_generated": 5,        │
│    "success": true                   │
│  }                                   │
└─────────────┬───────────────────────┘
              │
              │ acknowledge message
              ▼
       Ready for next message
```

### Memory Consolidation Worker Flow

```
Consolidation Worker Process
━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────────────────────────┐
│       Worker Startup                 │
│  1. Initialize services:             │
│     - ConsolidationEngine            │
│     - EmbeddingService               │
│     - MemoryServiceClient            │
│  2. Connect to RabbitMQ              │
│  3. Start consumer                   │
└─────────────┬────────────────────────┘
              │
              │ listen on CONSOLIDATION_REQUESTS
              ▼
┌─────────────────────────────────────┐
│      Message Received                │
│  {                                   │
│    "scope": {"type": "user"},       │
│    "user_id": "user_456",           │
│    "max_memories": 1000,            │
│    "detect_conflicts": true         │
│  }                                  │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 1: Fetch Memories              │
│                                      │
│  memory_client.list_memories(        │
│    scope_user_id="user_456",         │
│    limit=1000                        │
│  )                                   │
│                                      │
│  Returns 150 memories with           │
│  embeddings                          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 2: Convert to Memory Objects   │
│                                      │
│  Convert each to Memory:             │
│    Memory(                           │
│      id=UUID("..."),                │
│      fact="User enjoys hiking",      │
│      confidence=0.9,                 │
│      embedding=[0.1, 0.2, ...],      │
│      ...                             │
│    )                                 │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 3: Run Consolidation           │
│                                      │
│  consolidation_engine.               │
│    consolidate_memories(             │
│      memories=memory_objects,        │
│      detect_conflicts=true           │
│    )                                 │
│                                      │
│  Process:                            │
│  1. Compare all pairs (n×n/2)        │
│  2. Calculate similarity (cosine)    │
│  3. Find candidates (>0.85)          │
│  4. Detect conflicts (0.7-0.85)      │
│  5. Merge similar pairs              │
│                                      │
│  Result:                             │
│  - 12 merged memories                │
│  - 3 conflicts detected              │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 4: Generate New Embeddings     │
│                                      │
│  For each merged memory:             │
│                                      │
│  merged_facts = [                    │
│    "User loves hiking in mountains", │
│    ...                               │
│  ]                                   │
│                                      │
│  embedding_service.generate_         │
│    embeddings(merged_facts)          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Step 5: Save Consolidated           │
│                                      │
│  For each merged memory:             │
│                                      │
│    memory_client.create_memory(      │
│      scope={user_id: "user_456"},    │
│      fact="User loves hiking...",    │
│      source_type="consolidated",     │
│      embedding=[...],                │
│      confidence=1.0,                 │
│      importance=0.7                  │
│    )                                 │
│                                      │
│  TODO: Mark superseded memories      │
│        as soft-deleted               │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Return Success Result               │
│  {                                   │
│    "scope": {"type": "user"},       │
│    "memories_processed": 150,        │
│    "memories_merged": 24,            │
│    "conflicts_detected": 3,          │
│    "memories_updated": 12,           │
│    "success": true                   │
│  }                                   │
└─────────────────────────────────────┘
```

---

## Data Models

### MemoryGenerationRequest

Request to trigger memory extraction for a session:

```python
from pydantic import BaseModel
from uuid import UUID

class MemoryGenerationRequest(BaseModel):
    """Request to generate memories from a session."""

    session_id: UUID
    user_id: UUID
    scope: str = "user"  # "user", "org", or "global"

# Example
request = MemoryGenerationRequest(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    user_id="660e8400-e29b-41d4-a716-446655440001",
    scope="user"
)
```

### MemoryGenerationResult

Result of memory extraction processing:

```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class MemoryGenerationResult:
    """Result of memory generation processing."""

    session_id: UUID
    user_id: UUID
    memories_extracted: int = 0
    memories_saved: int = 0
    embeddings_generated: int = 0
    success: bool = False
    error: str | None = None

# Example
result = MemoryGenerationResult(
    session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    user_id=UUID("660e8400-e29b-41d4-a716-446655440001"),
    memories_extracted=5,
    memories_saved=5,
    embeddings_generated=5,
    success=True,
)
```

### ExtractionResult

Result from the Extraction Engine:

```python
class ExtractionResult:
    """Result of memory extraction operation."""

    def __init__(
        self,
        memories: list[dict[str, Any]],
        raw_response: str | None = None,
        error: str | None = None,
    ):
        self.memories = memories
        self.raw_response = raw_response
        self.error = error

    @property
    def success(self) -> bool:
        return self.error is None and len(self.memories) > 0

    @property
    def memory_count(self) -> int:
        return len(self.memories)

# Example
result = ExtractionResult(
    memories=[
        {
            "fact": "User enjoys hiking",
            "category": "preference",
            "confidence": 0.9,
            "topic": "outdoor activities",
            "importance": 0.7
        },
        {
            "fact": "User lives in Seattle",
            "category": "location",
            "confidence": 0.95,
            "topic": "residence",
            "importance": 0.8
        }
    ],
    raw_response="...",
)
```

### Memory (Extraction Format)

Memory as returned by ExtractionEngine:

```python
{
    "fact": str,           # The memory fact/statement
    "category": str,       # preference|fact|goal|habit|relationship|professional|location|temporal
    "confidence": float,   # 0.0-1.0, how certain about this fact
    "topic": str,          # Optional topic/category
    "importance": float,   # 0.0-1.0, how important this fact is
}

# Example
memory = {
    "fact": "User prefers dark roast coffee in the morning",
    "category": "preference",
    "confidence": 0.92,
    "topic": "beverages",
    "importance": 0.7
}
```

### Memory (Storage Format)

Memory as stored in database and retrieved from Memory Service:

```python
{
    "id": str,                    # UUID
    "scope": {                    # Scope definition
        "user_id": str,          # For user scope
        "org_id": str,           # For org scope (optional)
    },
    "fact": str,                  # The memory statement
    "source_type": str,           # "extracted" or "consolidated"
    "source_id": str,             # Session ID or parent memory ID
    "topic": str,                 # Optional category
    "confidence": float,          # 0.0-1.0
    "importance": float,          # 0.0-1.0
    "metadata": dict,             # Additional metadata
    "created_at": str,            # ISO 8601 timestamp
    "updated_at": str,            # ISO 8601 timestamp
}

# Example
memory = {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "scope": {
        "user_id": "660e8400-e29b-41d4-a716-446655440001"
    },
    "fact": "User prefers dark roast coffee in the morning",
    "source_type": "extracted",
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "topic": "beverages",
    "confidence": 0.92,
    "importance": 0.7,
    "metadata": {
        "category": "preference",
        "extraction_timestamp": "2025-01-15T10:30:00Z",
        "llm_model": "claude-3-5-sonnet-20240620"
    },
    "created_at": "2025-01-15T10:30:01Z",
    "updated_at": "2025-01-15T10:30:01Z"
}
```

### Memory (Consolidation Format)

Memory object used in consolidation:

```python
from dataclasses import dataclass
from uuid import UUID
from typing import Any

@dataclass
class Memory:
    """Memory representation for consolidation."""

    id: UUID
    fact: str
    confidence: float
    embedding: list[float]
    source_session_id: UUID | None = None
    metadata: dict[str, Any] | None = None

# Example
memory = Memory(
    id=UUID("770e8400-e29b-41d4-a716-446655440000"),
    fact="User enjoys hiking in mountains",
    confidence=0.9,
    embedding=[0.123, -0.456, 0.789, ...],  # 1536 dimensions
    source_session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    metadata={"category": "preference", "topic": "outdoor activities"}
)
```

### ConsolidationRequest

Request to trigger memory consolidation:

```python
from pydantic import BaseModel
from uuid import UUID

class ConsolidationRequest(BaseModel):
    """Request to consolidate memories."""

    scope: dict[str, Any]           # {"type": "user"} or {"type": "org", "org_id": "..."}
    user_id: UUID | None = None     # Required for user scope
    max_memories: int = 1000        # Maximum memories to fetch
    detect_conflicts: bool = True   # Whether to detect conflicts

# Example
request = ConsolidationRequest(
    scope={"type": "user"},
    user_id=UUID("660e8400-e29b-41d4-a716-446655440001"),
    max_memories=1000,
    detect_conflicts=True
)
```

### ConsolidationResult

Result of consolidation processing:

```python
from dataclasses import dataclass

@dataclass
class ConsolidationResult:
    """Result of consolidation processing."""

    scope: dict[str, Any]
    memories_processed: int = 0
    memories_merged: int = 0
    conflicts_detected: int = 0
    memories_updated: int = 0
    success: bool = False
    error: str | None = None

# Example
result = ConsolidationResult(
    scope={"type": "user"},
    memories_processed=150,
    memories_merged=24,  # 12 pairs merged
    conflicts_detected=3,
    memories_updated=12,  # 12 new consolidated memories saved
    success=True
)
```

### MergeCandidate

Pair of memories identified for potential merging:

```python
from dataclasses import dataclass

@dataclass
class MergeCandidate:
    """Candidate memory pair for merging."""

    memory1: Memory
    memory2: Memory
    similarity_score: float
    is_conflict: bool

# Example
candidate = MergeCandidate(
    memory1=Memory(...),
    memory2=Memory(...),
    similarity_score=0.92,
    is_conflict=False
)
```

### MergedMemory

Result of merging two memories:

```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class MergedMemory:
    """Result of merging memories."""

    fact: str
    confidence: float
    source_memory_ids: list[UUID]
    merge_reason: str

# Example
merged = MergedMemory(
    fact="User loves hiking in mountains",
    confidence=1.0,  # 0.9 + 0.1 boost
    source_memory_ids=[
        UUID("770e8400-e29b-41d4-a716-446655440000"),
        UUID("880e8400-e29b-41d4-a716-446655440001")
    ],
    merge_reason="Merged using highest_confidence strategy"
)
```

---

## Configuration Reference

### Extraction Settings

From `shared/extraction/config.py`:

```python
class ExtractionSettings(BaseSettings):
    """Configuration for memory extraction."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EXTRACTION_",
        case_sensitive=False,
    )

    # LLM Provider
    llm_provider: str = Field(
        default="anthropic",
        description="LLM provider (anthropic, openai)",
    )

    # Anthropic Settings
    anthropic_api_key: str = Field(...)
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20240620",
        description="Anthropic model ID",
    )
    anthropic_max_tokens: int = Field(
        default=4000,
        ge=1,
        le=8192,
        description="Maximum tokens in response",
    )
    anthropic_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (lower = more deterministic)",
    )
    anthropic_timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    anthropic_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts",
    )

    # Extraction Behavior
    extraction_min_events: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum events required for extraction",
    )
    extraction_max_facts: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum facts to extract per session",
    )
    use_few_shot: bool = Field(
        default=True,
        description="Include few-shot examples in prompts",
    )
    max_few_shot_examples: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum few-shot examples to include",
    )
```

**Environment Variables**:
```bash
# Required
EXTRACTION_ANTHROPIC_API_KEY=sk-ant-...

# Optional (with defaults)
EXTRACTION_LLM_PROVIDER=anthropic
EXTRACTION_ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
EXTRACTION_ANTHROPIC_MAX_TOKENS=4000
EXTRACTION_ANTHROPIC_TEMPERATURE=0.3
EXTRACTION_ANTHROPIC_TIMEOUT=60
EXTRACTION_ANTHROPIC_MAX_RETRIES=3
EXTRACTION_MIN_EVENTS=2
EXTRACTION_MAX_FACTS=20
EXTRACTION_USE_FEW_SHOT=true
EXTRACTION_MAX_FEW_SHOT_EXAMPLES=3
```

### Consolidation Settings

From `shared/consolidation/config.py`:

```python
class ConsolidationSettings(BaseSettings):
    """Configuration for memory consolidation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONSOLIDATION_",
        case_sensitive=False,
    )

    # Similarity Thresholds
    similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for merging (cosine similarity)",
    )
    conflict_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for conflict detection",
    )

    # Merge Strategy
    merge_strategy: str = Field(
        default="highest_confidence",
        description="Strategy for choosing which memory to keep (highest_confidence, most_recent, longest)",
    )
    merged_confidence_boost: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Confidence boost for merged memories",
    )

    # Processing Limits
    max_merge_candidates: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum merge candidates per consolidation run",
    )
```

**Environment Variables**:
```bash
# Optional (with defaults)
CONSOLIDATION_SIMILARITY_THRESHOLD=0.85
CONSOLIDATION_CONFLICT_THRESHOLD=0.7
CONSOLIDATION_MERGE_STRATEGY=highest_confidence
CONSOLIDATION_MERGED_CONFIDENCE_BOOST=0.1
CONSOLIDATION_MAX_MERGE_CANDIDATES=100
```

### Worker Settings

**Memory Generation Worker** (`workers/memory_generation/config.py`):
```python
class WorkerSettings(BaseSettings):
    """Memory generation worker configuration."""

    worker_name: str = Field(default="memory_generation_worker")
    worker_concurrency: int = Field(default=1, ge=1, le=10)
    worker_prefetch_count: int = Field(default=10, ge=1, le=100)
```

**Environment Variables**:
```bash
WORKER_NAME=memory_generation_worker
WORKER_CONCURRENCY=1
WORKER_PREFETCH_COUNT=10
```

**Consolidation Worker** (`workers/consolidation/config.py`):
```python
class ConsolidationWorkerSettings(BaseSettings):
    """Consolidation worker configuration."""

    worker_name: str = Field(default="consolidation_worker")
    worker_concurrency: int = Field(default=1, ge=1, le=10)
    worker_prefetch_count: int = Field(default=5, ge=1, le=50)
```

**Environment Variables**:
```bash
CONSOLIDATION_WORKER_NAME=consolidation_worker
CONSOLIDATION_WORKER_CONCURRENCY=1
CONSOLIDATION_WORKER_PREFETCH_COUNT=5
```

---

## Code Examples

### Example 1: Complete End-to-End Memory Creation

```python
import asyncio
import httpx
from uuid import UUID

async def create_session_and_extract_memories():
    """Complete example of creating a session and extracting memories."""

    base_url_sessions = "http://localhost:8001"
    base_url_memory = "http://localhost:8002"
    user_id = "660e8400-e29b-41d4-a716-446655440001"

    async with httpx.AsyncClient() as client:
        # 1. Create a session
        response = await client.post(
            f"{base_url_sessions}/api/v1/sessions",
            json={
                "user_id": user_id,
                "agent_id": "assistant_1",
                "metadata": {"source": "web_chat"}
            }
        )
        session = response.json()
        session_id = session["id"]
        print(f"Created session: {session_id}")

        # 2. Add conversation events
        conversation = [
            ("user", "I really enjoy mountain biking on weekends"),
            ("agent", "That sounds exciting! How long have you been mountain biking?"),
            ("user", "For about 3 years. I started in Colorado."),
            ("agent", "What's your favorite trail?"),
            ("user", "The Monarch Crest Trail. I try to ride it monthly when possible."),
        ]

        for speaker, content in conversation:
            event_type = "user_message" if speaker == "user" else "agent_message"
            await client.post(
                f"{base_url_sessions}/api/v1/sessions/{session_id}/events",
                json={
                    "event_type": event_type,
                    "data": {"content": content}
                }
            )

        print(f"Added {len(conversation)} events to session")

        # 3. Trigger memory extraction (via RabbitMQ or direct API call)
        # In production, this would publish to RabbitMQ EXTRACTION_REQUESTS queue
        # For this example, we'll simulate the extraction process

        # Fetch events
        events_response = await client.get(
            f"{base_url_sessions}/api/v1/sessions/{session_id}/events"
        )
        events = events_response.json()["events"]
        print(f"Retrieved {len(events)} events")

        # In a real scenario, MemoryGenerationWorker would:
        # - Extract memories using ExtractionEngine (LLM)
        # - Generate embeddings using EmbeddingService
        # - Save to Memory Service

        # 4. Check extracted memories (after worker processes)
        await asyncio.sleep(5)  # Wait for async processing

        memories_response = await client.get(
            f"{base_url_memory}/api/v1/memories",
            params={"scope_user_id": user_id, "limit": 20}
        )
        memories = memories_response.json()["memories"]

        print(f"\nExtracted {len(memories)} memories:")
        for mem in memories:
            print(f"  - {mem['fact']} (confidence: {mem['confidence']:.2f})")

# Run
asyncio.run(create_session_and_extract_memories())
```

**Expected Output**:
```
Created session: 550e8400-e29b-41d4-a716-446655440000
Added 5 events to session
Retrieved 5 events

Extracted 5 memories:
  - User enjoys mountain biking on weekends (confidence: 0.95)
  - User has been mountain biking for 3 years (confidence: 0.95)
  - User started mountain biking in Colorado (confidence: 0.95)
  - User's favorite trail is Monarch Crest Trail (confidence: 0.95)
  - User rides Monarch Crest Trail monthly when possible (confidence: 0.90)
```

### Example 2: Manual Memory Extraction

```python
from shared.extraction import ExtractionEngine, ExtractionSettings
from shared.embedding import EmbeddingService

def extract_memories_manually():
    """Manually extract memories from conversation without worker."""

    # Initialize services
    extraction_settings = ExtractionSettings()
    extraction_engine = ExtractionEngine(settings=extraction_settings)
    embedding_service = EmbeddingService()

    # Conversation events
    conversation_events = [
        {
            "speaker": "user",
            "content": "I work as a data scientist at Microsoft"
        },
        {
            "speaker": "agent",
            "content": "That's interesting! What kind of projects do you work on?"
        },
        {
            "speaker": "user",
            "content": "Mainly machine learning models for product recommendations"
        },
        {
            "speaker": "agent",
            "content": "How long have you been in this role?"
        },
        {
            "speaker": "user",
            "content": "Two years now. I moved from Google last year."
        },
    ]

    # Extract memories
    print("Extracting memories...")
    result = extraction_engine.extract_memories(
        conversation_events=conversation_events,
        min_confidence=0.5
    )

    if result.success:
        print(f"\nExtracted {result.memory_count} memories:")
        for mem in result.memories:
            print(f"\nFact: {mem['fact']}")
            print(f"  Category: {mem['category']}")
            print(f"  Confidence: {mem['confidence']:.2f}")
            print(f"  Topic: {mem.get('topic', 'N/A')}")

        # Generate embeddings
        print("\nGenerating embeddings...")
        memory_texts = [m["fact"] for m in result.memories]
        embedding_result = embedding_service.generate_embeddings(memory_texts)

        if embedding_result.success:
            print(f"Generated {embedding_result.count} embeddings")
            print(f"Vector dimensions: {len(embedding_result.embeddings[0])}")
    else:
        print(f"Extraction failed: {result.error}")

    # Cleanup
    extraction_engine.close()
    embedding_service.close()

# Run
extract_memories_manually()
```

**Expected Output**:
```
Extracting memories...

Extracted 4 memories:

Fact: User works as a data scientist at Microsoft
  Category: professional
  Confidence: 0.95
  Topic: employment

Fact: User works on machine learning models for product recommendations
  Category: professional
  Confidence: 0.90
  Topic: job responsibilities

Fact: User has been in current role for two years
  Category: professional
  Confidence: 0.95
  Topic: employment duration

Fact: User previously worked at Google
  Category: professional
  Confidence: 0.95
  Topic: work history

Generating embeddings...
Generated 4 embeddings
Vector dimensions: 1536
```

### Example 3: Manual Memory Consolidation

```python
from shared.consolidation import ConsolidationEngine, ConsolidationSettings
from shared.consolidation.engine import Memory
from shared.embedding import EmbeddingService
from uuid import UUID, uuid4

def consolidate_memories_manually():
    """Manually consolidate a set of memories."""

    # Initialize services
    consolidation_settings = ConsolidationSettings(
        similarity_threshold=0.85,
        merge_strategy="highest_confidence",
    )
    consolidation_engine = ConsolidationEngine(settings=consolidation_settings)
    embedding_service = EmbeddingService()

    # Create sample memories with embeddings
    facts = [
        "User enjoys hiking",
        "User loves hiking in mountains",
        "User likes mountain hiking",
        "User dislikes running",
        "User avoids jogging",
    ]

    # Generate embeddings
    embedding_result = embedding_service.generate_embeddings(facts)
    embeddings = embedding_result.embeddings

    # Create Memory objects
    memories = [
        Memory(
            id=uuid4(),
            fact=fact,
            confidence=0.9,
            embedding=embedding,
        )
        for fact, embedding in zip(facts, embeddings, strict=False)
    ]

    print(f"Consolidating {len(memories)} memories...")
    print("\nOriginal memories:")
    for i, mem in enumerate(memories):
        print(f"  {i+1}. {mem.fact}")

    # Run consolidation
    result = consolidation_engine.consolidate_memories(
        memories=memories,
        detect_conflicts=True
    )

    if result.success:
        print(f"\n✓ Consolidation complete!")
        print(f"  Memories processed: {result.memories_processed}")
        print(f"  Memories merged: {result.memories_merged}")
        print(f"  Merge pairs: {result.merge_count}")
        print(f"  Conflicts detected: {result.conflict_count}")

        if result.merged_memories:
            print(f"\nMerged memories:")
            for merged in result.merged_memories:
                print(f"\n  Fact: {merged.fact}")
                print(f"  Confidence: {merged.confidence:.2f}")
                print(f"  Source IDs: {[str(id)[:8] for id in merged.source_memory_ids]}")
                print(f"  Reason: {merged.merge_reason}")

        if result.conflicts_detected:
            print(f"\nConflicts detected:")
            for conflict in result.conflicts_detected:
                print(f"\n  Memory 1: {conflict.memory1.fact}")
                print(f"  Memory 2: {conflict.memory2.fact}")
                print(f"  Similarity: {conflict.similarity_score:.2f}")
    else:
        print(f"Consolidation failed: {result.error}")

    # Cleanup
    consolidation_engine.close()
    embedding_service.close()

# Run
consolidate_memories_manually()
```

**Expected Output**:
```
Consolidating 5 memories...

Original memories:
  1. User enjoys hiking
  2. User loves hiking in mountains
  3. User likes mountain hiking
  4. User dislikes running
  5. User avoids jogging

✓ Consolidation complete!
  Memories processed: 5
  Memories merged: 4
  Merge pairs: 2
  Conflicts detected: 0

Merged memories:

  Fact: User loves hiking in mountains
  Confidence: 1.00
  Source IDs: ['abc12345', 'def67890']
  Reason: Merged using highest_confidence strategy

  Fact: User dislikes running
  Confidence: 1.00
  Source IDs: ['ghi12345', 'jkl67890']
  Reason: Merged using highest_confidence strategy
```

### Example 4: Semantic Memory Search

```python
import asyncio
import httpx
from shared.embedding import EmbeddingService

async def search_memories_semantically():
    """Search for memories using semantic similarity."""

    base_url = "http://localhost:8002"
    user_id = "660e8400-e29b-41d4-a716-446655440001"

    # Initialize embedding service for query
    embedding_service = EmbeddingService()

    # Search query
    query = "What outdoor activities does the user like?"

    print(f"Query: {query}\n")

    # Generate query embedding
    query_embedding_result = embedding_service.generate_embedding(query)
    query_vector = query_embedding_result.embedding

    async with httpx.AsyncClient() as client:
        # Semantic search via Memory Service
        response = await client.post(
            f"{base_url}/api/v1/memories/search",
            json={
                "query_vector": query_vector,
                "scope": {"user_id": user_id},
                "limit": 5,
                "min_score": 0.7
            }
        )

        results = response.json()["results"]

        print(f"Found {len(results)} relevant memories:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['fact']}")
            print(f"   Similarity: {result['score']:.3f}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Topic: {result.get('topic', 'N/A')}")
            print()

    embedding_service.close()

# Run
asyncio.run(search_memories_semantically())
```

**Expected Output**:
```
Query: What outdoor activities does the user like?

Found 5 relevant memories:

1. User enjoys mountain biking on weekends
   Similarity: 0.892
   Confidence: 0.95
   Topic: outdoor activities

2. User loves hiking in mountains
   Similarity: 0.874
   Confidence: 1.00
   Topic: hiking

3. User's favorite trail is Monarch Crest Trail
   Similarity: 0.831
   Confidence: 0.95
   Topic: hiking

4. User has been mountain biking for 3 years
   Similarity: 0.798
   Confidence: 0.95
   Topic: outdoor activities

5. User started mountain biking in Colorado
   Similarity: 0.765
   Confidence: 0.95
   Topic: outdoor activities
```

### Example 5: Trigger Extraction via RabbitMQ

```python
import asyncio
from shared.messaging import MessagePublisher, RabbitMQClient
from shared.messaging.queues import Queues
from shared.messaging.config import MessagingSettings

async def trigger_memory_extraction():
    """Trigger memory extraction by publishing to RabbitMQ."""

    # Initialize RabbitMQ
    messaging_settings = MessagingSettings()
    rabbitmq_client = RabbitMQClient(url=messaging_settings.rabbitmq_url)
    publisher = MessagePublisher(client=rabbitmq_client)

    try:
        # Connect
        await rabbitmq_client.connect()
        print("Connected to RabbitMQ")

        # Extraction request message
        request = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "660e8400-e29b-41d4-a716-446655440001",
            "scope": "user"
        }

        # Publish to extraction requests queue
        await publisher.publish(
            queue_config=Queues.EXTRACTION_REQUESTS,
            message=request,
            persistent=True,
            priority=5
        )

        print(f"✓ Published extraction request for session {request['session_id']}")
        print("Memory Generation Worker will process this request asynchronously")

    finally:
        await rabbitmq_client.disconnect()

# Run
asyncio.run(trigger_memory_extraction())
```

**Expected Output**:
```
Connected to RabbitMQ
✓ Published extraction request for session 550e8400-e29b-41d4-a716-446655440000
Memory Generation Worker will process this request asynchronously
```

### Example 6: Trigger Consolidation via RabbitMQ

```python
import asyncio
from shared.messaging import MessagePublisher, RabbitMQClient
from shared.messaging.queues import Queues
from shared.messaging.config import MessagingSettings

async def trigger_memory_consolidation():
    """Trigger memory consolidation by publishing to RabbitMQ."""

    # Initialize RabbitMQ
    messaging_settings = MessagingSettings()
    rabbitmq_client = RabbitMQClient(url=messaging_settings.rabbitmq_url)
    publisher = MessagePublisher(client=rabbitmq_client)

    try:
        # Connect
        await rabbitmq_client.connect()
        print("Connected to RabbitMQ")

        # Consolidation request message
        request = {
            "scope": {"type": "user"},
            "user_id": "660e8400-e29b-41d4-a716-446655440001",
            "max_memories": 1000,
            "detect_conflicts": True
        }

        # Publish to consolidation requests queue
        await publisher.publish(
            queue_config=Queues.CONSOLIDATION_REQUESTS,
            message=request,
            persistent=True,
            priority=3
        )

        print(f"✓ Published consolidation request for user {request['user_id']}")
        print("Consolidation Worker will process this request asynchronously")

    finally:
        await rabbitmq_client.disconnect()

# Run
asyncio.run(trigger_memory_consolidation())
```

**Expected Output**:
```
Connected to RabbitMQ
✓ Published consolidation request for user 660e8400-e29b-41d4-a716-446655440001
Consolidation Worker will process this request asynchronously
```

---

## Memory Quality

### Confidence Scores

Confidence represents how certain we are about a memory fact:

**Confidence Levels**:
- **0.9 - 1.0**: Very high confidence - explicitly stated by user
  - Example: "I am a software engineer" → confidence: 0.95
- **0.7 - 0.9**: High confidence - clearly implied
  - Example: "I code in Python every day" → confidence: 0.85
- **0.5 - 0.7**: Medium confidence - inferred from context
  - Example: "That bug was tricky" → "User encounters software bugs" → confidence: 0.65
- **< 0.5**: Low confidence - speculative (usually filtered out)
  - Example: "I might try that" → confidence: 0.4 (filtered)

**Confidence in Extraction**:
```python
# LLM assigns confidence based on:
# - Explicitness of statement
# - Consistency with other statements
# - Clarity of language

extraction_result = extraction_engine.extract_memories(
    conversation_events=events,
    min_confidence=0.5  # Filter out low-confidence memories
)
```

**Confidence Boost in Consolidation**:
```python
# Merged memories receive confidence boost
# because they're supported by multiple observations
original_confidence = 0.85
boost = 0.1
merged_confidence = min(1.0, original_confidence + boost)  # = 0.95
```

### Importance Scores

Importance represents how significant a memory is for future interactions:

**Importance Levels**:
- **0.8 - 1.0**: Critical - Core identity/preferences
  - Example: "User is allergic to peanuts" → importance: 0.95
- **0.6 - 0.8**: High - Significant preferences/facts
  - Example: "User's favorite color is blue" → importance: 0.7
- **0.4 - 0.6**: Medium - Useful context
  - Example: "User watched a movie last weekend" → importance: 0.5
- **0.2 - 0.4**: Low - Minor details
  - Example: "User's coffee was cold this morning" → importance: 0.3
- **< 0.2**: Very low - Ephemeral (rarely stored)
  - Example: "User said 'hmm'" → importance: 0.1

**Importance in Retrieval**:
```python
# Combined relevance score for ranking
relevance_score = (
    0.6 * similarity_score +      # Semantic match
    0.2 * confidence +             # Certainty
    0.1 * importance +             # Significance
    0.1 * recency_score           # Freshness
)
```

### Category Classification

The 8 memory categories help organize and retrieve memories:

1. **preference** - Likes, dislikes, choices
   - Used for: Personalization, recommendations
   - Example: "User prefers dark mode"

2. **fact** - Objective information
   - Used for: Identity, background, context
   - Example: "User lives in Seattle"

3. **goal** - Aspirations, objectives
   - Used for: Motivation, planning
   - Example: "User wants to learn Spanish"

4. **habit** - Recurring behaviors
   - Used for: Predictions, scheduling
   - Example: "User exercises at 6 AM"

5. **relationship** - People connections
   - Used for: Social context
   - Example: "User's sister is named Sarah"

6. **professional** - Work-related
   - Used for: Career context, networking
   - Example: "User works as a designer"

7. **location** - Geographic information
   - Used for: Place-based recommendations
   - Example: "User frequently visits Tokyo"

8. **temporal** - Time-based information
   - Used for: Scheduling, reminders
   - Example: "User's birthday is June 15"

---

## Performance Considerations

### Batch Processing

**Extraction**:
- Process multiple sessions in parallel
- Worker concurrency: 1-10 workers
- Each worker processes one session at a time

**Embedding Generation**:
- Batch size: 100 texts per request (default)
- OpenAI batching: ~1000 texts/second
- Cost: $0.02 per 1M tokens

**Consolidation**:
- Batch memories by scope (user/org)
- Process 100-1000 memories at once
- Complexity: O(n²) for similarity comparison

### Async Operations

All I/O operations are async for better throughput:

```python
# Sessions are processed asynchronously
async def process_request(request):
    # Fetch events (async HTTP)
    events = await sessions_client.list_events(session_id)

    # Extract memories (sync LLM call in executor)
    extraction_result = await asyncio.to_thread(
        extraction_engine.extract_memories,
        events
    )

    # Generate embeddings (async HTTP to OpenAI)
    embedding_result = await embedding_service.generate_embeddings_async(texts)

    # Save memories (async HTTP)
    await memory_client.create_memory(...)
```

### Worker Concurrency

**Memory Generation Worker**:
```bash
# Environment variable
WORKER_CONCURRENCY=5  # Process 5 sessions simultaneously

# Prefetch count (messages fetched but not yet processed)
WORKER_PREFETCH_COUNT=10
```

**Consolidation Worker**:
```bash
# Lower concurrency for resource-intensive consolidation
CONSOLIDATION_WORKER_CONCURRENCY=2
CONSOLIDATION_WORKER_PREFETCH_COUNT=5
```

### Database Optimization

**Indexing**:
```sql
-- Index on scope for fast filtering
CREATE INDEX idx_memories_scope_user_id ON memories(scope_user_id);

-- Index on confidence for high-quality memories
CREATE INDEX idx_memories_confidence ON memories(confidence);

-- Index on created_at for recency sorting
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
```

**Query Optimization**:
```python
# Limit results to avoid large transfers
memories = await memory_client.list_memories(
    scope_user_id=user_id,
    limit=100  # Only fetch what's needed
)

# Use pagination for large result sets
memories = await memory_client.list_memories(
    scope_user_id=user_id,
    limit=50,
    offset=100  # Page 3 (50 per page)
)
```

### Vector Search Optimization

**HNSW Parameters** (Qdrant):
```python
# Trade-off between speed and accuracy
hnsw_config = {
    "m": 16,                    # Edges per node (higher = more accurate, slower)
    "ef_construct": 100,        # Construction quality
    "full_scan_threshold": 10000  # Exact search for small datasets
}
```

**Search Parameters**:
```python
# Limit results for faster search
results = vector_store.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,  # Only top 10 results
    score_threshold=0.7  # Early termination for low scores
)
```

### Caching

**Session Events**:
```python
# Cache fetched events to avoid repeated API calls
@lru_cache(maxsize=100)
async def get_session_events(session_id: str):
    return await sessions_client.list_events(session_id)
```

**Embeddings**:
```python
# Cache embeddings for common queries
@lru_cache(maxsize=1000)
def get_embedding(text: str):
    return embedding_service.generate_embedding(text)
```

---

## Monitoring & Observability

### Logging Best Practices

**Structured Logging**:
```python
import logging

logger = logging.getLogger(__name__)

# Log extraction start
logger.info(
    "Processing memory generation request",
    extra={
        "session_id": str(request.session_id),
        "user_id": str(request.user_id),
        "event_count": len(conversation_events)
    }
)

# Log extraction result
logger.info(
    "Memory extraction complete",
    extra={
        "session_id": str(request.session_id),
        "memories_extracted": result.memory_count,
        "duration_seconds": duration
    }
)

# Log errors with context
logger.error(
    "Extraction failed",
    extra={
        "session_id": str(request.session_id),
        "error": str(e),
        "event_count": len(conversation_events)
    },
    exc_info=True
)
```

### Metrics to Track

**Extraction Metrics**:
- `extraction_requests_total` - Total extraction requests
- `extraction_requests_success` - Successful extractions
- `extraction_requests_failed` - Failed extractions
- `extraction_duration_seconds` - Time to extract memories
- `memories_extracted_total` - Total memories extracted
- `memories_per_session` - Average memories per session

**Consolidation Metrics**:
- `consolidation_requests_total` - Total consolidation requests
- `consolidation_duration_seconds` - Time to consolidate
- `memories_merged_total` - Total memories merged
- `conflicts_detected_total` - Total conflicts detected
- `merge_candidates_found` - Merge candidates identified

**Storage Metrics**:
- `memories_stored_total` - Total memories saved
- `embeddings_generated_total` - Total embeddings created
- `memory_storage_duration_seconds` - Time to save memory

**Retrieval Metrics**:
- `memory_searches_total` - Total memory searches
- `search_duration_seconds` - Time to search
- `search_results_count` - Number of results returned

### Debugging Extraction Issues

**Check LLM Response**:
```python
extraction_result = extraction_engine.extract_memories(events)

# Inspect raw LLM response
print("Raw LLM Response:")
print(extraction_result.raw_response)

# Check for errors
if extraction_result.error:
    print(f"Error: {extraction_result.error}")
```

**Validate Memory Structure**:
```python
for memory in extraction_result.memories:
    is_valid = extraction_engine.validate_memory(memory)
    if not is_valid:
        print(f"Invalid memory: {memory}")
```

**Check Confidence Filtering**:
```python
# See all memories before filtering
all_memories = extraction_result.memories  # Before confidence filter

# See filtered memories
filtered_memories = [
    m for m in all_memories
    if m.get("confidence", 0.0) >= 0.5
]

print(f"Total: {len(all_memories)}, After filter: {len(filtered_memories)}")
```

### Debugging Consolidation

**Check Similarity Scores**:
```python
consolidation_engine = ConsolidationEngine()

# Calculate similarity between two memories
memory1 = Memory(...)
memory2 = Memory(...)

similarity = consolidation_engine._calculate_similarity(memory1, memory2)
print(f"Similarity: {similarity:.3f}")

# Compare to threshold
threshold = consolidation_engine.settings.similarity_threshold
print(f"Threshold: {threshold}")
print(f"Will merge: {similarity >= threshold}")
```

**Inspect Merge Candidates**:
```python
merge_candidates = consolidation_engine._find_merge_candidates(memories)

print(f"Found {len(merge_candidates)} merge candidates:")
for candidate in merge_candidates:
    print(f"\nMemory 1: {candidate.memory1.fact}")
    print(f"Memory 2: {candidate.memory2.fact}")
    print(f"Similarity: {candidate.similarity_score:.3f}")
    print(f"Is Conflict: {candidate.is_conflict}")
```

---

## Production Best Practices

### When to Trigger Extraction

**Recommended Triggers**:

1. **End of Session** - When conversation ends
   ```python
   # On session close
   await session_service.close_session(session_id)
   # Trigger extraction
   await trigger_extraction(session_id, user_id)
   ```

2. **After N Events** - Every 20-50 events
   ```python
   # In event creation endpoint
   event_count = await get_event_count(session_id)
   if event_count % 50 == 0:
       await trigger_extraction(session_id, user_id)
   ```

3. **Scheduled** - Daily batch extraction
   ```python
   # Cron job: Run at 2 AM daily
   @cron.schedule("0 2 * * *")
   async def daily_extraction():
       active_sessions = await get_active_sessions()
       for session in active_sessions:
           await trigger_extraction(session.id, session.user_id)
   ```

4. **On-Demand** - User requests memory generation
   ```python
   @router.post("/sessions/{session_id}/extract-memories")
   async def extract_memories(session_id: str):
       await trigger_extraction(session_id, get_current_user_id())
       return {"status": "extraction_started"}
   ```

**Avoid**:
- Extracting every event (too frequent, expensive)
- Extracting sessions with < 5 events (insufficient context)
- Extracting closed/deleted sessions

### When to Trigger Consolidation

**Recommended Triggers**:

1. **Scheduled Daily** - Run consolidation once daily
   ```python
   @cron.schedule("0 3 * * *")  # 3 AM daily
   async def daily_consolidation():
       active_users = await get_active_users()
       for user in active_users:
           await trigger_consolidation(user.id)
   ```

2. **After N Memories** - When user has > 100 memories
   ```python
   # After memory creation
   memory_count = await get_memory_count(user_id)
   if memory_count % 100 == 0:
       await trigger_consolidation(user_id)
   ```

3. **Manual Trigger** - Admin or user request
   ```python
   @router.post("/users/{user_id}/consolidate-memories")
   async def consolidate_memories(user_id: str):
       await trigger_consolidation(user_id)
       return {"status": "consolidation_started"}
   ```

**Avoid**:
- Running consolidation after every memory creation (too expensive)
- Consolidating users with < 20 memories (insufficient duplicates)
- Running multiple consolidations simultaneously for same user

### Error Handling Strategies

**Extraction Errors**:
```python
try:
    result = await processor.process_request(request)
    if not result.success:
        # Log error but don't fail hard
        logger.error(f"Extraction failed: {result.error}")
        # Retry with exponential backoff
        await retry_with_backoff(processor.process_request, request)
except Exception as e:
    # Log exception
    logger.exception("Unexpected error during extraction")
    # Send to dead letter queue for manual review
    await send_to_dlq(request, error=str(e))
```

**LLM API Errors**:
```python
# Retry configuration
ANTHROPIC_MAX_RETRIES = 3
ANTHROPIC_RETRY_DELAY = 2.0

# In ExtractionEngine
try:
    response = self.llm_client.extract_structured(...)
except AnthropicError as e:
    if "rate_limit" in str(e):
        # Wait and retry
        await asyncio.sleep(60)
        response = self.llm_client.extract_structured(...)
    else:
        # Log and fail
        logger.error(f"LLM error: {e}")
        raise
```

**Embedding Errors**:
```python
# Fallback to empty embeddings
embedding_result = self.embedding_service.generate_embeddings(texts)

if embedding_result.error:
    logger.warning(f"Embedding generation failed: {embedding_result.error}")
    # Save memories without embeddings (can generate later)
    embeddings = [[0.0] * 1536 for _ in texts]
else:
    embeddings = embedding_result.embeddings
```

### Data Quality Assurance

**Validation Before Storage**:
```python
def validate_memory_before_save(memory: dict) -> bool:
    """Validate memory meets quality standards."""

    # Required fields present
    if not all(k in memory for k in ["fact", "confidence"]):
        return False

    # Confidence in valid range
    if not (0.0 <= memory["confidence"] <= 1.0):
        return False

    # Fact is non-empty
    if not memory["fact"] or not memory["fact"].strip():
        return False

    # Fact is not too long (prevent abuse)
    if len(memory["fact"]) > 500:
        return False

    # Fact is not too short (prevent noise)
    if len(memory["fact"]) < 10:
        return False

    return True

# Use in processor
for memory in extraction_result.memories:
    if validate_memory_before_save(memory):
        await memory_client.create_memory(...)
    else:
        logger.warning(f"Invalid memory rejected: {memory}")
```

**Deduplication Check**:
```python
async def check_duplicate_before_save(
    user_id: str,
    fact: str,
    embedding: list[float]
) -> bool:
    """Check if similar memory already exists."""

    # Search for similar memories
    results = await vector_store.search(
        collection_name="memories",
        query_vector=embedding,
        limit=1,
        score_threshold=0.95,  # Very high similarity
        query_filter={"user_id": user_id}
    )

    if results and results[0]["score"] >= 0.95:
        logger.info(f"Duplicate memory found, skipping: {fact}")
        return True  # Is duplicate

    return False  # Not duplicate
```

**Conflict Detection Alert**:
```python
# After consolidation
if consolidation_result.conflicts_detected:
    # Alert admin or user
    conflicts = consolidation_result.conflicts_detected
    await send_conflict_alert(
        user_id=user_id,
        conflict_count=len(conflicts),
        conflicts=conflicts
    )
```

---

## Troubleshooting Guide

### Issue: No Memories Extracted

**Symptoms**:
- ExtractionResult returns 0 memories
- `memories_extracted` count is 0

**Possible Causes**:

1. **Insufficient Events**
   ```python
   # Check minimum events threshold
   if len(conversation_events) < settings.extraction_min_events:
       # Not enough events to extract from
       pass
   ```
   **Solution**: Ensure session has at least 2-5 events

2. **Low Confidence Filtering**
   ```python
   # All memories filtered out due to low confidence
   min_confidence = 0.5
   # Check if LLM assigned low confidence scores
   ```
   **Solution**: Lower `min_confidence` threshold or improve conversation quality

3. **LLM API Error**
   ```python
   # Check for errors in ExtractionResult
   if extraction_result.error:
       print(extraction_result.error)
   ```
   **Solution**: Check API keys, rate limits, network connectivity

4. **Empty/Invalid Event Content**
   ```python
   # Events have no content
   conversation_events = [
       {"speaker": "user", "content": ""},  # Empty!
       {"speaker": "agent", "content": ""}
   ]
   ```
   **Solution**: Ensure events have non-empty content

**Debugging Steps**:
```python
# 1. Check event count
print(f"Event count: {len(conversation_events)}")

# 2. Check event content
for event in conversation_events:
    print(f"{event['speaker']}: {event['content']}")

# 3. Check extraction result
print(f"Success: {extraction_result.success}")
print(f"Error: {extraction_result.error}")
print(f"Memory count: {extraction_result.memory_count}")

# 4. Check raw LLM response
print(f"Raw response: {extraction_result.raw_response}")
```

### Issue: Low Confidence Scores

**Symptoms**:
- Memories have confidence < 0.5
- Most memories filtered out

**Possible Causes**:

1. **Vague Conversation**
   - User speaks in generalities
   - No concrete facts stated
   **Solution**: Prompt users for specific information

2. **Ambiguous Language**
   - "Maybe", "I think", "probably"
   - Uncertain statements
   **Solution**: LLM correctly assigns lower confidence

3. **Conflicting Statements**
   - User contradicts themselves
   - LLM is uncertain which is correct
   **Solution**: Use consolidation to resolve conflicts

**Improving Confidence**:
```python
# Adjust extraction prompt to emphasize confidence
# (in shared/extraction/prompts.py)

EXTRACTION_SYSTEM_PROMPT = """
Only extract facts you are highly confident about.
Assign confidence based on:
- Explicitness: User directly states the fact (high confidence)
- Consistency: Fact is mentioned multiple times (boost confidence)
- Clarity: Unambiguous language (high confidence)
- Uncertainty markers: "maybe", "I think" (lower confidence)
"""
```

### Issue: Consolidation Not Merging

**Symptoms**:
- `memories_merged` count is 0
- Similar memories not consolidated

**Possible Causes**:

1. **Similarity Threshold Too High**
   ```python
   # Default: 0.85
   similarity_threshold = 0.85

   # Two similar memories:
   # "User enjoys hiking" - embedding A
   # "User likes hiking" - embedding B
   # Similarity: 0.82 (below threshold!)
   ```
   **Solution**: Lower threshold to 0.75-0.80

2. **Missing Embeddings**
   ```python
   # Memories don't have embeddings
   if not memory1.embedding or not memory2.embedding:
       similarity = 0.0  # Can't calculate!
   ```
   **Solution**: Ensure all memories have embeddings

3. **Insufficient Memories**
   ```python
   # Need at least 2 memories to consolidate
   if len(memories) < 2:
       return ConsolidationResult(success=True)
   ```
   **Solution**: Wait until more memories accumulate

4. **Memories Are Actually Different**
   ```python
   # "User enjoys hiking" vs "User dislikes running"
   # Similarity: 0.45 (correctly not merged)
   ```
   **Solution**: This is expected behavior

**Debugging Steps**:
```python
# 1. Check similarity threshold
print(f"Threshold: {consolidation_engine.settings.similarity_threshold}")

# 2. Calculate pairwise similarities
for i, mem1 in enumerate(memories):
    for mem2 in memories[i+1:]:
        sim = consolidation_engine._calculate_similarity(mem1, mem2)
        print(f"'{mem1.fact}' <-> '{mem2.fact}': {sim:.3f}")

# 3. Check merge candidates
candidates = consolidation_engine._find_merge_candidates(memories)
print(f"Merge candidates: {len(candidates)}")

# 4. Manually test with lower threshold
settings = ConsolidationSettings(similarity_threshold=0.75)
engine = ConsolidationEngine(settings=settings)
result = engine.consolidate_memories(memories)
```

### Issue: Performance Degradation

**Symptoms**:
- Slow extraction (> 30 seconds)
- Slow consolidation (> 60 seconds)
- High memory usage

**Possible Causes**:

1. **Too Many Events**
   ```python
   # Fetching 10,000+ events at once
   events = await sessions_client.list_events(session_id, limit=10000)
   ```
   **Solution**: Limit to 1000 events, process in batches

2. **Large Batch Consolidation**
   ```python
   # Consolidating 5000+ memories
   # Complexity: O(n²) = 25,000,000 comparisons!
   ```
   **Solution**: Limit to 1000 memories, consolidate incrementally

3. **Synchronous Operations**
   ```python
   # Blocking operations in async code
   for memory in memories:
       save_memory(memory)  # Blocks!
   ```
   **Solution**: Use async operations

4. **No Connection Pooling**
   ```python
   # Creating new HTTP client for each request
   for request in requests:
       client = httpx.AsyncClient()  # Expensive!
   ```
   **Solution**: Reuse client connections

**Optimization Steps**:
```python
# 1. Add timeouts
extraction_result = await asyncio.wait_for(
    extraction_engine.extract_memories(events),
    timeout=30.0
)

# 2. Batch operations
async def save_memories_batch(memories, batch_size=10):
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i+batch_size]
        await asyncio.gather(*[save_memory(m) for m in batch])

# 3. Add caching
@lru_cache(maxsize=1000)
def get_embedding(text: str):
    return embedding_service.generate_embedding(text)

# 4. Use connection pooling
client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100)
)
```

### Issue: RabbitMQ Messages Not Processing

**Symptoms**:
- Messages stuck in queue
- Worker not consuming
- No logs from worker

**Debugging Steps**:
```bash
# 1. Check RabbitMQ status
docker-compose ps rabbitmq

# 2. Check queue depth
curl -u guest:guest http://localhost:15672/api/queues/%2F/extraction.requests

# 3. Check worker logs
docker-compose logs memory-generation-worker

# 4. Check worker status
docker-compose ps memory-generation-worker
```

**Common Fixes**:
```bash
# Restart worker
docker-compose restart memory-generation-worker

# Clear stuck messages (destructive!)
docker-compose exec rabbitmq rabbitmqctl purge_queue extraction.requests

# Check network connectivity
docker-compose exec memory-generation-worker ping rabbitmq
```

---

**Related Documentation**:
- [MESSAGING.md](MESSAGING.md) - RabbitMQ messaging system details
- [EMBEDDINGS.md](EMBEDDINGS.md) - Text embeddings with OpenAI
- [VECTOR_SEARCH.md](VECTOR_SEARCH.md) - Qdrant vector search
- [API_USAGE.md](API_USAGE.md) - Memory Service API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview

---

**Last Updated**: December 2025

For questions or issues about the memory lifecycle, please open an issue on GitHub.
