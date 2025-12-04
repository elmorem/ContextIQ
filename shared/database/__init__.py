"""
Database utilities and configuration.
"""

from shared.database.base import Base, TimestampMixin, utc_now
from shared.database.connection import DatabaseConfig, DatabaseConnection
from shared.database.session import (
    close_database,
    get_database_url,
    get_db_connection,
    get_db_session,
    init_database,
)
from shared.database.utils import (
    build_filter_conditions,
    count_query,
    filter_to_scope,
    paginate_query,
    scope_to_filter,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "utc_now",
    # Connection
    "DatabaseConfig",
    "DatabaseConnection",
    # Session
    "init_database",
    "get_database_url",
    "get_db_connection",
    "get_db_session",
    "close_database",
    # Utils
    "count_query",
    "paginate_query",
    "build_filter_conditions",
    "scope_to_filter",
    "filter_to_scope",
]
