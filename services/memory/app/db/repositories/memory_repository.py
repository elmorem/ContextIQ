"""
Memory repository for database operations.

Provides CRUD operations and queries for Memory model.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.db.models import Memory
from services.memory.app.db.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    """Repository for Memory model."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize memory repository.

        Args:
            db_session: Database session
        """
        super().__init__(db_session, Memory)

    async def create_memory(
        self,
        scope: dict,
        fact: str,
        source_type: str,
        topic: str | None = None,
        embedding: list[float] | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        source_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> Memory:
        """
        Create a new memory.

        Args:
            scope: User/session scope
            fact: Memory fact or statement
            source_type: Source of memory
            topic: Optional topic category
            embedding: Optional vector embedding
            confidence: Confidence score (0-1)
            importance: Importance score (0-1)
            source_id: Optional source ID reference
            expires_at: Optional expiration timestamp

        Returns:
            Created memory instance
        """
        return await self.create(
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

    async def get_by_scope(
        self,
        scope: dict,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[Memory]:
        """
        Get memories by scope.

        Args:
            scope: Scope to filter by
            limit: Maximum number of memories to return
            offset: Number of memories to skip
            include_deleted: Whether to include soft-deleted memories

        Returns:
            List of matching memories
        """
        stmt = (
            select(Memory)
            .where(Memory.scope == scope)
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if not include_deleted:
            stmt = stmt.where(Memory.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_topic(
        self,
        scope: dict,
        topic: str,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[Memory]:
        """
        Get memories by topic.

        Args:
            scope: Scope to filter by
            topic: Topic to filter by
            limit: Maximum number of memories to return
            include_deleted: Whether to include soft-deleted memories

        Returns:
            List of matching memories
        """
        stmt = (
            select(Memory)
            .where(Memory.scope == scope)
            .where(Memory.topic == topic)
            .order_by(Memory.importance.desc())
            .limit(limit)
        )

        if not include_deleted:
            stmt = stmt.where(Memory.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_source(
        self,
        source_type: str,
        source_id: UUID,
        include_deleted: bool = False,
    ) -> list[Memory]:
        """
        Get memories by source.

        Args:
            source_type: Type of source
            source_id: ID of source
            include_deleted: Whether to include soft-deleted memories

        Returns:
            List of matching memories
        """
        stmt = (
            select(Memory)
            .where(Memory.source_type == source_type)
            .where(Memory.source_id == source_id)
            .order_by(Memory.created_at.desc())
        )

        if not include_deleted:
            stmt = stmt.where(Memory.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_access(self, memory_id: UUID) -> Memory | None:
        """
        Update memory access tracking.

        Args:
            memory_id: Memory ID

        Returns:
            Updated memory or None if not found
        """
        memory = await self.get_by_id(memory_id)
        if memory is None:
            return None

        memory.access_count += 1
        memory.last_accessed_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def soft_delete(self, memory_id: UUID) -> Memory | None:
        """
        Soft delete a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Soft-deleted memory or None if not found
        """
        memory = await self.get_by_id(memory_id)
        if memory is None:
            return None

        memory.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def restore(self, memory_id: UUID) -> Memory | None:
        """
        Restore a soft-deleted memory.

        Args:
            memory_id: Memory ID

        Returns:
            Restored memory or None if not found
        """
        memory = await self.get_by_id(memory_id)
        if memory is None:
            return None

        memory.deleted_at = None
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def list_memories(
        self,
        scope: dict | None = None,
        topic: str | None = None,
        source_type: str | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        """
        List memories with optional filtering.

        Args:
            scope: Optional scope filter
            topic: Optional topic filter
            source_type: Optional source type filter
            include_deleted: Whether to include soft-deleted memories
            limit: Maximum number of memories to return
            offset: Number of memories to skip

        Returns:
            List of memories ordered by importance then creation date
        """
        stmt = (
            select(Memory)
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if scope:
            stmt = stmt.where(Memory.scope == scope)

        if topic:
            stmt = stmt.where(Memory.topic == topic)

        if source_type:
            stmt = stmt.where(Memory.source_type == source_type)

        if not include_deleted:
            stmt = stmt.where(Memory.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_memories(
        self,
        scope: dict | None = None,
        topic: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Count memories with optional filtering.

        Args:
            scope: Optional scope filter
            topic: Optional topic filter
            include_deleted: Whether to include soft-deleted memories

        Returns:
            Number of memories
        """
        stmt = select(func.count()).select_from(Memory)

        if scope:
            stmt = stmt.where(Memory.scope == scope)

        if topic:
            stmt = stmt.where(Memory.topic == topic)

        if not include_deleted:
            stmt = stmt.where(Memory.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_expired_memories(self, batch_size: int = 100) -> list[Memory]:
        """
        Get expired memories that should be removed.

        Args:
            batch_size: Maximum number of memories to return

        Returns:
            List of expired memories
        """
        now = datetime.now(UTC)

        stmt = (
            select(Memory)
            .where(Memory.expires_at.isnot(None))
            .where(Memory.expires_at <= now)
            .where(Memory.deleted_at.is_(None))
            .limit(batch_size)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_expired_memories(self) -> int:
        """
        Soft delete all expired memories.

        Returns:
            Number of memories soft-deleted
        """
        expired = await self.get_expired_memories(batch_size=1000)
        now = datetime.now(UTC)

        count = 0
        for memory in expired:
            memory.deleted_at = now
            count += 1

        if count > 0:
            await self.db.flush()

        return count
