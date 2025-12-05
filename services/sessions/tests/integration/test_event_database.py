"""
Integration tests for Event database operations.

These tests require a running PostgreSQL database.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.sessions.app.db.repositories.event_repository import EventRepository
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
def event_repository(db_session):
    """Provide event repository for tests."""
    return EventRepository(db_session)


@pytest.fixture
def session_repository(db_session):
    """Provide session repository for tests."""
    return SessionRepository(db_session)


@pytest.fixture
async def test_session(session_repository, db_session):
    """Create a test session."""
    session = await session_repository.create_session(
        scope={"user_id": "event_test", "org_id": "test"}
    )
    await db_session.commit()
    return session


class TestEventCRUD:
    """Tests for basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_event(self, event_repository, test_session, db_session):
        """Test creating and retrieving an event."""
        event = await event_repository.create_event(
            session_id=test_session.id,
            event_type="user_message",
            data={"content": "Hello, world!", "metadata": {"source": "web"}},
            input_tokens=5,
            output_tokens=0,
        )
        await db_session.commit()

        # Retrieve event
        retrieved = await event_repository.get_by_id(event.id)

        assert retrieved is not None
        assert retrieved.session_id == test_session.id
        assert retrieved.event_type == "user_message"
        assert retrieved.data == {"content": "Hello, world!", "metadata": {"source": "web"}}
        assert retrieved.input_tokens == 5

    @pytest.mark.asyncio
    async def test_event_session_relationship(self, event_repository, test_session, db_session):
        """Test event-session relationship."""
        # Create events for session
        for i in range(3):
            await event_repository.create_event(
                session_id=test_session.id,
                event_type=f"event_type_{i}",
                data={"index": i},
            )
        await db_session.commit()

        # Get all events for session
        events = await event_repository.get_session_events(test_session.id)

        assert len(events) == 3
        assert all(e.session_id == test_session.id for e in events)


class TestEventQueries:
    """Tests for event queries."""

    @pytest.mark.asyncio
    async def test_get_events_by_type(self, event_repository, test_session, db_session):
        """Test filtering events by type."""
        # Create mix of event types
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="user_message",
            data={"msg": 1},
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="assistant_response",
            data={"msg": 2},
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="user_message",
            data={"msg": 3},
        )
        await db_session.commit()

        # Get only user messages
        user_messages = await event_repository.get_events_by_type(test_session.id, "user_message")

        assert len(user_messages) == 2
        assert all(e.event_type == "user_message" for e in user_messages)

    @pytest.mark.asyncio
    async def test_pagination(self, event_repository, test_session, db_session):
        """Test event pagination."""
        # Create 10 events
        for i in range(10):
            await event_repository.create_event(
                session_id=test_session.id,
                event_type="test_event",
                data={"index": i},
            )
        await db_session.commit()

        # Get first page
        page1 = await event_repository.get_session_events(test_session.id, limit=5, offset=0)
        assert len(page1) == 5
        assert page1[0].data["index"] == 0

        # Get second page
        page2 = await event_repository.get_session_events(test_session.id, limit=5, offset=5)
        assert len(page2) == 5
        assert page2[0].data["index"] == 5


class TestTokenTracking:
    """Tests for token usage tracking."""

    @pytest.mark.asyncio
    async def test_token_statistics(self, event_repository, test_session, db_session):
        """Test token usage statistics."""
        # Create events with different token counts
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="event1",
            data={},
            input_tokens=100,
            output_tokens=200,
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="event2",
            data={},
            input_tokens=150,
            output_tokens=250,
        )
        await db_session.commit()

        # Get token stats
        stats = await event_repository.get_token_stats(test_session.id)

        assert stats["total_input_tokens"] == 250
        assert stats["total_output_tokens"] == 450


class TestEventDeletion:
    """Tests for event deletion."""

    @pytest.mark.asyncio
    async def test_delete_session_events(self, event_repository, session_repository, db_session):
        """Test deleting all events for a session."""
        # Create a separate session for deletion test
        session = await session_repository.create_session(scope={"user_id": "delete_test"})
        await db_session.commit()

        # Create events
        for i in range(5):
            await event_repository.create_event(
                session_id=session.id,
                event_type=f"event{i}",
                data={},
            )
        await db_session.commit()

        # Delete all events
        deleted_count = await event_repository.delete_session_events(session.id)
        await db_session.commit()

        assert deleted_count == 5

        # Verify deletion
        count = await event_repository.count_session_events(session.id)
        assert count == 0
