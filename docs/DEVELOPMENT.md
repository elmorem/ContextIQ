# Development Guide

This guide covers everything you need to know to develop ContextIQ effectively.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Code Quality Tools](#code-quality-tools)
- [Testing Strategy](#testing-strategy)
- [Makefile Commands Reference](#makefile-commands-reference)
- [Git Workflow](#git-workflow)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Adding New Features](#adding-new-features)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)

## Development Environment Setup

### Prerequisites

- **Python 3.11+**: Required for all services
- **Docker & Docker Compose**: For running infrastructure
- **uv**: Fast Python package manager ([installation](https://github.com/astral-sh/uv))
- **Make**: For convenient command shortcuts
- **Git**: Version control

### Initial Setup

1. **Clone and install dependencies**:
   ```bash
   git clone https://github.com/yourusername/contextiq.git
   cd contextiq
   make setup
   ```

   This runs:
   - `make dev-install` - Installs all development dependencies
   - `make pre-commit-install` - Sets up pre-commit hooks

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure:
   ```bash
   # Database
   DATABASE_URL=postgresql+asyncpg://contextiq:contextiq_dev_password@localhost:5432/contextiq

   # Authentication (disabled by default for development)
   AUTH_REQUIRE_AUTH=false
   AUTH_JWT_SECRET_KEY=dev-secret-change-in-production

   # LLM API Keys (optional for development)
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Start development environment**:
   ```bash
   make dev
   ```

   This starts:
   - PostgreSQL (port 5432)
   - Redis (port 6379)
   - RabbitMQ (port 5672, management UI on 15672)
   - Qdrant (port 6333)
   - All microservices

   And runs:
   - Database migrations
   - Qdrant collection initialization
   - RabbitMQ queue initialization

4. **Verify setup**:
   ```bash
   make services-health
   ```

### IDE Setup

#### VS Code

Recommended extensions:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "ms-azuretools.vscode-docker"
  ]
}
```

Settings (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.analysis.typeCheckingMode": "basic"
}
```

## Project Structure

```
ContextIQ/
├── services/                   # All microservices
│   ├── gateway/               # API Gateway
│   │   └── app/
│   │       ├── main.py       # FastAPI app
│   │       └── ...
│   ├── sessions/              # Sessions Service
│   │   ├── app/
│   │   │   ├── api/          # API endpoints
│   │   │   ├── core/         # Business logic
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   └── main.py
│   │   └── tests/            # Service-specific tests
│   ├── memory/                # Memory Service
│   │   ├── app/
│   │   └── tests/
│   └── workers/               # Background workers
│       ├── memory_generation/
│       └── consolidation/
├── shared/                    # Shared code across services
│   ├── auth/                 # Authentication utilities
│   │   ├── jwt.py
│   │   ├── api_key.py
│   │   ├── middleware.py
│   │   └── ...
│   ├── config/               # Configuration utilities
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── ...
│   ├── observability/        # Metrics and tracing
│   │   ├── metrics.py
│   │   ├── tracing.py
│   │   └── middleware.py
│   └── models/               # Shared Pydantic models
├── tests/                     # Integration tests
│   ├── conftest.py
│   └── integration/
├── scripts/                   # Utility scripts
│   ├── db_init.py            # Database initialization
│   ├── db_migrate.py         # Migration management
│   └── generate_auth_config.py
├── alembic/                   # Database migrations
│   ├── versions/
│   └── env.py
├── docs/                      # Documentation
└── docker-compose.yml         # Development orchestration
```

### Service Structure

Each service follows this pattern:

```
service_name/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application
│   ├── api/                  # API routes
│   │   ├── __init__.py
│   │   ├── health.py         # Health check endpoints
│   │   └── v1/               # API version
│   │       └── resource.py   # Resource endpoints
│   ├── core/                 # Business logic
│   │   ├── __init__.py
│   │   ├── config.py         # Service configuration
│   │   ├── dependencies.py   # Dependency injection
│   │   └── service.py        # Service layer
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   └── resource.py       # SQLAlchemy models
│   └── schemas/              # Pydantic schemas
│       ├── __init__.py
│       └── resource.py       # Request/response models
└── tests/
    ├── __init__.py
    ├── conftest.py           # Test fixtures
    └── test_resource.py      # Tests
```

## Code Quality Tools

### Black (Code Formatting)

Format all code:
```bash
make format
```

Format specific files:
```bash
black services/sessions/app/main.py
```

Configuration (`.pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

### Ruff (Linting)

Lint all code:
```bash
make lint
```

Auto-fix issues:
```bash
ruff check --fix services/ shared/
```

Configuration (`.ruff.toml`):
```toml
line-length = 100
target-version = "py311"
```

### mypy (Type Checking)

Type check all code:
```bash
make type-check
```

Type check specific service:
```bash
mypy services/sessions/
```

Configuration (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### Run All Checks

```bash
make check  # Runs format + lint + type-check + test
```

## Testing Strategy

### Test Structure

```
tests/
├── unit/                     # Unit tests (fast, no external dependencies)
├── integration/              # Integration tests (database, Redis, etc.)
└── e2e/                      # End-to-end tests (full system)
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# With coverage
make test-cov
```

### Writing Tests

**Unit Test Example**:
```python
# tests/unit/test_memory_service.py
import pytest
from services.memory.app.core.service import MemoryService

def test_memory_validation():
    service = MemoryService()
    result = service.validate_memory_fact("User likes coffee")
    assert result.is_valid
```

**Integration Test Example**:
```python
# tests/integration/test_sessions_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_create_session(client: AsyncClient):
    response = await client.post(
        "/api/v1/sessions",
        json={"user_id": "user_123", "agent_id": "test_agent"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "user_123"
```

### Test Fixtures

Define reusable fixtures in `conftest.py`:
```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from services.sessions.app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

## Makefile Commands Reference

### Environment Setup
- `make install` - Install production dependencies
- `make dev-install` - Install development dependencies
- `make clean` - Clean cache and temporary files
- `make setup` - Complete development setup

### Code Quality
- `make format` - Format code with Black and Ruff
- `make lint` - Run linting checks
- `make type-check` - Run type checking with mypy
- `make check` - Run all quality checks

### Testing
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only
- `make test-cov` - Run tests with coverage report

### Docker
- `make docker-build` - Build all Docker images
- `make docker-up` - Start all services
- `make docker-down` - Stop all services
- `make docker-logs` - Show logs from all services
- `make docker-clean` - Stop services and remove volumes

### Database
- `make db-init` - Initialize database and extensions
- `make db-create MESSAGE="..."` - Create new migration
- `make db-upgrade` - Upgrade to latest schema
- `make db-downgrade REV=...` - Downgrade to specific revision
- `make db-current` - Show current schema version
- `make db-history` - Show migration history
- `make db-reset` - Reset database schema

### Services
- `make run-sessions` - Run Sessions service locally
- `make run-memory` - Run Memory service locally
- `make run-gateway` - Run API Gateway locally
- `make run-workers` - Run background workers locally
- `make services-health` - Check service health

### Quick Commands
- `make dev` - Start complete development environment
- `make qdrant-init` - Initialize Qdrant collections
- `make rabbitmq-init` - Initialize RabbitMQ queues

## Git Workflow

### Branch Naming

- `feat/feature-name` - New features
- `fix/bug-description` - Bug fixes
- `docs/documentation-updates` - Documentation changes
- `refactor/code-cleanup` - Code refactoring
- `test/test-coverage` - Test additions

### Commit Messages

Follow conventional commits:
```
feat: Add memory consolidation worker
fix: Fix session expiration logic
docs: Update API usage guide
refactor: Extract authentication middleware
test: Add integration tests for sessions API
```

### Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "feat: Add my feature"
   ```

   Pre-commit hooks will run automatically and:
   - Format code with Black
   - Lint with Ruff
   - Check types with mypy

3. **Run quality checks**:
   ```bash
   make check
   ```

4. **Push and create PR**:
   ```bash
   git push -u origin feat/my-feature
   gh pr create
   ```

## Pre-commit Hooks

### Installation

```bash
make pre-commit-install
```

### Configuration

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Running Manually

```bash
# Run on all files
make pre-commit-run

# Run on staged files
pre-commit run
```

## Adding New Features

### Adding a New Endpoint

1. **Define schema** (`app/schemas/resource.py`):
   ```python
   from pydantic import BaseModel

   class CreateResourceRequest(BaseModel):
       name: str
       description: str | None = None

   class ResourceResponse(BaseModel):
       id: str
       name: str
       created_at: datetime
   ```

2. **Create route** (`app/api/v1/resources.py`):
   ```python
   from fastapi import APIRouter, Depends
   from app.schemas.resource import CreateResourceRequest, ResourceResponse
   from app.core.service import ResourceService

   router = APIRouter(prefix="/resources", tags=["resources"])

   @router.post("/", response_model=ResourceResponse)
   async def create_resource(
       request: CreateResourceRequest,
       service: ResourceService = Depends(get_service),
   ):
       resource = await service.create(request)
       return ResourceResponse.model_validate(resource)
   ```

3. **Implement service** (`app/core/service.py`):
   ```python
   class ResourceService:
       async def create(self, request: CreateResourceRequest):
           # Business logic here
           return resource
   ```

4. **Add tests** (`tests/test_resources.py`):
   ```python
   async def test_create_resource(client: AsyncClient):
       response = await client.post(
           "/api/v1/resources",
           json={"name": "Test Resource"}
       )
       assert response.status_code == 201
   ```

### Adding a New Service

1. **Create service directory**:
   ```bash
   mkdir -p services/new_service/app/api/v1
   mkdir -p services/new_service/app/core
   mkdir -p services/new_service/tests
   ```

2. **Create main application** (`app/main.py`):
   ```python
   from fastapi import FastAPI
   from app.api.v1 import router

   app = FastAPI(title="New Service")
   app.include_router(router, prefix="/api/v1")
   ```

3. **Add to docker-compose.yml**:
   ```yaml
   new-service:
     build: ./services/new_service
     ports:
       - "8004:8004"
     environment:
       - DATABASE_URL=${DATABASE_URL}
   ```

4. **Add Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY . .
   RUN pip install -e .
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
   ```

## Debugging

### Local Debugging

**VS Code launch.json**:
```json
{
  "configurations": [
    {
      "name": "Sessions Service",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "services.sessions.app.main:app",
        "--reload",
        "--port", "8001"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

### Docker Debugging

View logs:
```bash
# All services
make docker-logs

# Specific service
docker-compose logs -f sessions-service

# Last 100 lines
docker-compose logs --tail=100 sessions-service
```

Connect to running container:
```bash
docker-compose exec sessions-service bash
```

### Database Debugging

Connect to PostgreSQL:
```bash
docker-compose exec postgres psql -U contextiq -d contextiq
```

View tables:
```sql
\dt
```

Query data:
```sql
SELECT * FROM sessions LIMIT 10;
```

## Common Tasks

### Update Dependencies

```bash
# Update all dependencies
uv pip compile --upgrade -o requirements.txt pyproject.toml

# Install updated dependencies
make dev-install
```

### Create Database Migration

```bash
# After modifying SQLAlchemy models
make db-create MESSAGE="add new column to sessions"

# Review generated migration
# Edit if needed: alembic/versions/YYYYMMDD_HHMM_<rev>_<slug>.py

# Apply migration
make db-upgrade
```

### Add New Environment Variable

1. Add to `.env.example`:
   ```bash
   NEW_SETTING=default_value
   ```

2. Add to configuration class:
   ```python
   # shared/config/settings.py
   class Settings(BaseSettings):
       new_setting: str = Field(default="default_value")
   ```

3. Document in relevant guide

### Reset Development Environment

```bash
# Stop everything
make docker-down

# Clean volumes
make docker-clean

# Restart fresh
make dev
```

### Generate API Documentation

```bash
# Services auto-generate OpenAPI docs at /docs
# Visit: http://localhost:8000/docs (Gateway)
#        http://localhost:8001/docs (Sessions)
#        http://localhost:8002/docs (Memory)
```

## Performance Profiling

### Using py-spy

```bash
# Profile running service
py-spy record -o profile.svg -- python -m uvicorn app.main:app

# Top view
py-spy top -- python -m uvicorn app.main:app
```

### Database Query Profiling

Enable query logging:
```python
# In database settings
echo_pool = True
echo = True
```

## Security Best Practices

1. **Never commit secrets**:
   - Use `.env` files (gitignored)
   - Use environment variables
   - Use secrets managers in production

2. **Always validate input**:
   - Use Pydantic for request validation
   - Sanitize database queries
   - Validate file uploads

3. **Use authentication**:
   - Enable `AUTH_REQUIRE_AUTH=true` in production
   - Rotate JWT secrets regularly
   - Use strong API keys

4. **Keep dependencies updated**:
   ```bash
   uv pip list --outdated
   ```

## Getting Help

- **Documentation**: [docs/](../docs/)
- **GitHub Issues**: [github.com/yourusername/contextiq/issues](https://github.com/yourusername/contextiq/issues)
- **Discussions**: [github.com/yourusername/contextiq/discussions](https://github.com/yourusername/contextiq/discussions)

## Additional Resources

- [Authentication Guide](AUTHENTICATION.md)
- [Database Migrations Guide](DATABASE_MIGRATIONS.md)
- [API Usage Guide](API_USAGE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Architecture Overview](ARCHITECTURE.md)
