# Processing Layer Guide

**Complete guide to ContextIQ's processing layer - the intelligence engines that transform raw data into structured knowledge**

## Table of Contents

- [Overview](#overview)
- [Processing Layer Architecture](#processing-layer-architecture)
- [Extraction Engine](#extraction-engine)
- [Consolidation Engine](#consolidation-engine)
- [Embedding Service](#embedding-service)
- [Revision Tracker](#revision-tracker)
- [Component Interactions](#component-interactions)
- [Data Flow Patterns](#data-flow-patterns)
- [Configuration Reference](#configuration-reference)
- [Performance Optimization](#performance-optimization)
- [Monitoring & Observability](#monitoring--observability)
- [Production Best Practices](#production-best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)

## Overview

### What is the Processing Layer?

The Processing Layer is the intelligence engine of ContextIQ, sitting between the Core Services Layer (Sessions, Memory) and the Storage Layer. It transforms raw conversation data into structured, searchable knowledge through four key components:

1. **Extraction Engine** - LLM-powered extraction of facts from conversations
2. **Consolidation Engine** - Deduplication and conflict resolution
3. **Embedding Service** - Vector generation for semantic search
4. **Revision Tracker** - Provenance and history management

### Why the Processing Layer Matters

**Without the Processing Layer**:
- Raw conversation data would be stored as-is with no structure
- No semantic understanding or searchability
- Duplicate and contradictory information would accumulate
- No ability to track memory evolution

**With the Processing Layer**:
- Intelligent extraction of meaningful facts
- Semantic similarity search capabilities
- Clean, deduplicated memory stores
- Complete provenance tracking

### Architecture Position

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Core Services Layer                          │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Sessions Service   │         │  Memory Service     │          │
│  │  - Events/State     │         │  - Generate/Search  │          │
│  └──────────┬──────────┘         └──────────┬──────────┘          │
└─────────────┼──────────────────────────────┼─────────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PROCESSING LAYER                               │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  Extraction Engine  │────────►│ Consolidation Engine│          │
│  │  - LLM Integration  │         │  - Merge Logic      │          │
│  │  - Fact Extraction  │         │  - Conflict Detect  │          │
│  └──────────┬──────────┘         └──────────┬──────────┘          │
│             │                               │                      │
│  ┌──────────▼──────────┐         ┌─────────▼──────────┐          │
│  │  Embedding Service  │         │   Revision Tracker  │          │
│  │  - Vector Gen       │         │  - History/Provenance│         │
│  └─────────────────────┘         └─────────────────────┘          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Storage Layer                                │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │  PostgreSQL         │         │   Qdrant Vector DB  │          │
│  │  - Memories/Events  │         │  - Embeddings       │          │
│  └─────────────────────┘         └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Processing Layer Architecture

### Component Overview

The Processing Layer consists of four specialized engines that work together:

```
Input: Raw Events
    │
    ▼
┌─────────────────────┐
│ Extraction Engine   │  Step 1: Extract structured facts
│ (LLM-powered)       │         from conversation events
└──────────┬──────────┘
           │ Extracted Facts
           ▼
┌─────────────────────┐
│ Embedding Service   │  Step 2: Generate vector embeddings
│ (OpenAI API)        │         for semantic search
└──────────┬──────────┘
           │ Facts + Embeddings
           ▼
┌─────────────────────┐
│Consolidation Engine │  Step 3: Merge with existing memories
│ (Similarity-based)  │         Detect duplicates/conflicts
└──────────┬──────────┘
           │ Consolidated Memories
           ▼
┌─────────────────────┐
│  Revision Tracker   │  Step 4: Create revision history
│  (Audit Trail)      │         Track changes
└──────────┬──────────┘
           │
           ▼
    Stored Memories
```

### Data Flow Through Processing Layer

**End-to-End Processing Pipeline**:

```
1. Session Events → Extraction Engine
   ↓
   Raw conversation:
   - User: "I enjoy hiking"
   - Agent: "That's great!"
   - User: "Especially in mountains"

2. Extraction Engine → Structured Facts
   ↓
   Extracted memories:
   - fact: "User enjoys hiking"
     category: "preference"
     confidence: 0.9
   - fact: "User especially enjoys mountain hiking"
     category: "preference"
     confidence: 0.85

3. Structured Facts → Embedding Service
   ↓
   Embeddings generated:
   - "User enjoys hiking" → [0.123, -0.456, 0.789, ...]
   - "User especially enjoys mountain hiking" → [0.134, -0.445, 0.801, ...]

4. Facts + Embeddings → Consolidation Engine
   ↓
   Analysis:
   - Check existing memories for duplicates
   - Calculate similarity scores
   - Decision: MERGE (similarity = 0.92)

5. Consolidated Result → Revision Tracker
   ↓
   Revision created:
   - Old: "User enjoys hiking"
   - New: "User especially enjoys mountain hiking"
   - Action: UPDATED

6. Final Storage
   ↓
   - PostgreSQL: Memory metadata + fact
   - Qdrant: Embedding vector
   - PostgreSQL: Revision record
```

---

## Extraction Engine

### Purpose

The Extraction Engine uses Large Language Models (LLMs) to analyze conversation events and extract structured, meaningful information as memory facts.

### Architecture

Located in `shared/extraction/engine.py`:

```python
class ExtractionEngine:
    """
    Core engine for extracting memories from conversation events.

    Uses LLM (Anthropic Claude) to analyze conversations and extract
    structured facts with categories, confidence scores, and topics.
    """

    def __init__(
        self,
        settings: ExtractionSettings | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.settings = settings or get_extraction_settings()
        self.llm_client = llm_client or LLMClient(settings=self.settings)
```

### Core Capabilities

#### 1. Fact Extraction

Analyzes conversations to identify memorable information:

```python
conversation_events = [
    {"speaker": "user", "content": "I work as a data scientist at Microsoft"},
    {"speaker": "agent", "content": "That's interesting! What projects?"},
    {"speaker": "user", "content": "Machine learning for product recommendations"},
]

result = extraction_engine.extract_memories(
    conversation_events=conversation_events,
    min_confidence=0.5
)

# Extracted facts:
# [
#   {
#     "fact": "User works as a data scientist at Microsoft",
#     "category": "professional",
#     "confidence": 0.95,
#     "topic": "employment"
#   },
#   {
#     "fact": "User works on machine learning for product recommendations",
#     "category": "professional",
#     "confidence": 0.90,
#     "topic": "job responsibilities"
#   }
# ]
```

#### 2. Category Classification

8 predefined categories for organizing memories:

1. **preference** - User likes, dislikes, choices
   - Example: "User prefers dark roast coffee"

2. **fact** - Objective information about user
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

#### 3. Confidence Scoring

LLM assigns confidence based on statement clarity:

- **0.9-1.0**: Explicitly stated facts
  - "I am a software engineer" → 0.95
- **0.7-0.9**: Clearly implied information
  - "I code in Python daily" → 0.85
- **0.5-0.7**: Inferred from context
  - "That bug was tricky" → 0.65
- **<0.5**: Speculative (filtered out)
  - "I might try that" → 0.4

#### 4. Topic Matching

Assigns topics for organization and retrieval:

```python
topics = [
    MemoryTopic(
        id="beverages",
        label="Beverages & Drinks",
        description="User preferences for coffee, tea, etc."
    ),
    MemoryTopic(
        id="outdoor_activities",
        label="Outdoor Activities",
        description="Hiking, camping, sports preferences"
    )
]

# LLM matches extracted facts to appropriate topics
fact = "User prefers dark roast coffee"
matched_topic = "beverages"
```

### LLM Integration

#### Provider: Anthropic Claude

Uses Anthropic's Claude for structured extraction:

```python
# Configuration
extraction_settings = ExtractionSettings(
    llm_provider="anthropic",
    anthropic_model="claude-3-5-sonnet-20240620",
    anthropic_max_tokens=4000,
    anthropic_temperature=0.3,  # Low temp for consistency
    anthropic_timeout=60,
    anthropic_max_retries=3,
)
```

#### Structured Extraction

Uses response schema for consistent output:

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
                            "preference", "fact", "goal", "habit",
                            "relationship", "professional",
                            "location", "temporal"
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

#### System Prompt

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

### Relationships to Other Components

#### → Consolidation Engine

Extraction Engine output flows to Consolidation Engine:

```python
# Extraction produces facts
extraction_result = extraction_engine.extract_memories(events)
extracted_facts = extraction_result.memories

# Consolidation merges with existing
consolidation_result = consolidation_engine.consolidate(
    new_memories=extracted_facts,
    existing_memories=existing_memories
)
```

#### → Embedding Service

Extracted facts are embedded for similarity search:

```python
# Extract facts
facts = ["User enjoys hiking", "User loves mountain hiking"]

# Generate embeddings
embeddings = embedding_service.generate_embeddings(facts)

# Store both fact and embedding
for fact, embedding in zip(facts, embeddings):
    memory_service.create_memory(
        fact=fact,
        embedding=embedding
    )
```

#### → Memory Service

Extraction Engine is invoked by Memory Generation Worker:

```python
# Memory Generation Worker orchestrates
class MemoryGenerationProcessor:
    async def process_request(self, request):
        # Step 1: Fetch events from Sessions Service
        events = await sessions_client.list_events(request.session_id)

        # Step 2: Extract memories with Extraction Engine
        result = extraction_engine.extract_memories(events)

        # Step 3: Generate embeddings
        embeddings = embedding_service.generate_embeddings(...)

        # Step 4: Save to Memory Service
        await memory_service.create_memory(...)
```

### Configuration

From `shared/extraction/config.py`:

```python
class ExtractionSettings(BaseSettings):
    # LLM Provider
    llm_provider: str = "anthropic"

    # Anthropic Settings
    anthropic_api_key: str  # Required
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    anthropic_max_tokens: int = 4000
    anthropic_temperature: float = 0.3
    anthropic_timeout: int = 60
    anthropic_max_retries: int = 3

    # Extraction Behavior
    extraction_min_events: int = 2  # Minimum events required
    extraction_max_facts: int = 20  # Maximum facts per session
    use_few_shot: bool = True       # Include examples in prompt
    max_few_shot_examples: int = 3
```

**Environment Variables**:
```bash
# Required
EXTRACTION_ANTHROPIC_API_KEY=sk-ant-...

# Optional (with defaults)
EXTRACTION_ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
EXTRACTION_ANTHROPIC_MAX_TOKENS=4000
EXTRACTION_ANTHROPIC_TEMPERATURE=0.3
EXTRACTION_MIN_EVENTS=2
EXTRACTION_MAX_FACTS=20
```

---

## Consolidation Engine

### Purpose

The Consolidation Engine prevents memory bloat by detecting duplicate memories, merging similar information, and identifying contradictions.

### Architecture

Located in `shared/consolidation/engine.py`:

```python
class ConsolidationEngine:
    """
    Engine for consolidating memories.

    Handles similarity detection, duplicate merging, and conflict resolution
    for memory management.
    """

    def __init__(self, settings: ConsolidationSettings | None = None):
        self.settings = settings or get_consolidation_settings()
```

### Core Capabilities

#### 1. Duplicate Detection

Uses cosine similarity on embeddings to find duplicates:

```python
def _calculate_similarity(self, memory1: Memory, memory2: Memory) -> float:
    """Calculate cosine similarity between two memories."""

    # Cosine similarity formula:
    # similarity = (A · B) / (||A|| × ||B||)

    dot_product = sum(a * b for a, b in zip(
        memory1.embedding,
        memory2.embedding
    ))

    magnitude1 = sum(a * a for a in memory1.embedding) ** 0.5
    magnitude2 = sum(b * b for b in memory2.embedding) ** 0.5

    return dot_product / (magnitude1 * magnitude2)
```

**Similarity Thresholds**:
- **≥0.85**: Strong merge candidates (default threshold)
- **0.70-0.85**: Potential conflicts (similar topic, different meaning)
- **<0.70**: Different memories (no action)

#### 2. Memory Merging

Three strategies for choosing which memory to keep:

**Strategy 1: Highest Confidence** (default)
```python
if memory1.confidence >= memory2.confidence:
    selected_fact = memory1.fact
    base_confidence = memory1.confidence
else:
    selected_fact = memory2.fact
    base_confidence = memory2.confidence
```

**Strategy 2: Most Recent**
```python
# Keep the most recently created memory
if memory1.created_at >= memory2.created_at:
    selected_fact = memory1.fact
else:
    selected_fact = memory2.fact
```

**Strategy 3: Longest**
```python
# Keep the memory with more detail
if len(memory1.fact) >= len(memory2.fact):
    selected_fact = memory1.fact
else:
    selected_fact = memory2.fact
```

#### 3. Confidence Boost

Merged memories receive confidence boost (supported by multiple observations):

```python
# Configuration
merged_confidence_boost = 0.1

# Example merge
original_confidence = 0.85
merged_confidence = min(1.0, 0.85 + 0.1)  # = 0.95
```

#### 4. Conflict Detection

Identifies contradictory memories:

```python
def _is_conflicting(
    self,
    memory1: Memory,
    memory2: Memory,
    similarity: float,
) -> bool:
    """Determine if two similar memories are conflicting."""

    # Memories conflict if:
    # 1. Similarity is above conflict threshold but below merge threshold
    # 2. Facts are substantively different

    if (self.settings.conflict_threshold <= similarity
        < self.settings.similarity_threshold):
        return memory1.fact.lower() != memory2.fact.lower()

    return False
```

**Example Conflict**:
```python
# Similar topic, contradictory information
memory1 = "User prefers morning coffee"
memory2 = "User avoids coffee in the morning"
similarity = 0.75  # Within conflict range

# Flagged as conflict for manual review
```

### Consolidation Pipeline

```python
def consolidate_memories(
    self,
    memories: list[Memory],
    detect_conflicts: bool = True,
) -> ConsolidationResult:
    """Consolidate a list of memories by detecting and merging duplicates."""

    # Step 1: Find merge candidates
    merge_candidates = self._find_merge_candidates(memories)

    # Step 2: Separate conflicts from mergeable pairs
    conflicts = []
    mergeable = []

    for candidate in merge_candidates:
        if detect_conflicts and candidate.is_conflict:
            conflicts.append(candidate)
        else:
            mergeable.append(candidate)

    # Step 3: Merge similar memories
    merged_memories = []
    for candidate in mergeable:
        merged = self._merge_memories(candidate.memory1, candidate.memory2)
        merged_memories.append(merged)

    # Step 4: Return result
    return ConsolidationResult(
        merged_memories=merged_memories,
        conflicts_detected=conflicts,
        memories_processed=len(memories),
        memories_merged=len(merged_memories) * 2,
        success=True,
    )
```

### Relationships to Other Components

#### ← Extraction Engine

Consolidation receives extracted facts:

```python
# Extraction produces new memories
new_memories = extraction_engine.extract_memories(events)

# Consolidation merges with existing
consolidation_result = consolidation_engine.consolidate(
    new_memories=new_memories,
    existing_memories=existing_memories
)
```

#### → Embedding Service

Consolidated memories need new embeddings:

```python
# After merging
merged_memory = MergedMemory(
    fact="User loves hiking in mountains",  # Merged from 2 memories
    confidence=1.0
)

# Generate new embedding
new_embedding = embedding_service.generate_embedding(
    merged_memory.fact
)

# Store with new embedding
memory_service.create_memory(
    fact=merged_memory.fact,
    embedding=new_embedding,
    source_type="consolidated"
)
```

#### → Revision Tracker

Creates revision history for merged/updated memories:

```python
# After consolidation
for merged_memory in consolidation_result.merged_memories:
    # Create revision record
    revision_tracker.create_revision(
        memory_id=merged_memory.id,
        action="MERGED",
        source_memory_ids=merged_memory.source_memory_ids,
        old_fact=old_memory.fact,
        new_fact=merged_memory.fact
    )
```

### Configuration

From `shared/consolidation/config.py`:

```python
class ConsolidationSettings(BaseSettings):
    # Similarity Thresholds
    similarity_threshold: float = 0.85  # Merge threshold
    conflict_threshold: float = 0.7     # Conflict detection threshold

    # Merge Strategy
    merge_strategy: str = "highest_confidence"  # or "most_recent", "longest"
    merged_confidence_boost: float = 0.1

    # Processing Limits
    max_merge_candidates: int = 100
```

**Environment Variables**:
```bash
CONSOLIDATION_SIMILARITY_THRESHOLD=0.85
CONSOLIDATION_CONFLICT_THRESHOLD=0.7
CONSOLIDATION_MERGE_STRATEGY=highest_confidence
CONSOLIDATION_MERGED_CONFIDENCE_BOOST=0.1
CONSOLIDATION_MAX_MERGE_CANDIDATES=100
```

---

## Embedding Service

### Purpose

The Embedding Service converts text into high-dimensional vector representations, enabling semantic similarity search and intelligent memory retrieval.

### Architecture

Located in `shared/embedding/service.py`:

```python
class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self, settings: EmbeddingSettings | None = None):
        self.settings = settings or get_embedding_settings()
        self._client: OpenAI | None = None
```

### Provider: OpenAI

**Model**: `text-embedding-3-small` (default)
- **Dimensions**: 1536 (configurable 256-3072)
- **Max Input**: 8191 tokens
- **Cost**: $0.02 per 1M tokens
- **Performance**: ~1000 texts/second (batch)

### Core Capabilities

#### 1. Single Embedding Generation

```python
embedding_service = EmbeddingService()

text = "User prefers dark roast coffee"
result = embedding_service.generate_embedding(text)

# result.embedding = [0.123, -0.456, 0.789, ..., 0.321]
# 1536-dimensional vector
```

#### 2. Batch Processing

```python
texts = [
    "User enjoys hiking",
    "User loves mountain biking",
    "User prefers dark roast coffee"
]

result = embedding_service.generate_embeddings(texts)

# result.embeddings = [
#   [0.123, -0.456, ...],  # hiking
#   [0.134, -0.445, ...],  # biking (similar to hiking)
#   [-0.523, 0.234, ...]   # coffee (different)
# ]
```

#### 3. Text Truncation

Automatically handles long text:

```python
# Settings
embedding_max_input_length = 8191  # tokens

# Long text is truncated
long_text = "..." * 10000  # Very long
result = embedding_service.generate_embedding(long_text)
# Automatically truncated to 8191 tokens
```

### Why Embeddings Matter

Embeddings enable semantic search - finding memories based on meaning rather than exact keywords:

**Example Query**: "What beverages does the user like?"

**Stored Memory**: "User prefers dark roast coffee"

**How it works**:
1. Generate embedding for query: `[0.234, -0.567, ...]`
2. Find similar embeddings in Qdrant vector store
3. Retrieve memory even though "beverages" ≠ "coffee"
4. Semantic similarity: 0.87 (high match!)

```
Query: "What beverages does the user like?"
  ↓ embedding
  [0.234, -0.567, 0.891, ...]
  ↓ cosine similarity
Memory: "User prefers dark roast coffee"
  [0.245, -0.571, 0.885, ...]
  ↓ similarity score
  0.87 → High match! Return this memory
```

### Relationships to Other Components

#### ← Extraction Engine

Embeddings are generated for extracted facts:

```python
# Extraction produces facts
facts = extraction_engine.extract_memories(events)

# Generate embeddings for each fact
fact_texts = [f["fact"] for f in facts]
embeddings = embedding_service.generate_embeddings(fact_texts)

# Combine for storage
for fact, embedding in zip(facts, embeddings):
    memory = {
        "fact": fact["fact"],
        "embedding": embedding,
        "confidence": fact["confidence"]
    }
```

#### ← Consolidation Engine

Merged memories need new embeddings:

```python
# After consolidation
merged_facts = [m.fact for m in consolidation_result.merged_memories]

# Generate embeddings for merged memories
embeddings = embedding_service.generate_embeddings(merged_facts)
```

#### → Vector Store (Qdrant)

Embeddings are stored in Qdrant for similarity search:

```python
# Store embedding in Qdrant
vector_store.upsert_points(
    collection_name="memories",
    points=[{
        "id": str(memory.id),
        "vector": embedding,  # 1536-dimensional vector
        "payload": {
            "memory_id": str(memory.id),
            "fact": memory.fact,
            "confidence": memory.confidence
        }
    }]
)
```

#### → Memory Service

Memory Service coordinates embedding generation:

```python
class MemoryService:
    async def create_memory(self, fact: str, ...):
        # Generate embedding
        embedding = embedding_service.generate_embedding(fact)

        # Store in database
        await db.insert_memory(fact=fact, ...)

        # Store in vector store
        await vector_store.upsert(embedding=embedding, ...)
```

### Configuration

From `shared/embedding/config.py`:

```python
class EmbeddingSettings(BaseSettings):
    # OpenAI Settings
    openai_api_key: str  # Required
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536  # 256-3072
    openai_timeout: int = 60
    openai_max_retries: int = 3

    # Batch Processing
    embedding_batch_size: int = 100  # Texts per batch
    embedding_max_input_length: int = 8191  # Max tokens
```

**Environment Variables**:
```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (with defaults)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
OPENAI_TIMEOUT=60
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_INPUT_LENGTH=8191
```

---

## Revision Tracker

### Purpose

The Revision Tracker maintains a complete audit trail of memory changes, enabling provenance tracking, historical queries, and rollback capabilities.

### Architecture

Located in `shared/revision/tracker.py` (planned):

```python
class RevisionTracker:
    """
    Tracks memory revisions and maintains provenance.

    Creates snapshots on every memory mutation to enable
    historical queries and rollback operations.
    """

    def create_revision(
        self,
        memory: Memory,
        action: str,
        source_session_id: UUID | None = None,
        extracted_memories: list[str] | None = None
    ) -> MemoryRevision:
        """Create revision snapshot for memory change."""
        pass
```

### Core Capabilities

#### 1. Revision Creation

Every memory change creates a revision:

```python
# Memory is updated
old_fact = "User enjoys hiking"
new_fact = "User especially enjoys mountain hiking"

# Create revision
revision = revision_tracker.create_revision(
    memory_id=memory.id,
    revision_number=memory.revision_count + 1,
    fact=new_fact,
    action="UPDATED",
    source_session_id=session_id,
    previous_fact=old_fact
)
```

#### 2. Revision Types

**CREATED**: Initial memory creation
```python
revision = MemoryRevision(
    memory_id=memory.id,
    revision_number=1,
    fact="User enjoys hiking",
    action="CREATED",
    source_session_id=session_id
)
```

**UPDATED**: Memory modified
```python
revision = MemoryRevision(
    memory_id=memory.id,
    revision_number=2,
    fact="User especially enjoys mountain hiking",
    action="UPDATED",
    source_session_id=session_id,
    previous_fact="User enjoys hiking"
)
```

**MERGED**: Memories consolidated
```python
revision = MemoryRevision(
    memory_id=memory.id,
    revision_number=3,
    fact="User loves hiking in mountains",
    action="MERGED",
    source_memory_ids=[mem1.id, mem2.id],
    merge_reason="Consolidated similar memories"
)
```

**DELETED**: Memory removed
```python
revision = MemoryRevision(
    memory_id=memory.id,
    revision_number=4,
    fact=None,
    action="DELETED",
    deletion_reason="Contradicted by new information"
)
```

#### 3. Historical Queries

Retrieve complete revision history:

```python
# Get all revisions for a memory
revisions = revision_tracker.get_history(memory_id)

# Timeline view
for revision in revisions:
    print(f"{revision.created_at}: {revision.action}")
    print(f"  Fact: {revision.fact}")
    if revision.action == "UPDATED":
        print(f"  Previous: {revision.previous_fact}")
```

#### 4. Rollback Operations

Restore memory to previous state:

```python
# Rollback to revision 2
restored_memory = revision_tracker.rollback(
    memory_id=memory.id,
    revision_number=2
)

# Creates new revision with action="ROLLBACK"
new_revision = MemoryRevision(
    memory_id=memory.id,
    revision_number=5,
    fact=restored_memory.fact,
    action="ROLLBACK",
    rollback_to_revision=2
)
```

### Relationships to Other Components

#### ← All Processing Components

Every component that modifies memories creates revisions:

**Extraction Engine**:
```python
# New memory created from extraction
revision_tracker.create_revision(
    memory=new_memory,
    action="CREATED",
    source_session_id=session_id
)
```

**Consolidation Engine**:
```python
# Memories merged during consolidation
revision_tracker.create_revision(
    memory=merged_memory,
    action="MERGED",
    source_memory_ids=[mem1.id, mem2.id]
)
```

**Memory Service**:
```python
# Direct memory update via API
revision_tracker.create_revision(
    memory=updated_memory,
    action="UPDATED",
    previous_fact=old_fact
)
```

#### → Storage Layer

Revisions are stored in PostgreSQL:

```sql
CREATE TABLE memory_revisions (
    id UUID PRIMARY KEY,
    memory_id UUID NOT NULL,
    revision_number INT NOT NULL,
    fact TEXT,
    action VARCHAR(50) NOT NULL,
    source_session_id UUID,
    source_memory_ids UUID[],
    previous_fact TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);
```

### Data Model

```python
@dataclass
class MemoryRevision:
    """Memory revision snapshot."""

    id: UUID
    memory_id: UUID
    revision_number: int
    fact: str | None
    action: str  # "CREATED", "UPDATED", "MERGED", "DELETED", "ROLLBACK"

    # Source tracking
    source_session_id: UUID | None = None
    source_memory_ids: list[UUID] | None = None

    # Change details
    previous_fact: str | None = None
    merge_reason: str | None = None
    deletion_reason: str | None = None
    rollback_to_revision: int | None = None

    # Metadata
    created_at: datetime
    created_by: str | None = None  # User/system
```

---

## Component Interactions

### Complete Processing Flow

End-to-end flow showing all component interactions:

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLETE PROCESSING FLOW                      │
└─────────────────────────────────────────────────────────────────┘

Step 1: Input from Core Services
┌─────────────────────┐
│  Sessions Service   │
│  GET /events        │
└──────────┬──────────┘
           │ Conversation Events
           ▼
┌─────────────────────────────────────────┐
│  EXTRACTION ENGINE                      │
│                                         │
│  1. Build prompt with conversation      │
│  2. Call LLM (Anthropic Claude)         │
│  3. Parse structured response           │
│  4. Validate facts                      │
│  5. Filter by confidence (≥0.5)         │
│                                         │
│  Output: Extracted Facts                │
│  - fact: "User enjoys hiking"           │
│  - category: "preference"               │
│  - confidence: 0.9                      │
└──────────┬──────────────────────────────┘
           │ Extracted Facts
           ▼
┌─────────────────────────────────────────┐
│  EMBEDDING SERVICE                      │
│                                         │
│  1. Batch facts for embedding           │
│  2. Call OpenAI API                     │
│  3. Generate 1536-dim vectors           │
│  4. Return embeddings list              │
│                                         │
│  Output: Facts + Embeddings             │
└──────────┬──────────────────────────────┘
           │ Facts + Embeddings
           ▼
┌─────────────────────────────────────────┐
│  CONSOLIDATION ENGINE                   │
│                                         │
│  1. Fetch existing memories (scope)     │
│  2. Calculate similarity (cosine)       │
│  3. Find merge candidates (≥0.85)       │
│  4. Detect conflicts (0.7-0.85)         │
│  5. Merge similar memories              │
│  6. Apply confidence boost (+0.1)       │
│                                         │
│  Output: Consolidated Memories          │
│  - New memories to create               │
│  - Existing memories to update          │
│  - Conflicts detected                   │
└──────────┬──────────────────────────────┘
           │ Consolidated Memories
           ▼
┌─────────────────────────────────────────┐
│  EMBEDDING SERVICE (2nd pass)           │
│                                         │
│  1. Generate embeddings for merged      │
│     memories (new facts)                │
│  2. Return new embeddings               │
└──────────┬──────────────────────────────┘
           │ Final Memories + Embeddings
           ▼
┌─────────────────────────────────────────┐
│  REVISION TRACKER                       │
│                                         │
│  For each memory change:                │
│  1. Create revision snapshot            │
│  2. Record action (CREATE/UPDATE/MERGE) │
│  3. Track source (session/memory IDs)   │
│  4. Store in database                   │
└──────────┬──────────────────────────────┘
           │ Memories + Revisions
           ▼
┌──────────────────────────────────────────┐
│  STORAGE LAYER                           │
│                                          │
│  PostgreSQL:                             │
│  - INSERT memories (fact, metadata)      │
│  - INSERT revisions (history)            │
│                                          │
│  Qdrant:                                 │
│  - UPSERT embeddings (vectors + payload) │
└──────────┬───────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Memory Service     │
│  Return Result      │
└─────────────────────┘
```

### Inter-Component Communication

#### Extraction → Embedding

```python
# Extraction produces structured facts
extraction_result = extraction_engine.extract_memories(
    conversation_events=events
)

if extraction_result.success:
    # Extract fact texts
    fact_texts = [mem["fact"] for mem in extraction_result.memories]

    # Generate embeddings
    embedding_result = embedding_service.generate_embeddings(fact_texts)

    # Combine
    for memory, embedding in zip(
        extraction_result.memories,
        embedding_result.embeddings
    ):
        memory["embedding"] = embedding
```

#### Embedding → Consolidation

```python
# Embeddings enable similarity comparison
memory1 = Memory(
    fact="User enjoys hiking",
    embedding=[0.123, -0.456, ...]
)

memory2 = Memory(
    fact="User loves mountain hiking",
    embedding=[0.134, -0.445, ...]
)

# Consolidation uses embeddings
similarity = consolidation_engine._calculate_similarity(
    memory1,
    memory2
)  # = 0.92 (very similar!)

if similarity >= 0.85:
    # Merge memories
    merged = consolidation_engine._merge_memories(memory1, memory2)
```

#### Consolidation → Revision

```python
# After consolidation
for merged_memory in consolidation_result.merged_memories:
    # Create revision for audit trail
    revision_tracker.create_revision(
        memory_id=new_memory_id,
        revision_number=1,
        fact=merged_memory.fact,
        action="MERGED",
        source_memory_ids=merged_memory.source_memory_ids,
        merge_reason=merged_memory.merge_reason
    )
```

---

## Data Flow Patterns

### Pattern 1: New Memory Creation

```
Input: Session Events
  │
  ▼
[Extraction Engine]
  │ Extracted Facts
  ▼
[Embedding Service]
  │ Facts + Embeddings
  ▼
[Consolidation Engine]
  │ No duplicates found
  ▼
[Revision Tracker]
  │ action="CREATED"
  ▼
Storage: New Memory
```

### Pattern 2: Duplicate Merging

```
Input: Session Events
  │
  ▼
[Extraction Engine]
  │ fact="User loves hiking"
  ▼
[Embedding Service]
  │ embedding=[0.134, ...]
  ▼
[Consolidation Engine]
  │ Compare with existing:
  │   - "User enjoys hiking" (similarity=0.92)
  │ Decision: MERGE
  ▼
[Embedding Service] (2nd pass)
  │ New embedding for merged fact
  ▼
[Revision Tracker]
  │ action="MERGED"
  │ source_memory_ids=[old_id]
  ▼
Storage: Updated Memory + Revision
```

### Pattern 3: Conflict Detection

```
Input: Session Events
  │
  ▼
[Extraction Engine]
  │ fact="User avoids coffee in morning"
  ▼
[Embedding Service]
  │ embedding=[0.245, -0.571, ...]
  ▼
[Consolidation Engine]
  │ Compare with existing:
  │   - "User prefers morning coffee"
  │   - similarity=0.75 (conflict range!)
  │ Decision: FLAG CONFLICT
  ▼
[Revision Tracker]
  │ action="CONFLICT_DETECTED"
  │ conflicting_memory_ids=[...]
  ▼
Storage: Conflict Record for Review
```

### Pattern 4: Memory Retrieval

```
Input: Search Query
  │ "What outdoor activities does user like?"
  ▼
[Embedding Service]
  │ Generate query embedding
  │ embedding=[0.234, -0.567, ...]
  ▼
[Vector Store] (Qdrant)
  │ Cosine similarity search
  │ Find top K similar memories
  ▼
[Consolidation Engine] (optional)
  │ Filter by confidence
  │ De-duplicate results
  ▼
[Revision Tracker] (optional)
  │ Check for recent updates
  ▼
Output: Ranked Memories
  - "User enjoys mountain biking" (score=0.89)
  - "User loves hiking" (score=0.87)
  - "User goes camping monthly" (score=0.82)
```

---

## Configuration Reference

### Extraction Engine Configuration

```python
# Environment Variables
EXTRACTION_ANTHROPIC_API_KEY=sk-ant-...
EXTRACTION_ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
EXTRACTION_ANTHROPIC_MAX_TOKENS=4000
EXTRACTION_ANTHROPIC_TEMPERATURE=0.3
EXTRACTION_MIN_EVENTS=2
EXTRACTION_MAX_FACTS=20
EXTRACTION_USE_FEW_SHOT=true
```

### Consolidation Engine Configuration

```python
# Environment Variables
CONSOLIDATION_SIMILARITY_THRESHOLD=0.85
CONSOLIDATION_CONFLICT_THRESHOLD=0.7
CONSOLIDATION_MERGE_STRATEGY=highest_confidence
CONSOLIDATION_MERGED_CONFIDENCE_BOOST=0.1
CONSOLIDATION_MAX_MERGE_CANDIDATES=100
```

### Embedding Service Configuration

```python
# Environment Variables
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
OPENAI_TIMEOUT=60
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_INPUT_LENGTH=8191
```

### Complete Configuration Example

```bash
# .env file for Processing Layer

# Extraction Engine
EXTRACTION_ANTHROPIC_API_KEY=sk-ant-api03-xxx
EXTRACTION_ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
EXTRACTION_ANTHROPIC_MAX_TOKENS=4000
EXTRACTION_ANTHROPIC_TEMPERATURE=0.3
EXTRACTION_MIN_EVENTS=2
EXTRACTION_MAX_FACTS=20
EXTRACTION_USE_FEW_SHOT=true

# Consolidation Engine
CONSOLIDATION_SIMILARITY_THRESHOLD=0.85
CONSOLIDATION_CONFLICT_THRESHOLD=0.7
CONSOLIDATION_MERGE_STRATEGY=highest_confidence
CONSOLIDATION_MERGED_CONFIDENCE_BOOST=0.1

# Embedding Service
OPENAI_API_KEY=sk-proj-xxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
OPENAI_TIMEOUT=60
EMBEDDING_BATCH_SIZE=100
```

---

## Performance Optimization

### Extraction Engine Optimization

**1. Batch Processing**
```python
# Process multiple sessions in parallel
import asyncio

async def process_sessions_batch(session_ids: list[str]):
    tasks = [
        process_single_session(session_id)
        for session_id in session_ids
    ]
    results = await asyncio.gather(*tasks)
    return results
```

**2. Prompt Caching**
```python
# Cache extraction prompts
from functools import lru_cache

@lru_cache(maxsize=100)
def get_extraction_prompt(topic: str, use_few_shot: bool):
    return build_extraction_prompt(topic, use_few_shot)
```

**3. Model Selection**
```python
# Use cheaper models for simple extraction
EXTRACTION_ANTHROPIC_MODEL=claude-3-haiku-20240307  # Faster, cheaper
```

### Consolidation Engine Optimization

**1. Limit Comparison Scope**
```python
# Only compare memories within same topic
consolidation_engine.consolidate(
    memories=memories,
    scope_filter={"topic": "outdoor_activities"}
)
```

**2. Early Termination**
```python
# Stop after finding N candidates
max_merge_candidates = 50  # Limit comparisons
```

**3. Incremental Consolidation**
```python
# Consolidate new memories only
new_memory_ids = [...]
existing_memories = fetch_memories_by_ids(new_memory_ids)
consolidation_engine.consolidate(existing_memories)
```

### Embedding Service Optimization

**1. Batch Sizing**
```python
# Optimize batch size for throughput
EMBEDDING_BATCH_SIZE=100  # Process 100 texts at once
```

**2. Connection Reuse**
```python
# Reuse HTTP client
class EmbeddingService:
    def __init__(self):
        self._client = OpenAI()  # Reuse connection pool
```

**3. Caching**
```python
# Cache embeddings for common texts
@lru_cache(maxsize=1000)
def get_embedding_cached(text: str):
    return embedding_service.generate_embedding(text)
```

### Overall System Optimization

**1. Async Operations**
```python
# Run extraction, embedding, consolidation in parallel where possible
async def process_memories(events):
    # Extract
    facts = await asyncio.to_thread(
        extraction_engine.extract_memories,
        events
    )

    # Generate embeddings in parallel
    embedding_tasks = [
        embedding_service.generate_embedding_async(fact)
        for fact in facts
    ]
    embeddings = await asyncio.gather(*embedding_tasks)
```

**2. Database Connection Pooling**
```python
# Use connection pooling for PostgreSQL
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=10
```

**3. Worker Scaling**
```python
# Scale background workers based on queue depth
MEMORY_GENERATION_WORKER_CONCURRENCY=10
CONSOLIDATION_WORKER_CONCURRENCY=5
```

---

## Monitoring & Observability

### Key Metrics to Track

#### Extraction Engine Metrics

```python
# Prometheus metrics
extraction_requests_total = Counter(
    'extraction_requests_total',
    'Total extraction requests'
)

extraction_duration_seconds = Histogram(
    'extraction_duration_seconds',
    'Time to extract memories'
)

memories_extracted_total = Counter(
    'memories_extracted_total',
    'Total memories extracted'
)

extraction_llm_api_errors = Counter(
    'extraction_llm_api_errors',
    'LLM API errors'
)
```

#### Consolidation Engine Metrics

```python
consolidation_requests_total = Counter(
    'consolidation_requests_total',
    'Total consolidation requests'
)

memories_merged_total = Counter(
    'memories_merged_total',
    'Total memories merged'
)

conflicts_detected_total = Counter(
    'conflicts_detected_total',
    'Total conflicts detected'
)

consolidation_duration_seconds = Histogram(
    'consolidation_duration_seconds',
    'Time to consolidate memories'
)
```

#### Embedding Service Metrics

```python
embeddings_generated_total = Counter(
    'embeddings_generated_total',
    'Total embeddings generated'
)

embedding_api_duration_seconds = Histogram(
    'embedding_api_duration_seconds',
    'OpenAI API call duration'
)

embedding_batch_size = Histogram(
    'embedding_batch_size',
    'Number of texts per batch'
)
```

### Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

# Extraction logging
logger.info(
    "Extraction completed",
    extra={
        "session_id": str(session_id),
        "memories_extracted": result.memory_count,
        "duration_ms": duration,
        "llm_model": settings.anthropic_model
    }
)

# Consolidation logging
logger.info(
    "Consolidation completed",
    extra={
        "scope": scope,
        "memories_processed": len(memories),
        "memories_merged": result.merge_count,
        "conflicts_detected": result.conflict_count
    }
)

# Embedding logging
logger.info(
    "Embeddings generated",
    extra={
        "batch_size": len(texts),
        "model": settings.openai_embedding_model,
        "dimensions": settings.openai_embedding_dimensions
    }
)
```

### Distributed Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("extract_memories")
def extract_memories(events):
    span = trace.get_current_span()
    span.set_attribute("event_count", len(events))

    # Extraction logic
    result = extraction_engine.extract_memories(events)

    span.set_attribute("memories_extracted", result.memory_count)
    return result
```

---

## Production Best Practices

### Error Handling

**1. Extraction Engine**
```python
try:
    result = extraction_engine.extract_memories(events)
except AnthropicError as e:
    logger.error(f"LLM API error: {e}")
    # Retry with exponential backoff
    await retry_with_backoff(extraction_engine.extract_memories, events)
except Exception as e:
    logger.exception("Unexpected extraction error")
    # Send to dead letter queue
    await send_to_dlq(request, error=str(e))
```

**2. Consolidation Engine**
```python
try:
    result = consolidation_engine.consolidate(memories)
except Exception as e:
    logger.exception("Consolidation failed")
    # Fall back to storing without consolidation
    for memory in new_memories:
        await memory_service.create_memory(memory)
```

**3. Embedding Service**
```python
try:
    embeddings = embedding_service.generate_embeddings(texts)
except OpenAIError as e:
    logger.error(f"Embedding API error: {e}")
    # Store memories without embeddings (generate later)
    embeddings = [[0.0] * 1536 for _ in texts]
```

### Resource Management

**1. LLM Rate Limiting**
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=50, period=60)  # 50 calls per minute
def call_llm_api(prompt):
    return llm_client.generate(prompt)
```

**2. Connection Pooling**
```python
# Configure HTTP client pools
http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

**3. Memory Management**
```python
# Clear large objects after processing
def process_large_batch(memories):
    result = consolidation_engine.consolidate(memories)

    # Clear memory
    del memories
    gc.collect()

    return result
```

### Data Quality Assurance

**1. Validation Before Storage**
```python
def validate_extracted_memory(memory: dict) -> bool:
    """Validate memory quality."""

    # Required fields
    if not all(k in memory for k in ["fact", "confidence"]):
        return False

    # Confidence range
    if not (0.0 <= memory["confidence"] <= 1.0):
        return False

    # Fact length
    if not (10 <= len(memory["fact"]) <= 500):
        return False

    return True
```

**2. Deduplication Check**
```python
async def check_duplicate(fact: str, embedding: list[float], scope: dict):
    """Check if similar memory exists."""

    results = await vector_store.search(
        query_vector=embedding,
        limit=1,
        score_threshold=0.95,
        query_filter=scope
    )

    return len(results) > 0  # Duplicate found
```

---

## Troubleshooting Guide

### Issue: Extraction Producing No Memories

**Symptoms**:
- `extraction_result.memory_count == 0`
- Empty memories list

**Possible Causes**:

1. **Insufficient events**
   ```python
   # Check event count
   if len(events) < settings.extraction_min_events:
       # Not enough events to extract from
   ```
   **Solution**: Ensure at least 2-5 events

2. **Low confidence filtering**
   ```python
   # All memories filtered out
   min_confidence = 0.5
   ```
   **Solution**: Lower threshold or improve conversation quality

3. **LLM API error**
   ```python
   if extraction_result.error:
       print(extraction_result.error)
   ```
   **Solution**: Check API keys, rate limits, network

### Issue: Consolidation Not Merging

**Symptoms**:
- `consolidation_result.merge_count == 0`
- Similar memories not merged

**Debugging**:
```python
# Check similarity scores
for i, mem1 in enumerate(memories):
    for mem2 in memories[i+1:]:
        sim = consolidation_engine._calculate_similarity(mem1, mem2)
        print(f"'{mem1.fact}' <-> '{mem2.fact}': {sim:.3f}")

# Check threshold
print(f"Threshold: {settings.similarity_threshold}")

# Test with lower threshold
settings.similarity_threshold = 0.75
result = consolidation_engine.consolidate(memories)
```

### Issue: Slow Processing

**Symptoms**:
- High latency (>30s for extraction)
- Timeouts

**Solutions**:

1. **Reduce LLM max_tokens**
   ```python
   EXTRACTION_ANTHROPIC_MAX_TOKENS=2000  # Down from 4000
   ```

2. **Batch operations**
   ```python
   # Process in smaller batches
   for batch in chunk(memories, size=100):
       consolidation_engine.consolidate(batch)
   ```

3. **Add timeouts**
   ```python
   result = await asyncio.wait_for(
       extraction_engine.extract_memories(events),
       timeout=30.0
   )
   ```

---

**Related Documentation**:
- [MEMORY_LIFECYCLE.md](MEMORY_LIFECYCLE.md) - Complete memory lifecycle with processing layer integration
- [MESSAGING.md](MESSAGING.md) - Message queue system for async processing
- [EMBEDDINGS.md](EMBEDDINGS.md) - Detailed embedding service documentation
- [VECTOR_SEARCH.md](VECTOR_SEARCH.md) - Qdrant vector search details
- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete system architecture

---

**Last Updated**: December 2025

For questions about the processing layer, please open an issue on GitHub.
