"""
Session repository for database operations.

Provides CRUD operations and queries for Session model.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.sessions.app.db.models import Session
from services.sessions.app.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for Session model."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize session repository.

        Args:
            db_session: Database session
        """
        super().__init__(db_session, Session)

    async def create_session(
        self,
        scope: dict,
        title: str | None = None,
        description: str | None = None,
        state: dict | None = None,
        ttl: int | None = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            scope: Session scope for isolation
            title: Optional session title
            description: Optional session description
            state: Initial state (default: empty dict)
            ttl: Time to live in seconds

        Returns:
            Created session instance
        """
        now = datetime.now(UTC)
        return await self.create(
            scope=scope,
            title=title,
            description=description,
            state=state or {},
            ttl=ttl,
            started_at=now,
            last_activity_at=now,
        )

    async def get_by_scope(self, scope: dict, limit: int = 100) -> list[Session]:
        """
        Get sessions by scope.

        Args:
            scope: Scope to filter by
            limit: Maximum number of sessions to return

        Returns:
            List of matching sessions
        """
        stmt = (
            select(Session)
            .where(Session.scope == scope)
            .where(Session.ended_at.is_(None))
            .order_by(Session.last_activity_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_sessions(
        self,
        scope: dict | None = None,
        limit: int = 100,
    ) -> list[Session]:
        """
        Get active (non-ended) sessions.

        Args:
            scope: Optional scope to filter by
            limit: Maximum number of sessions to return

        Returns:
            List of active sessions
        """
        stmt = (
            select(Session)
            .where(Session.ended_at.is_(None))
            .order_by(Session.last_activity_at.desc())
            .limit(limit)
        )

        if scope is not None:
            stmt = stmt.where(Session.scope == scope)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_activity(self, session_id: UUID) -> Session | None:
        """
        Update last activity timestamp.

        Args:
            session_id: Session ID

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session,
            last_activity_at=datetime.now(UTC),
        )

    async def update_state(
        self,
        session_id: UUID,
        state: dict,
    ) -> Session | None:
        """
        Update session state.

        Args:
            session_id: Session ID
            state: New state

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session,
            state=state,
            last_activity_at=datetime.now(UTC),
        )

    async def end_session(self, session_id: UUID) -> Session | None:
        """
        End a session.

        Args:
            session_id: Session ID

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session,
            ended_at=datetime.now(UTC),
        )

    async def get_expired_sessions(self, batch_size: int = 100) -> list[Session]:
        """
        Get sessions that have exceeded their TTL.

        Args:
            batch_size: Maximum number of sessions to return

        Returns:
            List of expired sessions
        """
        now = datetime.now(UTC)

        # Find sessions where:
        # 1. Session has a TTL set
        # 2. Session is not already ended
        # 3. last_activity_at + ttl < now
        stmt = (
            select(Session)
            .where(Session.ttl.isnot(None))
            .where(Session.ended_at.is_(None))
            .where(
                Session.last_activity_at + func.make_interval(0, 0, 0, 0, 0, 0, Session.ttl) < now
            )
            .limit(batch_size)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted sessions
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        stmt = delete(Session).where(Session.last_activity_at < cutoff_date)

        result = await self.db.execute(stmt)
        await self.db.flush()

        return result.rowcount if result.rowcount else 0

    async def list_sessions(
        self,
        scope: dict | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Session]:
        """
        List sessions with optional filtering.

        Args:
            scope: Optional scope to filter by
            active_only: If True, only return active (non-ended) sessions
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of sessions ordered by last_activity_at descending
        """
        stmt = select(Session).order_by(Session.last_activity_at.desc()).limit(limit).offset(offset)

        if scope:
            stmt = stmt.where(Session.scope == scope)

        if active_only:
            stmt = stmt.where(Session.ended_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_sessions(
        self,
        scope: dict | None = None,
        active_only: bool = True,
    ) -> int:
        """
        Count sessions with optional filtering.

        Args:
            scope: Optional scope to filter by
            active_only: If True, only count active (non-ended) sessions

        Returns:
            Number of sessions
        """
        stmt = select(func.count()).select_from(Session)

        if scope:
            stmt = stmt.where(Session.scope == scope)

        if active_only:
            stmt = stmt.where(Session.ended_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_scope(self, scope: dict) -> int:
        """
        Count sessions for a given scope.

        Args:
            scope: Scope to count

        Returns:
            Number of sessions
        """
        stmt = (
            select(func.count())
            .select_from(Session)
            .where(Session.scope == scope)
            .where(Session.ended_at.is_(None))
        )

        result = await self.db.execute(stmt)
        return result.scalar_one()
