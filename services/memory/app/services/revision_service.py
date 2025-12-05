"""
Revision service for memory history tracking.

Manages revision creation and retrieval.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.db.models import MemoryRevision
from services.memory.app.db.repositories.revision_repository import RevisionRepository


class RevisionService:
    """Service for managing memory revisions."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize revision service.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.revision_repo = RevisionRepository(db_session)

    async def create_revision(
        self,
        memory_id: UUID,
        previous_fact: str,
        new_fact: str,
        change_reason: str | None = None,
    ) -> MemoryRevision:
        """
        Create a new revision for a memory.

        Args:
            memory_id: ID of the memory being revised
            previous_fact: The fact before the change
            new_fact: The fact after the change
            change_reason: Optional reason for the change

        Returns:
            Created revision instance
        """
        # Get the next revision number
        revision_number = await self.revision_repo.get_next_revision_number(memory_id)

        # Create the revision
        revision = await self.revision_repo.create_revision(
            memory_id=memory_id,
            revision_number=revision_number,
            previous_fact=previous_fact,
            new_fact=new_fact,
            change_reason=change_reason,
        )

        return revision

    async def get_memory_history(
        self,
        memory_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> list[MemoryRevision]:
        """
        Get revision history for a memory.

        Args:
            memory_id: Memory ID
            limit: Maximum number of revisions to return
            offset: Number of revisions to skip

        Returns:
            List of revisions ordered by revision number descending
        """
        return await self.revision_repo.get_memory_revisions(
            memory_id,
            limit=limit,
            offset=offset,
        )

    async def get_latest_revision(self, memory_id: UUID) -> MemoryRevision | None:
        """
        Get the most recent revision for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Latest revision or None if no revisions exist
        """
        return await self.revision_repo.get_latest_revision(memory_id)

    async def get_revision_by_number(
        self,
        memory_id: UUID,
        revision_number: int,
    ) -> MemoryRevision | None:
        """
        Get a specific revision by its number.

        Args:
            memory_id: Memory ID
            revision_number: Revision number to retrieve

        Returns:
            Revision or None if not found
        """
        return await self.revision_repo.get_revision_by_number(
            memory_id,
            revision_number,
        )

    async def count_revisions(self, memory_id: UUID) -> int:
        """
        Count total revisions for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Number of revisions
        """
        return await self.revision_repo.count_revisions(memory_id)

    async def delete_memory_revisions(self, memory_id: UUID) -> int:
        """
        Delete all revisions for a memory.

        Used when a memory is permanently deleted.

        Args:
            memory_id: Memory ID

        Returns:
            Number of revisions deleted
        """
        return await self.revision_repo.delete_memory_revisions(memory_id)

    async def prune_old_revisions(
        self,
        memory_id: UUID,
        max_revisions: int,
    ) -> int:
        """
        Prune old revisions to keep only the most recent ones.

        Args:
            memory_id: Memory ID
            max_revisions: Maximum number of revisions to keep

        Returns:
            Number of revisions deleted
        """
        # Get all revisions ordered newest first
        all_revisions = await self.revision_repo.get_memory_revisions(
            memory_id,
            limit=1000,  # Reasonable upper bound
            offset=0,
        )

        # If we have more than max_revisions, delete the oldest ones
        if len(all_revisions) <= max_revisions:
            return 0

        # Get revisions to delete (oldest ones)
        revisions_to_delete = all_revisions[max_revisions:]

        # Delete each revision
        count = 0
        for revision in revisions_to_delete:
            await self.revision_repo.delete(revision)
            count += 1

        return count
