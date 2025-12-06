"""
Unit tests for Redis client.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from shared.cache.redis_client import RedisClient
from shared.exceptions import CacheConnectionError, CacheError


@pytest.fixture
def redis_url():
    """Test Redis URL."""
    return "redis://localhost:6379/0"


@pytest.fixture
def redis_client(redis_url):
    """Create Redis client."""
    return RedisClient(url=redis_url)


class TestRedisClientInitialization:
    """Tests for Redis client initialization."""

    def test_initialization(self, redis_client, redis_url):
        """Test client initialization with default settings."""
        assert redis_client.url == redis_url
        assert redis_client.max_connections == 50
        assert redis_client.decode_responses is True
        assert redis_client.socket_timeout == 5.0
        assert redis_client.socket_connect_timeout == 5.0
        assert redis_client._pool is None
        assert redis_client._client is None

    def test_initialization_custom_settings(self):
        """Test client initialization with custom settings."""
        client = RedisClient(
            url="redis://custom:6379/1",
            max_connections=100,
            decode_responses=False,
            socket_timeout=10.0,
            socket_connect_timeout=15.0,
        )

        assert client.url == "redis://custom:6379/1"
        assert client.max_connections == 100
        assert client.decode_responses is False
        assert client.socket_timeout == 10.0
        assert client.socket_connect_timeout == 15.0


class TestRedisClientConnection:
    """Tests for Redis client connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(self, redis_client):
        """Test successful connection to Redis."""
        mock_pool = MagicMock(spec=ConnectionPool)
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(return_value=True)

        with (
            patch("shared.cache.redis_client.ConnectionPool.from_url", return_value=mock_pool),
            patch("shared.cache.redis_client.Redis", return_value=mock_client),
        ):
            await redis_client.connect()

            assert redis_client._pool == mock_pool
            assert redis_client._client == mock_client
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, redis_client):
        """Test connection failure."""
        with patch(
            "shared.cache.redis_client.ConnectionPool.from_url",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(CacheConnectionError) as exc_info:
                await redis_client.connect()

            assert "Failed to connect to Redis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect(self, redis_client):
        """Test disconnection from Redis."""
        # Mock connection
        mock_client = AsyncMock(spec=Redis)
        mock_pool = MagicMock(spec=ConnectionPool)
        mock_pool.aclose = AsyncMock()
        redis_client._client = mock_client
        redis_client._pool = mock_pool

        await redis_client.disconnect()

        mock_client.aclose.assert_called_once()
        mock_pool.aclose.assert_called_once()
        assert redis_client._client is None
        assert redis_client._pool is None

    def test_get_client_not_connected(self, redis_client):
        """Test getting client when not connected."""
        with pytest.raises(CacheError) as exc_info:
            redis_client.get_client()

        assert "not connected" in str(exc_info.value)

    def test_get_client_connected(self, redis_client):
        """Test getting client when connected."""
        mock_client = MagicMock(spec=Redis)
        redis_client._client = mock_client

        client = redis_client.get_client()
        assert client == mock_client


class TestRedisClientOperations:
    """Tests for Redis client operations."""

    @pytest.fixture
    def connected_client(self, redis_client):
        """Create connected Redis client."""
        mock_client = AsyncMock(spec=Redis)
        redis_client._client = mock_client
        return redis_client

    @pytest.mark.asyncio
    async def test_ping_success(self, connected_client):
        """Test successful ping."""
        connected_client._client.ping = AsyncMock(return_value=True)

        result = await connected_client.ping()
        assert result is True
        connected_client._client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_failure(self, connected_client):
        """Test ping failure."""
        connected_client._client.ping = AsyncMock(side_effect=Exception("Ping failed"))

        with pytest.raises(CacheError) as exc_info:
            await connected_client.ping()

        assert "Redis ping failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, connected_client):
        """Test setting value without TTL."""
        connected_client._client.set = AsyncMock(return_value=True)

        result = await connected_client.set("test_key", "test_value")

        assert result is True
        connected_client._client.set.assert_called_once_with("test_key", "test_value")

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, connected_client):
        """Test setting value with TTL."""
        connected_client._client.setex = AsyncMock(return_value=True)

        result = await connected_client.set("test_key", "test_value", ttl=60)

        assert result is True
        connected_client._client.setex.assert_called_once_with("test_key", 60, "test_value")

    @pytest.mark.asyncio
    async def test_set_failure(self, connected_client):
        """Test set operation failure."""
        connected_client._client.set = AsyncMock(side_effect=Exception("Set failed"))

        with pytest.raises(CacheError) as exc_info:
            await connected_client.set("test_key", "test_value")

        assert "Redis set failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_success(self, connected_client):
        """Test getting value."""
        connected_client._client.get = AsyncMock(return_value="test_value")

        result = await connected_client.get("test_key")

        assert result == "test_value"
        connected_client._client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_not_found(self, connected_client):
        """Test getting non-existent key."""
        connected_client._client.get = AsyncMock(return_value=None)

        result = await connected_client.get("missing_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_failure(self, connected_client):
        """Test get operation failure."""
        connected_client._client.get = AsyncMock(side_effect=Exception("Get failed"))

        with pytest.raises(CacheError) as exc_info:
            await connected_client.get("test_key")

        assert "Redis get failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_success(self, connected_client):
        """Test deleting key."""
        connected_client._client.delete = AsyncMock(return_value=1)

        result = await connected_client.delete("test_key")

        assert result == 1
        connected_client._client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_not_found(self, connected_client):
        """Test deleting non-existent key."""
        connected_client._client.delete = AsyncMock(return_value=0)

        result = await connected_client.delete("missing_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_failure(self, connected_client):
        """Test delete operation failure."""
        connected_client._client.delete = AsyncMock(side_effect=Exception("Delete failed"))

        with pytest.raises(CacheError) as exc_info:
            await connected_client.delete("test_key")

        assert "Redis delete failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exists_true(self, connected_client):
        """Test checking if key exists (exists)."""
        connected_client._client.exists = AsyncMock(return_value=1)

        result = await connected_client.exists("test_key")

        assert result is True
        connected_client._client.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_false(self, connected_client):
        """Test checking if key exists (doesn't exist)."""
        connected_client._client.exists = AsyncMock(return_value=0)

        result = await connected_client.exists("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_failure(self, connected_client):
        """Test exists operation failure."""
        connected_client._client.exists = AsyncMock(side_effect=Exception("Exists failed"))

        with pytest.raises(CacheError) as exc_info:
            await connected_client.exists("test_key")

        assert "Redis exists failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_expire_success(self, connected_client):
        """Test setting expiration on key."""
        connected_client._client.expire = AsyncMock(return_value=True)

        result = await connected_client.expire("test_key", 60)

        assert result is True
        connected_client._client.expire.assert_called_once_with("test_key", 60)

    @pytest.mark.asyncio
    async def test_expire_failure(self, connected_client):
        """Test expire operation failure."""
        connected_client._client.expire = AsyncMock(side_effect=Exception("Expire failed"))

        with pytest.raises(CacheError) as exc_info:
            await connected_client.expire("test_key", 60)

        assert "Redis expire failed" in str(exc_info.value)
