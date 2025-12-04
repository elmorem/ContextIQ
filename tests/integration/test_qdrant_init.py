"""
Integration tests for Qdrant initialization script.

These tests require a running Qdrant instance.
"""

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from scripts.init_qdrant import (
    collection_exists,
    create_collection,
    create_qdrant_client,
    init_collections,
)
from shared.vector_store import get_memory_collection_config

# Skip all tests if Qdrant is not available
pytestmark = pytest.mark.integration


@pytest.fixture
def qdrant_client():
    """Provide Qdrant client for tests."""
    try:
        client = QdrantClient(host="localhost", port=6333)
        client.get_collections()
        yield client
    except Exception:
        pytest.skip("Qdrant not available")


@pytest.fixture
def clean_test_collection(qdrant_client):
    """Clean up test collection before and after test."""
    collection_name = "test_collection"

    # Clean up before test
    try:
        qdrant_client.delete_collection(collection_name)
    except UnexpectedResponse:
        pass

    yield collection_name

    # Clean up after test
    try:
        qdrant_client.delete_collection(collection_name)
    except UnexpectedResponse:
        pass


class TestCreateQdrantClient:
    """Tests for create_qdrant_client."""

    def test_connects_successfully(self):
        """Test successful connection to Qdrant."""
        client = create_qdrant_client("localhost", 6333)
        assert client is not None
        # Verify connection works
        client.get_collections()

    def test_fails_on_bad_host(self):
        """Test connection failure with bad host."""
        with pytest.raises(ConnectionError, match="Failed to connect"):
            create_qdrant_client("invalid-host", 6333)

    def test_fails_on_bad_port(self):
        """Test connection failure with bad port."""
        with pytest.raises(ConnectionError, match="Failed to connect"):
            create_qdrant_client("localhost", 9999)


class TestCollectionExists:
    """Tests for collection_exists."""

    def test_returns_false_for_nonexistent(self, qdrant_client):
        """Test returns False for non-existent collection."""
        result = collection_exists(qdrant_client, "nonexistent_collection_xyz")
        assert result is False

    def test_returns_true_for_existing(self, qdrant_client, clean_test_collection):
        """Test returns True for existing collection."""
        # Create collection
        config = get_memory_collection_config()
        qdrant_config = config.to_dict()
        create_collection(
            qdrant_client,
            clean_test_collection,
            qdrant_config,
        )

        # Check it exists
        result = collection_exists(qdrant_client, clean_test_collection)
        assert result is True


class TestCreateCollection:
    """Tests for create_collection."""

    def test_creates_new_collection(self, qdrant_client, clean_test_collection):
        """Test creating a new collection."""
        config = get_memory_collection_config()
        qdrant_config = config.to_dict()

        result = create_collection(
            qdrant_client,
            clean_test_collection,
            qdrant_config,
        )

        assert result is True
        assert collection_exists(qdrant_client, clean_test_collection)

    def test_skips_existing_collection(self, qdrant_client, clean_test_collection):
        """Test skips creating existing collection."""
        config = get_memory_collection_config()
        qdrant_config = config.to_dict()

        # Create collection first time
        create_collection(qdrant_client, clean_test_collection, qdrant_config)

        # Try creating again without recreate
        result = create_collection(
            qdrant_client,
            clean_test_collection,
            qdrant_config,
            recreate=False,
        )

        assert result is False

    def test_recreates_existing_collection(self, qdrant_client, clean_test_collection):
        """Test recreating an existing collection."""
        config = get_memory_collection_config()
        qdrant_config = config.to_dict()

        # Create collection first time
        create_collection(qdrant_client, clean_test_collection, qdrant_config)

        # Recreate
        result = create_collection(
            qdrant_client,
            clean_test_collection,
            qdrant_config,
            recreate=True,
        )

        assert result is True
        assert collection_exists(qdrant_client, clean_test_collection)

    def test_creates_collection_with_correct_config(self, qdrant_client, clean_test_collection):
        """Test collection created with correct configuration."""
        config = get_memory_collection_config()
        qdrant_config = config.to_dict()

        create_collection(qdrant_client, clean_test_collection, qdrant_config)

        # Get collection info
        collection_info = qdrant_client.get_collection(clean_test_collection)

        # Verify vector config
        assert collection_info.config.params.vectors.size == config.vector_size
        assert collection_info.config.params.vectors.distance.name == config.distance.name


class TestInitCollections:
    """Tests for init_collections."""

    @pytest.fixture(autouse=True)
    def cleanup_memories_collection(self, qdrant_client):
        """Clean up memories collection after test."""
        yield
        try:
            qdrant_client.delete_collection("memories")
        except UnexpectedResponse:
            pass

    def test_initializes_all_collections(self, qdrant_client):
        """Test initializes all configured collections."""
        created, skipped = init_collections("localhost", 6333, recreate=True)

        assert created > 0
        assert collection_exists(qdrant_client, "memories")

    def test_skips_existing_collections(self, qdrant_client):
        """Test skips existing collections when recreate=False."""
        # Initialize first time
        init_collections("localhost", 6333, recreate=True)

        # Initialize again without recreate
        created, skipped = init_collections("localhost", 6333, recreate=False)

        assert created == 0
        assert skipped > 0

    def test_recreates_all_collections(self, qdrant_client):
        """Test recreates all collections when recreate=True."""
        # Initialize first time
        init_collections("localhost", 6333, recreate=True)

        # Initialize again with recreate
        created, skipped = init_collections("localhost", 6333, recreate=True)

        assert created > 0
        assert skipped == 0

    def test_raises_on_connection_failure(self):
        """Test raises ConnectionError on connection failure."""
        with pytest.raises(ConnectionError):
            init_collections("invalid-host", 6333)
