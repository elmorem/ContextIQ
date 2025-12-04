"""
Health check script for ContextIQ infrastructure services.

This script validates connectivity and health of all required services:
- PostgreSQL database
- Redis cache
- RabbitMQ message broker
- Qdrant vector database

Usage:
    python scripts/health_check.py [--verbose]

Options:
    --verbose        Show detailed health check information
"""

import argparse
import asyncio
import logging
import sys
from typing import Any

import asyncpg
from aio_pika import connect_robust
from qdrant_client import QdrantClient
from redis import asyncio as aioredis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Result of a health check."""

    def __init__(self, service: str, healthy: bool, message: str, details: dict | None = None):
        self.service = service
        self.healthy = healthy
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        status = "✓" if self.healthy else "✗"
        return f"[{status}] {self.service}: {self.message}"


async def check_postgres(
    host: str = "localhost",
    port: int = 5432,
    database: str = "contextiq",
    user: str = "contextiq_user",
    password: str = "contextiq_pass",
) -> HealthCheckResult:
    """
    Check PostgreSQL database connectivity.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Database user
        password: Database password

    Returns:
        HealthCheckResult with connection status
    """
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
        version = await conn.fetchval("SELECT version()")
        await conn.close()

        return HealthCheckResult(
            service="PostgreSQL",
            healthy=True,
            message="Connected successfully",
            details={"version": version.split(",")[0]},
        )

    except Exception as e:
        return HealthCheckResult(
            service="PostgreSQL",
            healthy=False,
            message=f"Connection failed: {e}",
        )


async def check_redis(
    host: str = "localhost",
    port: int = 6379,
) -> HealthCheckResult:
    """
    Check Redis cache connectivity.

    Args:
        host: Redis host
        port: Redis port

    Returns:
        HealthCheckResult with connection status
    """
    try:
        redis = await aioredis.from_url(f"redis://{host}:{port}")
        await redis.ping()
        info = await redis.info()
        await redis.aclose()

        return HealthCheckResult(
            service="Redis",
            healthy=True,
            message="Connected successfully",
            details={
                "version": info.get("redis_version", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0),
            },
        )

    except Exception as e:
        return HealthCheckResult(
            service="Redis",
            healthy=False,
            message=f"Connection failed: {e}",
        )


async def check_rabbitmq(
    url: str = "amqp://guest:guest@localhost:5672/",
) -> HealthCheckResult:
    """
    Check RabbitMQ message broker connectivity.

    Args:
        url: RabbitMQ connection URL

    Returns:
        HealthCheckResult with connection status
    """
    try:
        connection = await connect_robust(url)
        channel = await connection.channel()
        await connection.close()

        return HealthCheckResult(
            service="RabbitMQ",
            healthy=True,
            message="Connected successfully",
            details={"url": url.split("@")[-1]},  # Hide credentials
        )

    except Exception as e:
        return HealthCheckResult(
            service="RabbitMQ",
            healthy=False,
            message=f"Connection failed: {e}",
        )


def check_qdrant(
    host: str = "localhost",
    port: int = 6333,
) -> HealthCheckResult:
    """
    Check Qdrant vector database connectivity.

    Args:
        host: Qdrant host
        port: Qdrant port

    Returns:
        HealthCheckResult with connection status
    """
    try:
        client = QdrantClient(host=host, port=port)
        collections = client.get_collections()

        return HealthCheckResult(
            service="Qdrant",
            healthy=True,
            message="Connected successfully",
            details={
                "collections": len(collections.collections),
                "collection_names": [c.name for c in collections.collections],
            },
        )

    except Exception as e:
        return HealthCheckResult(
            service="Qdrant",
            healthy=False,
            message=f"Connection failed: {e}",
        )


async def run_health_checks(verbose: bool = False) -> list[HealthCheckResult]:
    """
    Run health checks for all services.

    Args:
        verbose: If True, show detailed information

    Returns:
        List of HealthCheckResult objects
    """
    logger.info("Running health checks for ContextIQ infrastructure...")

    # Run checks concurrently
    results = await asyncio.gather(
        check_postgres(),
        check_redis(),
        check_rabbitmq(),
        return_exceptions=True,
    )

    # Qdrant check is synchronous
    qdrant_result = check_qdrant()

    # Combine results
    all_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Unexpected error during health check: {result}")
        else:
            all_results.append(result)

    all_results.append(qdrant_result)

    # Print results
    for result in all_results:
        logger.info(str(result))

        if verbose and result.healthy and result.details:
            for key, value in result.details.items():
                logger.info(f"  {key}: {value}")

    return all_results


async def main_async(verbose: bool) -> int:
    """
    Async main entry point.

    Args:
        verbose: If True, show detailed information

    Returns:
        Exit code (0 if all healthy, 1 if any unhealthy)
    """
    results = await run_health_checks(verbose)

    # Check if all services are healthy
    all_healthy = all(r.healthy for r in results)

    if all_healthy:
        logger.info("\n✓ All services are healthy")
        return 0
    else:
        unhealthy = [r.service for r in results if not r.healthy]
        logger.error(f"\n✗ Unhealthy services: {', '.join(unhealthy)}")
        return 1


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 if all healthy, 1 if any unhealthy)
    """
    parser = argparse.ArgumentParser(
        description="Health check for ContextIQ infrastructure services"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed health check information",
    )

    args = parser.parse_args()

    return asyncio.run(main_async(args.verbose))


if __name__ == "__main__":
    sys.exit(main())
