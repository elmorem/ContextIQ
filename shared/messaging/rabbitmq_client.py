"""
RabbitMQ client with async connection management.
"""

from typing import Any

import aio_pika
from aio_pika import Channel, ExchangeType
from aio_pika.abc import AbstractRobustConnection

from shared.config.logging import get_logger
from shared.exceptions import MessagingError
from shared.messaging.queues import QueueConfig, Queues

logger = get_logger(__name__)


class RabbitMQClient:
    """RabbitMQ client with async connection pool and automatic reconnection."""

    def __init__(
        self,
        url: str,
        heartbeat: int = 60,
        connection_attempts: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize RabbitMQ client.

        Args:
            url: RabbitMQ connection URL
            heartbeat: Heartbeat interval in seconds
            connection_attempts: Number of connection attempts
            retry_delay: Delay between retry attempts in seconds
        """
        self.url = url
        self.heartbeat = heartbeat
        self.connection_attempts = connection_attempts
        self.retry_delay = retry_delay
        self._connection: AbstractRobustConnection | None = None
        self._channel: Channel | None = None
        self._exchanges: dict[str, Any] = {}
        self._queues: dict[str, Any] = {}

    async def connect(self) -> None:
        """
        Connect to RabbitMQ server.

        Raises:
            MessagingError: If connection fails
        """
        try:
            logger.info("rabbitmq_connecting", url=self.url)

            self._connection = await aio_pika.connect_robust(
                self.url,
                heartbeat=self.heartbeat,
            )

            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            logger.info("rabbitmq_connected")

        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise MessagingError(f"Failed to connect to RabbitMQ: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ server."""
        try:
            if self._channel:
                await self._channel.close()
                self._channel = None

            if self._connection:
                await self._connection.close()
                self._connection = None

            logger.info("rabbitmq_disconnected")

        except Exception as e:
            logger.error("rabbitmq_disconnect_failed", error=str(e))

    def get_channel(self) -> Channel:
        """
        Get RabbitMQ channel.

        Returns:
            RabbitMQ channel

        Raises:
            MessagingError: If not connected
        """
        if not self._channel:
            raise MessagingError("Not connected to RabbitMQ")
        return self._channel

    async def declare_exchange(
        self,
        name: str,
        exchange_type: ExchangeType = ExchangeType.TOPIC,
        durable: bool = True,
    ) -> Any:
        """
        Declare an exchange.

        Args:
            name: Exchange name
            exchange_type: Exchange type (topic, direct, fanout, headers)
            durable: Whether exchange survives broker restart

        Returns:
            Exchange instance

        Raises:
            MessagingError: If declaration fails
        """
        try:
            if name in self._exchanges:
                return self._exchanges[name]

            channel = self.get_channel()
            exchange = await channel.declare_exchange(
                name,
                exchange_type,
                durable=durable,
            )

            self._exchanges[name] = exchange
            logger.debug("exchange_declared", exchange=name, type=exchange_type.value)

            return exchange

        except Exception as e:
            logger.error("exchange_declaration_failed", exchange=name, error=str(e))
            raise MessagingError(f"Failed to declare exchange '{name}': {e}") from e

    async def declare_queue(self, config: QueueConfig) -> Any:
        """
        Declare a queue from configuration.

        Args:
            config: Queue configuration

        Returns:
            Queue instance

        Raises:
            MessagingError: If declaration fails
        """
        try:
            if config.name in self._queues:
                return self._queues[config.name]

            channel = self.get_channel()

            # Declare queue
            queue = await channel.declare_queue(
                config.name,
                durable=config.durable,
                auto_delete=config.auto_delete,
            )

            # Bind to exchange if specified
            if config.exchange and config.routing_key:
                exchange = await self.declare_exchange(config.exchange)
                await queue.bind(exchange, routing_key=config.routing_key)
                logger.debug(
                    "queue_bound",
                    queue=config.name,
                    exchange=config.exchange,
                    routing_key=config.routing_key,
                )

            self._queues[config.name] = queue
            logger.debug("queue_declared", queue=config.name)

            return queue

        except Exception as e:
            logger.error("queue_declaration_failed", queue=config.name, error=str(e))
            raise MessagingError(f"Failed to declare queue '{config.name}': {e}") from e

    async def setup_all_queues(self) -> None:
        """
        Set up all queues defined in Queues class.

        Raises:
            MessagingError: If setup fails
        """
        try:
            logger.info("setting_up_all_queues")

            for queue_config in Queues.all_queues():
                await self.declare_queue(queue_config)

            logger.info("all_queues_setup_complete")

        except Exception as e:
            logger.error("queue_setup_failed", error=str(e))
            raise MessagingError(f"Failed to set up queues: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if RabbitMQ connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._connection or self._connection.is_closed:
                return False

            if not self._channel or self._channel.is_closed:
                return False

            return True

        except Exception as e:
            logger.error("rabbitmq_health_check_failed", error=str(e))
            return False

    async def __aenter__(self) -> "RabbitMQClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
