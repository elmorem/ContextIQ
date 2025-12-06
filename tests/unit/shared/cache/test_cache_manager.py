"""
Unit tests for cache manager.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from shared.cache.cache_manager import CacheManager
from shared.cache.redis_client import RedisClient
from shared.exceptions import CacheError


class SampleModel(BaseModel):
    """Test Pydantic model."""

    id: str
    name: str
    count: int


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = MagicMock(spec=RedisClient)
    client.get = AsyncMock()
    client.set = AsyncMock()
    client.delete = AsyncMock()
    client.get_client = MagicMock()
    return client


@pytest.fixture
def cache_manager(mock_redis_client):
    """Create cache manager."""
    return CacheManager(redis_client=mock_redis_client)


class TestCacheManagerInitialization:
    """Tests for cache manager initialization."""

    def test_initialization(self, cache_manager, mock_redis_client):
        """Test cache manager initialization."""
        assert cache_manager.redis == mock_redis_client


class TestGetJson:
    """Tests for getting JSON values."""

    @pytest.mark.asyncio
    async def test_get_json_dict_success(self, cache_manager, mock_redis_client):
        """Test getting dict from cache."""
        test_data = {"id": "123", "name": "test", "count": 42}
        mock_redis_client.get.return_value = json.dumps(test_data)

        result = await cache_manager.get_json("test_key")

        assert result == test_data
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_json_with_model(self, cache_manager, mock_redis_client):
        """Test getting and deserializing to Pydantic model."""
        test_data = {"id": "123", "name": "test", "count": 42}
        mock_redis_client.get.return_value = json.dumps(test_data)

        result = await cache_manager.get_json("test_key", model=SampleModel)

        assert isinstance(result, SampleModel)
        assert result.id == "123"
        assert result.name == "test"
        assert result.count == 42

    @pytest.mark.asyncio
    async def test_get_json_not_found(self, cache_manager, mock_redis_client):
        """Test getting non-existent key."""
        mock_redis_client.get.return_value = None

        result = await cache_manager.get_json("missing_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_invalid_json(self, cache_manager, mock_redis_client):
        """Test getting invalid JSON."""
        mock_redis_client.get.return_value = "not valid json"

        with pytest.raises(CacheError) as exc_info:
            await cache_manager.get_json("test_key")

        assert "Failed to decode JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_json_redis_error(self, cache_manager, mock_redis_client):
        """Test Redis error during get."""
        mock_redis_client.get.side_effect = Exception("Redis error")

        with pytest.raises(CacheError) as exc_info:
            await cache_manager.get_json("test_key")

        assert "Cache get JSON failed" in str(exc_info.value)


class TestSetJson:
    """Tests for setting JSON values."""

    @pytest.mark.asyncio
    async def test_set_json_dict(self, cache_manager, mock_redis_client):
        """Test setting dict to cache."""
        test_data = {"id": "123", "name": "test"}
        mock_redis_client.set.return_value = True

        result = await cache_manager.set_json("test_key", test_data)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ttl=None,
        )

    @pytest.mark.asyncio
    async def test_set_json_dict_with_ttl(self, cache_manager, mock_redis_client):
        """Test setting dict with TTL."""
        test_data = {"id": "123", "name": "test"}
        mock_redis_client.set.return_value = True

        result = await cache_manager.set_json("test_key", test_data, ttl=60)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ttl=60,
        )

    @pytest.mark.asyncio
    async def test_set_json_pydantic_model(self, cache_manager, mock_redis_client):
        """Test setting Pydantic model to cache."""
        test_model = SampleModel(id="123", name="test", count=42)
        mock_redis_client.set.return_value = True

        result = await cache_manager.set_json("test_key", test_model)

        assert result is True
        # Verify JSON was set (model_dump_json() is used for Pydantic models)
        call_args = mock_redis_client.set.call_args
        assert call_args[0][0] == "test_key"
        cached_data = json.loads(call_args[0][1])
        assert cached_data == {"id": "123", "name": "test", "count": 42}

    @pytest.mark.asyncio
    async def test_set_json_list(self, cache_manager, mock_redis_client):
        """Test setting list to cache."""
        test_data = [1, 2, 3, 4, 5]
        mock_redis_client.set.return_value = True

        result = await cache_manager.set_json("test_key", test_data)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ttl=None,
        )

    @pytest.mark.asyncio
    async def test_set_json_error(self, cache_manager, mock_redis_client):
        """Test Redis error during set."""
        mock_redis_client.set.side_effect = Exception("Redis error")

        with pytest.raises(CacheError) as exc_info:
            await cache_manager.set_json("test_key", {"data": "value"})

        assert "Cache set JSON failed" in str(exc_info.value)


class TestGetOrSet:
    """Tests for get_or_set pattern."""

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, cache_manager, mock_redis_client):
        """Test get_or_set with cache hit."""
        cached_data = {"id": "123", "name": "cached"}
        mock_redis_client.get.return_value = json.dumps(cached_data)

        factory = AsyncMock(return_value={"id": "456", "name": "fresh"})

        result = await cache_manager.get_or_set("test_key", factory)

        assert result == cached_data
        factory.assert_not_called()  # Factory shouldn't be called on cache hit

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss(self, cache_manager, mock_redis_client):
        """Test get_or_set with cache miss."""
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True

        fresh_data = {"id": "456", "name": "fresh"}
        factory = AsyncMock(return_value=fresh_data)

        result = await cache_manager.get_or_set("test_key", factory)

        assert result == fresh_data
        factory.assert_called_once()
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_set_with_ttl(self, cache_manager, mock_redis_client):
        """Test get_or_set with TTL."""
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True

        fresh_data = {"id": "456", "name": "fresh"}
        factory = AsyncMock(return_value=fresh_data)

        result = await cache_manager.get_or_set("test_key", factory, ttl=300)

        assert result == fresh_data
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ttl"] == 300

    @pytest.mark.asyncio
    async def test_get_or_set_with_model(self, cache_manager, mock_redis_client):
        """Test get_or_set with Pydantic model."""
        cached_data = {"id": "123", "name": "cached", "count": 42}
        mock_redis_client.get.return_value = json.dumps(cached_data)

        factory = AsyncMock()

        result = await cache_manager.get_or_set("test_key", factory, model=SampleModel)

        assert isinstance(result, SampleModel)
        assert result.id == "123"
        factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_set_error(self, cache_manager, mock_redis_client):
        """Test get_or_set with error."""
        mock_redis_client.get.side_effect = Exception("Redis error")

        factory = AsyncMock()

        with pytest.raises(CacheError) as exc_info:
            await cache_manager.get_or_set("test_key", factory)

        assert "Cache get_or_set failed" in str(exc_info.value)


class TestInvalidate:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_success(self, cache_manager, mock_redis_client):
        """Test invalidating a key."""
        mock_redis_client.delete.return_value = 1

        result = await cache_manager.invalidate("test_key")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_invalidate_not_found(self, cache_manager, mock_redis_client):
        """Test invalidating non-existent key."""
        mock_redis_client.delete.return_value = 0

        result = await cache_manager.invalidate("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_error(self, cache_manager, mock_redis_client):
        """Test invalidation error."""
        mock_redis_client.delete.side_effect = Exception("Redis error")

        with pytest.raises(CacheError) as exc_info:
            await cache_manager.invalidate("test_key")

        assert "Cache invalidate failed" in str(exc_info.value)


class TestInvalidatePattern:
    """Tests for pattern-based invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_pattern_success(self, cache_manager, mock_redis_client):
        """Test invalidating keys by pattern."""
        mock_client = AsyncMock()
        mock_redis_client.get_client.return_value = mock_client

        # Mock scan_iter to return keys
        async def mock_scan():
            for key in ["session:123", "session:456", "session:789"]:
                yield key

        mock_client.scan_iter = MagicMock(return_value=mock_scan())
        mock_client.delete = AsyncMock(return_value=3)

        result = await cache_manager.invalidate_pattern("session:*")

        assert result == 3
        mock_client.scan_iter.assert_called_once_with(match="session:*")
        mock_client.delete.assert_called_once_with("session:123", "session:456", "session:789")

    @pytest.mark.asyncio
    async def test_invalidate_pattern_no_matches(self, cache_manager, mock_redis_client):
        """Test invalidating pattern with no matches."""
        mock_client = AsyncMock()
        mock_redis_client.get_client.return_value = mock_client

        # Mock scan_iter to return no keys
        async def mock_scan():
            return
            yield  # Make it an async generator

        mock_client.scan_iter = MagicMock(return_value=mock_scan())

        result = await cache_manager.invalidate_pattern("nonexistent:*")

        assert result == 0

    @pytest.mark.asyncio
    async def test_invalidate_pattern_error(self, cache_manager, mock_redis_client):
        """Test pattern invalidation error."""
        mock_redis_client.get_client.side_effect = Exception("Redis error")

        with pytest.raises(CacheError) as exc_info:
            await cache_manager.invalidate_pattern("test:*")

        assert "Cache invalidate pattern failed" in str(exc_info.value)
