"""
High-level cache manager with JSON serialization.
"""

import json
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from shared.cache.redis_client import RedisClient
from shared.config.logging import get_logger
from shared.exceptions import CacheError

logger = get_logger(__name__)

T = TypeVar("T")


class CacheManager:
    """High-level cache manager with JSON serialization."""

    def __init__(self, redis_client: RedisClient):
        """
        Initialize cache manager.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    async def get_json(self, key: str, model: type[T] | None = None) -> T | dict | None:
        """
        Get and deserialize JSON value.

        Args:
            key: Cache key
            model: Optional Pydantic model to deserialize into

        Returns:
            Deserialized value or None if not found

        Raises:
            CacheError: If operation fails
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            data = json.loads(value)

            if model and issubclass(model, BaseModel):
                return model.model_validate(data)

            return data

        except json.JSONDecodeError as e:
            logger.error("cache_json_decode_failed", key=key, error=str(e))
            raise CacheError(f"Failed to decode JSON from cache: {e}") from e
        except Exception as e:
            logger.error("cache_get_json_failed", key=key, error=str(e))
            raise CacheError(f"Cache get JSON failed: {e}") from e

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Serialize and cache JSON value.

        Args:
            key: Cache key
            value: Value to cache (dict, list, or Pydantic model)
            ttl: Time to live in seconds

        Returns:
            True if successful

        Raises:
            CacheError: If operation fails
        """
        try:
            # Handle Pydantic models
            if isinstance(value, BaseModel):
                json_str = value.model_dump_json()
            else:
                json_str = json.dumps(value)

            return await self.redis.set(key, json_str, ttl=ttl)

        except Exception as e:
            logger.error("cache_set_json_failed", key=key, error=str(e))
            raise CacheError(f"Cache set JSON failed: {e}") from e

    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: int | None = None,
        model: type[T] | None = None,
    ) -> T | dict:
        """
        Get from cache or compute and cache if not found.

        Args:
            key: Cache key
            factory: Async callable to compute value if not cached
            ttl: Time to live in seconds
            model: Optional Pydantic model to deserialize into

        Returns:
            Cached or computed value

        Raises:
            CacheError: If operation fails
        """
        try:
            # Try to get from cache
            cached = await self.get_json(key, model=model)
            if cached is not None:
                logger.debug("cache_hit", key=key)
                return cached

            # Not in cache, compute value
            logger.debug("cache_miss", key=key)
            value = await factory()

            # Cache the computed value
            await self.set_json(key, value, ttl=ttl)

            return value

        except Exception as e:
            logger.error("cache_get_or_set_failed", key=key, error=str(e))
            raise CacheError(f"Cache get_or_set failed: {e}") from e

    async def invalidate(self, key: str) -> bool:
        """
        Invalidate (delete) a cache entry.

        Args:
            key: Cache key

        Returns:
            True if key was deleted

        Raises:
            CacheError: If operation fails
        """
        try:
            deleted = await self.redis.delete(key)
            if deleted:
                logger.debug("cache_invalidated", key=key)
            return bool(deleted)
        except Exception as e:
            logger.error("cache_invalidate_failed", key=key, error=str(e))
            raise CacheError(f"Cache invalidate failed: {e}") from e

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "session:*")

        Returns:
            Number of keys deleted

        Raises:
            CacheError: If operation fails
        """
        try:
            client = self.redis.get_client()

            # Scan for matching keys
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            # Delete all matching keys
            if keys:
                deleted = await client.delete(*keys)
                logger.debug("cache_pattern_invalidated", pattern=pattern, count=deleted)
                return deleted

            return 0

        except Exception as e:
            logger.error("cache_invalidate_pattern_failed", pattern=pattern, error=str(e))
            raise CacheError(f"Cache invalidate pattern failed: {e}") from e
