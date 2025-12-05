"""
Unit tests for Memory service.

Tests business logic and confidence management.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.core.config import MemoryServiceSettings
from services.memory.app.services.memory_service import MemoryService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=MemoryServiceSettings)
    settings.default_confidence = 1.0
    settings.default_importance = 0.5
    settings.default_memory_ttl_days = 365
    settings.max_memory_ttl_days = 730
    settings.confidence_decay_rate = 0.1
    settings.min_confidence_threshold = 0.3
    settings.enable_revision_tracking = True
    settings.max_revisions_per_memory = 50
    return settings


@pytest.fixture
def memory_service(mock_db, mock_settings):
    """Create memory service with mocks."""
    return MemoryService(mock_db, mock_settings)


@pytest.fixture
def sample_memory():
    """Create a sample memory for testing."""
    memory = MagicMock()
    memory.id = uuid4()
    memory.scope = {"user_id": "test_user"}
    memory.fact = "User prefers dark mode"
    memory.topic = "preferences"
    memory.embedding = [0.1, 0.2, 0.3]
    memory.confidence = 0.9
    memory.importance = 0.7
    memory.access_count = 0
    memory.last_accessed_at = None
    memory.source_type = "conversation"
    memory.source_id = uuid4()
    memory.expires_at = None
    memory.deleted_at = None
    memory.created_at = datetime.now(UTC)
    memory.updated_at = datetime.now(UTC)
    return memory


class TestCreateMemory:
    """Tests for create_memory method."""

    @pytest.mark.asyncio
    async def test_creates_memory_with_defaults(self, memory_service, sample_memory):
        """Test creating a memory with default settings."""
        memory_service.memory_repo.create_memory = AsyncMock(return_value=sample_memory)

        result = await memory_service.create_memory(
            scope={"user_id": "test_user"},
            fact="User likes Python",
            source_type="conversation",
        )

        memory_service.memory_repo.create_memory.assert_called_once()
        call_kwargs = memory_service.memory_repo.create_memory.call_args.kwargs

        # Check defaults were applied
        assert call_kwargs["confidence"] == 1.0
        assert call_kwargs["importance"] == 0.5
        assert call_kwargs["expires_at"] is not None
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_creates_memory_with_custom_values(self, memory_service, sample_memory):
        """Test creating a memory with custom values."""
        memory_service.memory_repo.create_memory = AsyncMock(return_value=sample_memory)

        result = await memory_service.create_memory(
            scope={"user_id": "test_user"},
            fact="User knows TypeScript",
            source_type="extraction",
            topic="skills",
            embedding=[0.1, 0.2],
            confidence=0.95,
            importance=0.8,
            ttl_days=30,
        )

        memory_service.memory_repo.create_memory.assert_called_once()
        call_kwargs = memory_service.memory_repo.create_memory.call_args.kwargs

        assert call_kwargs["confidence"] == 0.95
        assert call_kwargs["importance"] == 0.8
        assert call_kwargs["topic"] == "skills"
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_caps_ttl_at_maximum(self, memory_service, sample_memory):
        """Test that TTL is capped at maximum."""
        memory_service.memory_repo.create_memory = AsyncMock(return_value=sample_memory)

        await memory_service.create_memory(
            scope={"user_id": "test_user"},
            fact="Test fact",
            source_type="manual",
            ttl_days=1000,  # Exceeds max of 730
        )

        call_kwargs = memory_service.memory_repo.create_memory.call_args.kwargs
        expires_at = call_kwargs["expires_at"]

        # Should be capped at 730 days
        expected_max = datetime.now(UTC) + timedelta(days=730)
        time_diff = abs((expires_at - expected_max).total_seconds())
        assert time_diff < 2  # Within 2 seconds


class TestGetMemory:
    """Tests for get_memory method."""

    @pytest.mark.asyncio
    async def test_gets_memory_and_updates_access(self, memory_service, sample_memory):
        """Test getting a memory updates access tracking."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)
        memory_service.memory_repo.update_access = AsyncMock(return_value=sample_memory)

        result = await memory_service.get_memory(sample_memory.id)

        memory_service.memory_repo.get_by_id.assert_called_once_with(sample_memory.id)
        memory_service.memory_repo.update_access.assert_called_once_with(sample_memory.id)
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_memory(self, memory_service):
        """Test returns None when memory not found."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=None)

        result = await memory_service.get_memory(uuid4())

        assert result is None


class TestUpdateMemory:
    """Tests for update_memory method."""

    @pytest.mark.asyncio
    async def test_updates_memory_fact_with_revision(self, memory_service, sample_memory):
        """Test updating fact creates revision."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)
        memory_service.revision_service.create_revision = AsyncMock()
        memory_service.revision_service.prune_old_revisions = AsyncMock()

        old_fact = sample_memory.fact
        new_fact = "User prefers light mode"

        result = await memory_service.update_memory(
            memory_id=sample_memory.id,
            fact=new_fact,
            change_reason="User corrected preference",
        )

        # Check revision was created
        memory_service.revision_service.create_revision.assert_called_once_with(
            memory_id=sample_memory.id,
            previous_fact=old_fact,
            new_fact=new_fact,
            change_reason="User corrected preference",
        )

        # Check fact was updated
        assert sample_memory.fact == new_fact
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_updates_memory_without_fact_change(self, memory_service, sample_memory):
        """Test updating other fields without fact change."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)
        memory_service.revision_service.create_revision = AsyncMock()
        memory_service.revision_service.prune_old_revisions = AsyncMock()

        result = await memory_service.update_memory(
            memory_id=sample_memory.id,
            topic="updated_topic",
            confidence=0.8,
            importance=0.9,
        )

        # No revision should be created
        memory_service.revision_service.create_revision.assert_not_called()

        # Fields should be updated
        assert sample_memory.topic == "updated_topic"
        assert sample_memory.confidence == 0.8
        assert sample_memory.importance == 0.9
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_prunes_old_revisions_after_update(self, memory_service, sample_memory):
        """Test that old revisions are pruned after update."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)
        memory_service.revision_service.create_revision = AsyncMock()
        memory_service.revision_service.prune_old_revisions = AsyncMock()

        await memory_service.update_memory(
            memory_id=sample_memory.id,
            fact="New fact",
        )

        memory_service.revision_service.prune_old_revisions.assert_called_once_with(
            sample_memory.id,
            50,  # max_revisions_per_memory from settings
        )

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_memory(self, memory_service):
        """Test returns None when memory not found."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=None)

        result = await memory_service.update_memory(
            memory_id=uuid4(),
            fact="New fact",
        )

        assert result is None


class TestUpdateConfidence:
    """Tests for update_confidence method."""

    @pytest.mark.asyncio
    async def test_updates_confidence_directly(self, memory_service, sample_memory):
        """Test direct confidence update."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)

        result = await memory_service.update_confidence(
            memory_id=sample_memory.id,
            new_confidence=0.7,
            decay=False,
        )

        assert sample_memory.confidence == 0.7
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_applies_confidence_decay(self, memory_service, sample_memory):
        """Test confidence decay."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)
        sample_memory.confidence = 0.5

        result = await memory_service.update_confidence(
            memory_id=sample_memory.id,
            new_confidence=0.0,  # Ignored when decay=True
            decay=True,
        )

        # Should be 0.5 - 0.1 = 0.4
        assert sample_memory.confidence == 0.4
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_confidence_does_not_go_below_zero(self, memory_service, sample_memory):
        """Test confidence is bounded at 0."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)
        sample_memory.confidence = 0.05

        await memory_service.update_confidence(
            memory_id=sample_memory.id,
            new_confidence=0.0,
            decay=True,
        )

        assert sample_memory.confidence == 0.0

    @pytest.mark.asyncio
    async def test_confidence_capped_at_one(self, memory_service, sample_memory):
        """Test confidence is capped at 1.0."""
        memory_service.memory_repo.get_by_id = AsyncMock(return_value=sample_memory)

        await memory_service.update_confidence(
            memory_id=sample_memory.id,
            new_confidence=1.5,
            decay=False,
        )

        assert sample_memory.confidence == 1.0


class TestDeleteAndRestore:
    """Tests for delete and restore methods."""

    @pytest.mark.asyncio
    async def test_deletes_memory(self, memory_service, sample_memory):
        """Test soft-deleting a memory."""
        memory_service.memory_repo.soft_delete = AsyncMock(return_value=sample_memory)

        result = await memory_service.delete_memory(sample_memory.id)

        memory_service.memory_repo.soft_delete.assert_called_once_with(sample_memory.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_nonexistent(self, memory_service):
        """Test delete returns False when memory not found."""
        memory_service.memory_repo.soft_delete = AsyncMock(return_value=None)

        result = await memory_service.delete_memory(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_restores_memory(self, memory_service, sample_memory):
        """Test restoring a soft-deleted memory."""
        memory_service.memory_repo.restore = AsyncMock(return_value=sample_memory)

        result = await memory_service.restore_memory(sample_memory.id)

        memory_service.memory_repo.restore.assert_called_once_with(sample_memory.id)
        assert result == sample_memory


class TestGetMemoriesByScope:
    """Tests for get_memories_by_scope method."""

    @pytest.mark.asyncio
    async def test_gets_memories_by_scope(self, memory_service):
        """Test getting memories by scope."""
        mock_memories = [MagicMock(), MagicMock()]
        memory_service.memory_repo.get_by_scope = AsyncMock(return_value=mock_memories)

        scope = {"user_id": "test_user"}
        result = await memory_service.get_memories_by_scope(scope)

        memory_service.memory_repo.get_by_scope.assert_called_once_with(
            scope=scope,
            limit=100,
            offset=0,
            include_deleted=False,
        )
        assert result == mock_memories

    @pytest.mark.asyncio
    async def test_gets_memories_by_scope_and_topic(self, memory_service):
        """Test getting memories by scope and topic."""
        mock_memories = [MagicMock()]
        memory_service.memory_repo.get_by_topic = AsyncMock(return_value=mock_memories)

        scope = {"user_id": "test_user"}
        result = await memory_service.get_memories_by_scope(
            scope=scope,
            topic="skills",
            limit=50,
        )

        memory_service.memory_repo.get_by_topic.assert_called_once_with(
            scope=scope,
            topic="skills",
            limit=50,
            include_deleted=False,
        )
        assert result == mock_memories


class TestGetLowConfidenceMemories:
    """Tests for get_low_confidence_memories method."""

    @pytest.mark.asyncio
    async def test_filters_low_confidence_memories(self, memory_service):
        """Test filtering memories by confidence threshold."""
        high_conf = MagicMock()
        high_conf.confidence = 0.8

        low_conf1 = MagicMock()
        low_conf1.confidence = 0.2

        low_conf2 = MagicMock()
        low_conf2.confidence = 0.25

        memory_service.memory_repo.get_by_scope = AsyncMock(
            return_value=[high_conf, low_conf1, low_conf2]
        )

        scope = {"user_id": "test_user"}
        result = await memory_service.get_low_confidence_memories(scope)

        # Should only return memories below 0.3 threshold
        assert len(result) == 2
        assert low_conf1 in result
        assert low_conf2 in result
        assert high_conf not in result

    @pytest.mark.asyncio
    async def test_uses_custom_threshold(self, memory_service):
        """Test using custom confidence threshold."""
        mem1 = MagicMock()
        mem1.confidence = 0.4

        mem2 = MagicMock()
        mem2.confidence = 0.6

        memory_service.memory_repo.get_by_scope = AsyncMock(return_value=[mem1, mem2])

        scope = {"user_id": "test_user"}
        result = await memory_service.get_low_confidence_memories(scope, threshold=0.5)

        # Should only return mem1 (below 0.5)
        assert len(result) == 1
        assert mem1 in result


class TestCleanupExpiredMemories:
    """Tests for cleanup_expired_memories method."""

    @pytest.mark.asyncio
    async def test_deletes_expired_memories(self, memory_service):
        """Test deleting expired memories."""
        memory_service.memory_repo.delete_expired_memories = AsyncMock(return_value=5)

        count = await memory_service.cleanup_expired_memories()

        memory_service.memory_repo.delete_expired_memories.assert_called_once()
        assert count == 5


class TestCountMemories:
    """Tests for count_memories method."""

    @pytest.mark.asyncio
    async def test_counts_memories(self, memory_service):
        """Test counting memories."""
        memory_service.memory_repo.count_memories = AsyncMock(return_value=42)

        scope = {"user_id": "test_user"}
        count = await memory_service.count_memories(scope, topic="skills")

        memory_service.memory_repo.count_memories.assert_called_once_with(
            scope=scope,
            topic="skills",
            include_deleted=False,
        )
        assert count == 42
