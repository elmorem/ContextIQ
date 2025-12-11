"""
Prometheus metrics configuration and utilities.

Provides standardized metrics for HTTP requests, database operations,
and custom business metrics across all services.
"""

from prometheus_client import REGISTRY as DEFAULT_REGISTRY
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# HTTP Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["service", "method", "endpoint"],
)


# Database Metrics
db_operations_total = Counter(
    "db_operations_total",
    "Total database operations",
    ["service", "operation", "table", "status"],
)

db_operation_duration_seconds = Histogram(
    "db_operation_duration_seconds",
    "Database operation latency",
    ["service", "operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    ["service"],
)


# Message Queue Metrics
mq_messages_published_total = Counter(
    "mq_messages_published_total",
    "Total messages published",
    ["service", "queue", "status"],
)

mq_messages_consumed_total = Counter(
    "mq_messages_consumed_total",
    "Total messages consumed",
    ["service", "queue", "status"],
)

mq_message_processing_duration_seconds = Histogram(
    "mq_message_processing_duration_seconds",
    "Message processing latency",
    ["service", "queue"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)


# Cache Metrics
cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["service", "operation", "status"],
)

cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate (0-1)",
    ["service"],
)


# Business Metrics
memories_created_total = Counter(
    "memories_created_total",
    "Total memories created",
    ["service", "source_type"],
)

memories_retrieved_total = Counter(
    "memories_retrieved_total",
    "Total memories retrieved",
    ["service", "query_type"],
)

sessions_created_total = Counter(
    "sessions_created_total",
    "Total sessions created",
    ["service"],
)

events_added_total = Counter(
    "events_added_total",
    "Total events added to sessions",
    ["service", "event_type"],
)


def get_metrics() -> bytes:
    """
    Get current metrics in Prometheus format.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(DEFAULT_REGISTRY)
