"""
Database connection management.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class DatabaseConfig:
    """Database configuration."""

    def __init__(
        self,
        url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        echo: bool = False,
    ):
        """
        Initialize database configuration.

        Args:
            url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections beyond pool_size
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after this many seconds
            echo: Echo SQL statements for debugging
        """
        self.url = url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo


class DatabaseConnection:
    """Database connection manager."""

    def __init__(self, config: DatabaseConfig):
        """
        Initialize database connection.

        Args:
            config: Database configuration
        """
        self.config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: sessionmaker | None = None

    def get_engine(self) -> AsyncEngine:
        """
        Get or create async database engine.

        Returns:
            AsyncEngine instance
        """
        if self._engine is None:
            self._engine = create_async_engine(
                self.config.url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo,
                pool_pre_ping=True,  # Verify connections before using
            )
        return self._engine

    def get_session_factory(self) -> sessionmaker:
        """
        Get or create session factory.

        Returns:
            Session factory for creating database sessions
        """
        if self._session_factory is None:
            self._session_factory = sessionmaker(  # type: ignore[call-overload]
                self.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session as async context manager.

        Yields:
            AsyncSession instance
        """
        session_factory = self.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database connection and cleanup resources."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
