"""
Unit tests for EventRepository.

These tests use an in-memory SQLite database for testing.
"""


import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.sessions.app.db.repositories.event_repository import EventRepository
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
def event_repository(db_session):
    """Create event repository for tests."""
    return EventRepository(db_session)


@pytest.fixture
def session_repository(db_session):
    """Create session repository for tests."""
    return SessionRepository(db_session)


@pytest.fixture
async def test_session(session_repository):
    """Create a test session."""
    return await session_repository.create_session(scope={"user_id": "test_user"})


class TestCreateEvent:
    """Tests for create_event."""

    @pytest.mark.asyncio
    async def test_creates_event(self, event_repository, test_session):
        """Test creating a new event."""
        event = await event_repository.create_event(
            session_id=test_session.id,
            event_type="user_message",
            data={"content": "Hello"},
        )

        assert event.id is not None
        assert event.session_id == test_session.id
        assert event.event_type == "user_message"
        assert event.data == {"content": "Hello"}
        assert event.input_tokens == 0
        assert event.output_tokens == 0
        assert event.timestamp is not None

    @pytest.mark.asyncio
    async def test_creates_event_with_tokens(self, event_repository, test_session):
        """Test creating event with token counts."""
        event = await event_repository.create_event(
            session_id=test_session.id,
            event_type="assistant_response",
            data={"content": "Response"},
            input_tokens=10,
            output_tokens=20,
        )

        assert event.input_tokens == 10
        assert event.output_tokens == 20


class TestGetSessionEvents:
    """Tests for get_session_events."""

    @pytest.mark.asyncio
    async def test_returns_events_for_session(self, event_repository, test_session):
        """Test returns events for session."""
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="event1",
            data={},
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="event2",
            data={},
        )

        events = await event_repository.get_session_events(test_session.id)

        assert len(events) == 2
        assert all(e.session_id == test_session.id for e in events)

    @pytest.mark.asyncio
    async def test_orders_by_timestamp(self, event_repository, test_session):
        """Test events are ordered by timestamp ascending."""
        event1 = await event_repository.create_event(
            session_id=test_session.id,
            event_type="first",
            data={},
        )
        event2 = await event_repository.create_event(
            session_id=test_session.id,
            event_type="second",
            data={},
        )

        events = await event_repository.get_session_events(test_session.id)

        assert events[0].id == event1.id
        assert events[1].id == event2.id

    @pytest.mark.asyncio
    async def test_respects_limit(self, event_repository, test_session):
        """Test respects limit parameter."""
        for i in range(5):
            await event_repository.create_event(
                session_id=test_session.id,
                event_type=f"event{i}",
                data={},
            )

        events = await event_repository.get_session_events(test_session.id, limit=3)

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_respects_offset(self, event_repository, test_session):
        """Test respects offset parameter."""
        events_created = []
        for i in range(5):
            event = await event_repository.create_event(
                session_id=test_session.id,
                event_type=f"event{i}",
                data={},
            )
            events_created.append(event)

        events = await event_repository.get_session_events(test_session.id, limit=2, offset=2)

        assert len(events) == 2
        assert events[0].id == events_created[2].id


class TestGetEventsByType:
    """Tests for get_events_by_type."""

    @pytest.mark.asyncio
    async def test_filters_by_type(self, event_repository, test_session):
        """Test filters events by type."""
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="user_message",
            data={},
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="assistant_response",
            data={},
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="user_message",
            data={},
        )

        events = await event_repository.get_events_by_type(test_session.id, "user_message")

        assert len(events) == 2
        assert all(e.event_type == "user_message" for e in events)


class TestGetLatestEvents:
    """Tests for get_latest_events."""

    @pytest.mark.asyncio
    async def test_returns_most_recent(self, event_repository, test_session):
        """Test returns most recent events."""
        events_created = []
        for i in range(5):
            event = await event_repository.create_event(
                session_id=test_session.id,
                event_type=f"event{i}",
                data={},
            )
            events_created.append(event)

        events = await event_repository.get_latest_events(test_session.id, count=3)

        assert len(events) == 3
        # Should be newest first
        assert events[0].id == events_created[-1].id
        assert events[1].id == events_created[-2].id
        assert events[2].id == events_created[-3].id


class TestCountSessionEvents:
    """Tests for count_session_events."""

    @pytest.mark.asyncio
    async def test_counts_events(self, event_repository, test_session):
        """Test counts events for session."""
        for i in range(7):
            await event_repository.create_event(
                session_id=test_session.id,
                event_type=f"event{i}",
                data={},
            )

        count = await event_repository.count_session_events(test_session.id)

        assert count == 7

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_events(self, event_repository, session_repository):
        """Test returns 0 for session with no events."""
        session = await session_repository.create_session(scope={"user_id": "no_events"})

        count = await event_repository.count_session_events(session.id)

        assert count == 0


class TestGetTokenStats:
    """Tests for get_token_stats."""

    @pytest.mark.asyncio
    async def test_sums_tokens(self, event_repository, test_session):
        """Test sums token usage."""
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="event1",
            data={},
            input_tokens=10,
            output_tokens=20,
        )
        await event_repository.create_event(
            session_id=test_session.id,
            event_type="event2",
            data={},
            input_tokens=15,
            output_tokens=25,
        )

        stats = await event_repository.get_token_stats(test_session.id)

        assert stats["total_input_tokens"] == 25
        assert stats["total_output_tokens"] == 45

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_events(self, event_repository, session_repository):
        """Test returns zeros for session with no events."""
        session = await session_repository.create_session(scope={"user_id": "no_tokens"})

        stats = await event_repository.get_token_stats(session.id)

        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0


class TestDeleteSessionEvents:
    """Tests for delete_session_events."""

    @pytest.mark.asyncio
    async def test_deletes_all_events(self, event_repository, test_session):
        """Test deletes all events for session."""
        for i in range(5):
            await event_repository.create_event(
                session_id=test_session.id,
                event_type=f"event{i}",
                data={},
            )

        deleted_count = await event_repository.delete_session_events(test_session.id)

        assert deleted_count == 5

        # Verify events are deleted
        count = await event_repository.count_session_events(test_session.id)
        assert count == 0
