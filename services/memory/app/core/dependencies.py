"""
Dependency injection for memory service.

Provides FastAPI dependencies for services and repositories.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.core.config import MemoryServiceSettings, get_settings
from services.memory.app.services.memory_service import MemoryService
from services.memory.app.services.revision_service import RevisionService
from shared.database.session import get_db_session


async def get_memory_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[MemoryServiceSettings, Depends(get_settings)],
) -> MemoryService:
    """
    Get memory service instance.

    Args:
        db: Database session
        settings: Service settings

    Returns:
        MemoryService instance
    """
    return MemoryService(db, settings)


async def get_revision_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RevisionService:
    """
    Get revision service instance.

    Args:
        db: Database session

    Returns:
        RevisionService instance
    """
    return RevisionService(db)
