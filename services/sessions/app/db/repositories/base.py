"""
Base repository class for sessions service.

Provides common CRUD operations and database session management.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, db_session: AsyncSession, model: type[ModelType]):
        """
        Initialize repository.

        Args:
            db_session: Database session
            model: SQLAlchemy model class
        """
        self.db = db_session
        self.model = model

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """
        Get record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        """
        Update a record.

        Args:
            instance: Model instance to update
            **kwargs: Fields to update

        Returns:
            Updated model instance
        """
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """
        Delete a record.

        Args:
            instance: Model instance to delete
        """
        await self.db.delete(instance)
        await self.db.flush()

    async def commit(self) -> None:
        """Commit current transaction."""
        await self.db.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.db.rollback()
