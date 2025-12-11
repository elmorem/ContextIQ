# ContextIQ Deployment Guide

Comprehensive guide for deploying ContextIQ in local development, staging, and production environments.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Service Health Checks](#service-health-checks)
- [Monitoring & Observability](#monitoring--observability)
- [Production Considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

## Overview

ContextIQ supports multiple deployment models:

1. **Local Development**: Run services directly with Python
2. **Docker Compose**: Containerized deployment for development/staging
3. **Kubernetes**: Production-grade orchestration (planned)

This guide focuses on local and Docker Compose deployments.

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **uv**: Python package manager (recommended)
- **Make**: For convenience commands
- **PostgreSQL Client**: For database management (optional)

### Install Prerequisites

#### macOS

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 docker docker-compose make postgresql

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Install make
sudo apt install -y make

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### System Requirements

**Minimum** (Development):
- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB

**Recommended** (Production):
- CPU: 4-8 cores
- RAM: 16 GB
- Disk: 100 GB SSD

## Local Development

Run services directly on your machine without Docker.

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/contextiq.git
cd contextiq
```

### Step 2: Install Dependencies

```bash
# Using uv (recommended)
make dev-install

# Or using pip
pip install -e ".[dev]"
```

### Step 3: Start Infrastructure

Start required services (PostgreSQL, Redis, Qdrant, RabbitMQ):

```bash
# Start only infrastructure services
docker-compose up -d postgres redis qdrant rabbitmq

# Verify services are running
docker-compose ps
```

### Step 4: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Required settings:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://contextiq:contextiq_dev_password@localhost:5432/contextiq

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# RabbitMQ
RABBITMQ_URL=amqp://contextiq:contextiq_dev_password@localhost:5672/

# LLM Provider (at least one required)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Authentication (optional for development)
AUTH_REQUIRE_AUTH=false
AUTH_JWT_SECRET_KEY=your-dev-secret-key
```

### Step 5: Initialize Database

```bash
# Initialize database and extensions
make db-init

# Run migrations
make db-upgrade

# Verify migration status
make db-current
```

### Step 6: Initialize Services

```bash
# Initialize Qdrant collections
make qdrant-init

# Initialize RabbitMQ queues
make rabbitmq-init
```

### Step 7: Start Services

In separate terminal windows:

```bash
# Terminal 1: Sessions Service
make run-sessions

# Terminal 2: Memory Service
make run-memory

# Terminal 3: API Gateway
make run-gateway

# Terminal 4: Workers (in background)
make run-workers
```

### Step 8: Verify Installation

```bash
# Check service health
make services-health

# Or manually
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

Expected output:
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "1.0.0"
}
```

## Docker Compose Deployment

Recommended for staging and testing environments.

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/contextiq.git
cd contextiq

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start all services
make dev
```

This will:
1. Build Docker images
2. Start all services
3. Run database migrations
4. Initialize Qdrant collections
5. Initialize RabbitMQ queues

### Step-by-Step Deployment

#### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
- LLM API keys (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`)
- Authentication settings (if needed)
- Custom ports (if needed)

#### 2. Build Images

```bash
make docker-build
```

This builds:
- `contextiq-gateway` - API Gateway
- `contextiq-sessions` - Sessions Service
- `contextiq-memory` - Memory Service
- `contextiq-memory-generation-worker` - Memory generation worker
- `contextiq-consolidation-worker` - Consolidation worker

#### 3. Start Services

```bash
make docker-up
```

Services will start in this order:
1. PostgreSQL (with health check)
2. Redis (with health check)
3. Qdrant (with health check)
4. RabbitMQ (with health check)
5. Sessions Service (depends on Postgres, Redis)
6. Memory Service (depends on Postgres, Redis, Qdrant, RabbitMQ)
7. API Gateway (depends on Sessions, Memory)
8. Workers (depend on all infrastructure)

#### 4. Initialize Database

```bash
# Database is automatically initialized on first run
# To manually run migrations:
docker-compose exec sessions-service python scripts/db_migrate.py upgrade
```

#### 5. Verify Deployment

```bash
# Check all services
make services-health

# View logs
make docker-logs

# Check individual service
docker-compose logs -f memory-service
```

### Accessing Services

Once deployed, services are available at:

| Service | URL | Credentials |
|---------|-----|-------------|
| API Gateway | http://localhost:8000 | N/A |
| Sessions Service | http://localhost:8001 | N/A |
| Memory Service | http://localhost:8002 | N/A |
| RabbitMQ Management | http://localhost:15672 | contextiq / contextiq_dev_password |
| Qdrant Dashboard | http://localhost:6333/dashboard | N/A |
| PostgreSQL | localhost:5432 | contextiq / contextiq_dev_password |
| Redis | localhost:6379 | No password |

### Updating Services

```bash
# Pull latest code
git pull

# Rebuild images
make docker-build

# Restart services
make docker-down
make docker-up

# Run any new migrations
docker-compose exec sessions-service python scripts/db_migrate.py upgrade
```

### Scaling Services

Edit `docker-compose.yml` to add replicas:

```yaml
services:
  memory-service:
    # ...
    deploy:
      replicas: 3
```

Then restart:
```bash
docker-compose up -d --scale memory-service=3
```

## Environment Configuration

### Required Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/contextiq

# Redis
REDIS_URL=redis://host:6379/0

# Qdrant
QDRANT_URL=http://host:6333

# RabbitMQ
RABBITMQ_URL=amqp://user:password@host:5672/

# LLM Provider (at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Optional Variables

```bash
# Service Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
ENVIRONMENT=development           # development, staging, production

# Database Connection Pooling
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30.0
DATABASE_POOL_RECYCLE=3600

# Redis Settings
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5.0
REDIS_TTL_SESSION=86400           # 24 hours
REDIS_TTL_MEMORY=7200             # 2 hours

# Worker Configuration
WORKER_CONCURRENCY=5              # Parallel workers
WORKER_PREFETCH_COUNT=10          # Messages to prefetch

# Authentication
AUTH_REQUIRE_AUTH=false           # Enable authentication
AUTH_JWT_SECRET_KEY=secret        # JWT signing key
AUTH_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # OpenTelemetry endpoint
```

### Environment-Specific Configurations

#### Development

```bash
# .env.development
LOG_LEVEL=DEBUG
ENVIRONMENT=development
AUTH_REQUIRE_AUTH=false
DATABASE_POOL_SIZE=5
WORKER_CONCURRENCY=2
```

#### Staging

```bash
# .env.staging
LOG_LEVEL=INFO
ENVIRONMENT=staging
AUTH_REQUIRE_AUTH=true
DATABASE_POOL_SIZE=10
WORKER_CONCURRENCY=5
```

#### Production

```bash
# .env.production
LOG_LEVEL=INFO
ENVIRONMENT=production
AUTH_REQUIRE_AUTH=true
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
WORKER_CONCURRENCY=10
REDIS_MAX_CONNECTIONS=100
```

## Database Setup

### Initial Setup

```bash
# Initialize database
make db-init

# Run all migrations
make db-upgrade

# Verify current version
make db-current
```

### Creating Migrations

```bash
# Create new migration
make db-create MESSAGE="add new feature"

# Review generated migration in alembic/versions/

# Apply migration
make db-upgrade
```

### Rollback

```bash
# Rollback one version
make db-downgrade REV=-1

# Rollback to specific version
make db-downgrade REV=abc123

# Rollback to base (WARNING: deletes all data)
make db-downgrade REV=base
```

### Backup & Restore

#### Backup

```bash
# Backup entire database
pg_dump -h localhost -U contextiq contextiq > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific tables
pg_dump -h localhost -U contextiq -t sessions -t memories contextiq > backup.sql
```

#### Restore

```bash
# Restore from backup
psql -h localhost -U contextiq contextiq < backup.sql

# Or using Docker
docker-compose exec -T postgres psql -U contextiq contextiq < backup.sql
```

### Database Maintenance

```bash
# Vacuum database
psql -h localhost -U contextiq -d contextiq -c "VACUUM ANALYZE;"

# Check database size
psql -h localhost -U contextiq -d contextiq -c "
SELECT
    pg_size_pretty(pg_database_size('contextiq')) as size;
"

# Check table sizes
psql -h localhost -U contextiq -d contextiq -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## Service Health Checks

### Health Check Endpoints

All services expose health check endpoints:

```bash
# API Gateway
curl http://localhost:8000/health

# Sessions Service
curl http://localhost:8001/health

# Memory Service
curl http://localhost:8002/health

# Aggregate health check
curl http://localhost:8000/health/services
```

### Docker Health Checks

Health checks are configured in `docker-compose.yml`:

```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U contextiq"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Check service health:
```bash
docker-compose ps
```

### Monitoring Scripts

Create a monitoring script:

```bash
#!/bin/bash
# health_check.sh

check_service() {
    local name=$1
    local url=$2

    if curl -sf "$url" > /dev/null; then
        echo "✓ $name is healthy"
        return 0
    else
        echo "✗ $name is unhealthy"
        return 1
    fi
}

check_service "API Gateway" "http://localhost:8000/health"
check_service "Sessions Service" "http://localhost:8001/health"
check_service "Memory Service" "http://localhost:8002/health"
check_service "RabbitMQ" "http://localhost:15672"
check_service "Qdrant" "http://localhost:6333/health"
```

Run periodically:
```bash
chmod +x health_check.sh
watch -n 30 ./health_check.sh
```

## Monitoring & Observability

### Prometheus Metrics

Metrics are exposed on `/metrics` endpoints:

```bash
# API Gateway metrics
curl http://localhost:8000/metrics

# Sessions Service metrics
curl http://localhost:8001/metrics

# Memory Service metrics
curl http://localhost:8002/metrics
```

### Example Metrics

```
# HTTP request count
http_requests_total{service="api-gateway",method="GET",endpoint="/health",status_code="200"} 1234

# Request duration
http_request_duration_seconds_bucket{service="sessions",method="POST",endpoint="/sessions",le="0.1"} 890

# Database operations
db_operations_total{service="memory",operation="insert",table="memories",status="success"} 567
```

### Setting Up Prometheus

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'contextiq-api-gateway'
    static_configs:
      - targets: ['localhost:8000']

  - job_name: 'contextiq-sessions'
    static_configs:
      - targets: ['localhost:8001']

  - job_name: 'contextiq-memory'
    static_configs:
      - targets: ['localhost:8002']
```

Run Prometheus:
```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

Access at: http://localhost:9090

### Grafana Dashboards

Run Grafana:
```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana
```

1. Access: http://localhost:3000 (admin/admin)
2. Add Prometheus data source: http://prometheus:9090
3. Import dashboard or create custom dashboards

### Logging

View logs:

```bash
# All services
make docker-logs

# Specific service
docker-compose logs -f memory-service

# With timestamps
docker-compose logs -f --timestamps memory-service

# Last N lines
docker-compose logs --tail=100 memory-service
```

Logs are structured JSON:
```json
{
  "timestamp": "2025-12-11T10:30:00Z",
  "level": "INFO",
  "service": "memory-service",
  "message": "Memory generated",
  "user_id": "user_123",
  "duration_ms": 1234
}
```

### Distributed Tracing

OpenTelemetry traces are automatically generated. To collect them:

1. Run Jaeger:
```bash
docker run -d \
  --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest
```

2. Configure services:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

3. Access Jaeger UI: http://localhost:16686

## Production Considerations

### Security

#### 1. Enable Authentication

```bash
# Generate secure JWT secret
python scripts/generate_auth_config.py

# Set in .env
AUTH_REQUIRE_AUTH=true
AUTH_JWT_SECRET_KEY=<generated-secret>
```

#### 2. Use HTTPS

Use a reverse proxy (nginx, Traefik) for TLS termination:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3. Network Security

```bash
# Bind PostgreSQL to localhost only
DATABASE_HOST=127.0.0.1

# Use private networks in Docker
# See docker-compose.yml networks section

# Firewall rules (UFW example)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Block external database access
```

#### 4. Secrets Management

Don't commit `.env` files. Use:
- Environment variables in production
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets

### Performance

#### 1. Connection Pooling

```bash
# Increase pool size for production
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

REDIS_MAX_CONNECTIONS=100
```

#### 2. Worker Scaling

```bash
# Increase worker concurrency
WORKER_CONCURRENCY=10
WORKER_PREFETCH_COUNT=20
```

#### 3. Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_memories_scope ON memories USING gin(scope);
CREATE INDEX idx_memories_created_at ON memories(created_at);

-- Enable query optimization
ANALYZE sessions;
ANALYZE memories;
```

### High Availability

#### 1. Database Replication

Set up PostgreSQL streaming replication:

```bash
# Primary server
pg_ctl -D /var/lib/postgresql/data -l logfile start

# Replica server
pg_basebackup -h primary -D /var/lib/postgresql/data -U replication -Fp -Xs -P -R
```

#### 2. Redis Cluster

Use Redis Sentinel or Cluster mode for HA.

#### 3. Load Balancing

Use nginx or HAProxy:

```nginx
upstream contextiq_backend {
    least_conn;
    server localhost:8000 max_fails=3 fail_timeout=30s;
    server localhost:8001 max_fails=3 fail_timeout=30s;
    server localhost:8002 max_fails=3 fail_timeout=30s;
}
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Daily backup script

DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups

# Database backup
pg_dump -h localhost -U contextiq contextiq > $BACKUP_DIR/db_$DATE.sql
gzip $BACKUP_DIR/db_$DATE.sql

# Qdrant backup
curl -X POST http://localhost:6333/collections/memories/snapshots > $BACKUP_DIR/qdrant_$DATE.snapshot

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.snapshot" -mtime +30 -delete
```

Schedule with cron:
```bash
0 2 * * * /path/to/backup.sh
```

## Troubleshooting

### Service Won't Start

**Check logs**:
```bash
docker-compose logs <service-name>
```

**Common issues**:
- Port already in use: Change port in `.env`
- Database connection failed: Check `DATABASE_URL`
- Missing API key: Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

### Database Connection Errors

```bash
# Test connection
psql -h localhost -U contextiq -d contextiq

# Check if database exists
psql -h localhost -U contextiq -l

# Recreate database
dropdb -h localhost -U contextiq contextiq
createdb -h localhost -U contextiq contextiq
make db-init
make db-upgrade
```

### Memory Service Not Processing Jobs

**Check RabbitMQ**:
```bash
# RabbitMQ management UI
open http://localhost:15672

# Check queue depth
docker-compose exec rabbitmq rabbitmqctl list_queues
```

**Check worker logs**:
```bash
docker-compose logs -f memory-generation-worker
docker-compose logs -f consolidation-worker
```

**Restart workers**:
```bash
docker-compose restart memory-generation-worker consolidation-worker
```

### High Memory Usage

**Check Docker stats**:
```bash
docker stats
```

**Limit container memory**:
```yaml
services:
  memory-service:
    mem_limit: 1g
    mem_reservation: 512m
```

**Optimize database**:
```bash
# Vacuum database
docker-compose exec postgres psql -U contextiq -d contextiq -c "VACUUM FULL;"
```

### Slow API Responses

**Check metrics**:
```bash
curl http://localhost:8000/metrics | grep http_request_duration
```

**Enable query logging**:
```bash
# In .env
LOG_LEVEL=DEBUG
```

**Check database performance**:
```sql
-- Slow query log
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Reset Everything

```bash
# Stop all services
make docker-down

# Remove all data (WARNING: destructive)
make docker-clean

# Start fresh
make dev
```

## References

- [Architecture Overview](ARCHITECTURE.md)
- [Database Migrations Guide](DATABASE_MIGRATIONS.md)
- [Authentication Guide](AUTHENTICATION.md)
- [API Usage Guide](API_USAGE.md)
- [Development Guide](DEVELOPMENT.md)
