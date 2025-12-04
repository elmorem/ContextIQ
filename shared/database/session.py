"""
Database session management utilities.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import DatabaseConfig, DatabaseConnection

# Global database connection instance
_db_connection: DatabaseConnection | None = None


def get_database_url() -> str:
    """
    Get database URL from environment.

    Returns:
        Database connection URL

    Raises:
        ValueError: If DATABASE_URL is not set
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return url


def init_database(
    url: str | None = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 3600,
    echo: bool = False,
) -> DatabaseConnection:
    """
    Initialize global database connection.

    Args:
        url: Database URL (defaults to DATABASE_URL env var)
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections beyond pool_size
        pool_timeout: Timeout for getting connection from pool
        pool_recycle: Recycle connections after this many seconds
        echo: Echo SQL statements for debugging

    Returns:
        DatabaseConnection instance
    """
    global _db_connection

    if url is None:
        url = get_database_url()

    config = DatabaseConfig(
        url=url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo,
    )

    _db_connection = DatabaseConnection(config)
    return _db_connection


def get_db_connection() -> DatabaseConnection:
    """
    Get global database connection.

    Returns:
        DatabaseConnection instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_connection


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession instance

    Example:
        ```python
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    db_connection = get_db_connection()
    async for session in db_connection.get_session():
        yield session


async def close_database() -> None:
    """Close global database connection."""
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        _db_connection = None
