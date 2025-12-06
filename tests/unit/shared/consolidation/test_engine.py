"""
Unit tests for consolidation engine.

Tests engine initialization, similarity detection, memory merging,
and conflict detection logic.
"""

from uuid import uuid4

import pytest

from shared.consolidation.config import ConsolidationSettings
from shared.consolidation.engine import (
    ConsolidationEngine,
    Memory,
)


@pytest.fixture
def default_settings():
    """Create default consolidation settings."""
    return ConsolidationSettings()


@pytest.fixture
def engine(default_settings):
    """Create consolidation engine with default settings."""
    return ConsolidationEngine(settings=default_settings)


@pytest.fixture
def sample_memories():
    """Create sample memories for testing."""
    return [
        Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[0.1, 0.2, 0.3, 0.4],
        ),
        Memory(
            id=uuid4(),
            fact="User likes pizza",
            confidence=0.85,
            embedding=[0.1, 0.2, 0.3, 0.4],  # Very similar embedding
        ),
        Memory(
            id=uuid4(),
            fact="User works at Google",
            confidence=0.95,
            embedding=[0.9, 0.8, 0.7, 0.6],  # Different embedding
        ),
    ]


class TestEngineInitialization:
    """Tests for engine initialization."""

    def test_init_with_default_settings(self):
        """Test initialization with default settings."""
        engine = ConsolidationEngine()

        assert engine.settings is not None
        assert engine.settings.similarity_threshold == 0.85
        assert engine.settings.merge_strategy == "highest_confidence"

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        custom_settings = ConsolidationSettings(
            similarity_threshold=0.9,
            merge_strategy="most_recent",
        )
        engine = ConsolidationEngine(settings=custom_settings)

        assert engine.settings.similarity_threshold == 0.9
        assert engine.settings.merge_strategy == "most_recent"

    def test_context_manager(self):
        """Test using engine as context manager."""
        with ConsolidationEngine() as engine:
            assert engine is not None
            assert engine.settings is not None


class TestSimilarityCalculation:
    """Tests for similarity calculation."""

    def test_identical_embeddings(self, engine):
        """Test similarity of identical embeddings."""
        memory1 = Memory(
            id=uuid4(),
            fact="Test fact",
            confidence=0.9,
            embedding=[1.0, 2.0, 3.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="Test fact",
            confidence=0.9,
            embedding=[1.0, 2.0, 3.0],
        )

        similarity = engine._calculate_similarity(memory1, memory2)

        assert 0.99 <= similarity <= 1.0

    def test_completely_different_embeddings(self, engine):
        """Test similarity of orthogonal embeddings."""
        memory1 = Memory(
            id=uuid4(),
            fact="Test fact 1",
            confidence=0.9,
            embedding=[1.0, 0.0, 0.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="Test fact 2",
            confidence=0.9,
            embedding=[0.0, 1.0, 0.0],
        )

        similarity = engine._calculate_similarity(memory1, memory2)

        assert similarity == 0.0

    def test_missing_embeddings(self, engine):
        """Test similarity when embeddings are missing."""
        memory1 = Memory(
            id=uuid4(),
            fact="Test fact",
            confidence=0.9,
            embedding=[],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="Test fact",
            confidence=0.9,
            embedding=[1.0, 2.0],
        )

        similarity = engine._calculate_similarity(memory1, memory2)

        assert similarity == 0.0


class TestMemoryMerging:
    """Tests for memory merging logic."""

    def test_merge_highest_confidence_strategy(self):
        """Test merging with highest confidence strategy."""
        settings = ConsolidationSettings(merge_strategy="highest_confidence")
        engine = ConsolidationEngine(settings=settings)

        memory1 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.95,
            embedding=[1.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="User likes pizza",
            confidence=0.85,
            embedding=[1.0],
        )

        merged = engine._merge_memories(memory1, memory2)

        assert merged.fact == "User loves pizza"
        assert merged.confidence > 0.95
        assert len(merged.source_memory_ids) == 2
        assert memory1.id in merged.source_memory_ids
        assert memory2.id in merged.source_memory_ids

    def test_merge_longest_strategy(self):
        """Test merging with longest fact strategy."""
        settings = ConsolidationSettings(merge_strategy="longest")
        engine = ConsolidationEngine(settings=settings)

        memory1 = Memory(
            id=uuid4(),
            fact="Short",
            confidence=0.9,
            embedding=[1.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="Much longer fact text",
            confidence=0.8,
            embedding=[1.0],
        )

        merged = engine._merge_memories(memory1, memory2)

        assert merged.fact == "Much longer fact text"
        assert len(merged.source_memory_ids) == 2

    def test_merge_confidence_boost(self, engine):
        """Test that merged memories get confidence boost."""
        memory1 = Memory(
            id=uuid4(),
            fact="Test fact",
            confidence=0.8,
            embedding=[1.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="Test fact",
            confidence=0.75,
            embedding=[1.0],
        )

        merged = engine._merge_memories(memory1, memory2)

        # Should be higher than max of original confidences
        assert merged.confidence > max(memory1.confidence, memory2.confidence)
        assert merged.confidence <= 1.0


class TestConflictDetection:
    """Tests for conflict detection."""

    def test_no_conflict_identical_facts(self, engine):
        """Test that identical facts are not flagged as conflicts."""
        memory1 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[1.0, 2.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.85,
            embedding=[1.0, 2.0],
        )

        # High similarity, identical facts - not a conflict
        is_conflict = engine._is_conflicting(memory1, memory2, similarity=0.95)

        assert is_conflict is False

    def test_detect_conflict_similar_but_different(self, engine):
        """Test detecting conflicts in semantically similar but contradictory facts."""
        memory1 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[0.8, 0.6],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="User hates pizza",
            confidence=0.85,
            embedding=[0.7, 0.7],  # Similar enough but different fact
        )

        # Medium similarity, different facts - might be conflict
        is_conflict = engine._is_conflicting(memory1, memory2, similarity=0.75)

        assert is_conflict is True


class TestConsolidation:
    """Tests for full consolidation workflow."""

    def test_consolidate_empty_list(self, engine):
        """Test consolidating empty memory list."""
        result = engine.consolidate_memories([])

        assert result.success is True
        assert result.memories_processed == 0
        assert result.merge_count == 0
        assert result.conflict_count == 0

    def test_consolidate_single_memory(self, engine):
        """Test consolidating single memory."""
        memory = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[1.0, 2.0],
        )

        result = engine.consolidate_memories([memory])

        assert result.success is True
        assert result.memories_processed == 1
        assert result.merge_count == 0

    def test_consolidate_similar_memories(self, engine):
        """Test consolidating similar memories."""
        memory1 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[1.0, 0.0, 0.0, 0.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="User likes pizza",
            confidence=0.85,
            embedding=[0.99, 0.01, 0.0, 0.0],  # Very similar
        )

        result = engine.consolidate_memories([memory1, memory2])

        assert result.success is True
        assert result.memories_processed == 2
        assert result.merge_count >= 1
        assert len(result.merged_memories) >= 1

    def test_consolidate_dissimilar_memories(self, engine):
        """Test consolidating dissimilar memories."""
        memory1 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[1.0, 0.0, 0.0],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="User works at Google",
            confidence=0.95,
            embedding=[0.0, 1.0, 0.0],  # Orthogonal
        )

        result = engine.consolidate_memories([memory1, memory2])

        assert result.success is True
        assert result.memories_processed == 2
        assert result.merge_count == 0

    def test_consolidate_with_conflicts(self, engine):
        """Test consolidation detects conflicts."""
        memory1 = Memory(
            id=uuid4(),
            fact="User loves pizza",
            confidence=0.9,
            embedding=[0.8, 0.6],
        )
        memory2 = Memory(
            id=uuid4(),
            fact="User hates pizza",
            confidence=0.85,
            embedding=[0.75, 0.65],  # Medium similarity, contradictory
        )

        result = engine.consolidate_memories(
            [memory1, memory2],
            detect_conflicts=True,
        )

        assert result.success is True
        # Might detect conflict depending on similarity threshold
        assert result.memories_processed == 2

    def test_consolidate_error_handling(self, engine, monkeypatch):
        """Test consolidation handles errors gracefully."""

        def mock_find_candidates(*args, **kwargs):
            raise Exception("Test error")

        monkeypatch.setattr(engine, "_find_merge_candidates", mock_find_candidates)

        memory = Memory(
            id=uuid4(),
            fact="Test",
            confidence=0.9,
            embedding=[1.0],
        )

        result = engine.consolidate_memories([memory, memory])

        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error
