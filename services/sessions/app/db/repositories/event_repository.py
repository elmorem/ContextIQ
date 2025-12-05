"""
Event repository for database operations.

Provides CRUD operations and queries for Event model.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.sessions.app.db.models import Event
from services.sessions.app.db.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for Event model."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize event repository.

        Args:
            db_session: Database session
        """
        super().__init__(db_session, Event)

    async def create_event(
        self,
        session_id: UUID,
        event_type: str,
        data: dict,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> Event:
        """
        Create a new event.

        Args:
            session_id: Session ID this event belongs to
            event_type: Type of event
            data: Event data payload
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Created event instance
        """
        return await self.create(
            session_id=session_id,
            event_type=event_type,
            data=data,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now(UTC),
        )

    async def get_session_events(
        self,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        """
        Get events for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of events ordered by timestamp
        """
        stmt = (
            select(Event)
            .where(Event.session_id == session_id)
            .order_by(Event.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_events_by_type(
        self,
        session_id: UUID,
        event_type: str,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get events of a specific type for a session.

        Args:
            session_id: Session ID
            event_type: Type of events to retrieve
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        stmt = (
            select(Event)
            .where(Event.session_id == session_id)
            .where(Event.event_type == event_type)
            .order_by(Event.timestamp.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_events(
        self,
        session_id: UUID,
        count: int = 10,
    ) -> list[Event]:
        """
        Get the most recent events for a session.

        Args:
            session_id: Session ID
            count: Number of events to retrieve

        Returns:
            List of most recent events, newest first
        """
        stmt = (
            select(Event)
            .where(Event.session_id == session_id)
            .order_by(Event.timestamp.desc())
            .limit(count)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_session_events(self, session_id: UUID) -> int:
        """
        Count total events for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of events
        """
        stmt = select(func.count()).select_from(Event).where(Event.session_id == session_id)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_token_stats(self, session_id: UUID) -> dict[str, int]:
        """
        Get token usage statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with total_input_tokens and total_output_tokens
        """
        stmt = select(
            func.sum(Event.input_tokens).label("total_input"),
            func.sum(Event.output_tokens).label("total_output"),
        ).where(Event.session_id == session_id)

        result = await self.db.execute(stmt)
        row = result.one()

        return {
            "total_input_tokens": row.total_input or 0,
            "total_output_tokens": row.total_output or 0,
        }

    async def delete_session_events(self, session_id: UUID) -> int:
        """
        Delete all events for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of deleted events
        """
        events = await self.get_session_events(session_id, limit=10000)

        for event in events:
            await self.delete(event)

        await self.db.flush()
        return len(events)
