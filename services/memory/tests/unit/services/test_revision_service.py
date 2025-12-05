"""
Unit tests for Revision service.

Tests revision creation and history management.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.services.revision_service import RevisionService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def revision_service(mock_db):
    """Create revision service with mock database."""
    return RevisionService(mock_db)


@pytest.fixture
def sample_revision():
    """Create a sample revision for testing."""
    revision = MagicMock()
    revision.id = uuid4()
    revision.memory_id = uuid4()
    revision.revision_number = 1
    revision.previous_fact = "Old fact"
    revision.new_fact = "New fact"
    revision.change_reason = "Correction"
    return revision


class TestCreateRevision:
    """Tests for create_revision method."""

    @pytest.mark.asyncio
    async def test_creates_revision_with_auto_number(self, revision_service, sample_revision):
        """Test creating a revision with auto-incremented number."""
        memory_id = uuid4()

        revision_service.revision_repo.get_next_revision_number = AsyncMock(return_value=3)
        revision_service.revision_repo.create_revision = AsyncMock(return_value=sample_revision)

        result = await revision_service.create_revision(
            memory_id=memory_id,
            previous_fact="User prefers light mode",
            new_fact="User prefers dark mode",
            change_reason="User corrected preference",
        )

        # Check next number was retrieved
        revision_service.revision_repo.get_next_revision_number.assert_called_once_with(memory_id)

        # Check revision was created with correct number
        revision_service.revision_repo.create_revision.assert_called_once_with(
            memory_id=memory_id,
            revision_number=3,
            previous_fact="User prefers light mode",
            new_fact="User prefers dark mode",
            change_reason="User corrected preference",
        )

        assert result == sample_revision

    @pytest.mark.asyncio
    async def test_creates_revision_without_reason(self, revision_service, sample_revision):
        """Test creating a revision without change reason."""
        memory_id = uuid4()

        revision_service.revision_repo.get_next_revision_number = AsyncMock(return_value=1)
        revision_service.revision_repo.create_revision = AsyncMock(return_value=sample_revision)

        result = await revision_service.create_revision(
            memory_id=memory_id,
            previous_fact="Old fact",
            new_fact="New fact",
        )

        call_kwargs = revision_service.revision_repo.create_revision.call_args.kwargs
        assert call_kwargs["change_reason"] is None
        assert result == sample_revision


class TestGetMemoryHistory:
    """Tests for get_memory_history method."""

    @pytest.mark.asyncio
    async def test_gets_memory_history(self, revision_service):
        """Test getting revision history."""
        memory_id = uuid4()
        mock_revisions = [MagicMock(), MagicMock()]

        revision_service.revision_repo.get_memory_revisions = AsyncMock(return_value=mock_revisions)

        result = await revision_service.get_memory_history(memory_id)

        revision_service.revision_repo.get_memory_revisions.assert_called_once_with(
            memory_id,
            limit=10,
            offset=0,
        )
        assert result == mock_revisions

    @pytest.mark.asyncio
    async def test_supports_pagination(self, revision_service):
        """Test pagination parameters."""
        memory_id = uuid4()

        revision_service.revision_repo.get_memory_revisions = AsyncMock(return_value=[])

        await revision_service.get_memory_history(memory_id, limit=20, offset=5)

        revision_service.revision_repo.get_memory_revisions.assert_called_once_with(
            memory_id,
            limit=20,
            offset=5,
        )


class TestGetLatestRevision:
    """Tests for get_latest_revision method."""

    @pytest.mark.asyncio
    async def test_gets_latest_revision(self, revision_service, sample_revision):
        """Test getting the most recent revision."""
        memory_id = uuid4()

        revision_service.revision_repo.get_latest_revision = AsyncMock(return_value=sample_revision)

        result = await revision_service.get_latest_revision(memory_id)

        revision_service.revision_repo.get_latest_revision.assert_called_once_with(memory_id)
        assert result == sample_revision

    @pytest.mark.asyncio
    async def test_returns_none_when_no_revisions(self, revision_service):
        """Test returns None when no revisions exist."""
        memory_id = uuid4()

        revision_service.revision_repo.get_latest_revision = AsyncMock(return_value=None)

        result = await revision_service.get_latest_revision(memory_id)

        assert result is None


class TestGetRevisionByNumber:
    """Tests for get_revision_by_number method."""

    @pytest.mark.asyncio
    async def test_gets_specific_revision(self, revision_service, sample_revision):
        """Test getting a revision by number."""
        memory_id = uuid4()
        revision_number = 5

        revision_service.revision_repo.get_revision_by_number = AsyncMock(
            return_value=sample_revision
        )

        result = await revision_service.get_revision_by_number(memory_id, revision_number)

        revision_service.revision_repo.get_revision_by_number.assert_called_once_with(
            memory_id,
            revision_number,
        )
        assert result == sample_revision

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, revision_service):
        """Test returns None for nonexistent revision."""
        memory_id = uuid4()

        revision_service.revision_repo.get_revision_by_number = AsyncMock(return_value=None)

        result = await revision_service.get_revision_by_number(memory_id, 999)

        assert result is None


class TestCountRevisions:
    """Tests for count_revisions method."""

    @pytest.mark.asyncio
    async def test_counts_revisions(self, revision_service):
        """Test counting revisions."""
        memory_id = uuid4()

        revision_service.revision_repo.count_revisions = AsyncMock(return_value=10)

        count = await revision_service.count_revisions(memory_id)

        revision_service.revision_repo.count_revisions.assert_called_once_with(memory_id)
        assert count == 10


class TestDeleteMemoryRevisions:
    """Tests for delete_memory_revisions method."""

    @pytest.mark.asyncio
    async def test_deletes_all_revisions(self, revision_service):
        """Test deleting all revisions for a memory."""
        memory_id = uuid4()

        revision_service.revision_repo.delete_memory_revisions = AsyncMock(return_value=5)

        count = await revision_service.delete_memory_revisions(memory_id)

        revision_service.revision_repo.delete_memory_revisions.assert_called_once_with(memory_id)
        assert count == 5


class TestPruneOldRevisions:
    """Tests for prune_old_revisions method."""

    @pytest.mark.asyncio
    async def test_prunes_when_exceeds_limit(self, revision_service):
        """Test pruning old revisions when limit exceeded."""
        memory_id = uuid4()

        # Create 10 mock revisions
        mock_revisions = [MagicMock(id=uuid4()) for _ in range(10)]

        revision_service.revision_repo.get_memory_revisions = AsyncMock(return_value=mock_revisions)
        revision_service.revision_repo.delete = AsyncMock()

        # Keep only 5 most recent
        count = await revision_service.prune_old_revisions(memory_id, max_revisions=5)

        # Should delete 5 oldest revisions (indices 5-9)
        assert count == 5
        assert revision_service.revision_repo.delete.call_count == 5

        # Verify the correct revisions were deleted (oldest ones)
        deleted_revisions = [
            call.args[0] for call in revision_service.revision_repo.delete.call_args_list
        ]
        for i in range(5, 10):
            assert mock_revisions[i] in deleted_revisions

    @pytest.mark.asyncio
    async def test_does_not_prune_when_under_limit(self, revision_service):
        """Test no pruning when under limit."""
        memory_id = uuid4()

        # Create only 3 revisions
        mock_revisions = [MagicMock(id=uuid4()) for _ in range(3)]

        revision_service.revision_repo.get_memory_revisions = AsyncMock(return_value=mock_revisions)
        revision_service.revision_repo.delete = AsyncMock()

        # Keep 5 most recent (but only have 3)
        count = await revision_service.prune_old_revisions(memory_id, max_revisions=5)

        # Should not delete any
        assert count == 0
        revision_service.revision_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_prune_when_at_limit(self, revision_service):
        """Test no pruning when exactly at limit."""
        memory_id = uuid4()

        # Create exactly 5 revisions
        mock_revisions = [MagicMock(id=uuid4()) for _ in range(5)]

        revision_service.revision_repo.get_memory_revisions = AsyncMock(return_value=mock_revisions)
        revision_service.revision_repo.delete = AsyncMock()

        # Keep 5 most recent (exactly what we have)
        count = await revision_service.prune_old_revisions(memory_id, max_revisions=5)

        # Should not delete any
        assert count == 0
        revision_service.revision_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_empty_revisions(self, revision_service):
        """Test handling when no revisions exist."""
        memory_id = uuid4()

        revision_service.revision_repo.get_memory_revisions = AsyncMock(return_value=[])
        revision_service.revision_repo.delete = AsyncMock()

        count = await revision_service.prune_old_revisions(memory_id, max_revisions=5)

        assert count == 0
        revision_service.revision_repo.delete.assert_not_called()
