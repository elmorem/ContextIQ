"""
Unit tests for SessionService.

Tests business logic for session management.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.sessions.app.core.config import SessionsServiceSettings
from services.sessions.app.db.repositories.event_repository import EventRepository
from services.sessions.app.db.repositories.session_repository import SessionRepository
from services.sessions.app.services.session_service import (
    InvalidTTLError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionService,
)


@pytest.fixture
def settings():
    """Create test settings."""
    return SessionsServiceSettings(
        default_session_ttl=3600,
        max_session_ttl=86400,
        session_cleanup_batch_size=100,
        session_cleanup_days=30,
        enable_cache=False,
    )


@pytest.fixture
def session_repo():
    """Create mock session repository."""
    return AsyncMock(spec=SessionRepository)


@pytest.fixture
def event_repo():
    """Create mock event repository."""
    return AsyncMock(spec=EventRepository)


@pytest.fixture
def service(session_repo, event_repo, settings):
    """Create session service for tests."""
    return SessionService(session_repo, event_repo, settings)


@pytest.fixture
def mock_session():
    """Create a mock session."""
    session = MagicMock()
    session.id = uuid4()
    session.scope = {"user_id": "test_user"}
    session.title = "Test Session"
    session.description = "Test"
    session.state = {}
    session.ttl = 3600
    session.started_at = datetime.now(UTC)
    session.last_activity_at = datetime.now(UTC)
    session.ended_at = None
    session.event_count = 0
    session.total_input_tokens = 0
    session.total_output_tokens = 0
    return session


class TestCreateSession:
    """Tests for create_session."""

    @pytest.mark.asyncio
    async def test_creates_session_with_default_ttl(self, service, session_repo, mock_session):
        """Test creates session with default TTL."""
        session_repo.create_session.return_value = mock_session

        result = await service.create_session(scope={"user_id": "123"})

        assert result == mock_session
        session_repo.create_session.assert_called_once()
        call_kwargs = session_repo.create_session.call_args.kwargs
        assert call_kwargs["ttl"] == 3600

    @pytest.mark.asyncio
    async def test_creates_session_with_custom_ttl(self, service, session_repo, mock_session):
        """Test creates session with custom TTL."""
        session_repo.create_session.return_value = mock_session

        await service.create_session(scope={"user_id": "123"}, ttl=7200)

        call_kwargs = session_repo.create_session.call_args.kwargs
        assert call_kwargs["ttl"] == 7200

    @pytest.mark.asyncio
    async def test_validates_max_ttl(self, service):
        """Test validates TTL against maximum."""
        with pytest.raises(InvalidTTLError) as exc_info:
            await service.create_session(scope={"user_id": "123"}, ttl=90000)

        assert exc_info.value.ttl == 90000
        assert exc_info.value.max_ttl == 86400

    @pytest.mark.asyncio
    async def test_creates_with_title_and_description(self, service, session_repo, mock_session):
        """Test creates session with title and description."""
        session_repo.create_session.return_value = mock_session

        await service.create_session(
            scope={"user_id": "123"},
            title="My Session",
            description="Test session",
        )

        call_kwargs = session_repo.create_session.call_args.kwargs
        assert call_kwargs["title"] == "My Session"
        assert call_kwargs["description"] == "Test session"

    @pytest.mark.asyncio
    async def test_creates_with_initial_state(self, service, session_repo, mock_session):
        """Test creates session with initial state."""
        session_repo.create_session.return_value = mock_session
        initial_state = {"step": 1, "data": "test"}

        await service.create_session(scope={"user_id": "123"}, state=initial_state)

        call_kwargs = session_repo.create_session.call_args.kwargs
        assert call_kwargs["state"] == initial_state


class TestGetSession:
    """Tests for get_session."""

    @pytest.mark.asyncio
    async def test_gets_active_session(self, service, session_repo, mock_session):
        """Test gets active session."""
        session_repo.get_by_id.return_value = mock_session

        result = await service.get_session(mock_session.id)

        assert result == mock_session
        session_repo.get_by_id.assert_called_once_with(mock_session.id)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, session_repo):
        """Test raises error when session not found."""
        session_id = uuid4()
        session_repo.get_by_id.return_value = None

        with pytest.raises(SessionNotFoundError) as exc_info:
            await service.get_session(session_id)

        assert exc_info.value.session_id == session_id

    @pytest.mark.asyncio
    async def test_raises_expired_for_ended_session(self, service, session_repo, mock_session):
        """Test raises error for ended session."""
        mock_session.ended_at = datetime.now(UTC)
        session_repo.get_by_id.return_value = mock_session

        with pytest.raises(SessionExpiredError) as exc_info:
            await service.get_session(mock_session.id)

        assert exc_info.value.session_id == mock_session.id

    @pytest.mark.asyncio
    async def test_raises_expired_for_ttl_exceeded(self, service, session_repo, mock_session):
        """Test raises error when TTL exceeded."""
        # Set last activity to 2 hours ago, TTL is 1 hour
        mock_session.last_activity_at = datetime.now(UTC) - timedelta(hours=2)
        mock_session.ttl = 3600
        session_repo.get_by_id.return_value = mock_session

        with pytest.raises(SessionExpiredError):
            await service.get_session(mock_session.id)

    @pytest.mark.asyncio
    async def test_accepts_session_within_ttl(self, service, session_repo, mock_session):
        """Test accepts session within TTL."""
        # Set last activity to 30 minutes ago, TTL is 1 hour
        mock_session.last_activity_at = datetime.now(UTC) - timedelta(minutes=30)
        mock_session.ttl = 3600
        session_repo.get_by_id.return_value = mock_session

        result = await service.get_session(mock_session.id)

        assert result == mock_session


class TestUpdateSessionState:
    """Tests for update_session_state."""

    @pytest.mark.asyncio
    async def test_replaces_state(self, service, session_repo, mock_session):
        """Test replaces session state."""
        mock_session.state = {"old": "data"}
        session_repo.get_by_id.return_value = mock_session
        session_repo.update_state.return_value = mock_session
        new_state = {"new": "data"}

        await service.update_session_state(mock_session.id, new_state, merge=False)

        session_repo.update_state.assert_called_once_with(mock_session.id, new_state)

    @pytest.mark.asyncio
    async def test_merges_state(self, service, session_repo, mock_session):
        """Test merges with existing state."""
        mock_session.state = {"old": "data", "keep": "this"}
        session_repo.get_by_id.return_value = mock_session
        session_repo.update_state.return_value = mock_session
        new_state = {"new": "data"}

        await service.update_session_state(mock_session.id, new_state, merge=True)

        call_kwargs = session_repo.update_state.call_args.args
        merged = call_kwargs[1]
        assert merged == {"old": "data", "keep": "this", "new": "data"}

    @pytest.mark.asyncio
    async def test_validates_session_exists(self, service, session_repo):
        """Test validates session exists."""
        session_repo.get_by_id.return_value = None

        with pytest.raises(SessionNotFoundError):
            await service.update_session_state(uuid4(), {"new": "state"})


class TestUpdateActivity:
    """Tests for update_activity."""

    @pytest.mark.asyncio
    async def test_updates_activity(self, service, session_repo, mock_session):
        """Test updates activity timestamp."""
        session_repo.get_by_id.return_value = mock_session
        session_repo.update_activity.return_value = mock_session

        result = await service.update_activity(mock_session.id)

        assert result == mock_session
        session_repo.update_activity.assert_called_once_with(mock_session.id)

    @pytest.mark.asyncio
    async def test_validates_session_not_expired(self, service, session_repo, mock_session):
        """Test validates session not expired."""
        mock_session.ended_at = datetime.now(UTC)
        session_repo.get_by_id.return_value = mock_session

        with pytest.raises(SessionExpiredError):
            await service.update_activity(mock_session.id)


class TestEndSession:
    """Tests for end_session."""

    @pytest.mark.asyncio
    async def test_ends_session(self, service, session_repo, mock_session):
        """Test ends a session."""
        session_repo.end_session.return_value = mock_session

        result = await service.end_session(mock_session.id)

        assert result == mock_session
        session_repo.end_session.assert_called_once_with(mock_session.id)

    @pytest.mark.asyncio
    async def test_raises_not_found(self, service, session_repo):
        """Test raises error when session not found."""
        session_repo.end_session.return_value = None

        with pytest.raises(SessionNotFoundError):
            await service.end_session(uuid4())


class TestAddEvent:
    """Tests for add_event."""

    @pytest.mark.asyncio
    async def test_adds_event(self, service, session_repo, event_repo, mock_session):
        """Test adds event to session."""
        session_repo.get_by_id.return_value = mock_session
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.session_id = mock_session.id
        mock_event.event_type = "test"
        mock_event.data = {"content": "test"}
        mock_event.input_tokens = 10
        mock_event.output_tokens = 20
        mock_event.timestamp = datetime.now(UTC)
        event_repo.create_event.return_value = mock_event

        result = await service.add_event(
            mock_session.id,
            "test",
            {"content": "test"},
            input_tokens=10,
            output_tokens=20,
        )

        assert result == mock_event
        event_repo.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_activity_after_event(
        self, service, session_repo, event_repo, mock_session
    ):
        """Test updates activity timestamp after adding event."""
        session_repo.get_by_id.return_value = mock_session
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.session_id = mock_session.id
        mock_event.event_type = "test"
        mock_event.data = {}
        mock_event.input_tokens = 0
        mock_event.output_tokens = 0
        mock_event.timestamp = datetime.now(UTC)
        event_repo.create_event.return_value = mock_event

        await service.add_event(mock_session.id, "test", {})

        session_repo.update_activity.assert_called_once_with(mock_session.id)

    @pytest.mark.asyncio
    async def test_validates_session_not_expired(self, service, session_repo, mock_session):
        """Test validates session not expired before adding event."""
        mock_session.ended_at = datetime.now(UTC)
        session_repo.get_by_id.return_value = mock_session

        with pytest.raises(SessionExpiredError):
            await service.add_event(mock_session.id, "test", {})


class TestGetSessionEvents:
    """Tests for get_session_events."""

    @pytest.mark.asyncio
    async def test_gets_events(self, service, session_repo, event_repo, mock_session):
        """Test gets events for session."""
        session_repo.get_by_id.return_value = mock_session
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.session_id = mock_session.id
        mock_event.event_type = "test"
        mock_event.data = {}
        mock_event.input_tokens = 0
        mock_event.output_tokens = 0
        mock_event.timestamp = datetime.now(UTC)
        mock_events = [mock_event]
        event_repo.get_session_events.return_value = mock_events

        result = await service.get_session_events(mock_session.id, limit=10, offset=0)

        assert result == mock_events
        event_repo.get_session_events.assert_called_once_with(mock_session.id, 10, 0)

    @pytest.mark.asyncio
    async def test_validates_session_exists(self, service, session_repo):
        """Test validates session exists."""
        session_repo.get_by_id.return_value = None

        with pytest.raises(SessionNotFoundError):
            await service.get_session_events(uuid4())


class TestGetSessionsByScope:
    """Tests for get_sessions_by_scope."""

    @pytest.mark.asyncio
    async def test_gets_sessions(self, service, session_repo, mock_session):
        """Test gets sessions by scope."""
        scope = {"user_id": "123"}
        session_repo.get_by_scope.return_value = [mock_session]

        result = await service.get_sessions_by_scope(scope, limit=50)

        assert result == [mock_session]
        session_repo.get_by_scope.assert_called_once_with(scope, 50)


class TestCleanupExpiredSessions:
    """Tests for cleanup_expired_sessions."""

    @pytest.mark.asyncio
    async def test_ends_expired_sessions(self, service, session_repo, mock_session):
        """Test ends expired sessions."""
        expired_sessions = [mock_session]
        session_repo.get_expired_sessions.return_value = expired_sessions

        count = await service.cleanup_expired_sessions()

        assert count == 1
        session_repo.end_session.assert_called_once_with(mock_session.id)


class TestCleanupOldSessions:
    """Tests for cleanup_old_sessions."""

    @pytest.mark.asyncio
    async def test_deletes_old_sessions(self, service, session_repo):
        """Test deletes old sessions."""
        session_repo.delete_old_sessions.return_value = 5

        count = await service.cleanup_old_sessions()

        assert count == 5
        session_repo.delete_old_sessions.assert_called_once_with(days=30)
