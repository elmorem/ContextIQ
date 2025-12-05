"""
Session service for managing conversation sessions.

Provides business logic layer for session management, state handling, and expiry.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from redis.asyncio import Redis

from services.sessions.app.core.config import SessionsServiceSettings
from services.sessions.app.db.models import Event, Session
from services.sessions.app.db.repositories.event_repository import EventRepository
from services.sessions.app.db.repositories.session_repository import SessionRepository


class SessionNotFoundError(Exception):
    """Raised when a session is not found."""

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class SessionExpiredError(Exception):
    """Raised when trying to use an expired session."""

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        super().__init__(f"Session expired: {session_id}")


class InvalidTTLError(Exception):
    """Raised when TTL exceeds maximum allowed."""

    def __init__(self, ttl: int, max_ttl: int):
        self.ttl = ttl
        self.max_ttl = max_ttl
        super().__init__(f"TTL {ttl} exceeds maximum {max_ttl}")


class SessionService:
    """Service for managing sessions."""

    def __init__(
        self,
        session_repo: SessionRepository,
        event_repo: EventRepository,
        settings: SessionsServiceSettings,
        redis_client: Redis | None = None,
    ):
        """
        Initialize session service.

        Args:
            session_repo: Session repository
            event_repo: Event repository
            settings: Service settings
            redis_client: Optional Redis client for caching
        """
        self.session_repo = session_repo
        self.event_repo = event_repo
        self.settings = settings
        self.redis = redis_client

    def _get_cache_key(self, session_id: UUID) -> str:
        """Get cache key for session."""
        return f"session:{session_id}"

    async def _get_from_cache(self, session_id: UUID) -> Session | None:
        """Get session from cache."""
        if not self.redis or not self.settings.enable_cache:
            return None

        key = self._get_cache_key(session_id)
        data = await self.redis.get(key)
        if data:
            # Deserialize session data
            # Note: This is simplified - in production, use proper serialization
            return None  # For now, skip cache
        return None

    async def _set_in_cache(self, session: Session) -> None:
        """Set session in cache."""
        if not self.redis or not self.settings.enable_cache:
            return

        key = self._get_cache_key(session.id)
        # Note: This is simplified - in production, use proper serialization
        await self.redis.setex(
            key,
            self.settings.cache_ttl,
            json.dumps({"id": str(session.id)}),
        )

    async def _invalidate_cache(self, session_id: UUID) -> None:
        """Invalidate session cache."""
        if not self.redis or not self.settings.enable_cache:
            return

        key = self._get_cache_key(session_id)
        await self.redis.delete(key)

    def _is_expired(self, session: Session) -> bool:
        """Check if session is expired."""
        if session.ended_at is not None:
            return True

        if session.ttl is None:
            return False

        now = datetime.now(UTC)
        expiry_time = session.last_activity_at.replace(tzinfo=UTC) + timedelta(seconds=session.ttl)
        return now >= expiry_time

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
            scope: Session scope for isolation (e.g., {"user_id": "123"})
            title: Optional session title
            description: Optional session description
            state: Initial state dictionary
            ttl: Time to live in seconds (defaults to settings default)

        Returns:
            Created session

        Raises:
            InvalidTTLError: If TTL exceeds maximum
        """
        # Validate TTL
        if ttl is None:
            ttl = self.settings.default_session_ttl
        elif ttl > self.settings.max_session_ttl:
            raise InvalidTTLError(ttl, self.settings.max_session_ttl)

        # Create session
        session = await self.session_repo.create_session(
            scope=scope,
            title=title,
            description=description,
            state=state or {},
            ttl=ttl,
        )

        # Cache session
        await self._set_in_cache(session)

        return session

    async def get_session(self, session_id: UUID) -> Session:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session instance

        Raises:
            SessionNotFoundError: If session not found
            SessionExpiredError: If session is expired
        """
        # Try cache first
        session = await self._get_from_cache(session_id)

        # Fall back to database
        if session is None:
            session = await self.session_repo.get_by_id(session_id)

        if session is None:
            raise SessionNotFoundError(session_id)

        # Check if expired
        if self._is_expired(session):
            raise SessionExpiredError(session_id)

        # Update cache
        await self._set_in_cache(session)

        return session

    async def update_session_state(
        self,
        session_id: UUID,
        state: dict,
        merge: bool = False,
    ) -> Session:
        """
        Update session state.

        Args:
            session_id: Session ID
            state: New state dictionary
            merge: If True, merge with existing state; if False, replace

        Returns:
            Updated session

        Raises:
            SessionNotFoundError: If session not found
            SessionExpiredError: If session is expired
        """
        # Get session (validates existence and expiry)
        session = await self.get_session(session_id)

        # Merge or replace state
        if merge:
            new_state = {**session.state, **state}
        else:
            new_state = state

        # Update state
        updated = await self.session_repo.update_state(session_id, new_state)
        if updated is None:
            raise SessionNotFoundError(session_id)

        # Invalidate cache
        await self._invalidate_cache(session_id)

        return updated

    async def update_activity(self, session_id: UUID) -> Session:
        """
        Update session activity timestamp.

        Args:
            session_id: Session ID

        Returns:
            Updated session

        Raises:
            SessionNotFoundError: If session not found
            SessionExpiredError: If session is expired
        """
        # Get session (validates existence and expiry)
        await self.get_session(session_id)

        # Update activity
        updated = await self.session_repo.update_activity(session_id)
        if updated is None:
            raise SessionNotFoundError(session_id)

        # Invalidate cache
        await self._invalidate_cache(session_id)

        return updated

    async def end_session(self, session_id: UUID) -> Session:
        """
        End a session.

        Args:
            session_id: Session ID

        Returns:
            Ended session

        Raises:
            SessionNotFoundError: If session not found
        """
        # End session (no expiry check needed)
        ended = await self.session_repo.end_session(session_id)
        if ended is None:
            raise SessionNotFoundError(session_id)

        # Invalidate cache
        await self._invalidate_cache(session_id)

        return ended

    async def add_event(
        self,
        session_id: UUID,
        event_type: str,
        data: dict,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> Event:
        """
        Add an event to a session.

        Args:
            session_id: Session ID
            event_type: Type of event
            data: Event data
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Created event

        Raises:
            SessionNotFoundError: If session not found
            SessionExpiredError: If session is expired
        """
        # Validate session exists and is not expired
        await self.get_session(session_id)

        # Create event
        event = await self.event_repo.create_event(
            session_id=session_id,
            event_type=event_type,
            data=data,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Update session activity
        await self.session_repo.update_activity(session_id)

        # Invalidate cache
        await self._invalidate_cache(session_id)

        return event

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
            limit: Maximum number of events
            offset: Number of events to skip

        Returns:
            List of events

        Raises:
            SessionNotFoundError: If session not found
        """
        # Validate session exists
        await self.get_session(session_id)

        # Get events
        return await self.event_repo.get_session_events(session_id, limit, offset)

    async def get_sessions_by_scope(
        self,
        scope: dict,
        limit: int = 100,
    ) -> list[Session]:
        """
        Get sessions by scope.

        Args:
            scope: Scope dictionary
            limit: Maximum number of sessions

        Returns:
            List of sessions
        """
        return await self.session_repo.get_by_scope(scope, limit)

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions ended
        """
        expired = await self.session_repo.get_expired_sessions(
            batch_size=self.settings.session_cleanup_batch_size
        )

        count = 0
        for session in expired:
            await self.session_repo.end_session(session.id)
            await self._invalidate_cache(session.id)
            count += 1

        return count

    async def cleanup_old_sessions(self) -> int:
        """
        Delete old sessions.

        Returns:
            Number of sessions deleted
        """
        return await self.session_repo.delete_old_sessions(days=self.settings.session_cleanup_days)
