"""
Tests for cache manager.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from shared.cache.cache_manager import CacheManager
from shared.exceptions import CacheError


class TestModel(BaseModel):
    """Test Pydantic model."""

    name: str
    value: int


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.get_client = MagicMock()
    return redis


@pytest.fixture
def cache_manager(mock_redis):
    """Create cache manager with mock Redis."""
    return CacheManager(mock_redis)


class TestGetJson:
    """Tests for get_json."""

    @pytest.mark.asyncio
    async def test_get_existing_value(self, cache_manager, mock_redis):
        """Test getting existing JSON value."""
        data = {"name": "test", "value": 123}
        mock_redis.get.return_value = json.dumps(data)

        result = await cache_manager.get_json("test_key")

        assert result == data
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_non_existent_value(self, cache_manager, mock_redis):
        """Test getting non-existent value returns None."""
        mock_redis.get.return_value = None

        result = await cache_manager.get_json("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_pydantic_model(self, cache_manager, mock_redis):
        """Test getting value with Pydantic model."""
        data = {"name": "test", "value": 123}
        mock_redis.get.return_value = json.dumps(data)

        result = await cache_manager.get_json("test_key", model=TestModel)

        assert isinstance(result, TestModel)
        assert result.name == "test"
        assert result.value == 123

    @pytest.mark.asyncio
    async def test_get_invalid_json_raises_error(self, cache_manager, mock_redis):
        """Test that invalid JSON raises CacheError."""
        mock_redis.get.return_value = "invalid json"

        with pytest.raises(CacheError, match="Failed to decode JSON"):
            await cache_manager.get_json("test_key")

    @pytest.mark.asyncio
    async def test_get_redis_error_raises_cache_error(self, cache_manager, mock_redis):
        """Test that Redis error raises CacheError."""
        mock_redis.get.side_effect = Exception("Redis error")

        with pytest.raises(CacheError, match="Cache get JSON failed"):
            await cache_manager.get_json("test_key")


class TestSetJson:
    """Tests for set_json."""

    @pytest.mark.asyncio
    async def test_set_dict_value(self, cache_manager, mock_redis):
        """Test setting dict value."""
        data = {"name": "test", "value": 123}
        mock_redis.set.return_value = True

        result = await cache_manager.set_json("test_key", data)

        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test_key"
        assert json.loads(call_args[0][1]) == data

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_manager, mock_redis):
        """Test setting value with TTL."""
        data = {"name": "test"}
        mock_redis.set.return_value = True

        await cache_manager.set_json("test_key", data, ttl=3600)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[1]["ttl"] == 3600

    @pytest.mark.asyncio
    async def test_set_pydantic_model(self, cache_manager, mock_redis):
        """Test setting Pydantic model."""
        model = TestModel(name="test", value=123)
        mock_redis.set.return_value = True

        result = await cache_manager.set_json("test_key", model)

        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        stored_data = json.loads(call_args[0][1])
        assert stored_data["name"] == "test"
        assert stored_data["value"] == 123

    @pytest.mark.asyncio
    async def test_set_redis_error_raises_cache_error(self, cache_manager, mock_redis):
        """Test that Redis error raises CacheError."""
        mock_redis.set.side_effect = Exception("Redis error")

        with pytest.raises(CacheError, match="Cache set JSON failed"):
            await cache_manager.set_json("test_key", {"data": "value"})


class TestGetOrSet:
    """Tests for get_or_set."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache_manager, mock_redis):
        """Test cache hit returns cached value."""
        data = {"name": "test", "value": 123}
        mock_redis.get.return_value = json.dumps(data)

        factory = AsyncMock()
        result = await cache_manager.get_or_set("test_key", factory)

        assert result == data
        factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_manager, mock_redis):
        """Test cache miss calls factory and caches result."""
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        data = {"name": "test", "value": 123}
        factory = AsyncMock(return_value=data)

        result = await cache_manager.get_or_set("test_key", factory, ttl=3600)

        assert result == data
        factory.assert_called_once()
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_with_model(self, cache_manager, mock_redis):
        """Test cache miss with Pydantic model."""
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        model = TestModel(name="test", value=123)
        factory = AsyncMock(return_value=model)

        result = await cache_manager.get_or_set("test_key", factory, model=TestModel)

        assert isinstance(result, TestModel)
        factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_factory_error_raises_cache_error(self, cache_manager, mock_redis):
        """Test that factory error raises CacheError."""
        mock_redis.get.return_value = None

        factory = AsyncMock(side_effect=Exception("Factory error"))

        with pytest.raises(CacheError, match="Cache get_or_set failed"):
            await cache_manager.get_or_set("test_key", factory)


class TestInvalidate:
    """Tests for invalidate."""

    @pytest.mark.asyncio
    async def test_invalidate_existing_key(self, cache_manager, mock_redis):
        """Test invalidating existing key."""
        mock_redis.delete.return_value = 1

        result = await cache_manager.invalidate("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_invalidate_non_existent_key(self, cache_manager, mock_redis):
        """Test invalidating non-existent key."""
        mock_redis.delete.return_value = 0

        result = await cache_manager.invalidate("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_redis_error_raises_cache_error(self, cache_manager, mock_redis):
        """Test that Redis error raises CacheError."""
        mock_redis.delete.side_effect = Exception("Redis error")

        with pytest.raises(CacheError, match="Cache invalidate failed"):
            await cache_manager.invalidate("test_key")


class TestInvalidatePattern:
    """Tests for invalidate_pattern."""

    @pytest.mark.asyncio
    async def test_invalidate_matching_keys(self, cache_manager, mock_redis):
        """Test invalidating keys matching pattern."""
        mock_client = AsyncMock()
        mock_client.scan_iter = MagicMock(return_value=AsyncIteratorMock(["key1", "key2", "key3"]))
        mock_client.delete = AsyncMock(return_value=3)
        mock_redis.get_client.return_value = mock_client

        result = await cache_manager.invalidate_pattern("session:*")

        assert result == 3
        mock_client.delete.assert_called_once_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_invalidate_no_matching_keys(self, cache_manager, mock_redis):
        """Test invalidating with no matching keys."""
        mock_client = AsyncMock()
        mock_client.scan_iter = MagicMock(return_value=AsyncIteratorMock([]))
        mock_redis.get_client.return_value = mock_client

        result = await cache_manager.invalidate_pattern("session:*")

        assert result == 0

    @pytest.mark.asyncio
    async def test_invalidate_pattern_redis_error_raises_cache_error(
        self, cache_manager, mock_redis
    ):
        """Test that Redis error raises CacheError."""
        mock_client = AsyncMock()
        mock_client.scan_iter = MagicMock(side_effect=Exception("Redis error"))
        mock_redis.get_client.return_value = mock_client

        with pytest.raises(CacheError, match="Cache invalidate pattern failed"):
            await cache_manager.invalidate_pattern("session:*")


class AsyncIteratorMock:
    """Mock async iterator for scan_iter."""

    def __init__(self, items):
        """Initialize with items to iterate."""
        self.items = items
        self.index = 0

    def __aiter__(self):
        """Return self as async iterator."""
        return self

    async def __anext__(self):
        """Get next item."""
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item
