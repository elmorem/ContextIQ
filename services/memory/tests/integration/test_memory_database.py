"""
Integration tests for Memory database operations.

These tests require a running PostgreSQL database with pgvector extension.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.memory.app.db.repositories.memory_repository import MemoryRepository

# Skip all tests if database is not available
pytestmark = pytest.mark.integration


@pytest.fixture
async def db_session():
    """Provide database session for tests."""
    # Create engine for PostgreSQL
    engine = create_async_engine(
        "postgresql+asyncpg://contextiq_user:contextiq_pass@localhost:5432/contextiq",
        echo=False,
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
def memory_repository(db_session):
    """Provide memory repository for tests."""
    return MemoryRepository(db_session)


class TestMemoryCRUD:
    """Tests for basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_memory(self, memory_repository, db_session):
        """Test creating and retrieving a memory."""
        scope = {"user_id": "test_user", "org_id": "test_org"}
        fact = "User prefers dark mode for coding"

        # Create memory
        memory = await memory_repository.create_memory(
            scope=scope,
            fact=fact,
            source_type="conversation",
            topic="preferences",
            confidence=0.9,
            importance=0.7,
        )
        await db_session.commit()

        # Retrieve memory
        retrieved = await memory_repository.get_by_id(memory.id)

        assert retrieved is not None
        assert retrieved.id == memory.id
        assert retrieved.scope == scope
        assert retrieved.fact == fact
        assert retrieved.topic == "preferences"
        assert retrieved.confidence == 0.9
        assert retrieved.importance == 0.7

    @pytest.mark.asyncio
    async def test_create_memory_with_embedding(self, memory_repository, db_session):
        """Test creating a memory with vector embedding."""
        scope = {"user_id": "test_user"}
        fact = "User knows Python and TypeScript"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        memory = await memory_repository.create_memory(
            scope=scope,
            fact=fact,
            source_type="extraction",
            topic="skills",
            embedding=embedding,
        )
        await db_session.commit()

        retrieved = await memory_repository.get_by_id(memory.id)

        assert retrieved is not None
        assert retrieved.embedding == embedding


class TestScopeFiltering:
    """Tests for scope-based filtering."""

    @pytest.mark.asyncio
    async def test_get_memories_by_scope(self, memory_repository, db_session):
        """Test retrieving memories by scope."""
        scope1 = {"user_id": "user_123"}
        scope2 = {"user_id": "user_456"}

        # Create memories for different scopes
        await memory_repository.create_memory(
            scope=scope1,
            fact="User 123 fact 1",
            source_type="conversation",
        )
        await memory_repository.create_memory(
            scope=scope1,
            fact="User 123 fact 2",
            source_type="conversation",
        )
        await memory_repository.create_memory(
            scope=scope2,
            fact="User 456 fact",
            source_type="conversation",
        )
        await db_session.commit()

        # Retrieve memories for scope1
        memories = await memory_repository.get_by_scope(scope1)

        assert len(memories) >= 2
        for memory in memories:
            assert memory.scope == scope1

    @pytest.mark.asyncio
    async def test_get_memories_by_topic(self, memory_repository, db_session):
        """Test retrieving memories by topic."""
        scope = {"user_id": "test_user"}

        # Create memories with different topics
        await memory_repository.create_memory(
            scope=scope,
            fact="Likes Python",
            source_type="conversation",
            topic="skills",
        )
        await memory_repository.create_memory(
            scope=scope,
            fact="Lives in SF",
            source_type="conversation",
            topic="location",
        )
        await db_session.commit()

        # Retrieve memories by topic
        skills_memories = await memory_repository.get_by_topic(scope, "skills")

        assert len(skills_memories) >= 1
        for memory in skills_memories:
            assert memory.topic == "skills"


class TestAccessTracking:
    """Tests for access tracking."""

    @pytest.mark.asyncio
    async def test_update_access_increments_count(self, memory_repository, db_session):
        """Test that updating access increments the count."""
        scope = {"user_id": "test_user"}
        memory = await memory_repository.create_memory(
            scope=scope,
            fact="Test fact",
            source_type="manual",
        )
        await db_session.commit()

        initial_count = memory.access_count

        # Update access
        updated = await memory_repository.update_access(memory.id)
        await db_session.commit()

        assert updated is not None
        assert updated.access_count == initial_count + 1
        assert updated.last_accessed_at is not None

    @pytest.mark.asyncio
    async def test_update_access_multiple_times(self, memory_repository, db_session):
        """Test multiple access updates."""
        scope = {"user_id": "test_user"}
        memory = await memory_repository.create_memory(
            scope=scope,
            fact="Popular fact",
            source_type="manual",
        )
        await db_session.commit()

        # Update access 3 times
        for _ in range(3):
            await memory_repository.update_access(memory.id)
            await db_session.commit()

        retrieved = await memory_repository.get_by_id(memory.id)
        assert retrieved.access_count == 3


class TestSoftDelete:
    """Tests for soft delete functionality."""

    @pytest.mark.asyncio
    async def test_soft_delete_memory(self, memory_repository, db_session):
        """Test soft-deleting a memory."""
        scope = {"user_id": "test_user"}
        memory = await memory_repository.create_memory(
            scope=scope,
            fact="To be deleted",
            source_type="manual",
        )
        await db_session.commit()

        # Soft delete
        deleted = await memory_repository.soft_delete(memory.id)
        await db_session.commit()

        assert deleted is not None
        assert deleted.deleted_at is not None

        # Verify it's excluded from normal queries
        memories = await memory_repository.get_by_scope(scope)
        memory_ids = [m.id for m in memories]
        assert memory.id not in memory_ids

    @pytest.mark.asyncio
    async def test_restore_soft_deleted_memory(self, memory_repository, db_session):
        """Test restoring a soft-deleted memory."""
        scope = {"user_id": "test_user"}
        memory = await memory_repository.create_memory(
            scope=scope,
            fact="To be restored",
            source_type="manual",
        )
        await db_session.commit()

        # Soft delete
        await memory_repository.soft_delete(memory.id)
        await db_session.commit()

        # Restore
        restored = await memory_repository.restore(memory.id)
        await db_session.commit()

        assert restored is not None
        assert restored.deleted_at is None

        # Verify it's included in normal queries
        memories = await memory_repository.get_by_scope(scope)
        memory_ids = [m.id for m in memories]
        assert memory.id in memory_ids


class TestExpiration:
    """Tests for memory expiration."""

    @pytest.mark.asyncio
    async def test_get_expired_memories(self, memory_repository, db_session):
        """Test retrieving expired memories."""
        scope = {"user_id": "test_user"}

        # Create expired memory
        past = datetime.now(UTC) - timedelta(days=1)
        await memory_repository.create_memory(
            scope=scope,
            fact="Expired memory",
            source_type="conversation",
            expires_at=past,
        )

        # Create non-expired memory
        future = datetime.now(UTC) + timedelta(days=30)
        await memory_repository.create_memory(
            scope=scope,
            fact="Valid memory",
            source_type="conversation",
            expires_at=future,
        )
        await db_session.commit()

        # Get expired memories
        expired = await memory_repository.get_expired_memories()

        assert len(expired) >= 1
        for memory in expired:
            assert memory.expires_at <= datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_delete_expired_memories(self, memory_repository, db_session):
        """Test soft-deleting expired memories."""
        scope = {"user_id": "test_user"}

        # Create expired memory
        past = datetime.now(UTC) - timedelta(days=1)
        memory = await memory_repository.create_memory(
            scope=scope,
            fact="Old memory",
            source_type="conversation",
            expires_at=past,
        )
        await db_session.commit()

        # Delete expired memories
        count = await memory_repository.delete_expired_memories()
        await db_session.commit()

        assert count >= 1

        # Verify it was soft-deleted
        retrieved = await memory_repository.get_by_id(memory.id)
        assert retrieved.deleted_at is not None


class TestListAndCount:
    """Tests for list and count operations."""

    @pytest.mark.asyncio
    async def test_list_memories_with_pagination(self, memory_repository, db_session):
        """Test listing memories with pagination."""
        scope = {"user_id": "test_user"}

        # Create multiple memories
        for i in range(5):
            await memory_repository.create_memory(
                scope=scope,
                fact=f"Memory {i}",
                source_type="conversation",
            )
        await db_session.commit()

        # List with limit
        memories = await memory_repository.list_memories(scope=scope, limit=3)

        assert len(memories) <= 3

    @pytest.mark.asyncio
    async def test_count_memories(self, memory_repository, db_session):
        """Test counting memories."""
        scope = {"user_id": "test_user"}

        # Create memories
        for i in range(3):
            await memory_repository.create_memory(
                scope=scope,
                fact=f"Memory {i}",
                source_type="conversation",
                topic="test",
            )
        await db_session.commit()

        # Count all for scope
        total_count = await memory_repository.count_memories(scope=scope)
        assert total_count >= 3

        # Count by topic
        topic_count = await memory_repository.count_memories(scope=scope, topic="test")
        assert topic_count >= 3

    @pytest.mark.asyncio
    async def test_list_excludes_deleted(self, memory_repository, db_session):
        """Test that list excludes soft-deleted memories by default."""
        scope = {"user_id": "test_user"}

        # Create and delete a memory
        memory = await memory_repository.create_memory(
            scope=scope,
            fact="Deleted memory",
            source_type="manual",
        )
        await db_session.commit()

        await memory_repository.soft_delete(memory.id)
        await db_session.commit()

        # List should exclude deleted
        memories = await memory_repository.list_memories(scope=scope)
        memory_ids = [m.id for m in memories]
        assert memory.id not in memory_ids

        # List with include_deleted should include it
        memories_with_deleted = await memory_repository.list_memories(
            scope=scope,
            include_deleted=True,
        )
        memory_ids_with_deleted = [m.id for m in memories_with_deleted]
        assert memory.id in memory_ids_with_deleted
