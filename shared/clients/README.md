# HTTP Service Clients

This module provides HTTP clients for inter-service communication in the ContextIQ system.

## Overview

The service clients enable workers and other services to communicate with the Sessions Service and Memory Service over HTTP. They include built-in retry logic, timeout handling, and type-safe request/response models.

## Components

### Base Client (`base.py`)

The `BaseHTTPClient` provides common HTTP functionality:
- Automatic retry logic with exponential backoff
- Timeout handling
- Connection pooling
- Error handling for 4xx (no retry) and 5xx (retry) errors

### Sessions Client (`sessions_client.py`)

Provides methods to interact with the Sessions Service:

```python
from shared.clients import SessionsServiceClient

async with SessionsServiceClient() as client:
    # Create a session
    session = await client.create_session(
        scope={"user_id": "123"},
        title="Test Session"
    )

    # Add events to the session
    event = await client.create_event(
        session_id=session.id,
        event_type="message",
        data={"content": "Hello"},
        input_tokens=10
    )

    # List all events
    events = await client.list_events(session.id)
```

### Memory Client (`memory_client.py`)

Provides methods to interact with the Memory Service:

```python
from shared.clients import MemoryServiceClient

async with MemoryServiceClient() as client:
    # Create a memory
    memory = await client.create_memory(
        scope={"user_id": "123"},
        fact="User prefers Python",
        source_type="extracted",
        topic="preferences"
    )

    # List memories by scope
    memories = await client.list_memories(
        scope_user_id="123",
        topic="preferences"
    )

    # Update a memory
    updated = await client.update_memory(
        memory_id=memory.id,
        fact="User prefers Python and TypeScript",
        change_reason="User provided additional information"
    )
```

## Configuration

Clients can be configured via environment variables:

```bash
# Sessions Service
SESSIONS_SERVICE_URL=http://localhost:8001
SESSIONS_SERVICE_TIMEOUT=30
SESSIONS_SERVICE_MAX_RETRIES=3
SESSIONS_SERVICE_RETRY_DELAY=1.0

# Memory Service
MEMORY_SERVICE_URL=http://localhost:8002
MEMORY_SERVICE_TIMEOUT=30
MEMORY_SERVICE_MAX_RETRIES=3
MEMORY_SERVICE_RETRY_DELAY=1.0
```

Or by passing parameters directly:

```python
client = SessionsServiceClient(
    base_url="http://custom-host:8001",
    timeout=60,
    max_retries=5
)
```

## Integration with Workers

### Memory Generation Worker

The memory generation worker can use both clients:

```python
from shared.clients import SessionsServiceClient, MemoryServiceClient

class MemoryGenerationProcessor:
    def __init__(
        self,
        extraction_engine,
        embedding_service,
        vector_store,
        sessions_client: SessionsServiceClient,
        memory_client: MemoryServiceClient,
    ):
        self.sessions_client = sessions_client
        self.memory_client = memory_client
        # ...

    async def process_request(self, request):
        # Fetch conversation events from Sessions Service
        events = await self.sessions_client.list_events(
            session_id=request.session_id
        )

        # Extract memories from events
        # ... (extraction logic)

        # Save memories to Memory Service
        for memory_data in extracted_memories:
            await self.memory_client.create_memory(
                scope={"user_id": request.user_id},
                fact=memory_data["fact"],
                source_type="extracted",
                source_id=str(request.session_id),
                **memory_data
            )
```

### Consolidation Worker

The consolidation worker primarily uses the Memory Service client:

```python
from shared.clients import MemoryServiceClient

class ConsolidationProcessor:
    def __init__(self, memory_client: MemoryServiceClient):
        self.memory_client = memory_client

    async def process_consolidation(self, scope, memory_ids):
        # Fetch memories to consolidate
        memories = []
        for memory_id in memory_ids:
            memory = await self.memory_client.get_memory(memory_id)
            memories.append(memory)

        # Consolidate logic...
        # Update or create consolidated memories
        await self.memory_client.create_memory(
            scope=scope,
            fact=consolidated_fact,
            source_type="consolidated",
            **metadata
        )
```

## Error Handling

Clients raise specific exceptions for different error scenarios:

- `ServiceUnavailableError`: Service is unreachable after retries
- `httpx.HTTPStatusError`: HTTP error response (4xx, 5xx)
- `httpx.TimeoutException`: Request timed out
- `httpx.ConnectError`: Connection failed

```python
from shared.exceptions import ServiceUnavailableError
import httpx

try:
    session = await client.create_session(scope={"user_id": "123"})
except ServiceUnavailableError:
    logger.error("Sessions Service is unavailable")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        logger.error("Session not found")
    elif e.response.status_code >= 500:
        logger.error("Server error")
```

## Testing

All clients have comprehensive unit tests using mocked HTTP responses:

```bash
# Run client tests
pytest tests/unit/shared/clients/

# Run specific client tests
pytest tests/unit/shared/clients/test_sessions_client.py
pytest tests/unit/shared/clients/test_memory_client.py
```

## Future Enhancements

- Circuit breaker pattern for failing services
- Request/response caching
- Metrics and observability hooks
- gRPC support for high-performance communication
