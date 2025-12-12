# ContextIQ Documentation

Welcome to the ContextIQ documentation! This guide will help you understand, deploy, and develop with ContextIQ.

## Table of Contents

### Getting Started

- **[Main README](../README.md)** - Project overview and quick start
- **[Architecture Overview](ARCHITECTURE.md)** - System design and components
- **[API Usage Guide](API_USAGE.md)** - How to use the ContextIQ APIs

### Deployment & Operations

- **[Deployment Guide](DEPLOYMENT.md)** - Local, Docker, and production deployment
- **[Database Migrations](DATABASE_MIGRATIONS.md)** - Managing schema changes with Alembic
- **[Authentication Guide](AUTHENTICATION.md)** - JWT tokens, API keys, and permissions

### Development

- **[Development Guide](DEVELOPMENT.md)** - Setting up your development environment
- **[System Architecture](architecture/system_architecture.md)** - Detailed architecture documentation
- **[Data Models](architecture/data_models.md)** - Database schemas and models

### Technical Deep Dives

- **[Embeddings Guide](EMBEDDINGS.md)** - Text embeddings with OpenAI (models, configuration, optimization)
- **[Vector Search Guide](VECTOR_SEARCH.md)** - Qdrant vector database and similarity search

### Research & Background

- **[Agent Engine Memory Bank Research](agent_engine_memory_bank_research.md)** - Research notes on Google's approach
- **[Context Engineering Paper Summary](paper_summary.md)** - Summary of Google's Sessions & Memory whitepaper
- **[Anthropic Context Engineering](anthropic_context_engineering.md)** - Anthropic's perspective on context engineering

## Quick Links by Use Case

### I want to...

**...get started quickly**
1. Read the [Main README](../README.md) Quick Start section
2. Follow the [Deployment Guide](DEPLOYMENT.md) for local setup
3. Review [API Usage Guide](API_USAGE.md) for first API calls

**...deploy to production**
1. Read the [Deployment Guide](DEPLOYMENT.md) Production section
2. Configure [Authentication](AUTHENTICATION.md) properly
3. Set up [Database Migrations](DATABASE_MIGRATIONS.md) workflow

**...contribute code**
1. Follow the [Development Guide](DEVELOPMENT.md) setup
2. Understand the [Architecture](ARCHITECTURE.md)
3. Review code quality standards in [Development Guide](DEVELOPMENT.md)

**...integrate with my AI agent**
1. Review [API Usage Guide](API_USAGE.md) for authentication
2. See [Sessions API examples](API_USAGE.md#sessions-api)
3. See [Memory API examples](API_USAGE.md#memory-api)

**...understand the system design**

1. Read [Architecture Overview](ARCHITECTURE.md)
2. Review [System Architecture](architecture/system_architecture.md) details
3. Study [Data Models](architecture/data_models.md)

**...understand embeddings and vector search**

1. Read [Embeddings Guide](EMBEDDINGS.md) for text embedding details
2. Read [Vector Search Guide](VECTOR_SEARCH.md) for similarity search
3. Review [API Usage Guide](API_USAGE.md) for memory search examples

**...manage database changes**

1. Read [Database Migrations Guide](DATABASE_MIGRATIONS.md)
2. Learn migration commands and patterns
3. Understand production migration strategies

**...configure authentication**
1. Read [Authentication Guide](AUTHENTICATION.md)
2. Generate JWT secrets and API keys
3. Configure middleware in your services

## Documentation Structure

### Core Documentation
Files in the `docs/` root directory cover essential topics:
- Architecture, API usage, deployment, development
- Authentication, database migrations
- Research and background materials

### Architecture Details
The `docs/architecture/` directory contains detailed technical documentation:
- System architecture diagrams and explanations
- Data models and database schemas
- Design decisions and rationale

### PR Summaries
The `docs/pr_summaries/` directory contains:
- Summaries of major pull requests
- Implementation notes
- Migration guides for breaking changes

## Contributing to Documentation

When updating documentation:

1. **Keep it up to date**: Update docs when code changes
2. **Cross-reference**: Link to related documentation
3. **Use examples**: Show code examples where relevant
4. **Be comprehensive**: Cover common use cases and edge cases
5. **Follow markdown best practices**: Use headers, code blocks, lists

### Documentation Standards

- Use clear, concise language
- Include a table of contents for documents > 200 lines
- Use code blocks with language hints (```python, ```bash)
- Link to other docs using relative paths
- Keep line length reasonable (100-120 characters)
- Use meaningful heading hierarchy (# → ## → ###)

## Getting Help

If you can't find what you're looking for:

1. Search existing documentation
2. Check [GitHub Issues](https://github.com/yourusername/contextiq/issues)
3. Ask in [GitHub Discussions](https://github.com/yourusername/contextiq/discussions)
4. Review the code - it's well-commented!

## Documentation Roadmap

Planned documentation additions:

- [ ] Performance tuning guide
- [ ] Monitoring and observability setup guide
- [ ] Troubleshooting guide with common issues
- [ ] Integration guides for popular frameworks (LangGraph, CrewAI, etc.)
- [ ] API client SDK documentation (Python, TypeScript)
- [ ] Advanced deployment patterns (K8s, multi-region, etc.)
- [ ] Security best practices guide
- [ ] Backup and disaster recovery guide

---

**Last Updated**: December 2024

For questions or suggestions about documentation, please open an issue on GitHub.
