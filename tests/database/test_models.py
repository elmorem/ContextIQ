"""
Tests for database models.
"""

import uuid
from datetime import UTC, datetime

import pytest

from shared.models.extraction import ConsolidationJob, ExtractionJob
from shared.models.memory import (
    Memory,
    MemoryRevision,
    ProceduralMemory,
    ProceduralMemoryExecution,
)
from shared.models.session import Event, Session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_session(test_db):
    """Test creating a session."""
    session = Session(
        scope={"user_id": "123"},
        state={"key": "value"},
        started_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
    )

    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    assert session.id is not None
    assert session.scope == {"user_id": "123"}
    assert session.state == {"key": "value"}
    assert session.event_count == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_event(test_db):
    """Test creating an event."""
    # Create session first
    session = Session(
        scope={"user_id": "123"},
        state={},
        started_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
    )
    test_db.add(session)
    await test_db.commit()

    # Create event
    event = Event(
        session_id=session.id,
        event_type="user_message",
        data={"content": "Hello"},
        timestamp=datetime.now(UTC),
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    assert event.id is not None
    assert event.session_id == session.id
    assert event.event_type == "user_message"
    assert event.data == {"content": "Hello"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_event_relationship(test_db):
    """Test session-event relationship."""
    # Create session
    session = Session(
        scope={"user_id": "123"},
        state={},
        started_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
    )
    test_db.add(session)
    await test_db.commit()

    # Create events
    for i in range(3):
        event = Event(
            session_id=session.id,
            event_type="message",
            data={"index": i},
            timestamp=datetime.now(UTC),
        )
        test_db.add(event)

    await test_db.commit()
    await test_db.refresh(session)

    # Verify relationship (note: we need to manually query in async context)
    from sqlalchemy import select

    result = await test_db.execute(select(Event).where(Event.session_id == session.id))
    events = result.scalars().all()

    assert len(events) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_memory(test_db):
    """Test creating a memory."""
    memory = Memory(
        scope={"user_id": "123"},
        fact="User prefers dark mode",
        topic="preferences",
        source_type="direct",
    )

    test_db.add(memory)
    await test_db.commit()
    await test_db.refresh(memory)

    assert memory.id is not None
    assert memory.scope == {"user_id": "123"}
    assert memory.fact == "User prefers dark mode"
    assert memory.confidence == 1.0
    assert memory.importance == 0.5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_memory_revision(test_db):
    """Test creating a memory revision."""
    # Create memory first
    memory = Memory(
        scope={"user_id": "123"},
        fact="User prefers dark mode",
        source_type="direct",
    )
    test_db.add(memory)
    await test_db.commit()

    # Create revision
    revision = MemoryRevision(
        memory_id=memory.id,
        revision_number=1,
        previous_fact="User prefers dark mode",
        new_fact="User prefers light mode",
        change_reason="User preference changed",
    )
    test_db.add(revision)
    await test_db.commit()
    await test_db.refresh(revision)

    assert revision.id is not None
    assert revision.memory_id == memory.id
    assert revision.revision_number == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_procedural_memory(test_db):
    """Test creating a procedural memory."""
    proc_memory = ProceduralMemory(
        scope={"agent_id": "abc"},
        memory_type="workflow",
        name="Data Processing Pipeline",
        description="Pipeline for processing user data",
        content={
            "steps": [
                {"name": "validate", "action": "validate_input"},
                {"name": "process", "action": "process_data"},
                {"name": "store", "action": "store_results"},
            ]
        },
    )

    test_db.add(proc_memory)
    await test_db.commit()
    await test_db.refresh(proc_memory)

    assert proc_memory.id is not None
    assert proc_memory.memory_type == "workflow"
    assert proc_memory.name == "Data Processing Pipeline"
    assert len(proc_memory.content["steps"]) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_procedural_memory_execution(test_db):
    """Test creating a procedural memory execution."""
    # Create procedural memory first
    proc_memory = ProceduralMemory(
        scope={"agent_id": "abc"},
        memory_type="workflow",
        name="Test Workflow",
        content={"steps": []},
    )
    test_db.add(proc_memory)
    await test_db.commit()

    # Create execution
    execution = ProceduralMemoryExecution(
        procedural_memory_id=proc_memory.id,
        success=True,
        execution_time=1.5,
        input_data={"key": "value"},
        output_data={"result": "success"},
        executed_at=datetime.now(UTC),
    )
    test_db.add(execution)
    await test_db.commit()
    await test_db.refresh(execution)

    assert execution.id is not None
    assert execution.procedural_memory_id == proc_memory.id
    assert execution.success is True
    assert execution.execution_time == 1.5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_extraction_job(test_db):
    """Test creating an extraction job."""
    session_id = uuid.uuid4()

    job = ExtractionJob(
        session_id=session_id,
        scope={"user_id": "123"},
        status="pending",
        input_events=[{"type": "message", "content": "Hello"}],
    )

    test_db.add(job)
    await test_db.commit()
    await test_db.refresh(job)

    assert job.id is not None
    assert job.session_id == session_id
    assert job.status == "pending"
    assert len(job.input_events) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_consolidation_job(test_db):
    """Test creating a consolidation job."""
    memory_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

    job = ConsolidationJob(
        scope={"user_id": "123"},
        status="pending",
        input_memory_ids=[str(mid) for mid in memory_ids],
    )

    test_db.add(job)
    await test_db.commit()
    await test_db.refresh(job)

    assert job.id is not None
    assert job.status == "pending"
    assert len(job.input_memory_ids) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_soft_delete(test_db):
    """Test soft deleting a memory."""
    memory = Memory(scope={"user_id": "123"}, fact="Test fact", source_type="direct")

    test_db.add(memory)
    await test_db.commit()

    # Soft delete
    memory.deleted_at = datetime.now(UTC)
    await test_db.commit()
    await test_db.refresh(memory)

    assert memory.deleted_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_with_embedding(test_db):
    """Test creating memory with embedding vector."""
    embedding = [0.1] * 1536  # OpenAI embedding dimension

    memory = Memory(
        scope={"user_id": "123"},
        fact="Test fact",
        source_type="direct",
        embedding=embedding,
    )

    test_db.add(memory)
    await test_db.commit()
    await test_db.refresh(memory)

    assert memory.embedding is not None
    assert len(memory.embedding) == 1536
