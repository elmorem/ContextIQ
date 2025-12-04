"""
Cache key patterns and builders.
"""

from typing import Any


class CacheKeys:
    """Cache key patterns for different entity types."""

    # Key prefixes
    SESSION_PREFIX = "session"
    MEMORY_PREFIX = "memory"
    PROCEDURAL_MEMORY_PREFIX = "procedural"
    USER_PREFIX = "user"
    AGENT_PREFIX = "agent"
    JOB_PREFIX = "job"

    # Key separators
    SEPARATOR = ":"

    @classmethod
    def session(cls, session_id: str) -> str:
        """
        Generate cache key for a session.

        Args:
            session_id: Session ID

        Returns:
            Cache key
        """
        return f"{cls.SESSION_PREFIX}{cls.SEPARATOR}{session_id}"

    @classmethod
    def session_events(cls, session_id: str) -> str:
        """
        Generate cache key for session events.

        Args:
            session_id: Session ID

        Returns:
            Cache key
        """
        return f"{cls.SESSION_PREFIX}{cls.SEPARATOR}{session_id}{cls.SEPARATOR}events"

    @classmethod
    def session_state(cls, session_id: str) -> str:
        """
        Generate cache key for session state.

        Args:
            session_id: Session ID

        Returns:
            Cache key
        """
        return f"{cls.SESSION_PREFIX}{cls.SEPARATOR}{session_id}{cls.SEPARATOR}state"

    @classmethod
    def memory(cls, memory_id: str) -> str:
        """
        Generate cache key for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Cache key
        """
        return f"{cls.MEMORY_PREFIX}{cls.SEPARATOR}{memory_id}"

    @classmethod
    def memories_by_scope(cls, scope_hash: str) -> str:
        """
        Generate cache key for memories by scope.

        Args:
            scope_hash: Hashed scope

        Returns:
            Cache key
        """
        return f"{cls.MEMORY_PREFIX}{cls.SEPARATOR}scope{cls.SEPARATOR}{scope_hash}"

    @classmethod
    def procedural_memory(cls, memory_id: str) -> str:
        """
        Generate cache key for procedural memory.

        Args:
            memory_id: Procedural memory ID

        Returns:
            Cache key
        """
        return f"{cls.PROCEDURAL_MEMORY_PREFIX}{cls.SEPARATOR}{memory_id}"

    @classmethod
    def procedural_memories_by_type(cls, scope_hash: str, memory_type: str) -> str:
        """
        Generate cache key for procedural memories by type.

        Args:
            scope_hash: Hashed scope
            memory_type: Memory type

        Returns:
            Cache key
        """
        return f"{cls.PROCEDURAL_MEMORY_PREFIX}{cls.SEPARATOR}scope{cls.SEPARATOR}{scope_hash}{cls.SEPARATOR}{memory_type}"

    @classmethod
    def user_sessions(cls, user_id: str) -> str:
        """
        Generate cache key for user sessions.

        Args:
            user_id: User ID

        Returns:
            Cache key
        """
        return f"{cls.USER_PREFIX}{cls.SEPARATOR}{user_id}{cls.SEPARATOR}sessions"

    @classmethod
    def agent_sessions(cls, agent_id: str) -> str:
        """
        Generate cache key for agent sessions.

        Args:
            agent_id: Agent ID

        Returns:
            Cache key
        """
        return f"{cls.AGENT_PREFIX}{cls.SEPARATOR}{agent_id}{cls.SEPARATOR}sessions"

    @classmethod
    def extraction_job(cls, job_id: str) -> str:
        """
        Generate cache key for extraction job.

        Args:
            job_id: Job ID

        Returns:
            Cache key
        """
        return f"{cls.JOB_PREFIX}{cls.SEPARATOR}extraction{cls.SEPARATOR}{job_id}"

    @classmethod
    def consolidation_job(cls, job_id: str) -> str:
        """
        Generate cache key for consolidation job.

        Args:
            job_id: Job ID

        Returns:
            Cache key
        """
        return f"{cls.JOB_PREFIX}{cls.SEPARATOR}consolidation{cls.SEPARATOR}{job_id}"

    @classmethod
    def custom(cls, *parts: Any) -> str:
        """
        Generate custom cache key from parts.

        Args:
            *parts: Key parts to join

        Returns:
            Cache key
        """
        return cls.SEPARATOR.join(str(part) for part in parts)
