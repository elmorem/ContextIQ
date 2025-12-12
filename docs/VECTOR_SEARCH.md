# Vector Search Guide

Comprehensive guide to vector search in ContextIQ using Qdrant vector database, covering configuration, indexing, search operations, and optimization.

## Table of Contents

1. [Overview](#overview)
2. [Qdrant Vector Database](#qdrant-vector-database)
3. [Architecture](#architecture)
4. [Configuration](#configuration)
5. [Collections](#collections)
6. [HNSW Indexing](#hnsw-indexing)
7. [Search Operations](#search-operations)
8. [Vector Operations](#vector-operations)
9. [Filtering](#filtering)
10. [Usage Examples](#usage-examples)
11. [Performance Tuning](#performance-tuning)
12. [Scaling Considerations](#scaling-considerations)
13. [Monitoring](#monitoring)
14. [Troubleshooting](#troubleshooting)
15. [Best Practices](#best-practices)

---

## Overview

Vector search enables semantic similarity search over embeddings, allowing ContextIQ to find related memories based on meaning rather than exact text matches.

### What is Vector Search?

Vector search finds similar items by comparing their vector representations in high-dimensional space using distance metrics. Unlike traditional keyword search, it understands semantic meaning:

```
Query: "User enjoys coffee"
Embedding: [0.2, -0.5, 0.8, ...]

Similar Memories:
1. "User likes espresso" (score: 0.92)
2. "User prefers tea in morning" (score: 0.78)
3. "User drinks beverages" (score: 0.65)
```

### Why Vector Search?

1. **Semantic Understanding**: Finds conceptually similar content
2. **Multilingual**: Works across languages
3. **Fuzzy Matching**: Handles typos and variations
4. **Scalability**: Efficiently searches millions of vectors
5. **Real-time**: Sub-millisecond search performance

### Vector Search Pipeline

```
Query Text → Generate Embedding → Vector Search → Rank Results → Return Memories
     ↓              ↓                    ↓             ↓              ↓
"coffee"    [0.2, -0.5, ...]    Find similar    Sort by      Top 10 matches
                                   vectors      similarity
```

---

## Qdrant Vector Database

ContextIQ uses Qdrant as its vector database for storing and searching embeddings.

### Why Qdrant?

1. **Performance**: Written in Rust for maximum speed
2. **Scalability**: Handles billions of vectors
3. **Rich Filtering**: Combines vector search with metadata filters
4. **HNSW Indexing**: State-of-the-art approximate nearest neighbor search
5. **Production-Ready**: Battle-tested in production environments
6. **Developer-Friendly**: Excellent Python SDK and API

### Qdrant Features Used

| Feature | Usage in ContextIQ |
|---------|-------------------|
| **Collections** | Store memory embeddings (1536 dims) |
| **HNSW Index** | Fast similarity search |
| **Cosine Similarity** | Semantic distance metric |
| **Payload Filtering** | Filter by user_id, session_id, etc. |
| **Batch Operations** | Bulk upsert/delete |
| **Point Retrieval** | Get specific memories by ID |

### Qdrant Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Qdrant Server                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Collections                                 │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  memories (1536 dimensions, cosine)            │  │  │
│  │  │  ┌──────────────┐  ┌──────────────┐            │  │  │
│  │  │  │ HNSW Index   │  │   Payload    │            │  │  │
│  │  │  │  - m: 16     │  │   Storage    │            │  │  │
│  │  │  │  - ef: 100   │  │              │            │  │  │
│  │  │  └──────────────┘  └──────────────┘            │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### System Integration

```
┌──────────────────────────────────────────────────────────────┐
│                   ContextIQ Application                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐      ┌──────────────────┐               │
│  │ Memory Service │      │ Search Service   │               │
│  └───────┬────────┘      └────────┬─────────┘               │
│          │                        │                          │
│          └───────┬────────────────┘                          │
│                  │                                            │
│         ┌────────▼────────────┐                              │
│         │ QdrantClientWrapper │                              │
│         └────────┬────────────┘                              │
│                  │                                            │
│         ┌────────▼────────────┐                              │
│         │   Qdrant Client     │                              │
│         │   (Python SDK)      │                              │
│         └────────┬────────────┘                              │
└──────────────────┼──────────────────────────────────────────┘
                   │
                   │ HTTP/gRPC
                   │
          ┌────────▼────────────┐
          │  Qdrant Server      │
          │  (Vector Database)  │
          └─────────────────────┘
```

### Data Flow

#### Storing Vectors

```
1. Memory Created → 2. Generate Embedding → 3. Upsert to Qdrant
        ↓                    ↓                      ↓
   "User likes         [0.2, -0.5, ...]      Store in memories
    coffee"                                   collection with
                                              metadata
```

#### Searching Vectors

```
1. Query Text → 2. Generate Embedding → 3. Search Qdrant → 4. Return Results
      ↓               ↓                      ↓                  ↓
  "coffee"      [0.2, -0.5, ...]      Find similar       Top K memories
                                        vectors           with scores
```

### Component Responsibilities

**QdrantClientWrapper**:
- Connection management
- Collection operations (create, delete, exists)
- Point operations (upsert, search, retrieve, delete)
- Batch processing
- Error handling and retries
- Filter conversion

**Collections Module**:
- Collection configuration
- Schema definitions
- Distance metric selection
- HNSW parameters

---

## Configuration

### Environment Variables

Configure Qdrant connection in `.env`:

```bash
# ===== Qdrant Connection Settings =====

# Required: Qdrant server URL
QDRANT_URL=http://localhost:6333

# Optional: API key for authentication (cloud deployments)
QDRANT_API_KEY=your-api-key-here

# Optional: Request timeout in seconds (default: 30, range: 1-300)
QDRANT_TIMEOUT=30

# ===== Connection Pool Settings =====

# Optional: Use gRPC for better performance (default: false)
QDRANT_GRPC=false

# Optional: gRPC port (default: 6334)
QDRANT_GRPC_PORT=6334

# Optional: Prefer gRPC over HTTP when available (default: false)
QDRANT_PREFER_GRPC=false

# ===== Retry Settings =====

# Optional: Maximum retry attempts (default: 3, range: 0-10)
QDRANT_MAX_RETRIES=3

# Optional: Initial delay between retries in seconds (default: 1.0, range: 0.1-10.0)
QDRANT_RETRY_DELAY=1.0

# ===== Performance Settings =====

# Optional: Default batch size for bulk operations (default: 100, range: 1-1000)
QDRANT_BATCH_SIZE=100
```

### Configuration Object

```python
from shared.vector_store.config import QdrantSettings, get_qdrant_settings

# Load settings from environment
settings = get_qdrant_settings()

# Access configuration
print(f"URL: {settings.qdrant_url}")
print(f"Timeout: {settings.qdrant_timeout}s")
print(f"Batch size: {settings.qdrant_batch_size}")

# Create custom settings
custom_settings = QdrantSettings(
    qdrant_url="http://qdrant:6333",
    qdrant_timeout=60,
    qdrant_batch_size=200
)
```

### Settings Validation

```python
class QdrantSettings(BaseSettings):
    qdrant_timeout: int = Field(
        default=30,
        ge=1,      # Minimum 1 second
        le=300,    # Maximum 5 minutes
    )

    qdrant_max_retries: int = Field(
        default=3,
        ge=0,      # No retries
        le=10,     # Maximum 10 retries
    )

    qdrant_batch_size: int = Field(
        default=100,
        ge=1,      # Minimum 1 point
        le=1000,   # Maximum 1000 points
    )
```

---

## Collections

### Collection Configuration

Collections in Qdrant are like tables in SQL - they store vectors with specific configurations.

#### Memories Collection

The primary collection for storing memory embeddings:

```python
from shared.vector_store.collections import get_memory_collection_config

config = get_memory_collection_config()

# Configuration details:
# - Name: "memories"
# - Vector size: 1536 (OpenAI text-embedding-3-small)
# - Distance: Cosine similarity
# - On disk: false (kept in memory for speed)
# - HNSW: m=16, ef_construct=100
```

### Collection Properties

```python
@dataclass
class CollectionConfig:
    name: str              # Collection name
    vector_size: int       # Embedding dimensions
    distance: DistanceMetric  # Similarity metric
    on_disk: bool         # Store on disk vs memory
    hnsw_config: dict     # HNSW indexing parameters
    optimizers_config: dict  # Optimization settings
```

### Distance Metrics

ContextIQ uses **Cosine** similarity by default:

```python
class DistanceMetric(str, Enum):
    COSINE = "Cosine"      # Angular distance (default)
    EUCLIDEAN = "Euclid"   # L2 distance
    DOT = "Dot"            # Dot product
```

**Distance Metric Comparison**:

| Metric | Formula | Range | Use Case |
|--------|---------|-------|----------|
| **Cosine** | 1 - cos(θ) | [0, 2] | Text similarity (recommended) |
| **Euclidean** | √Σ(ai - bi)² | [0, ∞] | Spatial distance |
| **Dot Product** | Σ(ai × bi) | [-∞, ∞] | Pre-normalized vectors |

**Why Cosine?**
- Direction matters more than magnitude
- Normalized by vector length
- Standard for text embeddings
- Works well with OpenAI embeddings

### Creating Collections

```python
from shared.vector_store import QdrantClientWrapper
from shared.vector_store.collections import get_memory_collection_config

# Initialize client
wrapper = QdrantClientWrapper()

# Get collection configuration
config = get_memory_collection_config()

# Create collection
created = wrapper.create_collection(config)

if created:
    print("Collection created successfully")
else:
    print("Collection already exists")
```

### Collection Management

```python
# Check if collection exists
exists = wrapper.collection_exists("memories")

# Delete collection
deleted = wrapper.delete_collection("memories")

# Count points in collection
count = wrapper.count_points("memories", exact=True)
print(f"Collection has {count} vectors")
```

---

## HNSW Indexing

### What is HNSW?

HNSW (Hierarchical Navigable Small World) is a graph-based algorithm for approximate nearest neighbor search.

```
Layer 2:  [A]──────────[B]
          │            │
Layer 1:  [A]─[C]─[D]─[B]─[E]
          │ ╲ │ ╱ │ ╲ │ ╱ │
Layer 0:  [A][C][D][B][E][F][G][H]
```

**How it Works**:
1. Builds multi-layer graph of vectors
2. Each layer has decreasing connectivity
3. Search starts at top layer (sparse)
4. Drops down through layers to find neighbors
5. Returns approximate nearest neighbors

### HNSW Parameters

```python
hnsw_config = {
    "m": 16,                    # Edges per node
    "ef_construct": 100,        # Search width during construction
    "full_scan_threshold": 10000  # Switch to exact search threshold
}
```

#### Parameter: `m` (Number of Edges)

Controls the number of bi-directional links per node in the graph.

**Default**: 16

```python
# Low connectivity (faster build, less accurate search)
"m": 8

# Medium connectivity (balanced)
"m": 16  # Recommended

# High connectivity (slower build, more accurate search)
"m": 32
```

**Trade-offs**:

| m Value | Build Speed | Search Accuracy | Memory Usage | Search Speed |
|---------|-------------|-----------------|--------------|--------------|
| 4-8 | Fast | Lower | Low | Faster |
| 12-16 | Medium | Good | Medium | Medium |
| 24-32 | Slow | High | High | Slower |

**Guidelines**:
- **Small datasets (<100K)**: m=8-12
- **Medium datasets (100K-1M)**: m=16 (default)
- **Large datasets (>1M)**: m=16-24
- **Maximum accuracy**: m=32-48

#### Parameter: `ef_construct` (Construction Search Width)

Controls the size of the dynamic candidate list during index construction.

**Default**: 100

```python
# Fast construction, lower quality index
"ef_construct": 64

# Balanced (recommended)
"ef_construct": 100

# Slow construction, higher quality index
"ef_construct": 200
```

**Trade-offs**:

| ef_construct | Build Speed | Index Quality | Recommendations |
|--------------|-------------|---------------|-----------------|
| 50-64 | Fast | Lower | Development, testing |
| 100-128 | Medium | Good | Production (default) |
| 200-400 | Slow | Excellent | High-precision needs |

**Guidelines**:
- Should be larger than `m` (typically 2-4× larger)
- Minimum: 2 × m
- Recommended: 100-200
- High precision: 400-1000

#### Parameter: `full_scan_threshold`

Number of vectors below which exact search is used instead of HNSW.

**Default**: 10000

```python
# Use HNSW even for small collections
"full_scan_threshold": 1000

# Use exact search for medium collections
"full_scan_threshold": 10000  # Default

# Prefer HNSW for larger collections
"full_scan_threshold": 50000
```

**When Exact Search is Better**:
- Collections with <10,000 vectors
- Highest precision required
- Search speed not critical

### HNSW Performance Characteristics

```
Vectors: 1M vectors, 1536 dimensions

Search Performance:
- Recall@10: ~99%
- Search time: 1-5ms
- Memory overhead: ~200-300 bytes per vector

Build Performance:
- Construction time: ~30 minutes
- Memory during build: ~2GB
```

### Tuning HNSW for Different Scenarios

#### High Throughput (Real-time Search)

```python
hnsw_config = {
    "m": 16,
    "ef_construct": 100,
    "full_scan_threshold": 10000
}

# At search time, use lower ef
search_params = {"hnsw_ef": 64}  # Faster, slightly lower recall
```

#### High Precision (Batch Processing)

```python
hnsw_config = {
    "m": 24,
    "ef_construct": 200,
    "full_scan_threshold": 10000
}

# At search time, use higher ef
search_params = {"hnsw_ef": 128}  # Slower, higher recall
```

#### Large Scale (Millions of Vectors)

```python
hnsw_config = {
    "m": 16,              # Keep moderate for memory
    "ef_construct": 150,  # Higher quality index
    "full_scan_threshold": 50000
}
```

---

## Search Operations

### Similarity Search

Find vectors most similar to a query vector:

```python
from shared.vector_store import QdrantClientWrapper

wrapper = QdrantClientWrapper()

# Query embedding (from embedding service)
query_vector = [0.2, -0.5, 0.8, ...]  # 1536 dimensions

# Search for similar memories
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,                    # Top 10 results
    score_threshold=0.7          # Minimum similarity score
)

# Process results
for result in results:
    print(f"ID: {result['id']}")
    print(f"Score: {result['score']:.3f}")
    print(f"Fact: {result['payload']['fact']}")
```

### Search Parameters

```python
def search(
    collection_name: str,
    query_vector: list[float],
    limit: int = 10,                    # Number of results
    score_threshold: float | None = None,  # Minimum score
    query_filter: dict | None = None    # Metadata filters
) -> list[dict]:
```

**Parameters**:

- **query_vector**: The embedding to search for (1536 dimensions)
- **limit**: Maximum number of results to return
- **score_threshold**: Minimum similarity score (0.0 to 1.0 for cosine)
- **query_filter**: Filter results by payload fields

### Understanding Search Scores

With **Cosine** distance, scores represent similarity:

```
Score Range: 0.0 to 1.0 (higher is more similar)

1.0 = Identical vectors
0.9-1.0 = Very similar (paraphrases, same topic)
0.7-0.9 = Related (similar concepts)
0.5-0.7 = Somewhat related
< 0.5 = Different topics
```

**Example Score Interpretation**:

```python
Query: "User likes coffee"

Results:
1. "User enjoys espresso" (score: 0.95) → Nearly identical
2. "User prefers tea" (score: 0.82) → Related beverage preference
3. "User drinks water" (score: 0.68) → Same category (beverages)
4. "User plays guitar" (score: 0.23) → Unrelated
```

### Search with Filters

Combine vector similarity with metadata filtering:

```python
# Search for similar memories for specific user
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,
    query_filter={
        "user_id": "user123",
        "confidence": 0.8  # Only high-confidence memories
    }
)
```

### Advanced Search Patterns

#### Semantic Deduplication

Find duplicate memories:

```python
def find_duplicates(
    memory_embedding: list[float],
    wrapper: QdrantClientWrapper,
    threshold: float = 0.95
) -> list[dict]:
    """Find very similar (duplicate) memories."""
    results = wrapper.search(
        collection_name="memories",
        query_vector=memory_embedding,
        limit=5,
        score_threshold=threshold  # Very high threshold
    )

    return results  # Likely duplicates
```

#### Multi-stage Search

Narrow down with filters, then rank by similarity:

```python
def search_user_memories(
    query: str,
    user_id: str,
    embedding_service,
    wrapper: QdrantClientWrapper
):
    """Search within specific user's memories."""
    # Generate query embedding
    result = embedding_service.generate_embedding(query)
    if not result.success:
        return []

    # Search with user filter
    results = wrapper.search(
        collection_name="memories",
        query_vector=result.embeddings[0],
        limit=10,
        query_filter={"user_id": user_id}
    )

    return results
```

#### Threshold Optimization

Find optimal threshold for your use case:

```python
def optimize_threshold(
    test_queries: list[tuple[str, list[str]]],  # (query, expected_results)
    embedding_service,
    wrapper: QdrantClientWrapper
):
    """Find best score threshold for precision/recall."""
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    metrics = {}

    for threshold in thresholds:
        precision_scores = []
        recall_scores = []

        for query, expected in test_queries:
            # Generate query embedding
            result = embedding_service.generate_embedding(query)
            query_vector = result.embeddings[0]

            # Search with threshold
            results = wrapper.search(
                collection_name="memories",
                query_vector=query_vector,
                limit=10,
                score_threshold=threshold
            )

            # Calculate metrics
            retrieved = [r['id'] for r in results]
            true_positives = len(set(retrieved) & set(expected))
            precision = true_positives / len(retrieved) if retrieved else 0
            recall = true_positives / len(expected) if expected else 0

            precision_scores.append(precision)
            recall_scores.append(recall)

        metrics[threshold] = {
            'precision': sum(precision_scores) / len(precision_scores),
            'recall': sum(recall_scores) / len(recall_scores)
        }

    return metrics
```

---

## Vector Operations

### Upserting Vectors

Add or update vectors in the collection:

```python
from shared.vector_store import QdrantClientWrapper

wrapper = QdrantClientWrapper()

# Prepare points
points = [
    {
        "id": "mem_001",
        "vector": [0.1, 0.2, 0.3, ...],  # 1536 dimensions
        "payload": {
            "fact": "User likes coffee",
            "user_id": "user123",
            "confidence": 0.9,
            "created_at": "2025-01-15T10:00:00Z"
        }
    },
    {
        "id": "mem_002",
        "vector": [0.4, 0.5, 0.6, ...],
        "payload": {
            "fact": "User prefers tea",
            "user_id": "user123",
            "confidence": 0.85
        }
    }
]

# Upsert points
count = wrapper.upsert_points(
    collection_name="memories",
    points=points
)

print(f"Upserted {count} points")
```

### Batch Upsert

For large datasets, use batch operations:

```python
# Large dataset
large_dataset = [
    {"id": f"mem_{i}", "vector": [...], "payload": {...}}
    for i in range(10000)
]

# Upsert in batches of 100 (default)
count = wrapper.upsert_points(
    collection_name="memories",
    points=large_dataset,
    batch_size=100
)

# Or custom batch size
count = wrapper.upsert_points(
    collection_name="memories",
    points=large_dataset,
    batch_size=500  # Larger batches for faster throughput
)
```

### Retrieving Vectors

Get specific vectors by ID:

```python
# Get single point
point = wrapper.get_point(
    collection_name="memories",
    point_id="mem_001"
)

if point:
    print(f"ID: {point['id']}")
    print(f"Vector: {point['vector'][:5]}...")  # First 5 dimensions
    print(f"Payload: {point['payload']}")
else:
    print("Point not found")
```

### Deleting Vectors

Remove vectors from the collection:

```python
# Delete single point
count = wrapper.delete_points(
    collection_name="memories",
    point_ids=["mem_001"]
)

# Delete multiple points
count = wrapper.delete_points(
    collection_name="memories",
    point_ids=["mem_001", "mem_002", "mem_003"]
)

print(f"Deleted {count} points")
```

### UUID Support

ContextIQ supports both string and UUID identifiers:

```python
from uuid import uuid4, UUID

# String IDs
wrapper.upsert_points("memories", [
    {"id": "mem_001", "vector": [...], "payload": {...}}
])

# UUID IDs
memory_id = uuid4()
wrapper.upsert_points("memories", [
    {"id": memory_id, "vector": [...], "payload": {...}}
])

# Retrieve by UUID
point = wrapper.get_point("memories", memory_id)

# Delete by UUID
wrapper.delete_points("memories", [memory_id])
```

---

## Filtering

### Filter Syntax

Combine vector search with metadata filters:

```python
# Simple equality filter
query_filter = {
    "user_id": "user123"
}

results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,
    query_filter=query_filter
)
```

### Filter Conversion

The wrapper converts simple dictionaries to Qdrant Filter objects:

```python
def _convert_filter(self, filter_dict: dict) -> models.Filter:
    """
    Convert filter dictionary to Qdrant Filter model.

    Supports:
    - Equality: {"key": "value"}
    - Multiple conditions: {"key1": "value1", "key2": "value2"}
    """
    conditions = []

    for key, value in filter_dict.items():
        conditions.append(
            models.FieldCondition(
                key=key,
                match=models.MatchValue(value=value)
            )
        )

    return models.Filter(must=conditions)
```

### Common Filter Patterns

#### User-scoped Search

```python
# Find memories for specific user
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    query_filter={"user_id": "user123"}
)
```

#### Confidence Threshold

```python
# Only high-confidence memories
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    query_filter={"confidence": 0.8}  # Note: exact match
)
```

#### Session-based Filter

```python
# Memories from specific session
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    query_filter={"source_session_id": "session_456"}
)
```

#### Combined Filters

```python
# Multiple conditions (AND)
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    query_filter={
        "user_id": "user123",
        "source_type": "extracted"
    }
)
```

### Advanced Filtering (Direct Qdrant API)

For complex filters, use Qdrant client directly:

```python
from qdrant_client.http import models

# Range filter
results = wrapper.client.search(
    collection_name="memories",
    query_vector=query_vector,
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="confidence",
                range=models.Range(gte=0.7, lte=1.0)
            )
        ]
    ),
    limit=10
)

# Multiple conditions with OR
results = wrapper.client.search(
    collection_name="memories",
    query_vector=query_vector,
    query_filter=models.Filter(
        should=[  # OR conditions
            models.FieldCondition(key="user_id", match=models.MatchValue(value="user123")),
            models.FieldCondition(key="user_id", match=models.MatchValue(value="user456"))
        ]
    ),
    limit=10
)
```

---

## Usage Examples

### Basic Search Flow

```python
from shared.embedding import EmbeddingService
from shared.vector_store import QdrantClientWrapper

# Initialize services
embedding_service = EmbeddingService()
vector_store = QdrantClientWrapper()

# 1. Generate query embedding
query = "What does the user like to drink?"
result = embedding_service.generate_embedding(query)

if not result.success:
    print(f"Embedding failed: {result.error}")
    exit(1)

query_vector = result.embeddings[0]

# 2. Search for similar memories
results = vector_store.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=5,
    score_threshold=0.7
)

# 3. Process results
print(f"Found {len(results)} relevant memories:\n")

for i, result in enumerate(results, 1):
    print(f"{i}. {result['payload']['fact']}")
    print(f"   Score: {result['score']:.3f}")
    print(f"   User: {result['payload'].get('user_id', 'unknown')}")
    print()
```

### Memory Storage Example

```python
from shared.embedding import EmbeddingService
from shared.vector_store import QdrantClientWrapper
from uuid import uuid4

async def store_memory(
    user_id: str,
    fact: str,
    session_id: str,
    confidence: float,
    embedding_service: EmbeddingService,
    vector_store: QdrantClientWrapper
):
    """Store a memory with its embedding."""
    # Generate embedding
    result = embedding_service.generate_embedding(fact)

    if not result.success:
        return {"error": f"Embedding failed: {result.error}"}

    # Prepare point
    memory_id = uuid4()
    point = {
        "id": str(memory_id),
        "vector": result.embeddings[0],
        "payload": {
            "fact": fact,
            "user_id": user_id,
            "source_session_id": session_id,
            "confidence": confidence,
            "source_type": "extracted"
        }
    }

    # Store in Qdrant
    count = vector_store.upsert_points(
        collection_name="memories",
        points=[point]
    )

    if count == 1:
        return {"memory_id": str(memory_id), "success": True}
    else:
        return {"error": "Failed to store memory"}
```

### Batch Import Example

```python
from shared.embedding import EmbeddingService
from shared.vector_store import QdrantClientWrapper

def import_memories(
    memories: list[dict],
    embedding_service: EmbeddingService,
    vector_store: QdrantClientWrapper
):
    """
    Import batch of memories with embeddings.

    memories: [{"id": "...", "fact": "...", "user_id": "...", ...}, ...]
    """
    # Extract facts for embedding
    facts = [m["fact"] for m in memories]

    # Generate embeddings in batch
    result = embedding_service.generate_embeddings(facts)

    if not result.success:
        return {"error": f"Embedding generation failed: {result.error}"}

    # Prepare points
    points = []
    for i, memory in enumerate(memories):
        point = {
            "id": memory["id"],
            "vector": result.embeddings[i],
            "payload": {
                "fact": memory["fact"],
                "user_id": memory["user_id"],
                "confidence": memory.get("confidence", 1.0),
                "source_type": memory.get("source_type", "imported")
            }
        }
        points.append(point)

    # Batch upsert
    count = vector_store.upsert_points(
        collection_name="memories",
        points=points,
        batch_size=100
    )

    return {
        "success": True,
        "imported": count,
        "total": len(memories)
    }
```

### Deduplication Example

```python
from shared.embedding import EmbeddingService
from shared.vector_store import QdrantClientWrapper

async def check_duplicate_memory(
    new_fact: str,
    user_id: str,
    embedding_service: EmbeddingService,
    vector_store: QdrantClientWrapper,
    threshold: float = 0.95
) -> dict:
    """Check if memory is duplicate of existing memory."""
    # Generate embedding for new fact
    result = embedding_service.generate_embedding(new_fact)

    if not result.success:
        return {"is_duplicate": False, "error": result.error}

    # Search for very similar memories
    similar = vector_store.search(
        collection_name="memories",
        query_vector=result.embeddings[0],
        limit=3,
        score_threshold=threshold,
        query_filter={"user_id": user_id}
    )

    if similar:
        return {
            "is_duplicate": True,
            "duplicate_of": similar[0]["id"],
            "similarity": similar[0]["score"],
            "existing_fact": similar[0]["payload"]["fact"]
        }
    else:
        return {"is_duplicate": False}
```

### Memory Consolidation Example

From consolidation worker:

```python
from shared.embedding import EmbeddingService
from shared.vector_store import QdrantClientWrapper

async def consolidate_and_store(
    merged_memories: list[dict],
    superseded_ids: list[str],
    embedding_service: EmbeddingService,
    vector_store: QdrantClientWrapper
):
    """Store consolidated memories and remove superseded ones."""
    # Generate embeddings for merged memories
    merged_facts = [m["fact"] for m in merged_memories]
    result = embedding_service.generate_embeddings(merged_facts)

    if not result.success:
        return {"error": f"Embedding failed: {result.error}"}

    # Prepare consolidated points
    points = []
    for i, memory in enumerate(merged_memories):
        point = {
            "id": memory["id"],
            "vector": result.embeddings[i],
            "payload": {
                "fact": memory["fact"],
                "user_id": memory["user_id"],
                "confidence": memory["confidence"],
                "source_type": "consolidated"
            }
        }
        points.append(point)

    # Store consolidated memories
    upserted = vector_store.upsert_points(
        collection_name="memories",
        points=points
    )

    # Delete superseded memories
    deleted = vector_store.delete_points(
        collection_name="memories",
        point_ids=superseded_ids
    )

    return {
        "consolidated": upserted,
        "removed": deleted,
        "success": True
    }
```

---

## Performance Tuning

### 1. Search Performance

#### Adjust ef Parameter (Search-time)

```python
from qdrant_client.http import models

# Fast search (lower recall)
results = wrapper.client.search(
    collection_name="memories",
    query_vector=query_vector,
    search_params=models.SearchParams(hnsw_ef=32),
    limit=10
)

# Balanced (default)
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10
)  # Uses ef=128 (default)

# High recall (slower)
results = wrapper.client.search(
    collection_name="memories",
    query_vector=query_vector,
    search_params=models.SearchParams(hnsw_ef=256),
    limit=10
)
```

**ef Guidelines**:

| ef Value | Search Speed | Recall@10 | Use Case |
|----------|--------------|-----------|----------|
| 32-64 | Very fast | ~95% | Real-time, high QPS |
| 128 | Fast | ~98% | Default |
| 256-512 | Medium | ~99.5% | High precision |

### 2. Batch Size Optimization

```python
# Small batches: Better for memory, slower throughput
wrapper.upsert_points(points, batch_size=50)

# Medium batches: Balanced (recommended)
wrapper.upsert_points(points, batch_size=100)  # Default

# Large batches: Maximum throughput
wrapper.upsert_points(points, batch_size=500)
```

### 3. Memory vs Disk Storage

```python
# In-memory (faster search, more RAM)
config = CollectionConfig(
    name="memories",
    vector_size=1536,
    distance=DistanceMetric.COSINE,
    on_disk=False  # Keep vectors in RAM
)

# On-disk (slower search, less RAM)
config = CollectionConfig(
    name="memories",
    vector_size=1536,
    distance=DistanceMetric.COSINE,
    on_disk=True  # Store vectors on disk
)
```

**When to Use Disk Storage**:
- Very large collections (>10M vectors)
- Limited RAM
- Search speed not critical
- Cost optimization

### 4. Connection Optimization

#### Use gRPC for Better Performance

```bash
# .env
QDRANT_PREFER_GRPC=true
QDRANT_GRPC_PORT=6334
```

**gRPC Benefits**:
- 2-3× faster than HTTP for batch operations
- Lower latency
- Binary protocol (more efficient)

**When to Use gRPC**:
- High throughput requirements
- Batch operations
- Production deployments

#### Connection Pooling

```python
# Reuse wrapper instance
wrapper = QdrantClientWrapper()

# Bad: Creates new connection each time
for batch in batches:
    temp_wrapper = QdrantClientWrapper()
    temp_wrapper.upsert_points("memories", batch)

# Good: Reuse connection
wrapper = QdrantClientWrapper()
for batch in batches:
    wrapper.upsert_points("memories", batch)
```

### 5. Payload Optimization

**Minimize Payload Size**:

```python
# Bad: Large payloads slow down retrieval
payload = {
    "fact": "User likes coffee",
    "full_conversation": "..." * 10000,  # Huge field!
    "metadata": {...}  # Large nested object
}

# Good: Keep payloads compact
payload = {
    "fact": "User likes coffee",
    "user_id": "user123",
    "confidence": 0.9,
    "source_session_id": "session456"  # Reference, not full data
}
```

### 6. Index Optimization

```python
# For large collections, tune indexing
optimizers_config = {
    "indexing_threshold": 20000,  # Start indexing after 20K vectors
}

config = CollectionConfig(
    name="memories",
    vector_size=1536,
    distance=DistanceMetric.COSINE,
    hnsw_config={
        "m": 16,
        "ef_construct": 100
    },
    optimizers_config=optimizers_config
)
```

### Performance Benchmarks

**Typical Performance (1M vectors, 1536 dims)**:

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Search (ef=128) | 1-5ms | 200-1000 QPS |
| Upsert (batch=100) | 50-100ms | 10K vectors/sec |
| Get by ID | <1ms | 5000 QPS |
| Delete (batch=100) | 10-20ms | 5K deletes/sec |

---

## Scaling Considerations

### Vertical Scaling

**RAM Requirements**:

```python
# Estimate RAM needed for in-memory storage
vectors = 1_000_000
dimensions = 1536
bytes_per_float = 4

vector_data = vectors * dimensions * bytes_per_float
# = 6.4 GB for vectors alone

# Add HNSW index overhead (~20-30%)
total_ram = vector_data * 1.3
# = ~8 GB total

# Add OS and buffer (2× for safety)
recommended_ram = total_ram * 2
# = 16 GB recommended
```

**Scaling Formula**:

```
RAM (GB) = (vectors × dimensions × 4 bytes × 1.3 × 2) / 1GB
         = vectors × dimensions × 10.4e-9

Examples:
- 100K vectors: 1.6 GB
- 1M vectors: 16 GB
- 10M vectors: 160 GB
- 100M vectors: 1.6 TB
```

### Horizontal Scaling

For very large deployments:

1. **Sharding by User**:
```python
# Route users to different Qdrant instances
def get_vector_store_for_user(user_id: str) -> QdrantClientWrapper:
    """Route user to specific Qdrant shard."""
    shard = hash(user_id) % NUM_SHARDS

    return QdrantClientWrapper(
        settings=QdrantSettings(
            qdrant_url=f"http://qdrant-shard-{shard}:6333"
        )
    )
```

2. **Qdrant Cluster**:
```bash
# Set up distributed Qdrant cluster
# https://qdrant.tech/documentation/guides/distributed_deployment/
```

### Collection Optimization

**Partition Large Collections**:

```python
# Instead of one huge collection
"memories"  # 100M vectors

# Use multiple smaller collections
"memories_2023"  # 20M vectors
"memories_2024"  # 30M vectors
"memories_2025"  # 50M vectors

# Or partition by type
"memories_user"      # User-scope memories
"memories_org"       # Org-scope memories
"memories_global"    # Global memories
```

### Monitoring Resource Usage

```python
def check_collection_stats(
    wrapper: QdrantClientWrapper,
    collection_name: str
) -> dict:
    """Get collection statistics."""
    # Get collection info
    info = wrapper.client.get_collection(collection_name)

    return {
        "vectors_count": info.vectors_count,
        "indexed_vectors": info.indexed_vectors_count,
        "points_count": info.points_count,
        "segments_count": info.segments_count,
        "status": info.status
    }

# Usage
stats = check_collection_stats(wrapper, "memories")
print(f"Collection has {stats['vectors_count']:,} vectors")
print(f"Status: {stats['status']}")
```

---

## Monitoring

### Health Checks

```python
def vector_store_health_check(wrapper: QdrantClientWrapper) -> dict:
    """Comprehensive health check for vector store."""
    health = {
        "status": "unknown",
        "qdrant_reachable": False,
        "collections": []
    }

    try:
        # Check if Qdrant is reachable
        is_healthy = wrapper.health_check()
        health["qdrant_reachable"] = is_healthy

        if not is_healthy:
            health["status"] = "unhealthy"
            return health

        # Check collections
        collections = wrapper.client.get_collections().collections

        for collection in collections:
            info = wrapper.client.get_collection(collection.name)

            health["collections"].append({
                "name": collection.name,
                "vectors": info.vectors_count,
                "status": info.status
            })

        health["status"] = "healthy"

    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)

    return health
```

### Performance Metrics

```python
import time

class MeteredVectorStore:
    """Vector store wrapper with performance metrics."""

    def __init__(self, wrapper: QdrantClientWrapper):
        self.wrapper = wrapper
        self.metrics = {
            "searches": 0,
            "upserts": 0,
            "deletes": 0,
            "total_search_time": 0.0,
            "total_upsert_time": 0.0
        }

    def search(self, *args, **kwargs):
        """Search with timing."""
        start = time.time()
        results = self.wrapper.search(*args, **kwargs)
        elapsed = time.time() - start

        self.metrics["searches"] += 1
        self.metrics["total_search_time"] += elapsed

        return results

    def upsert_points(self, *args, **kwargs):
        """Upsert with timing."""
        start = time.time()
        count = self.wrapper.upsert_points(*args, **kwargs)
        elapsed = time.time() - start

        self.metrics["upserts"] += 1
        self.metrics["total_upsert_time"] += elapsed

        return count

    def get_stats(self) -> dict:
        """Get performance statistics."""
        searches = self.metrics["searches"]
        upserts = self.metrics["upserts"]

        return {
            "total_searches": searches,
            "total_upserts": upserts,
            "avg_search_time": (
                self.metrics["total_search_time"] / searches
                if searches > 0 else 0
            ),
            "avg_upsert_time": (
                self.metrics["total_upsert_time"] / upserts
                if upserts > 0 else 0
            )
        }
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Connection Failed

**Error**:
```
ConnectionError: Failed to connect to Qdrant at http://localhost:6333
```

**Solutions**:
1. Check Qdrant is running:
```bash
curl http://localhost:6333/
```

2. Verify URL in environment:
```bash
echo $QDRANT_URL
```

3. Check Docker container (if using Docker):
```bash
docker ps | grep qdrant
docker logs qdrant
```

#### Issue 2: Collection Already Exists

**Error**:
```
UnexpectedResponse: Collection 'memories' already exists
```

**Solution**:
```python
# Check before creating
if not wrapper.collection_exists("memories"):
    wrapper.create_collection(config)
```

#### Issue 3: Dimension Mismatch

**Error**:
```
Wrong input: Vector dimension mismatch: expected 1536, got 512
```

**Solution**:
```python
# Ensure embedding dimensions match collection
# Collection config
OPENAI_EMBEDDING_DIMENSIONS=1536  # In .env

# Must match collection
vector_size=1536  # In collection config
```

#### Issue 4: Search Returns No Results

**Possible Causes**:
1. Score threshold too high
2. No vectors in collection
3. Wrong collection name
4. Dimension mismatch

**Debug**:
```python
# Check collection has vectors
count = wrapper.count_points("memories", exact=True)
print(f"Collection has {count} vectors")

# Try search without threshold
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10
    # No score_threshold
)

print(f"Found {len(results)} results")
if results:
    print(f"Top score: {results[0]['score']}")
```

#### Issue 5: Slow Search Performance

**Solutions**:

1. Check collection size:
```python
count = wrapper.count_points("memories")
print(f"Vectors: {count:,}")
# If >10M, consider sharding
```

2. Reduce ef parameter:
```python
# Use lower ef for faster search
search_params = models.SearchParams(hnsw_ef=64)
```

3. Enable gRPC:
```bash
QDRANT_PREFER_GRPC=true
```

4. Check disk vs memory:
```python
info = wrapper.client.get_collection("memories")
# If on_disk=true, consider moving to memory
```

---

## Best Practices

### 1. Connection Management

```python
# Good: Reuse wrapper instance
wrapper = QdrantClientWrapper()
# Use throughout application lifecycle
wrapper.close()  # Close when done

# Bad: Create new wrapper for each operation
def search_memory():
    wrapper = QdrantClientWrapper()  # New connection!
    results = wrapper.search(...)
    wrapper.close()
```

### 2. Error Handling

```python
# Always handle errors
try:
    results = wrapper.search(
        collection_name="memories",
        query_vector=query_vector,
        limit=10
    )
except Exception as e:
    logger.error(f"Search failed: {e}")
    results = []  # Return empty results or retry
```

### 3. Batch Operations

```python
# Good: Batch upsert
points = [...]  # 1000 points
wrapper.upsert_points("memories", points, batch_size=100)

# Bad: Individual upserts
for point in points:
    wrapper.upsert_points("memories", [point])  # 1000 API calls!
```

### 4. Payload Design

```python
# Good: Minimal, indexed fields
payload = {
    "fact": "User likes coffee",
    "user_id": "user123",
    "confidence": 0.9
}

# Bad: Large, nested objects
payload = {
    "fact": "User likes coffee",
    "full_conversation": {...},  # Huge!
    "analysis": {...},  # Not needed for search
    "embedding_metadata": {...}  # Redundant
}
```

### 5. Score Threshold Selection

```python
# Use appropriate thresholds
DUPLICATE_THRESHOLD = 0.95  # Very similar
RELATED_THRESHOLD = 0.75    # Related content
MINIMUM_THRESHOLD = 0.5     # Minimum relevance

# In code
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    score_threshold=RELATED_THRESHOLD
)
```

### 6. Filter Efficiently

```python
# Good: Use filters to reduce search space
results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=10,
    query_filter={"user_id": "user123"}  # Narrow down first
)

# Less efficient: Filter in application code
all_results = wrapper.search(
    collection_name="memories",
    query_vector=query_vector,
    limit=1000  # Get many results
)
filtered = [r for r in all_results if r["payload"]["user_id"] == "user123"]
```

### 7. Monitor Performance

```python
# Track metrics in production
import time

start = time.time()
results = wrapper.search(...)
elapsed = time.time() - start

if elapsed > 0.1:  # 100ms threshold
    logger.warning(f"Slow search: {elapsed:.3f}s")

# Log metrics
metrics.histogram("vector_search.latency", elapsed)
metrics.increment("vector_search.requests")
```

### 8. Version Collections

```python
# Use versioned collection names for migrations
OLD_COLLECTION = "memories_v1"
NEW_COLLECTION = "memories_v2"

# Create new collection with updated config
wrapper.create_collection(new_config)

# Migrate data
# ... migration logic ...

# Switch application to new collection
# Update configuration

# Delete old collection after verification
wrapper.delete_collection(OLD_COLLECTION)
```

---

## See Also

- [Embeddings Guide](./EMBEDDINGS.md) - Generating embeddings for vector search
- [Architecture Overview](./ARCHITECTURE.md) - System architecture and design
- [API Documentation](./API_USAGE.md) - REST API reference
- [Qdrant Documentation](https://qdrant.tech/documentation/) - Official Qdrant docs

---

**Last Updated**: 2025-12-11
**ContextIQ Version**: 0.1.0
