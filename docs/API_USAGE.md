# ContextIQ API Usage Guide

Comprehensive guide for using the ContextIQ REST APIs with code examples and best practices.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Sessions API](#sessions-api)
- [Memory API](#memory-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)
- [Code Examples](#code-examples)

## Getting Started

### Base URL

The API Gateway provides a unified entry point for all services:

```
Development: http://localhost:8000
Production:  https://your-domain.com
```

### API Versioning

All endpoints are versioned with the `/api/v1/` prefix:

```
http://localhost:8000/api/v1/sessions
http://localhost:8000/api/v1/memories
```

### Content Type

All requests and responses use JSON:

```http
Content-Type: application/json
```

### Response Format

Successful responses return the requested data:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "created_at": "2025-12-11T10:30:00Z"
}
```

Error responses follow a consistent format:

```json
{
  "detail": "Session not found",
  "status_code": 404
}
```

## Authentication

ContextIQ supports two authentication methods: JWT tokens and API keys.

### Using JWT Tokens

JWT tokens are used for user authentication.

#### Get a Token

```python
from shared.auth.jwt import JWTHandler
from shared.auth.models import Permission

jwt_handler = JWTHandler(secret_key="your-secret-key")

token = jwt_handler.create_access_token(
    user_id="user_123",
    org_id="org_456",
    email="user@example.com",
    name="John Doe",
    permissions=[
        Permission.SESSION_CREATE,
        Permission.SESSION_READ,
        Permission.MEMORY_READ,
        Permission.MEMORY_CREATE,
    ],
)

print(f"Token: {token}")
```

#### Use Token in Requests

```bash
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8000/api/v1/sessions
```

```python
import httpx

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/sessions",
        headers=headers
    )
```

### Using API Keys

API keys are used for service-to-service and programmatic access.

#### Generate API Key

```python
from shared.auth.api_key import APIKeyHandler, APIKeyInfo
from shared.auth.models import Permission
from datetime import datetime, timedelta

handler = APIKeyHandler()

# Generate new key
api_key = handler.generate_api_key()
print(f"API Key: {api_key}")

# Register with permissions
key_info = APIKeyInfo(
    key_id="key_001",
    user_id="service_account",
    org_id="org_456",
    permissions=[
        Permission.SESSION_READ,
        Permission.MEMORY_READ,
        Permission.MEMORY_CREATE,
    ],
    expires_at=datetime.utcnow() + timedelta(days=90),
    is_active=True,
)

handler.register_api_key(api_key, key_info)
```

#### Use API Key in Requests

```bash
curl -H "X-API-Key: ck_xxxxx" \
  http://localhost:8000/api/v1/sessions
```

```python
headers = {
    "X-API-Key": "ck_xxxxx",
    "Content-Type": "application/json"
}

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/sessions",
        headers=headers
    )
```

### Disabling Authentication (Development)

Set `AUTH_REQUIRE_AUTH=false` in your `.env` file to disable authentication:

```bash
AUTH_REQUIRE_AUTH=false
```

## Sessions API

The Sessions API manages conversation sessions and event tracking.

### Create a Session

Create a new conversation session.

**Endpoint**: `POST /api/v1/sessions`

**Request Body**:
```json
{
  "user_id": "user_123",
  "agent_id": "my_agent",
  "scope": {
    "user_id": "user_123",
    "project": "alpha"
  },
  "metadata": {
    "client": "web_app",
    "version": "1.0.0"
  }
}
```

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "agent_id": "my_agent",
  "scope": {
    "user_id": "user_123",
    "project": "alpha"
  },
  "events": [],
  "state": {},
  "metadata": {
    "client": "web_app",
    "version": "1.0.0"
  },
  "created_at": "2025-12-11T10:30:00Z",
  "updated_at": "2025-12-11T10:30:00Z"
}
```

**Python Example**:
```python
import httpx

async def create_session(user_id: str, agent_id: str, scope: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/sessions",
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "scope": scope,
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

session = await create_session(
    user_id="user_123",
    agent_id="my_agent",
    scope={"user_id": "user_123", "project": "alpha"}
)
print(f"Created session: {session['id']}")
```

### Get a Session

Retrieve a session by ID.

**Endpoint**: `GET /api/v1/sessions/{session_id}`

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "agent_id": "my_agent",
  "scope": {"user_id": "user_123"},
  "events": [...],
  "state": {},
  "created_at": "2025-12-11T10:30:00Z"
}
```

**Python Example**:
```python
async def get_session(session_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

session = await get_session("550e8400-e29b-41d4-a716-446655440000")
```

### Append Event to Session

Add an event to a session.

**Endpoint**: `POST /api/v1/sessions/{session_id}/events`

**Request Body**:
```json
{
  "author": "user",
  "invocation_id": "inv_1",
  "content": {
    "role": "user",
    "parts": [
      {
        "text": "What's the weather today?"
      }
    ]
  }
}
```

**Response** (201 Created):
```json
{
  "id": "event_uuid",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "author": "user",
  "invocation_id": "inv_1",
  "content": {...},
  "timestamp": "2025-12-11T10:31:00Z"
}
```

**Python Example**:
```python
async def append_event(session_id: str, author: str, content: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/v1/sessions/{session_id}/events",
            json={
                "author": author,
                "invocation_id": f"inv_{datetime.now().timestamp()}",
                "content": content
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

event = await append_event(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    author="user",
    content={
        "role": "user",
        "parts": [{"text": "What's the weather today?"}]
    }
)
```

### List Sessions

List sessions with optional filtering.

**Endpoint**: `GET /api/v1/sessions`

**Query Parameters**:
- `user_id` (optional): Filter by user ID
- `agent_id` (optional): Filter by agent ID
- `limit` (optional): Max results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Example**: `GET /api/v1/sessions?user_id=user_123&limit=10`

**Response** (200 OK):
```json
{
  "sessions": [...],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

**Python Example**:
```python
async def list_sessions(user_id: str, limit: int = 100):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/sessions",
            params={"user_id": user_id, "limit": limit},
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

sessions = await list_sessions(user_id="user_123", limit=10)
```

### Update Session State

Update the state of a session.

**Endpoint**: `PATCH /api/v1/sessions/{session_id}/state`

**Request Body**:
```json
{
  "state": {
    "last_topic": "weather",
    "conversation_stage": "gathering_info"
  }
}
```

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "state": {
    "last_topic": "weather",
    "conversation_stage": "gathering_info"
  },
  "updated_at": "2025-12-11T10:32:00Z"
}
```

### Delete Session

Delete a session and all its events.

**Endpoint**: `DELETE /api/v1/sessions/{session_id}`

**Response** (204 No Content)

**Python Example**:
```python
async def delete_session(session_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"http://localhost:8000/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()

await delete_session("550e8400-e29b-41d4-a716-446655440000")
```

## Memory API

The Memory API manages long-term memory generation, storage, and retrieval.

### Generate Memories from Session

Extract memories from a conversation session (asynchronous).

**Endpoint**: `POST /api/v1/memories/generate`

**Request Body**:
```json
{
  "source_type": "session",
  "source_reference": "550e8400-e29b-41d4-a716-446655440000",
  "scope": {
    "user_id": "user_123"
  },
  "config": {
    "wait_for_completion": false,
    "extraction_model": "gpt-4o-mini",
    "topics": ["user_preferences", "facts"]
  }
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "job_uuid",
  "status": "pending",
  "source_type": "session",
  "source_reference": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-12-11T10:35:00Z"
}
```

**Python Example**:
```python
async def generate_memories(session_id: str, scope: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/memories/generate",
            json={
                "source_type": "session",
                "source_reference": session_id,
                "scope": scope,
                "config": {
                    "wait_for_completion": False
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

job = await generate_memories(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    scope={"user_id": "user_123"}
)
print(f"Job ID: {job['job_id']}")
```

### Check Memory Generation Job Status

Check the status of a memory generation job.

**Endpoint**: `GET /api/v1/memories/jobs/{job_id}`

**Response** (200 OK):
```json
{
  "job_id": "job_uuid",
  "status": "completed",
  "result": {
    "memories_created": 5,
    "memories_updated": 2,
    "memories_deleted": 0
  },
  "created_at": "2025-12-11T10:35:00Z",
  "completed_at": "2025-12-11T10:35:03Z"
}
```

### Create Memory Directly

Create a memory without extraction (synchronous).

**Endpoint**: `POST /api/v1/memories`

**Request Body**:
```json
{
  "scope": {
    "user_id": "user_123"
  },
  "fact": "User prefers dark mode",
  "topic": "user_preferences",
  "confidence": 0.95,
  "metadata": {
    "source": "manual_entry"
  }
}
```

**Response** (201 Created):
```json
{
  "id": "memory_uuid",
  "scope": {"user_id": "user_123"},
  "fact": "User prefers dark mode",
  "topic": "user_preferences",
  "confidence": 0.95,
  "metadata": {"source": "manual_entry"},
  "created_at": "2025-12-11T10:40:00Z"
}
```

**Python Example**:
```python
async def create_memory(scope: dict, fact: str, topic: str, confidence: float = 1.0):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/memories",
            json={
                "scope": scope,
                "fact": fact,
                "topic": topic,
                "confidence": confidence
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

memory = await create_memory(
    scope={"user_id": "user_123"},
    fact="User prefers dark mode",
    topic="user_preferences",
    confidence=0.95
)
```

### Search Memories

Search for memories using semantic similarity.

**Endpoint**: `POST /api/v1/memories/search`

**Request Body**:
```json
{
  "scope": {
    "user_id": "user_123"
  },
  "search_query": "What are the user's preferences?",
  "top_k": 5,
  "min_confidence": 0.7
}
```

**Response** (200 OK):
```json
{
  "memories": [
    {
      "id": "memory_uuid",
      "fact": "User prefers dark mode",
      "topic": "user_preferences",
      "confidence": 0.95,
      "similarity": 0.89,
      "created_at": "2025-12-11T10:40:00Z"
    },
    ...
  ],
  "total": 5
}
```

**Python Example**:
```python
async def search_memories(scope: dict, query: str, top_k: int = 5):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/memories/search",
            json={
                "scope": scope,
                "search_query": query,
                "top_k": top_k
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

results = await search_memories(
    scope={"user_id": "user_123"},
    query="What are the user's preferences?",
    top_k=5
)

for memory in results['memories']:
    print(f"- {memory['fact']} (confidence: {memory['confidence']})")
```

### Get Memory by ID

Retrieve a specific memory.

**Endpoint**: `GET /api/v1/memories/{memory_id}`

**Response** (200 OK):
```json
{
  "id": "memory_uuid",
  "scope": {"user_id": "user_123"},
  "fact": "User prefers dark mode",
  "topic": "user_preferences",
  "confidence": 0.95,
  "created_at": "2025-12-11T10:40:00Z"
}
```

### List Memories

List all memories for a scope.

**Endpoint**: `GET /api/v1/memories`

**Query Parameters**:
- `scope` (required): JSON-encoded scope (e.g., `{"user_id":"user_123"}`)
- `topic` (optional): Filter by topic
- `limit` (optional): Max results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Example**: `GET /api/v1/memories?scope={"user_id":"user_123"}&limit=10`

**Response** (200 OK):
```json
{
  "memories": [...],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

### Update Memory

Update an existing memory.

**Endpoint**: `PATCH /api/v1/memories/{memory_id}`

**Request Body**:
```json
{
  "fact": "User strongly prefers dark mode",
  "confidence": 0.98
}
```

**Response** (200 OK):
```json
{
  "id": "memory_uuid",
  "fact": "User strongly prefers dark mode",
  "confidence": 0.98,
  "updated_at": "2025-12-11T10:45:00Z"
}
```

### Delete Memory

Delete a memory.

**Endpoint**: `DELETE /api/v1/memories/{memory_id}`

**Response** (204 No Content)

### Get Memory Revision History

Retrieve the revision history for a memory.

**Endpoint**: `GET /api/v1/memories/{memory_id}/revisions`

**Response** (200 OK):
```json
{
  "revisions": [
    {
      "revision_number": 2,
      "fact": "User strongly prefers dark mode",
      "action": "UPDATED",
      "created_at": "2025-12-11T10:45:00Z"
    },
    {
      "revision_number": 1,
      "fact": "User prefers dark mode",
      "action": "CREATED",
      "created_at": "2025-12-11T10:40:00Z"
    }
  ]
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful GET/PATCH request
- `201 Created`: Successful POST request (resource created)
- `202 Accepted`: Async operation accepted
- `204 No Content`: Successful DELETE request
- `400 Bad Request`: Invalid request body or parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error
- `502 Bad Gateway`: Upstream service error
- `503 Service Unavailable`: Service temporarily unavailable
- `504 Gateway Timeout`: Upstream timeout

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400
}
```

For validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "user_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Python Error Handling

```python
import httpx

async def safe_api_call():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/api/v1/sessions/invalid-id",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print("Session not found")
        elif e.response.status_code == 401:
            print("Authentication required")
        elif e.response.status_code == 403:
            print("Permission denied")
        else:
            print(f"HTTP error: {e.response.status_code}")
            print(f"Response: {e.response.text}")

    except httpx.TimeoutException:
        print("Request timed out")

    except httpx.ConnectError:
        print("Could not connect to service")

    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Rate Limiting

Rate limiting is planned but not yet implemented. When available, rate limits will be:

- **Per API Key**: 1000 requests/minute
- **Per IP** (anonymous): 100 requests/minute
- **Burst Allowance**: 2x sustained rate

Rate limit headers will be included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1639233600
```

When rate limited, you'll receive a 429 response:

```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "status_code": 429
}
```

## Best Practices

### 1. Use Scopes Consistently

Scopes are critical for memory isolation. Always use consistent scope keys:

```python
# Good: Consistent scope structure
scope = {
    "user_id": "user_123",
    "project": "alpha"
}

# Bad: Inconsistent keys across calls
scope1 = {"user": "user_123"}
scope2 = {"user_id": "user_123"}
```

### 2. Handle Async Operations

Memory generation is asynchronous. Poll for job status or use webhooks (when available):

```python
async def wait_for_job(job_id: str, max_wait: int = 30):
    """Poll job status until completion."""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status = await get_job_status(job_id)

        if status['status'] == 'completed':
            return status['result']
        elif status['status'] == 'failed':
            raise Exception(f"Job failed: {status.get('error')}")

        await asyncio.sleep(1)

    raise TimeoutError("Job did not complete in time")
```

### 3. Cache Frequently Accessed Data

Sessions and memories are cached in Redis, but you can also cache on the client side:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class MemoryCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, key: str):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value):
        self.cache[key] = (value, datetime.now())

cache = MemoryCache(ttl_seconds=300)

async def get_session_cached(session_id: str):
    cached = cache.get(session_id)
    if cached:
        return cached

    session = await get_session(session_id)
    cache.set(session_id, session)
    return session
```

### 4. Use Semantic Search Effectively

When searching memories, use natural language queries:

```python
# Good: Natural language query
query = "What programming languages does the user know?"

# Less effective: Keyword search
query = "programming languages"
```

### 5. Set Appropriate Confidence Levels

When creating memories directly, use confidence levels that reflect certainty:

```python
# High confidence: Direct user statement
memory = await create_memory(
    fact="User is located in San Francisco",
    confidence=0.95
)

# Medium confidence: Inferred from context
memory = await create_memory(
    fact="User might prefer email notifications",
    confidence=0.7
)

# Low confidence: Speculation
memory = await create_memory(
    fact="User could be interested in AI",
    confidence=0.5
)
```

### 6. Handle Pagination

When listing resources, use pagination to avoid large responses:

```python
async def get_all_sessions(user_id: str):
    """Fetch all sessions with pagination."""
    all_sessions = []
    offset = 0
    limit = 100

    while True:
        response = await list_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        sessions = response['sessions']
        all_sessions.extend(sessions)

        if len(sessions) < limit:
            break

        offset += limit

    return all_sessions
```

### 7. Use Correlation IDs

For debugging, include correlation IDs in your requests:

```python
import uuid

headers = {
    "Authorization": f"Bearer {token}",
    "X-Correlation-ID": str(uuid.uuid4())
}

response = await client.get(url, headers=headers)
```

### 8. Implement Retries

Implement exponential backoff for transient failures:

```python
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> T:
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise

    raise Exception("Max retries exceeded")

# Usage
session = await retry_with_backoff(
    lambda: get_session(session_id)
)
```

## Code Examples

### Complete Example: Conversation with Memory

```python
import asyncio
import httpx
from typing import List, Dict

class ContextIQClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def create_session(self, user_id: str, agent_id: str, scope: dict):
        response = await self.client.post(
            f"{self.base_url}/api/v1/sessions",
            json={
                "user_id": user_id,
                "agent_id": agent_id,
                "scope": scope
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def add_message(self, session_id: str, author: str, text: str):
        response = await self.client.post(
            f"{self.base_url}/api/v1/sessions/{session_id}/events",
            json={
                "author": author,
                "invocation_id": f"inv_{asyncio.get_event_loop().time()}",
                "content": {
                    "role": author,
                    "parts": [{"text": text}]
                }
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def generate_memories(self, session_id: str, scope: dict):
        response = await self.client.post(
            f"{self.base_url}/api/v1/memories/generate",
            json={
                "source_type": "session",
                "source_reference": session_id,
                "scope": scope,
                "config": {"wait_for_completion": False}
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def search_memories(self, scope: dict, query: str, top_k: int = 5):
        response = await self.client.post(
            f"{self.base_url}/api/v1/memories/search",
            json={
                "scope": scope,
                "search_query": query,
                "top_k": top_k
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


async def main():
    # Initialize client
    client = ContextIQClient(
        base_url="http://localhost:8000",
        token="your-jwt-token"
    )

    try:
        # Create session
        session = await client.create_session(
            user_id="user_123",
            agent_id="assistant",
            scope={"user_id": "user_123", "project": "demo"}
        )
        session_id = session['id']
        print(f"Created session: {session_id}")

        # Have a conversation
        await client.add_message(
            session_id, "user",
            "I love Python programming and use it daily"
        )
        await client.add_message(
            session_id, "agent",
            "That's great! Python is a versatile language."
        )
        await client.add_message(
            session_id, "user",
            "I prefer dark mode in my IDE"
        )

        # Generate memories from conversation
        job = await client.generate_memories(
            session_id,
            scope={"user_id": "user_123"}
        )
        print(f"Memory generation job: {job['job_id']}")

        # Wait a bit for processing
        await asyncio.sleep(5)

        # Search for relevant memories
        results = await client.search_memories(
            scope={"user_id": "user_123"},
            query="What are the user's preferences?",
            top_k=5
        )

        print("\nRetrieved memories:")
        for memory in results['memories']:
            print(f"- {memory['fact']} (confidence: {memory['confidence']:.2f})")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Example: Multi-Agent Coordination

```python
async def multi_agent_workflow():
    """Example of coordinating multiple agents with shared memory."""

    client = ContextIQClient(base_url="http://localhost:8000", token=token)

    # Shared scope for all agents
    shared_scope = {
        "user_id": "user_123",
        "project": "multi_agent_demo"
    }

    # Create separate sessions for each agent
    coordinator_session = await client.create_session(
        user_id="user_123",
        agent_id="coordinator",
        scope=shared_scope
    )

    specialist_session = await client.create_session(
        user_id="user_123",
        agent_id="specialist",
        scope=shared_scope
    )

    # Coordinator receives user request
    await client.add_message(
        coordinator_session['id'],
        "user",
        "I need help analyzing sales data"
    )

    # Coordinator delegates to specialist
    await client.add_message(
        coordinator_session['id'],
        "coordinator",
        "Delegating to data specialist"
    )

    await client.add_message(
        specialist_session['id'],
        "coordinator",
        "User needs sales data analysis"
    )

    # Specialist processes request
    await client.add_message(
        specialist_session['id'],
        "specialist",
        "Analyzing sales trends..."
    )

    # Generate memories from both sessions
    # Both will be stored in the same scope, creating shared memory
    await client.generate_memories(
        coordinator_session['id'],
        shared_scope
    )
    await client.generate_memories(
        specialist_session['id'],
        shared_scope
    )

    # Either agent can now search the shared memory
    memories = await client.search_memories(
        shared_scope,
        "What does the user need help with?",
        top_k=5
    )

    await client.close()
```

## References

- [Authentication Guide](AUTHENTICATION.md) - Detailed authentication setup
- [Architecture Overview](ARCHITECTURE.md) - System architecture details
- [Database Migrations](DATABASE_MIGRATIONS.md) - Schema management
- [Deployment Guide](DEPLOYMENT.md) - Deployment instructions
- [Development Guide](DEVELOPMENT.md) - Development setup
