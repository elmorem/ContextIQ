"""
Integration tests for Qdrant connection.

Tests actual connectivity and operations with a running Qdrant instance.
Requires Qdrant to be running at localhost:6333 or the configured URL.
"""

import pytest

from shared.vector_store.collections import CollectionConfig, DistanceMetric
from shared.vector_store.config import QdrantSettings
from shared.vector_store.qdrant_client import QdrantClientWrapper

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def qdrant_settings():
    """Create Qdrant settings for testing."""
    return QdrantSettings(
        qdrant_url="http://localhost:6333",
        qdrant_timeout=10,
    )


@pytest.fixture
def qdrant_client(qdrant_settings):
    """Create Qdrant client for testing."""
    client = QdrantClientWrapper(settings=qdrant_settings)
    yield client
    client.close()


@pytest.fixture
def test_collection_config():
    """Create a test collection configuration."""
    return CollectionConfig(
        name="test_integration_collection",
        vector_size=128,
        distance=DistanceMetric.COSINE,
    )


class TestQdrantConnection:
    """Tests for Qdrant connection."""

    def test_health_check(self, qdrant_client):
        """Test that Qdrant server is healthy."""
        assert qdrant_client.health_check() is True

    def test_client_creation(self, qdrant_client):
        """Test that client is created successfully."""
        assert qdrant_client.client is not None


class TestCollectionManagement:
    """Tests for collection management."""

    def test_create_collection(self, qdrant_client, test_collection_config):
        """Test creating a collection."""
        # Clean up if exists
        qdrant_client.delete_collection(test_collection_config.name)

        # Create collection
        result = qdrant_client.create_collection(test_collection_config)
        assert result is True

        # Verify it exists
        assert qdrant_client.collection_exists(test_collection_config.name) is True

        # Clean up
        qdrant_client.delete_collection(test_collection_config.name)

    def test_create_collection_idempotent(self, qdrant_client, test_collection_config):
        """Test that creating an existing collection returns False."""
        # Clean up if exists
        qdrant_client.delete_collection(test_collection_config.name)

        # Create first time
        result1 = qdrant_client.create_collection(test_collection_config)
        assert result1 is True

        # Try to create again
        result2 = qdrant_client.create_collection(test_collection_config)
        assert result2 is False

        # Clean up
        qdrant_client.delete_collection(test_collection_config.name)

    def test_delete_collection(self, qdrant_client, test_collection_config):
        """Test deleting a collection."""
        # Create collection
        qdrant_client.delete_collection(test_collection_config.name)
        qdrant_client.create_collection(test_collection_config)

        # Delete it
        result = qdrant_client.delete_collection(test_collection_config.name)
        assert result is True

        # Verify it's gone
        assert qdrant_client.collection_exists(test_collection_config.name) is False

    def test_delete_nonexistent_collection(self, qdrant_client):
        """Test deleting a collection that doesn't exist."""
        result = qdrant_client.delete_collection("nonexistent_collection_xyz")
        assert result is False


class TestPointOperations:
    """Tests for point operations."""

    @pytest.fixture(autouse=True)
    def setup_collection(self, qdrant_client, test_collection_config):
        """Setup test collection before each test."""
        # Clean up and create fresh collection
        qdrant_client.delete_collection(test_collection_config.name)
        qdrant_client.create_collection(test_collection_config)
        yield
        # Cleanup after test
        qdrant_client.delete_collection(test_collection_config.name)

    def test_upsert_and_count(self, qdrant_client, test_collection_config):
        """Test upserting points and counting them."""
        points = [
            {"id": "1", "vector": [0.1] * 128, "payload": {"name": "point1"}},
            {"id": "2", "vector": [0.2] * 128, "payload": {"name": "point2"}},
            {"id": "3", "vector": [0.3] * 128, "payload": {"name": "point3"}},
        ]

        # Upsert points
        count = qdrant_client.upsert_points(test_collection_config.name, points)
        assert count == 3

        # Count points (use exact=True for integration tests)
        total = qdrant_client.count_points(test_collection_config.name, exact=True)
        assert total == 3

    def test_search(self, qdrant_client, test_collection_config):
        """Test searching for similar vectors."""
        # Insert test points
        points = [
            {"id": "1", "vector": [0.1] * 128, "payload": {"name": "similar1"}},
            {"id": "2", "vector": [0.15] * 128, "payload": {"name": "similar2"}},
            {"id": "3", "vector": [0.9] * 128, "payload": {"name": "different"}},
        ]
        qdrant_client.upsert_points(test_collection_config.name, points)

        # Search for similar to [0.1, 0.1, ...]
        results = qdrant_client.search(
            collection_name=test_collection_config.name,
            query_vector=[0.1] * 128,
            limit=2,
        )

        assert len(results) == 2
        # First result should be most similar
        assert results[0]["id"] == "1"
        assert results[0]["score"] > 0.9  # Cosine similarity

    def test_get_point(self, qdrant_client, test_collection_config):
        """Test retrieving a specific point."""
        # Insert a point
        point = {"id": "test_point", "vector": [0.5] * 128, "payload": {"key": "value"}}
        qdrant_client.upsert_points(test_collection_config.name, [point])

        # Retrieve it
        result = qdrant_client.get_point(test_collection_config.name, "test_point")

        assert result is not None
        assert result["id"] == "test_point"
        assert len(result["vector"]) == 128
        assert result["payload"]["key"] == "value"

    def test_get_nonexistent_point(self, qdrant_client, test_collection_config):
        """Test retrieving a point that doesn't exist."""
        result = qdrant_client.get_point(test_collection_config.name, "nonexistent")
        assert result is None

    def test_delete_points(self, qdrant_client, test_collection_config):
        """Test deleting points."""
        # Insert points
        points = [
            {"id": "1", "vector": [0.1] * 128},
            {"id": "2", "vector": [0.2] * 128},
            {"id": "3", "vector": [0.3] * 128},
        ]
        qdrant_client.upsert_points(test_collection_config.name, points)

        # Delete two points
        count = qdrant_client.delete_points(test_collection_config.name, ["1", "2"])
        assert count == 2

        # Verify they're deleted
        assert qdrant_client.get_point(test_collection_config.name, "1") is None
        assert qdrant_client.get_point(test_collection_config.name, "2") is None
        assert qdrant_client.get_point(test_collection_config.name, "3") is not None


class TestBatchOperations:
    """Tests for batch operations."""

    @pytest.fixture(autouse=True)
    def setup_collection(self, qdrant_client, test_collection_config):
        """Setup test collection before each test."""
        qdrant_client.delete_collection(test_collection_config.name)
        qdrant_client.create_collection(test_collection_config)
        yield
        qdrant_client.delete_collection(test_collection_config.name)

    def test_batch_upsert(self, qdrant_client, test_collection_config):
        """Test batch upserting with custom batch size."""
        # Create 150 points
        points = [{"id": str(i), "vector": [float(i)] * 128} for i in range(150)]

        # Upsert with batch size of 50
        count = qdrant_client.upsert_points(test_collection_config.name, points, batch_size=50)

        assert count == 150
        total = qdrant_client.count_points(test_collection_config.name, exact=True)
        assert total == 150
