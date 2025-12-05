"""
Integration tests for sessions CRUD API endpoints.

Tests all REST API operations for session and event management.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.sessions.app.core.dependencies import get_db_session
from services.sessions.app.main import create_app
from shared.database.base import Base

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


class TestCreateSession:
    """Tests for POST /api/v1/sessions endpoint."""

    def test_create_session_success(self, client):
        """Test creating a session successfully."""
        response = client.post(
            "/api/v1/sessions",
            json={
                "scope": {"user_id": "user_123"},
                "title": "Test Session",
                "description": "A test session",
                "state": {"step": 1},
                "ttl": 3600,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["scope"] == {"user_id": "user_123"}
        assert data["title"] == "Test Session"
        assert data["description"] == "A test session"
        assert data["state"] == {"step": 1}
        assert data["ttl"] == 3600
        assert data["event_count"] == 0
        assert data["total_input_tokens"] == 0
        assert data["total_output_tokens"] == 0
        assert data["ended_at"] is None

    def test_create_session_minimal(self, client):
        """Test creating a session with minimal data."""
        response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_456"}},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["scope"] == {"user_id": "user_456"}
        assert data["title"] is None
        assert data["description"] is None
        assert data["state"] == {}
        assert data["ttl"] == 3600  # Default TTL

    def test_create_session_invalid_ttl(self, client):
        """Test creating a session with invalid TTL."""
        response = client.post(
            "/api/v1/sessions",
            json={
                "scope": {"user_id": "user_789"},
                "ttl": 100000,  # Exceeds max
            },
        )

        assert response.status_code == 400
        assert "Invalid TTL" in response.json()["detail"]


class TestGetSession:
    """Tests for GET /api/v1/sessions/{session_id} endpoint."""

    def test_get_session_success(self, client):
        """Test retrieving a session by ID."""
        # Create a session first
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "scope": {"user_id": "user_abc"},
                "title": "Retrievable Session",
            },
        )
        session_id = create_response.json()["id"]

        # Get the session
        response = client.get(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["title"] == "Retrievable Session"

    def test_get_session_not_found(self, client):
        """Test retrieving a non-existent session."""
        response = client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListSessions:
    """Tests for GET /api/v1/sessions endpoint."""

    def test_list_sessions(self, client):
        """Test listing sessions."""
        # Create multiple sessions
        for i in range(3):
            client.post(
                "/api/v1/sessions",
                json={"scope": {"user_id": f"user_{i}"}},
            )

        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()

        assert "sessions" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["sessions"]) >= 3

    def test_list_sessions_with_filters(self, client):
        """Test listing sessions with scope filter."""
        # Create sessions with different user IDs
        client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "alice"}},
        )
        client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "bob"}},
        )

        response = client.get("/api/v1/sessions?scope_user_id=alice")

        assert response.status_code == 200
        data = response.json()

        # Should only return Alice's sessions
        for session in data["sessions"]:
            assert session["scope"]["user_id"] == "alice"

    def test_list_sessions_pagination(self, client):
        """Test pagination of session list."""
        # Create multiple sessions
        for i in range(5):
            client.post(
                "/api/v1/sessions",
                json={"scope": {"user_id": f"user_{i}"}},
            )

        response = client.get("/api/v1/sessions?limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()

        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["sessions"]) <= 2


class TestUpdateSessionState:
    """Tests for PUT /api/v1/sessions/{session_id}/state endpoint."""

    def test_update_state_merge(self, client):
        """Test merging state into a session."""
        # Create a session with initial state
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "scope": {"user_id": "user_merge"},
                "state": {"key1": "value1", "key2": "value2"},
            },
        )
        session_id = create_response.json()["id"]

        # Merge new state
        response = client.put(
            f"/api/v1/sessions/{session_id}/state",
            json={"state": {"key2": "updated", "key3": "new"}, "merge": True},
        )

        assert response.status_code == 200
        data = response.json()

        # key1 should remain, key2 should be updated, key3 should be added
        assert data["state"] == {"key1": "value1", "key2": "updated", "key3": "new"}

    def test_update_state_replace(self, client):
        """Test replacing state in a session."""
        # Create a session with initial state
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "scope": {"user_id": "user_replace"},
                "state": {"key1": "value1", "key2": "value2"},
            },
        )
        session_id = create_response.json()["id"]

        # Replace state
        response = client.put(
            f"/api/v1/sessions/{session_id}/state",
            json={"state": {"new_key": "new_value"}, "merge": False},
        )

        assert response.status_code == 200
        data = response.json()

        # Old keys should be gone
        assert data["state"] == {"new_key": "new_value"}

    def test_update_state_not_found(self, client):
        """Test updating state for non-existent session."""
        response = client.put(
            "/api/v1/sessions/00000000-0000-0000-0000-000000000000/state",
            json={"state": {"key": "value"}, "merge": False},
        )

        assert response.status_code == 404


class TestCreateEvent:
    """Tests for POST /api/v1/sessions/{session_id}/events endpoint."""

    def test_create_event_success(self, client):
        """Test creating an event for a session."""
        # Create a session first
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_event"}},
        )
        session_id = create_response.json()["id"]

        # Create an event
        response = client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={
                "event_type": "user_message",
                "data": {"content": "Hello!"},
                "input_tokens": 10,
                "output_tokens": 20,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["session_id"] == session_id
        assert data["event_type"] == "user_message"
        assert data["data"] == {"content": "Hello!"}
        assert data["input_tokens"] == 10
        assert data["output_tokens"] == 20

    def test_create_event_updates_token_counts(self, client):
        """Test that creating events updates session token counts."""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_tokens"}},
        )
        session_id = create_response.json()["id"]

        # Create first event
        client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={
                "event_type": "message",
                "data": {},
                "input_tokens": 10,
                "output_tokens": 20,
            },
        )

        # Create second event
        client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={
                "event_type": "message",
                "data": {},
                "input_tokens": 5,
                "output_tokens": 15,
            },
        )

        # Get session and check token counts
        response = client.get(f"/api/v1/sessions/{session_id}")
        data = response.json()

        assert data["event_count"] == 2
        assert data["total_input_tokens"] == 15
        assert data["total_output_tokens"] == 35

    def test_create_event_not_found(self, client):
        """Test creating an event for non-existent session."""
        response = client.post(
            "/api/v1/sessions/00000000-0000-0000-0000-000000000000/events",
            json={
                "event_type": "message",
                "data": {},
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )

        assert response.status_code == 404


class TestListEvents:
    """Tests for GET /api/v1/sessions/{session_id}/events endpoint."""

    def test_list_events(self, client):
        """Test listing events for a session."""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_list_events"}},
        )
        session_id = create_response.json()["id"]

        # Create multiple events
        for i in range(3):
            client.post(
                f"/api/v1/sessions/{session_id}/events",
                json={
                    "event_type": "message",
                    "data": {"index": i},
                    "input_tokens": i,
                    "output_tokens": i * 2,
                },
            )

        response = client.get(f"/api/v1/sessions/{session_id}/events")

        assert response.status_code == 200
        data = response.json()

        assert "events" in data
        assert "total" in data
        assert len(data["events"]) == 3
        assert data["total"] == 3

    def test_list_events_with_type_filter(self, client):
        """Test listing events filtered by type."""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_filter_events"}},
        )
        session_id = create_response.json()["id"]

        # Create events of different types
        client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={"event_type": "user_message", "data": {}, "input_tokens": 0, "output_tokens": 0},
        )
        client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={"event_type": "ai_response", "data": {}, "input_tokens": 0, "output_tokens": 0},
        )
        client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={"event_type": "user_message", "data": {}, "input_tokens": 0, "output_tokens": 0},
        )

        response = client.get(f"/api/v1/sessions/{session_id}/events?event_type=user_message")

        assert response.status_code == 200
        data = response.json()

        # Should only return user_message events
        assert len(data["events"]) == 2
        for event in data["events"]:
            assert event["event_type"] == "user_message"

    def test_list_events_pagination(self, client):
        """Test pagination of event list."""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_page_events"}},
        )
        session_id = create_response.json()["id"]

        # Create multiple events
        for i in range(5):
            client.post(
                f"/api/v1/sessions/{session_id}/events",
                json={
                    "event_type": "message",
                    "data": {"index": i},
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            )

        response = client.get(f"/api/v1/sessions/{session_id}/events?limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()

        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["events"]) == 2


class TestDeleteSession:
    """Tests for DELETE /api/v1/sessions/{session_id} endpoint."""

    def test_delete_session_success(self, client):
        """Test deleting a session."""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_delete"}},
        )
        session_id = create_response.json()["id"]

        # Delete the session
        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert session_id in data["message"]

        # Verify session is deleted
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404

    def test_delete_session_with_events(self, client):
        """Test deleting a session with events."""
        # Create a session with events
        create_response = client.post(
            "/api/v1/sessions",
            json={"scope": {"user_id": "user_delete_events"}},
        )
        session_id = create_response.json()["id"]

        # Add events
        client.post(
            f"/api/v1/sessions/{session_id}/events",
            json={
                "event_type": "message",
                "data": {},
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )

        # Delete the session
        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200

        # Verify events are also deleted
        events_response = client.get(f"/api/v1/sessions/{session_id}/events")
        assert events_response.status_code == 404

    def test_delete_session_not_found(self, client):
        """Test deleting a non-existent session."""
        response = client.delete("/api/v1/sessions/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
