"""
Database utility functions.
"""

from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

T = TypeVar("T")


async def count_query(db: AsyncSession, query: Select) -> int:
    """
    Count the number of results from a query.

    Args:
        db: Database session
        query: SQLAlchemy select query

    Returns:
        Number of matching records
    """
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    return result.scalar() or 0


async def paginate_query(
    db: AsyncSession,
    query: Select[tuple[T]],
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    Paginate a query and return results with metadata.

    Args:
        db: Database session
        query: SQLAlchemy select query
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Dictionary with 'items', 'total', 'page', 'page_size', 'pages'
    """
    # Get total count
    total = await count_query(db, query)

    # Calculate pagination
    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size  # Ceiling division

    # Get paginated results
    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


def build_filter_conditions(
    model: type,
    filters: dict[str, Any],
) -> list[Any]:
    """
    Build SQLAlchemy filter conditions from a dictionary.

    Args:
        model: SQLAlchemy model class
        filters: Dictionary of field names to values

    Returns:
        List of SQLAlchemy filter conditions

    Example:
        ```python
        filters = {"user_id": "123", "status": "active"}
        conditions = build_filter_conditions(Memory, filters)
        query = select(Memory).where(*conditions)
        ```
    """
    conditions = []
    for field, value in filters.items():
        if hasattr(model, field):
            column = getattr(model, field)
            if isinstance(column, InstrumentedAttribute):
                if isinstance(value, list | tuple):
                    conditions.append(column.in_(value))
                else:
                    conditions.append(column == value)
    return conditions


def scope_to_filter(scope: dict[str, str]) -> str:
    """
    Convert scope dictionary to filter string for queries.

    Args:
        scope: Scope dictionary (e.g., {"user_id": "123", "agent_id": "abc"})

    Returns:
        Filter string in format "key1:value1,key2:value2"

    Example:
        ```python
        scope = {"user_id": "123", "agent_id": "abc"}
        filter_str = scope_to_filter(scope)  # "agent_id:abc,user_id:123"
        ```
    """
    sorted_items = sorted(scope.items())
    return ",".join(f"{k}:{v}" for k, v in sorted_items)


def filter_to_scope(filter_str: str) -> dict[str, str]:
    """
    Convert filter string to scope dictionary.

    Args:
        filter_str: Filter string in format "key1:value1,key2:value2"

    Returns:
        Scope dictionary

    Example:
        ```python
        filter_str = "user_id:123,agent_id:abc"
        scope = filter_to_scope(filter_str)  # {"user_id": "123", "agent_id": "abc"}
        ```
    """
    if not filter_str:
        return {}

    scope = {}
    for pair in filter_str.split(","):
        if ":" in pair:
            key, value = pair.split(":", 1)
            scope[key.strip()] = value.strip()
    return scope
