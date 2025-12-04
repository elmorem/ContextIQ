"""
Tests for database session management.
"""


import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import (
    close_database,
    get_database_url,
    get_db_connection,
    get_db_session,
    init_database,
)


@pytest.mark.unit
def test_get_database_url_from_env(monkeypatch):
    """Test getting database URL from environment."""
    test_url = "postgresql+asyncpg://test:test@localhost/test"
    monkeypatch.setenv("DATABASE_URL", test_url)

    url = get_database_url()

    assert url == test_url


@pytest.mark.unit
def test_get_database_url_missing_raises_error(monkeypatch):
    """Test that missing DATABASE_URL raises ValueError."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL environment variable is not set"):
        get_database_url()


@pytest.mark.unit
def test_init_database_with_url():
    """Test initializing database with explicit URL."""
    test_url = "postgresql+asyncpg://test:test@localhost/test"

    conn = init_database(url=test_url)

    assert conn is not None
    assert conn.config.url == test_url
    assert conn.config.pool_size == 5


@pytest.mark.unit
def test_init_database_with_custom_settings():
    """Test initializing database with custom settings."""
    test_url = "postgresql+asyncpg://test:test@localhost/test"

    conn = init_database(url=test_url, pool_size=10, max_overflow=20, echo=True)

    assert conn.config.pool_size == 10
    assert conn.config.max_overflow == 20
    assert conn.config.echo is True


@pytest.mark.unit
def test_init_database_from_env(monkeypatch):
    """Test initializing database from environment variable."""
    test_url = "postgresql+asyncpg://test:test@localhost/test"
    monkeypatch.setenv("DATABASE_URL", test_url)

    conn = init_database()

    assert conn is not None
    assert conn.config.url == test_url


@pytest.mark.unit
def test_get_db_connection_after_init():
    """Test getting database connection after initialization."""
    test_url = "postgresql+asyncpg://test:test@localhost/test"
    init_database(url=test_url)

    conn = get_db_connection()

    assert conn is not None
    assert conn.config.url == test_url


@pytest.mark.unit
def test_get_db_connection_before_init_raises_error():
    """Test that getting connection before init raises RuntimeError."""
    # Close any existing connection
    import shared.database.session as session_module

    session_module._db_connection = None

    with pytest.raises(RuntimeError, match="Database not initialized"):
        get_db_connection()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_db_session(test_engine):
    """Test getting database session for dependency injection."""
    test_url = str(test_engine.url)
    init_database(url=test_url)

    async for session in get_db_session():
        assert isinstance(session, AsyncSession)
        assert session.is_active

    await close_database()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_close_database():
    """Test closing database connection."""
    test_url = "postgresql+asyncpg://test:test@localhost/test"
    conn = init_database(url=test_url)

    # Get engine to initialize it
    conn.get_engine()

    # Close database
    await close_database()

    # Verify connection was closed
    import shared.database.session as session_module

    assert session_module._db_connection is None
