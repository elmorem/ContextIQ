"""
Memory service for core business logic.

Manages memory creation, updates, and lifecycle with confidence tracking.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.core.config import MemoryServiceSettings, get_settings
from services.memory.app.db.models import Memory
from services.memory.app.db.repositories.memory_repository import MemoryRepository
from services.memory.app.services.revision_service import RevisionService


class MemoryService:
    """Service for managing episodic memories."""

    def __init__(
        self,
        db_session: AsyncSession,
        settings: MemoryServiceSettings | None = None,
    ):
        """
        Initialize memory service.

        Args:
            db_session: Database session
            settings: Optional service settings (defaults to global settings)
        """
        self.db = db_session
        self.settings = settings or get_settings()
        self.memory_repo = MemoryRepository(db_session)
        self.revision_service = RevisionService(db_session)

    async def create_memory(
        self,
        scope: dict,
        fact: str,
        source_type: str,
        topic: str | None = None,
        embedding: list[float] | None = None,
        confidence: float | None = None,
        importance: float | None = None,
        source_id: UUID | None = None,
        ttl_days: int | None = None,
    ) -> Memory:
        """
        Create a new memory.

        Args:
            scope: User/session scope for isolation
            fact: The memory fact or statement
            source_type: Source of memory (conversation, extraction, manual)
            topic: Optional topic category
            embedding: Optional vector embedding
            confidence: Optional confidence score (0-1), defaults to config
            importance: Optional importance score (0-1), defaults to config
            source_id: Optional source ID reference
            ttl_days: Optional TTL in days, defaults to config

        Returns:
            Created memory instance
        """
        # Apply defaults from settings
        if confidence is None:
            confidence = self.settings.default_confidence

        if importance is None:
            importance = self.settings.default_importance

        # Calculate expiration if TTL provided
        expires_at = None
        if ttl_days is not None:
            # Cap at max TTL
            ttl_days = min(ttl_days, self.settings.max_memory_ttl_days)
            expires_at = datetime.now(UTC) + timedelta(days=ttl_days)
        elif self.settings.default_memory_ttl_days > 0:
            expires_at = datetime.now(UTC) + timedelta(days=self.settings.default_memory_ttl_days)

        # Create the memory
        memory = await self.memory_repo.create_memory(
            scope=scope,
            fact=fact,
            source_type=source_type,
            topic=topic,
            embedding=embedding,
            confidence=confidence,
            importance=importance,
            source_id=source_id,
            expires_at=expires_at,
        )

        return memory

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        """
        Get a memory by ID and update access tracking.

        Args:
            memory_id: Memory ID

        Returns:
            Memory instance or None if not found
        """
        memory = await self.memory_repo.get_by_id(memory_id)
        if memory is None:
            return None

        # Update access tracking
        await self.memory_repo.update_access(memory_id)

        return memory

    async def update_memory(
        self,
        memory_id: UUID,
        fact: str | None = None,
        topic: str | None = None,
        embedding: list[float] | None = None,
        confidence: float | None = None,
        importance: float | None = None,
        change_reason: str | None = None,
    ) -> Memory | None:
        """
        Update a memory with revision tracking.

        Args:
            memory_id: Memory ID
            fact: Optional new fact
            topic: Optional new topic
            embedding: Optional new embedding
            confidence: Optional new confidence
            importance: Optional new importance
            change_reason: Optional reason for the change

        Returns:
            Updated memory or None if not found
        """
        memory = await self.memory_repo.get_by_id(memory_id)
        if memory is None:
            return None

        # Track fact changes with revisions if enabled
        if fact is not None and fact != memory.fact and self.settings.enable_revision_tracking:
            await self.revision_service.create_revision(
                memory_id=memory_id,
                previous_fact=memory.fact,
                new_fact=fact,
                change_reason=change_reason,
            )
            memory.fact = fact

        # Update other fields
        if topic is not None:
            memory.topic = topic

        if embedding is not None:
            memory.embedding = embedding

        if confidence is not None:
            memory.confidence = confidence

        if importance is not None:
            memory.importance = importance

        # Flush changes
        await self.db.flush()
        await self.db.refresh(memory)

        # Prune old revisions if needed
        if self.settings.enable_revision_tracking:
            await self.revision_service.prune_old_revisions(
                memory_id,
                self.settings.max_revisions_per_memory,
            )

        return memory

    async def update_confidence(
        self,
        memory_id: UUID,
        new_confidence: float,
        decay: bool = False,
    ) -> Memory | None:
        """
        Update memory confidence with optional decay.

        Args:
            memory_id: Memory ID
            new_confidence: New confidence value (0-1)
            decay: Whether to apply decay rate instead of direct update

        Returns:
            Updated memory or None if not found
        """
        memory = await self.memory_repo.get_by_id(memory_id)
        if memory is None:
            return None

        if decay:
            # Apply decay rate to reduce confidence
            memory.confidence = max(
                0.0,
                memory.confidence - self.settings.confidence_decay_rate,
            )
        else:
            # Direct update
            memory.confidence = new_confidence

        # Ensure confidence stays in valid range
        memory.confidence = max(0.0, min(1.0, memory.confidence))

        await self.db.flush()
        await self.db.refresh(memory)

        return memory

    async def delete_memory(self, memory_id: UUID) -> bool:
        """
        Soft delete a memory.

        Args:
            memory_id: Memory ID

        Returns:
            True if deleted, False if not found
        """
        memory = await self.memory_repo.soft_delete(memory_id)
        return memory is not None

    async def restore_memory(self, memory_id: UUID) -> Memory | None:
        """
        Restore a soft-deleted memory.

        Args:
            memory_id: Memory ID

        Returns:
            Restored memory or None if not found
        """
        return await self.memory_repo.restore(memory_id)

    async def get_memories_by_scope(
        self,
        scope: dict,
        topic: str | None = None,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[Memory]:
        """
        Get memories by scope with optional filtering.

        Args:
            scope: Scope to filter by
            topic: Optional topic filter
            limit: Maximum number of memories to return
            offset: Number of memories to skip
            include_deleted: Whether to include soft-deleted memories

        Returns:
            List of matching memories
        """
        if topic:
            return await self.memory_repo.get_by_topic(
                scope=scope,
                topic=topic,
                limit=limit,
                include_deleted=include_deleted,
            )
        else:
            return await self.memory_repo.get_by_scope(
                scope=scope,
                limit=limit,
                offset=offset,
                include_deleted=include_deleted,
            )

    async def get_low_confidence_memories(
        self,
        scope: dict,
        threshold: float | None = None,
    ) -> list[Memory]:
        """
        Get memories with low confidence scores.

        Args:
            scope: Scope to filter by
            threshold: Confidence threshold (defaults to config min threshold)

        Returns:
            List of memories with confidence below threshold
        """
        if threshold is None:
            threshold = self.settings.min_confidence_threshold

        # Get all memories for scope
        memories = await self.memory_repo.get_by_scope(scope, limit=1000)

        # Filter by confidence
        return [m for m in memories if m.confidence < threshold]

    async def cleanup_expired_memories(self) -> int:
        """
        Soft delete expired memories.

        Returns:
            Number of memories deleted
        """
        return await self.memory_repo.delete_expired_memories()

    async def count_memories(
        self,
        scope: dict,
        topic: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Count memories with optional filtering.

        Args:
            scope: Scope to filter by
            topic: Optional topic filter
            include_deleted: Whether to include soft-deleted memories

        Returns:
            Number of memories
        """
        return await self.memory_repo.count_memories(
            scope=scope,
            topic=topic,
            include_deleted=include_deleted,
        )

    async def search_memories(
        self,
        query_embedding: list[float],
        scope: dict | None = None,
        topic: str | None = None,
        limit: int = 10,
        min_confidence: float | None = None,
    ) -> list[tuple[Memory, float]]:
        """
        Search memories by vector similarity.

        Args:
            query_embedding: Query vector embedding
            scope: Optional scope filter
            topic: Optional topic filter
            limit: Maximum number of results (default 10)
            min_confidence: Optional minimum confidence threshold

        Returns:
            List of (Memory, similarity_score) tuples, ordered by similarity (highest first)
        """
        return await self.memory_repo.search_by_similarity(
            query_embedding=query_embedding,
            scope=scope,
            topic=topic,
            limit=limit,
            min_confidence=min_confidence,
            include_deleted=False,
        )
