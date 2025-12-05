"""
Integration tests for health check endpoints.

Tests health endpoints with real FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.memory.app.main import create_app
from shared.database.base import Base
from shared.database.session import get_db_session

# Skip all tests if database is not available
pytestmark = pytest.mark.integration


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "postgresql+asyncpg://contextiq_user:contextiq_pass@localhost:5432/contextiq",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    app = create_app()

    # Override database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_correct_structure(self, client):
        """Test health endpoint returns correct data structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_status_is_healthy(self, client):
        """Test health status is healthy."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "memory"
        assert data["version"] == "0.1.0"


class TestDetailedHealthEndpoint:
    """Tests for /health/detailed endpoint."""

    def test_detailed_health_returns_200(self, client):
        """Test detailed health endpoint returns 200 OK."""
        response = client.get("/health/detailed")

        assert response.status_code == 200

    def test_detailed_health_returns_correct_structure(self, client):
        """Test detailed health endpoint returns correct structure."""
        response = client.get("/health/detailed")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data
        assert "database" in data
        assert "redis" in data

    def test_detailed_health_checks_database(self, client):
        """Test detailed health checks database connectivity."""
        response = client.get("/health/detailed")
        data = response.json()

        assert data["database"] in ["healthy", "unhealthy"]


class TestReadinessEndpoint:
    """Tests for /health/ready endpoint."""

    def test_ready_returns_200(self, client):
        """Test readiness endpoint returns 200 when ready."""
        response = client.get("/health/ready")

        assert response.status_code == 200

    def test_ready_returns_correct_structure(self, client):
        """Test readiness endpoint returns correct structure."""
        response = client.get("/health/ready")
        data = response.json()

        assert "status" in data
        assert data["status"] == "ready"


class TestLivenessEndpoint:
    """Tests for /health/live endpoint."""

    def test_live_returns_200(self, client):
        """Test liveness endpoint returns 200."""
        response = client.get("/health/live")

        assert response.status_code == 200

    def test_live_returns_correct_structure(self, client):
        """Test liveness endpoint returns correct structure."""
        response = client.get("/health/live")
        data = response.json()

        assert "status" in data
        assert data["status"] == "alive"
