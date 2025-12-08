# Docker Setup Guide

This guide explains how to run ContextIQ using Docker and Docker Compose.

## Prerequisites

- Docker 20.10 or later
- Docker Compose V2
- At least 4GB of available RAM
- (Optional) Make for running convenience commands

## Quick Start

### 1. Set Up Environment Variables

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 2. Start All Services

**Production mode:**
```bash
docker-compose up -d
```

**Development mode (with hot-reloading):**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 3. Verify Services Are Running

```bash
docker-compose ps
```

All services should show as "healthy" or "running":
- `contextiq-postgres` - PostgreSQL database (port 5432)
- `contextiq-redis` - Redis cache (port 6379)
- `contextiq-qdrant` - Qdrant vector store (ports 6333, 6334)
- `contextiq-rabbitmq` - RabbitMQ message queue (ports 5672, 15672)
- `contextiq-sessions` - Sessions service (port 8001)
- `contextiq-memory` - Memory service (port 8002)
- `contextiq-memory-generation-worker` - Memory generation worker
- `contextiq-consolidation-worker` - Consolidation worker

### 4. Check Service Health

**Sessions Service:**
```bash
curl http://localhost:8001/health/live
```

**Memory Service:**
```bash
curl http://localhost:8002/health/live
```

**RabbitMQ Management UI:**
Open http://localhost:15672 in your browser
- Username: `contextiq`
- Password: `contextiq_dev_password`

**Qdrant Dashboard:**
Open http://localhost:6333/dashboard

## Architecture

### Infrastructure Services

#### PostgreSQL (with PostGIS)
- **Container:** `contextiq-postgres`
- **Image:** `postgis/postgis:15-3.4-alpine`
- **Port:** 5432
- **Volume:** `postgres_data`
- **Purpose:** Primary database for all services

#### Redis
- **Container:** `contextiq-redis`
- **Image:** `redis:7-alpine`
- **Port:** 6379
- **Volume:** `redis_data`
- **Purpose:** Cache and session storage

#### Qdrant
- **Container:** `contextiq-qdrant`
- **Image:** `qdrant/qdrant:latest`
- **Ports:** 6333 (REST), 6334 (gRPC)
- **Volume:** `qdrant_data`
- **Purpose:** Vector database for embeddings

#### RabbitMQ
- **Container:** `contextiq-rabbitmq`
- **Image:** `rabbitmq:3-management-alpine`
- **Ports:** 5672 (AMQP), 15672 (Management UI)
- **Volume:** `rabbitmq_data`
- **Purpose:** Message queue for async tasks

### Application Services

#### Sessions Service
- **Container:** `contextiq-sessions`
- **Port:** 8001
- **Purpose:** Conversation session management
- **Dependencies:** PostgreSQL, Redis

#### Memory Service
- **Container:** `contextiq-memory`
- **Port:** 8002
- **Purpose:** Episodic memory storage with embeddings
- **Dependencies:** PostgreSQL, Redis, Qdrant, RabbitMQ

### Worker Services

#### Memory Generation Worker
- **Container:** `contextiq-memory-generation-worker`
- **Purpose:** Process memory extraction requests
- **Dependencies:** PostgreSQL, Redis, Qdrant, RabbitMQ

#### Consolidation Worker
- **Container:** `contextiq-consolidation-worker`
- **Purpose:** Consolidate and update memories
- **Dependencies:** PostgreSQL, Redis, Qdrant, RabbitMQ

## Common Operations

### View Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
docker-compose logs -f memory-service
docker-compose logs -f consolidation-worker
```

### Restart a Service

```bash
docker-compose restart memory-service
```

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove Volumes (⚠️ Data Loss)

```bash
docker-compose down -v
```

### Rebuild Services After Code Changes

```bash
docker-compose build
docker-compose up -d
```

**Rebuild specific service:**
```bash
docker-compose build memory-service
docker-compose up -d memory-service
```

### Execute Commands in a Container

```bash
# Open shell in a service
docker-compose exec memory-service /bin/sh

# Run Python in a service
docker-compose exec memory-service python

# Run database migrations
docker-compose exec memory-service python -m alembic upgrade head
```

### Access PostgreSQL

```bash
docker-compose exec postgres psql -U contextiq -d contextiq
```

### Access Redis CLI

```bash
docker-compose exec redis redis-cli
```

## Development Workflow

### 1. Local Development with Hot-Reload

Use the development compose file for automatic code reloading:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Changes to Python files will automatically reload the services.

### 2. Running Tests

```bash
# Run all tests
docker-compose exec memory-service pytest

# Run specific test file
docker-compose exec memory-service pytest tests/test_memories.py

# Run with coverage
docker-compose exec memory-service pytest --cov=app tests/
```

### 3. Code Quality Checks

```bash
# Format code
docker-compose exec memory-service black .

# Lint code
docker-compose exec memory-service ruff check .

# Type check
docker-compose exec memory-service mypy app/
```

## Troubleshooting

### Services Won't Start

1. Check if ports are already in use:
   ```bash
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   lsof -i :6333  # Qdrant
   lsof -i :5672  # RabbitMQ
   lsof -i :8001  # Sessions service
   lsof -i :8002  # Memory service
   ```

2. Check Docker resources:
   ```bash
   docker system df
   docker system prune  # Clean up if needed
   ```

### Service Keeps Restarting

Check logs for errors:
```bash
docker-compose logs memory-service
```

Common issues:
- Missing environment variables
- Database connection failures
- API keys not set

### Database Connection Errors

1. Ensure PostgreSQL is healthy:
   ```bash
   docker-compose ps postgres
   ```

2. Check connection from service:
   ```bash
   docker-compose exec memory-service nc -zv postgres 5432
   ```

### Worker Not Processing Messages

1. Check RabbitMQ is healthy:
   ```bash
   docker-compose logs rabbitmq
   ```

2. Check worker logs:
   ```bash
   docker-compose logs memory-generation-worker
   docker-compose logs consolidation-worker
   ```

3. Verify queues exist in RabbitMQ Management UI:
   http://localhost:15672/#/queues

### Out of Memory

Increase Docker memory allocation in Docker Desktop settings to at least 4GB.

### Clean Slate Reset

To completely reset the environment:

```bash
# Stop all containers
docker-compose down

# Remove all volumes (⚠️ destroys all data)
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Rebuild everything
docker-compose build --no-cache
docker-compose up -d
```

## Production Deployment

For production deployment:

1. **Use production environment file:**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Set secure credentials:**
   - Change all default passwords
   - Use strong `SECRET_KEY`
   - Enable `API_KEY_ENABLED=true`
   - Set appropriate `LOG_LEVEL=WARNING` or `ERROR`

3. **Configure external services:**
   - Use managed PostgreSQL (e.g., AWS RDS, Google Cloud SQL)
   - Use managed Redis (e.g., AWS ElastiCache, Redis Cloud)
   - Use managed RabbitMQ (e.g., CloudAMQP)

4. **Deploy:**
   ```bash
   docker-compose --env-file .env.prod up -d
   ```

5. **Set up monitoring and backups:**
   - Configure health check endpoints
   - Set up database backups
   - Monitor service logs
   - Set up alerting for failures

## Network Configuration

All services run on the `contextiq-network` bridge network. Services can communicate with each other using their service names:

- `postgres:5432` - Database
- `redis:6379` - Cache
- `qdrant:6333` - Vector store
- `rabbitmq:5672` - Message queue
- `sessions-service:8001` - Sessions API
- `memory-service:8002` - Memory API

## Volume Management

Persistent data is stored in Docker volumes:

- `postgres_data` - PostgreSQL database
- `redis_data` - Redis cache (with AOF persistence)
- `qdrant_data` - Qdrant vector storage
- `rabbitmq_data` - RabbitMQ message queue data

To backup volumes:
```bash
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Environment Variables Reference

See [`.env.example`](.env.example) for complete list of configuration options.

Key environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `QDRANT_URL` - Qdrant REST API endpoint
- `RABBITMQ_URL` - RabbitMQ connection string
- `OPENAI_API_KEY` - OpenAI API key for LLM operations
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude models
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT` - Deployment environment (development, staging, production)

## Support

For issues and questions:
- Check the [troubleshooting section](#troubleshooting)
- Review service logs
- Open an issue on GitHub
