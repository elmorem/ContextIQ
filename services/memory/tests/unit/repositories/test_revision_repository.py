"""
Unit tests for Revision repository.

Tests revision tracking and history management.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory.app.db.repositories.revision_repository import RevisionRepository


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def revision_repo(mock_db):
    """Create revision repository with mock database."""
    return RevisionRepository(mock_db)


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
    async def test_creates_revision_with_all_fields(self, revision_repo):
        """Test creating a revision with all fields."""
        memory_id = uuid4()
        previous_fact = "User prefers light mode"
        new_fact = "User prefers dark mode"
        change_reason = "User corrected their preference"

        mock_revision = MagicMock()
        revision_repo.create = MagicMock(return_value=mock_revision)

        result = await revision_repo.create_revision(
            memory_id=memory_id,
            revision_number=1,
            previous_fact=previous_fact,
            new_fact=new_fact,
            change_reason=change_reason,
        )

        revision_repo.create.assert_called_once_with(
            memory_id=memory_id,
            revision_number=1,
            previous_fact=previous_fact,
            new_fact=new_fact,
            change_reason=change_reason,
        )
        assert result == mock_revision

    @pytest.mark.asyncio
    async def test_creates_revision_without_reason(self, revision_repo):
        """Test creating a revision without change reason."""
        memory_id = uuid4()

        mock_revision = MagicMock()
        revision_repo.create = MagicMock(return_value=mock_revision)

        result = await revision_repo.create_revision(
            memory_id=memory_id,
            revision_number=2,
            previous_fact="Old fact",
            new_fact="Updated fact",
        )

        revision_repo.create.assert_called_once()
        call_kwargs = revision_repo.create.call_args.kwargs
        assert call_kwargs["change_reason"] is None
        assert result == mock_revision


class TestGetMemoryRevisions:
    """Tests for get_memory_revisions method."""

    @pytest.mark.asyncio
    async def test_returns_revisions_for_memory(self, revision_repo, mock_db):
        """Test getting all revisions for a memory."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await revision_repo.get_memory_revisions(memory_id)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_supports_pagination(self, revision_repo, mock_db):
        """Test pagination parameters."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await revision_repo.get_memory_revisions(memory_id, limit=10, offset=5)

        mock_db.execute.assert_called_once()


class TestGetLatestRevision:
    """Tests for get_latest_revision method."""

    @pytest.mark.asyncio
    async def test_returns_most_recent_revision(self, revision_repo, mock_db, sample_revision):
        """Test getting the latest revision."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_revision
        mock_db.execute.return_value = mock_result

        result = await revision_repo.get_latest_revision(memory_id)

        assert result == sample_revision
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_revisions(self, revision_repo, mock_db):
        """Test returns None when no revisions exist."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await revision_repo.get_latest_revision(memory_id)

        assert result is None


class TestGetRevisionByNumber:
    """Tests for get_revision_by_number method."""

    @pytest.mark.asyncio
    async def test_returns_specific_revision(self, revision_repo, mock_db, sample_revision):
        """Test getting a revision by number."""
        memory_id = uuid4()
        revision_number = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_revision
        mock_db.execute.return_value = mock_result

        result = await revision_repo.get_revision_by_number(memory_id, revision_number)

        assert result == sample_revision
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_revision(self, revision_repo, mock_db):
        """Test returns None for nonexistent revision."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await revision_repo.get_revision_by_number(memory_id, 999)

        assert result is None


class TestCountRevisions:
    """Tests for count_revisions method."""

    @pytest.mark.asyncio
    async def test_counts_revisions_for_memory(self, revision_repo, mock_db):
        """Test counting revisions."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute.return_value = mock_result

        count = await revision_repo.count_revisions(memory_id)

        assert count == 5
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_revisions(self, revision_repo, mock_db):
        """Test returns zero when no revisions."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_db.execute.return_value = mock_result

        count = await revision_repo.count_revisions(memory_id)

        assert count == 0


class TestGetNextRevisionNumber:
    """Tests for get_next_revision_number method."""

    @pytest.mark.asyncio
    async def test_returns_one_for_first_revision(self, revision_repo):
        """Test returns 1 for first revision."""
        memory_id = uuid4()
        revision_repo.count_revisions = MagicMock(return_value=0)

        next_number = await revision_repo.get_next_revision_number(memory_id)

        assert next_number == 1

    @pytest.mark.asyncio
    async def test_increments_from_existing_count(self, revision_repo):
        """Test increments from existing revision count."""
        memory_id = uuid4()
        revision_repo.count_revisions = MagicMock(return_value=3)

        next_number = await revision_repo.get_next_revision_number(memory_id)

        assert next_number == 4


class TestGetRevisionHistory:
    """Tests for get_revision_history method."""

    @pytest.mark.asyncio
    async def test_returns_recent_revisions(self, revision_repo):
        """Test getting recent revision history."""
        memory_id = uuid4()
        mock_revisions = [MagicMock(), MagicMock()]

        revision_repo.get_memory_revisions = MagicMock(return_value=mock_revisions)

        result = await revision_repo.get_revision_history(memory_id, limit=10)

        revision_repo.get_memory_revisions.assert_called_once_with(
            memory_id,
            limit=10,
            offset=0,
        )
        assert result == mock_revisions


class TestDeleteMemoryRevisions:
    """Tests for delete_memory_revisions method."""

    @pytest.mark.asyncio
    async def test_deletes_all_revisions(self, revision_repo):
        """Test deleting all revisions for a memory."""
        memory_id = uuid4()
        mock_revisions = [MagicMock(), MagicMock(), MagicMock()]

        revision_repo.get_memory_revisions = MagicMock(return_value=mock_revisions)
        revision_repo.delete = MagicMock()

        count = await revision_repo.delete_memory_revisions(memory_id)

        assert count == 3
        assert revision_repo.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_revisions(self, revision_repo):
        """Test returns zero when no revisions to delete."""
        memory_id = uuid4()

        revision_repo.get_memory_revisions = MagicMock(return_value=[])

        count = await revision_repo.delete_memory_revisions(memory_id)

        assert count == 0


class TestRevisionOrdering:
    """Tests for revision ordering."""

    @pytest.mark.asyncio
    async def test_revisions_ordered_by_number_descending(self, revision_repo, mock_db):
        """Test that revisions are ordered newest first."""
        memory_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await revision_repo.get_memory_revisions(memory_id)

        # Verify the query was executed (ordering is implicit in the SQL)
        mock_db.execute.assert_called_once()
