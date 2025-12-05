"""
Unit tests for SessionRepository.

These tests use an in-memory SQLite database for testing.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.sessions.app.db.repositories.session_repository import SessionRepository
from shared.database.base import Base


@pytest.fixture
async def db_engine():
    """Create in-memory SQLite database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create database session for tests."""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def session_repository(db_session):
    """Create session repository for tests."""
    return SessionRepository(db_session)


class TestCreateSession:
    """Tests for create_session."""

    @pytest.mark.asyncio
    async def test_creates_session(self, session_repository, db_session):
        """Test creating a new session."""
        scope = {"user_id": "123"}
        session = await session_repository.create_session(scope=scope)

        assert session.id is not None
        assert session.scope == scope
        assert session.state == {}
        assert session.started_at is not None
        assert session.last_activity_at is not None
        assert session.ended_at is None

    @pytest.mark.asyncio
    async def test_creates_session_with_title(self, session_repository):
        """Test creating session with title."""
        scope = {"user_id": "123"}
        title = "Test Session"
        session = await session_repository.create_session(scope=scope, title=title)

        assert session.title == title

    @pytest.mark.asyncio
    async def test_creates_session_with_state(self, session_repository):
        """Test creating session with initial state."""
        scope = {"user_id": "123"}
        state = {"key": "value"}
        session = await session_repository.create_session(scope=scope, state=state)

        assert session.state == state

    @pytest.mark.asyncio
    async def test_creates_session_with_ttl(self, session_repository):
        """Test creating session with TTL."""
        scope = {"user_id": "123"}
        ttl = 3600
        session = await session_repository.create_session(scope=scope, ttl=ttl)

        assert session.ttl == ttl


class TestGetByScope:
    """Tests for get_by_scope."""

    @pytest.mark.asyncio
    async def test_returns_sessions_for_scope(self, session_repository):
        """Test returns sessions matching scope."""
        scope1 = {"user_id": "123"}
        scope2 = {"user_id": "456"}

        await session_repository.create_session(scope=scope1)
        await session_repository.create_session(scope=scope1)
        await session_repository.create_session(scope=scope2)

        sessions = await session_repository.get_by_scope(scope1)

        assert len(sessions) == 2
        assert all(s.scope == scope1 for s in sessions)

    @pytest.mark.asyncio
    async def test_excludes_ended_sessions(self, session_repository):
        """Test excludes ended sessions."""
        scope = {"user_id": "123"}

        session1 = await session_repository.create_session(scope=scope)
        await session_repository.create_session(scope=scope)
        await session_repository.end_session(session1.id)

        sessions = await session_repository.get_by_scope(scope)

        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_orders_by_activity(self, session_repository):
        """Test orders sessions by last activity."""
        scope = {"user_id": "123"}

        session1 = await session_repository.create_session(scope=scope)
        session2 = await session_repository.create_session(scope=scope)

        sessions = await session_repository.get_by_scope(scope)

        assert sessions[0].id == session2.id
        assert sessions[1].id == session1.id

    @pytest.mark.asyncio
    async def test_respects_limit(self, session_repository):
        """Test respects limit parameter."""
        scope = {"user_id": "123"}

        for _ in range(5):
            await session_repository.create_session(scope=scope)

        sessions = await session_repository.get_by_scope(scope, limit=3)

        assert len(sessions) == 3


class TestGetActiveSessions:
    """Tests for get_active_sessions."""

    @pytest.mark.asyncio
    async def test_returns_active_sessions(self, session_repository):
        """Test returns only active sessions."""
        scope = {"user_id": "123"}

        session1 = await session_repository.create_session(scope=scope)
        session2 = await session_repository.create_session(scope=scope)
        await session_repository.end_session(session1.id)

        sessions = await session_repository.get_active_sessions()

        assert len(sessions) == 1
        assert sessions[0].id == session2.id

    @pytest.mark.asyncio
    async def test_filters_by_scope(self, session_repository):
        """Test filters by scope when provided."""
        scope1 = {"user_id": "123"}
        scope2 = {"user_id": "456"}

        await session_repository.create_session(scope=scope1)
        await session_repository.create_session(scope=scope2)

        sessions = await session_repository.get_active_sessions(scope=scope1)

        assert len(sessions) == 1
        assert sessions[0].scope == scope1


class TestUpdateActivity:
    """Tests for update_activity."""

    @pytest.mark.asyncio
    async def test_updates_last_activity(self, session_repository):
        """Test updates last activity timestamp."""
        scope = {"user_id": "123"}
        session = await session_repository.create_session(scope=scope)
        original_time = session.last_activity_at

        updated = await session_repository.update_activity(session.id)

        assert updated is not None
        assert updated.last_activity_at > original_time

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, session_repository):
        """Test returns None for nonexistent session."""
        result = await session_repository.update_activity(uuid4())

        assert result is None


class TestUpdateState:
    """Tests for update_state."""

    @pytest.mark.asyncio
    async def test_updates_state(self, session_repository):
        """Test updates session state."""
        scope = {"user_id": "123"}
        session = await session_repository.create_session(scope=scope)
        new_state = {"updated": "state"}

        updated = await session_repository.update_state(session.id, new_state)

        assert updated is not None
        assert updated.state == new_state

    @pytest.mark.asyncio
    async def test_updates_activity_timestamp(self, session_repository):
        """Test updates activity timestamp."""
        scope = {"user_id": "123"}
        session = await session_repository.create_session(scope=scope)
        original_time = session.last_activity_at

        await session_repository.update_state(session.id, {"new": "state"})
        updated = await session_repository.get_by_id(session.id)

        assert updated is not None
        assert updated.last_activity_at > original_time


class TestEndSession:
    """Tests for end_session."""

    @pytest.mark.asyncio
    async def test_ends_session(self, session_repository):
        """Test ends a session."""
        scope = {"user_id": "123"}
        session = await session_repository.create_session(scope=scope)

        ended = await session_repository.end_session(session.id)

        assert ended is not None
        assert ended.ended_at is not None

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, session_repository):
        """Test returns None for nonexistent session."""
        result = await session_repository.end_session(uuid4())

        assert result is None


class TestCountByScope:
    """Tests for count_by_scope."""

    @pytest.mark.asyncio
    async def test_counts_sessions(self, session_repository):
        """Test counts sessions for scope."""
        scope = {"user_id": "123"}

        await session_repository.create_session(scope=scope)
        await session_repository.create_session(scope=scope)

        count = await session_repository.count_by_scope(scope)

        assert count == 2

    @pytest.mark.asyncio
    async def test_excludes_ended_sessions(self, session_repository):
        """Test excludes ended sessions from count."""
        scope = {"user_id": "123"}

        session1 = await session_repository.create_session(scope=scope)
        await session_repository.create_session(scope=scope)
        await session_repository.end_session(session1.id)

        count = await session_repository.count_by_scope(scope)

        assert count == 1
