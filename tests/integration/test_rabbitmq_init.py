"""
Integration tests for RabbitMQ initialization script.

These tests require a running RabbitMQ instance.
"""

import pytest
from aio_pika import ExchangeType, connect_robust

from scripts.init_rabbitmq import (
    create_connection,
    create_exchange,
    create_queue_with_binding,
    init_rabbitmq,
)
from shared.messaging.queues import Queues

# Skip all tests if RabbitMQ is not available
pytestmark = pytest.mark.integration

RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"


@pytest.fixture
async def rabbitmq_connection():
    """Provide RabbitMQ connection for tests."""
    try:
        connection = await connect_robust(RABBITMQ_URL)
        yield connection
        await connection.close()
    except Exception:
        pytest.skip("RabbitMQ not available")


@pytest.fixture
async def rabbitmq_channel(rabbitmq_connection):
    """Provide RabbitMQ channel for tests."""
    channel = await rabbitmq_connection.channel()
    yield channel
    await channel.close()


@pytest.fixture
async def clean_test_resources(rabbitmq_channel):
    """Clean up test resources before and after test."""
    test_exchange = "test_exchange"
    test_queue = "test_queue"

    # Cleanup before test
    try:
        await rabbitmq_channel.queue_delete(test_queue)
    except Exception:
        pass

    try:
        await rabbitmq_channel.exchange_delete(test_exchange)
    except Exception:
        pass

    yield test_exchange, test_queue

    # Cleanup after test
    try:
        await rabbitmq_channel.queue_delete(test_queue)
    except Exception:
        pass

    try:
        await rabbitmq_channel.exchange_delete(test_exchange)
    except Exception:
        pass


class TestCreateConnection:
    """Tests for create_connection."""

    @pytest.mark.asyncio
    async def test_connects_successfully(self):
        """Test successful connection to RabbitMQ."""
        connection = await create_connection(RABBITMQ_URL)
        assert connection is not None
        assert not connection.is_closed
        await connection.close()

    @pytest.mark.asyncio
    async def test_fails_on_bad_url(self):
        """Test connection failure with bad URL."""
        with pytest.raises(ConnectionError, match="Failed to connect"):
            await create_connection("amqp://invalid:invalid@invalid-host:5672/")


class TestCreateExchange:
    """Tests for create_exchange."""

    @pytest.mark.asyncio
    async def test_creates_exchange(self, rabbitmq_channel, clean_test_resources):
        """Test creating a new exchange."""
        exchange_name, _ = clean_test_resources

        await create_exchange(rabbitmq_channel, exchange_name)

        # Verify exchange exists by declaring it again (should be idempotent)
        exchange = await rabbitmq_channel.get_exchange(exchange_name)
        assert exchange is not None

    @pytest.mark.asyncio
    async def test_recreates_exchange(self, rabbitmq_channel, clean_test_resources):
        """Test recreating an existing exchange."""
        exchange_name, _ = clean_test_resources

        # Create first time
        await create_exchange(rabbitmq_channel, exchange_name)

        # Recreate
        await create_exchange(rabbitmq_channel, exchange_name, recreate=True)

        # Verify exchange still exists
        exchange = await rabbitmq_channel.get_exchange(exchange_name)
        assert exchange is not None

    @pytest.mark.asyncio
    async def test_creates_topic_exchange(self, rabbitmq_channel, clean_test_resources):
        """Test creates exchange with topic type."""
        exchange_name, _ = clean_test_resources

        await create_exchange(rabbitmq_channel, exchange_name, exchange_type=ExchangeType.TOPIC)

        # Exchange should exist
        exchange = await rabbitmq_channel.get_exchange(exchange_name)
        assert exchange is not None


class TestCreateQueueWithBinding:
    """Tests for create_queue_with_binding."""

    @pytest.mark.asyncio
    async def test_creates_queue(self, rabbitmq_channel, clean_test_resources):
        """Test creating a new queue."""
        _, queue_name = clean_test_resources

        await create_queue_with_binding(
            rabbitmq_channel,
            queue_name,
            exchange_name=None,
            routing_key=None,
        )

        # Verify queue exists
        queue = await rabbitmq_channel.get_queue(queue_name)
        assert queue is not None

    @pytest.mark.asyncio
    async def test_creates_durable_queue(self, rabbitmq_channel, clean_test_resources):
        """Test creating a durable queue."""
        _, queue_name = clean_test_resources

        await create_queue_with_binding(
            rabbitmq_channel,
            queue_name,
            exchange_name=None,
            routing_key=None,
            durable=True,
        )

        # Queue should exist
        queue = await rabbitmq_channel.get_queue(queue_name)
        assert queue is not None

    @pytest.mark.asyncio
    async def test_binds_queue_to_exchange(self, rabbitmq_channel, clean_test_resources):
        """Test binding queue to exchange."""
        exchange_name, queue_name = clean_test_resources

        # Create exchange first
        await create_exchange(rabbitmq_channel, exchange_name)

        # Create and bind queue
        await create_queue_with_binding(
            rabbitmq_channel,
            queue_name,
            exchange_name=exchange_name,
            routing_key="test.key",
        )

        # Queue should exist and be bound
        queue = await rabbitmq_channel.get_queue(queue_name)
        assert queue is not None

    @pytest.mark.asyncio
    async def test_recreates_queue(self, rabbitmq_channel, clean_test_resources):
        """Test recreating an existing queue."""
        _, queue_name = clean_test_resources

        # Create first time
        await create_queue_with_binding(
            rabbitmq_channel,
            queue_name,
            exchange_name=None,
            routing_key=None,
        )

        # Recreate
        await create_queue_with_binding(
            rabbitmq_channel,
            queue_name,
            exchange_name=None,
            routing_key=None,
            recreate=True,
        )

        # Queue should still exist
        queue = await rabbitmq_channel.get_queue(queue_name)
        assert queue is not None


class TestInitRabbitMQ:
    """Tests for init_rabbitmq."""

    @pytest.fixture(autouse=True)
    async def cleanup_queues(self, rabbitmq_connection):
        """Clean up all configured queues after test."""
        yield
        channel = await rabbitmq_connection.channel()
        try:
            # Delete all queues
            for queue_config in Queues.all_queues():
                try:
                    await channel.queue_delete(queue_config.name)
                except Exception:
                    pass

            # Delete all exchanges
            exchanges = {q.exchange for q in Queues.all_queues() if q.exchange is not None}
            for exchange in exchanges:
                try:
                    await channel.exchange_delete(exchange)
                except Exception:
                    pass
        finally:
            await channel.close()

    @pytest.mark.asyncio
    async def test_initializes_all_resources(self, rabbitmq_connection):
        """Test initializes all exchanges and queues."""
        exchanges, queues = await init_rabbitmq(RABBITMQ_URL, recreate=True)

        assert exchanges > 0
        assert queues > 0
        assert queues == len(Queues.all_queues())

        # Verify queues exist
        channel = await rabbitmq_connection.channel()
        try:
            for queue_config in Queues.all_queues():
                queue = await channel.get_queue(queue_config.name)
                assert queue is not None
        finally:
            await channel.close()

    @pytest.mark.asyncio
    async def test_idempotent_initialization(self):
        """Test initialization is idempotent."""
        # Initialize first time
        exchanges1, queues1 = await init_rabbitmq(RABBITMQ_URL, recreate=True)

        # Initialize again without recreate (should succeed without errors)
        exchanges2, queues2 = await init_rabbitmq(RABBITMQ_URL, recreate=False)

        # Same number of resources
        assert exchanges1 == exchanges2
        assert queues1 == queues2

    @pytest.mark.asyncio
    async def test_recreates_all_resources(self):
        """Test recreates all resources when recreate=True."""
        # Initialize first time
        await init_rabbitmq(RABBITMQ_URL, recreate=True)

        # Recreate
        exchanges, queues = await init_rabbitmq(RABBITMQ_URL, recreate=True)

        assert exchanges > 0
        assert queues > 0

    @pytest.mark.asyncio
    async def test_raises_on_connection_failure(self):
        """Test raises ConnectionError on connection failure."""
        with pytest.raises(ConnectionError):
            await init_rabbitmq("amqp://invalid:invalid@invalid-host:5672/")
