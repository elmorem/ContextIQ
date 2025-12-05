"""
Integration tests for memories CRUD API endpoints.

Tests all REST API operations for memory management.
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


class TestCreateMemory:
    """Tests for POST /api/v1/memories endpoint."""

    def test_create_memory_success(self, client):
        """Test creating a memory successfully."""
        response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_123"},
                "fact": "User prefers dark mode for coding",
                "source_type": "conversation",
                "topic": "preferences",
                "confidence": 0.9,
                "importance": 0.7,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["scope"] == {"user_id": "user_123"}
        assert data["fact"] == "User prefers dark mode for coding"
        assert data["source_type"] == "conversation"
        assert data["topic"] == "preferences"
        assert data["confidence"] == 0.9
        assert data["importance"] == 0.7
        assert data["access_count"] == 0
        assert data["last_accessed_at"] is None
        assert data["deleted_at"] is None

    def test_create_memory_minimal(self, client):
        """Test creating a memory with minimal required data."""
        response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_456"},
                "fact": "User is learning Python",
                "source_type": "conversation",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["scope"] == {"user_id": "user_456"}
        assert data["fact"] == "User is learning Python"
        assert data["source_type"] == "conversation"
        assert data["topic"] is None
        assert data["embedding"] is None
        assert data["confidence"] == 0.8  # Default
        assert data["importance"] == 0.5  # Default

    def test_create_memory_with_embedding(self, client):
        """Test creating a memory with vector embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"org_id": "org_789"},
                "fact": "Company uses agile methodology",
                "source_type": "extraction",
                "embedding": embedding,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["scope"] == {"org_id": "org_789"}
        assert data["embedding"] == embedding

    def test_create_memory_with_ttl(self, client):
        """Test creating a memory with TTL."""
        response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_ttl"},
                "fact": "Temporary note",
                "source_type": "manual",
                "ttl_days": 30,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["expires_at"] is not None

    def test_create_memory_invalid_confidence(self, client):
        """Test creating a memory with invalid confidence score."""
        response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_bad"},
                "fact": "Invalid confidence",
                "source_type": "conversation",
                "confidence": 1.5,  # Exceeds max
            },
        )

        assert response.status_code == 422


class TestGetMemory:
    """Tests for GET /api/v1/memories/{memory_id} endpoint."""

    def test_get_memory_success(self, client):
        """Test retrieving a memory by ID."""
        # Create a memory first
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_get"},
                "fact": "Retrievable fact",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Get the memory
        response = client.get(f"/api/v1/memories/{memory_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == memory_id
        assert data["fact"] == "Retrievable fact"
        assert data["access_count"] == 1  # Should increment on access

    def test_get_memory_updates_access_count(self, client):
        """Test that getting a memory updates access tracking."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_access"},
                "fact": "Access tracking test",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Get the memory multiple times
        client.get(f"/api/v1/memories/{memory_id}")
        client.get(f"/api/v1/memories/{memory_id}")
        response = client.get(f"/api/v1/memories/{memory_id}")

        data = response.json()
        assert data["access_count"] == 3
        assert data["last_accessed_at"] is not None

    def test_get_memory_not_found(self, client):
        """Test retrieving a non-existent memory."""
        response = client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListMemories:
    """Tests for GET /api/v1/memories endpoint."""

    def test_list_memories_by_user_scope(self, client):
        """Test listing memories filtered by user scope."""
        # Create memories for different users
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "alice"},
                "fact": "Alice's fact",
                "source_type": "conversation",
            },
        )
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "bob"},
                "fact": "Bob's fact",
                "source_type": "conversation",
            },
        )
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "alice"},
                "fact": "Alice's second fact",
                "source_type": "conversation",
            },
        )

        response = client.get("/api/v1/memories?scope_user_id=alice")

        assert response.status_code == 200
        data = response.json()

        assert "memories" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 2

        # Should only return Alice's memories
        for memory in data["memories"]:
            assert memory["scope"]["user_id"] == "alice"

    def test_list_memories_by_org_scope(self, client):
        """Test listing memories filtered by org scope."""
        # Create memories for different orgs
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"org_id": "org_1"},
                "fact": "Org 1 fact",
                "source_type": "extraction",
            },
        )
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"org_id": "org_2"},
                "fact": "Org 2 fact",
                "source_type": "extraction",
            },
        )

        response = client.get("/api/v1/memories?scope_org_id=org_1")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["memories"][0]["scope"]["org_id"] == "org_1"

    def test_list_memories_by_topic(self, client):
        """Test listing memories filtered by topic."""
        # Create memories with different topics
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_topic"},
                "fact": "Preference fact",
                "source_type": "conversation",
                "topic": "preferences",
            },
        )
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_topic"},
                "fact": "Goal fact",
                "source_type": "conversation",
                "topic": "goals",
            },
        )
        client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_topic"},
                "fact": "Another preference",
                "source_type": "conversation",
                "topic": "preferences",
            },
        )

        response = client.get("/api/v1/memories?scope_user_id=user_topic&topic=preferences")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        for memory in data["memories"]:
            assert memory["topic"] == "preferences"

    def test_list_memories_pagination(self, client):
        """Test pagination of memory list."""
        # Create multiple memories
        for i in range(5):
            client.post(
                "/api/v1/memories",
                json={
                    "scope": {"user_id": "user_page"},
                    "fact": f"Fact {i}",
                    "source_type": "conversation",
                },
            )

        response = client.get("/api/v1/memories?scope_user_id=user_page&limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()

        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["memories"]) == 2
        assert data["total"] == 5

    def test_list_memories_requires_scope(self, client):
        """Test that listing memories requires at least one scope parameter."""
        response = client.get("/api/v1/memories")

        assert response.status_code == 400
        assert "scope parameter" in response.json()["detail"].lower()

    def test_list_memories_excludes_deleted(self, client):
        """Test that deleted memories are excluded by default."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_deleted"},
                "fact": "To be deleted",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Delete it
        client.delete(f"/api/v1/memories/{memory_id}")

        # List memories
        response = client.get("/api/v1/memories?scope_user_id=user_deleted")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_memories_includes_deleted_when_requested(self, client):
        """Test that deleted memories can be included if requested."""
        # Create and delete a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_include_deleted"},
                "fact": "Deleted fact",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]
        client.delete(f"/api/v1/memories/{memory_id}")

        # List with include_deleted=true
        response = client.get(
            "/api/v1/memories?scope_user_id=user_include_deleted&include_deleted=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["memories"][0]["deleted_at"] is not None


class TestUpdateMemory:
    """Tests for PATCH /api/v1/memories/{memory_id} endpoint."""

    def test_update_memory_fact(self, client):
        """Test updating a memory's fact."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_update"},
                "fact": "Original fact",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Update the fact
        response = client.patch(
            f"/api/v1/memories/{memory_id}",
            json={"fact": "Updated fact"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["fact"] == "Updated fact"

    def test_update_memory_topic(self, client):
        """Test updating a memory's topic."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_topic_update"},
                "fact": "Some fact",
                "source_type": "conversation",
                "topic": "old_topic",
            },
        )
        memory_id = create_response.json()["id"]

        # Update the topic
        response = client.patch(
            f"/api/v1/memories/{memory_id}",
            json={"topic": "new_topic"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "new_topic"

    def test_update_memory_confidence_and_importance(self, client):
        """Test updating confidence and importance scores."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_scores"},
                "fact": "Score test",
                "source_type": "conversation",
                "confidence": 0.5,
                "importance": 0.5,
            },
        )
        memory_id = create_response.json()["id"]

        # Update scores
        response = client.patch(
            f"/api/v1/memories/{memory_id}",
            json={"confidence": 0.95, "importance": 0.85},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["confidence"] == 0.95
        assert data["importance"] == 0.85

    def test_update_memory_with_change_reason(self, client):
        """Test updating a memory with change reason for revision tracking."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_revision"},
                "fact": "Original fact",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Update with change reason
        response = client.patch(
            f"/api/v1/memories/{memory_id}",
            json={
                "fact": "Corrected fact",
                "change_reason": "User provided correction",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["fact"] == "Corrected fact"

    def test_update_memory_not_found(self, client):
        """Test updating a non-existent memory."""
        response = client.patch(
            "/api/v1/memories/00000000-0000-0000-0000-000000000000",
            json={"fact": "New fact"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDeleteMemory:
    """Tests for DELETE /api/v1/memories/{memory_id} endpoint."""

    def test_delete_memory_success(self, client):
        """Test soft deleting a memory."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_delete"},
                "fact": "To be deleted",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Delete the memory
        response = client.delete(f"/api/v1/memories/{memory_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"].lower()

        # Verify memory is soft deleted (not returned in normal queries)
        get_response = client.get(f"/api/v1/memories/{memory_id}")
        assert get_response.status_code == 404

    def test_delete_memory_not_found(self, client):
        """Test deleting a non-existent memory."""
        response = client.delete("/api/v1/memories/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
