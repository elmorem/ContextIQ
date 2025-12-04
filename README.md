# ContextIQ

**Context engineering engine for AI agents with Sessions and Memory management**

ContextIQ is an open-source, production-ready context engineering platform that provides persistent memory and session management for AI agents. Built as a competitor to Google's Agent Engine Memory Bank, ContextIQ offers both declarative and procedural memory capabilities with true framework-agnostic design.

## Features

- **Sessions Management**: Chronological conversation tracking with events and state
- **Declarative Memory**: Long-term memory for user preferences, facts, and context
- **Procedural Memory**: Workflow patterns, skills, and agent learning capabilities
- **Multi-Agent Support**: Built-in coordination patterns for multi-agent systems
- **Framework Agnostic**: Direct REST APIs work with any agent framework (ADK, LangGraph, CrewAI, custom)
- **Production Ready**: Scalable architecture with observability, security, and deployment strategies

## Architecture

ContextIQ is built as a microservices architecture:

- **Sessions Service**: Manages conversation sessions, events, and temporary state
- **Memory Service**: Handles declarative memory generation, consolidation, and retrieval
- **Procedural Memory Service**: Stores workflows, skills, and agent trajectories
- **Extraction Worker**: Background worker for LLM-powered memory extraction
- **Consolidation Worker**: Background worker for memory merging and conflict resolution
- **API Gateway**: Unified entry point with routing and rate limiting

## Tech Stack

- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15+ (with Alembic migrations)
- **Vector Store**: Qdrant
- **Cache**: Redis 7+
- **Message Queue**: RabbitMQ
- **LLM Integration**: LiteLLM (supports OpenAI, Anthropic, Google, etc.)
- **Deployment**: Docker + Kubernetes

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Make (for convenience commands)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/contextiq.git
   cd contextiq
   ```

2. **Install dependencies**
   ```bash
   make dev-install
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Start development environment**
   ```bash
   make dev
   ```

   This will:
   - Start all services (PostgreSQL, Redis, Qdrant, RabbitMQ, all microservices)
   - Run database migrations
   - Initialize Qdrant collections
   - Initialize RabbitMQ queues

5. **Verify services are running**
   ```bash
   make services-health
   ```

### Services Available

Once running, you can access:

- **API Gateway**: http://localhost:8000
- **Sessions API**: http://localhost:8001
- **Memory API**: http://localhost:8002
- **Procedural Memory API**: http://localhost:8003
- **RabbitMQ Management UI**: http://localhost:15672 (user: `contextiq`, pass: `contextiq_dev_password`)
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Development

### Common Commands

```bash
# Format code (runs Black)
make format

# Run linting
make lint

# Run type checking
make type-check

# Run all tests
make test

# Run tests with coverage
make test-cov

# Run all quality checks (format + lint + type-check + test)
make check

# View logs from all services
make docker-logs

# Stop all services
make docker-down

# Clean up (removes volumes)
make docker-clean
```

### Database Migrations

```bash
# Create a new migration
make db-revision MSG="add new table"

# Run migrations
make db-migrate

# Rollback migration
make db-downgrade

# Reset database (WARNING: deletes all data)
make db-reset
```

### Running Individual Services

You can run services individually without Docker:

```bash
# Run Sessions service
make run-sessions

# Run Memory service
make run-memory

# Run Procedural Memory service
make run-procedural

# Run background workers
make run-workers

# Run API Gateway
make run-gateway
```

## Documentation

- [System Architecture](docs/architecture/system_architecture.md)
- [Data Models & Schemas](docs/architecture/data_models.md)
- [Agent Engine Memory Bank Research](docs/agent_engine_memory_bank_research.md)

## API Usage Examples

### Create a Session

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/sessions",
        json={
            "user_id": "user_123",
            "agent_id": "my_agent",
            "scope": {"user_id": "user_123", "project": "alpha"}
        }
    )
    session = response.json()
    print(f"Session created: {session['id']}")
```

### Append Event to Session

```python
response = await client.post(
    f"http://localhost:8000/api/v1/sessions/{session_id}/events",
    json={
        "author": "user",
        "invocation_id": "inv_1",
        "content": {
            "role": "user",
            "parts": [{"text": "What's the weather today?"}]
        }
    }
)
```

### Generate Memories from Session

```python
response = await client.post(
    "http://localhost:8000/api/v1/memories/generate",
    json={
        "source_type": "session",
        "source_reference": session_id,
        "scope": {"user_id": "user_123"},
        "config": {
            "wait_for_completion": False  # Async generation
        }
    }
)
job = response.json()
print(f"Memory generation job started: {job['id']}")
```

### Search Memories

```python
response = await client.post(
    "http://localhost:8000/api/v1/memories/search",
    json={
        "scope": {"user_id": "user_123"},
        "search_query": "What are the user's preferences?",
        "top_k": 5
    }
)
memories = response.json()
for memory in memories:
    print(f"- {memory['fact']} (confidence: {memory['confidence']})")
```

## Testing

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run tests with coverage report
make test-cov
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Create a feature branch
2. Make your changes
3. Run `make check` to ensure all quality checks pass
4. Commit your changes (pre-commit hooks will run automatically)
5. Push and create a pull request

### Code Quality

We use:
- **Black** for code formatting (100 character line length)
- **Ruff** for linting
- **mypy** for type checking
- **pytest** for testing

All checks run automatically via pre-commit hooks and CI/CD.

## Project Structure

```
ContextIQ/
├── services/              # Microservices
│   ├── sessions/         # Sessions service
│   ├── memory/           # Memory service
│   ├── procedural/       # Procedural memory service
│   ├── workers/          # Background workers
│   └── api-gateway/      # API gateway
├── shared/               # Shared code across services
│   ├── database/        # Database utilities
│   ├── models/          # Common Pydantic models
│   ├── cache/           # Redis utilities
│   └── messaging/       # RabbitMQ utilities
├── tests/               # Integration tests
├── docs/                # Documentation
├── scripts/             # Utility scripts
├── infrastructure/      # IaC (Terraform, K8s manifests)
└── alembic/            # Database migrations
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **GitHub Issues**: [github.com/yourusername/contextiq/issues](https://github.com/yourusername/contextiq/issues)
- **Documentation**: [docs/](docs/)
- **Discussions**: [github.com/yourusername/contextiq/discussions](https://github.com/yourusername/contextiq/discussions)

## Roadmap

- [ ] Complete Sessions Service implementation
- [ ] Complete Memory Service implementation
- [ ] Complete Procedural Memory Service implementation
- [ ] Implement background workers
- [ ] API Gateway with rate limiting
- [ ] OpenAPI/Swagger documentation
- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] ADK integration adapter
- [ ] LangGraph integration
- [ ] CrewAI integration
- [ ] Production deployment guide
- [ ] Observability dashboard
- [ ] Security audit
- [ ] Performance benchmarks
- [ ] Cloud-managed offering

## Acknowledgments

ContextIQ is inspired by Google's [Context Engineering: Sessions & Memory whitepaper](docs/Context%20Engineering_%20Sessions%20&%20Memory.pdf) and designed to compete with Vertex AI Agent Engine Memory Bank, while providing an open-source, self-hostable alternative.

---

**Built with ❤️ by the ContextIQ Team**
