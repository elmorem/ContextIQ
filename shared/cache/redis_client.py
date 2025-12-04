"""
Redis client with connection pooling.
"""

from typing import Any

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from shared.config.logging import get_logger
from shared.exceptions import CacheConnectionError, CacheError

logger = get_logger(__name__)


class RedisClient:
    """Redis client with async connection pool."""

    def __init__(
        self,
        url: str,
        max_connections: int = 50,
        decode_responses: bool = True,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        """
        Initialize Redis client.

        Args:
            url: Redis connection URL
            max_connections: Maximum number of connections
            decode_responses: Decode responses to strings
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
        """
        self.url = url
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout

        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> None:
        """
        Connect to Redis server.

        Raises:
            CacheConnectionError: If connection fails
        """
        try:
            self._pool = ConnectionPool.from_url(
                self.url,
                max_connections=self.max_connections,
                decode_responses=self.decode_responses,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
            )

            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()

            logger.info("redis_connected", url=self.url)

        except Exception as e:
            logger.error("redis_connection_failed", error=str(e), url=self.url)
            raise CacheConnectionError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client:
            await self._client.aclose()
            self._client = None

        if self._pool:
            await self._pool.aclose()
            self._pool = None

        logger.info("redis_disconnected")

    def get_client(self) -> Redis:
        """
        Get Redis client.

        Returns:
            Redis client instance

        Raises:
            CacheError: If not connected
        """
        if not self._client:
            raise CacheError("Redis client not connected. Call connect() first.")
        return self._client

    async def ping(self) -> bool:
        """
        Ping Redis server.

        Returns:
            True if ping successful

        Raises:
            CacheError: If ping fails
        """
        try:
            client = self.get_client()
            result: bool = await client.ping()
            return result
        except Exception as e:
            logger.error("redis_ping_failed", error=str(e))
            raise CacheError(f"Redis ping failed: {e}") from e

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set a key-value pair.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful

        Raises:
            CacheError: If operation fails
        """
        try:
            client = self.get_client()
            if ttl:
                return await client.setex(key, ttl, value)  # type: ignore[no-any-return]
            else:
                return await client.set(key, value)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            raise CacheError(f"Redis set failed: {e}") from e

    async def get(self, key: str) -> Any | None:
        """
        Get a value by key.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found

        Raises:
            CacheError: If operation fails
        """
        try:
            client = self.get_client()
            return await client.get(key)
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            raise CacheError(f"Redis get failed: {e}") from e

    async def delete(self, key: str) -> int:
        """
        Delete a key.

        Args:
            key: Cache key

        Returns:
            Number of keys deleted

        Raises:
            CacheError: If operation fails
        """
        try:
            client = self.get_client()
            return await client.delete(key)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error("redis_delete_failed", key=key, error=str(e))
            raise CacheError(f"Redis delete failed: {e}") from e

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists

        Raises:
            CacheError: If operation fails
        """
        try:
            client = self.get_client()
            return bool(await client.exists(key))
        except Exception as e:
            logger.error("redis_exists_failed", key=key, error=str(e))
            raise CacheError(f"Redis exists failed: {e}") from e

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful

        Raises:
            CacheError: If operation fails
        """
        try:
            client = self.get_client()
            return await client.expire(key, ttl)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error("redis_expire_failed", key=key, ttl=ttl, error=str(e))
            raise CacheError(f"Redis expire failed: {e}") from e
