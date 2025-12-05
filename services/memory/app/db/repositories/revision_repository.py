"""
Revision repository for database operations.

Provides operations for tracking memory revision history.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.db.models import MemoryRevision
from services.memory.app.db.repositories.base import BaseRepository


class RevisionRepository(BaseRepository[MemoryRevision]):
    """Repository for MemoryRevision model."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize revision repository.

        Args:
            db_session: Database session
        """
        super().__init__(db_session, MemoryRevision)

    async def create_revision(
        self,
        memory_id: UUID,
        revision_number: int,
        previous_fact: str,
        new_fact: str,
        change_reason: str | None = None,
    ) -> MemoryRevision:
        """
        Create a new revision record.

        Args:
            memory_id: ID of the memory being revised
            revision_number: Sequential revision number
            previous_fact: The fact before the change
            new_fact: The fact after the change
            change_reason: Optional reason for the change

        Returns:
            Created revision instance
        """
        return await self.create(
            memory_id=memory_id,
            revision_number=revision_number,
            previous_fact=previous_fact,
            new_fact=new_fact,
            change_reason=change_reason,
        )

    async def get_memory_revisions(
        self,
        memory_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryRevision]:
        """
        Get all revisions for a memory.

        Args:
            memory_id: Memory ID
            limit: Maximum number of revisions to return
            offset: Number of revisions to skip

        Returns:
            List of revisions ordered by revision number descending
        """
        stmt = (
            select(MemoryRevision)
            .where(MemoryRevision.memory_id == memory_id)
            .order_by(MemoryRevision.revision_number.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_revision(self, memory_id: UUID) -> MemoryRevision | None:
        """
        Get the most recent revision for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Latest revision or None if no revisions exist
        """
        stmt = (
            select(MemoryRevision)
            .where(MemoryRevision.memory_id == memory_id)
            .order_by(MemoryRevision.revision_number.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_revision_by_number(
        self,
        memory_id: UUID,
        revision_number: int,
    ) -> MemoryRevision | None:
        """
        Get a specific revision by number.

        Args:
            memory_id: Memory ID
            revision_number: Revision number to retrieve

        Returns:
            Revision or None if not found
        """
        stmt = (
            select(MemoryRevision)
            .where(MemoryRevision.memory_id == memory_id)
            .where(MemoryRevision.revision_number == revision_number)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_revisions(self, memory_id: UUID) -> int:
        """
        Count total revisions for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Number of revisions
        """
        stmt = (
            select(func.count())
            .select_from(MemoryRevision)
            .where(MemoryRevision.memory_id == memory_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_next_revision_number(self, memory_id: UUID) -> int:
        """
        Get the next revision number for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Next revision number (1 if no revisions exist)
        """
        count = await self.count_revisions(memory_id)
        return count + 1

    async def get_revision_history(
        self,
        memory_id: UUID,
        limit: int = 10,
    ) -> list[MemoryRevision]:
        """
        Get recent revision history for a memory.

        This is a convenience method that returns the most recent revisions
        in reverse chronological order (newest first).

        Args:
            memory_id: Memory ID
            limit: Maximum number of revisions to return

        Returns:
            List of recent revisions
        """
        return await self.get_memory_revisions(memory_id, limit=limit, offset=0)

    async def delete_memory_revisions(self, memory_id: UUID) -> int:
        """
        Delete all revisions for a memory.

        Note: This should typically be handled by CASCADE on the foreign key,
        but is provided for explicit cleanup if needed.

        Args:
            memory_id: Memory ID

        Returns:
            Number of revisions deleted
        """
        revisions = await self.get_memory_revisions(memory_id, limit=10000)

        for revision in revisions:
            await self.delete(revision)

        await self.db.flush()
        return len(revisions)
