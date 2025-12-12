# Embeddings Guide

Comprehensive guide to text embeddings in ContextIQ, covering OpenAI integration, configuration, architecture, and best practices.

## Table of Contents

1. [Overview](#overview)
2. [OpenAI Embedding Model](#openai-embedding-model)
3. [Architecture](#architecture)
4. [Configuration](#configuration)
5. [Core Components](#core-components)
6. [Embedding Generation](#embedding-generation)
7. [Batch Processing](#batch-processing)
8. [Usage Examples](#usage-examples)
9. [Performance Optimization](#performance-optimization)
10. [Cost Optimization](#cost-optimization)
11. [Error Handling](#error-handling)
12. [Testing](#testing)
13. [Alternative Models](#alternative-models)
14. [Troubleshooting](#troubleshooting)
15. [Best Practices](#best-practices)

---

## Overview

Embeddings are vector representations of text that capture semantic meaning in high-dimensional space. ContextIQ uses embeddings to enable semantic search, memory similarity detection, and intelligent memory consolidation.

### What are Embeddings?

Embeddings convert text into numerical vectors (arrays of floating-point numbers) where semantically similar texts have similar vector representations. This allows for:

- **Semantic Search**: Find content by meaning, not just keywords
- **Similarity Detection**: Identify related memories across conversations
- **Clustering**: Group similar memories together
- **Consolidation**: Merge duplicate or overlapping memories

### Embedding Pipeline in ContextIQ

```
Text Input → Preprocessing → OpenAI API → Vector (1536 dimensions) → Storage
     ↓            ↓              ↓                ↓                    ↓
  "User likes    Truncate    Generate         [0.023, -0.156,    Qdrant
   coffee"       to 8191     embedding         0.891, ...]      Vector DB
                 tokens
```

---

## OpenAI Embedding Model

ContextIQ uses OpenAI's `text-embedding-3-small` model by default, which provides an excellent balance of performance, cost, and quality.

### Model Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Model Name** | `text-embedding-3-small` | Latest generation embedding model |
| **Default Dimensions** | 1536 | Configurable from 256 to 3072 |
| **Max Input Tokens** | 8191 | Approximately 30,000+ characters |
| **Performance** | ~62.3% MTEB score | High quality for most use cases |
| **Cost** | $0.02 per 1M tokens | Very cost-effective |
| **Speed** | ~3000 tokens/sec | Fast generation |

### Why text-embedding-3-small?

1. **Cost-Effective**: 5x cheaper than text-embedding-ada-002
2. **High Quality**: Better performance on most benchmarks
3. **Flexible Dimensions**: Supports dimension reduction for faster search
4. **Production-Ready**: Stable and well-tested by OpenAI
5. **Multilingual**: Supports 100+ languages

### Dimension Trade-offs

The model supports variable output dimensions through matryoshka representation learning:

```python
# Higher dimensions = Better accuracy, slower search, more storage
openai_embedding_dimensions=3072  # Maximum quality

# Default dimensions = Balanced performance
openai_embedding_dimensions=1536  # Recommended

# Lower dimensions = Faster search, less storage, slightly lower accuracy
openai_embedding_dimensions=512   # Good for large-scale deployments
openai_embedding_dimensions=256   # Minimum viable quality
```

**Dimension Benchmarks (MTEB Score)**:
- 3072 dimensions: 62.3%
- 1536 dimensions: 62.0% (minimal loss)
- 512 dimensions: 61.0% (acceptable loss)
- 256 dimensions: 58.8% (noticeable loss)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ContextIQ Application                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────┐                │
│  │  Memory Worker   │      │Consolidation Wkr │                │
│  └────────┬─────────┘      └────────┬─────────┘                │
│           │                         │                           │
│           └────────┬────────────────┘                           │
│                    │                                             │
│           ┌────────▼─────────┐                                  │
│           │ EmbeddingService │                                  │
│           └────────┬─────────┘                                  │
│                    │                                             │
│           ┌────────▼─────────┐                                  │
│           │   OpenAI Client  │                                  │
│           └────────┬─────────┘                                  │
└────────────────────┼─────────────────────────────────────────────┘
                     │
                     │ HTTPS
                     │
            ┌────────▼─────────┐
            │   OpenAI API     │
            │  (Embeddings)    │
            └──────────────────┘
```

### Data Flow

1. **Input**: Memory worker extracts facts from conversation
2. **Batching**: EmbeddingService groups texts into batches
3. **Truncation**: Long texts truncated to 8191 tokens
4. **API Call**: Batch sent to OpenAI embeddings API
5. **Response**: Vector embeddings returned (1536 dimensions each)
6. **Storage**: Vectors stored in Qdrant for similarity search

### Integration Points

The embedding service integrates with:

- **Memory Generation Worker**: Embeds extracted memories
- **Consolidation Worker**: Embeds merged memories
- **Vector Store (Qdrant)**: Stores embeddings for search
- **Memory Service**: Associates embeddings with memory records

---

## Configuration

### Environment Variables

All embedding configuration is managed through environment variables in `.env`:

```bash
# ===== OpenAI API Configuration =====

# Required: Your OpenAI API key
OPENAI_API_KEY=sk-proj-...

# Optional: Embedding model to use (default: text-embedding-3-small)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional: Vector dimensions (default: 1536, range: 256-3072)
OPENAI_EMBEDDING_DIMENSIONS=1536

# Optional: API request timeout in seconds (default: 60, range: 1-300)
OPENAI_TIMEOUT=60

# Optional: Max retry attempts for failed requests (default: 3, range: 0-10)
OPENAI_MAX_RETRIES=3

# ===== Batch Processing Configuration =====

# Optional: Batch size for bulk operations (default: 100, range: 1-2048)
EMBEDDING_BATCH_SIZE=100

# Optional: Max input token length (default: 8191, range: 1-8191)
EMBEDDING_MAX_INPUT_LENGTH=8191
```

### Configuration Object

The `EmbeddingSettings` class manages all configuration:

```python
from shared.embedding.config import EmbeddingSettings, get_embedding_settings

# Load settings from environment
settings = get_embedding_settings()

# Access configuration values
print(f"Model: {settings.openai_embedding_model}")
print(f"Dimensions: {settings.openai_embedding_dimensions}")
print(f"Batch size: {settings.embedding_batch_size}")

# Create custom settings (useful for testing)
custom_settings = EmbeddingSettings(
    openai_api_key="sk-test-key",
    openai_embedding_dimensions=512,
    embedding_batch_size=50
)
```

### Settings Validation

All settings are validated using Pydantic:

```python
class EmbeddingSettings(BaseSettings):
    openai_embedding_dimensions: int = Field(
        default=1536,
        ge=256,      # Minimum 256 dimensions
        le=3072,     # Maximum 3072 dimensions
    )

    openai_timeout: int = Field(
        default=60,
        ge=1,        # Minimum 1 second
        le=300,      # Maximum 5 minutes
    )

    embedding_batch_size: int = Field(
        default=100,
        ge=1,        # Minimum 1 text per batch
        le=2048,     # Maximum 2048 texts per batch
    )
```

Invalid values will raise validation errors at startup.

---

## Core Components

### EmbeddingService

The main service class that handles all embedding operations:

```python
from shared.embedding import EmbeddingService

# Initialize service (loads config from environment)
service = EmbeddingService()

# Or with custom settings
from shared.embedding.config import EmbeddingSettings

settings = EmbeddingSettings(
    openai_api_key="your-key",
    openai_embedding_dimensions=1536
)
service = EmbeddingService(settings=settings)
```

**Key Methods**:

- `generate_embedding(text)`: Generate embedding for single text
- `generate_embeddings(texts)`: Generate embeddings for multiple texts
- `generate_embeddings_batch(texts, batch_size)`: Process large lists in batches
- `close()`: Close OpenAI client connection

**Features**:

- Lazy client initialization (only connects when needed)
- Automatic retry logic with exponential backoff
- Text truncation for long inputs
- Comprehensive error handling
- Context manager support

### EmbeddingResult

Response object containing embedding generation results:

```python
class EmbeddingResult:
    embeddings: list[list[float]]  # Generated vectors
    texts: list[str]               # Original input texts
    model: str                     # Model used (e.g., "text-embedding-3-small")
    dimensions: int                # Vector dimensions
    error: str | None              # Error message if failed

    @property
    def success(self) -> bool:
        """True if generation succeeded"""
        return self.error is None and len(self.embeddings) > 0

    @property
    def count(self) -> int:
        """Number of embeddings generated"""
        return len(self.embeddings)
```

**Usage**:

```python
result = service.generate_embeddings(["Hello world", "Goodbye world"])

if result.success:
    print(f"Generated {result.count} embeddings")
    for i, embedding in enumerate(result.embeddings):
        print(f"Text: {result.texts[i]}")
        print(f"Vector: {embedding[:5]}... ({len(embedding)} dims)")
else:
    print(f"Error: {result.error}")
```

### OpenAI Client

The service uses the official OpenAI Python client:

```python
# Client is created lazily and cached
@property
def client(self) -> OpenAI:
    if self._client is None:
        self._client = OpenAI(
            api_key=self.settings.openai_api_key,
            max_retries=self.settings.openai_max_retries,
            timeout=float(self.settings.openai_timeout),
        )
    return self._client
```

**Client Features**:
- Automatic retries on transient failures
- Request timeout protection
- Connection pooling for efficiency
- Thread-safe operations

---

## Embedding Generation

### Single Text Embedding

Generate an embedding for a single piece of text:

```python
from shared.embedding import EmbeddingService

service = EmbeddingService()

# Generate embedding for single text
result = service.generate_embedding("User prefers dark mode")

if result.success:
    embedding = result.embeddings[0]
    print(f"Vector dimensions: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    # Output: [0.023, -0.156, 0.891, 0.234, -0.445]
```

### Multiple Text Embeddings

Generate embeddings for multiple texts in a single API call:

```python
texts = [
    "User enjoys morning coffee",
    "User prefers tea in the afternoon",
    "User likes dark chocolate"
]

result = service.generate_embeddings(texts)

if result.success:
    for i, embedding in enumerate(result.embeddings):
        print(f"{texts[i]}: {len(embedding)} dimensions")
else:
    print(f"Failed: {result.error}")
```

### Text Preprocessing

The service automatically handles text preprocessing:

#### 1. Truncation for Long Texts

```python
# Texts exceeding 8191 tokens are automatically truncated
long_text = "Very long text..." * 10000

result = service.generate_embedding(long_text)
# Text is truncated to ~32,764 characters (8191 tokens × 4 chars/token estimate)
```

The truncation strategy:

```python
def _truncate_texts(self, texts: list[str]) -> list[str]:
    """
    Truncate texts that exceed maximum input length.

    Uses simple character-based truncation with 4 chars/token estimate.
    For production, consider using tiktoken for accurate token counting.
    """
    max_chars = self.settings.embedding_max_input_length * 4

    truncated = []
    for text in texts:
        if len(text) > max_chars:
            truncated.append(text[:max_chars])
        else:
            truncated.append(text)

    return truncated
```

#### 2. Empty Text Handling

```python
# Empty list raises error
result = service.generate_embeddings([])
# Raises: ValueError("texts cannot be empty")

# Empty strings are allowed (but not recommended)
result = service.generate_embeddings(["", "valid text"])
# Both will get embeddings, but empty string embedding is not meaningful
```

### API Request Format

Under the hood, the service makes this API call:

```python
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=["Text 1", "Text 2", "Text 3"],
    dimensions=1536
)

# Response structure:
# {
#   "object": "list",
#   "data": [
#     {
#       "object": "embedding",
#       "embedding": [0.023, -0.156, ...],  # 1536 floats
#       "index": 0
#     },
#     ...
#   ],
#   "model": "text-embedding-3-small",
#   "usage": {
#     "prompt_tokens": 8,
#     "total_tokens": 8
#   }
# }
```

---

## Batch Processing

### Why Batch Processing?

1. **API Efficiency**: Single API call for multiple texts
2. **Cost Savings**: Reduced overhead per text
3. **Rate Limit Management**: Better utilization of rate limits
4. **Memory Management**: Process large datasets in chunks

### Batch Size Selection

The optimal batch size depends on several factors:

```python
# Small batches (10-50): Better for real-time processing
EMBEDDING_BATCH_SIZE=25

# Medium batches (50-200): Good balance for most use cases
EMBEDDING_BATCH_SIZE=100  # Default

# Large batches (200-2048): Maximum throughput for bulk processing
EMBEDDING_BATCH_SIZE=500
```

**Considerations**:

| Batch Size | Pros | Cons | Use Case |
|------------|------|------|----------|
| 10-50 | Low latency, quick feedback | Higher API overhead | Real-time embedding |
| 100-200 | Balanced performance | - | General purpose (recommended) |
| 500-2048 | Maximum throughput | High latency, memory usage | Batch jobs, migrations |

### Batch Processing Example

```python
from shared.embedding import EmbeddingService

service = EmbeddingService()

# Large list of texts to embed
memories = [
    "User loves Python programming",
    "User enjoys hiking on weekends",
    # ... 1000 more memories
]

# Process in batches of 100 (default)
results = service.generate_embeddings_batch(memories)

# Process results
total_embeddings = 0
failed_batches = 0

for i, result in enumerate(results):
    if result.success:
        total_embeddings += result.count
        print(f"Batch {i+1}: {result.count} embeddings")
    else:
        failed_batches += 1
        print(f"Batch {i+1} failed: {result.error}")

print(f"\nTotal: {total_embeddings}/{len(memories)} embeddings")
print(f"Failed batches: {failed_batches}/{len(results)}")
```

### Custom Batch Size

```python
# Override default batch size for specific operation
results = service.generate_embeddings_batch(
    texts=large_text_list,
    batch_size=50  # Process 50 at a time
)
```

### Memory-Efficient Batch Processing

For very large datasets, process batches iteratively:

```python
def embed_large_dataset(texts: list[str], service: EmbeddingService):
    """
    Embed large dataset with progress tracking and memory efficiency.
    """
    batch_size = 100
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = service.generate_embeddings(batch)

        if result.success:
            all_embeddings.extend(result.embeddings)
            print(f"Progress: {len(all_embeddings)}/{len(texts)}")
        else:
            print(f"Batch {i//batch_size + 1} failed: {result.error}")
            # Decide: continue or abort?

    return all_embeddings
```

---

## Usage Examples

### Basic Usage

```python
from shared.embedding import EmbeddingService

# Initialize service
with EmbeddingService() as service:
    # Single text
    result = service.generate_embedding("User likes coffee")

    if result.success:
        embedding = result.embeddings[0]
        print(f"Generated {len(embedding)}-dimensional vector")
    else:
        print(f"Error: {result.error}")
```

### Memory Worker Integration

Real-world example from the memory generation worker:

```python
from shared.embedding import EmbeddingService
from shared.extraction import ExtractionEngine

class MemoryGenerationProcessor:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.extraction_engine = ExtractionEngine()

    async def process_session(self, session_id: str, events: list):
        # Extract memories from conversation
        extraction_result = self.extraction_engine.extract_memories(
            conversation_events=events,
            min_confidence=0.5
        )

        if not extraction_result.success:
            return {"error": extraction_result.error}

        # Generate embeddings for extracted memories
        memory_texts = [mem["fact"] for mem in extraction_result.memories]
        embedding_result = self.embedding_service.generate_embeddings(memory_texts)

        if not embedding_result.success:
            return {"error": embedding_result.error}

        # Store memories with embeddings
        for i, memory in enumerate(extraction_result.memories):
            embedding = embedding_result.embeddings[i]
            await self.save_memory(
                fact=memory["fact"],
                embedding=embedding,
                confidence=memory["confidence"]
            )

        return {
            "memories_extracted": extraction_result.memory_count,
            "embeddings_generated": embedding_result.count
        }
```

### Consolidation Worker Integration

Example from the consolidation worker:

```python
from shared.embedding import EmbeddingService
from shared.consolidation import ConsolidationEngine

class ConsolidationProcessor:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.consolidation_engine = ConsolidationEngine()

    async def consolidate_memories(self, memories: list):
        # Run consolidation to merge similar memories
        result = self.consolidation_engine.consolidate_memories(memories)

        if not result.success:
            return {"error": result.error}

        # Generate embeddings for merged memories
        merged_facts = [m.fact for m in result.merged_memories]
        embedding_result = self.embedding_service.generate_embeddings(merged_facts)

        if not embedding_result.success:
            return {"error": embedding_result.error}

        # Update database with consolidated memories
        for i, merged_memory in enumerate(result.merged_memories):
            embedding = embedding_result.embeddings[i]
            await self.update_memory(
                memory_id=merged_memory.id,
                fact=merged_memory.fact,
                embedding=embedding
            )

        return {
            "memories_merged": result.merge_count,
            "embeddings_generated": embedding_result.count
        }
```

### Testing with Mock Service

Example of testing with mocked embeddings:

```python
import pytest
from unittest.mock import MagicMock
from shared.embedding import EmbeddingService, EmbeddingResult

@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service for testing."""
    service = EmbeddingService()

    # Mock the generate_embeddings method
    def mock_generate(texts):
        # Return fake embeddings
        return EmbeddingResult(
            embeddings=[[0.1] * 1536 for _ in texts],
            texts=texts,
            model="text-embedding-3-small",
            dimensions=1536
        )

    service.generate_embeddings = mock_generate
    return service

def test_memory_processing(mock_embedding_service):
    """Test memory processing with mocked embeddings."""
    memories = ["User likes coffee", "User prefers tea"]
    result = mock_embedding_service.generate_embeddings(memories)

    assert result.success
    assert result.count == 2
    assert len(result.embeddings[0]) == 1536
```

### Custom Configuration

```python
from shared.embedding.config import EmbeddingSettings
from shared.embedding import EmbeddingService

# Create service with custom settings
custom_settings = EmbeddingSettings(
    openai_api_key="your-api-key",
    openai_embedding_model="text-embedding-3-large",  # Higher quality
    openai_embedding_dimensions=3072,  # Maximum dimensions
    openai_timeout=120,  # Longer timeout
    embedding_batch_size=50  # Smaller batches
)

service = EmbeddingService(settings=custom_settings)

# Use custom service
result = service.generate_embedding("Important memory")
```

### Error Handling Pattern

```python
from shared.embedding import EmbeddingService

service = EmbeddingService()

def safe_embed(texts: list[str]) -> tuple[list[list[float]], str | None]:
    """
    Safely generate embeddings with error handling.

    Returns:
        Tuple of (embeddings, error_message)
    """
    try:
        result = service.generate_embeddings(texts)

        if result.success:
            return result.embeddings, None
        else:
            return [], result.error

    except Exception as e:
        return [], f"Unexpected error: {str(e)}"

# Usage
embeddings, error = safe_embed(["text1", "text2"])

if error:
    print(f"Failed to generate embeddings: {error}")
else:
    print(f"Successfully generated {len(embeddings)} embeddings")
```

---

## Performance Optimization

### 1. Batch Size Tuning

Benchmark different batch sizes for your workload:

```python
import time
from shared.embedding import EmbeddingService

def benchmark_batch_size(texts: list[str], batch_sizes: list[int]):
    """Benchmark different batch sizes."""
    service = EmbeddingService()
    results = {}

    for batch_size in batch_sizes:
        start = time.time()
        batch_results = service.generate_embeddings_batch(
            texts=texts,
            batch_size=batch_size
        )
        elapsed = time.time() - start

        total_embeddings = sum(r.count for r in batch_results if r.success)
        results[batch_size] = {
            "time": elapsed,
            "embeddings": total_embeddings,
            "rate": total_embeddings / elapsed if elapsed > 0 else 0
        }

    return results

# Test with 1000 texts
texts = [f"Memory {i}" for i in range(1000)]
results = benchmark_batch_size(texts, [25, 50, 100, 200, 500])

for batch_size, metrics in results.items():
    print(f"Batch size {batch_size}: {metrics['rate']:.1f} embeddings/sec")
```

### 2. Connection Reuse

Reuse the service instance to avoid connection overhead:

```python
# Bad: Creates new client for each request
def process_memories_bad(memories: list[str]):
    for memory in memories:
        service = EmbeddingService()  # New connection each time!
        result = service.generate_embedding(memory)
        service.close()

# Good: Reuse service instance
def process_memories_good(memories: list[str]):
    service = EmbeddingService()  # Single connection
    for memory in memories:
        result = service.generate_embedding(memory)
    service.close()

# Better: Use context manager
def process_memories_better(memories: list[str]):
    with EmbeddingService() as service:
        for memory in memories:
            result = service.generate_embedding(memory)
```

### 3. Parallel Processing

For very large datasets, consider parallel processing:

```python
from concurrent.futures import ThreadPoolExecutor
from shared.embedding import EmbeddingService

def parallel_embed(texts: list[str], max_workers: int = 4):
    """
    Generate embeddings in parallel using multiple workers.

    Note: Each worker creates its own service instance.
    """
    chunk_size = len(texts) // max_workers
    chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]

    def process_chunk(chunk: list[str]):
        with EmbeddingService() as service:
            return service.generate_embeddings(chunk)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_chunk, chunks))

    # Combine results
    all_embeddings = []
    for result in results:
        if result.success:
            all_embeddings.extend(result.embeddings)

    return all_embeddings
```

### 4. Dimension Reduction

Use lower dimensions for faster similarity search:

```python
# High quality, slower search
OPENAI_EMBEDDING_DIMENSIONS=1536  # Default

# Faster search, minimal quality loss
OPENAI_EMBEDDING_DIMENSIONS=512

# Very fast search, some quality loss
OPENAI_EMBEDDING_DIMENSIONS=256
```

### 5. Caching Strategy

Implement caching for frequently embedded texts:

```python
from functools import lru_cache
from shared.embedding import EmbeddingService

class CachedEmbeddingService:
    """Embedding service with LRU cache."""

    def __init__(self, cache_size: int = 1000):
        self.service = EmbeddingService()
        self._cache = {}
        self._cache_size = cache_size

    def generate_embedding_cached(self, text: str) -> list[float]:
        """Generate embedding with caching."""
        if text in self._cache:
            return self._cache[text]

        result = self.service.generate_embedding(text)
        if result.success:
            embedding = result.embeddings[0]

            # Maintain cache size
            if len(self._cache) >= self._cache_size:
                # Remove oldest entry (simple FIFO)
                oldest = next(iter(self._cache))
                del self._cache[oldest]

            self._cache[text] = embedding
            return embedding

        return []

# Usage
cached_service = CachedEmbeddingService(cache_size=1000)

# First call: API request
embedding1 = cached_service.generate_embedding_cached("User likes coffee")

# Second call: Retrieved from cache (instant)
embedding2 = cached_service.generate_embedding_cached("User likes coffee")

assert embedding1 == embedding2  # Same embedding
```

---

## Cost Optimization

### Pricing Model

OpenAI charges for embeddings based on input tokens:

```
Model: text-embedding-3-small
Price: $0.02 per 1 million tokens

Model: text-embedding-3-large (alternative)
Price: $0.13 per 1 million tokens
```

### Cost Calculation

```python
# Average tokens per text (rough estimate: 1 token ≈ 4 characters)
avg_chars_per_text = 200
avg_tokens_per_text = avg_chars_per_text / 4  # ~50 tokens

# Number of texts to embed
num_texts = 10000

# Total tokens
total_tokens = num_texts * avg_tokens_per_text  # 500,000 tokens

# Cost calculation
cost_per_million = 0.02  # text-embedding-3-small
cost = (total_tokens / 1_000_000) * cost_per_million

print(f"Estimated cost: ${cost:.4f}")  # $0.0100
```

### Cost Optimization Strategies

#### 1. Avoid Re-embedding Unchanged Content

```python
class SmartEmbeddingService:
    """Only embed text if it has changed."""

    def __init__(self):
        self.service = EmbeddingService()
        self.text_hashes = {}  # Track text hashes

    async def embed_if_changed(
        self,
        memory_id: str,
        text: str,
        existing_embedding: list[float] | None
    ) -> list[float] | None:
        """Only generate new embedding if text changed."""
        import hashlib

        # Hash the text
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Check if text changed
        if existing_embedding and self.text_hashes.get(memory_id) == text_hash:
            return existing_embedding  # Reuse existing embedding

        # Generate new embedding
        result = self.service.generate_embedding(text)
        if result.success:
            self.text_hashes[memory_id] = text_hash
            return result.embeddings[0]

        return None
```

#### 2. Batch Aggressively

```python
# Expensive: 1000 API calls
for text in texts:
    service.generate_embedding(text)  # 1000 calls × overhead

# Cheap: 10 API calls (100× fewer calls)
service.generate_embeddings_batch(texts, batch_size=100)  # 10 calls total
```

#### 3. Use Appropriate Dimensions

```python
# More expensive: Larger payloads, more processing
OPENAI_EMBEDDING_DIMENSIONS=3072  # 2× the data

# More economical: Smaller payloads
OPENAI_EMBEDDING_DIMENSIONS=1536  # Default, good balance

# Most economical: Minimum viable dimensions
OPENAI_EMBEDDING_DIMENSIONS=512   # 1/3 the data
```

#### 4. Deduplicate Before Embedding

```python
def embed_unique_texts(texts: list[str], service: EmbeddingService):
    """Only embed unique texts to avoid duplicate API calls."""
    # Find unique texts
    unique_texts = list(set(texts))

    # Generate embeddings for unique texts only
    result = service.generate_embeddings(unique_texts)

    if not result.success:
        return None

    # Create mapping
    embedding_map = dict(zip(unique_texts, result.embeddings))

    # Map back to original order
    embeddings = [embedding_map[text] for text in texts]

    return embeddings

# Example: 1000 texts with only 500 unique
texts = ["text1", "text2", "text1", "text3", "text2", ...]  # 1000 items
embeddings = embed_unique_texts(texts, service)  # Only 500 API calls!
```

#### 5. Monitor Usage

Track embedding API usage:

```python
class MeteredEmbeddingService:
    """Track embedding API usage for cost monitoring."""

    def __init__(self):
        self.service = EmbeddingService()
        self.total_tokens = 0
        self.total_requests = 0

    def generate_embeddings(self, texts: list[str]):
        """Generate embeddings with usage tracking."""
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = sum(len(text) // 4 for text in texts)

        result = self.service.generate_embeddings(texts)

        if result.success:
            self.total_tokens += estimated_tokens
            self.total_requests += 1

        return result

    def get_estimated_cost(self) -> float:
        """Calculate estimated cost in USD."""
        cost_per_million = 0.02  # text-embedding-3-small
        return (self.total_tokens / 1_000_000) * cost_per_million

    def print_usage_stats(self):
        """Print usage statistics."""
        print(f"Total API requests: {self.total_requests}")
        print(f"Total tokens: {self.total_tokens:,}")
        print(f"Estimated cost: ${self.get_estimated_cost():.4f}")

# Usage
metered_service = MeteredEmbeddingService()

# Use throughout application
metered_service.generate_embeddings(["text1", "text2"])
metered_service.generate_embeddings(["text3", "text4"])

# Check costs
metered_service.print_usage_stats()
# Output:
# Total API requests: 2
# Total tokens: 8
# Estimated cost: $0.0000
```

### Cost Monitoring Dashboard

```python
def monthly_embedding_cost_estimate(
    memories_per_day: int,
    avg_memory_length: int = 200
) -> dict:
    """
    Estimate monthly embedding costs.

    Args:
        memories_per_day: Average memories generated per day
        avg_memory_length: Average character length of memories

    Returns:
        Cost breakdown dictionary
    """
    # Calculate tokens
    avg_tokens_per_memory = avg_memory_length / 4
    daily_tokens = memories_per_day * avg_tokens_per_memory
    monthly_tokens = daily_tokens * 30

    # Calculate cost
    cost_per_million = 0.02
    monthly_cost = (monthly_tokens / 1_000_000) * cost_per_million

    return {
        "memories_per_day": memories_per_day,
        "avg_memory_length": avg_memory_length,
        "daily_tokens": daily_tokens,
        "monthly_tokens": monthly_tokens,
        "monthly_cost_usd": monthly_cost
    }

# Example: 1000 memories/day, 200 chars each
estimate = monthly_embedding_cost_estimate(
    memories_per_day=1000,
    avg_memory_length=200
)

print(f"Monthly cost: ${estimate['monthly_cost_usd']:.2f}")
# Output: Monthly cost: $0.30
```

---

## Error Handling

### Error Types

The embedding service handles several types of errors:

#### 1. Configuration Errors

```python
from shared.embedding import EmbeddingService

# Missing API key
service = EmbeddingService()
try:
    result = service.generate_embedding("test")
except ValueError as e:
    print(f"Configuration error: {e}")
    # Output: Configuration error: OpenAI API key not configured
```

#### 2. API Errors

```python
result = service.generate_embeddings(["test"])

if not result.success:
    print(f"API error: {result.error}")
    # Examples:
    # - "OpenAI API error: Rate limit exceeded"
    # - "OpenAI API error: Invalid API key"
    # - "OpenAI API error: Model not found"
```

#### 3. Network Errors

```python
# Network timeout or connection issues
result = service.generate_embeddings(["test"])

if not result.success:
    # Error message will contain details:
    # "OpenAI API error: Connection timeout after 60 seconds"
```

#### 4. Validation Errors

```python
# Empty input
try:
    result = service.generate_embeddings([])
except ValueError as e:
    print(f"Validation error: {e}")
    # Output: Validation error: texts cannot be empty
```

### Retry Logic

The service implements automatic retry with exponential backoff:

```python
# Configured via settings
settings = EmbeddingSettings(
    openai_api_key="your-key",
    openai_max_retries=3,  # Retry up to 3 times
    openai_timeout=60      # 60 second timeout per attempt
)

service = EmbeddingService(settings=settings)

# Retry sequence for transient failures:
# 1. Initial attempt
# 2. Wait ~1 second, retry
# 3. Wait ~2 seconds, retry
# 4. Wait ~4 seconds, retry
# 5. Give up, return error
```

### Error Handling Best Practices

#### 1. Always Check Success

```python
result = service.generate_embeddings(texts)

if result.success:
    # Process embeddings
    process_embeddings(result.embeddings)
else:
    # Handle error
    logger.error(f"Embedding failed: {result.error}")
    # Decide: retry, skip, or fail?
```

#### 2. Graceful Degradation

```python
async def generate_memory_with_fallback(
    fact: str,
    service: EmbeddingService
) -> dict:
    """Generate memory with fallback to no embedding."""
    result = service.generate_embedding(fact)

    if result.success:
        return {
            "fact": fact,
            "embedding": result.embeddings[0],
            "has_embedding": True
        }
    else:
        # Still save memory without embedding
        logger.warning(f"Embedding failed: {result.error}")
        return {
            "fact": fact,
            "embedding": None,
            "has_embedding": False
        }
```

#### 3. Batch Error Handling

```python
def process_batch_results(results: list[EmbeddingResult]):
    """Process batch results with partial failure handling."""
    all_embeddings = []
    failed_batches = []

    for i, result in enumerate(results):
        if result.success:
            all_embeddings.extend(result.embeddings)
        else:
            logger.error(f"Batch {i} failed: {result.error}")
            failed_batches.append(i)

    if failed_batches:
        logger.warning(
            f"{len(failed_batches)}/{len(results)} batches failed"
        )

    return all_embeddings, failed_batches
```

#### 4. Circuit Breaker Pattern

```python
class CircuitBreakerEmbeddingService:
    """Embedding service with circuit breaker for repeated failures."""

    def __init__(self, failure_threshold: int = 5):
        self.service = EmbeddingService()
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.circuit_open = False

    def generate_embeddings(self, texts: list[str]):
        """Generate embeddings with circuit breaker."""
        if self.circuit_open:
            return EmbeddingResult(
                embeddings=[],
                texts=texts,
                model="text-embedding-3-small",
                dimensions=1536,
                error="Circuit breaker open due to repeated failures"
            )

        result = self.service.generate_embeddings(texts)

        if result.success:
            # Reset failure count on success
            self.failure_count = 0
        else:
            # Increment failure count
            self.failure_count += 1

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

        return result

    def reset_circuit(self):
        """Manually reset circuit breaker."""
        self.circuit_open = False
        self.failure_count = 0
```

---

## Testing

### Unit Tests

Example unit tests for embedding service:

```python
import pytest
from unittest.mock import MagicMock, patch
from shared.embedding import EmbeddingService, EmbeddingResult
from shared.embedding.config import EmbeddingSettings

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return EmbeddingSettings(
        openai_api_key="test-key",
        openai_embedding_model="text-embedding-3-small",
        openai_embedding_dimensions=1536,
        openai_timeout=60,
        openai_max_retries=3,
        embedding_batch_size=100
    )

@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3] * 512),  # 1536 values
        MagicMock(embedding=[0.4, 0.5, 0.6] * 512)
    ]
    mock_response.model = "text-embedding-3-small"
    return mock_response

def test_generate_single_embedding(mock_settings, mock_openai_response):
    """Test generating single embedding."""
    service = EmbeddingService(settings=mock_settings)

    # Mock OpenAI client
    service._client = MagicMock()
    service._client.embeddings.create.return_value = mock_openai_response

    # Generate embedding
    result = service.generate_embedding("test text")

    # Assertions
    assert result.success
    assert result.count == 2  # Mock returns 2 embeddings
    assert len(result.embeddings[0]) == 1536
    assert result.model == "text-embedding-3-small"

def test_generate_embeddings_batch(mock_settings):
    """Test batch embedding generation."""
    service = EmbeddingService(settings=mock_settings)

    # Mock successful responses
    def mock_generate(texts):
        return EmbeddingResult(
            embeddings=[[0.1] * 1536 for _ in texts],
            texts=texts,
            model="text-embedding-3-small",
            dimensions=1536
        )

    service.generate_embeddings = mock_generate

    # Generate batch
    texts = [f"text {i}" for i in range(250)]  # 250 texts
    results = service.generate_embeddings_batch(texts, batch_size=100)

    # Should create 3 batches (100, 100, 50)
    assert len(results) == 3
    assert all(r.success for r in results)

def test_error_handling(mock_settings):
    """Test error handling for API failures."""
    service = EmbeddingService(settings=mock_settings)

    # Mock OpenAI client to raise error
    service._client = MagicMock()
    service._client.embeddings.create.side_effect = Exception("API Error")

    # Generate embedding
    result = service.generate_embeddings(["test"])

    # Should return error result
    assert not result.success
    assert "Embedding generation failed" in result.error
    assert len(result.embeddings) == 0
```

### Integration Tests

Test with actual OpenAI API:

```python
import pytest
from shared.embedding import EmbeddingService

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY"
)
def test_real_embedding_generation():
    """Test embedding generation with real OpenAI API."""
    service = EmbeddingService()

    # Generate embedding
    result = service.generate_embedding("This is a test")

    # Assertions
    assert result.success
    assert result.count == 1
    assert len(result.embeddings[0]) == 1536
    assert result.model == "text-embedding-3-small"

    # Test vector properties
    embedding = result.embeddings[0]
    assert all(isinstance(v, float) for v in embedding)
    assert -1 <= max(embedding) <= 1  # Values typically in [-1, 1]
    assert -1 <= min(embedding) <= 1
```

### Mock Service for Tests

Create reusable mock service:

```python
# tests/fixtures/embedding.py
import pytest
from shared.embedding import EmbeddingService, EmbeddingResult

@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service that returns fake embeddings."""
    service = EmbeddingService()

    original_generate = service.generate_embeddings

    def mock_generate_embeddings(texts: list[str]):
        """Return fake but valid embeddings."""
        return EmbeddingResult(
            embeddings=[[0.1] * 1536 for _ in texts],
            texts=texts,
            model="text-embedding-3-small",
            dimensions=1536
        )

    service.generate_embeddings = mock_generate_embeddings
    service.generate_embedding = lambda text: mock_generate_embeddings([text])

    return service

# Use in tests
def test_with_mock_service(mock_embedding_service):
    """Test using mock embedding service."""
    result = mock_embedding_service.generate_embedding("test")
    assert result.success
    assert len(result.embeddings[0]) == 1536
```

---

## Alternative Models

### Switching to text-embedding-3-large

For higher quality embeddings:

```bash
# .env
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_DIMENSIONS=3072  # Maximum for this model
```

**Comparison**:

| Model | Dimensions | MTEB Score | Cost (per 1M tokens) |
|-------|------------|------------|---------------------|
| text-embedding-3-small | 1536 | 62.3% | $0.02 |
| text-embedding-3-large | 3072 | 64.6% | $0.13 |

**When to use text-embedding-3-large**:
- Highest quality required
- Complex semantic understanding needed
- Budget allows for 6.5× higher costs
- Processing smaller datasets

### Using ada-002 (Legacy)

For backwards compatibility:

```bash
# .env
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
OPENAI_EMBEDDING_DIMENSIONS=1536  # Fixed dimension
```

**Note**: ada-002 is 5× more expensive than text-embedding-3-small and lower quality. Only use if required for compatibility.

### Other OpenAI Models

OpenAI supports other embedding models (future):

```bash
# Check available models
import openai
client = openai.Client()
models = client.models.list()

for model in models:
    if "embedding" in model.id:
        print(model.id)
```

### Non-OpenAI Alternatives

To use alternative embedding providers, extend the EmbeddingService:

```python
from shared.embedding.service import EmbeddingService, EmbeddingResult

class HuggingFaceEmbeddingService(EmbeddingService):
    """Embedding service using HuggingFace models."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def generate_embeddings(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings using HuggingFace model."""
        try:
            embeddings = self.model.encode(texts)

            return EmbeddingResult(
                embeddings=embeddings.tolist(),
                texts=texts,
                model=self.model_name,
                dimensions=len(embeddings[0])
            )
        except Exception as e:
            return EmbeddingResult(
                embeddings=[],
                texts=texts,
                model=self.model_name,
                dimensions=0,
                error=str(e)
            )
```

**Popular alternatives**:
- **Sentence Transformers**: Free, local, fast
- **Cohere**: Commercial, good quality
- **Voyage AI**: Optimized for retrieval
- **Azure OpenAI**: Enterprise OpenAI

---

## Troubleshooting

### Common Issues

#### Issue 1: API Key Not Found

**Error**:
```
ValueError: OpenAI API key not configured
```

**Solution**:
```bash
# Check .env file
cat .env | grep OPENAI_API_KEY

# Set environment variable
export OPENAI_API_KEY=sk-proj-...

# Or update .env
echo "OPENAI_API_KEY=sk-proj-..." >> .env
```

#### Issue 2: Rate Limit Exceeded

**Error**:
```
OpenAI API error: Rate limit exceeded
```

**Solutions**:
1. Reduce batch size:
```bash
EMBEDDING_BATCH_SIZE=50  # Smaller batches
```

2. Add delays between batches:
```python
import time

for batch in batches:
    result = service.generate_embeddings(batch)
    time.sleep(1)  # 1 second delay
```

3. Upgrade OpenAI plan for higher limits

#### Issue 3: Timeout Errors

**Error**:
```
OpenAI API error: Connection timeout after 60 seconds
```

**Solutions**:
1. Increase timeout:
```bash
OPENAI_TIMEOUT=120  # 2 minutes
```

2. Reduce batch size:
```bash
EMBEDDING_BATCH_SIZE=50  # Smaller batches
```

3. Check network connectivity

#### Issue 4: Invalid Dimensions

**Error**:
```
validation error for EmbeddingSettings
openai_embedding_dimensions
  Input should be greater than or equal to 256
```

**Solution**:
```bash
# Use valid dimension range: 256-3072
OPENAI_EMBEDDING_DIMENSIONS=1536
```

#### Issue 5: Memory Issues with Large Batches

**Error**:
```
MemoryError: Unable to allocate array
```

**Solutions**:
1. Reduce batch size:
```bash
EMBEDDING_BATCH_SIZE=100  # Smaller batches
```

2. Process incrementally:
```python
# Don't load all embeddings at once
for batch in service.generate_embeddings_batch(texts):
    process_batch(batch)  # Process immediately
    # Don't accumulate in memory
```

### Debugging

Enable debug logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable OpenAI debug logs
logging.getLogger("openai").setLevel(logging.DEBUG)

# Now generate embeddings with full logging
from shared.embedding import EmbeddingService

service = EmbeddingService()
result = service.generate_embeddings(["test"])
```

### Health Check

Test embedding service health:

```python
from shared.embedding import EmbeddingService

def check_embedding_health() -> dict:
    """
    Check embedding service health.

    Returns:
        Health status dictionary
    """
    try:
        service = EmbeddingService()

        # Test with simple text
        result = service.generate_embedding("health check")

        if result.success:
            return {
                "status": "healthy",
                "model": result.model,
                "dimensions": result.dimensions
            }
        else:
            return {
                "status": "unhealthy",
                "error": result.error
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Run health check
health = check_embedding_health()
print(health)
```

---

## Best Practices

### 1. Use Context Managers

Always use context managers to ensure proper cleanup:

```python
# Good
with EmbeddingService() as service:
    result = service.generate_embeddings(texts)
    # Client automatically closed

# Also good
service = EmbeddingService()
try:
    result = service.generate_embeddings(texts)
finally:
    service.close()
```

### 2. Batch When Possible

Batch operations are more efficient:

```python
# Bad: 100 API calls
for text in texts:
    service.generate_embedding(text)

# Good: 1 API call
service.generate_embeddings(texts)

# Better: Controlled batching
service.generate_embeddings_batch(texts, batch_size=100)
```

### 3. Check Success Before Using Results

Always verify operations succeeded:

```python
result = service.generate_embeddings(texts)

# Good
if result.success:
    embeddings = result.embeddings
else:
    logger.error(f"Failed: {result.error}")
    # Handle error appropriately

# Bad - might crash
embeddings = result.embeddings  # Could be empty!
```

### 4. Use Appropriate Error Handling

Different contexts require different error strategies:

```python
# Critical path: Fail fast
result = service.generate_embeddings(texts)
if not result.success:
    raise RuntimeError(f"Embedding failed: {result.error}")

# Background job: Log and continue
result = service.generate_embeddings(texts)
if not result.success:
    logger.warning(f"Embedding failed: {result.error}")
    # Continue with partial results

# User-facing: Graceful degradation
result = service.generate_embeddings(texts)
if not result.success:
    return {"status": "partial", "error": result.error}
```

### 5. Monitor Performance and Costs

Track metrics:

```python
import time

start = time.time()
result = service.generate_embeddings(texts)
elapsed = time.time() - start

logger.info(
    f"Generated {result.count} embeddings in {elapsed:.2f}s "
    f"({result.count/elapsed:.1f} embeddings/sec)"
)
```

### 6. Validate Input

Validate inputs before API calls:

```python
def validate_texts(texts: list[str]) -> tuple[bool, str | None]:
    """Validate text inputs for embedding."""
    if not texts:
        return False, "Empty text list"

    if any(not isinstance(t, str) for t in texts):
        return False, "All texts must be strings"

    if any(len(t) == 0 for t in texts):
        return False, "Empty strings not allowed"

    return True, None

# Use validation
valid, error = validate_texts(texts)
if not valid:
    logger.error(f"Invalid input: {error}")
else:
    result = service.generate_embeddings(texts)
```

### 7. Use Configuration Wisely

Don't hardcode settings:

```python
# Bad
service = EmbeddingService()
service.settings.openai_embedding_dimensions = 512  # Don't modify!

# Good
from shared.embedding.config import EmbeddingSettings

settings = EmbeddingSettings(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_embedding_dimensions=512
)
service = EmbeddingService(settings=settings)
```

### 8. Leverage Existing Infrastructure

Integrate with the application's patterns:

```python
# Use dependency injection
class MemoryProcessor:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    async def process(self, memories: list[str]):
        result = self.embedding_service.generate_embeddings(memories)
        return result

# Initialize in worker/service
from shared.embedding import EmbeddingService

embedding_service = EmbeddingService()
processor = MemoryProcessor(embedding_service=embedding_service)
```

---

## See Also

- [Vector Search Guide](./VECTOR_SEARCH.md) - Using embeddings for similarity search
- [Architecture Overview](./ARCHITECTURE.md) - System architecture and design
- [API Documentation](./API_USAGE.md) - REST API reference

---

**Last Updated**: 2025-12-11
**ContextIQ Version**: 0.1.0
