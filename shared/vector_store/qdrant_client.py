"""
Qdrant client wrapper for ContextIQ.

This module provides a high-level wrapper around the Qdrant client with
connection management, error handling, and batch operations.
"""

import time
from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from shared.vector_store.collections import CollectionConfig
from shared.vector_store.config import QdrantSettings, get_qdrant_settings


class QdrantClientWrapper:
    """
    Wrapper around Qdrant client with enhanced functionality.

    Provides connection management, retry logic, and simplified API
    for common vector operations.
    """

    def __init__(self, settings: QdrantSettings | None = None):
        """
        Initialize Qdrant client wrapper.

        Args:
            settings: Qdrant settings (uses defaults if not provided)
        """
        self.settings = settings or get_qdrant_settings()
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        """
        Get or create Qdrant client instance.

        Returns:
            QdrantClient instance

        Raises:
            ConnectionError: If unable to connect to Qdrant
        """
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> QdrantClient:
        """
        Create a new Qdrant client with configured settings.

        Returns:
            Configured QdrantClient instance

        Raises:
            ConnectionError: If unable to connect
        """
        try:
            return QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key,
                timeout=self.settings.qdrant_timeout,
                prefer_grpc=self.settings.qdrant_prefer_grpc,
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Qdrant at {self.settings.qdrant_url}: {e}"
            ) from e

    def close(self) -> None:
        """Close the Qdrant client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def health_check(self) -> bool:
        """
        Check if Qdrant server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Simple health check by listing collections
            self.client.get_collections()
            return True
        except Exception:
            return False

    def create_collection(self, config: CollectionConfig) -> bool:
        """
        Create a collection with the given configuration.

        Args:
            config: Collection configuration

        Returns:
            True if collection was created, False if it already exists

        Raises:
            Exception: If creation fails for reasons other than already exists
        """
        try:
            # Check if collection exists
            if self.collection_exists(config.name):
                return False

            # Create collection
            self.client.create_collection(
                collection_name=config.name,
                vectors_config=models.VectorParams(
                    size=config.vector_size,
                    distance=models.Distance[config.distance.value.upper()],
                    on_disk=config.on_disk,
                ),
                hnsw_config=(
                    models.HnswConfigDiff(**config.hnsw_config) if config.hnsw_config else None
                ),
                optimizers_config=(
                    models.OptimizersConfigDiff(**config.optimizers_config)
                    if config.optimizers_config
                    else None
                ),
            )
            return True

        except UnexpectedResponse as e:
            if "already exists" in str(e).lower():
                return False
            raise

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if deleted, False if collection didn't exist
        """
        try:
            if not self.collection_exists(collection_name):
                return False

            self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception:
            return False

    def upsert_points(
        self,
        collection_name: str,
        points: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> int:
        """
        Upsert points into a collection.

        Args:
            collection_name: Name of the collection
            points: List of point dictionaries with 'id', 'vector', and optional 'payload'
            batch_size: Batch size for bulk operations (uses default if not provided)

        Returns:
            Number of points upserted

        Raises:
            ValueError: If points are invalid
        """
        if not points:
            return 0

        batch_size = batch_size or self.settings.qdrant_batch_size

        # Convert points to Qdrant format
        qdrant_points = []
        for point in points:
            if "id" not in point or "vector" not in point:
                raise ValueError("Each point must have 'id' and 'vector' fields")

            qdrant_points.append(
                models.PointStruct(
                    id=str(point["id"]) if isinstance(point["id"], UUID) else point["id"],
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                )
            )

        # Upsert in batches
        total_upserted = 0
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i : i + batch_size]
            self.client.upsert(collection_name=collection_name, points=batch)
            total_upserted += len(batch)

        return total_upserted

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        query_filter: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            query_filter: Optional filter conditions

        Returns:
            List of search results with 'id', 'score', and 'payload'
        """
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=self._convert_filter(query_filter) if query_filter else None,
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload or {},
            }
            for result in results
        ]

    def get_point(self, collection_name: str, point_id: str | UUID) -> dict[str, Any] | None:
        """
        Retrieve a specific point by ID.

        Args:
            collection_name: Name of the collection
            point_id: ID of the point to retrieve

        Returns:
            Point data with 'id', 'vector', and 'payload', or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=collection_name,
                ids=[str(point_id) if isinstance(point_id, UUID) else point_id],
            )

            if not result:
                return None

            point = result[0]
            return {
                "id": point.id,
                "vector": point.vector,
                "payload": point.payload or {},
            }
        except Exception:
            return None

    def delete_points(
        self,
        collection_name: str,
        point_ids: list[str | UUID],
    ) -> int:
        """
        Delete points from a collection.

        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs to delete

        Returns:
            Number of points deleted
        """
        if not point_ids:
            return 0

        ids = [str(pid) if isinstance(pid, UUID) else pid for pid in point_ids]

        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=ids),
        )

        return len(ids)

    def count_points(self, collection_name: str, exact: bool = False) -> int:
        """
        Count points in a collection.

        Args:
            collection_name: Name of the collection
            exact: If True, perform exact count (slower but accurate)

        Returns:
            Number of points in the collection
        """
        result = self.client.count(collection_name=collection_name, exact=exact)
        return result.count

    def _convert_filter(self, filter_dict: dict) -> models.Filter:
        """
        Convert filter dictionary to Qdrant Filter model.

        Args:
            filter_dict: Dictionary with filter conditions

        Returns:
            Qdrant Filter model
        """
        # Simple filter conversion for common cases
        # Can be extended for more complex filter logic
        conditions = []

        for key, value in filter_dict.items():
            conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value),
                )
            )

        return models.Filter(must=conditions) if conditions else models.Filter()

    def _retry_operation(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Retry an operation with exponential backoff.

        Args:
            operation: Callable to retry
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result of the operation

        Raises:
            Exception: If all retries fail
        """
        last_exception: Exception | None = None
        delay = self.settings.qdrant_retry_delay

        for attempt in range(self.settings.qdrant_max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.settings.qdrant_max_retries:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Retry operation failed with no exception")

    def __enter__(self) -> "QdrantClientWrapper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
