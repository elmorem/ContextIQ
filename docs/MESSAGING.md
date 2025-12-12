# RabbitMQ Messaging System - Technical Deep Dive

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Core Components](#core-components)
5. [Message Flow](#message-flow)
6. [Queue Patterns](#queue-patterns)
7. [Publishing Messages](#publishing-messages)
8. [Consuming Messages](#consuming-messages)
9. [RPC Pattern](#rpc-pattern)
10. [Error Handling](#error-handling)
11. [Reliability Features](#reliability-features)
12. [Performance Tuning](#performance-tuning)
13. [Monitoring](#monitoring)
14. [Production Deployment](#production-deployment)
15. [Troubleshooting](#troubleshooting)

---

## Overview

### What is the Messaging System?

ContextIQ uses **RabbitMQ** as its message broker to enable asynchronous, distributed processing across multiple services and worker processes. The messaging system provides:

- **Decoupling**: Services communicate without direct dependencies
- **Scalability**: Multiple workers can process messages in parallel
- **Reliability**: Messages are persisted and guaranteed delivery
- **Load Balancing**: Work is distributed across available workers
- **Fault Tolerance**: Failed messages are retried or sent to dead letter queues

### Why RabbitMQ?

RabbitMQ was chosen for ContextIQ because:

1. **Mature & Battle-Tested**: Industry standard with proven reliability
2. **Advanced Routing**: Topic exchanges enable flexible message routing
3. **High Performance**: Handles thousands of messages per second
4. **Developer-Friendly**: Excellent Python support via `aio_pika`
5. **Operational Excellence**: Great monitoring, management UI, clustering support
6. **Feature Rich**: Dead letter queues, publisher confirms, consumer prefetch, TTL, priorities

### Key Use Cases in ContextIQ

- **Memory Extraction**: Sessions service triggers async memory extraction via workers
- **Memory Consolidation**: Periodic deduplication and merging of memories
- **Event Broadcasting**: Publishing session and memory events to multiple consumers
- **Task Distribution**: Load balancing work across multiple worker instances

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           ContextIQ Architecture                          │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Sessions API   │         │   Memory API    │         │  Other Services │
│                 │         │                 │         │                 │
│ - Create        │         │ - Store         │         │ - Analytics     │
│ - Read          │         │ - Retrieve      │         │ - Search        │
│ - Update        │         │ - Update        │         │                 │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │ Publish                   │ Publish                   │ Publish
         │ Messages                  │ Messages                  │ Messages
         ▼                           ▼                           ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           RabbitMQ Broker                                  │
│                                                                            │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │  contextiq.extraction│  │ contextiq.consolidation│  │ contextiq.events│ │
│  │     (topic)          │  │      (topic)          │  │    (topic)      │ │
│  └──────────┬───────────┘  └──────────┬───────────┘  └────────┬────────┘ │
│             │                          │                       │          │
│  ┌──────────▼───────────┐  ┌──────────▼───────────┐  ┌────────▼────────┐ │
│  │ extraction.requests  │  │consolidation.requests│  │ session.events  │ │
│  │     (queue)          │  │      (queue)         │  │    (queue)      │ │
│  └──────────────────────┘  └──────────────────────┘  └─────────────────┘ │
│                                                                            │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │ extraction.results   │  │consolidation.results │  │  memory.events  │ │
│  │     (queue)          │  │      (queue)         │  │    (queue)      │ │
│  └──────────────────────┘  └──────────────────────┘  └─────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                 contextiq.dlx (dead letter exchange)                 │ │
│  │  ┌────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    dead_letter (queue)                         │  │ │
│  │  └────────────────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
         │                           │                           │
         │ Consume                   │ Consume                   │ Consume
         │ Messages                  │ Messages                  │ Messages
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Memory Worker   │         │Consolidation    │         │  Event Handler  │
│                 │         │    Worker       │         │                 │
│ - Extract       │         │ - Deduplicate   │         │ - Analytics     │
│ - Embed         │         │ - Merge         │         │ - Logging       │
│ - Store         │         │ - Update        │         │ - Webhooks      │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Integration Points

1. **API Services** → Publish messages when work needs to be done asynchronously
2. **Workers** → Consume messages and process background tasks
3. **Event Handlers** → Subscribe to events for analytics, logging, webhooks
4. **Monitoring** → Track queue depths, message rates, consumer health

---

## Configuration

### Environment Variables

All RabbitMQ settings are configured via environment variables with the `RABBITMQ_` prefix:

#### Connection Settings

```bash
# Option 1: Complete connection URL (takes precedence)
RABBITMQ_URL=amqp://contextiq:contextiq_dev_password@localhost:5672/

# Option 2: Individual components
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=contextiq
RABBITMQ_PASSWORD=contextiq_dev_password
RABBITMQ_VHOST=/
```

**Note**: If `RABBITMQ_URL` is set to a non-default value, it takes precedence over individual components. Otherwise, the URL is built from the individual settings.

#### Connection Behavior

```bash
# Heartbeat interval in seconds (10-300)
# Prevents idle connections from being closed
RABBITMQ_HEARTBEAT=60

# Number of connection retry attempts (1-10)
RABBITMQ_CONNECTION_ATTEMPTS=3

# Delay between retry attempts in seconds (0.1-60.0)
RABBITMQ_RETRY_DELAY=2.0
```

#### Queue Settings

```bash
# Default prefetch count for consumers (1-100)
# How many unacknowledged messages a consumer can have
RABBITMQ_DEFAULT_PREFETCH_COUNT=10

# Default message TTL in milliseconds (0 = no expiration)
# Messages older than this are discarded
RABBITMQ_DEFAULT_MESSAGE_TTL=86400000  # 24 hours
```

#### Exchange Settings

```bash
# Default exchange type
# Options: topic, direct, fanout, headers
RABBITMQ_DEFAULT_EXCHANGE_TYPE=topic
```

#### Dead Letter Configuration

```bash
# Enable dead letter queue for failed messages
RABBITMQ_ENABLE_DEAD_LETTER=true

# Dead letter exchange name
RABBITMQ_DEAD_LETTER_EXCHANGE=contextiq.dlx
```

#### Feature Flags

```bash
# Enable publisher confirms for reliability
RABBITMQ_ENABLE_PUBLISHER_CONFIRMS=true

# Enable consumer prefetch for flow control
RABBITMQ_ENABLE_CONSUMER_PREFETCH=true
```

### MessagingSettings Class

All configuration is managed through the `MessagingSettings` Pydantic model:

```python
from shared.messaging.config import MessagingSettings, get_messaging_settings

# Get settings (cached via lru_cache)
settings = get_messaging_settings()

# Access configuration
print(f"URL: {settings.get_effective_url()}")
print(f"Heartbeat: {settings.heartbeat}s")
print(f"Prefetch: {settings.default_prefetch_count}")
print(f"Dead Letter: {settings.enable_dead_letter}")
```

#### Configuration Properties

```python
@dataclass
class MessagingSettings:
    # Connection settings
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672  # Must be 1-65535
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"

    # Connection behavior
    heartbeat: int = 60  # Must be 10-300
    connection_attempts: int = 3  # Must be 1-10
    retry_delay: float = 2.0  # Must be 0.1-60.0

    # Queue settings
    default_prefetch_count: int = 10  # Must be 1-100
    default_message_ttl: int = 86400000  # 24 hours in ms

    # Exchange settings
    default_exchange_type: str = "topic"

    # Dead letter configuration
    enable_dead_letter: bool = True
    dead_letter_exchange: str = "contextiq.dlx"

    # Feature flags
    enable_publisher_confirms: bool = True
    enable_consumer_prefetch: bool = True
```

### Configuration Examples

#### Development Configuration

```bash
# .env.development
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_HEARTBEAT=60
RABBITMQ_CONNECTION_ATTEMPTS=3
RABBITMQ_DEFAULT_PREFETCH_COUNT=5
RABBITMQ_ENABLE_DEAD_LETTER=true
```

#### Production Configuration

```bash
# .env.production
RABBITMQ_URL=amqps://contextiq:${RABBITMQ_PASSWORD}@rabbitmq.production.internal:5671/contextiq
RABBITMQ_HEARTBEAT=30
RABBITMQ_CONNECTION_ATTEMPTS=5
RABBITMQ_RETRY_DELAY=5.0
RABBITMQ_DEFAULT_PREFETCH_COUNT=20
RABBITMQ_ENABLE_DEAD_LETTER=true
RABBITMQ_ENABLE_PUBLISHER_CONFIRMS=true
```

#### Docker Compose Configuration

```bash
# .env.docker
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=contextiq
RABBITMQ_PASSWORD=contextiq_dev_password
RABBITMQ_VHOST=/
```

---

## Core Components

### RabbitMQClient

The `RabbitMQClient` class manages connections, channels, exchanges, and queues.

#### Features

- **Async Connection Management**: Using `aio_pika` for asyncio support
- **Automatic Reconnection**: `AbstractRobustConnection` handles network failures
- **Channel Pooling**: Efficient channel reuse
- **QoS Configuration**: Prefetch count for flow control
- **Health Checking**: Monitor connection health

#### Basic Usage

```python
from shared.messaging import RabbitMQClient
from shared.messaging.config import get_messaging_settings

# Initialize client
settings = get_messaging_settings()
client = RabbitMQClient(
    url=settings.get_effective_url(),
    heartbeat=settings.heartbeat,
    connection_attempts=settings.connection_attempts,
    retry_delay=settings.retry_delay,
)

# Connect to RabbitMQ
await client.connect()

# Use client...

# Disconnect when done
await client.disconnect()
```

#### Context Manager Usage

```python
async with RabbitMQClient(url=settings.get_effective_url()) as client:
    # Client is automatically connected
    channel = client.get_channel()
    # Do work...
    # Client is automatically disconnected on exit
```

#### Exchange Management

```python
from aio_pika import ExchangeType

# Declare topic exchange
exchange = await client.declare_exchange(
    name="contextiq.extraction",
    exchange_type=ExchangeType.TOPIC,
    durable=True,
)

# Declare direct exchange
exchange = await client.declare_exchange(
    name="contextiq.tasks",
    exchange_type=ExchangeType.DIRECT,
    durable=True,
)

# Declare fanout exchange (broadcast)
exchange = await client.declare_exchange(
    name="contextiq.broadcasts",
    exchange_type=ExchangeType.FANOUT,
    durable=True,
)
```

#### Queue Management

```python
from shared.messaging.queues import QueueConfig, Queues

# Declare queue from config
queue = await client.declare_queue(Queues.EXTRACTION_REQUESTS)

# Declare custom queue
custom_config = QueueConfig(
    name="my.custom.queue",
    durable=True,
    auto_delete=False,
    exchange="contextiq.custom",
    routing_key="custom.task.*",
)
queue = await client.declare_queue(custom_config)
```

#### Setup All Queues

```python
# Declare all predefined queues at startup
await client.setup_all_queues()
```

#### Health Checking

```python
# Check connection health
is_healthy = await client.health_check()
if not is_healthy:
    print("RabbitMQ connection is unhealthy!")
    # Attempt reconnection...
```

#### Error Handling

```python
from shared.exceptions import MessagingError

try:
    await client.connect()
except MessagingError as e:
    print(f"Failed to connect: {e.message}")
    print(f"Error code: {e.error_code}")
    print(f"Details: {e.details}")
```

---

### MessagePublisher

The `MessagePublisher` class provides methods for publishing messages to queues.

#### Features

- **JSON Serialization**: Automatic serialization of message payloads
- **Message Persistence**: Optional persistent storage
- **Priority Support**: Message prioritization (0-9)
- **Correlation IDs**: Request-response tracking
- **Batch Publishing**: Efficient bulk operations
- **RPC Pattern**: Request-response with reply queues

#### Basic Publishing

```python
from shared.messaging import MessagePublisher, RabbitMQClient
from shared.messaging.queues import Queues

# Initialize
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()

publisher = MessagePublisher(client=client)

# Publish message
message = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_123",
    "timestamp": "2025-12-11T10:30:00Z",
}

await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
    persistent=True,
)
```

#### Publishing with Priority

```python
# High priority message (processed first)
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=urgent_message,
    priority=9,  # 0-9, higher is more important
    persistent=True,
)

# Normal priority message
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=normal_message,
    priority=5,
    persistent=True,
)

# Low priority message (processed last)
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=low_priority_message,
    priority=0,
    persistent=True,
)
```

#### Publishing with Correlation ID

```python
import uuid

correlation_id = str(uuid.uuid4())

await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
    correlation_id=correlation_id,
    persistent=True,
)

# Track this message for correlation
print(f"Published message with correlation_id: {correlation_id}")
```

#### Non-Persistent Messages

```python
# Faster but not durable (lost on broker restart)
await publisher.publish(
    queue_config=Queues.SESSION_EVENTS,
    message=event_data,
    persistent=False,  # DeliveryMode.NOT_PERSISTENT
)
```

#### Batch Publishing

```python
messages = [
    {"session_id": "session_1", "event": "created"},
    {"session_id": "session_2", "event": "created"},
    {"session_id": "session_3", "event": "created"},
]

await publisher.publish_batch(
    queue_config=Queues.SESSION_EVENTS,
    messages=messages,
    priority=5,
    persistent=True,
)

print(f"Published {len(messages)} messages")
```

#### Direct Queue Publishing

```python
# Publish directly to queue (no exchange)
custom_queue = QueueConfig(name="my.direct.queue")

await publisher.publish(
    queue_config=custom_queue,
    message=message,
    persistent=True,
)
```

#### Publishing to Exchange with Routing Key

```python
# Publish to exchange with specific routing key
queue_config = QueueConfig(
    name="extraction.results",
    exchange="contextiq.extraction",
    routing_key="extraction.result.success",
)

await publisher.publish(
    queue_config=queue_config,
    message=result_data,
    persistent=True,
)
```

#### Error Handling

```python
from shared.exceptions import MessagePublishError

try:
    await publisher.publish(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message=message,
    )
except MessagePublishError as e:
    print(f"Failed to publish to {e.details['queue']}")
    print(f"Error: {e.message}")
    # Implement retry logic...
```

---

### MessageConsumer

The `MessageConsumer` class provides methods for consuming messages from queues.

#### Features

- **Async Message Handling**: Non-blocking message processing
- **Auto-Acknowledgment**: Optional automatic message acknowledgment
- **Prefetch Control**: Flow control via QoS settings
- **Error Handling**: Automatic message rejection and requeue
- **Reply Support**: Send replies for RPC pattern
- **Graceful Shutdown**: Clean consumer shutdown

#### Basic Consumption

```python
from shared.messaging import MessageConsumer, RabbitMQClient
from shared.messaging.queues import Queues
from typing import Any

# Initialize
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()

consumer = MessageConsumer(client=client)

# Define message handler
async def handle_message(message: dict[str, Any]) -> None:
    print(f"Processing message: {message}")
    # Process the message...
    print("Message processed successfully")

# Start consuming
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handle_message,
    auto_ack=False,  # Manual acknowledgment
    prefetch_count=10,
)

print("Consumer started, waiting for messages...")
```

#### Manual Acknowledgment

```python
# Handler with manual acknowledgment (auto_ack=False)
async def handle_with_manual_ack(message: dict[str, Any]) -> None:
    try:
        # Process message
        result = await process_extraction(message)
        print(f"Processed: {result}")
        # Message is automatically acknowledged on success
    except ValueError as e:
        # Validation errors - don't requeue
        print(f"Invalid message: {e}")
        # Message is rejected without requeue
        raise
    except Exception as e:
        # Processing errors - requeue for retry
        print(f"Processing failed: {e}")
        # Message is rejected with requeue
        raise

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handle_with_manual_ack,
    auto_ack=False,
)
```

#### Auto Acknowledgment

```python
# Handler with auto acknowledgment (auto_ack=True)
async def handle_with_auto_ack(message: dict[str, Any]) -> None:
    # Message is acknowledged immediately upon receipt
    # Use only for non-critical messages where loss is acceptable
    print(f"Processing: {message}")
    await process_event(message)

await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=handle_with_auto_ack,
    auto_ack=True,  # Automatic acknowledgment
    prefetch_count=20,
)
```

#### Prefetch Count Tuning

```python
# Low prefetch for slow processing (memory-intensive tasks)
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=slow_handler,
    prefetch_count=1,  # Process one message at a time
)

# High prefetch for fast processing (lightweight tasks)
await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=fast_handler,
    prefetch_count=50,  # Process many messages concurrently
)

# Balanced prefetch (default)
await consumer.consume(
    queue_config=Queues.CONSOLIDATION_REQUESTS,
    handler=balanced_handler,
    prefetch_count=10,  # Default
)
```

#### Worker Mode (Blocking)

```python
# Run consumer in blocking mode (for worker processes)
async def worker_handler(message: dict[str, Any]) -> None:
    print(f"Worker processing: {message}")
    await do_work(message)

# This blocks until stopped
await consumer.run_consumer(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=worker_handler,
    auto_ack=False,
    prefetch_count=10,
)
```

#### Graceful Shutdown

```python
import signal

# Setup signal handlers
def signal_handler(signum, frame):
    print("Shutdown signal received")
    consumer.stop()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Run consumer
try:
    await consumer.run_consumer(
        queue_config=Queues.EXTRACTION_REQUESTS,
        handler=handle_message,
    )
except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    await consumer.stop_all()
    await client.disconnect()
    print("Consumer stopped gracefully")
```

#### Stopping Consumers

```python
# Stop specific consumer
await consumer.stop_consuming("extraction.requests")

# Stop all consumers
await consumer.stop_all()
```

#### Multiple Consumers

```python
# Consume from multiple queues
async def handle_extraction(message: dict[str, Any]) -> None:
    await process_extraction(message)

async def handle_consolidation(message: dict[str, Any]) -> None:
    await process_consolidation(message)

# Start multiple consumers
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handle_extraction,
)

await consumer.consume(
    queue_config=Queues.CONSOLIDATION_REQUESTS,
    handler=handle_consolidation,
)

# Keep running
import asyncio
while True:
    await asyncio.sleep(1)
```

---

### Queue Definitions

All queue configurations are defined in `shared/messaging/queues.py`.

#### QueueConfig Class

```python
from dataclasses import dataclass

@dataclass
class QueueConfig:
    """Queue configuration."""

    name: str  # Queue name
    durable: bool = True  # Survives broker restart
    auto_delete: bool = False  # Delete when last consumer disconnects
    exchange: str | None = None  # Exchange to bind to
    routing_key: str | None = None  # Routing key for binding
```

#### Predefined Queues

```python
from shared.messaging.queues import Queues

# Extraction queues
Queues.EXTRACTION_REQUESTS  # Memory extraction requests
Queues.EXTRACTION_RESULTS   # Memory extraction results

# Consolidation queues
Queues.CONSOLIDATION_REQUESTS  # Memory consolidation requests
Queues.CONSOLIDATION_RESULTS   # Memory consolidation results

# Event queues
Queues.SESSION_EVENTS  # Session lifecycle events
Queues.MEMORY_EVENTS   # Memory lifecycle events

# Dead letter queue
Queues.DEAD_LETTER  # Failed messages
```

#### Queue Details

##### Extraction Requests Queue

```python
EXTRACTION_REQUESTS = QueueConfig(
    name="extraction.requests",
    exchange="contextiq.extraction",
    routing_key="extraction.request",
    durable=True,
    auto_delete=False,
)

# Usage
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message={
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user_123",
    },
)
```

##### Extraction Results Queue

```python
EXTRACTION_RESULTS = QueueConfig(
    name="extraction.results",
    exchange="contextiq.extraction",
    routing_key="extraction.result",
    durable=True,
    auto_delete=False,
)

# Usage
await publisher.publish(
    queue_config=Queues.EXTRACTION_RESULTS,
    message={
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "memories_extracted": 15,
        "success": True,
    },
)
```

##### Consolidation Requests Queue

```python
CONSOLIDATION_REQUESTS = QueueConfig(
    name="consolidation.requests",
    exchange="contextiq.consolidation",
    routing_key="consolidation.request",
    durable=True,
    auto_delete=False,
)

# Usage
await publisher.publish(
    queue_config=Queues.CONSOLIDATION_REQUESTS,
    message={
        "scope": "user",
        "user_id": "user_123",
        "similarity_threshold": 0.85,
    },
)
```

##### Consolidation Results Queue

```python
CONSOLIDATION_RESULTS = QueueConfig(
    name="consolidation.results",
    exchange="contextiq.consolidation",
    routing_key="consolidation.result",
    durable=True,
    auto_delete=False,
)

# Usage
await publisher.publish(
    queue_config=Queues.CONSOLIDATION_RESULTS,
    message={
        "scope": "user",
        "memories_merged": 5,
        "success": True,
    },
)
```

##### Session Events Queue

```python
SESSION_EVENTS = QueueConfig(
    name="session.events",
    exchange="contextiq.events",
    routing_key="session.*",  # Wildcard routing
    durable=True,
    auto_delete=False,
)

# Usage - different event types
await publisher.publish(
    queue_config=QueueConfig(
        name="session.events",
        exchange="contextiq.events",
        routing_key="session.created",
    ),
    message={"session_id": "...", "event": "created"},
)

await publisher.publish(
    queue_config=QueueConfig(
        name="session.events",
        exchange="contextiq.events",
        routing_key="session.updated",
    ),
    message={"session_id": "...", "event": "updated"},
)
```

##### Memory Events Queue

```python
MEMORY_EVENTS = QueueConfig(
    name="memory.events",
    exchange="contextiq.events",
    routing_key="memory.*",  # Wildcard routing
    durable=True,
    auto_delete=False,
)

# Usage
await publisher.publish(
    queue_config=QueueConfig(
        name="memory.events",
        exchange="contextiq.events",
        routing_key="memory.created",
    ),
    message={"memory_id": "...", "event": "created"},
)
```

##### Dead Letter Queue

```python
DEAD_LETTER = QueueConfig(
    name="dead_letter",
    exchange="contextiq.dlx",
    routing_key="dead_letter",
    durable=True,
    auto_delete=False,
)

# Messages automatically routed here on failure
# Consume for manual inspection/reprocessing
async def handle_dead_letter(message: dict[str, Any]) -> None:
    print(f"Failed message: {message}")
    # Log, alert, or reprocess...
```

#### Getting All Queue Configs

```python
# Get all predefined queue configurations
all_queues = Queues.all_queues()

for queue_config in all_queues:
    print(f"Queue: {queue_config.name}")
    print(f"  Exchange: {queue_config.exchange}")
    print(f"  Routing Key: {queue_config.routing_key}")
    print(f"  Durable: {queue_config.durable}")
```

#### Creating Custom Queues

```python
# Create custom queue configuration
custom_queue = QueueConfig(
    name="analytics.events",
    durable=True,
    auto_delete=False,
    exchange="contextiq.analytics",
    routing_key="analytics.*",
)

# Declare and use
await client.declare_queue(custom_queue)
await publisher.publish(queue_config=custom_queue, message=data)
```

---

## Message Flow

### Session Event to Memory Extraction Flow

This diagram shows how a session creation event triggers memory extraction:

```
┌─────────────┐
│ Sessions API│
│             │
│ POST        │
│ /sessions   │
└──────┬──────┘
       │
       │ 1. Create session in database
       ▼
┌────────────────────────────────┐
│     PostgreSQL Database        │
│  sessions table (INSERTED)     │
└────────────────────────────────┘
       │
       │ 2. Publish extraction request
       ▼
┌────────────────────────────────────────────────┐
│            RabbitMQ Broker                     │
│                                                │
│  Exchange: contextiq.extraction                │
│  Routing Key: extraction.request               │
│            │                                   │
│            ▼                                   │
│  ┌──────────────────────────┐                 │
│  │ extraction.requests      │                 │
│  │                          │                 │
│  │ Message:                 │                 │
│  │ {                        │                 │
│  │   "session_id": "...",   │                 │
│  │   "user_id": "...",      │                 │
│  │   "timestamp": "..."     │                 │
│  │ }                        │                 │
│  └──────────────────────────┘                 │
└────────────────────────────────────────────────┘
       │
       │ 3. Consume message
       ▼
┌────────────────────────────────┐
│    Memory Generation Worker    │
│                                │
│  1. Fetch session events       │
│  2. Extract memories (LLM)     │
│  3. Generate embeddings        │
│  4. Store in Qdrant            │
│  5. Save to database           │
└──────┬─────────────────────────┘
       │
       │ 4. Publish result
       ▼
┌────────────────────────────────────────────────┐
│            RabbitMQ Broker                     │
│                                                │
│  Exchange: contextiq.extraction                │
│  Routing Key: extraction.result                │
│            │                                   │
│            ▼                                   │
│  ┌──────────────────────────┐                 │
│  │ extraction.results       │                 │
│  │                          │                 │
│  │ Message:                 │                 │
│  │ {                        │                 │
│  │   "session_id": "...",   │                 │
│  │   "memories_extracted": 15,│              │
│  │   "success": true        │                 │
│  │ }                        │                 │
│  └──────────────────────────┘                 │
└────────────────────────────────────────────────┘
       │
       │ 5. Consume result (optional)
       ▼
┌────────────────────────────────┐
│    Result Handler / Analytics  │
│                                │
│  - Update metrics              │
│  - Log success                 │
│  - Trigger consolidation       │
└────────────────────────────────┘
```

### Memory Extraction to Consolidation Flow

This diagram shows how memory extraction triggers consolidation:

```
┌────────────────────────────────┐
│  Memory Generation Worker      │
│                                │
│  Completed extraction for      │
│  user_123                      │
└──────┬─────────────────────────┘
       │
       │ 1. Publish consolidation request
       ▼
┌────────────────────────────────────────────────┐
│            RabbitMQ Broker                     │
│                                                │
│  Exchange: contextiq.consolidation             │
│  Routing Key: consolidation.request            │
│            │                                   │
│            ▼                                   │
│  ┌──────────────────────────┐                 │
│  │ consolidation.requests   │                 │
│  │                          │                 │
│  │ Message:                 │                 │
│  │ {                        │                 │
│  │   "scope": "user",       │                 │
│  │   "user_id": "user_123", │                 │
│  │   "threshold": 0.85      │                 │
│  │ }                        │                 │
│  └──────────────────────────┘                 │
└────────────────────────────────────────────────┘
       │
       │ 2. Consume message
       ▼
┌────────────────────────────────┐
│   Consolidation Worker         │
│                                │
│  1. Fetch user memories        │
│  2. Find duplicates            │
│  3. Merge similar memories     │
│  4. Resolve conflicts          │
│  5. Update database            │
└──────┬─────────────────────────┘
       │
       │ 3. Publish result
       ▼
┌────────────────────────────────────────────────┐
│            RabbitMQ Broker                     │
│                                                │
│  Exchange: contextiq.consolidation             │
│  Routing Key: consolidation.result             │
│            │                                   │
│            ▼                                   │
│  ┌──────────────────────────┐                 │
│  │ consolidation.results    │                 │
│  │                          │                 │
│  │ Message:                 │                 │
│  │ {                        │                 │
│  │   "scope": "user",       │                 │
│  │   "memories_merged": 5,  │                 │
│  │   "success": true        │                 │
│  │ }                        │                 │
│  └──────────────────────────┘                 │
└────────────────────────────────────────────────┘
```

### Event Publishing Flow

This diagram shows how events are broadcast to multiple consumers:

```
┌─────────────┐       ┌─────────────┐
│Sessions API │       │ Memory API  │
│             │       │             │
│ Create/     │       │ Create/     │
│ Update      │       │ Update      │
└──────┬──────┘       └──────┬──────┘
       │                     │
       │ session.created     │ memory.created
       │                     │
       ▼                     ▼
┌────────────────────────────────────────────────────────┐
│                 RabbitMQ Broker                        │
│                                                        │
│  ┌───────────────────────────┐  ┌──────────────────┐  │
│  │ contextiq.events          │  │ contextiq.events │  │
│  │ (topic exchange)          │  │ (topic exchange) │  │
│  │                           │  │                  │  │
│  │ Routing: session.created  │  │ Routing:         │  │
│  │          session.updated  │  │   memory.created │  │
│  │          session.deleted  │  │   memory.updated │  │
│  └───────┬───────────────────┘  └────────┬─────────┘  │
│          │                               │            │
│          │ session.*                     │ memory.*   │
│          │                               │            │
│          ▼                               ▼            │
│  ┌──────────────────┐          ┌──────────────────┐  │
│  │ session.events   │          │ memory.events    │  │
│  │ (queue)          │          │ (queue)          │  │
│  └──────────────────┘          └──────────────────┘  │
└────────────────────────────────────────────────────────┘
       │                               │
       │                               │
       ▼                               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Analytics    │  │ Logging      │  │ Webhook      │
│ Service      │  │ Service      │  │ Service      │
│              │  │              │  │              │
│ - Track      │  │ - Audit log  │  │ - Notify     │
│   metrics    │  │ - Debug log  │  │   external   │
│              │  │              │  │   systems    │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Queue Patterns

### Work Queue Pattern

Work queues distribute tasks among multiple workers for parallel processing.

#### Characteristics

- **Load Balancing**: Messages are distributed evenly across workers
- **Scaling**: Add more workers to increase throughput
- **Reliability**: If a worker dies, messages are requeued
- **Fair Dispatch**: Prefetch count ensures fair distribution

#### Example: Memory Extraction

```python
# Producer (Sessions API)
async def trigger_extraction(session_id: str, user_id: str):
    """Trigger memory extraction for a session."""
    await publisher.publish(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message={
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
        persistent=True,
    )

# Consumer (Memory Worker - Instance 1)
async def worker_1_handler(message: dict[str, Any]) -> None:
    print(f"Worker 1 processing: {message['session_id']}")
    await extract_memories(message)

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=worker_1_handler,
    prefetch_count=5,
)

# Consumer (Memory Worker - Instance 2)
async def worker_2_handler(message: dict[str, Any]) -> None:
    print(f"Worker 2 processing: {message['session_id']}")
    await extract_memories(message)

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=worker_2_handler,
    prefetch_count=5,
)

# Result: Messages are distributed evenly
# Worker 1: session_1, session_3, session_5
# Worker 2: session_2, session_4, session_6
```

#### Scaling Work Queues

```bash
# Start multiple worker instances
docker-compose up --scale memory-worker=5
docker-compose up --scale consolidation-worker=3

# Or manually
python -m workers.memory_generation.worker &  # Instance 1
python -m workers.memory_generation.worker &  # Instance 2
python -m workers.memory_generation.worker &  # Instance 3
```

---

### Event Queue Pattern

Event queues broadcast events to multiple interested consumers.

#### Characteristics

- **Pub/Sub**: One message, many consumers
- **Topic Routing**: Consumers filter by routing key patterns
- **Decoupling**: Producers don't know about consumers
- **Extensibility**: Add new consumers without changing producers

#### Example: Session Events

```python
# Publisher (Sessions API)
async def publish_session_event(
    session_id: str,
    event_type: str,
    data: dict[str, Any],
):
    """Publish session lifecycle event."""
    routing_key = f"session.{event_type}"

    await publisher.publish(
        queue_config=QueueConfig(
            name="session.events",
            exchange="contextiq.events",
            routing_key=routing_key,
        ),
        message={
            "session_id": session_id,
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        },
        persistent=False,  # Events are ephemeral
    )

# Usage
await publish_session_event(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    event_type="created",
    data={"user_id": "user_123"},
)

await publish_session_event(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    event_type="updated",
    data={"updated_fields": ["title", "context"]},
)

await publish_session_event(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    event_type="deleted",
    data={},
)
```

#### Consumer 1: Analytics Service

```python
async def analytics_handler(message: dict[str, Any]) -> None:
    """Track analytics for all session events."""
    event = message["event"]
    session_id = message["session_id"]

    # Increment metrics
    metrics.increment(f"session.{event}")

    # Store in analytics database
    await analytics_db.insert({
        "event_type": f"session.{event}",
        "session_id": session_id,
        "timestamp": message["timestamp"],
    })

# Subscribe to all session events
await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=analytics_handler,
)
```

#### Consumer 2: Logging Service

```python
async def logging_handler(message: dict[str, Any]) -> None:
    """Log all session events for audit trail."""
    logger.info(
        "session_event",
        event=message["event"],
        session_id=message["session_id"],
        data=message["data"],
    )

# Subscribe to all session events
await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=logging_handler,
)
```

#### Consumer 3: Webhook Service

```python
async def webhook_handler(message: dict[str, Any]) -> None:
    """Send webhooks for session creation only."""
    if message["event"] == "created":
        await send_webhook(
            url="https://external.api/webhooks/session-created",
            data=message,
        )

# Subscribe to all session events (filter in handler)
await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=webhook_handler,
)
```

---

### Dead Letter Queue Pattern

Dead letter queues capture failed messages for later inspection or reprocessing.

#### How It Works

1. Message processing fails (exception raised)
2. Consumer rejects message without requeue
3. Message is routed to dead letter exchange
4. Dead letter exchange routes to dead letter queue
5. Admin inspects/reprocesses failed messages

#### Configuration

```python
# Dead letter queue is automatically configured
# when RABBITMQ_ENABLE_DEAD_LETTER=true

# Messages are sent to DLQ when:
# 1. Processing fails and requeue=False
# 2. Message TTL expires
# 3. Queue reaches max length (if configured)
```

#### Processing Dead Letters

```python
async def dead_letter_handler(message: dict[str, Any]) -> None:
    """Handle messages that failed processing."""
    logger.error(
        "dead_letter_received",
        message=message,
    )

    # Log to error tracking system
    await sentry.capture_message({
        "message": "Failed message in DLQ",
        "data": message,
    })

    # Attempt manual reprocessing
    try:
        await reprocess_message(message)
        logger.info("dead_letter_reprocessed", message=message)
    except Exception as e:
        logger.error("dead_letter_reprocess_failed", error=str(e))
        # Send alert to ops team
        await alert_ops_team(message, error=str(e))

# Consume dead letter queue
await consumer.consume(
    queue_config=Queues.DEAD_LETTER,
    handler=dead_letter_handler,
    auto_ack=False,
)
```

#### Manual Inspection

```python
async def inspect_dead_letters():
    """Inspect messages in dead letter queue without consuming."""
    # Use RabbitMQ Management API
    import aiohttp

    async with aiohttp.ClientSession() as session:
        response = await session.get(
            "http://localhost:15672/api/queues/%2F/dead_letter/",
            auth=aiohttp.BasicAuth("contextiq", "password"),
        )
        data = await response.json()

        print(f"Dead letter queue depth: {data['messages']}")
        print(f"Message rate: {data['messages_ready']}/sec")
```

#### Requeuing Dead Letters

```python
async def requeue_dead_letter(message: dict[str, Any], target_queue: QueueConfig):
    """Requeue a dead letter message to original queue."""
    await publisher.publish(
        queue_config=target_queue,
        message=message,
        persistent=True,
    )
    logger.info("dead_letter_requeued", target=target_queue.name)

# Example: Requeue to extraction queue
message = await get_dead_letter_message()
await requeue_dead_letter(
    message=message,
    target_queue=Queues.EXTRACTION_REQUESTS,
)
```

---

## Publishing Messages

### Complete Publishing Examples

#### Example 1: Simple Message

```python
from shared.messaging import MessagePublisher, RabbitMQClient
from shared.messaging.queues import Queues
from shared.messaging.config import get_messaging_settings

# Setup
settings = get_messaging_settings()
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()
publisher = MessagePublisher(client=client)

# Publish
message = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_123",
}

await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
)

print("Message published successfully")
```

#### Example 2: High Priority Message

```python
# Urgent extraction request
urgent_message = {
    "session_id": "urgent-session-id",
    "user_id": "vip_user_456",
    "priority": "high",
}

await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=urgent_message,
    priority=9,  # Highest priority
    persistent=True,
)
```

#### Example 3: Batch Publishing

```python
# Publish multiple messages efficiently
sessions = ["session_1", "session_2", "session_3"]

messages = [
    {"session_id": sid, "user_id": "user_123"}
    for sid in sessions
]

await publisher.publish_batch(
    queue_config=Queues.EXTRACTION_REQUESTS,
    messages=messages,
    priority=5,
    persistent=True,
)

print(f"Published {len(messages)} messages")
```

#### Example 4: Event Publishing

```python
# Publish session created event
await publisher.publish(
    queue_config=QueueConfig(
        name="session.events",
        exchange="contextiq.events",
        routing_key="session.created",
    ),
    message={
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user_123",
        "event": "created",
        "timestamp": datetime.utcnow().isoformat(),
    },
    persistent=False,  # Events are ephemeral
)
```

#### Example 5: Publishing with Context Manager

```python
# Automatic connection management
async with RabbitMQClient(url=settings.get_effective_url()) as client:
    publisher = MessagePublisher(client=client)

    await publisher.publish(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message={"session_id": "..."},
    )
    # Client automatically disconnected
```

#### Example 6: Error Handling

```python
from shared.exceptions import MessagePublishError

try:
    await publisher.publish(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message=message,
    )
except MessagePublishError as e:
    logger.error(
        "publish_failed",
        queue=e.details["queue"],
        error=e.message,
    )
    # Implement retry logic
    await retry_publish(message)
```

#### Example 7: Publishing from API Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException
from shared.messaging import MessagePublisher, RabbitMQClient

router = APIRouter()

async def get_publisher() -> MessagePublisher:
    """Dependency to get message publisher."""
    settings = get_messaging_settings()
    client = RabbitMQClient(url=settings.get_effective_url())
    await client.connect()
    return MessagePublisher(client=client)

@router.post("/sessions/{session_id}/extract")
async def trigger_extraction(
    session_id: str,
    publisher: MessagePublisher = Depends(get_publisher),
):
    """Trigger memory extraction for a session."""
    try:
        await publisher.publish(
            queue_config=Queues.EXTRACTION_REQUESTS,
            message={
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            persistent=True,
        )
        return {"status": "extraction_triggered", "session_id": session_id}
    except MessagePublishError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Example 8: Publishing with Correlation ID

```python
import uuid

# Generate correlation ID
correlation_id = str(uuid.uuid4())

# Publish request
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message={
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user_123",
    },
    correlation_id=correlation_id,
    persistent=True,
)

# Track for correlation
print(f"Request sent with correlation_id: {correlation_id}")

# Later, when result arrives with same correlation_id:
# "This result corresponds to our request"
```

#### Example 9: Publishing to Multiple Queues

```python
# Publish to extraction queue
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=extraction_message,
)

# Also publish to event queue
await publisher.publish(
    queue_config=QueueConfig(
        name="session.events",
        exchange="contextiq.events",
        routing_key="session.extraction_requested",
    ),
    message=event_message,
    persistent=False,
)

print("Message published to multiple queues")
```

#### Example 10: Scheduled Publishing

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def publish_consolidation_request():
    """Publish consolidation request every hour."""
    await publisher.publish(
        queue_config=Queues.CONSOLIDATION_REQUESTS,
        message={
            "scope": "user",
            "user_id": "user_123",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

# Schedule hourly consolidation
scheduler.add_job(
    publish_consolidation_request,
    trigger="interval",
    hours=1,
)

scheduler.start()
```

---

## Consuming Messages

### Complete Consumption Examples

#### Example 1: Basic Consumer

```python
from shared.messaging import MessageConsumer, RabbitMQClient
from shared.messaging.queues import Queues
from typing import Any

# Setup
settings = get_messaging_settings()
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()
consumer = MessageConsumer(client=client)

# Define handler
async def handle_message(message: dict[str, Any]) -> None:
    print(f"Received: {message}")
    await process_message(message)
    print("Processed successfully")

# Start consuming
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handle_message,
    auto_ack=False,
    prefetch_count=10,
)
```

#### Example 2: Worker Process

```python
# Complete worker implementation
class MemoryWorker:
    def __init__(self):
        settings = get_messaging_settings()
        self.client = RabbitMQClient(url=settings.get_effective_url())
        self.consumer = MessageConsumer(client=self.client)
        self._running = False

    async def start(self):
        """Start worker and consume messages."""
        self._running = True
        await self.client.connect()

        await self.consumer.run_consumer(
            queue_config=Queues.EXTRACTION_REQUESTS,
            handler=self.handle_message,
            auto_ack=False,
            prefetch_count=10,
        )

    async def stop(self):
        """Stop worker gracefully."""
        self._running = False
        self.consumer.stop()
        await self.consumer.stop_all()
        await self.client.disconnect()

    async def handle_message(self, message: dict[str, Any]) -> None:
        """Process extraction request."""
        session_id = message["session_id"]
        print(f"Processing session: {session_id}")

        # Extract memories
        result = await extract_memories(message)

        print(f"Extracted {result['count']} memories")

# Run worker
worker = MemoryWorker()
try:
    await worker.start()
except KeyboardInterrupt:
    await worker.stop()
```

#### Example 3: Multiple Consumers

```python
# Consume from multiple queues in parallel
async def handle_extraction(message: dict[str, Any]) -> None:
    print(f"Extraction: {message}")
    await process_extraction(message)

async def handle_consolidation(message: dict[str, Any]) -> None:
    print(f"Consolidation: {message}")
    await process_consolidation(message)

async def handle_events(message: dict[str, Any]) -> None:
    print(f"Event: {message}")
    await process_event(message)

# Start all consumers
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handle_extraction,
    prefetch_count=10,
)

await consumer.consume(
    queue_config=Queues.CONSOLIDATION_REQUESTS,
    handler=handle_consolidation,
    prefetch_count=5,
)

await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=handle_events,
    prefetch_count=20,
)

# Keep running
while True:
    await asyncio.sleep(1)
```

#### Example 4: Error Handling in Consumer

```python
async def robust_handler(message: dict[str, Any]) -> None:
    """Handler with comprehensive error handling."""
    try:
        # Validate message
        session_id = message.get("session_id")
        if not session_id:
            raise ValueError("Missing session_id")

        # Process message
        result = await process_extraction(message)

        # Log success
        logger.info(
            "extraction_complete",
            session_id=session_id,
            memories=result["count"],
        )

    except ValueError as e:
        # Validation error - don't requeue
        logger.error("invalid_message", error=str(e), message=message)
        raise  # Rejected without requeue

    except Exception as e:
        # Processing error - requeue for retry
        logger.error("processing_failed", error=str(e), message=message)
        raise  # Rejected with requeue

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=robust_handler,
    auto_ack=False,
)
```

#### Example 5: Consumer with Retry Logic

```python
async def handler_with_retry(message: dict[str, Any]) -> None:
    """Handler with automatic retry logic."""
    max_retries = 3
    retry_count = message.get("_retry_count", 0)

    try:
        await process_message(message)
    except Exception as e:
        if retry_count < max_retries:
            # Increment retry count
            message["_retry_count"] = retry_count + 1

            # Requeue with delay
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff

            logger.warning(
                "retrying_message",
                retry=retry_count + 1,
                max_retries=max_retries,
            )

            raise  # Reject with requeue
        else:
            # Max retries exceeded - don't requeue
            logger.error(
                "max_retries_exceeded",
                retries=retry_count,
                message=message,
            )
            raise ValueError("Max retries exceeded")  # Reject without requeue

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handler_with_retry,
)
```

#### Example 6: Consumer with Metrics

```python
from prometheus_client import Counter, Histogram

# Define metrics
messages_processed = Counter(
    "messages_processed_total",
    "Total messages processed",
    ["queue", "status"],
)

processing_duration = Histogram(
    "message_processing_duration_seconds",
    "Message processing duration",
    ["queue"],
)

async def handler_with_metrics(message: dict[str, Any]) -> None:
    """Handler that tracks metrics."""
    queue_name = "extraction.requests"

    with processing_duration.labels(queue=queue_name).time():
        try:
            await process_message(message)
            messages_processed.labels(queue=queue_name, status="success").inc()
        except Exception as e:
            messages_processed.labels(queue=queue_name, status="error").inc()
            raise

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handler_with_metrics,
)
```

#### Example 7: Consumer with Rate Limiting

```python
from asyncio import Semaphore

# Limit concurrent processing
semaphore = Semaphore(5)  # Max 5 concurrent messages

async def rate_limited_handler(message: dict[str, Any]) -> None:
    """Handler with rate limiting."""
    async with semaphore:
        print(f"Processing (concurrent: {6 - semaphore._value})")
        await process_message(message)
        print("Processing complete")

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=rate_limited_handler,
    prefetch_count=10,
)
```

#### Example 8: Consumer with Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise

circuit_breaker = CircuitBreaker()

async def handler_with_circuit_breaker(message: dict[str, Any]) -> None:
    """Handler with circuit breaker pattern."""
    try:
        await circuit_breaker.call(process_message, message)
    except Exception as e:
        logger.error("circuit_breaker_error", error=str(e))
        raise

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handler_with_circuit_breaker,
)
```

#### Example 9: Consumer with Graceful Shutdown

```python
import signal

class GracefulWorker:
    def __init__(self):
        self.consumer = None
        self.client = None
        self.running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False
        if self.consumer:
            self.consumer.stop()

    async def start(self):
        """Start worker with graceful shutdown."""
        self.running = True

        settings = get_messaging_settings()
        self.client = RabbitMQClient(url=settings.get_effective_url())
        await self.client.connect()

        self.consumer = MessageConsumer(client=self.client)

        try:
            await self.consumer.run_consumer(
                queue_config=Queues.EXTRACTION_REQUESTS,
                handler=self.handle_message,
            )
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        logger.info("cleaning_up")
        if self.consumer:
            await self.consumer.stop_all()
        if self.client:
            await self.client.disconnect()
        logger.info("cleanup_complete")

    async def handle_message(self, message: dict[str, Any]) -> None:
        """Process message."""
        if not self.running:
            logger.warning("shutdown_in_progress_skipping_message")
            raise Exception("Shutdown in progress")

        await process_message(message)

# Run worker
worker = GracefulWorker()
await worker.start()
```

#### Example 10: Consumer with Dead Letter Handling

```python
async def handler_with_dlq(message: dict[str, Any]) -> None:
    """Handler that sends failures to DLQ."""
    try:
        # Attempt processing
        await process_message(message)

    except ValueError as e:
        # Validation error - send to DLQ
        logger.error("validation_error_sending_to_dlq", error=str(e))
        raise  # Rejected without requeue (goes to DLQ)

    except Exception as e:
        # Check retry count
        retry_count = message.get("_retry_count", 0)

        if retry_count >= 3:
            # Max retries - send to DLQ
            logger.error("max_retries_sending_to_dlq", error=str(e))
            raise ValueError("Max retries exceeded")  # Goes to DLQ
        else:
            # Retry
            message["_retry_count"] = retry_count + 1
            logger.warning("retrying_message", retry=retry_count + 1)
            raise  # Rejected with requeue

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handler_with_dlq,
)
```

---

## RPC Pattern

### Request-Response with Correlation IDs

The RPC (Remote Procedure Call) pattern enables request-response communication over message queues.

#### How It Works

```
┌─────────┐                            ┌─────────┐
│ Client  │                            │ Server  │
└────┬────┘                            └────┬────┘
     │                                      │
     │ 1. Generate correlation_id           │
     │    correlation_id = uuid4()          │
     │                                      │
     │ 2. Create reply queue                │
     │    reply_queue = "reply.123"         │
     │                                      │
     │ 3. Publish request                   │
     │    - correlation_id                  │
     │    - reply_to: "reply.123"           │
     ├─────────────────────────────────────>│
     │                                      │
     │                                      │ 4. Process request
     │                                      │    result = process(message)
     │                                      │
     │                                      │ 5. Publish response
     │                                      │    - correlation_id (same)
     │                                      │    - routing_key: "reply.123"
     │<─────────────────────────────────────┤
     │                                      │
     │ 6. Match correlation_id              │
     │    and return result                 │
     │                                      │
```

### RPC Publishing Example

```python
from shared.messaging import MessagePublisher, RabbitMQClient
from shared.messaging.queues import Queues

# Initialize
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()
publisher = MessagePublisher(client=client)

# Make RPC call
request = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_123",
}

try:
    response = await publisher.publish_with_reply(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message=request,
        reply_queue="extraction.reply",
        timeout=30.0,  # 30 second timeout
    )

    print(f"Received response: {response}")
    print(f"Memories extracted: {response['memories_extracted']}")

except TimeoutError:
    print("Request timed out after 30 seconds")
except Exception as e:
    print(f"RPC failed: {e}")
```

### RPC Consumer Example

```python
from shared.messaging import MessageConsumer, RabbitMQClient
from typing import Any

# Initialize
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()
consumer = MessageConsumer(client=client)

# Define RPC handler (must return result)
async def rpc_handler(message: dict[str, Any]) -> dict[str, Any]:
    """Handle RPC request and return response."""
    session_id = message["session_id"]
    user_id = message["user_id"]

    # Process request
    result = await extract_memories(session_id, user_id)

    # Return response
    return {
        "session_id": session_id,
        "memories_extracted": result["count"],
        "success": True,
    }

# Start consuming (reply is automatic)
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=rpc_handler,
    auto_ack=False,
)

# Consumer automatically sends reply when handler returns a value
```

### Manual RPC Implementation

```python
import uuid
import asyncio

async def manual_rpc_call(
    queue_config: QueueConfig,
    message: dict[str, Any],
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Manual RPC implementation for more control."""

    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    reply_queue_name = f"reply.{correlation_id}"

    # Create reply future
    reply_future = asyncio.Future()

    # Declare exclusive reply queue
    channel = client.get_channel()
    reply_queue = await channel.declare_queue(
        reply_queue_name,
        exclusive=True,
        auto_delete=True,
    )

    # Setup reply consumer
    async def on_reply(msg):
        if msg.correlation_id == correlation_id:
            reply_data = json.loads(msg.body.decode())
            reply_future.set_result(reply_data)
            await msg.ack()

    await reply_queue.consume(on_reply)

    # Publish request
    await publisher.publish(
        queue_config=queue_config,
        message=message,
        correlation_id=correlation_id,
        reply_to=reply_queue_name,
    )

    # Wait for reply with timeout
    try:
        reply = await asyncio.wait_for(reply_future, timeout=timeout)
        return reply
    except asyncio.TimeoutError:
        raise TimeoutError(f"RPC timeout after {timeout}s")
    finally:
        # Cleanup reply queue
        await reply_queue.delete()

# Usage
response = await manual_rpc_call(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message={"session_id": "..."},
    timeout=30.0,
)
```

### RPC with Error Handling

```python
async def rpc_handler_with_errors(message: dict[str, Any]) -> dict[str, Any]:
    """RPC handler that returns error responses."""
    try:
        result = await process_request(message)
        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        # Return error response
        return {
            "success": False,
            "error": "validation_error",
            "message": str(e),
        }
    except Exception as e:
        # Return error response
        return {
            "success": False,
            "error": "processing_error",
            "message": str(e),
        }

# Client side
response = await publisher.publish_with_reply(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=request,
    reply_queue="extraction.reply",
)

if response["success"]:
    print(f"Success: {response['data']}")
else:
    print(f"Error: {response['error']} - {response['message']}")
```

---

## Error Handling

### Message Processing Errors

#### Automatic Error Handling

The `MessageConsumer` automatically handles errors:

```python
async def process_message(message: IncomingMessage) -> None:
    try:
        # Parse message
        body = json.loads(message.body.decode())

        # Handle message
        result = await handler(body)

        # Send reply if needed
        if message.reply_to and result is not None:
            await self._send_reply(message, result)

        # Acknowledge message
        await message.ack()

    except json.JSONDecodeError as e:
        # Malformed message - reject without requeue
        logger.error("message_decode_failed", error=str(e))
        await message.reject(requeue=False)  # Goes to DLQ

    except Exception as e:
        # Processing error - reject with requeue
        logger.error("message_processing_failed", error=str(e))
        await message.reject(requeue=True)  # Retry
```

#### Custom Error Handling

```python
async def custom_error_handler(message: dict[str, Any]) -> None:
    """Handler with custom error logic."""
    try:
        await process_message(message)

    except ValueError as e:
        # Validation error - don't requeue
        logger.error("validation_error", error=str(e))
        raise  # Automatic reject(requeue=False)

    except ConnectionError as e:
        # Temporary error - requeue with delay
        logger.warning("connection_error_retrying", error=str(e))
        await asyncio.sleep(5)  # Wait before requeue
        raise  # Automatic reject(requeue=True)

    except Exception as e:
        # Unknown error - send to DLQ
        logger.error("unknown_error_sending_to_dlq", error=str(e))
        # Send alert
        await alert_ops_team(message, error=e)
        raise ValueError("Unhandled error")  # Goes to DLQ
```

### Retry Logic

#### Exponential Backoff

```python
async def handler_with_exponential_backoff(message: dict[str, Any]) -> None:
    """Handler with exponential backoff retry."""
    retry_count = message.get("_retry_count", 0)
    max_retries = 5

    try:
        await process_message(message)
    except Exception as e:
        if retry_count < max_retries:
            # Calculate backoff delay: 2^retry seconds
            delay = 2 ** retry_count

            logger.warning(
                "retrying_with_backoff",
                retry=retry_count + 1,
                delay=delay,
            )

            # Update retry count
            message["_retry_count"] = retry_count + 1

            # Wait before requeue
            await asyncio.sleep(delay)

            raise  # Requeue
        else:
            logger.error("max_retries_exceeded", retries=retry_count)
            raise ValueError("Max retries exceeded")  # DLQ
```

#### Retry with Different Delays

```python
async def handler_with_custom_delays(message: dict[str, Any]) -> None:
    """Handler with custom retry delays."""
    retry_count = message.get("_retry_count", 0)
    retry_delays = [1, 5, 15, 60, 300]  # 1s, 5s, 15s, 1m, 5m

    try:
        await process_message(message)
    except Exception as e:
        if retry_count < len(retry_delays):
            delay = retry_delays[retry_count]

            logger.warning(
                "retrying",
                retry=retry_count + 1,
                delay=delay,
            )

            message["_retry_count"] = retry_count + 1
            await asyncio.sleep(delay)

            raise  # Requeue
        else:
            logger.error("all_retries_exhausted")
            raise ValueError("All retries exhausted")  # DLQ
```

### Dead Letter Queue Handling

#### Consuming Dead Letters

```python
async def dead_letter_consumer():
    """Consume and process dead letter messages."""
    consumer = MessageConsumer(client=client)

    async def handle_dead_letter(message: dict[str, Any]) -> None:
        logger.error(
            "dead_letter_received",
            message=message,
        )

        # Extract original queue info
        original_queue = message.get("_original_queue")
        error_reason = message.get("_error")

        # Log to monitoring system
        await log_failed_message(
            queue=original_queue,
            message=message,
            error=error_reason,
        )

        # Send alert
        if should_alert(error_reason):
            await send_alert(
                subject="Message processing failed",
                message=message,
                error=error_reason,
            )

    await consumer.consume(
        queue_config=Queues.DEAD_LETTER,
        handler=handle_dead_letter,
    )
```

#### Reprocessing Dead Letters

```python
async def reprocess_dead_letters():
    """Reprocess messages from dead letter queue."""
    # Get messages from DLQ
    dead_letters = await get_dead_letter_messages()

    for msg in dead_letters:
        try:
            # Determine original queue
            original_queue = determine_original_queue(msg)

            # Remove error metadata
            clean_msg = remove_metadata(msg)

            # Republish to original queue
            await publisher.publish(
                queue_config=original_queue,
                message=clean_msg,
                persistent=True,
            )

            logger.info(
                "dead_letter_reprocessed",
                queue=original_queue.name,
            )

        except Exception as e:
            logger.error(
                "dead_letter_reprocess_failed",
                error=str(e),
            )
```

### Connection Error Handling

#### Automatic Reconnection

```python
# RabbitMQClient uses AbstractRobustConnection
# which automatically reconnects on connection loss

client = RabbitMQClient(url=settings.get_effective_url())

# Connection is automatically re-established
# Channels are automatically re-declared
# Consumers are automatically re-started
```

#### Manual Reconnection

```python
async def connect_with_retry(max_attempts: int = 5) -> RabbitMQClient:
    """Connect to RabbitMQ with retry logic."""
    client = RabbitMQClient(url=settings.get_effective_url())

    for attempt in range(1, max_attempts + 1):
        try:
            await client.connect()
            logger.info("connected_to_rabbitmq", attempt=attempt)
            return client
        except MessagingError as e:
            if attempt < max_attempts:
                delay = 2 ** attempt  # Exponential backoff
                logger.warning(
                    "connection_failed_retrying",
                    attempt=attempt,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
            else:
                logger.error("connection_failed_all_attempts", attempts=attempt)
                raise

# Usage
client = await connect_with_retry(max_attempts=5)
```

### Publisher Confirmation

```python
# Enable publisher confirms in settings
RABBITMQ_ENABLE_PUBLISHER_CONFIRMS=true

# Publisher confirms are automatically handled by aio_pika
# If publish fails, MessagePublishError is raised

try:
    await publisher.publish(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message=message,
    )
    # Message was confirmed by broker
except MessagePublishError as e:
    # Publish was not confirmed
    logger.error("publish_not_confirmed", error=str(e))
    # Implement retry or alert
```

---

## Reliability Features

### Message Persistence

#### Persistent Messages

```python
# Messages survive broker restart
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
    persistent=True,  # DeliveryMode.PERSISTENT
)

# Queue must also be durable
QueueConfig(
    name="extraction.requests",
    durable=True,  # Queue survives broker restart
)
```

#### Non-Persistent Messages

```python
# Faster but lost on broker restart
await publisher.publish(
    queue_config=Queues.SESSION_EVENTS,
    message=event,
    persistent=False,  # DeliveryMode.NOT_PERSISTENT
)

# Use for:
# - Events that can be lost
# - High-throughput scenarios
# - Non-critical notifications
```

### Publisher Confirms

```python
# Enable in configuration
RABBITMQ_ENABLE_PUBLISHER_CONFIRMS=true

# Ensures message reaches broker before publish() returns
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
    persistent=True,
)
# At this point, broker has confirmed receipt
```

### Prefetch Control

#### Consumer Prefetch

```python
# Low prefetch for slow/memory-intensive processing
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=slow_handler,
    prefetch_count=1,  # One message at a time
)

# High prefetch for fast processing
await consumer.consume(
    queue_config=Queues.SESSION_EVENTS,
    handler=fast_handler,
    prefetch_count=50,  # Many messages buffered
)

# Balanced (default)
await consumer.consume(
    queue_config=Queues.CONSOLIDATION_REQUESTS,
    handler=handler,
    prefetch_count=10,
)
```

#### Why Prefetch Matters

```
Without Prefetch (prefetch_count=1):
┌────────┐     ┌────────┐     ┌────────┐
│ Msg 1  │     │ Msg 2  │     │ Msg 3  │
└───┬────┘     └────────┘     └────────┘
    │
    ▼ Process
    │ Ack
    └──> Fetch Next

With Prefetch (prefetch_count=10):
┌────────┬────────┬────────┬────────┐
│ Msg 1  │ Msg 2  │ Msg 3  │ Msg 4  │ ... (10 buffered)
└───┬────┴────┬───┴────┬───┴────┬───┘
    ▼         ▼        ▼        ▼
  Process  Process  Process  Process (parallel)
```

### Connection Recovery

```python
# AbstractRobustConnection handles recovery automatically
client = RabbitMQClient(url=settings.get_effective_url())
await client.connect()

# If connection is lost:
# 1. Client attempts reconnection
# 2. Channels are re-declared
# 3. Exchanges are re-declared
# 4. Queues are re-declared
# 5. Consumers are restarted
# All automatic!
```

### Message TTL

```python
# Configure default TTL
RABBITMQ_DEFAULT_MESSAGE_TTL=86400000  # 24 hours

# Messages older than TTL are:
# 1. Automatically removed from queue
# 2. Sent to dead letter queue (if configured)

# Use for:
# - Time-sensitive tasks
# - Preventing queue buildup
# - Automatic cleanup
```

### Queue Durability

```python
# Durable queues survive broker restart
QueueConfig(
    name="extraction.requests",
    durable=True,  # Queue persists
)

# Non-durable queues are deleted on restart
QueueConfig(
    name="temporary.queue",
    durable=False,  # Deleted on restart
)
```

### Auto-Delete Queues

```python
# Auto-delete when last consumer disconnects
QueueConfig(
    name="temporary.results",
    auto_delete=True,  # Cleanup automatic
)

# Manual cleanup required
QueueConfig(
    name="persistent.queue",
    auto_delete=False,  # Never auto-delete
)
```

---

## Performance Tuning

### Prefetch Count Optimization

#### Finding Optimal Prefetch

```python
# Test different prefetch counts
prefetch_values = [1, 5, 10, 20, 50]

for prefetch in prefetch_values:
    print(f"Testing prefetch={prefetch}")

    start_time = time.time()
    message_count = 0

    async def benchmark_handler(message: dict[str, Any]) -> None:
        nonlocal message_count
        await process_message(message)
        message_count += 1

    await consumer.consume(
        queue_config=Queues.EXTRACTION_REQUESTS,
        handler=benchmark_handler,
        prefetch_count=prefetch,
    )

    # Run for 60 seconds
    await asyncio.sleep(60)

    duration = time.time() - start_time
    throughput = message_count / duration

    print(f"Prefetch {prefetch}: {throughput:.2f} msg/s")
```

#### Prefetch Guidelines

```python
# CPU-bound processing (heavy computation)
prefetch_count = 1  # One message per CPU core

# I/O-bound processing (network calls, DB queries)
prefetch_count = 10-50  # Higher prefetch for waiting

# Memory-intensive processing (large payloads)
prefetch_count = 1-5  # Low to prevent OOM

# Lightweight processing (logging, metrics)
prefetch_count = 50-100  # High for throughput
```

### Batch Operations

#### Batch Publishing

```python
# Inefficient: Multiple publish calls
for session_id in session_ids:
    await publisher.publish(
        queue_config=Queues.EXTRACTION_REQUESTS,
        message={"session_id": session_id},
    )

# Efficient: Batch publish
messages = [
    {"session_id": sid}
    for sid in session_ids
]

await publisher.publish_batch(
    queue_config=Queues.EXTRACTION_REQUESTS,
    messages=messages,
)
```

#### Batch Processing

```python
# Process messages in batches
batch = []
batch_size = 10

async def batching_handler(message: dict[str, Any]) -> None:
    batch.append(message)

    if len(batch) >= batch_size:
        # Process batch
        await process_batch(batch)
        batch.clear()

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=batching_handler,
    prefetch_count=batch_size * 2,
)
```

### Connection Pooling

```python
# Create connection pool
class RabbitMQPool:
    def __init__(self, size: int = 5):
        self.size = size
        self.clients = []
        self._index = 0

    async def initialize(self):
        """Initialize connection pool."""
        for _ in range(self.size):
            client = RabbitMQClient(url=settings.get_effective_url())
            await client.connect()
            self.clients.append(client)

    def get_client(self) -> RabbitMQClient:
        """Get next client (round-robin)."""
        client = self.clients[self._index]
        self._index = (self._index + 1) % self.size
        return client

    async def close_all(self):
        """Close all connections."""
        for client in self.clients:
            await client.disconnect()

# Usage
pool = RabbitMQPool(size=5)
await pool.initialize()

# Get publisher with pooled client
client = pool.get_client()
publisher = MessagePublisher(client=client)

await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
)
```

### Message Compression

```python
import gzip
import base64

async def publish_compressed(
    publisher: MessagePublisher,
    queue_config: QueueConfig,
    message: dict[str, Any],
):
    """Publish compressed message."""
    # Serialize and compress
    json_data = json.dumps(message).encode()
    compressed = gzip.compress(json_data)
    encoded = base64.b64encode(compressed).decode()

    # Publish compressed message
    await publisher.publish(
        queue_config=queue_config,
        message={
            "_compressed": True,
            "data": encoded,
        },
    )

async def consume_compressed(message: dict[str, Any]) -> dict[str, Any]:
    """Decompress and parse message."""
    if message.get("_compressed"):
        encoded = message["data"]
        compressed = base64.b64decode(encoded)
        json_data = gzip.decompress(compressed)
        return json.loads(json_data)
    return message
```

### Parallel Processing

```python
# Process multiple messages in parallel
async def parallel_handler(message: dict[str, Any]) -> None:
    """Handler that processes messages in parallel."""
    # Create task for processing
    task = asyncio.create_task(process_message(message))

    # Don't await - let it run in background
    # (prefetch_count controls concurrency)

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=parallel_handler,
    prefetch_count=20,  # Up to 20 parallel tasks
)
```

### Memory Optimization

```python
# Process large payloads efficiently
async def memory_efficient_handler(message: dict[str, Any]) -> None:
    """Handler optimized for large messages."""

    # Process in chunks
    if "large_data" in message:
        data = message["large_data"]
        chunk_size = 1000

        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            await process_chunk(chunk)

            # Allow garbage collection
            del chunk
            await asyncio.sleep(0)  # Yield control

    # Delete large fields after processing
    if "large_data" in message:
        del message["large_data"]
```

---

## Monitoring

### Health Checks

```python
# Check RabbitMQ connection health
is_healthy = await client.health_check()

if is_healthy:
    print("RabbitMQ connection is healthy")
else:
    print("RabbitMQ connection is unhealthy")
    # Alert ops team
    await alert_ops_team("RabbitMQ connection down")
```

### Queue Depth Monitoring

```python
import aiohttp

async def get_queue_depth(queue_name: str) -> int:
    """Get number of messages in queue."""
    management_url = "http://localhost:15672"
    username = "contextiq"
    password = "password"

    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"{management_url}/api/queues/%2F/{queue_name}",
            auth=aiohttp.BasicAuth(username, password),
        )
        data = await response.json()
        return data["messages"]

# Monitor queue depth
depth = await get_queue_depth("extraction.requests")
if depth > 1000:
    print(f"Queue depth high: {depth} messages")
    # Scale up workers
    await scale_workers(count=10)
```

### Message Rate Tracking

```python
from prometheus_client import Counter, Gauge

# Define metrics
messages_published = Counter(
    "rabbitmq_messages_published_total",
    "Total messages published",
    ["queue"],
)

messages_consumed = Counter(
    "rabbitmq_messages_consumed_total",
    "Total messages consumed",
    ["queue", "status"],
)

queue_depth = Gauge(
    "rabbitmq_queue_depth",
    "Current queue depth",
    ["queue"],
)

# Track publishing
await publisher.publish(
    queue_config=Queues.EXTRACTION_REQUESTS,
    message=message,
)
messages_published.labels(queue="extraction.requests").inc()

# Track consumption
async def monitored_handler(message: dict[str, Any]) -> None:
    try:
        await process_message(message)
        messages_consumed.labels(
            queue="extraction.requests",
            status="success",
        ).inc()
    except Exception as e:
        messages_consumed.labels(
            queue="extraction.requests",
            status="error",
        ).inc()
        raise

# Update queue depth
async def update_queue_metrics():
    """Update queue depth metrics."""
    while True:
        for queue_config in Queues.all_queues():
            depth = await get_queue_depth(queue_config.name)
            queue_depth.labels(queue=queue_config.name).set(depth)

        await asyncio.sleep(10)  # Update every 10s
```

### Consumer Health

```python
class ConsumerHealthCheck:
    def __init__(self):
        self.last_message_time = time.time()
        self.messages_processed = 0

    async def handle_message(self, message: dict[str, Any]) -> None:
        """Handler that tracks health."""
        self.last_message_time = time.time()
        self.messages_processed += 1

        await process_message(message)

    def is_healthy(self) -> bool:
        """Check if consumer is healthy."""
        # Check if messages are being processed
        time_since_last = time.time() - self.last_message_time

        if time_since_last > 300:  # 5 minutes
            return False

        return True

    def get_stats(self) -> dict:
        """Get consumer statistics."""
        return {
            "messages_processed": self.messages_processed,
            "last_message_age": time.time() - self.last_message_time,
            "is_healthy": self.is_healthy(),
        }

# Usage
health_check = ConsumerHealthCheck()

await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=health_check.handle_message,
)

# Check health
stats = health_check.get_stats()
print(f"Consumer stats: {stats}")
```

### Logging

```python
# Structured logging with context
logger.info(
    "message_published",
    queue="extraction.requests",
    session_id="550e8400-e29b-41d4-a716-446655440000",
    correlation_id="abc123",
)

logger.info(
    "message_consumed",
    queue="extraction.requests",
    correlation_id="abc123",
    processing_time_ms=1234,
)

logger.error(
    "message_processing_failed",
    queue="extraction.requests",
    error="ValueError: Invalid session_id",
    correlation_id="abc123",
)
```

---

## Production Deployment

### RabbitMQ Cluster

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  rabbitmq-1:
    image: rabbitmq:3.12-management
    hostname: rabbitmq-1
    environment:
      RABBITMQ_ERLANG_COOKIE: 'secret_cookie'
      RABBITMQ_DEFAULT_USER: contextiq
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq-1-data:/var/lib/rabbitmq
    networks:
      - rabbitmq-cluster

  rabbitmq-2:
    image: rabbitmq:3.12-management
    hostname: rabbitmq-2
    environment:
      RABBITMQ_ERLANG_COOKIE: 'secret_cookie'
      RABBITMQ_DEFAULT_USER: contextiq
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq-2-data:/var/lib/rabbitmq
    networks:
      - rabbitmq-cluster
    depends_on:
      - rabbitmq-1

  rabbitmq-3:
    image: rabbitmq:3.12-management
    hostname: rabbitmq-3
    environment:
      RABBITMQ_ERLANG_COOKIE: 'secret_cookie'
      RABBITMQ_DEFAULT_USER: contextiq
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq-3-data:/var/lib/rabbitmq
    networks:
      - rabbitmq-cluster
    depends_on:
      - rabbitmq-1

networks:
  rabbitmq-cluster:
    driver: bridge

volumes:
  rabbitmq-1-data:
  rabbitmq-2-data:
  rabbitmq-3-data:
```

### High Availability Queues

```python
# Configure HA queues via RabbitMQ policy
import aiohttp

async def setup_ha_policy():
    """Setup high availability queue policy."""
    management_url = "http://localhost:15672"

    policy = {
        "pattern": "^(extraction|consolidation)\\.",
        "definition": {
            "ha-mode": "all",  # Replicate to all nodes
            "ha-sync-mode": "automatic",
            "ha-sync-batch-size": 1,
        },
        "priority": 0,
        "apply-to": "queues",
    }

    async with aiohttp.ClientSession() as session:
        await session.put(
            f"{management_url}/api/policies/%2F/ha-policy",
            json=policy,
            auth=aiohttp.BasicAuth("contextiq", "password"),
        )

await setup_ha_policy()
```

### Load Balancing

```nginx
# nginx.conf
upstream rabbitmq_cluster {
    server rabbitmq-1:5672;
    server rabbitmq-2:5672;
    server rabbitmq-3:5672;
}

server {
    listen 5672;
    proxy_pass rabbitmq_cluster;
}
```

### Worker Scaling

```yaml
# kubernetes/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-worker
spec:
  replicas: 5  # Scale to 5 instances
  selector:
    matchLabels:
      app: memory-worker
  template:
    metadata:
      labels:
        app: memory-worker
    spec:
      containers:
      - name: worker
        image: contextiq/memory-worker:latest
        env:
        - name: RABBITMQ_URL
          valueFrom:
            secretKeyRef:
              name: rabbitmq-secret
              key: url
        - name: WORKER_PREFETCH_COUNT
          value: "10"
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
```

### Auto-Scaling

```yaml
# kubernetes/worker-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: memory-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: memory-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: External
    external:
      metric:
        name: rabbitmq_queue_depth
        selector:
          matchLabels:
            queue: extraction.requests
      target:
        type: AverageValue
        averageValue: "100"
```

### Monitoring Stack

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}

  rabbitmq-exporter:
    image: kbudde/rabbitmq-exporter:latest
    environment:
      RABBIT_URL: http://rabbitmq:15672
      RABBIT_USER: contextiq
      RABBIT_PASSWORD: ${RABBITMQ_PASSWORD}
    ports:
      - "9419:9419"

volumes:
  prometheus-data:
  grafana-data:
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Messages Not Being Consumed

**Symptoms:**
- Queue depth increasing
- No consumer activity
- Workers appear idle

**Diagnosis:**
```python
# Check queue depth
depth = await get_queue_depth("extraction.requests")
print(f"Queue depth: {depth}")

# Check consumer count
async def get_consumer_count(queue_name: str) -> int:
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"http://localhost:15672/api/queues/%2F/{queue_name}",
            auth=aiohttp.BasicAuth("contextiq", "password"),
        )
        data = await response.json()
        return data["consumers"]

consumers = await get_consumer_count("extraction.requests")
print(f"Active consumers: {consumers}")
```

**Solutions:**
1. Check if workers are running
2. Verify queue configuration
3. Check for errors in worker logs
4. Verify prefetch_count setting
5. Check network connectivity

#### Issue 2: High Memory Usage

**Symptoms:**
- Worker memory increasing
- OOM errors
- Slow processing

**Diagnosis:**
```python
import psutil

process = psutil.Process()
memory_info = process.memory_info()

print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
print(f"Prefetch count: {consumer.prefetch_count}")
```

**Solutions:**
```python
# Reduce prefetch count
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handler,
    prefetch_count=1,  # Reduce from 10
)

# Process messages in chunks
async def memory_efficient_handler(message: dict[str, Any]) -> None:
    # Process in chunks
    # Delete processed data
    # Yield control periodically
    pass
```

#### Issue 3: Connection Timeouts

**Symptoms:**
- MessagingError on connect
- Connection refused
- Timeout errors

**Diagnosis:**
```python
# Test connection
try:
    client = RabbitMQClient(url=settings.get_effective_url())
    await client.connect()
    print("Connection successful")
except MessagingError as e:
    print(f"Connection failed: {e.message}")
```

**Solutions:**
```python
# Increase timeout
client = RabbitMQClient(
    url=settings.get_effective_url(),
    connection_attempts=5,  # Increase from 3
    retry_delay=5.0,  # Increase from 2.0
)

# Check RabbitMQ health
import aiohttp

async with aiohttp.ClientSession() as session:
    response = await session.get(
        "http://localhost:15672/api/healthchecks/node",
        auth=aiohttp.BasicAuth("contextiq", "password"),
    )
    health = await response.json()
    print(f"RabbitMQ health: {health}")
```

#### Issue 4: Messages Going to Dead Letter Queue

**Symptoms:**
- Dead letter queue filling up
- Messages not being processed
- Errors in logs

**Diagnosis:**
```python
# Inspect dead letter queue
async def inspect_dlq():
    async with aiohttp.ClientSession() as session:
        # Get messages from DLQ
        response = await session.get(
            "http://localhost:15672/api/queues/%2F/dead_letter/get",
            json={"count": 10, "ackmode": "ack_requeue_false"},
            auth=aiohttp.BasicAuth("contextiq", "password"),
        )
        messages = await response.json()

        for msg in messages:
            print(f"Dead letter: {msg['payload']}")
            print(f"Headers: {msg['properties']['headers']}")

await inspect_dlq()
```

**Solutions:**
1. Fix validation errors
2. Handle exceptions properly
3. Increase retry attempts
4. Reprocess dead letters manually

#### Issue 5: Slow Message Processing

**Symptoms:**
- High queue depth
- Low throughput
- Messages timing out

**Diagnosis:**
```python
import time

processing_times = []

async def benchmark_handler(message: dict[str, Any]) -> None:
    start = time.time()
    await process_message(message)
    duration = time.time() - start

    processing_times.append(duration)

    if len(processing_times) >= 100:
        avg_time = sum(processing_times) / len(processing_times)
        print(f"Average processing time: {avg_time:.2f}s")
        processing_times.clear()
```

**Solutions:**
```python
# Increase prefetch for I/O-bound tasks
await consumer.consume(
    queue_config=Queues.EXTRACTION_REQUESTS,
    handler=handler,
    prefetch_count=20,  # Increase from 10
)

# Scale workers
docker-compose up --scale memory-worker=10

# Optimize processing logic
async def optimized_handler(message: dict[str, Any]) -> None:
    # Use async operations
    # Batch database queries
    # Cache frequently accessed data
    pass
```

### Debugging Tools

#### RabbitMQ Management UI

Access at `http://localhost:15672`

- View queue depths
- Monitor message rates
- Check consumer connections
- Inspect messages
- View exchange bindings

#### Command Line Tools

```bash
# List queues
docker exec rabbitmq rabbitmqctl list_queues name messages consumers

# List exchanges
docker exec rabbitmq rabbitmqctl list_exchanges name type

# List bindings
docker exec rabbitmq rabbitmqctl list_bindings

# Check cluster status
docker exec rabbitmq rabbitmqctl cluster_status

# View connections
docker exec rabbitmq rabbitmqctl list_connections

# View channels
docker exec rabbitmq rabbitmqctl list_channels
```

#### Python Debugging

```python
# Enable debug logging
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("aio_pika")
logger.setLevel(logging.DEBUG)

# Log all messages
async def debug_handler(message: dict[str, Any]) -> None:
    logger.debug(f"Received message: {message}")
    await process_message(message)
    logger.debug(f"Processed message: {message}")
```

---

## Cross-References

### Related Documentation

- [Architecture](ARCHITECTURE.md) - Overall system architecture
- [Development](DEVELOPMENT.md) - Development environment setup
- [Deployment](DEPLOYMENT.md) - Production deployment guide
- [API Usage](API_USAGE.md) - HTTP API documentation

### Related Code

- `/shared/messaging/` - Messaging implementation
- `/workers/memory_generation/` - Memory extraction worker
- `/workers/consolidation/` - Consolidation worker
- `/services/sessions/` - Sessions API (publisher)
- `/services/memory/` - Memory API (publisher)

### External Resources

- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [aio_pika Documentation](https://aio-pika.readthedocs.io/)
- [RabbitMQ Best Practices](https://www.rabbitmq.com/best-practices.html)
- [AMQP 0-9-1 Reference](https://www.rabbitmq.com/amqp-0-9-1-reference.html)

---

## Conclusion

This document has provided a comprehensive technical deep dive into ContextIQ's RabbitMQ messaging system. Key takeaways:

1. **Reliable Messaging**: Publisher confirms, message persistence, and dead letter queues ensure reliability
2. **Scalability**: Work queues and prefetch control enable horizontal scaling
3. **Flexibility**: Topic exchanges and routing keys support complex message routing
4. **Observability**: Health checks, metrics, and logging enable effective monitoring
5. **Production-Ready**: Clustering, HA queues, and auto-scaling support production workloads

For questions or issues, consult the troubleshooting section or refer to the related documentation.
