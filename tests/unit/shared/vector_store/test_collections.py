"""
Tests for collection configuration utilities.
"""


from shared.vector_store.collections import (
    CollectionConfig,
    DistanceMetric,
    get_collection_configs,
    get_memory_collection_config,
)


class TestDistanceMetric:
    """Tests for DistanceMetric enum."""

    def test_has_cosine(self):
        """Test that COSINE metric exists."""
        assert DistanceMetric.COSINE == "Cosine"

    def test_has_euclidean(self):
        """Test that EUCLIDEAN metric exists."""
        assert DistanceMetric.EUCLIDEAN == "Euclid"

    def test_has_dot(self):
        """Test that DOT metric exists."""
        assert DistanceMetric.DOT == "Dot"


class TestCollectionConfig:
    """Tests for CollectionConfig."""

    def test_create_basic_config(self):
        """Test creating basic collection configuration."""
        config = CollectionConfig(
            name="test_collection",
            vector_size=768,
            distance=DistanceMetric.COSINE,
        )

        assert config.name == "test_collection"
        assert config.vector_size == 768
        assert config.distance == DistanceMetric.COSINE
        assert config.on_disk is False
        assert config.hnsw_config is None
        assert config.optimizers_config is None

    def test_create_config_with_hnsw(self):
        """Test creating configuration with HNSW settings."""
        hnsw = {"m": 16, "ef_construct": 100}
        config = CollectionConfig(
            name="test",
            vector_size=768,
            distance=DistanceMetric.EUCLIDEAN,
            hnsw_config=hnsw,
        )

        assert config.hnsw_config == hnsw

    def test_create_config_with_optimizers(self):
        """Test creating configuration with optimizer settings."""
        optimizers = {"indexing_threshold": 20000}
        config = CollectionConfig(
            name="test",
            vector_size=768,
            distance=DistanceMetric.DOT,
            optimizers_config=optimizers,
        )

        assert config.optimizers_config == optimizers

    def test_to_dict_basic(self):
        """Test converting basic config to dictionary."""
        config = CollectionConfig(
            name="test",
            vector_size=384,
            distance=DistanceMetric.COSINE,
        )

        result = config.to_dict()

        assert "vectors" in result
        assert result["vectors"]["size"] == 384
        assert result["vectors"]["distance"] == "Cosine"
        assert result["vectors"]["on_disk"] is False
        assert "hnsw_config" not in result
        assert "optimizers_config" not in result

    def test_to_dict_with_hnsw(self):
        """Test converting config with HNSW to dictionary."""
        hnsw = {"m": 16, "ef_construct": 100}
        config = CollectionConfig(
            name="test",
            vector_size=768,
            distance=DistanceMetric.COSINE,
            hnsw_config=hnsw,
        )

        result = config.to_dict()

        assert "hnsw_config" in result
        assert result["hnsw_config"] == hnsw

    def test_to_dict_with_optimizers(self):
        """Test converting config with optimizers to dictionary."""
        optimizers = {"indexing_threshold": 10000}
        config = CollectionConfig(
            name="test",
            vector_size=768,
            distance=DistanceMetric.COSINE,
            optimizers_config=optimizers,
        )

        result = config.to_dict()

        assert "optimizers_config" in result
        assert result["optimizers_config"] == optimizers

    def test_to_dict_on_disk(self):
        """Test converting config with on_disk flag."""
        config = CollectionConfig(
            name="test",
            vector_size=768,
            distance=DistanceMetric.COSINE,
            on_disk=True,
        )

        result = config.to_dict()

        assert result["vectors"]["on_disk"] is True


class TestGetMemoryCollectionConfig:
    """Tests for get_memory_collection_config."""

    def test_returns_collection_config(self):
        """Test that function returns CollectionConfig."""
        config = get_memory_collection_config()
        assert isinstance(config, CollectionConfig)

    def test_collection_name(self):
        """Test collection name is correct."""
        config = get_memory_collection_config()
        assert config.name == "memories"

    def test_vector_size(self):
        """Test vector size matches OpenAI ada-002."""
        config = get_memory_collection_config()
        assert config.vector_size == 1536

    def test_distance_metric(self):
        """Test uses cosine similarity."""
        config = get_memory_collection_config()
        assert config.distance == DistanceMetric.COSINE

    def test_not_on_disk(self):
        """Test collection is in-memory."""
        config = get_memory_collection_config()
        assert config.on_disk is False

    def test_has_hnsw_config(self):
        """Test has HNSW configuration."""
        config = get_memory_collection_config()
        assert config.hnsw_config is not None
        assert "m" in config.hnsw_config
        assert "ef_construct" in config.hnsw_config
        assert "full_scan_threshold" in config.hnsw_config

    def test_has_optimizer_config(self):
        """Test has optimizer configuration."""
        config = get_memory_collection_config()
        assert config.optimizers_config is not None
        assert "indexing_threshold" in config.optimizers_config


class TestGetCollectionConfigs:
    """Tests for get_collection_configs."""

    def test_returns_list(self):
        """Test returns list of configs."""
        configs = get_collection_configs()
        assert isinstance(configs, list)

    def test_contains_memory_collection(self):
        """Test list contains memories collection."""
        configs = get_collection_configs()
        names = [c.name for c in configs]
        assert "memories" in names

    def test_all_items_are_collection_configs(self):
        """Test all items are CollectionConfig instances."""
        configs = get_collection_configs()
        assert all(isinstance(c, CollectionConfig) for c in configs)

    def test_non_empty(self):
        """Test returns at least one configuration."""
        configs = get_collection_configs()
        assert len(configs) > 0
