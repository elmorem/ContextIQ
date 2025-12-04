"""
Tests for database connection management.
"""

from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import DatabaseConfig, DatabaseConnection


@pytest.mark.unit
def test_database_config_initialization():
    """Test DatabaseConfig initialization with defaults."""
    config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")

    assert config.url == "postgresql+asyncpg://localhost/test"
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.pool_timeout == 30.0
    assert config.pool_recycle == 3600
    assert config.echo is False


@pytest.mark.unit
def test_database_config_custom_values():
    """Test DatabaseConfig initialization with custom values."""
    config = DatabaseConfig(
        url="postgresql+asyncpg://localhost/test",
        pool_size=10,
        max_overflow=20,
        pool_timeout=60.0,
        pool_recycle=7200,
        echo=True,
    )

    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 60.0
    assert config.pool_recycle == 7200
    assert config.echo is True


@pytest.mark.unit
def test_database_connection_initialization():
    """Test DatabaseConnection initialization."""
    config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
    conn = DatabaseConnection(config)

    assert conn.config == config
    assert conn._engine is None
    assert conn._session_factory is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_get_engine(test_engine):
    """Test getting database engine."""
    config = DatabaseConfig(url=str(test_engine.url))
    conn = DatabaseConnection(config)

    engine = conn.get_engine()

    assert engine is not None
    assert conn._engine is engine
    # Getting engine again should return same instance
    assert conn.get_engine() is engine

    await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_get_session_factory(test_engine):
    """Test getting session factory."""
    config = DatabaseConfig(url=str(test_engine.url))
    conn = DatabaseConnection(config)

    factory = conn.get_session_factory()

    assert factory is not None
    assert conn._session_factory is factory
    # Getting factory again should return same instance
    assert conn.get_session_factory() is factory

    await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_get_session(test_engine):
    """Test getting database session."""
    config = DatabaseConfig(url=str(test_engine.url))
    conn = DatabaseConnection(config)

    async for session in conn.get_session():
        assert isinstance(session, AsyncSession)
        assert session.is_active

    await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_session_commit(test_db):
    """Test that session commits on success."""
    from shared.models.session import Session as SessionModel

    config = DatabaseConfig(url=str(test_db.bind.url))
    conn = DatabaseConnection(config)

    session_id = None

    # Create a session within the context manager
    async for session in conn.get_session():
        from datetime import datetime

        new_session = SessionModel(
            scope={"user_id": "test"},
            state={},
            started_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        session.add(new_session)
        session_id = new_session.id

    # Verify session was committed
    async for session in conn.get_session():
        from sqlalchemy import select

        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        found_session = result.scalar_one_or_none()
        assert found_session is not None
        assert found_session.scope == {"user_id": "test"}

    await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_session_rollback_on_error(test_db):
    """Test that session rolls back on error."""
    from shared.models.session import Session as SessionModel

    config = DatabaseConfig(url=str(test_db.bind.url))
    conn = DatabaseConnection(config)

    # Try to create a session that will fail
    with pytest.raises(ValueError, match="Test error"):
        async for session in conn.get_session():
            from datetime import datetime

            new_session = SessionModel(
                scope={"user_id": "test"},
                state={},
                started_at=datetime.now(UTC),
                last_activity_at=datetime.now(UTC),
            )
            session.add(new_session)
            raise ValueError("Test error")

    # Verify nothing was committed
    async for session in conn.get_session():
        from sqlalchemy import select

        result = await session.execute(select(SessionModel))
        sessions = result.scalars().all()
        assert len(sessions) == 0

    await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_close(test_engine):
    """Test closing database connection."""
    config = DatabaseConfig(url=str(test_engine.url))
    conn = DatabaseConnection(config)

    # Get engine to initialize it
    engine = conn.get_engine()
    assert engine is not None

    # Close connection
    await conn.close()

    assert conn._engine is None
    assert conn._session_factory is None
