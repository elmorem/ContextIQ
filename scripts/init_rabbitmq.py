"""
RabbitMQ initialization script.

This script initializes RabbitMQ exchanges and queues for ContextIQ.
It creates all necessary queues with proper configuration and bindings.

Usage:
    python scripts/init_rabbitmq.py [--url URL] [--recreate]

Options:
    --url URL        RabbitMQ connection URL (default: amqp://guest:guest@localhost:5672/)
    --recreate       Delete and recreate existing queues/exchanges
"""

import argparse
import asyncio
import logging
import sys

from aio_pika import ExchangeType, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection

from shared.messaging.queues import Queues

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_connection(url: str) -> AbstractConnection:
    """
    Create and test RabbitMQ connection.

    Args:
        url: RabbitMQ connection URL

    Returns:
        Connected RabbitMQ connection

    Raises:
        ConnectionError: If unable to connect to RabbitMQ
    """
    try:
        connection = await connect_robust(url)
        logger.info(f"Successfully connected to RabbitMQ at {url}")
        return connection
    except Exception as e:
        raise ConnectionError(f"Failed to connect to RabbitMQ: {e}") from e


async def create_exchange(
    channel: AbstractChannel,
    exchange_name: str,
    exchange_type: ExchangeType = ExchangeType.TOPIC,
    recreate: bool = False,
) -> None:
    """
    Create a RabbitMQ exchange.

    Args:
        channel: RabbitMQ channel
        exchange_name: Name of the exchange
        exchange_type: Type of exchange (default: topic)
        recreate: If True, delete existing exchange before creating

    Raises:
        Exception: If exchange creation fails
    """
    if recreate:
        try:
            logger.info(f"Deleting existing exchange: {exchange_name}")
            await channel.exchange_delete(exchange_name)
        except Exception:
            # Exchange might not exist, that's ok
            pass

    logger.info(f"Creating exchange: {exchange_name}")
    await channel.declare_exchange(
        exchange_name,
        exchange_type,
        durable=True,
    )
    logger.info(f"Successfully created exchange: {exchange_name}")


async def create_queue_with_binding(
    channel: AbstractChannel,
    queue_name: str,
    exchange_name: str | None,
    routing_key: str | None,
    durable: bool = True,
    auto_delete: bool = False,
    recreate: bool = False,
) -> None:
    """
    Create a RabbitMQ queue and bind it to an exchange.

    Args:
        channel: RabbitMQ channel
        queue_name: Name of the queue
        exchange_name: Name of the exchange to bind to (None for default)
        routing_key: Routing key for binding (None for no binding)
        durable: If True, queue survives broker restart
        auto_delete: If True, queue is deleted when last consumer disconnects
        recreate: If True, delete existing queue before creating

    Raises:
        Exception: If queue creation or binding fails
    """
    if recreate:
        try:
            logger.info(f"Deleting existing queue: {queue_name}")
            await channel.queue_delete(queue_name)
        except Exception:
            # Queue might not exist, that's ok
            pass

    logger.info(f"Creating queue: {queue_name}")
    queue = await channel.declare_queue(
        queue_name,
        durable=durable,
        auto_delete=auto_delete,
    )
    logger.info(f"Successfully created queue: {queue_name}")

    # Bind queue to exchange if specified
    if exchange_name and routing_key:
        logger.info(f"Binding queue {queue_name} to exchange {exchange_name}")
        await queue.bind(exchange_name, routing_key=routing_key)
        logger.info(f"Successfully bound queue {queue_name}")


async def init_rabbitmq(url: str, recreate: bool = False) -> tuple[int, int]:
    """
    Initialize all RabbitMQ exchanges and queues.

    Args:
        url: RabbitMQ connection URL
        recreate: If True, delete and recreate existing exchanges/queues

    Returns:
        Tuple of (exchanges_created, queues_created)

    Raises:
        ConnectionError: If unable to connect to RabbitMQ
    """
    connection = await create_connection(url)
    channel = await connection.channel()

    try:
        # Get unique exchanges from queue configs
        exchanges = set()
        for queue_config in Queues.all_queues():
            if queue_config.exchange:
                exchanges.add(queue_config.exchange)

        # Create exchanges
        exchanges_created = 0
        for exchange in exchanges:
            await create_exchange(channel, exchange, recreate=recreate)
            exchanges_created += 1

        # Create queues and bindings
        queues_created = 0
        for queue_config in Queues.all_queues():
            await create_queue_with_binding(
                channel,
                queue_config.name,
                queue_config.exchange,
                queue_config.routing_key,
                durable=queue_config.durable,
                auto_delete=queue_config.auto_delete,
                recreate=recreate,
            )
            queues_created += 1

        return exchanges_created, queues_created

    finally:
        await connection.close()


async def main_async(url: str, recreate: bool) -> int:
    """
    Async main entry point.

    Args:
        url: RabbitMQ connection URL
        recreate: If True, delete and recreate existing resources

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        exchanges, queues = await init_rabbitmq(url, recreate)
        logger.info(
            f"Initialization complete: {exchanges} exchanges, {queues} queues created"
        )
        return 0

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return 1


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Initialize RabbitMQ exchanges and queues for ContextIQ"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="amqp://guest:guest@localhost:5672/",
        help="RabbitMQ connection URL (default: amqp://guest:guest@localhost:5672/)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate existing exchanges and queues",
    )

    args = parser.parse_args()

    return asyncio.run(main_async(args.url, args.recreate))


if __name__ == "__main__":
    sys.exit(main())
