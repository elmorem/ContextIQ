"""Tests for database utility functions."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.database.utils import (
    build_filter_conditions,
    count_query,
    filter_to_scope,
    paginate_query,
    scope_to_filter,
)


# Test model for utility functions
class Base(DeclarativeBase):
    """Base for test models."""

    pass


class SampleModel(Base):
    """Sample model for database utilities."""

    __tablename__ = "test_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50))


class TestCountQuery:
    """Test count_query function."""

    @pytest.mark.asyncio
    async def test_count_query_with_results(self):
        """Test counting query results."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        query = select(SampleModel)
        count = await count_query(mock_db, query)

        assert count == 42
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_query_with_no_results(self):
        """Test counting when no results."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        query = select(SampleModel)
        count = await count_query(mock_db, query)

        assert count == 0


class TestPaginateQuery:
    """Test paginate_query function."""

    @pytest.mark.asyncio
    async def test_paginate_query_first_page(self):
        """Test pagination on first page."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        # Mock paginated query
        mock_paginated_result = MagicMock()
        mock_items = [MagicMock() for _ in range(20)]
        mock_paginated_result.scalars.return_value.all.return_value = mock_items

        mock_db.execute.side_effect = [mock_count_result, mock_paginated_result]

        query = select(SampleModel)
        result = await paginate_query(mock_db, query, page=1, page_size=20)

        assert result["items"] == mock_items
        assert result["total"] == 50
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["pages"] == 3  # 50 items / 20 per page = 3 pages

    @pytest.mark.asyncio
    async def test_paginate_query_middle_page(self):
        """Test pagination on middle page."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        mock_paginated_result = MagicMock()
        mock_items = [MagicMock() for _ in range(20)]
        mock_paginated_result.scalars.return_value.all.return_value = mock_items

        mock_db.execute.side_effect = [mock_count_result, mock_paginated_result]

        query = select(SampleModel)
        result = await paginate_query(mock_db, query, page=3, page_size=20)

        assert result["items"] == mock_items
        assert result["total"] == 100
        assert result["page"] == 3
        assert result["page_size"] == 20
        assert result["pages"] == 5

    @pytest.mark.asyncio
    async def test_paginate_query_last_page_partial(self):
        """Test pagination on last page with partial results."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 45

        mock_paginated_result = MagicMock()
        mock_items = [MagicMock() for _ in range(5)]
        mock_paginated_result.scalars.return_value.all.return_value = mock_items

        mock_db.execute.side_effect = [mock_count_result, mock_paginated_result]

        query = select(SampleModel)
        result = await paginate_query(mock_db, query, page=3, page_size=20)

        assert len(result["items"]) == 5
        assert result["total"] == 45
        assert result["pages"] == 3  # 45 / 20 = 2.25 -> ceil = 3

    @pytest.mark.asyncio
    async def test_paginate_query_empty_results(self):
        """Test pagination with no results."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_paginated_result = MagicMock()
        mock_paginated_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_count_result, mock_paginated_result]

        query = select(SampleModel)
        result = await paginate_query(mock_db, query, page=1, page_size=20)

        assert result["items"] == []
        assert result["total"] == 0
        assert result["pages"] == 0


class TestBuildFilterConditions:
    """Test build_filter_conditions function."""

    def test_build_filter_conditions_single_value(self):
        """Test building filter conditions with single values."""
        filters = {"user_id": "123", "status": "active"}
        conditions = build_filter_conditions(SampleModel, filters)

        assert len(conditions) == 2
        # Check that conditions are created (exact comparison is complex with SQLAlchemy)
        assert all(hasattr(c, "compare") for c in conditions)

    def test_build_filter_conditions_list_value(self):
        """Test building filter conditions with list values (IN clause)."""
        filters = {"status": ["active", "pending", "completed"]}
        conditions = build_filter_conditions(SampleModel, filters)

        assert len(conditions) == 1

    def test_build_filter_conditions_tuple_value(self):
        """Test building filter conditions with tuple values (IN clause)."""
        filters = {"category": ("tech", "science", "art")}
        conditions = build_filter_conditions(SampleModel, filters)

        assert len(conditions) == 1

    def test_build_filter_conditions_invalid_field(self):
        """Test that invalid fields are ignored."""
        filters = {"user_id": "123", "invalid_field": "value", "status": "active"}
        conditions = build_filter_conditions(SampleModel, filters)

        # Should only create conditions for valid fields
        assert len(conditions) == 2

    def test_build_filter_conditions_empty(self):
        """Test building filter conditions with empty dict."""
        filters = {}
        conditions = build_filter_conditions(SampleModel, filters)

        assert len(conditions) == 0

    def test_build_filter_conditions_mixed_types(self):
        """Test building filter conditions with mixed value types."""
        filters = {
            "user_id": "123",
            "status": ["active", "pending"],
            "category": "tech",
        }
        conditions = build_filter_conditions(SampleModel, filters)

        assert len(conditions) == 3


class TestScopeToFilter:
    """Test scope_to_filter function."""

    def test_scope_to_filter_single_item(self):
        """Test converting single-item scope to filter."""
        scope = {"user_id": "123"}
        filter_str = scope_to_filter(scope)

        assert filter_str == "user_id:123"

    def test_scope_to_filter_multiple_items(self):
        """Test converting multi-item scope to filter."""
        scope = {"user_id": "123", "agent_id": "abc"}
        filter_str = scope_to_filter(scope)

        # Should be sorted alphabetically
        assert filter_str == "agent_id:abc,user_id:123"

    def test_scope_to_filter_empty(self):
        """Test converting empty scope."""
        scope = {}
        filter_str = scope_to_filter(scope)

        assert filter_str == ""

    def test_scope_to_filter_maintains_order(self):
        """Test that scope_to_filter maintains consistent ordering."""
        scope1 = {"user_id": "123", "agent_id": "abc", "session_id": "xyz"}
        scope2 = {"session_id": "xyz", "user_id": "123", "agent_id": "abc"}

        filter_str1 = scope_to_filter(scope1)
        filter_str2 = scope_to_filter(scope2)

        assert filter_str1 == filter_str2


class TestFilterToScope:
    """Test filter_to_scope function."""

    def test_filter_to_scope_single_item(self):
        """Test converting single-item filter to scope."""
        filter_str = "user_id:123"
        scope = filter_to_scope(filter_str)

        assert scope == {"user_id": "123"}

    def test_filter_to_scope_multiple_items(self):
        """Test converting multi-item filter to scope."""
        filter_str = "user_id:123,agent_id:abc,session_id:xyz"
        scope = filter_to_scope(filter_str)

        assert scope == {"user_id": "123", "agent_id": "abc", "session_id": "xyz"}

    def test_filter_to_scope_empty(self):
        """Test converting empty filter."""
        filter_str = ""
        scope = filter_to_scope(filter_str)

        assert scope == {}

    def test_filter_to_scope_with_whitespace(self):
        """Test converting filter with whitespace."""
        filter_str = "user_id: 123 , agent_id : abc "
        scope = filter_to_scope(filter_str)

        assert scope == {"user_id": "123", "agent_id": "abc"}

    def test_filter_to_scope_with_colon_in_value(self):
        """Test converting filter where value contains colon."""
        filter_str = "url:https://example.com"
        scope = filter_to_scope(filter_str)

        assert scope == {"url": "https://example.com"}

    def test_filter_to_scope_invalid_format(self):
        """Test converting filter with invalid format (no colon)."""
        filter_str = "invalid,user_id:123"
        scope = filter_to_scope(filter_str)

        # Should skip invalid pairs
        assert scope == {"user_id": "123"}


class TestScopeFilterRoundTrip:
    """Test round-trip conversion between scope and filter."""

    def test_scope_filter_roundtrip(self):
        """Test that scope -> filter -> scope maintains data."""
        original_scope = {"user_id": "123", "agent_id": "abc", "session_id": "xyz"}

        filter_str = scope_to_filter(original_scope)
        result_scope = filter_to_scope(filter_str)

        assert result_scope == original_scope

    def test_filter_scope_roundtrip(self):
        """Test that filter -> scope -> filter maintains data."""
        original_filter = "agent_id:abc,session_id:xyz,user_id:123"

        scope = filter_to_scope(original_filter)
        result_filter = scope_to_filter(scope)

        assert result_filter == original_filter
