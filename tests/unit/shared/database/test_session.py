"""Tests for database session management."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import DatabaseConnection
from shared.database.session import (
    close_database,
    get_database_url,
    get_db_connection,
    get_db_session,
    init_database,
)


class TestGetDatabaseUrl:
    """Test get_database_url function."""

    def test_get_database_url_success(self):
        """Test getting database URL from environment."""
        test_url = "postgresql+asyncpg://test:test@localhost/testdb"

        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            url = get_database_url()
            assert url == test_url

    def test_get_database_url_missing(self):
        """Test error when DATABASE_URL not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL environment variable is not set"):
                get_database_url()


class TestInitDatabase:
    """Test init_database function."""

    def teardown_method(self):
        """Clean up global connection after each test."""
        import shared.database.session

        shared.database.session._db_connection = None

    def test_init_database_with_url(self):
        """Test database initialization with explicit URL."""
        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        connection = init_database(url=test_url)

        assert isinstance(connection, DatabaseConnection)
        assert connection.config.url == test_url
        assert connection.config.pool_size == 5

    def test_init_database_with_env_url(self):
        """Test database initialization from environment."""
        test_url = "postgresql+asyncpg://env:env@localhost/envdb"

        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            connection = init_database()

            assert isinstance(connection, DatabaseConnection)
            assert connection.config.url == test_url

    def test_init_database_with_custom_pool_settings(self):
        """Test database initialization with custom pool settings."""
        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        connection = init_database(
            url=test_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=60.0,
            pool_recycle=7200,
            echo=True,
        )

        assert connection.config.pool_size == 10
        assert connection.config.max_overflow == 20
        assert connection.config.pool_timeout == 60.0
        assert connection.config.pool_recycle == 7200
        assert connection.config.echo is True

    def test_init_database_sets_global(self):
        """Test that init_database sets global connection."""
        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        connection1 = init_database(url=test_url)
        connection2 = get_db_connection()

        assert connection1 is connection2


class TestGetDbConnection:
    """Test get_db_connection function."""

    def teardown_method(self):
        """Clean up global connection after each test."""
        import shared.database.session

        shared.database.session._db_connection = None

    def test_get_db_connection_success(self):
        """Test getting initialized connection."""
        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        init_database(url=test_url)

        connection = get_db_connection()
        assert isinstance(connection, DatabaseConnection)

    def test_get_db_connection_not_initialized(self):
        """Test error when connection not initialized."""
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_db_connection()


class TestGetDbSession:
    """Test get_db_session function."""

    def teardown_method(self):
        """Clean up global connection after each test."""
        import shared.database.session

        shared.database.session._db_connection = None

    @pytest.mark.asyncio
    async def test_get_db_session_success(self):
        """Test getting database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_connection = MagicMock(spec=DatabaseConnection)

        async def mock_get_session():
            yield mock_session

        mock_connection.get_session = mock_get_session

        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        init_database(url=test_url)

        with patch("shared.database.session.get_db_connection", return_value=mock_connection):
            async for session in get_db_session():
                assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_db_session_not_initialized(self):
        """Test error when database not initialized."""
        with pytest.raises(RuntimeError, match="Database not initialized"):
            async for _ in get_db_session():
                pass


class TestCloseDatabase:
    """Test close_database function."""

    def teardown_method(self):
        """Clean up global connection after each test."""
        import shared.database.session

        shared.database.session._db_connection = None

    @pytest.mark.asyncio
    async def test_close_database_success(self):
        """Test closing database connection."""
        mock_connection = AsyncMock(spec=DatabaseConnection)

        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        init_database(url=test_url)

        with patch("shared.database.session._db_connection", mock_connection):
            await close_database()
            mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_database_not_initialized(self):
        """Test closing when not initialized."""
        # Should not raise
        await close_database()

    @pytest.mark.asyncio
    async def test_close_database_clears_global(self):
        """Test that close_database clears global connection."""
        import shared.database.session

        test_url = "postgresql+asyncpg://test:test@localhost/testdb"
        init_database(url=test_url)

        assert shared.database.session._db_connection is not None

        with patch.object(shared.database.session._db_connection, "close", new_callable=AsyncMock):
            await close_database()

        assert shared.database.session._db_connection is None
