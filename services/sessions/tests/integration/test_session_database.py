"""
Integration tests for Session database operations.

These tests require a running PostgreSQL database.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.sessions.app.db.repositories.session_repository import SessionRepository

# Skip all tests if database is not available
pytestmark = pytest.mark.integration


@pytest.fixture
async def db_session():
    """Provide database session for tests."""
    # Create engine for PostgreSQL
    engine = create_async_engine(
        "postgresql+asyncpg://contextiq_user:contextiq_pass@localhost:5432/contextiq",
        echo=False,
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
def session_repository(db_session):
    """Provide session repository for tests."""
    return SessionRepository(db_session)


class TestSessionCRUD:
    """Tests for basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_session(self, session_repository, db_session):
        """Test creating and retrieving a session."""
        scope = {"user_id": "test_user", "org_id": "test_org"}
        title = "Integration Test Session"

        # Create session
        session = await session_repository.create_session(
            scope=scope,
            title=title,
            state={"count": 0},
        )
        await db_session.commit()

        # Retrieve session
        retrieved = await session_repository.get_by_id(session.id)

        assert retrieved is not None
        assert retrieved.id == session.id
        assert retrieved.scope == scope
        assert retrieved.title == title
        assert retrieved.state == {"count": 0}

    @pytest.mark.asyncio
    async def test_update_session_state(self, session_repository, db_session):
        """Test updating session state."""
        scope = {"user_id": "test_user"}
        session = await session_repository.create_session(scope=scope)
        await db_session.commit()

        # Update state
        new_state = {"step": 1, "data": "test"}
        await session_repository.update_state(session.id, new_state)
        await db_session.commit()

        # Verify update
        retrieved = await session_repository.get_by_id(session.id)
        assert retrieved is not None
        assert retrieved.state == new_state

    @pytest.mark.asyncio
    async def test_delete_session(self, session_repository, db_session):
        """Test deleting a session."""
        scope = {"user_id": "test_user"}
        session = await session_repository.create_session(scope=scope)
        await db_session.commit()

        # Delete session
        await session_repository.delete(session)
        await db_session.commit()

        # Verify deletion
        retrieved = await session_repository.get_by_id(session.id)
        assert retrieved is None


class TestScopeQueries:
    """Tests for scope-based queries."""

    @pytest.mark.asyncio
    async def test_get_sessions_by_scope(self, session_repository, db_session):
        """Test retrieving sessions by scope."""
        scope = {"user_id": "scope_test", "org_id": "test"}

        # Create multiple sessions with same scope
        for i in range(3):
            await session_repository.create_session(
                scope=scope,
                title=f"Session {i}",
            )
        await db_session.commit()

        # Retrieve by scope
        sessions = await session_repository.get_by_scope(scope)

        assert len(sessions) >= 3
        assert all(s.scope == scope for s in sessions[:3])

    @pytest.mark.asyncio
    async def test_count_sessions_by_scope(self, session_repository, db_session):
        """Test counting sessions by scope."""
        scope = {"user_id": "count_test"}

        # Create sessions
        for _ in range(5):
            await session_repository.create_session(scope=scope)
        await db_session.commit()

        # Count sessions
        count = await session_repository.count_by_scope(scope)

        assert count >= 5


class TestActivityTracking:
    """Tests for activity tracking."""

    @pytest.mark.asyncio
    async def test_update_activity_timestamp(self, session_repository, db_session):
        """Test updating last activity timestamp."""
        scope = {"user_id": "activity_test"}
        session = await session_repository.create_session(scope=scope)
        await db_session.commit()

        original_time = session.last_activity_at

        # Update activity
        updated = await session_repository.update_activity(session.id)
        await db_session.commit()

        assert updated is not None
        assert updated.last_activity_at > original_time

    @pytest.mark.asyncio
    async def test_end_session(self, session_repository, db_session):
        """Test ending a session."""
        scope = {"user_id": "end_test"}
        session = await session_repository.create_session(scope=scope)
        await db_session.commit()

        # End session
        ended = await session_repository.end_session(session.id)
        await db_session.commit()

        assert ended is not None
        assert ended.ended_at is not None

        # Verify ended sessions are excluded from active queries
        active_sessions = await session_repository.get_by_scope(scope)
        assert session.id not in [s.id for s in active_sessions]


class TestTransactions:
    """Tests for transaction handling."""

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, session_repository, db_session):
        """Test that changes are rolled back on error."""
        scope = {"user_id": "rollback_test"}

        # Create session
        session = await session_repository.create_session(scope=scope)

        # Don't commit - rollback instead
        await db_session.rollback()

        # Session should not exist
        retrieved = await session_repository.get_by_id(session.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_commit_persists_changes(self, session_repository, db_session):
        """Test that commit persists changes."""
        scope = {"user_id": "commit_test"}

        # Create and commit
        session = await session_repository.create_session(scope=scope)
        await db_session.commit()

        # Create new session to verify persistence
        new_db_session = db_session.get_bind()
        async with AsyncSession(new_db_session) as new_session:
            new_repo = SessionRepository(new_session)
            retrieved = await new_repo.get_by_id(session.id)

            assert retrieved is not None
            assert retrieved.id == session.id
