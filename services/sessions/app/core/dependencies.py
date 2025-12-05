"""
Dependency injection for sessions service.

Provides FastAPI dependencies for database sessions and repositories.
"""

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from services.sessions.app.core.config import SessionsServiceSettings, get_settings
from services.sessions.app.db.repositories.event_repository import EventRepository
from services.sessions.app.db.repositories.session_repository import SessionRepository

# Global engine (initialized once)
_engine = None
_async_session_maker = None
_redis_client = None


def get_engine(settings: SessionsServiceSettings) -> AsyncEngine:
    """
    Get or create database engine.

    Args:
        settings: Service settings

    Returns:
        SQLAlchemy async engine
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            echo=settings.database_echo,
        )
    return _engine


def get_session_maker(settings: SessionsServiceSettings) -> Any:
    """
    Get or create session maker.

    Args:
        settings: Service settings

    Returns:
        SQLAlchemy session maker
    """
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine(settings)
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_db_session(
    settings: Annotated[SessionsServiceSettings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.

    Args:
        settings: Service settings

    Yields:
        Database session
    """
    session_maker = get_session_maker(settings)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis_client(
    settings: Annotated[SessionsServiceSettings, Depends(get_settings)],
) -> AsyncGenerator[Redis, None]:
    """
    Get Redis client dependency.

    Args:
        settings: Service settings

    Yields:
        Redis client
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=settings.redis_decode_responses,
            socket_timeout=settings.redis_socket_timeout,
        )
    try:
        yield _redis_client
    finally:
        # Don't close the connection, reuse it
        pass


def get_session_repository(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionRepository:
    """
    Get session repository dependency.

    Args:
        db: Database session

    Returns:
        Session repository instance
    """
    return SessionRepository(db)


def get_event_repository(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventRepository:
    """
    Get event repository dependency.

    Args:
        db: Database session

    Returns:
        Event repository instance
    """
    return EventRepository(db)


async def close_connections() -> None:
    """Close all global connections."""
    global _engine, _redis_client

    if _engine is not None:
        await _engine.dispose()
        _engine = None

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
