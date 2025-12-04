"""
Integration tests for health check script.

These tests require all infrastructure services to be running.
"""

import pytest

from scripts.health_check import (
    HealthCheckResult,
    check_postgres,
    check_qdrant,
    check_rabbitmq,
    check_redis,
    run_health_checks,
)

# Skip all tests if services are not available
pytestmark = pytest.mark.integration


class TestHealthCheckResult:
    """Tests for HealthCheckResult."""

    def test_create_healthy_result(self):
        """Test creating a healthy result."""
        result = HealthCheckResult(
            service="TestService",
            healthy=True,
            message="All good",
        )

        assert result.service == "TestService"
        assert result.healthy is True
        assert result.message == "All good"
        assert result.details == {}

    def test_create_unhealthy_result(self):
        """Test creating an unhealthy result."""
        result = HealthCheckResult(
            service="TestService",
            healthy=False,
            message="Connection failed",
        )

        assert result.service == "TestService"
        assert result.healthy is False
        assert result.message == "Connection failed"

    def test_result_with_details(self):
        """Test creating result with details."""
        details = {"version": "1.0", "uptime": 100}
        result = HealthCheckResult(
            service="TestService",
            healthy=True,
            message="OK",
            details=details,
        )

        assert result.details == details

    def test_string_representation_healthy(self):
        """Test string representation of healthy result."""
        result = HealthCheckResult(
            service="TestService",
            healthy=True,
            message="OK",
        )

        assert "✓" in str(result)
        assert "TestService" in str(result)
        assert "OK" in str(result)

    def test_string_representation_unhealthy(self):
        """Test string representation of unhealthy result."""
        result = HealthCheckResult(
            service="TestService",
            healthy=False,
            message="Failed",
        )

        assert "✗" in str(result)
        assert "TestService" in str(result)
        assert "Failed" in str(result)


class TestCheckPostgres:
    """Tests for check_postgres."""

    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """Test successful PostgreSQL connection."""
        result = await check_postgres()

        # Should be healthy if PostgreSQL is running
        # If not running, will be unhealthy but shouldn't raise
        assert isinstance(result, HealthCheckResult)
        assert result.service == "PostgreSQL"

        if result.healthy:
            assert "Connected successfully" in result.message
            assert "version" in result.details

    @pytest.mark.asyncio
    async def test_failed_connection(self):
        """Test failed PostgreSQL connection."""
        result = await check_postgres(host="invalid-host")

        assert isinstance(result, HealthCheckResult)
        assert result.service == "PostgreSQL"
        assert result.healthy is False
        assert "Connection failed" in result.message


class TestCheckRedis:
    """Tests for check_redis."""

    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """Test successful Redis connection."""
        result = await check_redis()

        assert isinstance(result, HealthCheckResult)
        assert result.service == "Redis"

        if result.healthy:
            assert "Connected successfully" in result.message
            assert "version" in result.details
            assert "uptime_days" in result.details

    @pytest.mark.asyncio
    async def test_failed_connection(self):
        """Test failed Redis connection."""
        result = await check_redis(host="invalid-host")

        assert isinstance(result, HealthCheckResult)
        assert result.service == "Redis"
        assert result.healthy is False
        assert "Connection failed" in result.message


class TestCheckRabbitMQ:
    """Tests for check_rabbitmq."""

    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """Test successful RabbitMQ connection."""
        result = await check_rabbitmq()

        assert isinstance(result, HealthCheckResult)
        assert result.service == "RabbitMQ"

        if result.healthy:
            assert "Connected successfully" in result.message
            assert "url" in result.details

    @pytest.mark.asyncio
    async def test_failed_connection(self):
        """Test failed RabbitMQ connection."""
        result = await check_rabbitmq(url="amqp://invalid:invalid@invalid-host:5672/")

        assert isinstance(result, HealthCheckResult)
        assert result.service == "RabbitMQ"
        assert result.healthy is False
        assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_hides_credentials_in_details(self):
        """Test that credentials are hidden in details."""
        result = await check_rabbitmq(url="amqp://guest:guest@localhost:5672/")

        if result.healthy:
            # URL should not contain credentials
            assert "guest:guest" not in result.details.get("url", "")
            assert "localhost:5672" in result.details.get("url", "")


class TestCheckQdrant:
    """Tests for check_qdrant."""

    def test_successful_connection(self):
        """Test successful Qdrant connection."""
        result = check_qdrant()

        assert isinstance(result, HealthCheckResult)
        assert result.service == "Qdrant"

        if result.healthy:
            assert "Connected successfully" in result.message
            assert "collections" in result.details
            assert "collection_names" in result.details

    def test_failed_connection(self):
        """Test failed Qdrant connection."""
        result = check_qdrant(host="invalid-host")

        assert isinstance(result, HealthCheckResult)
        assert result.service == "Qdrant"
        assert result.healthy is False
        assert "Connection failed" in result.message


class TestRunHealthChecks:
    """Tests for run_health_checks."""

    @pytest.mark.asyncio
    async def test_checks_all_services(self):
        """Test runs checks for all services."""
        results = await run_health_checks(verbose=False)

        assert len(results) == 4  # PostgreSQL, Redis, RabbitMQ, Qdrant

        services = {r.service for r in results}
        assert "PostgreSQL" in services
        assert "Redis" in services
        assert "RabbitMQ" in services
        assert "Qdrant" in services

    @pytest.mark.asyncio
    async def test_returns_health_check_results(self):
        """Test returns HealthCheckResult objects."""
        results = await run_health_checks(verbose=False)

        for result in results:
            assert isinstance(result, HealthCheckResult)
            assert hasattr(result, "service")
            assert hasattr(result, "healthy")
            assert hasattr(result, "message")
            assert hasattr(result, "details")

    @pytest.mark.asyncio
    async def test_verbose_mode(self):
        """Test verbose mode (should not raise errors)."""
        results = await run_health_checks(verbose=True)

        # Should still return results even in verbose mode
        assert len(results) > 0
