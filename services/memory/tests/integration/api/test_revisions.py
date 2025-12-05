"""
Integration tests for revision history API endpoints.

Tests revision tracking and retrieval functionality.
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


class TestListRevisions:
    """Tests for GET /api/v1/memories/{memory_id}/revisions endpoint."""

    def test_list_revisions_empty(self, client):
        """Test listing revisions for a memory with no revisions."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_revisions"},
                "fact": "Original fact",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # List revisions
        response = client.get(f"/api/v1/memories/{memory_id}/revisions")

        assert response.status_code == 200
        data = response.json()

        assert "revisions" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 0
        assert len(data["revisions"]) == 0

    def test_list_revisions_after_updates(self, client):
        """Test that revisions are created when memory is updated."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_revisions"},
                "fact": "First version",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Update the memory multiple times
        client.patch(
            f"/api/v1/memories/{memory_id}",
            json={
                "fact": "Second version",
                "change_reason": "First update",
            },
        )

        client.patch(
            f"/api/v1/memories/{memory_id}",
            json={
                "fact": "Third version",
                "change_reason": "Second update",
            },
        )

        # List revisions
        response = client.get(f"/api/v1/memories/{memory_id}/revisions")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["revisions"]) == 2

        # Check revisions are ordered newest first (descending revision number)
        assert data["revisions"][0]["revision_number"] == 2
        assert data["revisions"][1]["revision_number"] == 1

        # Verify revision content
        assert data["revisions"][0]["previous_fact"] == "Second version"
        assert data["revisions"][0]["new_fact"] == "Third version"
        assert data["revisions"][0]["change_reason"] == "Second update"

        assert data["revisions"][1]["previous_fact"] == "First version"
        assert data["revisions"][1]["new_fact"] == "Second version"
        assert data["revisions"][1]["change_reason"] == "First update"

    def test_list_revisions_pagination(self, client):
        """Test pagination of revision list."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_pagination"},
                "fact": "Version 0",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Create multiple revisions
        for i in range(1, 6):
            client.patch(
                f"/api/v1/memories/{memory_id}",
                json={
                    "fact": f"Version {i}",
                    "change_reason": f"Update {i}",
                },
            )

        # Test pagination with limit and offset
        response = client.get(f"/api/v1/memories/{memory_id}/revisions?limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()

        assert data["limit"] == 2
        assert data["offset"] == 1
        assert data["total"] == 5
        assert len(data["revisions"]) == 2

        # Should return revisions 4 and 3 (newest first, skipping revision 5)
        assert data["revisions"][0]["revision_number"] == 4
        assert data["revisions"][1]["revision_number"] == 3

    def test_list_revisions_respects_limit(self, client):
        """Test that limit parameter is respected."""
        # Create a memory and several revisions
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_limit"},
                "fact": "Original",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Create 5 revisions
        for i in range(5):
            client.patch(
                f"/api/v1/memories/{memory_id}",
                json={"fact": f"Update {i}"},
            )

        # Request only 3 revisions
        response = client.get(f"/api/v1/memories/{memory_id}/revisions?limit=3")

        assert response.status_code == 200
        data = response.json()

        assert len(data["revisions"]) == 3
        assert data["limit"] == 3
        assert data["total"] == 5

    def test_list_revisions_nonexistent_memory(self, client):
        """Test listing revisions for non-existent memory returns empty list."""
        response = client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000/revisions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["revisions"]) == 0


class TestGetRevision:
    """Tests for GET /api/v1/memories/{memory_id}/revisions/{revision_number} endpoint."""

    def test_get_revision_success(self, client):
        """Test retrieving a specific revision by number."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_get_revision"},
                "fact": "Original fact",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Update to create a revision
        client.patch(
            f"/api/v1/memories/{memory_id}",
            json={
                "fact": "Updated fact",
                "change_reason": "Correction needed",
            },
        )

        # Get the revision
        response = client.get(f"/api/v1/memories/{memory_id}/revisions/1")

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["memory_id"] == memory_id
        assert data["revision_number"] == 1
        assert data["previous_fact"] == "Original fact"
        assert data["new_fact"] == "Updated fact"
        assert data["change_reason"] == "Correction needed"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_revision_specific_number(self, client):
        """Test retrieving a specific revision from multiple revisions."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_specific"},
                "fact": "Version 0",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Create multiple revisions
        for i in range(1, 4):
            client.patch(
                f"/api/v1/memories/{memory_id}",
                json={
                    "fact": f"Version {i}",
                    "change_reason": f"Update {i}",
                },
            )

        # Get revision 2
        response = client.get(f"/api/v1/memories/{memory_id}/revisions/2")

        assert response.status_code == 200
        data = response.json()

        assert data["revision_number"] == 2
        assert data["previous_fact"] == "Version 1"
        assert data["new_fact"] == "Version 2"
        assert data["change_reason"] == "Update 2"

    def test_get_revision_not_found(self, client):
        """Test retrieving a non-existent revision returns 404."""
        # Create a memory without updates
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_not_found"},
                "fact": "No revisions",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Try to get a revision that doesn't exist
        response = client.get(f"/api/v1/memories/{memory_id}/revisions/1")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_revision_invalid_number(self, client):
        """Test retrieving revision with invalid number."""
        # Create a memory and one revision
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_invalid"},
                "fact": "Original",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        client.patch(
            f"/api/v1/memories/{memory_id}",
            json={"fact": "Updated"},
        )

        # Try to get revision 99 (doesn't exist)
        response = client.get(f"/api/v1/memories/{memory_id}/revisions/99")

        assert response.status_code == 404

    def test_get_revision_nonexistent_memory(self, client):
        """Test getting revision for non-existent memory returns 404."""
        response = client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000/revisions/1")

        assert response.status_code == 404


class TestRevisionTimestamps:
    """Tests for revision timestamp tracking."""

    def test_revision_has_timestamps(self, client):
        """Test that revisions have created_at and updated_at timestamps."""
        # Create a memory and update it
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_timestamps"},
                "fact": "Original",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        client.patch(
            f"/api/v1/memories/{memory_id}",
            json={"fact": "Updated"},
        )

        # Get the revision
        response = client.get(f"/api/v1/memories/{memory_id}/revisions/1")

        assert response.status_code == 200
        data = response.json()

        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] is not None
        assert data["updated_at"] is not None


class TestRevisionWithoutChangeReason:
    """Tests for revisions created without change_reason."""

    def test_revision_without_reason(self, client):
        """Test that revisions can be created without change_reason."""
        # Create a memory
        create_response = client.post(
            "/api/v1/memories",
            json={
                "scope": {"user_id": "user_no_reason"},
                "fact": "Original",
                "source_type": "conversation",
            },
        )
        memory_id = create_response.json()["id"]

        # Update without change_reason
        client.patch(
            f"/api/v1/memories/{memory_id}",
            json={"fact": "Updated"},
        )

        # Get the revision
        response = client.get(f"/api/v1/memories/{memory_id}/revisions/1")

        assert response.status_code == 200
        data = response.json()

        assert data["change_reason"] is None
