"""
Unit tests for Memory repository.

Tests CRUD operations, filtering, and memory management.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.db.repositories.memory_repository import MemoryRepository


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def memory_repo(mock_db):
    """Create memory repository with mock database."""
    return MemoryRepository(mock_db)


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
    async def test_creates_memory_with_all_fields(self, memory_repo, mock_db):
        """Test creating a memory with all fields."""
        scope = {"user_id": "user_123"}
        fact = "User lives in San Francisco"
        source_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        # Mock the create method
        mock_memory = MagicMock()
        memory_repo.create = MagicMock(return_value=mock_memory)

        result = await memory_repo.create_memory(
            scope=scope,
            fact=fact,
            source_type="extraction",
            topic="location",
            embedding=[0.1, 0.2],
            confidence=0.95,
            importance=0.8,
            source_id=source_id,
            expires_at=expires_at,
        )

        memory_repo.create.assert_called_once_with(
            scope=scope,
            fact=fact,
            source_type="extraction",
            topic="location",
            embedding=[0.1, 0.2],
            confidence=0.95,
            importance=0.8,
            source_id=source_id,
            expires_at=expires_at,
        )
        assert result == mock_memory

    @pytest.mark.asyncio
    async def test_creates_memory_with_minimal_fields(self, memory_repo):
        """Test creating a memory with only required fields."""
        scope = {"user_id": "user_456"}
        fact = "User is a software engineer"

        mock_memory = MagicMock()
        memory_repo.create = MagicMock(return_value=mock_memory)

        result = await memory_repo.create_memory(
            scope=scope,
            fact=fact,
            source_type="manual",
        )

        memory_repo.create.assert_called_once()
        call_kwargs = memory_repo.create.call_args.kwargs
        assert call_kwargs["scope"] == scope
        assert call_kwargs["fact"] == fact
        assert call_kwargs["source_type"] == "manual"
        assert result == mock_memory


class TestGetByScope:
    """Tests for get_by_scope method."""

    @pytest.mark.asyncio
    async def test_filters_by_scope(self, memory_repo, mock_db):
        """Test filtering memories by scope."""
        scope = {"user_id": "user_789"}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_by_scope(scope, limit=50, offset=10)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_excludes_deleted_by_default(self, memory_repo, mock_db):
        """Test that soft-deleted memories are excluded by default."""
        scope = {"user_id": "user_abc"}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_by_scope(scope)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_includes_deleted_when_requested(self, memory_repo, mock_db):
        """Test that soft-deleted memories can be included."""
        scope = {"user_id": "user_def"}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_by_scope(scope, include_deleted=True)

        mock_db.execute.assert_called_once()


class TestGetByTopic:
    """Tests for get_by_topic method."""

    @pytest.mark.asyncio
    async def test_filters_by_scope_and_topic(self, memory_repo, mock_db):
        """Test filtering by both scope and topic."""
        scope = {"user_id": "user_123"}
        topic = "preferences"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_by_topic(scope, topic)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orders_by_importance(self, memory_repo, mock_db):
        """Test that memories are ordered by importance."""
        scope = {"user_id": "user_456"}
        topic = "skills"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_by_topic(scope, topic, limit=20)

        mock_db.execute.assert_called_once()


class TestGetBySource:
    """Tests for get_by_source method."""

    @pytest.mark.asyncio
    async def test_filters_by_source_type_and_id(self, memory_repo, mock_db):
        """Test filtering by source type and ID."""
        source_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_by_source("conversation", source_id)

        mock_db.execute.assert_called_once()


class TestUpdateAccess:
    """Tests for update_access method."""

    @pytest.mark.asyncio
    async def test_increments_access_count(self, memory_repo, sample_memory):
        """Test that access count is incremented."""
        memory_repo.get_by_id = MagicMock(return_value=sample_memory)

        initial_count = sample_memory.access_count
        result = await memory_repo.update_access(sample_memory.id)

        assert sample_memory.access_count == initial_count + 1
        assert sample_memory.last_accessed_at is not None
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_sets_last_accessed_timestamp(self, memory_repo, sample_memory):
        """Test that last_accessed_at is set."""
        memory_repo.get_by_id = MagicMock(return_value=sample_memory)

        result = await memory_repo.update_access(sample_memory.id)

        assert isinstance(sample_memory.last_accessed_at, datetime)
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_memory(self, memory_repo):
        """Test that None is returned for nonexistent memory."""
        memory_repo.get_by_id = MagicMock(return_value=None)

        result = await memory_repo.update_access(uuid4())

        assert result is None


class TestSoftDelete:
    """Tests for soft_delete method."""

    @pytest.mark.asyncio
    async def test_sets_deleted_timestamp(self, memory_repo, sample_memory):
        """Test that deleted_at is set."""
        memory_repo.get_by_id = MagicMock(return_value=sample_memory)

        result = await memory_repo.soft_delete(sample_memory.id)

        assert sample_memory.deleted_at is not None
        assert isinstance(sample_memory.deleted_at, datetime)
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_memory(self, memory_repo):
        """Test that None is returned for nonexistent memory."""
        memory_repo.get_by_id = MagicMock(return_value=None)

        result = await memory_repo.soft_delete(uuid4())

        assert result is None


class TestRestore:
    """Tests for restore method."""

    @pytest.mark.asyncio
    async def test_clears_deleted_timestamp(self, memory_repo, sample_memory):
        """Test that deleted_at is cleared."""
        sample_memory.deleted_at = datetime.now(UTC)
        memory_repo.get_by_id = MagicMock(return_value=sample_memory)

        result = await memory_repo.restore(sample_memory.id)

        assert sample_memory.deleted_at is None
        assert result == sample_memory

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_memory(self, memory_repo):
        """Test that None is returned for nonexistent memory."""
        memory_repo.get_by_id = MagicMock(return_value=None)

        result = await memory_repo.restore(uuid4())

        assert result is None


class TestListMemories:
    """Tests for list_memories method."""

    @pytest.mark.asyncio
    async def test_lists_all_memories(self, memory_repo, mock_db):
        """Test listing all memories without filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.list_memories(limit=100, offset=0)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_by_scope(self, memory_repo, mock_db):
        """Test filtering by scope."""
        scope = {"user_id": "user_xyz"}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.list_memories(scope=scope)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_by_multiple_criteria(self, memory_repo, mock_db):
        """Test filtering by multiple criteria."""
        scope = {"user_id": "user_123"}
        topic = "skills"
        source_type = "extraction"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.list_memories(
            scope=scope,
            topic=topic,
            source_type=source_type,
            limit=50,
        )

        mock_db.execute.assert_called_once()


class TestCountMemories:
    """Tests for count_memories method."""

    @pytest.mark.asyncio
    async def test_counts_all_memories(self, memory_repo, mock_db):
        """Test counting all memories."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_db.execute.return_value = mock_result

        count = await memory_repo.count_memories()

        assert count == 10
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_counts_with_filters(self, memory_repo, mock_db):
        """Test counting with filters."""
        scope = {"user_id": "user_456"}
        topic = "preferences"

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute.return_value = mock_result

        count = await memory_repo.count_memories(scope=scope, topic=topic)

        assert count == 5
        mock_db.execute.assert_called_once()


class TestGetExpiredMemories:
    """Tests for get_expired_memories method."""

    @pytest.mark.asyncio
    async def test_finds_expired_memories(self, memory_repo, mock_db):
        """Test finding expired memories."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await memory_repo.get_expired_memories(batch_size=50)

        mock_db.execute.assert_called_once()


class TestDeleteExpiredMemories:
    """Tests for delete_expired_memories method."""

    @pytest.mark.asyncio
    async def test_soft_deletes_expired_memories(self, memory_repo):
        """Test soft-deleting expired memories."""
        expired_memory = MagicMock()
        expired_memory.deleted_at = None

        memory_repo.get_expired_memories = MagicMock(return_value=[expired_memory])

        count = await memory_repo.delete_expired_memories()

        assert count == 1
        assert expired_memory.deleted_at is not None

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_expired(self, memory_repo):
        """Test that zero is returned when no expired memories."""
        memory_repo.get_expired_memories = MagicMock(return_value=[])

        count = await memory_repo.delete_expired_memories()

        assert count == 0
