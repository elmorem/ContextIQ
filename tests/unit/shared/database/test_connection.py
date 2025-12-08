"""Tests for database connection management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from shared.database.connection import DatabaseConfig, DatabaseConnection


class TestDatabaseConfig:
    """Test database configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")

        assert config.url == "postgresql+asyncpg://localhost/test"
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30.0
        assert config.pool_recycle == 3600
        assert config.echo is False

    def test_custom_config(self):
        """Test custom configuration values."""
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


class TestDatabaseConnection:
    """Test database connection management."""

    def test_init(self):
        """Test connection initialization."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)

        assert connection.config == config
        assert connection._engine is None
        assert connection._session_factory is None

    @patch("shared.database.connection.create_async_engine")
    def test_get_engine_creates_new(self, mock_create_engine):
        """Test engine creation on first call."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)

        engine = connection.get_engine()

        assert engine == mock_engine
        mock_create_engine.assert_called_once_with(
            "postgresql+asyncpg://localhost/test",
            pool_size=5,
            max_overflow=10,
            pool_timeout=30.0,
            pool_recycle=3600,
            echo=False,
            pool_pre_ping=True,
        )

    @patch("shared.database.connection.create_async_engine")
    def test_get_engine_returns_cached(self, mock_create_engine):
        """Test engine caching on subsequent calls."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)

        engine1 = connection.get_engine()
        engine2 = connection.get_engine()

        assert engine1 is engine2
        assert mock_create_engine.call_count == 1

    @patch("shared.database.connection.create_async_engine")
    @patch("shared.database.connection.sessionmaker")
    def test_get_session_factory(self, mock_sessionmaker, mock_create_engine):
        """Test session factory creation."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)

        factory = connection.get_session_factory()

        assert factory == mock_factory
        mock_sessionmaker.assert_called_once_with(
            mock_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    @patch("shared.database.connection.create_async_engine")
    @patch("shared.database.connection.sessionmaker")
    def test_get_session_factory_cached(self, mock_sessionmaker, mock_create_engine):
        """Test session factory caching."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)

        factory1 = connection.get_session_factory()
        factory2 = connection.get_session_factory()

        assert factory1 is factory2
        assert mock_sessionmaker.call_count == 1

    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Test successful session creation and commit."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)
        connection._session_factory = mock_factory

        async for session in connection.get_session():
            assert session == mock_session
            # Simulate successful work
            pass

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_close(self):
        """Test connection cleanup."""
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_factory = MagicMock()

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)
        connection._engine = mock_engine
        connection._session_factory = mock_factory

        await connection.close()

        mock_engine.dispose.assert_called_once()
        assert connection._engine is None
        assert connection._session_factory is None

    @pytest.mark.asyncio
    async def test_close_when_not_initialized(self):
        """Test close when connection not initialized."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/test")
        connection = DatabaseConnection(config)

        # Should not raise
        await connection.close()

        assert connection._engine is None
        assert connection._session_factory is None
