"""
Unit tests for Qdrant client wrapper.

Tests client initialization, connection management, and basic operations with mocked Qdrant.
"""

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from shared.vector_store.collections import CollectionConfig, DistanceMetric
from shared.vector_store.config import QdrantSettings
from shared.vector_store.qdrant_client import QdrantClientWrapper


@pytest.fixture
def mock_settings():
    """Create mock Qdrant settings."""
    return QdrantSettings(
        qdrant_url="http://test:6333",
        qdrant_timeout=10,
        qdrant_max_retries=2,
        qdrant_retry_delay=0.1,
        qdrant_batch_size=50,
    )


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    return MagicMock()


@pytest.fixture
def qdrant_wrapper(mock_settings, mock_qdrant_client):
    """Create QdrantClientWrapper with mocked client."""
    wrapper = QdrantClientWrapper(settings=mock_settings)
    # Set the mock client directly instead of going through property
    wrapper._client = mock_qdrant_client
    return wrapper


class TestInitialization:
    """Tests for client initialization."""

    def test_init_with_settings(self, mock_settings):
        """Test initialization with custom settings."""
        wrapper = QdrantClientWrapper(settings=mock_settings)
        assert wrapper.settings == mock_settings
        assert wrapper._client is None

    def test_init_without_settings(self):
        """Test initialization with default settings."""
        with patch("shared.vector_store.qdrant_client.get_qdrant_settings") as mock_get_settings:
            mock_get_settings.return_value = QdrantSettings()
            wrapper = QdrantClientWrapper()
            assert wrapper.settings is not None
            mock_get_settings.assert_called_once()

    def test_client_property_creates_client(self, mock_settings):
        """Test that accessing client property creates the client."""
        with patch("shared.vector_store.qdrant_client.QdrantClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            wrapper = QdrantClientWrapper(settings=mock_settings)
            client = wrapper.client

            assert client == mock_client
            mock_client_class.assert_called_once_with(
                url=mock_settings.qdrant_url,
                api_key=mock_settings.qdrant_api_key,
                timeout=mock_settings.qdrant_timeout,
                prefer_grpc=mock_settings.qdrant_prefer_grpc,
            )

    def test_client_property_reuses_client(self, qdrant_wrapper):
        """Test that client property reuses existing client."""
        client1 = qdrant_wrapper.client
        client2 = qdrant_wrapper.client
        assert client1 is client2


class TestConnectionManagement:
    """Tests for connection management."""

    def test_close_client(self, qdrant_wrapper, mock_qdrant_client):
        """Test closing the client."""
        qdrant_wrapper.close()
        mock_qdrant_client.close.assert_called_once()
        assert qdrant_wrapper._client is None

    def test_health_check_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test health check when server is healthy."""
        mock_qdrant_client.get_collections.return_value = Mock()
        assert qdrant_wrapper.health_check() is True

    def test_health_check_failure(self, qdrant_wrapper, mock_qdrant_client):
        """Test health check when server is unhealthy."""
        mock_qdrant_client.get_collections.side_effect = Exception("Connection failed")
        assert qdrant_wrapper.health_check() is False

    def test_context_manager(self, mock_settings):
        """Test using wrapper as context manager."""
        with patch("shared.vector_store.qdrant_client.QdrantClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            with QdrantClientWrapper(settings=mock_settings) as wrapper:
                assert wrapper is not None
                # Access client property to trigger initialization
                _ = wrapper.client

            mock_client.close.assert_called_once()


class TestCollectionOperations:
    """Tests for collection operations."""

    def test_collection_exists_true(self, qdrant_wrapper, mock_qdrant_client):
        """Test checking if collection exists (exists)."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        # Create a mock collection with name attribute
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections

        assert qdrant_wrapper.collection_exists("test_collection") is True

    def test_collection_exists_false(self, qdrant_wrapper, mock_qdrant_client):
        """Test checking if collection exists (doesn't exist)."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        # Create a mock collection with different name
        mock_collection = Mock()
        mock_collection.name = "other_collection"

        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections

        assert qdrant_wrapper.collection_exists("test_collection") is False

    def test_collection_exists_error(self, qdrant_wrapper, mock_qdrant_client):
        """Test collection exists check when error occurs."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        mock_qdrant_client.get_collections.side_effect = Exception("Error")
        assert qdrant_wrapper.collection_exists("test_collection") is False

    def test_create_collection_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test creating a new collection."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        config = CollectionConfig(
            name="test_collection",
            vector_size=128,
            distance=DistanceMetric.COSINE,
        )

        # Mock collection doesn't exist
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections

        result = qdrant_wrapper.create_collection(config)

        assert result is True
        mock_qdrant_client.create_collection.assert_called_once()

    def test_create_collection_already_exists(self, qdrant_wrapper, mock_qdrant_client):
        """Test creating a collection that already exists."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        config = CollectionConfig(
            name="existing_collection",
            vector_size=128,
            distance=DistanceMetric.COSINE,
        )

        # Mock collection exists
        mock_collection = Mock()
        mock_collection.name = "existing_collection"

        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections

        result = qdrant_wrapper.create_collection(config)

        assert result is False
        mock_qdrant_client.create_collection.assert_not_called()

    def test_delete_collection_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test deleting an existing collection."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        # Mock collection exists
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections

        result = qdrant_wrapper.delete_collection("test_collection")

        assert result is True
        mock_qdrant_client.delete_collection.assert_called_once_with(
            collection_name="test_collection"
        )

    def test_delete_collection_not_exists(self, qdrant_wrapper, mock_qdrant_client):
        """Test deleting a collection that doesn't exist."""
        # Reset mock to clear any previous calls
        mock_qdrant_client.reset_mock()

        # Mock collection doesn't exist
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections

        result = qdrant_wrapper.delete_collection("nonexistent")

        assert result is False
        mock_qdrant_client.delete_collection.assert_not_called()


class TestPointOperations:
    """Tests for point operations."""

    def test_upsert_points_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test upserting points successfully."""
        points = [
            {"id": "1", "vector": [0.1, 0.2, 0.3], "payload": {"key": "value"}},
            {"id": "2", "vector": [0.4, 0.5, 0.6], "payload": {"key": "value2"}},
        ]

        count = qdrant_wrapper.upsert_points("test_collection", points)

        assert count == 2
        mock_qdrant_client.upsert.assert_called_once()

    def test_upsert_points_with_uuid(self, qdrant_wrapper, mock_qdrant_client):
        """Test upserting points with UUID ids."""
        point_id = uuid4()
        points = [
            {"id": point_id, "vector": [0.1, 0.2, 0.3]},
        ]

        qdrant_wrapper.upsert_points("test_collection", points)

        call_args = mock_qdrant_client.upsert.call_args
        assert str(point_id) in str(call_args)

    def test_upsert_points_empty(self, qdrant_wrapper, mock_qdrant_client):
        """Test upserting empty list."""
        count = qdrant_wrapper.upsert_points("test_collection", [])

        assert count == 0
        mock_qdrant_client.upsert.assert_not_called()

    def test_upsert_points_invalid(self, qdrant_wrapper):
        """Test upserting points with invalid data."""
        points = [{"vector": [0.1, 0.2, 0.3]}]  # Missing 'id'

        with pytest.raises(ValueError, match="must have 'id' and 'vector' fields"):
            qdrant_wrapper.upsert_points("test_collection", points)

    def test_search_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test searching for similar vectors."""
        mock_result = Mock()
        mock_result.id = "1"
        mock_result.score = 0.95
        mock_result.payload = {"key": "value"}

        mock_qdrant_client.search.return_value = [mock_result]

        results = qdrant_wrapper.search(
            collection_name="test_collection",
            query_vector=[0.1, 0.2, 0.3],
            limit=10,
        )

        assert len(results) == 1
        assert results[0]["id"] == "1"
        assert results[0]["score"] == 0.95
        assert results[0]["payload"] == {"key": "value"}

    def test_get_point_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test retrieving a point by ID."""
        mock_point = Mock()
        mock_point.id = "1"
        mock_point.vector = [0.1, 0.2, 0.3]
        mock_point.payload = {"key": "value"}

        mock_qdrant_client.retrieve.return_value = [mock_point]

        result = qdrant_wrapper.get_point("test_collection", "1")

        assert result is not None
        assert result["id"] == "1"
        assert result["vector"] == [0.1, 0.2, 0.3]
        assert result["payload"] == {"key": "value"}

    def test_get_point_not_found(self, qdrant_wrapper, mock_qdrant_client):
        """Test retrieving a point that doesn't exist."""
        mock_qdrant_client.retrieve.return_value = []

        result = qdrant_wrapper.get_point("test_collection", "nonexistent")

        assert result is None

    def test_delete_points_success(self, qdrant_wrapper, mock_qdrant_client):
        """Test deleting points."""
        point_ids = ["1", "2", "3"]

        count = qdrant_wrapper.delete_points("test_collection", point_ids)

        assert count == 3
        mock_qdrant_client.delete.assert_called_once()

    def test_delete_points_empty(self, qdrant_wrapper, mock_qdrant_client):
        """Test deleting with empty list."""
        count = qdrant_wrapper.delete_points("test_collection", [])

        assert count == 0
        mock_qdrant_client.delete.assert_not_called()

    def test_count_points(self, qdrant_wrapper, mock_qdrant_client):
        """Test counting points in a collection."""
        mock_result = Mock()
        mock_result.count = 42

        mock_qdrant_client.count.return_value = mock_result

        count = qdrant_wrapper.count_points("test_collection")

        assert count == 42
        mock_qdrant_client.count.assert_called_once_with(
            collection_name="test_collection", exact=False
        )
