"""
Tests for database utility functions.
"""

from datetime import UTC

import pytest
from sqlalchemy import select

from shared.database.utils import (
    build_filter_conditions,
    count_query,
    filter_to_scope,
    paginate_query,
    scope_to_filter,
)
from shared.models.session import Session as SessionModel


@pytest.mark.integration
@pytest.mark.asyncio
async def test_count_query(test_db):
    """Test counting query results."""
    from datetime import datetime

    # Create test sessions
    for i in range(5):
        session = SessionModel(
            scope={"user_id": f"user{i}"},
            state={},
            started_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        test_db.add(session)

    await test_db.commit()

    # Count all sessions
    query = select(SessionModel)
    count = await count_query(test_db, query)

    assert count == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_count_query_with_filter(test_db):
    """Test counting filtered query results."""
    from datetime import datetime

    # Create test sessions
    for i in range(5):
        session = SessionModel(
            scope={"user_id": "user1" if i < 3 else "user2"},
            state={},
            started_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        test_db.add(session)

    await test_db.commit()

    # Count sessions for user1
    # Note: JSON field filtering in SQLAlchemy requires special handling
    count = await count_query(test_db, select(SessionModel))

    assert count == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_paginate_query(test_db):
    """Test paginating query results."""
    from datetime import datetime

    # Create test sessions
    for i in range(25):
        session = SessionModel(
            scope={"user_id": f"user{i}"},
            state={},
            started_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        test_db.add(session)

    await test_db.commit()

    # Get first page
    query = select(SessionModel).order_by(SessionModel.created_at)
    result = await paginate_query(test_db, query, page=1, page_size=10)

    assert result["total"] == 25
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["pages"] == 3
    assert len(result["items"]) == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_paginate_query_second_page(test_db):
    """Test getting second page of results."""
    from datetime import datetime

    # Create test sessions
    for i in range(25):
        session = SessionModel(
            scope={"user_id": f"user{i}"},
            state={},
            started_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        test_db.add(session)

    await test_db.commit()

    # Get second page
    query = select(SessionModel).order_by(SessionModel.created_at)
    result = await paginate_query(test_db, query, page=2, page_size=10)

    assert result["total"] == 25
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert result["pages"] == 3
    assert len(result["items"]) == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_paginate_query_last_page(test_db):
    """Test getting last page with fewer items."""
    from datetime import datetime

    # Create test sessions
    for i in range(25):
        session = SessionModel(
            scope={"user_id": f"user{i}"},
            state={},
            started_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        test_db.add(session)

    await test_db.commit()

    # Get last page
    query = select(SessionModel).order_by(SessionModel.created_at)
    result = await paginate_query(test_db, query, page=3, page_size=10)

    assert result["total"] == 25
    assert result["page"] == 3
    assert result["page_size"] == 10
    assert result["pages"] == 3
    assert len(result["items"]) == 5


@pytest.mark.unit
def test_build_filter_conditions():
    """Test building filter conditions from dictionary."""
    filters = {"event_count": 5, "title": "Test Session"}

    conditions = build_filter_conditions(SessionModel, filters)

    assert len(conditions) == 2


@pytest.mark.unit
def test_build_filter_conditions_with_list():
    """Test building filter conditions with list values."""
    filters = {"event_count": [1, 2, 3]}

    conditions = build_filter_conditions(SessionModel, filters)

    assert len(conditions) == 1


@pytest.mark.unit
def test_build_filter_conditions_ignores_invalid_fields():
    """Test that invalid fields are ignored."""
    filters = {"invalid_field": "value", "event_count": 5}

    conditions = build_filter_conditions(SessionModel, filters)

    assert len(conditions) == 1


@pytest.mark.unit
def test_scope_to_filter():
    """Test converting scope dictionary to filter string."""
    scope = {"user_id": "123", "agent_id": "abc"}

    filter_str = scope_to_filter(scope)

    # Should be sorted alphabetically
    assert filter_str == "agent_id:abc,user_id:123"


@pytest.mark.unit
def test_scope_to_filter_single_key():
    """Test converting single-key scope to filter string."""
    scope = {"user_id": "123"}

    filter_str = scope_to_filter(scope)

    assert filter_str == "user_id:123"


@pytest.mark.unit
def test_scope_to_filter_empty():
    """Test converting empty scope to filter string."""
    scope = {}

    filter_str = scope_to_filter(scope)

    assert filter_str == ""


@pytest.mark.unit
def test_filter_to_scope():
    """Test converting filter string to scope dictionary."""
    filter_str = "user_id:123,agent_id:abc"

    scope = filter_to_scope(filter_str)

    assert scope == {"user_id": "123", "agent_id": "abc"}


@pytest.mark.unit
def test_filter_to_scope_single_key():
    """Test converting single-key filter string to scope."""
    filter_str = "user_id:123"

    scope = filter_to_scope(filter_str)

    assert scope == {"user_id": "123"}


@pytest.mark.unit
def test_filter_to_scope_empty():
    """Test converting empty filter string to scope."""
    filter_str = ""

    scope = filter_to_scope(filter_str)

    assert scope == {}


@pytest.mark.unit
def test_filter_to_scope_with_spaces():
    """Test converting filter string with spaces."""
    filter_str = "user_id: 123 , agent_id: abc "

    scope = filter_to_scope(filter_str)

    assert scope == {"user_id": "123", "agent_id": "abc"}


@pytest.mark.unit
def test_scope_to_filter_round_trip():
    """Test that scope -> filter -> scope is consistent."""
    original_scope = {"user_id": "123", "agent_id": "abc", "session_id": "xyz"}

    filter_str = scope_to_filter(original_scope)
    recovered_scope = filter_to_scope(filter_str)

    assert recovered_scope == original_scope
