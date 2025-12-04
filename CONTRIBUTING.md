# Contributing to ContextIQ

Thank you for your interest in contributing to ContextIQ! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Issue Guidelines](#issue-guidelines)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and collaborative environment. We expect all contributors to:

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Make
- Git

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/contextiq.git
   cd contextiq
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original/contextiq.git
   ```

4. **Install dependencies**:
   ```bash
   make setup
   ```
   This will:
   - Install development dependencies
   - Install pre-commit hooks
   - Set up the development environment

5. **Copy environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Start development environment**:
   ```bash
   make dev
   ```

7. **Verify everything works**:
   ```bash
   make check
   ```

## Development Workflow

### 1. Create a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feat/your-feature-name
```

Branch naming conventions:
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements
- `chore/` - Maintenance tasks

### 2. Make Your Changes

- Write clean, readable code
- Follow the [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
make type-check

# Run tests
make test

# Run all checks
make check
```

### 4. Commit Your Changes

We use conventional commits. Format your commit messages as:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/improvements
- `chore`: Maintenance tasks

**Example**:
```
feat(memory): add similarity search endpoint

Implement similarity search for memories using Qdrant vector store.
Includes scope-based filtering and top-k results.

Closes #123
```

**Commit with pre-commit hooks**:
```bash
git add .
git commit -m "feat(memory): add similarity search endpoint"
```

Pre-commit hooks will automatically:
- Format code with Black
- Lint with Ruff
- Check types with mypy
- Validate YAML files

### 5. Keep Your Branch Updated

Regularly sync with upstream:

```bash
git fetch upstream
git rebase upstream/main
```

### 6. Push Your Changes

```bash
git push origin feat/your-feature-name
```

## Pull Request Process

### 1. Create a Pull Request

- Go to GitHub and create a PR from your fork
- Use the PR template provided
- Fill in all relevant sections
- Link related issues

### 2. PR Checklist

Ensure your PR meets these requirements:

- [ ] Code follows style guidelines (`make format` passed)
- [ ] Linting passes (`make lint` passed)
- [ ] Type checking passes (`make type-check` passed)
- [ ] All tests pass (`make test` passed)
- [ ] Test coverage >80% for new code
- [ ] Documentation updated
- [ ] Docstrings added for public APIs
- [ ] No sensitive information committed
- [ ] `DEVELOPMENT_PLAN.md` updated (if scope changed)

### 3. CI/CD Checks

All PRs must pass automated checks:
- ✅ Linting (Ruff)
- ✅ Type checking (mypy)
- ✅ Tests (pytest with coverage)
- ✅ Security scan (Bandit)
- ✅ Docker builds (if applicable)

### 4. Code Review

- Address reviewer comments promptly
- Push updates to the same branch
- Request re-review after changes
- Be open to feedback and suggestions

### 5. Merging

- PRs require at least 1 approval
- All CI checks must pass
- No unresolved conversations
- Branch must be up-to-date with main

## Coding Standards

### Python Style

We use **Black** for formatting and **Ruff** for linting:

```bash
# Format code
make format

# Check linting
make lint
```

**Key guidelines**:
- Line length: 100 characters
- Use type hints for all functions
- Write docstrings for public APIs (Google style)
- Use meaningful variable names
- Keep functions focused and small

### Type Hints

All code must include type hints:

```python
from typing import Dict, List, Optional

def create_memory(
    scope: Dict[str, str],
    fact: str,
    confidence: float = 1.0
) -> Memory:
    """
    Create a new memory.

    Args:
        scope: Memory scope dictionary
        fact: Memory fact in first person
        confidence: Confidence score (0.0 to 1.0)

    Returns:
        Created memory object

    Raises:
        ValidationError: If scope or fact is invalid
    """
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    Longer description if needed. Explain the purpose,
    behavior, and any important details.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
        KeyError: When param1 not found

    Examples:
        >>> function_name("test", 5)
        True
    """
    ...
```

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log errors with context
- Don't catch exceptions silently

```python
from shared.exceptions import ValidationError

def validate_scope(scope: Dict[str, str]) -> None:
    """Validate memory scope."""
    if len(scope) > 5:
        raise ValidationError(
            f"Scope can have maximum 5 keys, got {len(scope)}"
        )
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                  # Unit tests
│   └── services/
│       └── test_memory_service.py
├── integration/           # Integration tests
│   └── api/
│       └── test_memory_api.py
└── e2e/                  # End-to-end tests
    └── test_memory_generation_flow.py
```

### Writing Tests

**Unit Tests**:
```python
import pytest
from services.memory.app.services.memory_service import MemoryService

@pytest.mark.unit
def test_create_memory():
    """Test memory creation."""
    service = MemoryService()
    memory = service.create_memory(
        scope={"user_id": "123"},
        fact="Test fact"
    )
    assert memory.fact == "Test fact"
    assert memory.scope == {"user_id": "123"}
```

**Integration Tests**:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_memory_endpoint(client: AsyncClient):
    """Test POST /api/v1/memories endpoint."""
    response = await client.post(
        "/api/v1/memories",
        json={
            "scope": {"user_id": "123"},
            "fact": "Test fact"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["fact"] == "Test fact"
```

### Test Coverage

- Aim for >80% coverage on new code
- Test happy paths and error cases
- Test edge cases and boundary conditions
- Mock external dependencies

```bash
# Run tests with coverage
make test-cov

# View coverage report
open htmlcov/index.html
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow-running test
@pytest.mark.asyncio       # Async test
```

Run specific test categories:
```bash
pytest -m unit            # Run only unit tests
pytest -m "not slow"      # Skip slow tests
```

## Documentation

### Code Documentation

- Docstrings for all public APIs
- Inline comments for complex logic
- Type hints for all functions
- README updates for new features

### Architecture Documentation

Update relevant docs in `docs/`:
- `docs/architecture/` - Architecture changes
- `docs/api/` - API documentation
- `docs/guides/` - User guides
- `DEVELOPMENT_PLAN.md` - Plan updates

### API Documentation

We use FastAPI's automatic OpenAPI generation:
- Document all endpoints with docstrings
- Define request/response models with Pydantic
- Include examples in schema definitions

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

class CreateMemoryRequest(BaseModel):
    """Request model for creating a memory."""
    scope: Dict[str, str] = Field(
        ...,
        description="Memory scope (max 5 key-value pairs)",
        example={"user_id": "123"}
    )
    fact: str = Field(
        ...,
        description="Memory fact in first person",
        example="I prefer dark mode interfaces"
    )

@router.post("/memories", response_model=Memory)
async def create_memory(request: CreateMemoryRequest):
    """
    Create a new memory.

    Creates a memory directly without extraction or consolidation.
    The memory will be stored with the provided scope and fact.
    """
    ...
```

## Issue Guidelines

### Reporting Bugs

Use the **Bug Report** template and include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Logs and error messages
- Screenshots if applicable

### Requesting Features

Use the **Feature Request** template and include:
- Clear description of the feature
- Problem it solves
- Proposed solution
- Use cases and examples
- Technical considerations

### Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `question` - Further information requested
- `priority:high` - High priority
- `priority:low` - Low priority

## Development Best Practices

### Security

- Never commit API keys, passwords, or secrets
- Use environment variables for configuration
- Validate all user inputs
- Sanitize data before storage
- Review code for security vulnerabilities

### Performance

- Optimize database queries
- Use async operations where appropriate
- Implement caching strategically
- Profile code for bottlenecks
- Consider scalability

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Log errors with context
- Return appropriate HTTP status codes

### Logging

Use structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "memory_created",
    memory_id=memory.id,
    scope=memory.scope,
    user_id=memory.scope.get("user_id")
)
```

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and discussions
- **Documentation**: Check docs/ directory
- **Development Plan**: See DEVELOPMENT_PLAN.md

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes
- Project documentation

Thank you for contributing to ContextIQ! 🎉
